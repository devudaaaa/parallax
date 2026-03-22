"""
Tests for the Sequential Decision Model (Phase 1).

Tests cover:
    1. State initialization and serialization
    2. Belief state CRUD and Bayesian updates
    3. Decision history tracking and analytics
    4. Transition function (all three triggers)
    5. Full sequential decision loop
    6. Faith variable signal detection
    7. State persistence (save/load)
"""

import json
import os
import tempfile

import pytest

from sequential.state import (
    State,
    BeliefState,
    BeliefType,
    Belief,
    DecisionHistory,
    DecisionRecord,
    ResourceState,
)
from sequential.transition import TransitionFunction
from sequential.model import (
    SequentialDecisionModel,
    DecisionScenario,
    ArgumentationResult,
    placeholder_policy,
)


# ═══════════════════════════════════════════════════════════════
# BELIEF STATE TESTS
# ═══════════════════════════════════════════════════════════════

class TestBeliefState:

    def test_default_beliefs_initialized(self):
        bs = BeliefState.default_beliefs()
        assert len(bs.beliefs) > 0
        assert bs.get_belief("val_faith") is not None
        assert bs.get_belief("val_faith").category == BeliefType.VALUE

    def test_set_and_get_belief(self):
        bs = BeliefState()
        b = Belief(key="test_key", category=BeliefType.VALUE,
                    description="Test belief", estimate=0.7)
        bs.set_belief(b)
        retrieved = bs.get_belief("test_key")
        assert retrieved is not None
        assert retrieved.estimate == 0.7

    def test_get_beliefs_by_category(self):
        bs = BeliefState.default_beliefs()
        values = bs.get_value_beliefs()
        prefs = bs.get_preference_beliefs()
        assert len(values) > 0
        assert len(prefs) > 0
        assert all(b.category == BeliefType.VALUE for b in values)
        assert all(b.category == BeliefType.PREFERENCE for b in prefs)

    def test_belief_update_from_evidence(self):
        bs = BeliefState.default_beliefs()
        faith = bs.get_belief("val_faith")
        original_estimate = faith.estimate
        original_count = faith.evidence_count

        bs.update_belief_from_evidence("val_faith", 1.0, learning_rate=0.2)

        updated = bs.get_belief("val_faith")
        assert updated.estimate > original_estimate
        assert updated.evidence_count == original_count + 1
        assert updated.confidence > 0.0
        assert updated.source == "observed"

    def test_belief_update_nonexistent_key(self):
        bs = BeliefState()
        result = bs.update_belief_from_evidence("nonexistent", 1.0)
        assert result is None

    def test_belief_confidence_grows_with_evidence(self):
        bs = BeliefState()
        bs.set_belief(Belief(key="x", category=BeliefType.VALUE,
                             description="test", estimate=0.5, confidence=0.1))
        for _ in range(20):
            bs.update_belief_from_evidence("x", 0.8, 0.1)
        assert bs.get_belief("x").confidence > 0.8

    def test_serialization_roundtrip(self):
        bs = BeliefState.default_beliefs()
        data = bs.to_dict()
        restored = BeliefState.from_dict(data)
        assert len(restored.beliefs) == len(bs.beliefs)
        for key in bs.beliefs:
            assert restored.get_belief(key).estimate == bs.get_belief(key).estimate


# ═══════════════════════════════════════════════════════════════
# DECISION HISTORY TESTS
# ═══════════════════════════════════════════════════════════════

class TestDecisionHistory:

    def _make_record(self, diverged=False, below_threshold=False,
                     domain="career", human_choice="proceed", temporal_mode="professional"):
        r = DecisionRecord(
            decision_id=DecisionRecord.generate_id("test"),
            timestamp="2026-03-19T12:00:00",
            question="Should I take this opportunity?",
            twin_choice="decline" if diverged else "proceed",
            twin_confidence=0.3 if below_threshold else 0.7,
            twin_outcome="decline" if diverged else "proceed",
            human_choice=human_choice,
            diverged=diverged,
            below_faith_threshold=below_threshold,
            faith_signal="STRONG" if (diverged and below_threshold) else "NONE",
            domain=domain,
            temporal_mode=temporal_mode,
        )
        return r

    def test_empty_history(self):
        h = DecisionHistory()
        assert h.total_decisions == 0
        assert h.divergence_rate() == 0.0
        assert h.faith_divergence_rate() == 0.0

    def test_add_and_retrieve(self):
        h = DecisionHistory()
        r = self._make_record()
        h.add(r)
        assert h.total_decisions == 1
        assert len(h.get_recent(5)) == 1

    def test_divergence_tracking(self):
        h = DecisionHistory()
        h.add(self._make_record(diverged=False))
        h.add(self._make_record(diverged=True))
        h.add(self._make_record(diverged=True, below_threshold=True))

        assert len(h.divergences) == 2
        assert len(h.faith_divergences) == 1
        assert h.divergence_rate() == pytest.approx(2 / 3, abs=0.01)

    def test_domain_breakdown(self):
        h = DecisionHistory()
        h.add(self._make_record(diverged=True, domain="career"))
        h.add(self._make_record(diverged=False, domain="career"))
        h.add(self._make_record(diverged=True, domain="finance"))

        rates = h.domain_divergence_rates()
        assert rates["career"] == pytest.approx(0.5)
        assert rates["finance"] == pytest.approx(1.0)

    def test_temporal_breakdown(self):
        h = DecisionHistory()
        h.add(self._make_record(diverged=True, temporal_mode="reflective"))
        h.add(self._make_record(diverged=False, temporal_mode="professional"))

        rates = h.temporal_divergence_rates()
        assert rates["reflective"] == 1.0
        assert rates["professional"] == 0.0


