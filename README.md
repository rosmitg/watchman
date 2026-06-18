# Watchman

> Most financial tools answer questions. Watchman asks them first.

Watchman is an AI-powered **proactive** portfolio intelligence app. Instead of
waiting for you to look something up, it continuously watches your holdings —
news, fundamentals, sentiment, price action, and SEC filings — and surfaces a
daily brief plus real-time alerts about the things that actually matter to *your*
portfolio.

## What it does

- **Syncs your portfolio** from Alpaca (positions, cost basis, market value).
- **Runs a multi-agent LangGraph pipeline** across five specialized agents that
  share a single typed state.
- **Generates a daily brief** with a portfolio-health score, themed sections,
  and ticker-tagged insights, synthesized by Claude.
- **Pushes time-sensitive alerts** over WebSockets the moment something moves.
- **Remembers context** via semantic search over news and filings (Pinecone +
  Voyage AI embeddings).

## Architecture

```
        ┌──────────┐
        │  Alpaca  │
        └────┬─────┘
             │ positions
             ▼
     ┌────────────────┐
     │ Portfolio Sync │
     └───────┬────────┘
             │ tickers + holdings
             ▼
 ┌──────────────────────────────────────────────────────┐
 │              LangGraph Pipeline (5 agents)             │
 │                                                        │
 │   news → fundamentals → sentiment → sec → synthesis    │
 └──────────────────────────┬─────────────────────────────┘
                            │ Brief + Alerts
                            ▼
              ┌───────────────────────────┐
              │  Redis Queue + PostgreSQL  │
              └─────────────┬──────────────┘
                            │ WebSocket Push
                            ▼
                  ┌───────────────────┐
                  │  React Frontend   │
                  └───────────────────┘
```

## Tech stack

| Layer          | Technology                                              |
| -------------- | ------------------------------------------------------- |
| Frontend       | React, TypeScript, Tailwind, shadcn/ui, Vite, Zustand   |
| Backend        | FastAPI, Python 3.11, uv                                 |
| Agents         | LangGraph                                               |
| LLM            | Claude (`claude-sonnet-4-6`)                             |
| Auth           | Supabase                                                |
| Database       | PostgreSQL (Cloud SQL)                                  |
| Cache          | Redis (GCP Memorystore)                                 |
| Vector         | Pinecone + Voyage AI                                    |
| Scheduling     | APScheduler + Cloud Scheduler                          |
| Observability  | LangSmith                                               |
| Infra          | GCP Cloud Run                                           |

## Local development

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# edit backend/.env with your keys

# 2. Bring up the stack (postgres + redis + backend)
docker compose up --build

# Backend is now on http://localhost:8000
#   GET /health  -> {"status": "ok", "env": "development"}
```

### Running the backend without Docker

```bash
cd backend
pip install uv
uv pip install --system -e ".[dev]"

# Apply database migrations before starting the server
alembic upgrade head

uvicorn app.main:app --reload
pytest
```

## Architecture Decision Records

- [ADR 001 — LangGraph over CrewAI](docs/adr/001-langgraph-over-crewai.md)
- [ADR 002 — Redis alert queue & brief cache](docs/adr/002-redis-alert-queue.md)
- [ADR 003 — WebSockets over polling](docs/adr/003-websockets-over-polling.md)
- [ADR 004 — Pinecone over ChromaDB](docs/adr/004-pinecone-over-chromadb.md)
- [ADR 005 — shadcn/ui over raw Tailwind](docs/adr/005-shadcn-over-raw-tailwind.md)

## Sprint progress

- [x] **Sprint 1 — Core infrastructure**: scaffold, config, LangGraph skeleton,
      health check, CI, docker-compose, ADRs.
- [ ] **Sprint 2 — Agent implementations**: wire up news, fundamentals,
      sentiment, SEC, and synthesis agents.
- [ ] **Sprint 3 — Brief generation & persistence**: PostgreSQL models,
      brief storage, Redis caching.
- [ ] **Sprint 4 — Real-time alerts**: Redis queue, WebSocket push, scheduler.
- [ ] **Sprint 5 — Frontend**: React dashboard, brief view, live alerts.
