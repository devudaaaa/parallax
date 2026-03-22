"""
Argumentation Layer — Dung's Abstract Argumentation Framework for Parallax.

PHASE 2 BUILD (this is the interface shell — implementation coming next).

This module will provide:
    - framework.py: Pure Python Dung AF (grounded extension via fixpoint)
    - aspartix_bridge.py: Shell to clingo for preferred/stable extensions
    - generator.py: LLM → structured arguments + attack relations
    - personality_rules.py: PFA rules → ASPARTIX pref()/val() facts

The argumentation layer takes (State, DecisionScenario) as input
and returns an ArgumentationResult with formally computed extensions.
It plugs into SequentialDecisionModel.set_policy().

Reference:
    Dung, P.M. (1995). On the Acceptability of Arguments and its
    Fundamental Role in Nonmonotonic Reasoning, Logic Programming
    and N-Person Games. Artificial Intelligence 77, 321-357.

    Egly, Gaggl, Woltran (2008). ASPARTIX: Implementing Argumentation
    Frameworks Using Answer-Set Programming. ICLP 2008.
"""

from argumentation.framework import (
    Argument,
    ArgumentSource,
    Attack,
    Certainty,
    DungAF,
    IncompleteAF,
    DecisionEvaluator,
)

__all__ = [
    "Argument",
    "ArgumentSource",
    "Attack",
    "Certainty",
    "DungAF",
    "IncompleteAF",
    "DecisionEvaluator",
]

# Phase 2 next steps:
# from argumentation.aspartix_bridge import ASPARTIXSolver
# from argumentation.generator import ArgumentGenerator
# from argumentation.personality_rules import PersonalityRuleEngine
