# Vision — Parallax and the devudaaaa Research Program

*Where this project came from, where it's going, and how the pieces connect.*

---

## Origin

In 2020, before large language models existed as consumer products, we built a system that attempted to replicate an individual's decision-making from personal data — PROLOG-based reasoning, neural network personality modeling, 380GB of training data. The system was deployed on Keybase and Slack and achieved 55-65% behavioral similarity in messaging interactions.

The system replicated facts well. It replicated communication style well. It even replicated reasoning patterns on straightforward problems.

But there was a ceiling. On a specific class of decision — ambiguous, values-laden, personally consequential — the system's predictions diverged systematically from the real person's choices. Not randomly. *Systematically.* The divergence wasn't noise. It was signal.

That observation became a research question: **What fills the gap between computational prediction and human decision-making?**

Parallax is the instrument built to measure that gap with modern tools. The devudaaaa research lab (devudaaaa.xyz) is the program that studies what the measurements reveal.

---

## The Research Ecosystem

Parallax is one instrument in a connected research infrastructure. Here is how the pieces fit together:

```
┌─────────────────────────────────────────────────────────────────┐
│                     devudaaaa Research Lab                       │
│              devudaaaa.xyz — "what makes us, us?"                │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Parallax    │  │    AGORA     │  │       Claw             │  │
│  │              │  │              │  │                        │  │
│  │  Generative  │  │  Multi-      │  │  OPA-gated MCP        │  │
│  │  agent of    │◄─┤  constitu-   │  │  governance for        │  │
│  │  one person  │  │  tional      │  │  AI agent access       │  │
│  │              │  │  argumen-    │  │  control                │  │
│  │  Measures    │  │  tation      │  │                        │  │
│  │  divergence  │  │  engine      │  │  Policy enforcement    │  │
│  │  signal      │  │              │  │  for who/what/when     │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘  │
│         │                 │                       │               │
│         └─────────────────┼───────────────────────┘               │
│                           │                                       │
│  ┌────────────────────────┴──────────────────────────────────┐   │
│  │            Vedic-ABA Constitutional Framework              │   │
│  │   Formalizing ancient wisdom for modern AI governance      │   │
│  │   (Dung 1995 → multi-cultural debate → emergent ethics)    │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Parallax → The Measurement Instrument

What it does: Creates a high-fidelity generative agent of a single individual, presents it with real decisions, and records every divergence between the model's choice and the human's choice.

What it produces: A longitudinal dataset of decision-level divergences annotated with confidence scores, reasoning chains, temporal context, and argumentation graphs.

Research output: Quantitative mapping of the boundary between computationally predictable and computationally unpredictable human behavior.

### AGORA → The Reasoning Backbone

What it does: Implements multi-constitutional argumentation — structured debate between ethical frameworks (Vedic, Confucian, Islamic, Western liberal) using Dung's (1995) argumentation semantics to resolve conflicting arguments.

How it connects to Parallax: When Parallax's reasoning engine faces a decision where arguments conflict, AGORA provides the formal resolution mechanism. Instead of a simple weighted average, it computes the grounded extension (the set of arguments that survive all attacks) and synthesizes cross-cultural resolutions.

Why this matters: Behavioral prediction breaks down differently across cultural contexts. A person's divergence from their computational model may be driven by cultural reasoning patterns that a single-framework model cannot capture. AGORA enables Parallax to model decisions through multiple ethical lenses simultaneously, improving prediction for culturally grounded behavior while making the remaining divergences — the truly irreducible ones — sharper and more informative.

Research output: Published framework for multi-constitutional AI governance (Annam 2025), with implementation demonstrating how ancient Vedic principles like apad-dharma (emergency ethics) and lok-sangraha (collective welfare) can be formalized using assumption-based argumentation and integrated with modern access control systems.

### Claw → The Governance Layer

What it does: OPA-gated MCP (Model Context Protocol) server that enforces fine-grained access control policies on AI agent interactions. Built on Open Policy Agent with full test coverage (github.com/Leeladitya/claw — 2,192 lines).

How it connects to Parallax: Parallax's authorization tiers (public → friends → close → private) need enforcement that goes beyond prompt instructions. Claw provides the infrastructure: policy-as-code that determines which tools the agent can access, which data it can retrieve, and which actions it can take — all evaluated at runtime against the caller's identity, the temporal context, and the sensitivity of the requested resource.

Why this matters: As generative agents become more capable, the governance question becomes critical. Enterprise deployment of behavioral simulations (the problem Simile is solving commercially) requires auditable, policy-driven access control. Claw demonstrates that this governance layer can be built using existing infrastructure (OPA + MCP) rather than requiring novel systems.

Research output: Production-ready governance architecture for agentic AI systems, demonstrating constitutional AI principles implemented as enforceable policy.

### Vedic-ABA Framework → The Theoretical Foundation

What it does: Formalizes ancient Vedic civilizational wisdom — specifically contextual decision-making principles like apad-dharma — into computational logic using assumption-based argumentation (Bondarenko, Dung, Kowalski & Toni 1997).

How it connects to everything: This is the theoretical foundation. The framework demonstrates that AI constitutional governance need not be limited to a single cultural tradition (as in Bai et al. 2022's Constitutional AI). Instead, multiple constitutional models trained on different civilizational principles can engage in structured debate, potentially discovering ethical principles that transcend individual traditions.

The multi-constitutional debate structure:

```
vedic_model        →  dharma, ahimsa, apad-dharma, lok-sangraha
confucian_model    →  ren, li, harmony, social order
islamic_model      →  justice, mercy, maslaha, protection of life
western_model      →  individual rights, utilitarianism, rule of law

         ↓ structured argumentation ↓

