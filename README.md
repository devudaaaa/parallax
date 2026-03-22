<div align="center">

# PARALLAX

### A Generative Agent of One

*Measuring what computation cannot replicate about human decision-making*

![Status](https://img.shields.io/badge/version-2.0--alpha-58B09C?style=flat-square)
![License](https://img.shields.io/badge/license-CIL%20v1.0-D4A843?style=flat-square)
![Tests](https://img.shields.io/badge/tests-96%20passing-58B09C?style=flat-square)
![Privacy](https://img.shields.io/badge/privacy-CLAW%20enforced-F4845F?style=flat-square)

**[Register to Use](https://devudaaaa.xyz/parallax/register.html) · [devudaaaa Research Lab](https://devudaaaa.xyz) · [CHANGELOG](CHANGELOG.md)**

---

*When algorithms can predict your next purchase, your next click, your next relationship —*
*what's left that's irreducibly yours?*

</div>

---

## The Question That Started This

Imagine you're facing a decision. You've analyzed the data. The spreadsheet says no. The probability is below 45%. Every rational framework points to decline.

But you do it anyway. And sometimes, it works.

That gap — where logic says *no* but conviction says *yes* — is what Parallax studies. Not by trying to model faith or intuition (we can't). But by building a computational version of you that follows pure logic, and then measuring every moment where the real you disagrees.

**The divergence IS the data.**

We call it the faith variable. You might call it gut feeling, intuition, or conviction. The Telugu word for it is **దేవుడా** (*devudaaaa!*) — the cry to god when stakes are high and logic has run out.

Parallax doesn't try to explain it. Parallax measures its shape.

---

## Explain It Like I'm In High School

You have a twin. Not a physical twin — a computer program that thinks exactly like you. It reads your messages, learns your style, knows your values, understands how you make decisions. It's scarily accurate.

Now, you and your twin both face the same question: *"Should I take this risk?"*

Most of the time, you agree. That's expected.

But sometimes, your twin says *"The math doesn't work, I'd say no"* — and you say *"I'm doing it anyway."* And sometimes you're right.

Those moments are what Parallax collects. Not your personal decisions (those stay private). The **patterns**. How often does it happen? In what kinds of situations? At what time of day? When you're alone vs. with people?

**"But wait — how do you keep my stuff private?"**

Parallax integrates the PII detection and redaction pipeline from [Claw](https://github.com/Leeladitya/claw), our AI governance engine. Before any insight leaves your machine — before it enters the collective — Claw's scanner strips emails, phone numbers, names, SSNs, financial details, and anything else that could identify you. What remains is the pattern, not the person. Your twin knows you. The community knows patterns. Nobody knows both.

Over time, across many people, those patterns map something real: **the boundary between what computers can predict and what they can't.**

---

## Explain It Like I'm a Researcher

Parallax is a single-subject generative agent research instrument implementing three formally grounded layers:

### Layer 1: Sequential Decision Analytics (Powell 2022)

Every decision is a step in a sequential process with five components:

| Component | Parallax Implementation |
|-----------|------------------------|
| **State S_t** | Personality profile + Bayesian belief state + decision history + GTRBAC temporal mode |
| **Decision x_t** | Output from the formal argumentation layer |
| **Exogenous info W_{t+1}** | Human's actual choice + decision outcome + environmental changes |
| **Transition S^M** | Belief update (divergence-weighted), history append, VFA learning |
| **Objective F(π)** | Rational expected value (twin) vs. unknown objective (human) — the gap is the signal |

Powell's four policy classes map to:
- **PFA** → Personality rules generating CERTAIN arguments
- **CFA** → Preference orderings in ASPARTIX PAF/VAF format
- **VFA** → Learning from past divergence patterns
- **DLA** → The argumentation engine itself (lookahead over extensions)

### Layer 2: Abstract Argumentation (Dung 1995 + Fazzinga et al. 2026)

Each decision scenario becomes an Incomplete Abstract Argumentation Framework:

```
iAAF = ⟨A, A?, D, D?⟩

A   = Certain arguments (from personality rules, user statements)
A?  = Uncertain arguments (from LLM inference, world observations)
D   = Certain attacks (known contradictions)
D?  = Uncertain attacks (inferred contradictions)
```

The engine computes grounded (fixpoint of F_AF), preferred (maximal admissible), and stable extensions with i\*-extension verification — polynomial under ad, st, co, gr semantics (Fazzinga et al. Theorem 1).

**Critical design choice:** the LLM generates arguments. It does NOT evaluate them. Evaluation is formally computed. The confidence score is extension membership status, not an LLM's guess.

### Layer 3: Temporal Access Control (GTRBAC)

The twin's behavioral mode shifts on a clock — professional at 9am, casual at 6pm, reflective at 10pm. The GTRBAC engine (Joshi et al. 2005) implements the full Disabled → Enabled → Active lifecycle. A divergence at 3am means something different than a divergence at 2pm. The temporal engine captures this.

### Privacy Layer: Claw Integration

Parallax imports the PII detection and automatic redaction module from the [Claw governance engine](https://github.com/Leeladitya/claw). This operates at every data boundary — between the user and the twin, between storage and research export. All personally identifiable information is stripped before divergence patterns are recorded. The collective intelligence pipeline is architecturally incapable of containing personal data because it was destroyed before the pattern was ever stored.

Claw itself is a full 6-stage AI governance pipeline (PII scanning → policy gate → knowledge hub → argumentation-based conflict resolution → context assembly → model inference). In Parallax, we use its PII and redaction capabilities specifically to guarantee anonymity in shared research data.

---

## What Can You Build With This?

Parallax is a research instrument, but the components are modular. Here's what's possible — and we'd love to see what the community invents.

### Smart Home Preference Engines

Every household has preference conflicts. Temperature, lighting, music, energy usage — people disagree. Current smart home systems average preferences into mediocrity. Parallax's argumentation framework can model each person's preferences as arguments, conflicts as attacks, and compute the extension that formally resolves the dispute. When someone overrides, that's a data point the system learns from. **Build a Home Assistant plugin. Build a Google Home middleware. Build the smart home that actually understands your household.**

### Clinical Decision Support

Treatment choices involve value conflicts — effectiveness vs. quality of life, risk tolerance vs. caution, patient preference vs. clinical evidence. These aren't just data problems; they're argumentation problems. Model clinical evidence as arguments, patient values as preference orderings, and compute which treatment options survive under the patient's own value system. **Build a tool that structures shared decision-making, not one that replaces the doctor.**

### Investor Behavior Modeling

When a human holds a stock against every quantitative signal, that's a faith-variable decision. Parallax can model investment reasoning as an AF, compute the rational recommendation, and track overrides. Over time, the patterns reveal something no risk questionnaire captures: *when* and *why* people trust conviction over computation. **Build a behavioral analytics layer for any trading platform. Build the anti-robo-advisor.**

### Learning Path Personalization

A student picks art history over computer science despite every career optimizer saying otherwise. That divergence isn't irrational — it's where intrinsic motivation lives. Track how student decisions diverge from recommended paths. The pattern reveals genuine interest, not compliance. **Build an LMS plugin that detects real engagement by measuring where students override algorithmic recommendations.**

### Autonomous System Handoff Analysis

When a human takes manual control from an autonomous system — car, drone, factory robot — that override contains information. Across thousands of handoffs, the pattern reveals what humans perceive that sensors don't. **Build a handoff analytics pipeline for any autonomous system. The argumentation framework models the conflict between sensor logic and human intuition.**

### Legal Argumentation Support

Legal disputes are argumentation frameworks by nature. Model each party's arguments, identify attack relations, compute extensions under different semantics. The grounded extension shows what survives skeptical analysis. The preferred extensions show defensible alternatives. **Build a case analysis tool. Build a plea negotiation simulator. Build a regulatory compliance checker.**

### Negotiation Engines

Any multi-party negotiation has conflicting arguments. Labor disputes, contract terms, international agreements. The argumentation framework provides formal structure. The divergence tracker shows where parties override formal recommendations — revealing their true priorities, not their stated ones. **Build a negotiation support system for any domain where parties disagree.**

### Personal Journaling / Self-Reflection Tools

Give someone a private twin that models their stated values and tracks when their actual decisions diverge. No sharing, no collective — just personal insight. "You say you prioritize health, but you override health-related recommendations 80% of the time after 9pm." **Build a self-awareness tool. Build the mirror that reflects patterns, not faces.**

The point: **Parallax gives you the formal machinery. What you build with it is yours.** We just ask that you share the anonymized patterns back, so the collective understanding grows.

---

## Why Collective Intelligence?

One person's divergence data is anecdotal. A thousand people's divergence data is a research breakthrough.

If you run Parallax on your investment decisions and discover that you override the system 70% of the time when your family is involved — that's interesting for you. But if 500 people show the same pattern, we've measured something real about how kinship bonds override financial optimization. That's publishable. That's actionable. That's knowledge that didn't exist before.

**The Collective Intelligence License is not a restriction. It's the mechanism that makes this possible.**

You use the engine. You discover patterns. You share those patterns (anonymized — Claw-enforced, not just promised). The collective dataset grows. New researchers build on it. The understanding deepens. You benefit from everyone else's contributions too.

This isn't altruism. It's the same logic as open science: science works because results are shared. Parallax works because patterns are shared.

### What you share:
- Divergence patterns (how often, in what domains, under what conditions)
- Novel argument structures or attack patterns you discover
- Performance improvements to the engine
- Research findings in published work (with attribution)

### What you never share (Claw enforces this):
- Personal decisions or private data
- Identifying information about yourself or others
- Raw data that could be de-anonymized

### What you get back:
- Access to the collective insight database
- Patterns from hundreds of other users' domains
- The most comprehensive dataset of human conviction-based behavior ever assembled

---

## Getting Started

### Prerequisites
- Python 3.10+
- `pip install pytest loguru pyyaml`

### Run the Tests

```bash
git clone https://github.com/devudaaaa/parallax.git
cd parallax
python -m pytest tests/test_temporal.py tests/test_sequential.py tests/test_argumentation.py -v
# → 96 passed
```

### Your First Decision

```python
from argumentation.framework import *

# Build an argumentation framework for a decision
proceed = Argument.create("Market timing is good", source=ArgumentSource.LLM_GENERATED, direction="for")
family  = Argument.create("Family needs stability", source=ArgumentSource.PERSONALITY_RULE, direction="against")
belief  = Argument.create("I believe in the team",  source=ArgumentSource.USER_STATED, direction="for")

af = DungAF(
    arguments={proceed, family, belief},
    attacks={Attack(attacker=family.id, target=proceed.id, reason="Stability concern undermines risk-taking")}
)

# Compute: what survives formal evaluation?
grounded = af.grounded_extension()
# → family and belief survive (proceed is attacked, belief is unattacked)
```

---

## The Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PARALLAX ENGINE v2                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │         POWELL SEQUENTIAL DECISION LAYER             │   │
│   │   State → Policy → Decision → Outcome → Transition  │   │
│   │                                                     │   │
│   │   ┌─────────────────────────────────────────────┐   │   │
│   │   │      DUNG ARGUMENTATION LAYER                │   │   │
│   │   │   Arguments → Attacks → Extensions → Choice  │   │   │
│   │   │                                             │   │   │
│   │   │   ┌─────────────────────────────────────┐   │   │   │
│   │   │   │    GTRBAC TEMPORAL ENGINE            │   │   │   │
│   │   │   │  Time-aware behavioral modes        │   │   │   │
│   │   │   └─────────────────────────────────────┘   │   │   │
│   │   └─────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ╔═════════════════════════════════════════════════════╗   │
│   ║          CLAW PII REDACTION (imported)              ║   │
│   ║   Strips all identifiable data before storage       ║   │
│   ║   and before any insight enters the collective      ║   │
│   ╚═════════════════════════════════════════════════════╝   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Academic References

| Paper | Year | Role in Parallax |
|-------|------|-----------------|
| Dung, *On the Acceptability of Arguments*. AI 77 | 1995 | Grounded, preferred, stable extension semantics |
| Powell, *Sequential Decision Analytics*. Princeton | 2022 | State, transition, four policy classes |
| Fazzinga et al., *Revisiting iAAFs*. AI 354 | 2026 | Incomplete AF, i*-extensions, polynomial verification |
| Alfano et al., *Extending AAFs with Knowledge Bases*. KR | 2025 | Metadata-enriched arguments, KAF design |
| Joshi et al., *GTRBAC*. IEEE TKDE | 2005 | Temporal access control engine |
| Park et al., *Generative Agents*. UIST'23 | 2023 | Parallax inverts their approach: depth over breadth |
| Craandijk & Toni, *DL for Abstract Argumentation*. IJCAI | 2020 | Future GNN-based VFA policy (Phase 5+) |

---

## Project Structure

```
parallax/
├── sequential/                  ← Powell's Sequential Decision Framework
│   ├── state.py                    BeliefState, DecisionHistory, ResourceState
│   ├── transition.py               S_{t+1} = S^M(S_t, x_t, W_{t+1})
│   └── model.py                    SequentialDecisionModel orchestrator
│
├── argumentation/               ← Dung's Formal Argumentation
│   └── framework.py                DungAF, IncompleteAF (iAAF), DecisionEvaluator
│
├── temporal_engine/             GTRBAC temporal access control (16 tests)
├── phase1_data_pipeline/        Data ingestion + embeddings + ChromaDB
├── phase2_logic_twin/           Twin core: reasoning, personality, memory
├── phase4_platform/
│   └── measurement/             Divergence tracker
├── tests/                       96 tests (temporal + sequential + argumentation)
├── docs/
│   └── register.html            CIL license acceptance + registration
├── LICENSE                      Collective Intelligence License v1.0
└── CHANGELOG.md                 Version history
```

---

## License: Collective Intelligence License v1.0

**This is not open source. This is not closed source. This is a commitment.**

| ✅ You CAN | ❌ You CANNOT |
|-----------|-------------|
| Use for research, personal, academic work | Use commercially without a separate agreement |
| Modify for your own use | Build a competing product without a license |
| Publish findings (with attribution) | Remove attribution or license notices |
| Access the collective insight database | Redistribute without consent |

**The one obligation:** share anonymized insights within 12 months.

**The one guarantee:** Claw's PII redaction ensures what you share is structurally incapable of containing personal data.

**[Accept the license and register →](https://devudaaaa.xyz/parallax/register.html)**

---

<div align="center">

**devudaaaa Research Lab**

[devudaaaa.xyz](https://devudaaaa.xyz) · [GitHub](https://github.com/devudaaaa) · [Claw](https://github.com/Leeladitya/claw)

*"We don't add faith to the twin — we measure its absence."*

**దేవుడా!**

</div>
