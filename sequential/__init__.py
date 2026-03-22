"""
Sequential Decision Analytics Layer — Powell's Universal Framework for Parallax.

This module provides the outer temporal loop for Parallax's decision engine.
Every decision becomes a step in a sequential process with five components:

    S_t        → State variables (personality + memory + beliefs + history)
    x_t        → Decision variables (output from argumentation layer)
    W_{t+1}    → Exogenous information (outcomes, human choices, events)
    S^M        → Transition function (how state evolves)
    F(π)       → Objective function (what the twin optimizes)

The four policy classes (PFA, CFA, VFA, DLA) map to:
    PFA → Personality rules generating arguments
    CFA → Preference orderings in ASPARTIX PAF/VAF
    VFA → Learning from past divergences
    DLA → The argumentation engine itself (lookahead over extensions)

Reference:
    Powell, W.B. (2022). Sequential Decision Analytics and Modeling.
    Foundations and Trends in Technology, Information and Operations Management.
"""

from sequential.state import (
    State,
    BeliefState,
    DecisionHistory,
    ResourceState,
)
from sequential.model import SequentialDecisionModel
from sequential.transition import TransitionFunction

__all__ = [
    "State",
    "BeliefState",
    "DecisionHistory",
    "ResourceState",
    "SequentialDecisionModel",
    "TransitionFunction",
]
