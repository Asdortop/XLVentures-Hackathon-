# Praxis AI — Agentic Decision Intelligence Platform

> **Turn any business signal into ranked, evidence-backed Next Best Actions — powered by a 6-agent LangGraph pipeline and 3-layer memory that learns from every human decision.**

---

## 👥 Team

| Name | 
|---|
| **Tejas G** | 
| **Pranav Talupula** | 
| **Rushindra M** | 

---

## 🔗 Links

| | Link |
|---|---|
| 🚀 **Live Deployment** | [https://xl-ventures-hackathon-1ddi.vercel.app/](https://xl-ventures-hackathon-1ddi.vercel.app/) |
| 📦 **GitHub Repository** | [https://github.com/Asdortop/XLVentures-Hackathon-](https://github.com/Asdortop/XLVentures-Hackathon-) |

---

## Screenshots

### Command Center
![Command Center](docs/screenshots/command_center.png)

### Live Agent Pipeline — Submit Interaction
![Submit Interaction](docs/screenshots/interact.png)

### NBA Inbox
![NBA Inbox](docs/screenshots/nba_inbox.png)

### Memory Explorer
![Memory Explorer](docs/screenshots/memory_explorer.png)

### Blueprint Studio — Add Your Own Domain
![Blueprint Studio](docs/screenshots/blueprint_studio.png)

---

## What It Does

Praxis AI is a **B2B decision intelligence platform** for customer-facing teams. You paste in a raw business signal — a meeting note, CRM update, or email — and 6 specialized AI agents reason over it in sequence, drawing on memory of past decisions, to produce ranked Next Best Actions with confidence scores and LLM-generated reasoning.

A human reviews and approves/rejects each recommendation. That decision gets written back into a 3-layer memory system, so the platform gets smarter with every interaction.

---

## Architecture

```mermaid
flowchart TD
    INPUT["📥 User Input\nEntity Name + Interaction Text\nmeeting notes · emails · CRM updates"]

    subgraph CONFIG["⚙️ Domain Configuration"]
        ADAPTER["Domain Adapter\nYAML Config\nintents · actions · rules · knowledge"]
        LLM["LLM Provider\nGroq → Gemini → Ollama\nfallback chain"]
    end

    subgraph PIPELINE["🤖 LangGraph Agent Pipeline  —  SSE Streamed Live to UI"]
        direction LR
        P["✦ Planner\nClassify intent\n& keywords"]
        C["◈ Context\nSearch 3 memory\nlayers"]
        D["⬡ Dependency\nMap entity graph\n& blast radius"]
        R["◎ Risk\nScore severity\n& urgency"]
        REC["★ Recommender\nRank & reason\nactions"]
        CR["⚑ Critic\nReflect &\nvalidate quality"]
        P --> C --> D --> R --> REC --> CR
    end

    subgraph NBA["📋 Next Best Actions"]
        NBA1["Ranked · Confidence Scored\nEvidence-Backed · LLM Explained"]
    end

    subgraph HITL["👤 Human-in-the-Loop"]
        APPROVE["✓ Approve"]
        REJECT["✕ Reject + Reason"]
    end

    subgraph MEMORY["🧠 3-Layer Memory System"]
        M1["◎ SQL Patterns\nissue → resolution\nsuccess rates"]
        M2["🔮 Vector Store\nsentence-transformers\ncosine similarity"]
        M3["⬡ Entity Graph\nNetworkX / GraphRAG\nrelationship weights"]
    end

    INPUT --> CONFIG
    CONFIG --> PIPELINE
    LLM -.->|"powers Risk,\nRecommender,\nCritic"| PIPELINE
    PIPELINE --> NBA
    NBA --> HITL
    APPROVE -->|"writes decision back"| MEMORY
    REJECT -->|"embeds correction"| MEMORY
    MEMORY -->|"feeds Context agent\non next request"| C

    style PIPELINE fill:#1a1f35,stroke:#6366f1,color:#e2e8f0
    style MEMORY fill:#0f1f18,stroke:#10b981,color:#e2e8f0
    style CONFIG fill:#1a1520,stroke:#a855f7,color:#e2e8f0
    style HITL fill:#1a1208,stroke:#f59e0b,color:#e2e8f0
    style NBA fill:#0f1520,stroke:#818cf8,color:#e2e8f0
```

### The 6 Agents — What Each One Does

| Agent | Responsibility | Key Output |
|---|---|---|
| **✦ Planner** | Reads `intents.yaml` → classifies the interaction into a known intent | `matched_intent`, `keywords_found` |
| **◈ Context** | Queries all 3 memory layers → finds past similar cases, semantic matches, playbooks, CRM data | `semantic_memories`, `memory_patterns`, `playbook_matches` |
| **⬡ Dependency** | Walks the entity graph → identifies related entities and blast radius | `affected_entities`, `blast_radius`, `graph_context` |
| **◎ Risk** | Keyword triggers + LLM assessment → assigns severity level | `severity`, `risk_signals`, `risk_reasoning` |
| **★ Recommender** | Ranks actions by confidence formula (base × severity × memory boosts), LLM writes 2-sentence reasoning | `ranked_actions` with evidence chains |
| **⚑ Critic** | Reflects on top recommendation → flags `LOW_CONFIDENCE` or `ESCALATE` | `critique`, `critique_flag` |

---

## Key Features

- **Live Agent Streaming** — SSE streams each agent's output to the UI as it runs. Watch the 6-agent pipeline execute step by step with animated cards.
- **Animated Recommendations** — After pipeline completes, ranked action cards slide in with staggered animation and confidence bars that fill in real time.
- **Self-Healing Blueprint Studio** — Describe your business in plain text; the LLM generates a full YAML domain adapter. Validation errors trigger automatic re-generation (up to 3 attempts), streamed live.
- **3-Layer Memory** — SQL patterns track issue→resolution success rates. Vector store finds semantically similar past cases. Entity graph maps relationships between accounts/candidates/cases and improves context every run.
- **Rejection Learning Loop** — When a human rejects an NBA with a reason, that correction is embedded into vector memory so future recommendations improve automatically.
- **Multi-Domain Isolation** — Each company gets its own memory, adapter config, and entity graph. Switch between domains in one click.
- **Document Ingestion** — Upload PDF, DOCX, TXT, CSV, or Markdown SOPs directly into the onboarding form for knowledge extraction.
- **Memory Explorer** — Visual canvas showing the entity knowledge graph, semantic memories, SQL patterns, and full decision timeline.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, Vanilla CSS |
| Backend | FastAPI, Python 3.12 |
| Agent Pipeline | LangGraph 0.1, stateful directed graph |
| LLM | Groq (Llama 3) → Gemini 1.5 Flash → Ollama (fallback chain) |
| Memory — Layer 1 | SQLite + SQLAlchemy (issue→resolution patterns) |
| Memory — Layer 2 | sentence-transformers, 384-dim embeddings, cosine search |
| Memory — Layer 3 | NetworkX (entity relationship graph, GraphRAG) |
| Domain Config | Self-generated YAML adapters (intents, actions, rules, knowledge) |
| Streaming | Server-Sent Events (SSE) for both pipeline + blueprint generation |

---

## Included Domains

| Domain | Industry | Primary Entity |
|---|---|---|
| **TalentBridge** | Executive Staffing | Candidate Search |
| **Meridian SaaS** | B2B SaaS | Customer Account |
| **LexOps Legal** | Legal Services | Matter / Case |

Each comes pre-loaded with intents, actions, rules, and sample scenarios. Add your own via Blueprint Studio.

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- API key from [console.groq.com](https://console.groq.com) (free) **or** a Gemini API key

### 1. Clone & configure

```bash
git clone https://github.com/Asdortop/XLVentures-Hackathon-.git
cd XLVentures-Hackathon-
```

Create `backend/.env`:
```env
GROQ_API_KEY=gsk_your_key_here

# Optional fallbacks
# GEMINI_API_KEY=AIza...
# OLLAMA_BASE_URL=http://localhost:11434
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
python migrate.py        # first time only — sets up the database
uvicorn main:app --reload --port 8000
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)**

The app auto-seeds 3 demo domains (TalentBridge, Meridian SaaS, LexOps Legal) on first startup.

---

## Demo in 5 Steps

**1. Pick a domain** — Select **Meridian SaaS** from the sidebar domain switcher.

**2. Submit an interaction** — Go to **Submit Interaction** and click the **"Churn Risk"** sample chip. Hit **Analyze & Generate Recommendations**.

**3. Watch the pipeline** — 6 agent cards animate live as each agent processes. See the active agent pulse with a glow ring while others show checkmarks as they complete.

**4. Review recommendations** — Ranked action cards slide in with animated confidence bars. The top card has LLM reasoning explaining why it was chosen.

**5. Approve & see memory update** — Click **View Full Analysis → Approve All**. Then go to **🧠 Memory Explorer** to see the vector memories and entity graph that were just written.

---

## Project Structure

```
XLHack/
├── backend/
│   ├── agents/               # 6 LangGraph agents
│   │   ├── planner.py
│   │   ├── context.py
│   │   ├── dependency.py
│   │   ├── risk.py
│   │   ├── recommender.py
│   │   └── critic.py
│   ├── adapters/             # Domain YAML configs (per-company)
│   │   ├── talentbridge/
│   │   ├── saas_csm/
│   │   └── lexops_legal/
│   ├── core/
│   │   ├── adapter.py        # YAML loader + cache
│   │   ├── adapter_builder.py # Self-healing LLM generation
│   │   └── pipeline.py       # LangGraph state machine
│   ├── memory/
│   │   ├── vector_store.py   # Neural embeddings + cosine search
│   │   └── entity_graph.py   # NetworkX GraphRAG
│   ├── routes/               # FastAPI route handlers
│   ├── database.py           # SQLAlchemy models
│   ├── llm_provider.py       # Multi-provider fallback chain
│   └── main.py
│
└── frontend/
    └── app/
        ├── page.tsx           # Command Center dashboard
        ├── interact/          # Submit Interaction (SSE streaming)
        ├── nba/               # NBA Inbox + Detail + HITL
        ├── memory/            # Memory Explorer
        ├── outcomes/          # Business Outcomes dashboard
        └── onboarding/        # Blueprint Studio
```

---

## Environment Variables

```env
# backend/.env

# LLM — at least one required (Groq is fastest, recommended)
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...          # optional fallback
OLLAMA_BASE_URL=http://localhost:11434  # optional local fallback

# Production only
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```