grounded extension  →  arguments that survive all attacks
synthesized wisdom  →  cross-cultural resolution
emergent principles →  insights not encoded in any single tradition
```

Research output: Published paper formalizing this framework with full implementation in logic programming.

---

## Why These Pieces Belong Together

The research program asks: *What makes human decisions irreducibly human?*

To answer that, you need:

1. **An instrument that measures the gap** (Parallax) — building the best possible computational model of a person and recording where it fails.

2. **A reasoning system that can model decisions through multiple cultural lenses** (AGORA) — because the gap between computation and humanity isn't culturally neutral. A model calibrated to Western rational decision-making will fail differently on decisions grounded in Vedic dharma or Confucian li. Multi-constitutional argumentation makes the remaining divergences more informative.

3. **A governance layer that controls what the agent can do** (Claw) — because building a high-fidelity model of a real person raises real privacy, safety, and ethical concerns that require enforceable policy, not just prompt instructions.

4. **A theoretical foundation that connects ancient wisdom to modern computation** (Vedic-ABA) — because the civilizations that have navigated extraordinary circumstances for millennia have encoded decision-making wisdom that modern AI systems, trained on recent and culturally narrow data, lack access to.

---

## Roadmap

### Completed

- [x] Data pipeline: message, document, and photo ingestion with style profiling
- [x] Cognitive core: personality engine, argumentation-based reasoning, RAG memory
- [x] Temporal engine: GTRBAC periodic expressions, state machine, conflict resolution
- [x] Platform: REST API, WebSocket, Slack/Discord connectors
- [x] Divergence tracker: decision logging with confidence scoring
- [x] Test suite: 10 tests validating temporal engine formalism
- [x] Claw: OPA-gated MCP governance (separate repo, production-ready)
- [x] Vedic-ABA paper: multi-constitutional framework formalized and published

### In Progress

- [ ] AGORA integration: connect multi-constitutional debate to Parallax's reasoning engine
- [ ] Divergence analysis toolkit: statistical methods for signal extraction from decision logs
- [ ] Qualitative interview protocol: structured methodology for building agent profiles (aligned with Park et al. 2024's two-hour interview approach)

### Planned

- [ ] Population mode: multiple Parallax agents interacting in a shared environment (connecting to the agent-based modeling tradition of Epstein & Axtell)
- [ ] Simile API compatibility layer: enable Parallax agents to participate in Simile's population-scale simulations
- [ ] Cross-cultural divergence studies: compare displacement patterns across agents built from individuals in different cultural contexts
- [ ] Faith-variable publication: formal analysis of the divergence signal with game-theoretic experimental design

---

## On Simile and Parallax

Simile is building the foundation model for behavioral prediction at population scale. Their trajectory — from the Smallville research prototype to a company with Fortune 10 customers in months — is remarkable product execution in a field that barely existed two years ago.

Parallax and the devudaaaa research program exist in the same intellectual ecosystem but occupy a different niche. Three areas of natural connection:

**Behavioral conflict resolution.** When Simile's agents face ambiguous scenarios where training data points in multiple directions, the argumentation framework underlying Parallax and AGORA provides a formal, auditable mechanism for resolution. Enterprise customers running simulated litigation or policy testing will need explainable reasoning for why the simulation chose one behavioral path over another. Argumentation semantics provide exactly this — which arguments survived, which were defeated, and why.

**Prediction calibration.** Simile's agents achieve 85%+ accuracy on social science benchmarks. But at scale, customers will encounter the remaining 15% — and they'll ask why the model missed. Parallax's research on where behavioral prediction systematically breaks down, and the divergence tracker's methodology for classifying those breakdowns, could inform calibration features that help customers understand when to trust a simulation and when to seek further validation.

**Multi-cultural modeling.** Simile's initial agent bank of 1,000 people is representative of the U.S. population. As the product expands globally, the challenge of simulating behavior across diverse cultural contexts intensifies. The multi-constitutional framework (Vedic, Confucian, Islamic, Western) provides a principled approach to modeling culturally grounded decision-making rather than defaulting to a single cultural lens.

---

## Who Built This

**Leela Aditya Annam (Leed)** — Product Specialist, researcher, consultant and founder. Former technical lead at Thailand's National Science and Technology Development Agency (NSTDA), where he led a distributed team shipping cybersecurity infrastructure protecting it's citizens. Founded and exited a cybersecurity startup ($2M+ enterprise contracts). Trained in formal methods under Professor Phan Minh Dung (creator of argumentation framework theory, Artificial Intelligence 1995). Built the original digital twin system in 2020. Currently operates the devudaaaa research lab studying human decision-making at the intersection of game theory, behavioral science, and the question of what computation cannot replicate.

Portfolio: [leed.life](https://leed.life) · Lab: [devudaaaa.xyz](https://devudaaaa.xyz) · Code: [github.com/Leeladitya/claw](https://github.com/Leeladitya/claw)

---

<p align="center">
<em>"The artifact gleamed under the museum's soft lighting, its intricate engravings<br/>
telling a story far more complex than any textbook could capture."</em><br/><br/>
Sometimes research is less about grand revelations and more about quiet,<br/>
unexpected moments of understanding. A recurring signal stretching across<br/>
thousands of decisions. A subtle thread of human connection that computation<br/>
can measure but not replicate.<br/><br/>
That's what we're looking for.
</p>
