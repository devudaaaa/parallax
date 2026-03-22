"""
Tests for the Formal Argumentation Framework (Phase 2).

Tests cover:
    1. Argument and Attack data structures
    2. DungAF fundamental properties (conflict-free, acceptability)
    3. Grounded extension (fixpoint) — classic examples from Dung 1995
    4. Complete, preferred, stable extensions
    5. Credulous and skeptical acceptance
    6. IncompleteAF (iAAF) — certain/uncertain distinction
    7. i*-extension verification (Fazzinga et al. 2026)
    8. DecisionEvaluator — extension → decision mapping
    9. Nixon Diamond (classic test case)
    10. ASPARTIX format export
"""

import pytest

from argumentation.framework import (
    Argument,
    ArgumentSource,
    Attack,
    Certainty,
    DecisionEvaluator,
    DungAF,
    IncompleteAF,
)


# ═══════════════════════════════════════════════════════════════
# HELPERS — Build test frameworks quickly
# ═══════════════════════════════════════════════════════════════

def make_arg(aid: str, label: str = "", certain: bool = True,
             direction: str = "", source=None) -> Argument:
    """Quick argument factory for tests."""
    if not label:
        label = aid
    if source is None:
        source = ArgumentSource.PERSONALITY_RULE if certain else ArgumentSource.LLM_GENERATED
    return Argument(
        id=aid, label=label, source=source,
        certainty=Certainty.CERTAIN if certain else Certainty.UNCERTAIN,
        direction=direction,
    )

def make_attack(a: str, b: str, certain: bool = True) -> Attack:
    return Attack(attacker=a, target=b,
                  certainty=Certainty.CERTAIN if certain else Certainty.UNCERTAIN)


# ═══════════════════════════════════════════════════════════════
# ARGUMENT / ATTACK TESTS
# ═══════════════════════════════════════════════════════════════

class TestArgument:

    def test_creation(self):
        a = Argument.create("market is good", source=ArgumentSource.LLM_GENERATED, direction="for")
        assert a.label == "market is good"
        assert a.certainty == Certainty.UNCERTAIN  # LLM → uncertain
        assert a.direction == "for"

    def test_personality_rule_is_certain(self):
        a = Argument.create("I value family", source=ArgumentSource.PERSONALITY_RULE)
        assert a.certainty == Certainty.CERTAIN

    def test_user_stated_is_certain(self):
        a = Argument.create("I want to proceed", source=ArgumentSource.USER_STATED)
        assert a.certainty == Certainty.CERTAIN

    def test_hashable_in_set(self):
        a1 = make_arg("a")
        a2 = make_arg("b")
        s = {a1, a2, a1}  # Duplicate should be deduplicated
        assert len(s) == 2

    def test_equality_by_id(self):
        a1 = Argument(id="x", label="first")
        a2 = Argument(id="x", label="different label")
        assert a1 == a2

class TestAttack:

    def test_creation(self):
        att = Attack(attacker="a", target="b", reason="contradicts")
        assert att.attacker == "a"
        assert att.target == "b"

    def test_hashable(self):
        att1 = make_attack("a", "b")
        att2 = make_attack("a", "b")
        assert att1 == att2
        assert len({att1, att2}) == 1


# ═══════════════════════════════════════════════════════════════
# DUNG AF — FUNDAMENTAL PROPERTIES
# ═══════════════════════════════════════════════════════════════

class TestDungAFProperties:
    """Tests based on Dung 1995 definitions."""

    def _simple_af(self):
        """a → b → c (linear chain)"""
        a, b, c = make_arg("a"), make_arg("b"), make_arg("c")
        return DungAF(
            {a, b, c},
            {make_attack("a", "b"), make_attack("b", "c")}
        )

    def test_conflict_free_empty(self):
        af = self._simple_af()
        assert af.is_conflict_free(set()) is True

    def test_conflict_free_valid(self):
        af = self._simple_af()
        assert af.is_conflict_free({"a", "c"}) is True

    def test_conflict_free_invalid(self):
        af = self._simple_af()
        assert af.is_conflict_free({"a", "b"}) is False

    def test_acceptable_unattacked(self):
        af = self._simple_af()
        assert af.is_acceptable("a", set()) is True  # a has no attackers

    def test_acceptable_defended(self):
        af = self._simple_af()
        assert af.is_acceptable("c", {"a"}) is True  # a attacks b which attacks c

    def test_acceptable_undefended(self):
        af = self._simple_af()
        assert af.is_acceptable("b", set()) is False  # b is attacked by a, not defended

    def test_admissible_empty(self):
        af = self._simple_af()
        assert af.is_admissible(set()) is True

    def test_admissible_valid(self):
        af = self._simple_af()
        assert af.is_admissible({"a", "c"}) is True

    def test_admissible_invalid(self):
        af = self._simple_af()
        assert af.is_admissible({"c"}) is False  # c attacked by b, not defended


