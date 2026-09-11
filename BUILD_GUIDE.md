# Agentic Build Guide

## Autonomous B2B Competitive Intelligence Engine — 5-Phase Development Pipeline

Breaking an autonomous, multi-service project into focused, bite-sized tasks is the exact way to avoid AI code bloat and hallucinated dependencies. When you ask an AI assistant to "build the whole app," it invents imaginary imports, skips edge-case handling, and produces unmaintainable code.

To build this cleanly in VS Code, treat the development process as a **5-Phase Linear Pipeline**. Each block has its own dedicated prompt that builds directly on the files created in the previous step.

---

## Step-by-Step Build Rules for Agentic Coding

1. **Never skip validation** — Run the verification check for the current phase before giving the agent the next prompt.
2. **Strict file scoping** — Always tell the AI the exact file paths to create or edit so it doesn't scatter files across unexpected directories.
3. **Keep context clean** — Open a new chat session in your agent for each phase, referencing only the relevant interfaces from earlier phases.

```
┌────────────────────────┐
│ Phase 1: Docker & Env  │ ──► Verify: All containers healthy in Coolify/local
└───────────┬────────────┘
            │
┌───────────▼────────────┐
│ Phase 2: DB & Schema   │ ──► Verify: Tables created, migrations run cleanly
└───────────┬────────────┘
            │
┌───────────▼────────────┐
│ Phase 3: LangGraph Core│ ──► Verify: CLI script returns validated battlecard JSON
└───────────┬────────────┘
            │
┌───────────▼────────────┐
│ Phase 4: API & Queue   │ ──► Verify: POST job -> SSE streams progress events
└───────────┬────────────┘
            │
┌───────────▼────────────┐
│ Phase 5: Next.js UI    │ ──► Verify: End-to-end user flow working in browser
└────────────────────────┘
```

---

## Phase 1: Environment & Infrastructure

**Goal:** Establish the root workspace, environment configuration, and local multi-container development environment.

### Prompt to Give Your Agent