# ═══════════════════════════════════════════════════════════════
# STATE TESTS
# ═══════════════════════════════════════════════════════════════

class TestState:

    def test_default_initialization(self):
        s = State()
        assert s.step == 0
        assert s.has_history is False
        assert s.faith_signal_strength == "NO_DATA"
        assert len(s.beliefs.beliefs) > 0  # Default beliefs

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            s = State()
            s.step = 5
            s.beliefs.update_belief_from_evidence("val_faith", 0.9, 0.2)
            s.save(path)

            loaded = State.load(path)
            assert loaded.step == 5
            assert loaded.beliefs.get_belief("val_faith").estimate > 0.8
        finally:
            os.unlink(path)

    def test_to_json(self):
        s = State()
        j = s.to_json()
        data = json.loads(j)
        assert "step" in data
        assert "beliefs" in data
        assert "faith_signal_strength" in data


# ═══════════════════════════════════════════════════════════════
# TRANSITION FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════

class TestTransitionFunction:

    def _make_state_and_record(self, confidence=0.7):
        state = State()
        record = DecisionRecord(
            decision_id="test_001",
            timestamp="2026-03-19T12:00:00",
            question="Should I invest in this startup?",
            twin_choice="decline" if confidence < 0.45 else "proceed",
            twin_confidence=confidence,
            twin_outcome="decline" if confidence < 0.45 else "proceed",
            below_faith_threshold=confidence < 0.45,
            domain="finance",
            stakes_level="high",
        )
        return state, record

    def test_on_decision_made(self):
        tf = TransitionFunction()
        state, record = self._make_state_and_record()

        state = tf.on_decision_made(state, record)
        assert state.step == 1
        assert state.history.total_decisions == 1
        assert state.last_decision_at is not None

    def test_on_human_agreed(self):
        tf = TransitionFunction()
        state, record = self._make_state_and_record(confidence=0.7)
        state = tf.on_decision_made(state, record)

        state = tf.on_human_responded(state, "test_001", "proceed")
        r = state.history.records[0]
        assert r.diverged is False
        assert r.faith_signal == "NONE"

    def test_on_human_diverged_above_threshold(self):
        tf = TransitionFunction()
        state, record = self._make_state_and_record(confidence=0.7)
        state = tf.on_decision_made(state, record)

        state = tf.on_human_responded(state, "test_001", "decline")
        r = state.history.records[0]
        assert r.diverged is True
        assert r.faith_signal == "MODERATE"

    def test_on_human_diverged_below_threshold(self):
        """The most important case: faith divergence."""
        tf = TransitionFunction()
        state, record = self._make_state_and_record(confidence=0.3)
        state = tf.on_decision_made(state, record)

        state = tf.on_human_responded(state, "test_001", "proceed")
        r = state.history.records[0]
        assert r.diverged is True
        assert r.below_faith_threshold is True
        assert r.faith_signal == "STRONG"

    def test_belief_updates_on_divergence(self):
        tf = TransitionFunction()
        state, record = self._make_state_and_record(confidence=0.3)
        faith_before = state.beliefs.get_belief("val_faith").estimate

        state = tf.on_decision_made(state, record)
        state = tf.on_human_responded(state, "test_001", "proceed")

        faith_after = state.beliefs.get_belief("val_faith").estimate
        assert faith_after > faith_before  # Faith belief should increase

    def test_outcome_observed_faith_vindicated(self):
        tf = TransitionFunction()
        state, record = self._make_state_and_record(confidence=0.3)

        state = tf.on_decision_made(state, record)
        state = tf.on_human_responded(state, "test_001", "proceed")
        state = tf.on_outcome_observed(state, "test_001", outcome_positive=True)

        r = state.history.records[0]
        assert r.outcome_known is True
        assert r.outcome_positive is True

    def test_domain_belief_created_on_divergence(self):
        tf = TransitionFunction()
        state, record = self._make_state_and_record(confidence=0.3)

        state = tf.on_decision_made(state, record)
        state = tf.on_human_responded(state, "test_001", "proceed")

        domain_belief = state.beliefs.get_belief("pref_domain_finance_boldness")
        assert domain_belief is not None
        assert domain_belief.estimate > 0.5  # Human was bold → estimate > 0.5


