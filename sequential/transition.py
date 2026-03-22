"""
Transition Function — S_{t+1} = S^M(S_t, x_t, W_{t+1})

The transition function models how the state evolves after each decision.
This is the engine of sequential learning in Parallax.

When the human makes a decision that diverges from the twin:
    1. Belief state updates (the twin learns what the human values)
    2. Decision history grows (more data for pattern detection)
    3. Resource state may change (time advances, emotional context shifts)

When an outcome is observed:
    1. Beliefs about capabilities and world state update
    2. If the human's faith-based override led to a positive outcome,
       that's the strongest possible faith-variable signal

This implements Powell's transition function with domain-specific
logic for the devudaaaa measurement framework.
"""

from datetime import datetime
from typing import Optional
from loguru import logger

from sequential.state import (
    State,
    BeliefState,
    BeliefType,
    Belief,
    DecisionRecord,
    ResourceState,
)


class TransitionFunction:
    """
    Implements S_{t+1} = S^M(S_t, x_t, W_{t+1}).

    The transition function has three triggers:
        1. decision_made   — Twin produces a recommendation (x_t)
        2. human_responded — Human provides their actual choice (part of W_{t+1})
        3. outcome_observed — Result of the decision becomes known (part of W_{t+1})

    Each trigger updates different components of the state.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        faith_threshold: float = 0.45,
        divergence_boost: float = 0.15,
    ):
        """
        Args:
            learning_rate: How fast beliefs update from evidence (Powell's VFA step size)
            faith_threshold: Below this confidence, decisions are faith-threshold flagged
            divergence_boost: Extra learning rate applied when human diverges
                              (divergences are more informative than agreements)
        """
        self.learning_rate = learning_rate
        self.faith_threshold = faith_threshold
        self.divergence_boost = divergence_boost

    def on_decision_made(
        self,
        state: State,
        record: DecisionRecord,
    ) -> State:
        """
        Trigger 1: The twin has produced a recommendation.

        This is called after the argumentation engine computes extensions
        and maps them to a decision. The record contains the twin's output
        but NOT the human's choice yet.

        Updates:
            - history: append the new decision record
            - step: increment
            - last_decision_at: update timestamp
        """
        state.history.add(record)
        state.step += 1
        state.last_decision_at = datetime.now().isoformat()

        logger.info(
            f"Step {state.step}: Twin decided '{record.twin_choice}' "
            f"(confidence={record.twin_confidence:.2f}, "
            f"below_threshold={record.below_faith_threshold})"
        )

        return state

    def on_human_responded(
        self,
        state: State,
        decision_id: str,
        human_choice: str,
        human_notes: str = "",
    ) -> State:
        """
        Trigger 2: The human has provided their actual choice.

        This is the critical moment for the devudaaaa research.
        If the human diverges, especially below the faith threshold,
        we have a faith-variable data point.

        Updates:
            - history: update the decision record with human's choice
            - beliefs: update value beliefs based on divergence pattern
        """
        # Find the decision record
        record = None
        for r in reversed(state.history.records):
            if r.decision_id == decision_id:
                record = r
                break

        if record is None:
            logger.warning(f"Decision {decision_id} not found in history")
            return state

        # Record the human's choice
        record.human_choice = human_choice
        record.human_notes = human_notes
        record.diverged = (human_choice.lower() != record.twin_choice.lower())

        # Classify the faith signal
        if record.diverged and record.below_faith_threshold:
            record.faith_signal = "STRONG"
            logger.info(
                f"🔮 FAITH DIVERGENCE at step {state.step}: "
                f"Twin='{record.twin_choice}' (conf={record.twin_confidence:.2f}), "
                f"Human='{human_choice}'. Below threshold. STRONG signal."
            )
        elif record.diverged:
            record.faith_signal = "MODERATE"
            logger.info(
                f"↔️ Divergence at step {state.step}: "
                f"Twin='{record.twin_choice}', Human='{human_choice}'"
            )
        else:
            record.faith_signal = "NONE"
            logger.debug(
                f"✓ Agreement at step {state.step}: '{human_choice}'"
            )

        # ── Update beliefs based on divergence ──
        if record.diverged:
            self._update_beliefs_from_divergence(state, record)

        return state

    def on_outcome_observed(
        self,
        state: State,
        decision_id: str,
        outcome_positive: bool,
        outcome_notes: str = "",
    ) -> State:
        """
        Trigger 3: The outcome of a decision is now known.

        This completes the feedback loop. If the human diverged
        AND the outcome was positive, that's the strongest signal:
        faith-based override led to a better result than logic predicted.

        Updates:
            - history: update outcome fields
            - beliefs: update capability and world beliefs
        """
        record = None
        for r in reversed(state.history.records):
            if r.decision_id == decision_id:
                record = r
                break

        if record is None:
            logger.warning(f"Decision {decision_id} not found for outcome")
            return state

        record.outcome_known = True
        record.outcome_positive = outcome_positive
        record.outcome_notes = outcome_notes

        # The most interesting case: human diverged AND outcome was positive
        if record.diverged and outcome_positive:
            if record.below_faith_threshold:
                logger.info(
                    f"⚡ FAITH VINDICATED at step {state.step}: "
                    f"Human overrode twin below threshold, and it WORKED. "
                    f"Decision: '{record.question[:50]}...'"
                )
            self._update_beliefs_from_outcome(state, record, vindicated=True)
        elif record.diverged and not outcome_positive:
            logger.info(
                f"📉 Divergence negative outcome at step {state.step}: "
                f"Human's override didn't work this time."
            )
            self._update_beliefs_from_outcome(state, record, vindicated=False)
        else:
            # Twin and human agreed — update world/capability beliefs normally
            self._update_beliefs_from_outcome(state, record, vindicated=None)

        return state

    # ─── BELIEF UPDATE INTERNALS ──────────────────────────────

    def _update_beliefs_from_divergence(
        self,
        state: State,
        record: DecisionRecord,
    ) -> None:
        """
        When the human diverges, update beliefs about their values.

        If the human chose to PROCEED where the twin said DECLINE,
        the human values something the twin's preference model underweights.
        We look at the arguments_for that the twin had and boost related
        value beliefs.

        If the human chose to DECLINE where the twin said PROCEED,
        the human is more cautious than the model predicts — boost
        risk-aversion and deliberation-related beliefs.
        """
        lr = self.learning_rate + self.divergence_boost  # Learn faster from divergences

        if record.human_choice and record.human_choice.lower() == "proceed":
            # Human was bolder than twin → boost action-oriented values
            for key in ["val_faith", "val_building", "val_autonomy"]:
                state.beliefs.update_belief_from_evidence(key, 1.0, lr)

        elif record.human_choice and record.human_choice.lower() == "decline":
            # Human was more cautious → boost deliberation values
            for key in ["val_truth", "val_wisdom"]:
                state.beliefs.update_belief_from_evidence(key, 1.0, lr)

        # Domain-specific preference learning
        if record.domain:
            pref_key = f"pref_domain_{record.domain}_boldness"
            existing = state.beliefs.get_belief(pref_key)
            if existing is None:
                state.beliefs.set_belief(Belief(
                    key=pref_key,
                    category=BeliefType.PREFERENCE,
                    description=f"Boldness tendency in {record.domain} decisions",
                    estimate=0.5,
                    confidence=0.1,
                    source="divergence_observed",
                ))
            observed = 0.8 if record.human_choice == "proceed" else 0.2
            state.beliefs.update_belief_from_evidence(pref_key, observed, lr)

    def _update_beliefs_from_outcome(
        self,
        state: State,
        record: DecisionRecord,
        vindicated: Optional[bool],
    ) -> None:
        """
        Update beliefs based on the observed outcome of a decision.

        If the human's faith-override was vindicated (positive outcome),
        the twin should increase its faith-variable estimate for this
        domain and context. This is Powell's VFA in action.
        """
        lr = self.learning_rate

        if vindicated is True:
            # Faith worked — the human was right to override logic
            state.beliefs.update_belief_from_evidence("val_faith", 1.0, lr * 1.5)
            # Update domain-specific capability belief
            if record.domain:
                cap_key = f"cap_intuition_{record.domain}"
                existing = state.beliefs.get_belief(cap_key)
                if existing is None:
                    state.beliefs.set_belief(Belief(
                        key=cap_key,
                        category=BeliefType.CAPABILITY,
                        description=f"Human's intuitive accuracy in {record.domain}",
                        estimate=0.5,
                        confidence=0.1,
                        source="outcome_observed",
                    ))
                state.beliefs.update_belief_from_evidence(cap_key, 1.0, lr)

        elif vindicated is False:
            # Override failed — logic was right
            state.beliefs.update_belief_from_evidence("val_faith", 0.3, lr)
            if record.domain:
                cap_key = f"cap_intuition_{record.domain}"
                existing = state.beliefs.get_belief(cap_key)
                if existing:
                    state.beliefs.update_belief_from_evidence(cap_key, 0.0, lr)

    # ─── STATE SERIALIZATION ──────────────────────────────────

    def checkpoint(self, state: State, path: str) -> None:
        """Save a state checkpoint for recovery."""
        state.save(path)
        logger.debug(f"State checkpoint saved at step {state.step}")
