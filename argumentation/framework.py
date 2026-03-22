"""
Formal Argumentation Framework for Parallax.

Implements Dung's Abstract Argumentation Framework (1995) with extensions:
    - Incomplete AAFs (Fazzinga et al. 2026): certain/uncertain arguments and attacks
    - Metadata-enriched arguments (inspired by Alfano et al. 2025 KAF)
    - Pure Python solvers for grounded, admissible, complete, stable semantics
    - i*-extension verification (polynomial time under ad, st, co, gr)

The LLM generates arguments — this module evaluates them formally.

Architecture:
    Argument     → Data structure with metadata (source, certainty, domain, etc.)
    Attack       → Directed relation with certainty label
    DungAF       → Standard AF = ⟨AR, attacks⟩ with extension computation
    IncompleteAF → iAAF = ⟨A, A?, D, D?⟩ with i*-extension support

References:
    Dung (1995). On the Acceptability of Arguments. AI 77, 321-357.
    Fazzinga et al. (2026). Revisiting Extension/Acceptance over iAAFs. AI 354.
    Alfano et al. (2025). Extending AAFs with Knowledge Bases. KR 2025.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import FrozenSet, Optional


# ═══════════════════════════════════════════════════════════════
# ARGUMENT — Metadata-enriched abstract argument
# ═══════════════════════════════════════════════════════════════

class ArgumentSource(str, Enum):
    """Where an argument came from — determines certainty."""
    PERSONALITY_RULE = "personality_rule"   # From PFA rules → CERTAIN
    USER_STATED = "user_stated"            # User explicitly said this → CERTAIN
    LLM_GENERATED = "llm_generated"        # LLM inferred this → UNCERTAIN
    WORLD_FACT = "world_fact"              # External data → depends on source
    HISTORICAL = "historical"              # From past decisions → CERTAIN


class Certainty(str, Enum):
    """Whether an argument/attack is certain or uncertain (iAAF)."""
    CERTAIN = "certain"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, eq=True)
class Argument:
    """
    A metadata-enriched abstract argument.

    In Dung's original formulation, arguments are abstract entities.
    We preserve this — the acceptability computation depends ONLY on
    the attack relation, not on metadata. But metadata travels with
    the argument for:
        - Determining certainty (personality rules → certain, LLM → uncertain)
        - Tracing decisions back to their source (explainability)
        - KAF-style knowledge queries (future MANAS integration)
        - Research export (which argument types get overridden?)

    Frozen + hashable so arguments can be set members.
    """
    id: str                                    # Unique identifier
    label: str                                 # Human-readable short label
    description: str = ""                      # Full text of the argument
    source: ArgumentSource = ArgumentSource.LLM_GENERATED
    certainty: Certainty = Certainty.UNCERTAIN
    domain: str = ""                           # career / finance / relationship / etc.
    direction: str = ""                        # "for" or "against" (the decision)
    author: str = ""                           # Who generated this (person id, "llm", rule name)
    timestamp: str = ""                        # When generated
    strength: float = 0.5                      # Source-assigned strength (0-1), NOT used in formal computation
    raw_text: str = ""                         # Original text from LLM or user

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, 'timestamp', datetime.now().isoformat())

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Argument):
            return self.id == other.id
        return NotImplemented

    def __repr__(self):
        cert = "✓" if self.certainty == Certainty.CERTAIN else "?"
        return f"Arg({self.id}:{self.label}[{cert}])"

    @classmethod
    def create(cls, label: str, source: ArgumentSource = ArgumentSource.LLM_GENERATED,
               direction: str = "", **kwargs) -> Argument:
        """Factory with auto-generated ID."""
        raw = f"{label}:{time.time()}"
        arg_id = hashlib.sha256(raw.encode()).hexdigest()[:10]
        certainty = (Certainty.CERTAIN
                     if source in (ArgumentSource.PERSONALITY_RULE,
                                   ArgumentSource.USER_STATED,
                                   ArgumentSource.HISTORICAL)
                     else Certainty.UNCERTAIN)
        return cls(id=arg_id, label=label, source=source,
                   certainty=certainty, direction=direction, **kwargs)


@dataclass(frozen=True, eq=True)
class Attack:
    """
    A directed attack relation between two arguments.

    attack(a, b) means argument a attacks argument b.
    Certainty follows iAAF: certain attacks are always present,
    uncertain attacks may or may not be present in a given completion.
    """
    attacker: str    # Argument ID
    target: str      # Argument ID
    certainty: Certainty = Certainty.CERTAIN
    reason: str = ""  # Why this attack exists (for explainability)

    def __hash__(self):
        return hash((self.attacker, self.target))

    def __eq__(self, other):
        if isinstance(other, Attack):
            return self.attacker == other.attacker and self.target == other.target
        return NotImplemented

    def __repr__(self):
        cert = "—" if self.certainty == Certainty.CERTAIN else "~"
        return f"({self.attacker} {cert}> {self.target})"


# ═══════════════════════════════════════════════════════════════
# DUNG AF — Standard Abstract Argumentation Framework
# ═══════════════════════════════════════════════════════════════

class DungAF:
    """
    Standard Dung Abstract Argumentation Framework AF = ⟨AR, attacks⟩.

    Implements:
        - Conflict-free check
        - Acceptability (defense)
        - Characteristic function F_AF
        - Admissible extensions
        - Grounded extension (fixpoint of F_AF — unique, always exists)
        - Complete extensions
        - Preferred extensions (maximal admissible — at least one exists)
        - Stable extensions (may not exist)

    All computation is pure Python. No external solver needed
    except for preferred extensions on large frameworks (future ASPARTIX bridge).
    """

    def __init__(self, arguments: set[Argument] | None = None,
                 attacks: set[Attack] | None = None):
        self.arguments: set[Argument] = arguments or set()
        self.attacks: set[Attack] = attacks or set()

        # Index structures for fast lookup
        self._arg_by_id: dict[str, Argument] = {}
        self._attackers_of: dict[str, set[str]] = {}  # target → set of attacker IDs
        self._targets_of: dict[str, set[str]] = {}    # attacker → set of target IDs
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild lookup indices after modification."""
        self._arg_by_id = {a.id: a for a in self.arguments}
        self._attackers_of = {a.id: set() for a in self.arguments}
        self._targets_of = {a.id: set() for a in self.arguments}
        for att in self.attacks:
            if att.target in self._attackers_of:
                self._attackers_of[att.target].add(att.attacker)
            if att.attacker in self._targets_of:
                self._targets_of[att.attacker].add(att.target)

    @property
    def arg_ids(self) -> set[str]:
        return set(self._arg_by_id.keys())

    def get_arg(self, arg_id: str) -> Optional[Argument]:
        return self._arg_by_id.get(arg_id)

    def add_argument(self, arg: Argument) -> None:
        self.arguments.add(arg)
        self._arg_by_id[arg.id] = arg
        self._attackers_of.setdefault(arg.id, set())
        self._targets_of.setdefault(arg.id, set())

    def add_attack(self, attack: Attack) -> None:
        self.attacks.add(attack)
        self._attackers_of.setdefault(attack.target, set()).add(attack.attacker)
        self._targets_of.setdefault(attack.attacker, set()).add(attack.target)

    # ─── FUNDAMENTAL PROPERTIES ───────────────────────────────

    def attacks_set(self, s: set[str], a: str) -> bool:
        """Does set S attack argument a?"""
        return bool(self._attackers_of.get(a, set()) & s)

    def is_conflict_free(self, s: set[str]) -> bool:
        """A set S is conflict-free iff no argument in S attacks another in S."""
        for att in self.attacks:
            if att.attacker in s and att.target in s:
                return False
        return True

    def is_acceptable(self, a: str, s: set[str]) -> bool:
        """
        Argument a is acceptable w.r.t. S iff every attacker of a is attacked by S.
        (Dung 1995, Definition 6.1)
        """
        for attacker_id in self._attackers_of.get(a, set()):
            if not self.attacks_set(s, attacker_id):
                return False
        return True

    def characteristic_function(self, s: set[str]) -> set[str]:
        """
        F_AF(S) = {a ∈ AR | a is acceptable w.r.t. S}
        (Dung 1995, Definition 16)
        """
        return {a for a in self.arg_ids if self.is_acceptable(a, s)}

    def is_admissible(self, s: set[str]) -> bool:
        """S is admissible iff S is conflict-free and every arg in S is acceptable w.r.t. S."""
        if not self.is_conflict_free(s):
            return False
        return all(self.is_acceptable(a, s) for a in s)

    # ─── EXTENSION COMPUTATION ────────────────────────────────

    def grounded_extension(self) -> set[str]:
        """
        The grounded extension is the LEAST fixpoint of F_AF.
        (Dung 1995, Definition 20)

        Computed iteratively: start from ∅, repeatedly apply F_AF
        until stable. Always exists, always unique.
        This is the twin's most conservative (skeptical) assessment.
        """
        s = set()
        while True:
            new_s = self.characteristic_function(s)
            if new_s == s:
                return s
            s = new_s

    def complete_extensions(self) -> list[set[str]]:
        """
        S is a complete extension iff S is admissible and contains
        every argument acceptable w.r.t. S.
        (Dung 1995, Definition 23)

        Brute-force enumeration for small frameworks.
        For large frameworks, use ASPARTIX bridge.
        """
        from itertools import combinations
        results = []
        ids = list(self.arg_ids)
        for size in range(len(ids) + 1):
            for combo in combinations(ids, size):
                s = set(combo)
                if self.is_admissible(s) and self.characteristic_function(s) == s:
                    results.append(s)
        return results

    def preferred_extensions(self) -> list[set[str]]:
        """
        Preferred extensions are ⊆-maximal admissible sets.
        (Dung 1995, Definition 7)

        At least one always exists. Computed by filtering complete extensions.
        For large frameworks, use ASPARTIX bridge with clingo.
        """
        complete = self.complete_extensions()
        if not complete:
            return [set()]

        preferred = []
        for ext in complete:
            is_maximal = True
            for other in complete:
                if ext != other and ext.issubset(other):
                    is_maximal = False
                    break
            if is_maximal:
                preferred.append(ext)
        return preferred if preferred else [set()]

    def stable_extensions(self) -> list[set[str]]:
        """
        S is a stable extension iff S is conflict-free and
        S attacks every argument not in S.
        (Dung 1995, Definition 13)

        May not exist. Every stable extension is preferred (but not vice versa).
        """
        from itertools import combinations
        results = []
        ids = list(self.arg_ids)
        for size in range(len(ids) + 1):
            for combo in combinations(ids, size):
                s = set(combo)
                if not self.is_conflict_free(s):
                    continue
                outside = self.arg_ids - s
                if all(self.attacks_set(s, a) for a in outside):
                    results.append(s)
        return results

    # ─── ACCEPTANCE ───────────────────────────────────────────

    def credulously_accepted(self, semantics: str = "preferred") -> set[str]:
        """Arguments belonging to AT LEAST ONE extension."""
        extensions = self._get_extensions(semantics)
        if not extensions:
            return set()
        return set().union(*extensions)

    def skeptically_accepted(self, semantics: str = "preferred") -> set[str]:
        """Arguments belonging to EVERY extension."""
        extensions = self._get_extensions(semantics)
        if not extensions:
            return self.arg_ids  # Vacuously true
        result = set(extensions[0])
        for ext in extensions[1:]:
            result &= ext
        return result

    def _get_extensions(self, semantics: str) -> list[set[str]]:
        dispatch = {
            "grounded": lambda: [self.grounded_extension()],
            "complete": self.complete_extensions,
            "preferred": self.preferred_extensions,
            "stable": self.stable_extensions,
            "admissible": self._admissible_extensions,
        }
        fn = dispatch.get(semantics)
        if fn is None:
            raise ValueError(f"Unknown semantics: {semantics}")
        return fn()

    def _admissible_extensions(self) -> list[set[str]]:
        """All admissible sets (including ∅)."""
        from itertools import combinations
        results = []
        ids = list(self.arg_ids)
        for size in range(len(ids) + 1):
            for combo in combinations(ids, size):
                s = set(combo)
                if self.is_admissible(s):
                    results.append(s)
        return results

    # ─── SERIALIZATION ────────────────────────────────────────

    def to_apx(self) -> str:
        """Export to ASPARTIX .apx format."""
        lines = []
        for a in sorted(self.arg_ids):
            lines.append(f"arg({a}).")
        for att in sorted(self.attacks, key=lambda x: (x.attacker, x.target)):
            lines.append(f"att({att.attacker},{att.target}).")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "arguments": [
                {"id": a.id, "label": a.label, "source": a.source.value,
                 "certainty": a.certainty.value, "direction": a.direction,
                 "domain": a.domain, "strength": a.strength}
                for a in self.arguments
            ],
            "attacks": [
                {"attacker": att.attacker, "target": att.target,
                 "certainty": att.certainty.value, "reason": att.reason}
                for att in self.attacks
            ],
        }

    def __repr__(self):
        return f"DungAF(args={len(self.arguments)}, attacks={len(self.attacks)})"