# ═══════════════════════════════════════════════════════════════
# FULL SEQUENTIAL MODEL TESTS
# ═══════════════════════════════════════════════════════════════

class TestSequentialDecisionModel:

    def _make_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            return SequentialDecisionModel(
                persistence_path=os.path.join(tmpdir, "state.json"),
                db_path=os.path.join(tmpdir, "decisions.db"),
            ), tmpdir

    def test_initialization(self):
        model, _ = self._make_model()
        assert model.state.step == 0
        assert model.faith_threshold == 0.45

    def test_decide_with_placeholder(self):
        model, _ = self._make_model()
        scenario = DecisionScenario(
            question="Should I accept the job offer?",
            domain="career",
            stakes_level="high",
        )
        record = model.decide(scenario)
        assert record.decision_id != ""
        assert model.state.step == 1

    def test_full_loop(self):
        """Test the complete: decide → human responds → outcome."""
        model, _ = self._make_model()

        # Custom policy that returns a real result
        def test_policy(state, scenario):
            return ArgumentationResult(
                chosen="proceed",
                confidence=0.65,
                reasoning="Test reasoning",
                arguments_for=["market is good", "team is ready"],
                arguments_against=["cash is low"],
                grounded_extension=["proceed", "market_good"],
                solver_used="test",
            )

        model.set_policy(test_policy)

        # Step 1: Decide
        scenario = DecisionScenario(
            question="Should I launch the product?",
            domain="business",
            stakes_level="high",
        )
        record = model.decide(scenario)
        assert record.twin_choice == "proceed"
        assert record.twin_confidence == 0.65

        # Step 2: Human diverges
        model.record_human_choice(record.decision_id, "decline", "Too risky right now")

        # Step 3: Outcome
        model.record_outcome(record.decision_id, positive=False, notes="Market crashed")

        # Verify state evolution
        assert model.state.step == 1
        assert len(model.state.history.divergences) == 1

    def test_faith_threshold_enforcement(self):
        """Twin must DECLINE when confidence < threshold, even if policy says proceed."""
        model, _ = self._make_model()

        def reckless_policy(state, scenario):
            return ArgumentationResult(chosen="proceed", confidence=0.2)

        model.set_policy(reckless_policy)
        record = model.decide(DecisionScenario(question="Risky bet?"))

        # The model should have overridden to decline
        assert record.twin_choice == "decline"
        assert record.below_faith_threshold is True

    def test_multi_step_sequential(self):
        """Multiple decisions build sequential history."""
        model, _ = self._make_model()

        def simple_policy(state, scenario):
            # Get slightly more confident as history grows
            base = 0.4 + (state.step * 0.1)
            return ArgumentationResult(
                chosen="proceed" if base >= 0.45 else "decline",
                confidence=min(base, 0.9),
            )

        model.set_policy(simple_policy)

        for i in range(5):
            record = model.decide(DecisionScenario(
                question=f"Decision {i+1}?",
                domain="test",
            ))
            model.record_human_choice(record.decision_id, "proceed")

        assert model.state.step == 5
        assert model.state.history.total_decisions == 5

    def test_analysis_export(self):
        model, tmpdir = self._make_model()
        model.decide(DecisionScenario(question="Test?"))

        analysis = model.get_analysis()
        assert "model_summary" in analysis
        assert "rates" in analysis
        assert "belief_state" in analysis
        assert analysis["model_summary"]["total_steps"] == 1

    def test_faith_signal_strength_accumulates(self):
        """After enough faith divergences, signal should strengthen."""
        model, _ = self._make_model()

        def low_confidence_policy(state, scenario):
            return ArgumentationResult(chosen="decline", confidence=0.3)

        model.set_policy(low_confidence_policy)

        # Create several faith divergences
        for i in range(6):
            record = model.decide(DecisionScenario(
                question=f"Faith test {i}?", domain="faith_test",
            ))
            model.record_human_choice(record.decision_id, "proceed")

        assert model.state.faith_signal_strength == "STRONG"


# ═══════════════════════════════════════════════════════════════
# RESOURCE STATE TESTS
# ═══════════════════════════════════════════════════════════════

class TestResourceState:

    def test_default_values(self):
        rs = ResourceState()
        assert rs.temporal_mode == "default"
        assert rs.time_pressure == 0.0
        assert rs.social_context == "alone"

    def test_serialization(self):
        rs = ResourceState(temporal_mode="reflective", time_pressure=0.8)
        d = rs.to_dict()
        assert d["temporal_mode"] == "reflective"
        assert d["time_pressure"] == 0.8
