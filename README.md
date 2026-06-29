# Watchman — Portfolio Intelligence Engine for STK

Proactive multi-agent system that monitors your portfolio and delivers personalised daily briefs.

**Integration:** Powers the Brief tab in [STK Portfolio Assistant](https://github.com/rosmitg/stk-portfolio-assistant) — https://stk-frontend-512165788990.australia-southeast1.run.app

---

## What it does

Watchman runs on a schedule rather than on request. Each morning it reads every user's holdings from the shared database, runs a five-agent LangGraph pipeline across news, fundamentals, sentiment, and SEC filings, and synthesises the results into a single brief — a portfolio-health score, themed sections, and ticker-tagged insights. The brief is written back to PostgreSQL (where STK reads it) and emailed to the user at **07:00 Australia/Sydney**.

---

## The five agents

Each agent contributes findings to a single typed LangGraph state; the synthesis agent reads that state and writes the final brief.

| Agent | Data source | Purpose |
|---|---|---|
| News | NewsAPI | Pulls recent headlines for every held ticker. |
| Fundamentals | yfinance | Fetches price, valuation, and fundamental metrics per holding. |
| Sentiment | FinBERT | Scores the tone of each ticker's news flow. |
| SEC | EDGAR (SEC.gov) | Surfaces recent filings for held companies. |
| Synthesis | Claude (`claude-sonnet-4-6`) | Merges all findings into a scored, sectioned daily brief. |

---

## Architecture

```
  ┌─────────────┐   07:00 Australia/Sydney
  │ APScheduler │───────────────┐
  └─────────────┘               │
                                ▼
                    ┌───────────────────────┐
                    │   LangGraph Pipeline   │
                    │                        │
                    │  News ─┐               │
                    │  Fund. ─┤              │
                    │  Sent. ─┼─► Synthesis  │
                    │  SEC  ─┘               │
                    └───────────┬────────────┘
                                │ Brief + Alerts
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
        ┌───────────────────┐       ┌──────────────────┐
        │  Shared PostgreSQL │       │   Email (Resend) │
        │  (read by STK)     │       │   daily brief    │
        └───────────────────┘       └──────────────────┘
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Agents | LangGraph |
| LLM | Claude API (`claude-sonnet-4-6`) |
| Backend | FastAPI, Python 3.11 |
| Cache / queue | Redis (GCP Memorystore) |
| Vector | Pinecone + Voyage AI |
| Scheduling | APScheduler + Cloud Scheduler |
| Email | Resend |
| Infra | GCP Cloud Run |

---

## Deployment

Watchman runs on **GCP Cloud Run**, triggered daily by **Cloud Scheduler** (with an in-process APScheduler cron as the timing backbone). It shares a single **PostgreSQL (Cloud SQL)** instance with STK — Watchman reads holdings and writes briefs; STK serves those briefs through its Brief tab. Secrets are managed in Secret Manager, and the daily brief is delivered by email via Resend.

---

## Local development

```bash
cp backend/.env.example backend/.env   # add your keys
docker compose up --build              # postgres + redis + backend
# Backend on http://localhost:8000  →  GET /health
```

Without Docker:

```bash
cd backend
pip install uv
uv pip install --system -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

---

> Part of the STK ecosystem — see [github.com/rosmitg/stk-portfolio-assistant](https://github.com/rosmitg/stk-portfolio-assistant).