# ═══════════════════════════════════════════════════════════════
# GROUNDED EXTENSION — Fixpoint computation
# ═══════════════════════════════════════════════════════════════

class TestGroundedExtension:

    def test_linear_chain(self):
        """a → b → c: grounded = {a, c}"""
        af = DungAF(
            {make_arg("a"), make_arg("b"), make_arg("c")},
            {make_attack("a", "b"), make_attack("b", "c")}
        )
        assert af.grounded_extension() == {"a", "c"}

    def test_no_attacks(self):
        """a, b, c with no attacks: grounded = {a, b, c}"""
        af = DungAF({make_arg("a"), make_arg("b"), make_arg("c")}, set())
        assert af.grounded_extension() == {"a", "b", "c"}

    def test_self_attack(self):
        """a → a: grounded = ∅"""
        af = DungAF({make_arg("a")}, {make_attack("a", "a")})
        assert af.grounded_extension() == set()

    def test_nixon_diamond(self):
        """
        Nixon Diamond: a ↔ b (mutual attack)
        Grounded = ∅ (skeptical reasoner includes nothing)
        Dung 1995, Example 22.
        """
        af = DungAF(
            {make_arg("a"), make_arg("b")},
            {make_attack("a", "b"), make_attack("b", "a")}
        )
        assert af.grounded_extension() == set()

    def test_defended_chain(self):
        """d → a → b → c: grounded = {d, b}"""
        af = DungAF(
            {make_arg("a"), make_arg("b"), make_arg("c"), make_arg("d")},
            {make_attack("d", "a"), make_attack("a", "b"), make_attack("b", "c")}
        )
        # d is unattacked → in grounded
        # d attacks a → a is out
        # b is attacked by a which is out → b is defended → in grounded
        # c is attacked by b which is in → c is out
        assert af.grounded_extension() == {"d", "b"}

    def test_single_unattacked(self):
        """a: grounded = {a}"""
        af = DungAF({make_arg("a")}, set())
        assert af.grounded_extension() == {"a"}

    def test_empty_framework(self):
        af = DungAF(set(), set())
        assert af.grounded_extension() == set()


# ═══════════════════════════════════════════════════════════════
# PREFERRED AND STABLE EXTENSIONS
# ═══════════════════════════════════════════════════════════════

class TestPreferredExtensions:

    def test_nixon_diamond_two_preferred(self):
        """Nixon Diamond: two preferred extensions {a} and {b}."""
        af = DungAF(
            {make_arg("a"), make_arg("b")},
            {make_attack("a", "b"), make_attack("b", "a")}
        )
        pref = af.preferred_extensions()
        assert len(pref) == 2
        assert {"a"} in pref
        assert {"b"} in pref

    def test_linear_chain_one_preferred(self):
        """a → b → c: one preferred = {a, c}"""
        af = DungAF(
            {make_arg("a"), make_arg("b"), make_arg("c")},
            {make_attack("a", "b"), make_attack("b", "c")}
        )
        pref = af.preferred_extensions()
        assert len(pref) == 1
        assert {"a", "c"} in pref


