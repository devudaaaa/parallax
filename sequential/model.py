"""
Sequential Decision Model — The Outer Loop of Parallax.

This is the orchestrator. It manages the complete decision cycle:

    1. Receive decision scenario
    2. Prepare state S_t for the argumentation layer
    3. Receive argumentation output (Phase 2 will provide this)
    4. Record twin's decision
    5. Receive human's actual choice
    6. Receive outcome
    7. Transition to S_{t+1}
    8. Loop

The model does NOT implement the argumentation layer itself —
that's Phase 2 (Dung/ASPARTIX). This model provides the INTERFACE
that the argumentation layer plugs into, and the SEQUENTIAL STRUCTURE
that gives meaning to individual decisions over time.

This separation of model from policy is Powell's key insight:
"Separate the creation of the model from the design of policies
for making decisions."
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from loguru import logger

from sequential.state import (
    State,
    BeliefState,
    DecisionHistory,
    DecisionRecord,
    ResourceState,
)
from sequential.transition import TransitionFunction


class DecisionScenario:
    """
    A decision scenario presented to the twin.

    This is the input at each decision step. The argumentation layer
    will construct an AF from this scenario + the current state.
    """

    def __init__(
        self,
        question: str,
        context: str = "",
        options: list[str] | None = None,
        domain: str = "",
        stakes_level: str = "medium",
        available_info: list[str] | None = None,
        metadata: dict | None = None,
    ):
        self.question = question
        self.context = context
        self.options = options or ["proceed", "decline", "defer"]
        self.domain = domain
        self.stakes_level = stakes_level
        self.available_info = available_info or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "context": self.context,
            "options": self.options,
            "domain": self.domain,
            "stakes_level": self.stakes_level,
            "available_info": self.available_info,
            "metadata": self.metadata,
        }


class ArgumentationResult:
    """
    The output of the argumentation layer (Phase 2).

    This is the INTERFACE that the Dung/ASPARTIX engine will implement.
    For now, it's a data class. In Phase 2, the argumentation engine
    will populate this with formally computed results.
    """

    def __init__(
        self,
        chosen: str = "uncertain",
        confidence: float = 0.5,
        reasoning: str = "",
        arguments_for: list[str] | None = None,
        arguments_against: list[str] | None = None,
        grounded_extension: list[str] | None = None,
        preferred_extensions: list[list[str]] | None = None,
        stable_extensions: list[list[str]] | None = None,
        af_size: int = 0,
        solver_used: str = "none",
    ):
        self.chosen = chosen
        self.confidence = confidence
        self.reasoning = reasoning
        self.arguments_for = arguments_for or []
        self.arguments_against = arguments_against or []
        self.grounded_extension = grounded_extension or []
        self.preferred_extensions = preferred_extensions or []
        self.stable_extensions = stable_extensions or []
        self.af_size = af_size
        self.solver_used = solver_used


# Type alias for the argumentation policy function
# Phase 2 will provide a real implementation
ArgumentationPolicy = Callable[[State, DecisionScenario], ArgumentationResult]


def placeholder_policy(state: State, scenario: DecisionScenario) -> ArgumentationResult:
    """
    Placeholder policy until Phase 2 (formal argumentation) is built.

    This mimics the current LLM-delegated approach so the sequential
    model can be tested end-to-end before the argumentation layer exists.
    """
    return ArgumentationResult(
        chosen="uncertain",
        confidence=0.5,
        reasoning="Placeholder — formal argumentation engine not yet integrated.",
        solver_used="placeholder",
    )


class SequentialDecisionModel:
    """
    The complete sequential decision model for Parallax.

    This is the main entry point. Initialize with a state and a policy
    (argumentation engine), then run decision scenarios through it.

    Usage:
        model = SequentialDecisionModel()
        model.set_policy(my_argumentation_engine)

        # Decision loop
        result = model.decide(scenario)
        model.record_human_choice(result.decision_id, "proceed")
        model.record_outcome(result.decision_id, positive=True)

        # Export research data
        analysis = model.get_analysis()
    """

    def __init__(
        self,
        state: State | None = None,
        policy: ArgumentationPolicy | None = None,
        faith_threshold: float = 0.45,
        persistence_path: str = "./data/sequential_state.json",
        db_path: str = "./data/decisions/sequential.db",
    ):
        self.state = state or State()
        self.policy = policy or placeholder_policy
        self.faith_threshold = faith_threshold
        self.transition = TransitionFunction(
            faith_threshold=faith_threshold,
        )
        self.persistence_path = persistence_path
        self._init_db(db_path)

    def _init_db(self, db_path: str) -> None:
        """Initialize SQLite for persistent decision storage."""
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sequential_decisions (
                decision_id TEXT PRIMARY KEY,
                step INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                domain TEXT,
                stakes_level TEXT,
                twin_choice TEXT,
                twin_confidence REAL,
                below_faith_threshold BOOLEAN,
                grounded_extension TEXT,
                preferred_extensions TEXT,
                arguments_for TEXT,
                arguments_against TEXT,
                human_choice TEXT,
                diverged BOOLEAN,
                faith_signal TEXT,
                outcome_positive BOOLEAN,
                outcome_notes TEXT,
                temporal_mode TEXT,
                solver_used TEXT,
                state_snapshot TEXT
            )
        """)
        self.db.commit()

    def set_policy(self, policy: ArgumentationPolicy) -> None:
        """
        Set the argumentation policy (decision-making engine).

        In Phase 2, this will be the formal Dung/ASPARTIX engine.
        The policy takes (State, DecisionScenario) and returns
        an ArgumentationResult with formally computed extensions.
        """
        self.policy = policy
        logger.info("Argumentation policy updated")

    def decide(self, scenario: DecisionScenario) -> DecisionRecord:
        """
        Run a decision scenario through the full pipeline.

        1. Prepare current state
        2. Call the argumentation policy
        3. Map result to a DecisionRecord
        4. Apply transition function (on_decision_made)
        5. Persist to database
        6. Return the record (caller provides human choice later)
        """
        # Step 1: Update resource state with current temporal context
        self.state.resources.current_time = datetime.now().isoformat()

        # Step 2: Call the argumentation policy
        result = self.policy(self.state, scenario)

        # Step 3: Build the decision record
        below_threshold = result.confidence < self.faith_threshold

        # Enforce the twin's rationality constraint
        if below_threshold and result.chosen.lower() == "proceed":
            logger.warning(
                f"Policy returned 'proceed' at confidence {result.confidence:.2f} "
                f"< threshold {self.faith_threshold}. Overriding to 'decline'."
            )
            result.chosen = "decline"

        record = DecisionRecord(
            decision_id=DecisionRecord.generate_id(scenario.question),
            timestamp=datetime.now().isoformat(),
            question=scenario.question,
            twin_choice=result.chosen,
            twin_confidence=result.confidence,
            twin_outcome=result.chosen,
            grounded_extension=result.grounded_extension,
            preferred_extensions=result.preferred_extensions,
            arguments_for=result.arguments_for,
            arguments_against=result.arguments_against,
            below_faith_threshold=below_threshold,
            temporal_mode=self.state.resources.temporal_mode,
            domain=scenario.domain,
            stakes_level=scenario.stakes_level,
        )

        # Step 4: Transition
        self.state = self.transition.on_decision_made(self.state, record)

        # Step 5: Persist
        self._persist_decision(record, result)

        return record

    def record_human_choice(
        self,
        decision_id: str,
        human_choice: str,
        notes: str = "",
    ) -> State:
        """
        Record what the real human chose.

        This is the Phase 3 data collection moment. The divergence
        between twin and human IS the faith variable.
        """
        self.state = self.transition.on_human_responded(
            self.state, decision_id, human_choice, notes,
        )

        # Update database
        self.db.execute(
            "UPDATE sequential_decisions SET human_choice=?, diverged=?, faith_signal=? "
            "WHERE decision_id=?",
            (human_choice,
             any(r.diverged for r in self.state.history.records if r.decision_id == decision_id),
             next((r.faith_signal for r in self.state.history.records if r.decision_id == decision_id), ""),
             decision_id),
        )
        self.db.commit()

        return self.state

    def record_outcome(
        self,
        decision_id: str,
        positive: bool,
        notes: str = "",
    ) -> State:
        """
        Record the outcome of a decision.

        Completes the feedback loop. If human diverged AND outcome
        was positive, we have the strongest faith-variable signal.
        """
        self.state = self.transition.on_outcome_observed(
            self.state, decision_id, positive, notes,
        )

        # Update database
        self.db.execute(
            "UPDATE sequential_decisions SET outcome_positive=?, outcome_notes=? "
            "WHERE decision_id=?",
            (positive, notes, decision_id),
        )
        self.db.commit()

        return self.state

    def _persist_decision(self, record: DecisionRecord, result: ArgumentationResult) -> None:
        """Write decision to persistent storage."""
        try:
            self.db.execute(
                """INSERT INTO sequential_decisions
                   (decision_id, step, timestamp, question, domain, stakes_level,
                    twin_choice, twin_confidence, below_faith_threshold,
                    grounded_extension, preferred_extensions,
                    arguments_for, arguments_against,
                    temporal_mode, solver_used)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.decision_id, self.state.step, record.timestamp,
                    record.question, record.domain, record.stakes_level,
                    record.twin_choice, record.twin_confidence,
                    record.below_faith_threshold,
                    json.dumps(result.grounded_extension),
                    json.dumps(result.preferred_extensions),
                    json.dumps(result.arguments_for),
                    json.dumps(result.arguments_against),
                    record.temporal_mode, result.solver_used,
                ),
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to persist decision: {e}")

    # ─── ANALYSIS & EXPORT ────────────────────────────────────

    def get_analysis(self) -> dict:
        """
        Get comprehensive sequential analysis for research export.

        This is the primary research output — the longitudinal
        faith-variable measurement.
        """
        history = self.state.history

        return {
            "model_summary": {
                "total_steps": self.state.step,
                "total_decisions": history.total_decisions,
                "decisions_with_human_data": len(history.decisions_with_human_data),
                "total_divergences": len(history.divergences),
                "faith_divergences": len(history.faith_divergences),
                "faith_threshold": self.faith_threshold,
            },
            "rates": {
                "divergence_rate": history.divergence_rate(),
                "faith_divergence_rate": history.faith_divergence_rate(),
                "domain_rates": history.domain_divergence_rates(),
                "temporal_rates": history.temporal_divergence_rates(),
            },
            "belief_state": self.state.beliefs.to_dict(),
            "faith_signal_strength": self.state.faith_signal_strength,
            "recent_decisions": [
                r.to_dict() for r in history.get_recent(20)
            ],
            "generated_at": datetime.now().isoformat(),
        }

    def export_for_research(self, path: str) -> None:
        """Export full analysis as JSON for research use."""
        analysis = self.get_analysis()
        with open(path, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        logger.info(f"Research export saved to {path}")

    def save_state(self) -> None:
        """Persist current state."""
        self.state.save(self.persistence_path)

    def load_state(self) -> None:
        """Load persisted state."""
        path = Path(self.persistence_path)
        if path.exists():
            self.state = State.load(str(path))
            logger.info(f"State loaded from {path} (step {self.state.step})")
