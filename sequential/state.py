"""
State Variables for the Sequential Decision Model.

In Powell's framework, the state S_t contains ALL information needed to:
    1. Compute performance metrics
    2. Make decisions
    3. Model the evolution of the system over time

For Parallax, the state includes:
    - PersonalitySnapshot: Static + dynamic personality traits (from personality.py)
    - BeliefState: What the twin believes about uncertain quantities
    - DecisionHistory: Past decisions, outcomes, and divergence records
    - ResourceState: Temporal context from GTRBAC, emotional markers

The state is the COMPLETE input to the argumentation layer at each decision point.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════
# BELIEF STATE — What the twin believes about uncertain quantities
# ═══════════════════════════════════════════════════════════════

class BeliefType(str, Enum):
    """Categories of beliefs the twin maintains."""
    VALUE = "value"           # What the human values (updated by divergence)
    CAPABILITY = "capability" # What the human can do (updated by outcomes)
    PREFERENCE = "preference" # What the human prefers (updated by choices)
    WORLD = "world"           # What's true about the world (updated by events)


@dataclass
class Belief:
    """
    A single belief with uncertainty.

    The twin maintains beliefs about uncertain quantities.
    Each belief has a point estimate and a confidence measure.
    Beliefs are updated via the transition function when new
    information (W_{t+1}) arrives.

    For Parallax, the critical beliefs are about the human's VALUES —
    these determine the preference ordering in the argumentation framework.
    When the human diverges, value beliefs are updated to reflect
    what the human actually prioritizes.
    """
    key: str                              # Unique identifier
    category: BeliefType                  # What kind of belief
    description: str                      # Human-readable description
    estimate: float                       # Point estimate (0-1 for normalized, or raw)
    confidence: float = 0.5               # How confident in this estimate (0-1)
    evidence_count: int = 0               # How many observations support this
    last_updated: str = ""                # ISO timestamp
    source: str = "prior"                 # Where this belief came from

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "category": self.category.value,
            "description": self.description,
            "estimate": self.estimate,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "last_updated": self.last_updated,
            "source": self.source,
        }


@dataclass
class BeliefState:
    """
    The complete belief state of the twin at time t.

    This is the "knowledge state" component of S_t in Powell's framework.
    It tracks what the twin believes about:
        - The human's values (drives preference orderings in PAF/VAF)
        - The human's capabilities (affects argument generation)
        - The human's preferences (directly feeds ASPARTIX pref() facts)
        - The state of the world (situational arguments)

    Beliefs are updated by the transition function after each decision.
    The key insight: when the human DIVERGES from the twin's recommendation,
    the belief state updates to better reflect the human's actual values.
    This is Powell's VFA (Value Function Approximation) policy class.
    """
    beliefs: dict[str, Belief] = field(default_factory=dict)

    def set_belief(self, belief: Belief) -> None:
        """Add or update a belief."""
        self.beliefs[belief.key] = belief

    def get_belief(self, key: str) -> Optional[Belief]:
        """Retrieve a belief by key."""
        return self.beliefs.get(key)

    def get_beliefs_by_category(self, category: BeliefType) -> list[Belief]:
        """Get all beliefs of a given type."""
        return [b for b in self.beliefs.values() if b.category == category]

    def get_value_beliefs(self) -> list[Belief]:
        """Get beliefs about what the human values — feeds into PAF/VAF."""
        return self.get_beliefs_by_category(BeliefType.VALUE)

    def get_preference_beliefs(self) -> list[Belief]:
        """Get beliefs about preferences — directly maps to ASPARTIX pref() facts."""
        return self.get_beliefs_by_category(BeliefType.PREFERENCE)

    def update_belief_from_evidence(
        self,
        key: str,
        observed_value: float,
        learning_rate: float = 0.1,
    ) -> Optional[Belief]:
        """
        Bayesian-inspired belief update.

        When new evidence arrives (the human made a choice, an outcome occurred),
        update the belief towards the observed value. The learning rate controls
        how quickly the twin adapts.

        This is the core of Powell's VFA — learning from experience to improve
        future decisions.
        """
        belief = self.beliefs.get(key)
        if belief is None:
            return None

        # Weighted update: new_estimate = (1 - lr) * old + lr * observed
        old = belief.estimate
        belief.estimate = (1.0 - learning_rate) * old + learning_rate * observed_value

        # Confidence increases with evidence (asymptotic to 1.0)
        belief.evidence_count += 1
        belief.confidence = min(0.99, 1.0 - (1.0 / (1.0 + belief.evidence_count * 0.5)))

        belief.last_updated = datetime.now().isoformat()
        belief.source = "observed"

        return belief

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self.beliefs.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "BeliefState":
        state = cls()
        for k, v in data.items():
            v["category"] = BeliefType(v["category"])
            state.beliefs[k] = Belief(**v)
        return state

    @classmethod
    def default_beliefs(cls) -> "BeliefState":
        """
        Initialize with default beliefs derived from Ade's personality config.

        These are the prior beliefs before any divergence data is collected.
        They map directly to the personality engine's values and traits.
        """
        state = cls()
        # Value beliefs — from personality.py's values list
        default_values = [
            ("val_truth", "Values truth through scientific method", 0.85),
            ("val_wisdom", "Values wisdom as highest contribution", 0.90),
            ("val_faith", "Values faith as a real force", 0.80),
            ("val_building", "Values building things that matter", 0.85),
            ("val_understanding", "Values understanding what makes us human", 0.88),
            ("val_family", "Values family and close relationships", 0.90),
            ("val_autonomy", "Values independent thinking", 0.80),
        ]
        for key, desc, est in default_values:
            state.set_belief(Belief(
                key=key, category=BeliefType.VALUE,
                description=desc, estimate=est, confidence=0.3,
                source="personality_prior",
            ))

        # Preference beliefs — relative orderings for PAF
        default_prefs = [
            ("pref_family_over_profit", "Prefers family loyalty over financial gain", 0.85),
            ("pref_longterm_over_quick", "Prefers long-term strategy over quick wins", 0.75),
            ("pref_principle_over_convenience", "Prefers principled action over convenience", 0.70),
            ("pref_depth_over_breadth", "Prefers deep understanding over surface coverage", 0.80),
        ]
        for key, desc, est in default_prefs:
            state.set_belief(Belief(
                key=key, category=BeliefType.PREFERENCE,
                description=desc, estimate=est, confidence=0.3,
                source="personality_prior",
            ))

        return state


# ═══════════════════════════════════════════════════════════════
# DECISION HISTORY — Sequential record of past decisions
# ═══════════════════════════════════════════════════════════════

@dataclass
class DecisionRecord:
    """
    A single decision record in the sequential history.

    This captures both the twin's formal output and the human's actual choice,
    along with the argumentation details and outcome.
    """
    decision_id: str
    timestamp: str
    question: str

    # Twin's output (from argumentation layer)
    twin_choice: str                         # What the twin recommended
    twin_confidence: float                   # Formal confidence from extension analysis
    twin_outcome: str                        # proceed / decline / defer
    grounded_extension: list[str] = field(default_factory=list)
    preferred_extensions: list[list[str]] = field(default_factory=list)
    arguments_for: list[str] = field(default_factory=list)
    arguments_against: list[str] = field(default_factory=list)

    # Human's actual choice
    human_choice: Optional[str] = None
    human_notes: str = ""

    # Divergence analysis
    diverged: Optional[bool] = None
    below_faith_threshold: bool = False
    faith_signal: str = ""                   # STRONG / MODERATE / WEAK / NONE

    # Outcome (filled in later when result is known)
    outcome_known: bool = False
    outcome_positive: Optional[bool] = None
    outcome_notes: str = ""

    # Context
    access_tier: str = "private"
    temporal_mode: str = ""                  # From GTRBAC: professional/casual/reflective
    domain: str = ""                         # career / finance / relationship / health / etc.
    stakes_level: str = ""                   # low / medium / high / critical

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "question": self.question,
            "twin_choice": self.twin_choice,
            "twin_confidence": self.twin_confidence,
            "twin_outcome": self.twin_outcome,
            "grounded_extension": self.grounded_extension,
            "preferred_extensions": self.preferred_extensions,
            "arguments_for": self.arguments_for,
            "arguments_against": self.arguments_against,
            "human_choice": self.human_choice,
            "human_notes": self.human_notes,
            "diverged": self.diverged,
            "below_faith_threshold": self.below_faith_threshold,
            "faith_signal": self.faith_signal,
            "outcome_known": self.outcome_known,
            "outcome_positive": self.outcome_positive,
            "outcome_notes": self.outcome_notes,
            "access_tier": self.access_tier,
            "temporal_mode": self.temporal_mode,
            "domain": self.domain,
            "stakes_level": self.stakes_level,
        }

    @classmethod
    def generate_id(cls, question: str) -> str:
        """Generate a unique decision ID."""
        raw = f"{question}:{time.time()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class DecisionHistory:
    """
    Sequential record of all decisions.

    This is the "decision history" component of S_t.
    The transition function appends to this after each decision.
    The VFA policy class reads from this to learn patterns.
    """
    records: list[DecisionRecord] = field(default_factory=list)

    @property
    def total_decisions(self) -> int:
        return len(self.records)

    @property
    def decisions_with_human_data(self) -> list[DecisionRecord]:
        return [r for r in self.records if r.human_choice is not None]

    @property
    def divergences(self) -> list[DecisionRecord]:
        return [r for r in self.records if r.diverged is True]

    @property
    def faith_divergences(self) -> list[DecisionRecord]:
        return [r for r in self.records if r.diverged and r.below_faith_threshold]

    def add(self, record: DecisionRecord) -> None:
        self.records.append(record)

    def get_recent(self, n: int = 10) -> list[DecisionRecord]:
        return self.records[-n:]

    def get_by_domain(self, domain: str) -> list[DecisionRecord]:
        return [r for r in self.records if r.domain == domain]

    def divergence_rate(self) -> float:
        """Overall rate at which human overrides twin."""
        with_data = self.decisions_with_human_data
        if not with_data:
            return 0.0
        return len(self.divergences) / len(with_data)

    def faith_divergence_rate(self) -> float:
        """Rate of override specifically when below faith threshold."""
        below = [r for r in self.decisions_with_human_data if r.below_faith_threshold]
        if not below:
            return 0.0
        faith_divs = [r for r in below if r.diverged]
        return len(faith_divs) / len(below)

    def domain_divergence_rates(self) -> dict[str, float]:
        """Divergence rate broken down by decision domain."""
        by_domain: dict[str, list[DecisionRecord]] = {}
        for r in self.decisions_with_human_data:
            domain = r.domain or "unclassified"
            by_domain.setdefault(domain, []).append(r)
        return {
            d: len([r for r in recs if r.diverged]) / len(recs)
            for d, recs in by_domain.items()
            if recs
        }

    def temporal_divergence_rates(self) -> dict[str, float]:
        """Divergence rate broken down by temporal mode (from GTRBAC)."""
        by_mode: dict[str, list[DecisionRecord]] = {}
        for r in self.decisions_with_human_data:
            mode = r.temporal_mode or "unknown"
            by_mode.setdefault(mode, []).append(r)
        return {
            m: len([r for r in recs if r.diverged]) / len(recs)
            for m, recs in by_mode.items()
            if recs
        }

    def to_dict(self) -> dict:
        return {
            "total_decisions": self.total_decisions,
            "records": [r.to_dict() for r in self.records],
        }


# ═══════════════════════════════════════════════════════════════
# RESOURCE STATE — Temporal context and environmental conditions
# ═══════════════════════════════════════════════════════════════

@dataclass
class ResourceState:
    """
    Resource and environmental state at time t.

    Captures temporal context (from GTRBAC), emotional markers,
    and environmental conditions that affect decision-making.
    The temporal engine determines the agent's behavioral mode
    (professional/casual/reflective) which changes argument weights.
    """
    # Temporal context (from GTRBAC engine)
    current_time: str = ""
    temporal_mode: str = "default"       # professional / casual / reflective
    active_roles: list[str] = field(default_factory=list)

    # Environmental / resource markers
    time_pressure: float = 0.0           # 0 = no pressure, 1 = extreme
    emotional_valence: float = 0.5       # 0 = very negative, 1 = very positive
    cognitive_load: float = 0.3          # 0 = fresh, 1 = exhausted
    social_context: str = "alone"        # alone / private / social / public

    def to_dict(self) -> dict:
        return {
            "current_time": self.current_time,
            "temporal_mode": self.temporal_mode,
            "active_roles": self.active_roles,
            "time_pressure": self.time_pressure,
            "emotional_valence": self.emotional_valence,
            "cognitive_load": self.cognitive_load,
            "social_context": self.social_context,
        }


# ═══════════════════════════════════════════════════════════════
# COMPLETE STATE S_t — Everything the twin knows at time t
# ═══════════════════════════════════════════════════════════════

@dataclass
class State:
    """
    Complete state S_t at decision time t.

    This is the FULL input to the argumentation layer.
    Powell's framework: S_t contains all information needed to
    compute performance metrics, make decisions, and model evolution.

    Components:
        beliefs       → Drives preference orderings (PAF/VAF) in argumentation
        history       → Enables VFA learning from past divergences
        resources     → Temporal context affects argument weights
        personality   → PFA rules generating base arguments
        step          → Sequential decision index

    The personality_config is a snapshot from PersonalityEngine
    (not the full engine — just the config dict for serialization).
    """
    beliefs: BeliefState = field(default_factory=BeliefState.default_beliefs)
    history: DecisionHistory = field(default_factory=DecisionHistory)
    resources: ResourceState = field(default_factory=ResourceState)
    personality_config: dict = field(default_factory=dict)
    step: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_decision_at: Optional[str] = None

    @property
    def has_history(self) -> bool:
        return self.history.total_decisions > 0

    @property
    def faith_signal_strength(self) -> str:
        """
        Assess the overall strength of the faith variable signal.
        Based on accumulated divergence data.
        """
        rate = self.history.faith_divergence_rate()
        n = len(self.history.faith_divergences)
        if n == 0:
            return "NO_DATA"
        elif rate > 0.5 and n >= 5:
            return "STRONG"
        elif rate > 0.2 and n >= 3:
            return "MODERATE"
        elif n >= 1:
            return "WEAK"
        return "NO_DATA"

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "beliefs": self.beliefs.to_dict(),
            "history": self.history.to_dict(),
            "resources": self.resources.to_dict(),
            "personality_config": self.personality_config,
            "created_at": self.created_at,
            "last_decision_at": self.last_decision_at,
            "faith_signal_strength": self.faith_signal_strength,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def save(self, path: str) -> None:
        """Persist state to disk."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "State":
        """Load state from disk."""
        with open(path, "r") as f:
            data = json.loads(f.read())
        state = cls()
        state.step = data.get("step", 0)
        state.created_at = data.get("created_at", "")
        state.last_decision_at = data.get("last_decision_at")
        state.personality_config = data.get("personality_config", {})
        if "beliefs" in data:
            state.beliefs = BeliefState.from_dict(data["beliefs"])
        if "resources" in data:
            r = data["resources"]
            state.resources = ResourceState(**r)
        # History reconstruction from dict is heavier — handled separately
        return state