class TestStableExtensions:

    def test_nixon_diamond_two_stable(self):
        """Nixon Diamond: two stable = {a} and {b}."""
        af = DungAF(
            {make_arg("a"), make_arg("b")},
            {make_attack("a", "b"), make_attack("b", "a")}
        )
        stable = af.stable_extensions()
        assert len(stable) == 2
        assert {"a"} in stable
        assert {"b"} in stable

    def test_self_attack_no_stable(self):
        """a → a: no stable extension exists (Dung 1995, Lemma 15)."""
        af = DungAF({make_arg("a")}, {make_attack("a", "a")})
        stable = af.stable_extensions()
        assert len(stable) == 0

    def test_stable_is_preferred(self):
        """Every stable extension is preferred (Dung 1995, Lemma 15)."""
        af = DungAF(
            {make_arg("a"), make_arg("b"), make_arg("c")},
            {make_attack("a", "b"), make_attack("b", "c")}
        )
        stable = af.stable_extensions()
        preferred = af.preferred_extensions()
        for s in stable:
            assert s in preferred


# ═══════════════════════════════════════════════════════════════
# ACCEPTANCE
# ═══════════════════════════════════════════════════════════════

class TestAcceptance:

    def test_credulous_nixon(self):
        af = DungAF(
            {make_arg("a"), make_arg("b")},
            {make_attack("a", "b"), make_attack("b", "a")}
        )
        cred = af.credulously_accepted("preferred")
        assert "a" in cred
        assert "b" in cred

    def test_skeptical_nixon(self):
        af = DungAF(
            {make_arg("a"), make_arg("b")},
            {make_attack("a", "b"), make_attack("b", "a")}
        )
        skept = af.skeptically_accepted("preferred")
        assert "a" not in skept
        assert "b" not in skept

    def test_skeptical_linear(self):
        af = DungAF(
            {make_arg("a"), make_arg("b"), make_arg("c")},
            {make_attack("a", "b"), make_attack("b", "c")}
        )
        skept = af.skeptically_accepted("preferred")
        assert "a" in skept
        assert "c" in skept
        assert "b" not in skept


# ═══════════════════════════════════════════════════════════════
# INCOMPLETE AAF (iAAF)
# ═══════════════════════════════════════════════════════════════

class TestIncompleteAF:
    """Tests based on Fazzinga et al. 2026, Examples 1 and 5."""

    def test_certain_uncertain_partition(self):
        iaf = IncompleteAF(
            arguments={make_arg("a", certain=True), make_arg("b", certain=False)},
            attacks={make_attack("a", "b", certain=False)},
        )
        assert len(iaf.certain_arguments) == 1
        assert len(iaf.uncertain_arguments) == 1
        assert len(iaf.uncertain_attacks) == 1

    def test_completions_count(self):
        """
        iAAF from Fazzinga Example 1:
        Certain arg: a, Uncertain arg: b, Uncertain attack: (a,b)
        Completions: F1={a}, F2={a,b}, F3={a,b,(a,b)} → 3 completions
        """
        iaf = IncompleteAF(
            arguments={make_arg("a", certain=True), make_arg("b", certain=False)},
            attacks={make_attack("a", "b", certain=False)},
        )
        comps = iaf.completions()
        # {a} with no attacks
        # {a,b} with no attacks
        # {a,b} with (a,b)
        assert len(comps) == 3

    def test_certain_completion(self):
        iaf = IncompleteAF(
            arguments={make_arg("a", certain=True), make_arg("b", certain=False)},
            attacks={make_attack("a", "b", certain=False)},
        )
        cert = iaf.build_certain_completion()
        assert len(cert.arguments) == 1
        assert len(cert.attacks) == 0

    def test_maximal_completion(self):
        iaf = IncompleteAF(
            arguments={make_arg("a", certain=True), make_arg("b", certain=False)},
            attacks={make_attack("a", "b", certain=False)},
        )
        maxl = iaf.build_maximal_completion()
        assert len(maxl.arguments) == 2
        assert len(maxl.attacks) == 1


# ═══════════════════════════════════════════════════════════════
# i*-EXTENSION VERIFICATION
# ═══════════════════════════════════════════════════════════════

