# Parallax

### A generative agent of one.

---

*In astronomy, parallax is the apparent displacement of an object when observed from two different positions. The greater the distance between viewpoints, the more precise the measurement.*

*This project creates two viewpoints of the same person: a computational model built from their actual data, and the person themselves. The displacement between what the model decides and what the human decides is the measurement.*

*That measurement is the research.*

---

## The Landscape

In 2023, a team at Stanford introduced **generative agents** — computational software agents that simulate believable human behavior by combining large language models with memory, reflection, and planning (Park et al., UIST'23). Twenty-five agents woke up, cooked breakfast, formed opinions, and initiated conversations in a simulated town. The work won best paper and launched a field.

That team went further. They conducted two-hour qualitative interviews with over 1,000 real people and built generative agents that replicated those individuals' survey responses with 85% of the accuracy that the real people achieved when re-tested two weeks later (Park et al., 2024). For the first time, AI agents could meaningfully stand in for real humans in social science research.

The commercial venture born from this work, **Simile**, is now building a foundation model for predicting human behavior at any scale — from earnings call rehearsals to policy simulations to entire societies.

**Parallax** lives in the same intellectual tradition, but asks a fundamentally different question.

Where genagents simulates **1,000 people with breadth**, Parallax models **one person with depth**. Where Simile predicts what populations *will* do, Parallax measures what one individual *actually* does — and studies the displacement between prediction and reality.

That displacement — small in routine decisions, large in moments of genuine moral or existential weight — is a signal. It maps the boundary of what computation can replicate about human decision-making, and what it cannot.

---

## The Question

Here is the observation that motivates this work:

You can build a remarkably faithful model of how a person communicates, reasons, and remembers. Modern LLMs, grounded in real personal data, can replicate someone's writing style, decision patterns, and emotional register with surprising accuracy.

But there is a category of decision where the model hesitates.

Not factual questions. Not optimization problems. The other kind — where competing values collide, where evidence is genuinely ambiguous, where rational calculus doesn't resolve, and yet the real person acts with conviction.

The model says: *I'm 43% confident. Both options have merit.*

The person says: *I know what to do.*

Sometimes that conviction comes from experience too deep to articulate. Sometimes from cultural intuition. Sometimes from what different traditions have called conscience, inner voice, or faith.

Parallax doesn't name it. It **measures** it — by building the most complete logical replica of an individual that current technology allows, and systematically studying every moment where the real person diverges from that replica.

Each divergence is a data point. Over time, the data points become a signal. The signal maps a boundary.

---

## How It Works

The architecture follows four layers, each grounded in a specific lineage in simulation research.

### Perception — *What the agent knows about you*

Before a generative agent can model you, it must perceive your world. Following the principle that believable agents require grounding in rich, specific data (Bates 1994), the data pipeline ingests your actual digital footprint:

**Messages** — Slack exports, WhatsApp conversations, Discord logs. Parsed with timestamps, speaker identification, and a timeline of how you communicate with different people at different times.

**Documents** — PDFs, notes, source code, research papers. Chunked, analyzed for topic and formality, and tagged with an authorization tier that determines who the agent can share it with.

**Photos** — Described by a vision model for content, context, mood, and significance. EXIF metadata adds where and when.

Everything flows through a style analyzer that measures your actual communication fingerprint: sentence length distributions, vocabulary richness, formality range, humor frequency, tone patterns across contexts. Not a personality quiz — a statistical profile built from your own words.

The output is a vector database (ChromaDB) where every piece of your digital life is embedded, searchable, and access-controlled — the agent's equivalent of what Park et al. call the **memory stream**.

### Cognition — *How the agent reasons*

The cognitive core implements three subsystems, drawing from the tradition of cognitive architectures (Newell 1990, Soar) that model the mind as interacting components:

**Personality Engine** — Generates dynamic behavioral instructions from your real communication profile. Not "you are helpful and friendly" — more like "you use 23% more analytical language in professional contexts, drop formality by 40% after 9 PM, and default to Socratic questioning when you disagree." Adapts based on who the agent is talking to, what time it is, and what access tier the conversation falls under.

**Reasoning Engine** — When the agent faces a structured decision, it uses argumentation-based reasoning grounded in Dung's (1995) framework: generating arguments for and against, identifying attack and support relations between claims, computing acceptable argument sets, and producing a confidence score. Every decision is logged. Every confidence score is recorded. When confidence drops below 45%, the system flags that moment as one where logic alone wasn't enough. *(See [VISION.md](VISION.md) for how this connects to the AGORA multi-constitutional debate framework.)*

**Memory System** — Retrieval-augmented generation over your personal vector store, with authorization-aware filtering. The agent recalls what's relevant, respects what's private, and builds conversational context across interactions — grounded in *your real data* rather than synthetic personas.

### Temporality — *When the agent shifts behavior*

Most AI agents exist outside of time. They respond identically at 3 PM and 3 AM, to a stranger and a close friend.

Humans don't work that way. You're sharper in the morning, more reflective at night, more guarded with acquaintances, more honest with people you trust. These rhythms aren't random — they follow temporal patterns that are principled and measurable.

Parallax's temporal engine implements this using a formal constraint system based on periodic time expressions (Bertino et al. 1998) and the Generalized Temporal Role-Based Access Control model (Joshi et al. 2005). Every 60 seconds, the engine evaluates all active constraints and transitions the agent's behavioral state through a formal state machine:

```
 06:00  ·  default mode, public tier
 09:00  ·  professional mode, colleagues tier
 18:00  ·  casual mode, friends tier
 22:00  ·  reflective mode, close tier
 03:00  ·  quiet — system returns to default
```

This is a full state machine with conflict resolution (higher priority overrides lower; negative-takes-precedence at equal priority), dependent triggers (professional mode can automatically enable colleagues tier), and composable periodic expressions that can represent any recurring temporal pattern.

The formalism ensures transitions are auditable, configurable, and grounded in published access control theory — not ad-hoc heuristics.

### Interaction — *Where the agent meets the world*

The agent participates in real environments through:

**Messaging Platforms** — Slack and Discord integrations with human-like response timing, typing indicators, and context-aware behavior that respects temporal state and authorization tiers.

**REST API & WebSocket** — Full programmatic access for sending messages, requesting structured decisions, querying memory, checking temporal state, and streaming real-time interactions.

**Divergence Tracker** — Silently records every decision the agent makes, then waits for you to log what *you* actually decided. Over time, this builds the longitudinal dataset that drives the research.

---

## The Research

The methodology follows the tradition of agent-based modeling (Epstein & Axtell 1996) combined with the emerging field of generative agent simulation (Park et al. 2023, 2024):

**Build the most complete logical model** of a single individual that current technology allows.

**Present that model with real decisions.** Not trivia — genuine dilemmas where the optimal choice is ambiguous, where values compete, where computation alone cannot resolve.

**Record both responses.** What the model chose and what the human chose, with full reasoning chains, confidence scores, temporal context, and the complete argumentation graph.

**Study the displacement.** Particularly where the model's confidence was low and the human acted with conviction anyway. Those moments map the boundary between computational and non-computational decision-making.

The divergence tracker classifies data points by category, computes signal strength, and builds a longitudinal dataset. When enough decisions accumulate, the analysis becomes publishable. This project is an instrument of the **devudaaaa research lab** (devudaaaa.xyz) — see [VISION.md](VISION.md) for how it connects to the lab's broader research program.

---

## Getting Started

### Prerequisites

Python 3.10+ and one of: an Anthropic API key, an OpenAI API key, or [Ollama](https://ollama.ai) for fully offline operation.

### Install

```bash
git clone https://github.com/leeladitya/parallax.git
cd parallax

pip install -r requirements.txt

cp .env.example .env
# Add your API key(s) to .env
```

### Feed it your data

Export your digital footprint into `data/raw/`:

```
data/raw/
├── messages/       # Slack JSON, WhatsApp .txt, Discord exports
├── documents/      # PDFs, .docx, .md, source code, research papers
└── photos/         # Images (EXIF metadata preserved if available)
```

### Run the pipeline

```bash
python -m phase1_data_pipeline.run_pipeline
```

### Talk to your agent

```bash
python -m phase2_logic_twin.twin
```

| Command | What it does |
|---|---|
| `/tier public\|friends\|close\|private` | Set who the agent thinks it's talking to |
| `/decide <question>` | Structured decision with argumentation + confidence |
| `/temporal` | Show the temporal engine state |
| `/tick` | Force a temporal constraint evaluation |
| `/status` | Full system diagnostics |

### Launch the platform

```bash
python -m phase4_platform.api.server
```

API reference at `localhost:8000/docs`:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/chat` | Conversational interaction |
| `POST /api/v1/decide` | Structured decision with reasoning chain |
| `POST /api/v1/decide/record` | Log what *you* actually decided |
| `GET /api/v1/temporal/status` | Current clock state and active modes |
| `GET /api/v1/temporal/schedule` | Preview the next 24 hours |
| `GET /api/v1/divergence` | Research analytics |

### Verify the temporal engine

```bash
python tests/test_temporal.py
```

10 tests validate periodic expressions, the role state machine, conflict resolution, trigger dependencies, and the default behavioral policy.

---

## Project Structure

```
parallax/
│
├── phase1_data_pipeline/            # Perception
│   ├── ingestors/                   #   Message, document, photo parsers
│   ├── processors/                  #   Style extraction, tone analysis
│   ├── embeddings/                  #   Sentence transformer embeddings
│   └── vector_store/                #   ChromaDB with auth-aware retrieval
│
├── phase2_logic_twin/               # Cognition
│   ├── twin_core/
│   │   ├── personality.py           #   Dynamic personality from real data
│   │   ├── reasoning.py             #   Argumentation-based decisions
│   │   └── memory.py                #   RAG memory with access control
│   ├── twin.py                      #   Agent orchestrator + CLI
│   └── fine_tuning/                 #   Training data formatters
│
├── temporal_engine/                 # Temporality
│   ├── calendars.py                 #   Periodic expressions (Bertino 1998)
│   ├── engine.py                    #   GTRBAC state machine + triggers
│   └── __init__.py                  #   Default behavioral policy
│
├── phase4_platform/                 # Interaction
│   ├── api/                         #   FastAPI with REST + WebSocket
│   ├── connectors/                  #   Slack, Discord integrations
│   └── measurement/                 #   Divergence tracker
│
├── VISION.md                        # Research roadmap + lab integration
├── tests/                           # Temporal engine test suite
├── config.yaml                      # Schedules, tiers, personality config
└── requirements.txt
```

---

## Intellectual Foundations

| Concept | Source | Role in Parallax |
|---|---|---|
| Generative agents | Park et al. (UIST 2023) | Architecture: memory stream + reflection + planning |
| Simulating real people | Park et al. (2024), 1000 agents | Methodology: grounding agents in real individual data |
| Cognitive architectures | Newell (1990), Soar, CoALA (Sumers et al. 2024) | Subsystem design: perception → cognition → action |
| Believability | Bates (1994) | Design goal: the agent should *feel* like the person |
| Bottom-up simulation | Schelling (1978), Epstein & Axtell (1996) | Philosophy: complex behavior emerges from individuals |
| Wicked problems | Rittel & Webber (1973) | Motivation: some problems resist optimization |
| Argumentation frameworks | Dung (1995) | Reasoning engine: structured argument evaluation |
| Multi-constitutional AI | Annam (2025), Vedic-ABA framework | Vision: cross-cultural behavioral modeling via AGORA |
| Periodic time formalism | Bertino et al. (1998) | Temporal constraint expressions |
| Temporal access control | Joshi et al. (2005), GTRBAC | State machine for behavioral mode transitions |
| Network dynamics | Chang et al. (2021) | Future: agent participation in network simulations |
| Ethics of simulation | Wang et al. (2024), Santurkar et al. (2023) | Boundaries: what simulation can and cannot represent |
| Generative ghosts | Morris & Brubaker (2024) | Ethical framing: modeling real people responsibly |
| Simulation schema | NetLogo (Wilensky), D3 (Bostock et al. 2011) | Design inspiration for composable agent definitions |

---

## Ethics

**This models you, not others.** The data pipeline only processes data you explicitly export. No scraping, no inference about other people, no surveillance.

**Privacy by architecture.** All data stays local. LLM API calls are replaceable with local Ollama for fully offline operation. The four-tier authorization system ensures the agent never reveals information above the caller's clearance.

**Not a replacement.** Following Wang et al. (2024), language models cannot fully portray identity groups or replace human participants. Parallax is a research instrument, not a product that pretends to be you.

**Not a ghost.** Morris & Brubaker (2024) explore ethical implications of AI systems that model individuals beyond their lifetime. Parallax is designed for use by the living person it models — a mirror, not a memorial.

**Consent is structural.** You control what goes in, who talks to it, and what tier they see. No one else can create an agent of you.

---

<p align="center">
<strong>Parallax</strong> — a generative agent for studying human decision-making<br/>
An instrument of the <a href="https://devudaaaa.xyz">devudaaaa research lab</a><br/>
<br/>
<em>The displacement between the model and the person is the measurement.<br/>
The measurement is the research.</em>
</p>
