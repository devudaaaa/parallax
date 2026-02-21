"""
Temporal Engine — GTRBAC-based clock system for the Digital Twin.

Implements the periodic expression formalism from Bertino et al. (1998)
as researched at AIT for the Temporal Extension for RBAC.

This is the clock and scheduler that governs:
  - WHEN the twin is in which personality mode
  - WHAT access tier is active at any given time
  - HOW constraints, triggers, and schedules interact
  - WHERE the GTRBAC state machine (Enabled→Active→Disabled) applies

The τ (tick) runs every 60 seconds by default, evaluating all
temporal constraints and updating the twin's behavioral state.
"""

from .calendars import (
    CalendarUnit,
    CalendarSelector,
    WeekdaySelector,
    Duration,
    TimeInterval,
    PeriodicExpression,
    PeriodicExpressions,
    is_sub_calendar,
)

from .engine import (
    GTRBACEngine,
    RoleState,
    OperationMode,
    Operation,
    TemporalConstraint,
    Trigger,
    RoleSnapshot,
)

from loguru import logger

__all__ = [
    "CalendarUnit", "CalendarSelector", "WeekdaySelector",
    "Duration", "TimeInterval", "PeriodicExpression", "PeriodicExpressions",
    "is_sub_calendar",
    "GTRBACEngine", "RoleState", "OperationMode", "Operation",
    "TemporalConstraint", "Trigger", "RoleSnapshot",
    "create_default_twin_engine",
]


def create_default_twin_engine(tick_seconds: int = 60) -> GTRBACEngine:
    """
    Create a GTRBAC engine pre-configured with default digital twin policies.
    
    This maps the AIT GTRBAC research to the digital twin context:
    
    GTRBAC Concept        → Digital Twin Application
    ─────────────────────────────────────────────────
    Role                  → Behavioral mode (professional, casual, etc.)
    Role State            → Mode state (disabled/enabled/active)
    User-Role assignment  → Caller gets access to a mode
    Role-Permission       → Mode grants access tier
    Periodic constraint   → Schedule (work hours, evenings, weekends)
    Trigger               → Dependent mode activation
    Engine tick (τ)       → System heartbeat (1 min)
    
    Example AIT scenarios translated:
    
    AIT: "Supervisor vacation delegation for 2 weeks, Saturdays only"
    Twin: "Close-friend tier active evenings and weekends only"
    
    AIT: "Night-shift nurse enables when night-shift doctor enables"  
    Twin: "Reflective mode enables when evening-casual mode is active"
    """
    engine = GTRBACEngine(tick_interval_seconds=tick_seconds)
    
    # ── Register Roles (Twin Behavioral Modes) ─────────────
    
    # Personality modes
    engine.register_role("mode_professional", RoleState.DISABLED)
    engine.register_role("mode_casual", RoleState.DISABLED)
    engine.register_role("mode_reflective", RoleState.DISABLED)
    engine.register_role("mode_creative", RoleState.DISABLED)
    
    # Access tiers (as roles that can be enabled/disabled temporally)
    engine.register_role("tier_public", RoleState.ENABLED)      # always available
    engine.register_role("tier_friends", RoleState.DISABLED)
    engine.register_role("tier_close", RoleState.DISABLED)
    engine.register_role("tier_private", RoleState.DISABLED)
    
    # ── Add Temporal Constraints (Periodic Schedules) ──────
    
    # Work hours: 9am-5pm weekdays → professional mode
    engine.add_constraint(TemporalConstraint(
        name="work_hours_professional",
        periodic=PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.DAYS),
                CalendarSelector.select(
                    set(range(9, 17)), CalendarUnit.HOURS
                ),
            ],
            duration=Duration(1, CalendarUnit.HOURS),
            name="WorkHours",
        ),
        event_mode=OperationMode.ENABLE_ROLE,
        target="mode_professional",
        priority=5,
    ))
    
    # Evening hours: 6pm-11pm → casual mode
    engine.add_constraint(TemporalConstraint(
        name="evening_casual",
        periodic=PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.DAYS),
                CalendarSelector.select(
                    set(range(18, 24)), CalendarUnit.HOURS
                ),
            ],
            duration=Duration(1, CalendarUnit.HOURS),
            name="EveningHours",
        ),
        event_mode=OperationMode.ENABLE_ROLE,
        target="mode_casual",
        priority=5,
    ))
    
    # Late night: 11pm-2am → reflective mode (deep thinking time)
    engine.add_constraint(TemporalConstraint(
        name="late_night_reflective",
        periodic=PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.DAYS),
                CalendarSelector.select(
                    {23, 0, 1}, CalendarUnit.HOURS
                ),
            ],
            duration=Duration(1, CalendarUnit.HOURS),
            name="LateNight",
        ),
        event_mode=OperationMode.ENABLE_ROLE,
        target="mode_reflective",
        priority=5,
    ))
    
    # Friends tier: available during casual and reflective modes (evenings+)
    engine.add_constraint(TemporalConstraint(
        name="friends_tier_evening",
        periodic=PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.DAYS),
                CalendarSelector.select(
                    set(range(18, 24)) | {0, 1}, CalendarUnit.HOURS
                ),
            ],
            duration=Duration(1, CalendarUnit.HOURS),
            name="FriendsTierHours",
        ),
        event_mode=OperationMode.ENABLE_ROLE,
        target="tier_friends",
        priority=3,
    ))
    
    # Close tier: weekends + late nights only
    engine.add_constraint(TemporalConstraint(
        name="close_tier_personal_time",
        periodic=PeriodicExpression(
            selectors=[
                CalendarSelector.all(CalendarUnit.DAYS),
                CalendarSelector.select(
                    {22, 23, 0, 1}, CalendarUnit.HOURS
                ),
            ],
            duration=Duration(1, CalendarUnit.HOURS),
            name="CloseTierHours",
        ),
        event_mode=OperationMode.ENABLE_ROLE,
        target="tier_close",
        priority=2,
    ))
    
    # ── Add Triggers (Dependent Activations) ───────────────
    
    # "Night-shift nurse enables when night-shift doctor enables"
    # → Reflective mode triggers when casual mode is active at night
    engine.add_trigger(Trigger(
        name="reflective_from_casual_night",
        conditions=[
            ("mode_casual", RoleState.ENABLED),
            ("mode_reflective", RoleState.ENABLED),
        ],
        fire_mode=OperationMode.ACTIVATE_ROLE,
        fire_target="mode_reflective",
        fire_priority=3,
    ))
    
    # Professional mode auto-activates friends tier (colleagues)
    engine.add_trigger(Trigger(
        name="professional_enables_friends",
        conditions=[
            ("mode_professional", RoleState.ENABLED),
        ],
        fire_mode=OperationMode.ENABLE_ROLE,
        fire_target="tier_friends",
        fire_priority=4,
    ))
    
    logger.info(
        f"Default twin engine configured: "
        f"{len(engine.roles)} roles, "
        f"{len(engine.constraints)} constraints, "
        f"{len(engine.triggers)} triggers"
    )
    
    return engine