# ═══════════════════════════════════════════════════════════════
# INCOMPLETE AAF — iAAF = ⟨A, A?, D, D?⟩
# ═══════════════════════════════════════════════════════════════

class IncompleteAF:
    """
    Incomplete Abstract Argumentation Framework.
    (Fazzinga, Flesca, Furfaro 2026)

    Extends DungAF with certain/uncertain distinction:
        A  = certain arguments (always present)
        A? = uncertain arguments (may or may not be present)
        D  = certain attacks (present whenever both incident args present)
        D? = uncertain attacks (may or may not be present)

    An iAAF compactly encodes multiple possible scenarios (completions).
    Each completion is a standard DungAF.

    For Parallax:
        - Personality-derived arguments → CERTAIN
        - LLM-generated arguments → UNCERTAIN
        - Personality-derived attacks → CERTAIN
        - LLM-inferred attacks → UNCERTAIN

    Key result from Fazzinga et al.:
        Verifying i*-extensions under ad, st, co, gr is P (not NP-complete).
        This means we can handle uncertainty without computational penalty.
    """

    def __init__(self, arguments: set[Argument] | None = None,
                 attacks: set[Attack] | None = None):
        self.arguments = arguments or set()
        self.attacks = attacks or set()

    @property
    def certain_arguments(self) -> set[Argument]:
        return {a for a in self.arguments if a.certainty == Certainty.CERTAIN}

    @property
    def uncertain_arguments(self) -> set[Argument]:
        return {a for a in self.arguments if a.certainty == Certainty.UNCERTAIN}

    @property
    def certain_attacks(self) -> set[Attack]:
        return {att for att in self.attacks if att.certainty == Certainty.CERTAIN}

    @property
    def uncertain_attacks(self) -> set[Attack]:
        return {att for att in self.attacks if att.certainty == Certainty.UNCERTAIN}

    @property
    def certain_arg_ids(self) -> set[str]:
        return {a.id for a in self.certain_arguments}

    @property
    def uncertain_arg_ids(self) -> set[str]:
        return {a.id for a in self.uncertain_arguments}

    @property
    def all_arg_ids(self) -> set[str]:
        return {a.id for a in self.arguments}

    def _arg_by_id(self) -> dict[str, Argument]:
        return {a.id: a for a in self.arguments}

    def completions(self) -> list[DungAF]:
        """
        Enumerate all completions of this iAAF.

        A completion contains all certain args/attacks plus a subset
        of uncertain args/attacks. Each completion is a standard DungAF.

        WARNING: Exponential in |A?| + |D?|. Only for small frameworks.
        For large frameworks, use i*-extension verification directly.
        """
        from itertools import combinations
        unc_args = list(self.uncertain_arguments)
        unc_atts = list(self.uncertain_attacks)

        completions = []
        for n_args in range(len(unc_args) + 1):
            for arg_combo in combinations(unc_args, n_args):
                chosen_args = set(self.certain_arguments) | set(arg_combo)
                chosen_arg_ids = {a.id for a in chosen_args}

                # Certain attacks between chosen arguments
                base_attacks = {att for att in self.certain_attacks
                                if att.attacker in chosen_arg_ids
                                and att.target in chosen_arg_ids}

                # Subsets of uncertain attacks between chosen arguments
                available_unc_atts = [att for att in unc_atts
                                      if att.attacker in chosen_arg_ids
                                      and att.target in chosen_arg_ids]

                for n_atts in range(len(available_unc_atts) + 1):
                    for att_combo in combinations(available_unc_atts, n_atts):
                        comp_attacks = base_attacks | set(att_combo)
                        completions.append(DungAF(set(chosen_args), comp_attacks))

        return completions

    # ─── i*-EXTENSION VERIFICATION ────────────────────────────
    # Fazzinga et al. 2026, Definitions 5-6
    #
    # i*-extension: S is a possible (resp. necessary) i*-extension
    # iff S is an extension of SOME (resp. EVERY) completion F.
    #
    # Key difference from i-extension: the completion F must
    # contain ALL arguments of S (not just S ∩ A').

    def is_possible_istar_extension(
        self,
        s: set[str],
        semantics: str = "admissible",
    ) -> bool:
        """
        Check if S is a possible i*-extension.
        (Fazzinga et al. 2026, Definition 5 — possible perspective)

        For ad, st: Construct the canonical completion and verify.
        This is P, not NP-complete (Theorem 1).

        For co, gr: More complex algorithms (Theorems 2, 3) but still P.
        For pr: Σ₂ᵖ-complete — use ASPARTIX for large frameworks.
        """
        # Check that all arguments in S exist in the iAAF
        if not s.issubset(self.all_arg_ids):
            return False

        if semantics in ("admissible", "stable"):
            return self._istar_verify_ad_st(s, semantics)
        elif semantics == "complete":
            return self._istar_verify_co(s)
        elif semantics == "grounded":
            return self._istar_verify_gr(s)
        elif semantics == "preferred":
            # For small frameworks, enumerate completions
            return self._istar_verify_by_enumeration(s, semantics)
        else:
            raise ValueError(f"Unknown semantics: {semantics}")

    def is_necessary_istar_extension(
        self,
        s: set[str],
        semantics: str = "admissible",
    ) -> bool:
        """
        Check if S is a necessary i*-extension.
        (Fazzinga et al. 2026, Definition 5 — necessary perspective)

        S must be an extension in EVERY completion.
        Necessary i*-extensions contain only certain arguments (Proposition 2).
        P under ad, st, co, gr. coNP-complete under pr.
        """
        # Necessary i*-extensions can only contain certain arguments
        if not s.issubset(self.certain_arg_ids):
            return False

        return self._istar_verify_by_enumeration(s, semantics, necessary=True)

    def _istar_verify_ad_st(self, s: set[str], semantics: str) -> bool:
        """
        Polynomial verification for admissible/stable i*-extensions.
        (Fazzinga et al. 2026, Theorem 1)

        Construct the canonical completion F:
            - Args: all certain args + args of S (even if uncertain)
            - Attacks: certain attacks between these args
                     + uncertain attacks FROM S to args outside S
        Then check if S is an extension of F.
        """
        arg_map = self._arg_by_id()

        # Build canonical completion arguments
        comp_args = set()
        for a in self.arguments:
            if a.certainty == Certainty.CERTAIN or a.id in s:
                comp_args.add(a)
        comp_arg_ids = {a.id for a in comp_args}

        # Build canonical completion attacks
        comp_attacks = set()
        for att in self.attacks:
            if att.attacker not in comp_arg_ids or att.target not in comp_arg_ids:
                continue
            if att.certainty == Certainty.CERTAIN:
                comp_attacks.add(att)
            elif att.certainty == Certainty.UNCERTAIN:
                # Include uncertain attacks FROM S to outside S
                if att.attacker in s and att.target not in s:
                    comp_attacks.add(att)

        # Also remove uncertain args that certainly attack S and aren't attacked by S
        # (Fazzinga et al. line 1 of Theorem 1 proof)
        to_remove = set()
        for a in comp_args:
            if a.id in s or a.certainty == Certainty.CERTAIN:
                continue
            has_certain_attack_to_s = any(
                att.attacker == a.id and att.target in s and att.certainty == Certainty.CERTAIN
                for att in self.attacks
            )
            attacked_by_s = any(
                att.attacker in s and att.target == a.id
                for att in comp_attacks
            )
            if has_certain_attack_to_s and not attacked_by_s:
                to_remove.add(a)

        comp_args -= to_remove
        comp_arg_ids = {a.id for a in comp_args}
        comp_attacks = {att for att in comp_attacks
                        if att.attacker in comp_arg_ids and att.target in comp_arg_ids}

        # Build DungAF and verify
        completion = DungAF(comp_args, comp_attacks)

        if semantics == "admissible":
            return completion.is_admissible(s)
        elif semantics == "stable":
            if not completion.is_conflict_free(s):
                return False
            outside = comp_arg_ids - s
            return all(completion.attacks_set(s, a) for a in outside)
        return False

    def _istar_verify_co(self, s: set[str]) -> bool:
        """
        Polynomial verification for complete i*-extensions.
        (Fazzinga et al. 2026, Theorem 2 — Algorithm 1)

        Constructs a completion and iteratively removes attacks/args
        to make arguments outside S non-acceptable w.r.t. S.
        """
        # Simplified: construct canonical completion and verify
        # Full Algorithm 1 implementation with snail detection
        # For now, delegate to enumeration for small frameworks
        # TODO: Implement full Algorithm 1 for O(n³) performance
        return self._istar_verify_by_enumeration(s, "complete")

    def _istar_verify_gr(self, s: set[str]) -> bool:
        """
        Polynomial verification for grounded i*-extensions.
        (Fazzinga et al. 2026, Theorem 3 — Algorithm 2)

        Incrementally builds a completion where S is the grounded extension.
        """
        # Simplified: construct completion and check grounded
        # TODO: Implement full Algorithm 2 for O(n³) performance
        return self._istar_verify_by_enumeration(s, "grounded")

    def _istar_verify_by_enumeration(
        self, s: set[str], semantics: str, necessary: bool = False,
    ) -> bool:
        """
        Verify by enumerating completions (exponential, for small frameworks).
        For possible: S is extension in SOME completion.
        For necessary: S is extension in EVERY completion.
        """
        for comp in self.completions():
            comp_arg_ids = comp.arg_ids
            # For i*-extension, S must be subset of completion's arguments
            if not s.issubset(comp_arg_ids):
                if necessary:
                    # S contains args not in this completion → can't be extension here
                    # For necessary, this is only OK if args are uncertain
                    # (they simply don't appear in this completion)
                    # But necessary i*-ext requires S is extension in EVERY completion
                    # If S has uncertain args, some completions won't contain them → fail
                    return False
                continue

            extensions = comp._get_extensions(semantics)
            is_ext = s in [set(e) for e in extensions]

            if necessary and not is_ext:
                return False
            if not necessary and is_ext:
                return True

        return necessary  # If we got here: necessary=True means all passed

    # ─── CONVENIENCE: BUILD COMPLETION FOR DECISION ───────────

    def build_maximal_completion(self) -> DungAF:
        """
        Build the completion with ALL arguments and attacks present.
        Useful as a starting point for analysis.
        """
        return DungAF(set(self.arguments), set(self.attacks))

    def build_certain_completion(self) -> DungAF:
        """
        Build the completion with ONLY certain arguments and attacks.
        The most conservative view.
        """
        cert_args = self.certain_arguments
        cert_arg_ids = {a.id for a in cert_args}
        cert_attacks = {att for att in self.certain_attacks
                        if att.attacker in cert_arg_ids and att.target in cert_arg_ids}
        return DungAF(cert_args, cert_attacks)

    # ─── SERIALIZATION ────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "certain_arguments": [a.id for a in self.certain_arguments],
            "uncertain_arguments": [a.id for a in self.uncertain_arguments],
            "certain_attacks": [(att.attacker, att.target) for att in self.certain_attacks],
            "uncertain_attacks": [(att.attacker, att.target) for att in self.uncertain_attacks],
            "all_arguments": [
                {"id": a.id, "label": a.label, "source": a.source.value,
                 "certainty": a.certainty.value, "direction": a.direction}
                for a in self.arguments
            ],
        }

    def __repr__(self):
        return (f"IncompleteAF(certain_args={len(self.certain_arguments)}, "
                f"uncertain_args={len(self.uncertain_arguments)}, "
                f"certain_atts={len(self.certain_attacks)}, "
                f"uncertain_atts={len(self.uncertain_attacks)})")


