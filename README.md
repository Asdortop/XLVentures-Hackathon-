# Praxis AI — Agentic Decision Intelligence Platform

> **B2B decision automation powered by a 6-agent LangGraph pipeline, 3-layer memory, and human-in-the-loop control.**

Praxis AI turns unstructured business signals (meeting notes, CRM updates, emails) into ranked, evidence-backed **Next Best Actions** — learning from every approval and rejection your team makes.

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PRAXIS AI PLATFORM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   USER INPUT                                                                │
│   ─────────                                                                 │
│   Entity Name + Interaction Text (free text)                                │
│            │                                                                │
│            ▼                                                                │
│   ┌──────────────────┐        ┌──────────────────────────────────┐          │
│   │  Domain Adapter  │        │         LLM Provider             │          │
│   │  (YAML Config)   │        │   Groq → Gemini → Ollama         │          │
│   │                  │        │         (fallback chain)          │          │
│   │  • intents.yaml  │        └──────────────────────────────────┘          │
│   │  • actions.yaml  │                       │                              │
│   │  • rules.yaml    │◄──────────────────────┘                              │
│   │  • knowledge.yaml│                                                      │
│   └────────┬─────────┘                                                      │
│            │  feeds                                                          │
│            ▼                                                                │
│   ╔═════════════════════════════════════════════════════════════╗            │
│   ║              LANGGRAPH AGENT PIPELINE                      ║            │
│   ║                  (SSE Streamed)                            ║            │
│   ║                                                             ║            │
│   ║  ┌──────────┐   ┌──────────┐   ┌──────────┐              ║            │
│   ║  │✦ PLANNER │──▶│◈ CONTEXT │──▶│⬡ DEPEND. │              ║            │
│   ║  │          │   │          │   │          │              ║            │
│   ║  │Classify  │   │Search    │   │Map entity│              ║            │
│   ║  │intent &  │   │memory &  │   │graph &   │              ║            │
│   ║  │entities  │   │past cases│   │relations │              ║            │
│   ║  └──────────┘   └────┬─────┘   └────┬─────┘              ║            │
│   ║                      │  reads        │                    ║            │
│   ║                      ▼              ▼                    ║            │
│   ║  ┌──────────┐   ┌──────────┐   ┌──────────┐              ║            │
│   ║  │⚑ CRITIC  │◀──│★ RECOMM. │◀──│◎ RISK    │              ║            │
│   ║  │          │   │          │   │          │              ║            │
│   ║  │Reflect & │   │Rank &    │   │Score     │              ║            │
│   ║  │validate  │   │reason    │   │severity  │              ║            │
│   ║  │quality   │   │actions   │   │& urgency │              ║            │
│   ║  └────┬─────┘   └──────────┘   └──────────┘              ║            │
│   ║       │ flags LOW_CONFIDENCE / ESCALATE                   ║            │
│   ╚═══════╪═════════════════════════════════════════════════════╝            │
│            │                                                                │
│            ▼                                                                │
│   ┌─────────────────────────────────┐                                       │
│   │    NBA (Next Best Actions)      │                                       │
│   │    Ranked · Confidence scored   │                                       │
│   │    Evidence-backed · Explained  │                                       │
│   └────────────────┬────────────────┘                                       │
│                    │                                                        │
│                    ▼                                                        │
│   ┌─────────────────────────────────┐                                       │
│   │    HUMAN-IN-THE-LOOP (HITL)     │                                       │
│   │    Approve  │  Reject + Reason  │                                       │
│   └────────────────┬────────────────┘                                       │
│                    │  writes decision                                        │
│                    ▼                                                        │
│   ╔═════════════════════════════════════════════════╗                        │
│   ║              3-LAYER MEMORY SYSTEM              ║                        │
│   ║                                                 ║                        │
│   ║  ┌─────────────┐  ┌─────────────┐  ┌────────┐ ║                        │
│   ║  │ SQL Patterns│  │Vector Store │  │ Entity │ ║                        │
│   ║  │             │  │             │  │ Graph  │ ║                        │
│   ║  │issue→resol. │  │sentence-    │  │Network │ ║                        │
│   ║  │success rates│  │transformers │  │X / RAG │ ║                        │
│   ║  │             │  │cosine sim.  │  │        │ ║                        │
│   ║  └─────────────┘  └─────────────┘  └────────┘ ║                        │
│   ╚═════════════════════════════════════════════════╝                        │
│            │  ▲                                                             │
│            │  │  feeds back into Context agent on next request             │
│            └──┘                                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Map

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 14, React 18 | SSE streaming UI, HITL review, animated recommendations |
| **Backend** | FastAPI, Python 3.12 | REST + SSE endpoints, domain management |
| **Agent Pipeline** | LangGraph 0.1 | Stateful 6-agent directed graph |
| **LLM** | Groq (Llama 3) → Gemini → Ollama | Multi-provider with automatic fallback |
| **Memory — Layer 1** | SQLite + SQLAlchemy | Issue→resolution pattern table with success rates |
| **Memory — Layer 2** | sentence-transformers + SQLite | 384-dim neural embeddings, cosine similarity search |
| **Memory — Layer 3** | NetworkX | Entity relationship graph (GraphRAG) |
| **Domain Config** | YAML adapters | Per-domain intents, actions, rules, knowledge — LLM-generated |
| **Database** | SQLite (`praxis.db`) | Interactions, NBAs, actions, events, domains |

