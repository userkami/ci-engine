# CI Engine — Autonomous B2B Competitive Intelligence

An autonomous agent that researches a competitor and generates a **citation-backed sales battlecard**: pricing teardowns, verified churn complaints, and counter-objection talk tracks — streamed to your browser in real time.

![Architecture](https://img.shields.io/badge/stack-Next.js_15_·_FastAPI_·_Celery_·_Redis_·_Postgres_16-blue)

## How it works

```
┌──────────┐   POST /api/jobs/create   ┌───────────────┐   LangGraph   ┌──────────────┐
│ Next.js  │ ────────────────────────► │   FastAPI     │ ────────────► │  Celery Worker│
│ (App Rtr)│    deduct 5 credits +     │  (SSE API)    │  enqueue job  │  (LangGraph)  │
└──────────┘    create research_job    └───────┬───────┘               └──────┬───────┘
       │                                       │                              │
       │  EventSource /api/jobs/{id}/stream    │        Redis Pub/Sub         │
       └───────────── progress ◄───────────────┴◄────── job_progress:{id} ◄──┘
                                               │
                                        battlecards (JSONB)
```

**Agent pipeline** (`planning → retrieving → verifying → synthesizing`): a fast LLM plans targeted queries, Tavily + Firecrawl retrieve pricing pages and G2/Capterra/Reddit reviews, a verification node checks for real pricing figures and quotable complaints (self-correcting loop, max 2 retries), then a heavy LLM synthesizes a structured battlecard with source URLs.

## Repository layout

```
├── docker-compose.yml        # 5 services on ci_network with 8GB-safe resource limits
├── .env.example              # all configuration (DB, Redis, LLM keys, auth secrets)
├── SPEC.md                   # full technical specification
├── BUILD_GUIDE.md            # phased build guide
├── backend/
│   ├── Dockerfile            # Python 3.11
│   ├── requirements.txt
│   ├── alembic/              # migrations (pgvector + 4 tables)
│   └── app/
│       ├── database.py       # async SQLAlchemy 2.0 engine
│       ├── models.py         # users · user_credits · research_jobs · battlecards
│       ├── main.py           # FastAPI: jobs, SSE stream, battlecards
│       ├── core/             # llm factory · redis client · security (JWT)
│       ├── agents/           # LangGraph pipeline (schemas, nodes, ci_graph)
│       ├── services/         # atomic credit ledger (SELECT ... FOR UPDATE)
│       └── worker/           # Celery app, tasks, progress publisher
└── frontend/
    ├── Dockerfile            # Next.js 15 standalone
    └── src/
        ├── app/              # dashboard, samples, battlecard viewer
        ├── components/       # stream progress, credit tracker, battlecard canvas
        └── lib/              # auth.js (Google OAuth), backend API client
```

## Quick start (local)

```powershell
cp .env.example .env        # fill in GEMINI_API_KEY, TAVILY_API_KEY, AUTH secrets, etc.

docker compose up -d postgres redis
docker compose run --rm backend alembic upgrade head
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| FastAPI | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### Run the agent standalone

```bash
cd backend
pip install -r requirements.txt
python test_agent.py        # Target: Linear vs Competitor: Jira → prints battlecard JSON
```

## Credits & billing model

Every user starts with **5 free credits**. One research job costs **5 credits**, deducted atomically (`SELECT ... FOR UPDATE` row locking — no double-spend). Failed dispatches are auto-refunded.

## Documentation

- [`SPEC.md`](./SPEC.md) — database schema, agent state machine, API contracts, VPS resource budget
- [`BUILD_GUIDE.md`](./BUILD_GUIDE.md) — 5-phase implementation guide (infra → DB → agent → queue → UI)

## Deployment

Designed for a single 4 vCPU / 8 GB VPS via [Coolify](https://coolify.io) — container CPU/memory limits are pre-tuned in [`docker-compose.yml`](./docker-compose.yml) (Postgres 600 MB · Redis 300 MB · backend 1 GB · worker 2.5 GB · frontend 1 GB).