# ═══════════════════════════════════════════════════════════════
# DECISION EVALUATOR — Maps extensions to decisions
# ═══════════════════════════════════════════════════════════════

class DecisionEvaluator:
    """
    Maps argumentation results to a decision with confidence.

    Given an iAAF for a decision scenario, computes extensions
    and determines:
        - Whether "proceed" arguments survive in extensions
        - Confidence level based on which semantics accept them
        - The formal reasoning trail

    This is the bridge between the argumentation framework
    and the sequential decision model's ArgumentationResult.
    """

    def __init__(self, faith_threshold: float = 0.45):
        self.faith_threshold = faith_threshold

    def evaluate(self, iaf: IncompleteAF, proceed_args: set[str],
                 decline_args: set[str]) -> dict:
        """
        Evaluate a decision using the iAAF.

        Args:
            iaf: The incomplete argumentation framework
            proceed_args: Argument IDs that support proceeding
            decline_args: Argument IDs that support declining

        Returns:
            Decision dict with chosen, confidence, reasoning, extensions
        """
        # Use maximal completion for primary analysis
        af = iaf.build_maximal_completion()

        # Compute extensions under multiple semantics
        grounded = af.grounded_extension()
        complete = af.complete_extensions()
        preferred = af.preferred_extensions()
        stable = af.stable_extensions()

        # Analyze which "proceed" arguments survive
        proceed_in_grounded = proceed_args & grounded
        proceed_in_all_preferred = proceed_args.copy()
        for ext in preferred:
            proceed_in_all_preferred &= ext
        proceed_in_some_preferred = set()
        for ext in preferred:
            proceed_in_some_preferred |= (proceed_args & ext)

        # Compute confidence based on extension membership
        # Grounded (skeptical) → high confidence
        # All preferred → good confidence
        # Some preferred → moderate confidence
        # None → low confidence
        if proceed_in_grounded:
            confidence = 0.85 + 0.15 * (len(proceed_in_grounded) / max(len(proceed_args), 1))
        elif proceed_in_all_preferred:
            confidence = 0.65 + 0.20 * (len(proceed_in_all_preferred) / max(len(proceed_args), 1))
        elif proceed_in_some_preferred:
            confidence = 0.35 + 0.30 * (len(proceed_in_some_preferred) / max(len(proceed_args), 1))
        else:
            confidence = 0.15

        # Determine decision
        if confidence >= self.faith_threshold:
            chosen = "proceed"
        else:
            chosen = "decline"

        # Build reasoning trace
        reasoning_parts = []
        if proceed_in_grounded:
            reasoning_parts.append(
                f"Proceed arguments {proceed_in_grounded} survive in grounded extension (skeptical)."
            )
        if proceed_in_some_preferred and not proceed_in_grounded:
            reasoning_parts.append(
                f"Proceed arguments {proceed_in_some_preferred} survive in some preferred extensions (credulous)."
            )
        decline_in_grounded = decline_args & grounded
        if decline_in_grounded:
            reasoning_parts.append(
                f"Decline arguments {decline_in_grounded} also survive in grounded extension."
            )

        return {
            "chosen": chosen,
            "confidence": round(confidence, 4),
            "reasoning": " ".join(reasoning_parts) if reasoning_parts else "No proceed arguments survive formal evaluation.",
            "grounded_extension": list(grounded),
            "preferred_extensions": [list(e) for e in preferred],
            "stable_extensions": [list(e) for e in stable],
            "proceed_in_grounded": list(proceed_in_grounded),
            "proceed_in_some_preferred": list(proceed_in_some_preferred),
            "proceed_in_all_preferred": list(proceed_in_all_preferred),
            "af_size": len(af.arguments),
            "solver_used": "python_native",
        }