---

## The 6 Agents — What Each One Does

```
✦ PLANNER      Reads intents.yaml → classifies the interaction into a known intent
               (e.g. "churn_risk", "renewal_approaching", "candidate_rejection")
                    │
                    ▼
◈ CONTEXT      Queries all 3 memory layers → finds past similar cases, semantic
               matches, and entity history to build an evidence package
                    │
                    ▼
⬡ DEPENDENCY   Walks the entity graph → identifies related entities and past
               decisions that may be impacted by this interaction
                    │
                    ▼
◎ RISK         Reads rules.yaml → runs deterministic keyword triggers, then
               calls LLM with context to assign severity (low/medium/high/critical)
                    │
                    ▼
★ RECOMMENDER  Reads actions.yaml → filters by intent, ranks by base priority +
               memory boosts + semantic evidence, calls LLM for 2-sentence reasoning
                    │
                    ▼
⚑ CRITIC       Reviews the top recommendation → flags LOW_CONFIDENCE if evidence
               is thin, or ESCALATE if severity is critical with no clear path
```

---

## Key Features

- **Live Agent Streaming** — Each agent streams its output via SSE as it runs. Watch the pipeline execute in real time.
- **Self-Healing Blueprint Studio** — Describe your business in plain text; the LLM generates a full YAML domain adapter. Validation errors trigger automatic re-generation (up to 3 attempts).
- **3-Layer Memory** — SQL patterns track success rates. Vector store finds semantically similar past cases. Entity graph maps relationships between accounts/candidates/cases.
- **Rejection Learning Loop** — When a human rejects an NBA with a reason, that correction is embedded into vector memory so future recommendations improve.
- **Multi-Domain** — Each company gets isolated memory, adapter config, and entity graph. Switch between domains in one click.
- **Document Ingestion** — Upload PDF, DOCX, TXT, CSV, or Markdown SOPs directly into the onboarding form.

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- A Groq API key (free at [console.groq.com](https://console.groq.com)) or Gemini API key

### 1. Backend

```bash
cd backend

# Copy env and add your API key
cp .env.example .env
# → Set GROQ_API_KEY or GEMINI_API_KEY in .env

# Install dependencies
pip install -r requirements.txt

# Run database migration (first time only)
python migrate.py

# Start the server
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

---

## Environment Variables

```env
# .env (backend/)

# LLM — at least one required (Groq recommended, fastest)
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
OLLAMA_BASE_URL=http://localhost:11434   # optional local fallback

# LLM model names (defaults shown)
GROQ_MODEL=llama3-8b-8192
GEMINI_MODEL=gemini-1.5-flash
```

The system tries providers in order: **Groq → Gemini → Ollama**. If one fails or has no key, it moves to the next automatically.

---

## Demo Walkthrough

### Step 1 — Pick a domain
Select **TalentBridge** (Staffing) or **Meridian SaaS** from the domain switcher in the sidebar.

### Step 2 — Submit an interaction
Go to **Submit Interaction** and paste:

> *"Just got off a call with GlobalBank's hiring director. They rejected our 3rd candidate today for the CFO search — said our profiles are completely off-brief. This is their largest contract ($2.4M). The client hasn't paid last month's retainer either."*

Watch all 6 agents stream their output live.

### Step 3 — Review the recommendations
See the ranked Next Best Actions slide in with confidence scores and LLM reasoning. The top action has a shimmer effect and expanded reasoning.

### Step 4 — Approve or reject
Click **View Full Analysis → Approve All** to approve. The decision writes to all 3 memory layers.

### Step 5 — Submit again (same entity)
Submit another interaction about GlobalBank. Watch the **Context agent** find the previous decision semantically (`similarity: 0.72`) and the recommendations improve.

### Step 6 — Memory Explorer
Go to **🧠 Memory Explorer** to see:
- The vector memories that were stored
- The entity knowledge graph (canvas visualization)
- Decision timeline

### Step 7 — Add your own domain
Go to **Blueprint Studio** → describe your company → upload your SOPs as PDF → click **Generate Blueprint** → watch the self-healing LLM generation stream live → **Deploy**.

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
│   │   ├── adapter_builder.py # Self-healing LLM generation loop
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
        ├── page.tsx           # Command Center
        ├── interact/          # Submit Interaction (SSE streaming)
        ├── nba/               # NBA Inbox + Detail
        ├── memory/            # Memory Explorer
        ├── outcomes/          # Business Outcomes dashboard
        └── onboarding/        # Blueprint Studio
```

---

## Evaluation Alignment

| Criterion | Implementation |
|---|---|
| **Agentic AI Architecture** | 6-agent LangGraph directed graph with state passing, critic reflection loop |
| **Reusability & Extensibility** | YAML adapter system — new domain = new adapter, same pipeline |
| **Memory & Orchestration** | 3-layer memory (SQL + vector embeddings + entity graph), rejection learning loop |
| **User Experience** | SSE live streaming, animated recommendation reveal, HITL review, Memory Explorer |
| **Innovation** | Self-healing blueprint generation, PDF knowledge ingestion, GraphRAG entity context |
| **Business Reasoning** | LLM-generated reasoning per recommendation, evidence-tagged by source |
| **NBA Quality** | Ranked by: base priority + semantic boost + memory success rate + recency |
| **Measurable Outcomes** | Approval rate, avg time-to-decision, confidence trend, value awaiting |
