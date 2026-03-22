# Changelog

All notable changes to the Parallax Engine are documented here.

## [2.0.0] — 2026-03-20

### Added — Sequential Decision Model (Phase 1)
- `sequential/state.py` — Complete state variable system
  - `BeliefState` with Bayesian updates (Powell's VFA learning engine)
  - `DecisionHistory` with divergence analytics by domain and temporal mode
  - `ResourceState` for GTRBAC temporal engine integration
  - `State` class with JSON persistence (save/load)
- `sequential/transition.py` — Three-trigger transition function
  - `on_decision_made` — twin outputs recommendation
  - `on_human_responded` — divergence detection + faith signal classification
  - `on_outcome_observed` — faith vindication tracking + capability learning
- `sequential/model.py` — Sequential decision orchestrator
  - `SequentialDecisionModel` with SQLite persistence
  - `DecisionScenario` and `ArgumentationResult` interfaces
  - Faith threshold enforcement (twin cannot proceed below 0.45)
  - Full research export (`get_analysis()`, `export_for_research()`)
- `tests/test_sequential.py` — 31 tests covering beliefs, history, transitions, full loops

### Added — Formal Argumentation Engine (Phase 2)
- `argumentation/framework.py` — Dung's Abstract Argumentation Framework
  - `Argument` — Metadata-enriched (source, certainty, domain, direction, author)
  - `Attack` — With certainty label for iAAF support
  - `DungAF` — Standard AF with pure Python solvers:
    - Grounded extension (fixpoint of characteristic function F_AF)
    - Complete extensions (admissible + fixed point)
    - Preferred extensions (maximal admissible)
    - Stable extensions (conflict-free + attacks all outside)
    - Credulous and skeptical acceptance
    - ASPARTIX .apx format export
  - `IncompleteAF` — iAAF = ⟨A, A?, D, D?⟩ (Fazzinga et al. 2026)
    - Certain/uncertain argument and attack distinction
    - Completion enumeration
    - i*-extension verification (P under ad, st, co, gr semantics)
    - Canonical completion construction for polynomial verification
  - `DecisionEvaluator` — Maps extension membership to decisions
    - Grounded survival → high confidence
    - Some preferred survival → moderate confidence
    - No survival → below faith threshold → DECLINE
- `tests/test_argumentation.py` — 49 tests including Nixon Diamond, iAAF properties

### Changed
- `LICENSE` — Changed from MIT to Collective Intelligence License v1.0 (devudaaaa Research Lab)
- `README.md` — Updated for v2 architecture

### Architecture
- Three nested layers: Powell SDA → Dung AF → ASPARTIX/clingo solver
- Personality-derived arguments are CERTAIN, LLM-generated are UNCERTAIN
- Arguments carry metadata for explainability and future KAF integration
- 96 total tests passing, zero regressions on temporal engine

### References
- Dung, P.M. (1995). AI 77, 321-357.
- Powell, W.B. (2022). Sequential Decision Analytics. Princeton.
- Fazzinga et al. (2026). Revisiting iAAFs. AI 354.
- Alfano et al. (2025). Extending AAFs with Knowledge Bases. KR 2025.
- Joshi et al. (2005). GTRBAC. IEEE TKDE.

## [1.0.0] — 2025

### Original Release
- GTRBAC temporal engine (16 passing tests)
- LLM-delegated reasoning engine
- Data pipeline (ChromaDB + embeddings)
- Divergence tracker (SQLite)
- Personality engine
- Memory system (RAG)
- Platform API (FastAPI)