> Act as a DevOps and Infrastructure Engineer. We are building a B2B Competitive Intelligence SaaS hosted on a VPS via Coolify, composed of Next.js 15, FastAPI, Celery, Redis, and PostgreSQL with pgvector.
>
> 1. Set up the root directory structure:
>    - `docker-compose.yml` (for local development and Coolify deployment)
>    - `.env.example` with placeholders for Postgres credentials, Redis URL, API keys (`GEMINI_API_KEY`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`), model strings (`LLM_FAST_MODEL`, `LLM_HEAVY_MODEL`), and auth secrets.
>    - `/backend` folder with a basic `Dockerfile` for Python 3.11.
>    - `/frontend` folder with a standard Next.js 15 standalone `Dockerfile`.
> 2. Ensure all services reside on an internal Docker bridge network `ci_network`.
> 3. Add sensible memory and CPU resource limits so the stack runs comfortably inside 8 GB total server RAM.
>
> Generate only the directory skeleton, `docker-compose.yml`, `backend/Dockerfile`, and `.env.example`.

### Verification Checklist Before Moving Forward

- [ ] Run `docker compose up -d postgres redis`
- [ ] Check container logs with `docker compose logs` to verify Postgres 16 (with pgvector) and Redis 7 start cleanly.

---

## Phase 2: PostgreSQL Database & Credit Ledger

**Goal:** Create the database models, async connection engine, and atomic credit deduction system.

### Prompt to Give Your Agent

> Act as a Backend Database Engineer. In the `/backend` directory:
>
> 1. Create a `pyproject.toml` or `requirements.txt` containing: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic`, `pgvector`.
> 2. Create `app/database.py` with an async SQLAlchemy 2.0 engine and session factory reading `DATABASE_URL` from the environment.
> 3. Create `app/models.py` defining SQLAlchemy models:
>    - `User`: `id` (UUID), `email` (unique), `name`, `created_at`
>    - `UserCredit`: `user_id` (FK), `balance` (default 5), `tier` ('free', 'starter'), `updated_at`
>    - `ResearchJob`: `id` (UUID), `user_id` (FK), `target_company`, `competitor`, `status` ('queued', 'running', 'completed', 'failed'), `cost_credits` (default 5), `created_at`
>    - `Battlecard`: `id` (UUID), `job_id` (FK, unique), `user_id` (FK), `target_company`, `competitor`, `report_data` (JSONB), `created_at`
> 4. Create `app/services/credit_service.py` containing an atomic function `deduct_credits(session, user_id, amount) -> bool` using `with_for_update()` to prevent double-spending or negative balances.
> 5. Provide an initial SQL script or Alembic migration to create these tables.
>
> Write clean, production-grade asynchronous Python code.

### Verification Checklist Before Moving Forward

- [ ] Run the migration against your local or VPS Postgres container.
- [ ] Connect with `psql` and confirm all tables and foreign keys exist.

---

## Phase 3: LangGraph Agent & Model Abstraction

**Goal:** Build the standalone AI agent engine that executes planning, search, scraping, verification, and JSON battlecard generation.

### Prompt to Give Your Agent

> Act as an AI Agent Engineer. We are building the core research pipeline inside `/backend/app/agents`.
>
> 1. In `app/core/llm.py`, create a model factory `get_chat_model(role: str = 'fast')` using LangChain's `init_chat_model` so models can be swapped via environment variables (`LLM_FAST_MODEL`, `LLM_HEAVY_MODEL`). It must work with Google GenAI (`google_genai:gemini-2.5-flash`), Anthropic, and OpenAI.
> 2. In `app/agents/schemas.py`, define Pydantic schemas for the final report:
>    - `PricingTier`: name, price, limitations, source_url
>    - `ChurnDriver`: pain_point, exact_quote, source_platform, source_url, objection_rebuttal
>    - `BattlecardOutput`: executive_summary, swot, pricing (List[PricingTier]), churn_drivers (List[ChurnDriver]), landmine_questions (List[str])
> 3. In `app/agents/ci_graph.py`, build a compiled LangGraph workflow with State `CIState`:
>    - `planner_node`: Generates targeted search sub-queries for pricing, G2 complaints, and product changelogs.
>    - `retriever_node`: Uses `tavily-python` for search and falls back gracefully if individual links fail.
>    - `verification_node`: Checks whether extracted content actually has pricing figures and review quotes. If missing, it adds targeted queries and loops back (max 2 retries).
>    - `synthesis_node`: Uses the heavy model with `.with_structured_output(BattlecardOutput)`.
> 4. Create a standalone test script `test_agent.py` that runs the graph for `Target: Linear` vs `Competitor: Jira` and prints the resulting JSON.
>
> Avoid placeholders. Deliver complete, working LangGraph code.

### Verification Checklist Before Moving Forward

- [ ] Run `python test_agent.py` in your terminal with your free `GEMINI_API_KEY` and `TAVILY_API_KEY`.
- [ ] Verify that the script outputs a fully formed JSON battlecard with valid source links.

---

## Phase 4: Celery Worker, Redis Pub/Sub, & Streaming API

**Goal:** Connect the LangGraph agent to asynchronous background workers and expose real-time SSE progress streams to the frontend.

### Prompt to Give Your Agent

> Act as a Distributed Systems and Backend Engineer. In the `/backend` directory:
>
> 1. Add `celery` and `redis` to dependencies.
> 2. Create `app/worker/celery_app.py` configuring Celery with Redis broker and result backend.
> 3. Create `app/worker/tasks.py` with a task `execute_research_job(job_id: str, target: str, competitor: str, user_id: str)`:
>    - It updates `research_jobs.status` in the DB.
>    - It runs the LangGraph compiled graph from Phase 3.
>    - As each node completes, it publishes progress messages (`{'step': 'planning'|'retrieving'|'verifying'|'synthesizing', 'msg': '...'}`) to a Redis Pub/Sub channel `job_progress:{job_id}`.
>    - Upon completion, it saves the final JSON to the `battlecards` table and marks the job status as `completed`.
> 4. In `app/main.py`, implement FastAPI routes:
>    - `POST /api/jobs/create`: Checks/deducts 5 user credits atomically, creates a `research_jobs` record, and dispatches the Celery task.
>    - `GET /api/jobs/{job_id}/stream`: An SSE (Server-Sent Events) endpoint that subscribes to `job_progress:{job_id}` and streams status updates to the client in real time.
>    - `GET /api/battlecards/{id}`: Returns the saved battlecard JSON.
>
> Ensure proper error handling if Celery or Redis drops a connection.

### Verification Checklist Before Moving Forward

- [ ] Start FastAPI (`uvicorn app.main:app`) and Celery (`celery -A app.worker.celery_app worker`).
- [ ] Trigger a test run via `curl -X POST /api/jobs/create`.
- [ ] Connect with `curl -N http://localhost:8000/api/jobs/{job_id}/stream` and verify you see real-time progress events streaming in.

---

## Phase 5: Next.js 15 Frontend & Real-Time Dashboard

**Goal:** Build the user-facing web app with Google OAuth, interactive sample previews, real-time agent tracking, and the battlecard report canvas.

### Prompt to Give Your Agent

> Act as a Senior Frontend & UI/UX Engineer. In the `/frontend` directory:
>
> 1. Set up a Next.js 15 App Router project with Tailwind CSS, Lucide React, and Shadcn UI components (Card, Button, Badge, Input, Tabs, Dialog, Progress).
> 2. Configure Auth.js / NextAuth with Google OAuth provider.
> 3. Build a Dashboard page (`/dashboard`):
>    - **Credit Tracker Header:** Displays current balance (default 5 free credits) and user profile.
>    - **Research Input Bar:** Inputs for 'Your Company', 'Competitor Name', and an 'Analyze' button.
>    - **Interactive Sample Gallery:** 2 clickable pre-rendered mock battlecards (e.g., Linear vs Jira) so visitors can explore the UI without spending their credit.
> 4. Build a Real-Time Agent Streamer Component:
>    - Listens to the FastAPI `/api/jobs/{job_id}/stream` endpoint via native `EventSource`.
>    - Shows a live multi-step progress bar (Planning -> Scraping -> Verifying Sources -> Synthesizing).
> 5. Build the Battlecard Presentation View:
>    - Pricing comparison table highlighting limitations and hidden costs.
>    - Churn drivers grid displaying exact customer quotes and rebuttal talk tracks.
>    - 'Export to Markdown' button and a clean print stylesheet for PDF exports.
>
> Make the UI clean, modern, and responsive. Use client components only where state/streaming is needed.

### Verification Checklist Before Moving Forward

- [ ] Sign in via Google OAuth.
- [ ] Submit a new competitor search.
- [ ] Verify the live progress steps animate in real time and smoothly transition to the final battlecard dashboard upon completion.

---

## How to Manage This Workflow in VS Code

1. Create a `SPEC.md` file in the root of your project containing the schemas, models, and architecture from your blueprint.
2. In your agent's instructions (e.g., in `.cursorrules`, agent instructions, or system context), add:
   > "Always refer to `SPEC.md` for variable names, database schema definitions, and model factory patterns. Never invent alternate naming conventions."
3. Feed the prompts one phase at a time. Only proceed to the next prompt after running the verification steps for the current one.