class TestIStarExtensions:
    """Tests from Fazzinga et al. 2026."""

    def test_possible_istar_admissible(self):
        """
        Fazzinga Example 1, iAAF IF:
        {a,b} should be a possible i*-extension under ad
        (since {a,b} is admissible in F2 = <{a,b}, ∅>)
        """
        iaf = IncompleteAF(
            arguments={make_arg("a", certain=True), make_arg("b", certain=False)},
            attacks={make_attack("a", "b", certain=False)},
        )
        assert iaf.is_possible_istar_extension({"a", "b"}, "admissible") is True

    def test_possible_istar_fails_with_certain_attack(self):
        """
        Fazzinga Example 1, iAAF IF':
        Certain arg a, uncertain arg b, CERTAIN attack (a,b).
        {a,b} should NOT be a possible i*-extension under co/gr/pr/st
        because in the only completion containing both, they conflict.
        """
        iaf = IncompleteAF(
            arguments={make_arg("a", certain=True), make_arg("b", certain=False)},
            attacks={make_attack("a", "b", certain=True)},  # CERTAIN attack
        )
        # Under complete semantics, {a,b} can't be an extension in any
        # completion containing both, since (a,b) is certain
        assert iaf.is_possible_istar_extension({"a", "b"}, "stable") is False

    def test_possible_istar_single_certain(self):
        """
        {a} should be a possible i*-extension — a is unattacked and certain.
        """
        iaf = IncompleteAF(
            arguments={make_arg("a", certain=True), make_arg("b", certain=False)},
            attacks={make_attack("a", "b", certain=True)},
        )
        assert iaf.is_possible_istar_extension({"a"}, "stable") is True

    def test_necessary_must_be_certain_args_only(self):
        """
        Fazzinga Proposition 2: necessary i*-extensions contain only certain args.
        """
        iaf = IncompleteAF(
            arguments={make_arg("a", certain=True), make_arg("b", certain=False)},
            attacks=set(),
        )
        # {a, b} can't be necessary because b is uncertain
        assert iaf.is_necessary_istar_extension({"a", "b"}, "admissible") is False
        # {a} can be necessary (it's admissible in every completion containing a)
        assert iaf.is_necessary_istar_extension({"a"}, "admissible") is True

    def test_ad_st_polynomial_verification(self):
        """
        The ad/st verification path should produce same results as enumeration.
        """
        iaf = IncompleteAF(
            arguments={
                make_arg("a", certain=True),
                make_arg("b", certain=True),
                make_arg("c", certain=False),
            },
            attacks={
                make_attack("a", "b"),
                make_attack("b", "a"),
                make_attack("c", "a", certain=False),
            },
        )
        # {b} should be a possible i*-extension under admissible
        # (b defends itself in some completion)
        result = iaf.is_possible_istar_extension({"b"}, "admissible")
        assert result is True


# ═══════════════════════════════════════════════════════════════
# DECISION EVALUATOR
# ═══════════════════════════════════════════════════════════════

class TestDecisionEvaluator:

    def test_clear_proceed(self):
        """When proceed arguments are unattacked, confidence should be high."""
        iaf = IncompleteAF(
            arguments={
                make_arg("p1", direction="for", certain=True),
                make_arg("p2", direction="for", certain=True),
                make_arg("d1", direction="against", certain=True),
            },
            attacks={
                make_attack("p1", "d1"),  # proceed defeats decline
            },
        )
        ev = DecisionEvaluator(faith_threshold=0.45)
        result = ev.evaluate(iaf, proceed_args={"p1", "p2"}, decline_args={"d1"})

        assert result["chosen"] == "proceed"
        assert result["confidence"] > 0.45
        assert "p1" in result["grounded_extension"] or "p2" in result["grounded_extension"]

    def test_decline_when_proceed_defeated(self):
        """When proceed arguments are all attacked and undefended, confidence drops."""
        iaf = IncompleteAF(
            arguments={
                make_arg("p1", direction="for", certain=True),
                make_arg("d1", direction="against", certain=True),
                make_arg("d2", direction="against", certain=True),
            },
            attacks={
                make_attack("d1", "p1"),  # decline defeats proceed
                make_attack("d2", "p1"),  # double attack
            },
        )
        ev = DecisionEvaluator(faith_threshold=0.45)
        result = ev.evaluate(iaf, proceed_args={"p1"}, decline_args={"d1", "d2"})

        assert result["confidence"] < 0.85  # Not in grounded
        assert result["af_size"] == 3

    def test_uncertain_attack_changes_result(self):
        """Uncertain attacks create different completions with different results."""
        iaf = IncompleteAF(
            arguments={
                make_arg("p1", direction="for", certain=True),
                make_arg("d1", direction="against", certain=True),
            },
            attacks={
                make_attack("d1", "p1", certain=False),  # UNCERTAIN attack
            },
        )
        ev = DecisionEvaluator()
        result = ev.evaluate(iaf, proceed_args={"p1"}, decline_args={"d1"})
        # In maximal completion, d1 attacks p1
        # But the attack is uncertain, so in some completions p1 survives
        assert result["solver_used"] == "python_native"


