"""
Calendar System — Implements the Periodic Time formalism from Bertino et al. (1998).

Based on Ade's AIT research: "Temporal Extension for RBAC"
Section 2.1.1 — Periodic Expression

Core concepts implemented:
  - Calendars (Hours, Days, Weeks, Months, Years) as countable sets of border intervals
  - Sub-calendar relation: C1 ⊑ C2
  - generate() function for deriving new calendars
  - Basic calendar τ (tick) — the smallest unit / heartbeat of the system
  - Periodic expressions: ⟨[begin,end], P⟩ where P = Σ O_i.C_i ▷ x.C_d

Reference:
  Bertino, E., Bettini, C., Ferrari, E., & Samarati, P. (1998).
  An access control model supporting periodicity constraints and temporal reasoning.
  ACM Transactions on Database Systems (TODS), 23(3), 231–285.

  Niezette, M., & Stevenne, J. (1992).
  An efficient symbolic representation of periodic time.
  Proceedings of CIKM, 161–168.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import Optional, Iterator
from loguru import logger


# ═══════════════════════════════════════════════════════════
# Calendar Definitions
# ═══════════════════════════════════════════════════════════

class CalendarUnit(Enum):
    """
    Standard calendar units forming the hierarchy.
    
    From the paper: "if the set of calendars consists of calendars
    of Hours, Days, Weeks, Months, Years, then the basic calendar
    which is Hours will be the tick of the system (τ)."
    
    We extend to include Minutes as our tick (τ) since the GTRBAC
    engine implementation runs every 1 minute.
    """
    MINUTES = auto()    # τ — tick of the system
    HOURS = auto()
    DAYS = auto()
    WEEKS = auto()
    MONTHS = auto()
    YEARS = auto()

    @property
    def to_minutes(self) -> int:
        """Approximate conversion to minutes (the base tick τ)."""
        conversions = {
            CalendarUnit.MINUTES: 1,
            CalendarUnit.HOURS: 60,
            CalendarUnit.DAYS: 1440,
            CalendarUnit.WEEKS: 10080,
            CalendarUnit.MONTHS: 43200,    # ~30 days
            CalendarUnit.YEARS: 525600,    # ~365 days
        }
        return conversions[self]


# Sub-calendar relation: C1 ⊑ C2
# "C1 is the sub-calendar of C2 iff every interval of C2 can be
#  covered by definite intervals in C1"
SUB_CALENDAR_ORDER = [
    CalendarUnit.MINUTES,
    CalendarUnit.HOURS,
    CalendarUnit.DAYS,
    CalendarUnit.WEEKS,
    CalendarUnit.MONTHS,
    CalendarUnit.YEARS,
]


def is_sub_calendar(c1: CalendarUnit, c2: CalendarUnit) -> bool:
    """Check if c1 ⊑ c2 (c1 is sub-calendar of c2)."""
    return SUB_CALENDAR_ORDER.index(c1) <= SUB_CALENDAR_ORDER.index(c2)


# ═══════════════════════════════════════════════════════════
# Time Interval
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TimeInterval:
    """
    A time interval [begin, end].
    
    From the paper: "the interval [begin,end] will be the time interval
    which denotes the upper limit and lower limit which should be put
    on the P instants."
    """
    begin: datetime
    end: datetime

    def __post_init__(self):
        if self.begin > self.end:
            raise ValueError(f"begin ({self.begin}) must be <= end ({self.end})")

    def contains(self, t: datetime) -> bool:
        """Check if time t falls within this interval."""
        return self.begin <= t <= self.end

    def contains_interval(self, other: TimeInterval) -> bool:
        """Check if another interval is fully contained."""
        return self.begin <= other.begin and other.end <= self.end

    def overlaps(self, other: TimeInterval) -> bool:
        """Check if two intervals overlap."""
        return self.begin <= other.end and other.begin <= self.end

    @property
    def duration(self) -> timedelta:
        return self.end - self.begin

    @property
    def duration_minutes(self) -> float:
        return self.duration.total_seconds() / 60

    def __repr__(self):
        return f"[{self.begin.strftime('%Y-%m-%d %H:%M')}, {self.end.strftime('%Y-%m-%d %H:%M')}]"


# ═══════════════════════════════════════════════════════════
# Calendar Selector (O_i in the periodic expression)
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CalendarSelector:
    """
    Represents O_i.C_i in the periodic expression.
    
    From Definition 2.0.1:
        P = Σ(i=1 to n) O_i.C_i ▷ x.C_d
    
    Where O_i ∈ 2^N ∪ {all} selects specific intervals from calendar C_i.
    
    Examples:
        - all.Years          → every year
        - {2,8}.Months       → 2nd and 8th month
        - {1}.Days           → 1st day
        - {9,10,11}.Hours    → hours 9, 10, 11
    """
    indices: frozenset[int] | None  # None = "all"
    calendar: CalendarUnit

    @classmethod
    def all(cls, calendar: CalendarUnit) -> CalendarSelector:
        """Select all intervals: 'all.Calendar'"""
        return cls(indices=None, calendar=calendar)

    @classmethod
    def select(cls, indices: set[int], calendar: CalendarUnit) -> CalendarSelector:
        """Select specific intervals: '{indices}.Calendar'"""
        return cls(indices=frozenset(indices), calendar=calendar)

    @property
    def is_all(self) -> bool:
        return self.indices is None

    def matches(self, t: datetime) -> bool:
        """Check if time t matches this selector."""
        if self.is_all:
            return True

        value = self._extract_calendar_value(t)
        return value in self.indices

    def _extract_calendar_value(self, t: datetime) -> int:
        """Extract the calendar-specific index from a datetime."""
        if self.calendar == CalendarUnit.MINUTES:
            return t.minute
        elif self.calendar == CalendarUnit.HOURS:
            return t.hour
        elif self.calendar == CalendarUnit.DAYS:
            return t.day
        elif self.calendar == CalendarUnit.WEEKS:
            return t.isocalendar()[1]  # ISO week number
        elif self.calendar == CalendarUnit.MONTHS:
            return t.month
        elif self.calendar == CalendarUnit.YEARS:
            return t.year
        raise ValueError(f"Unknown calendar unit: {self.calendar}")

    def __repr__(self):
        if self.is_all:
            return f"all.{self.calendar.name}"
        return f"{{{','.join(str(i) for i in sorted(self.indices))}}}.{self.calendar.name}"


# ═══════════════════════════════════════════════════════════
# Duration Expression
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Duration:
    """
    Duration expression: x.C_d
    
    The ▷ symbol in P separates the starting point specification
    from the duration specification in terms of calendar C_d.
    
    Example: 3.Months → duration of 3 months
             2.Hours  → duration of 2 hours
    """
    count: int
    calendar: CalendarUnit

    @property
    def to_timedelta(self) -> timedelta:
        """Convert to Python timedelta (approximate for months/years)."""
        return timedelta(minutes=self.count * self.calendar.to_minutes)

    def __repr__(self):
        return f"{self.count}.{self.calendar.name}"


# ═══════════════════════════════════════════════════════════
# Periodic Expression — The Core Formalism
# ═══════════════════════════════════════════════════════════

@dataclass
class PeriodicExpression:
    """
    Periodic Expression — Definition 2.0.1 (Bertino et al., 1998)
    
    Given calendars C_d, C_1, ..., C_n, a periodic expression P is:
    
        P = Σ(i=1 to n) O_i.C_i ▷ x.C_d
    
    The full temporal constraint is the pair ⟨[begin, end], P⟩ where:
        - [begin, end] bounds the infinite set of periodic instants
        - P generates the actual intervals within those bounds
    
    Examples from the AIT research:
        - all.Years + {2,8}.Months ▷ 3.Months
          → intervals starting at 2nd and 8th month of every year, 
            each lasting 3 months
        
        - Saturday between 10am-4pm (AIT cafeteria delegation):
          all.Weeks + {6}.Days + {10,11,12,13,14,15}.Hours ▷ 1.Hours
    
    Applied to the Digital Twin:
        - all.Days + {9,10,11,12,13,14,15,16,17}.Hours ▷ 1.Hours
          → work hours (9am-5pm daily) — twin in professional mode
        
        - all.Weeks + {6,7}.Days ▷ 1.Days
          → weekends — twin in casual/personal mode
    """

    # The selectors: O_1.C_1 + O_2.C_2 + ... + O_n.C_n
    selectors: list[CalendarSelector]

    # The duration: x.C_d (how long each generated interval lasts)
    duration: Duration

    # The bounding interval: [begin, end]
    # None = unbounded (infinite, as per the original formalism)
    bound: TimeInterval | None = None

    # Human-readable name for this expression
    name: str = ""

    def is_active(self, t: datetime) -> bool:
        """
        Check if time t falls within any interval generated by this
        periodic expression.
        
        This is the core evaluation — used by the GTRBAC engine
        every tick to determine what's currently active.
        """
        # Check bounds first
        if self.bound and not self.bound.contains(t):
            return False

        # All selectors must match (they form the conjunction
        # that identifies the starting point of intervals)
        return all(sel.matches(t) for sel in self.selectors)

    def next_activation(self, after: datetime) -> datetime | None:
        """
        Find the next time this expression becomes active after
        a given datetime. Useful for scheduling.
        
        Searches forward up to 1 year (limited to prevent infinite loops).
        """
        # Step forward by the smallest calendar unit in our selectors
        step = timedelta(minutes=1)  # τ tick

        # For efficiency, step by the smallest selector's calendar
        smallest = min(
            (s.calendar for s in self.selectors),
            key=lambda c: c.to_minutes,
            default=CalendarUnit.MINUTES,
        )
        if smallest.to_minutes > 1:
            step = timedelta(minutes=smallest.to_minutes)

        current = after + step
        max_search = after + timedelta(days=366)  # 1 year limit

        while current < max_search:
            if self.is_active(current):
                return current
            current += step

        return None

    def generate_intervals(
        self,
        start: datetime,
        end: datetime,
        max_intervals: int = 1000,
    ) -> list[TimeInterval]:
        """
        Generate all intervals within [start, end] that match
        this periodic expression.
        
        Used for visualization and schedule planning.
        """
        intervals = []
        current = start
        step = timedelta(minutes=max(1, min(s.calendar.to_minutes for s in self.selectors)))

        in_active = False
        interval_start = None

        while current <= end and len(intervals) < max_intervals:
            active = self.is_active(current)

            if active and not in_active:
                # Start of a new interval
                interval_start = current
                in_active = True
            elif not active and in_active:
                # End of interval
                intervals.append(TimeInterval(begin=interval_start, end=current))
                in_active = False

            current += step

        # Close any open interval
        if in_active and interval_start:
            intervals.append(TimeInterval(begin=interval_start, end=current))

        return intervals

    def __repr__(self):
        parts = " + ".join(str(s) for s in self.selectors)
        expr = f"{parts} ▷ {self.duration}"
        if self.bound:
            return f"⟨{self.bound}, {expr}⟩"
        if self.name:
            return f"{self.name} = {expr}"
        return expr


# ═══════════════════════════════════════════════════════════
# Convenience Builders — Common periodic patterns
# ═══════════════════════════════════════════════════════════

class PeriodicExpressions:
    """
    Factory for common periodic expressions used in the digital twin.
    
    These map the GTRBAC temporal constraints from the AIT research
    to digital twin behaviors.
    """

    @staticmethod
    def work_hours(start_hour: int = 9, end_hour: int = 17) -> PeriodicExpression:
        """
        Work hours — twin is in professional/formal mode.
        
        Example from AIT: faculty availability "at least six hours per week"
        """
        hours = set(range(start_hour, end_hour))
        return PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.DAYS),
                CalendarSelector.select(hours, CalendarUnit.HOURS),
            ],
            duration=Duration(1, CalendarUnit.HOURS),
            name="WorkHours",
        )

    @staticmethod
    def weekdays() -> PeriodicExpression:
        """Monday through Friday (ISO weekday 1-5)."""
        return PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.WEEKS),
                WeekdaySelector(indices=frozenset({1, 2, 3, 4, 5}), calendar=CalendarUnit.DAYS),
            ],
            duration=Duration(1, CalendarUnit.DAYS),
            name="Weekdays",
        )

    @staticmethod
    def weekends() -> PeriodicExpression:
        """
        Saturday and Sunday (ISO weekday 6-7) — twin in casual/personal mode.
        
        From AIT cafeteria scenario: "only on Saturdays because
        the transactions are done at weekends only"
        """
        return PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.WEEKS),
                WeekdaySelector(indices=frozenset({6, 7}), calendar=CalendarUnit.DAYS),
            ],
            duration=Duration(1, CalendarUnit.DAYS),
            name="Weekends",
        )

    @staticmethod
    def evening_hours(start: int = 18, end: int = 23) -> PeriodicExpression:
        """Evening — twin in reflective/personal mode."""
        return PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.DAYS),
                CalendarSelector.select(set(range(start, end + 1)), CalendarUnit.HOURS),
            ],
            duration=Duration(1, CalendarUnit.HOURS),
            name="EveningHours",
        )

    @staticmethod
    def specific_months(months: set[int], duration_months: int = 1) -> PeriodicExpression:
        """
        Specific months of the year.
        
        From the paper example: all.Years + {2,8}.Months ▷ 3.Months
        """
        return PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.YEARS),
                CalendarSelector.select(months, CalendarUnit.MONTHS),
            ],
            duration=Duration(duration_months, CalendarUnit.MONTHS),
            name=f"Months_{months}",
        )

    @staticmethod
    def bounded_period(
        begin: datetime,
        end: datetime,
        hours: set[int] | None = None,
    ) -> PeriodicExpression:
        """
        A time-bounded periodic expression.
        
        Like the AIT delegation scenario:
        "03/05/2019 to 17/05/2019, Saturday between 10am-4pm"
        """
        selectors = [CalendarSelector.all(CalendarUnit.DAYS)]
        if hours:
            selectors.append(CalendarSelector.select(hours, CalendarUnit.HOURS))

        return PeriodicExpression(
            selectors=selectors,
            duration=Duration(1, CalendarUnit.HOURS),
            bound=TimeInterval(begin=begin, end=end),
            name="BoundedPeriod",
        )

    @staticmethod
    def every_n_minutes(n: int) -> PeriodicExpression:
        """
        Every N minutes — for the engine tick.
        
        From the GTRBAC implementation: "we choose to run the engine
        every 1 minute in the current implementation"
        """
        # Select minutes that are multiples of n
        minutes = set(range(0, 60, n))
        return PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.HOURS),
                CalendarSelector.select(minutes, CalendarUnit.MINUTES),
            ],
            duration=Duration(n, CalendarUnit.MINUTES),
            name=f"Every{n}Min",
        )


# ═══════════════════════════════════════════════════════════
# Calendar-aware Weekday Selector (extension)
# ═══════════════════════════════════════════════════════════

class WeekdaySelector(CalendarSelector):
    """
    Extended selector that understands weekday vs weekend.
    
    Standard CalendarSelector uses calendar indices. This adds
    awareness of Monday=1 through Sunday=7 (ISO weekday).
    """

    def matches(self, t: datetime) -> bool:
        if self.calendar != CalendarUnit.DAYS:
            return super().matches(t)

        if self.is_all:
            return True

        # Use ISO weekday (1=Mon, 7=Sun)
        return t.isoweekday() in self.indices