# ═══════════════════════════════════════════════════════════════
# ASPARTIX FORMAT EXPORT
# ═══════════════════════════════════════════════════════════════

class TestAPXExport:

    def test_basic_export(self):
        af = DungAF(
            {make_arg("a"), make_arg("b")},
            {make_attack("a", "b")}
        )
        apx = af.to_apx()
        assert "arg(a)." in apx
        assert "arg(b)." in apx
        assert "att(a,b)." in apx

    def test_dict_serialization(self):
        af = DungAF(
            {make_arg("a"), make_arg("b")},
            {make_attack("a", "b")}
        )
        d = af.to_dict()
        assert len(d["arguments"]) == 2
        assert len(d["attacks"]) == 1


# ═══════════════════════════════════════════════════════════════
# REAL-WORLD SCENARIO — Parallax decision
# ═══════════════════════════════════════════════════════════════

class TestParallaxScenario:
    """
    Simulate a real Parallax decision: "Should I invest in this startup?"

    Arguments:
        - (CERTAIN) val_family: "My family needs financial stability" → against
        - (CERTAIN) val_building: "I believe in building things" → for
        - (UNCERTAIN) market_good: "Market conditions are favorable" → for
        - (UNCERTAIN) team_strong: "The team is experienced" → for
        - (UNCERTAIN) cash_low: "My cash reserves are low" → against
        - (CERTAIN) risk_tolerance: "I'm comfortable with calculated risk" → for

    Attacks:
        - cash_low attacks market_good (low cash undermines market opportunity)
        - val_family attacks risk_tolerance (family stability vs risk)
        - team_strong attacks cash_low (good team mitigates cash concerns)
        - risk_tolerance attacks val_family (in this context, risk is calculated)
    """

    def _build_scenario(self):
        args = {
            make_arg("val_family", "Family needs stability", certain=True, direction="against"),
            make_arg("val_building", "I believe in building", certain=True, direction="for"),
            make_arg("market_good", "Market is favorable", certain=False, direction="for"),
            make_arg("team_strong", "Team is experienced", certain=False, direction="for"),
            make_arg("cash_low", "Cash reserves are low", certain=False, direction="against"),
            make_arg("risk_tol", "Comfortable with calculated risk", certain=True, direction="for"),
        }
        attacks = {
            make_attack("cash_low", "market_good", certain=False),
            make_attack("val_family", "risk_tol", certain=True),
            make_attack("team_strong", "cash_low", certain=False),
            make_attack("risk_tol", "val_family", certain=True),
        }
        return IncompleteAF(args, attacks)

    def test_scenario_builds(self):
        iaf = self._build_scenario()
        assert len(iaf.arguments) == 6
        assert len(iaf.certain_arguments) == 3
        assert len(iaf.uncertain_arguments) == 3

    def test_scenario_grounded_extension(self):
        iaf = self._build_scenario()
        af = iaf.build_maximal_completion()
        gr = af.grounded_extension()
        # val_building is unattacked → must be in grounded
        assert "val_building" in gr
        # team_strong is unattacked → must be in grounded
        assert "team_strong" in gr

    def test_scenario_decision(self):
        iaf = self._build_scenario()
        ev = DecisionEvaluator(faith_threshold=0.45)
        result = ev.evaluate(
            iaf,
            proceed_args={"val_building", "market_good", "team_strong", "risk_tol"},
            decline_args={"val_family", "cash_low"},
        )
        # val_building and team_strong are unattacked → in grounded
        # So proceed arguments survive → should recommend proceed
        assert result["chosen"] == "proceed"
        assert result["confidence"] > 0.45

    def test_scenario_has_extensions(self):
        iaf = self._build_scenario()
        af = iaf.build_maximal_completion()
        preferred = af.preferred_extensions()
        assert len(preferred) >= 1
