# Product & Technical Specification (SPEC.md)

## 1. Project Overview
* **Product Name:** Autonomous B2B Competitive Intelligence Engine
* **Core Function:** An autonomous research agent that deconstructs high-level B2B SaaS competitor topics into validated, citation-backed sales battlecards (pricing teardowns, verified churn complaints, and counter-objection hooks).
* **Target Audience:** Product Marketing Managers (PMMs), Founders, and Enterprise Sales/RevOps teams.
* **Target Environment:** Single Contabo VPS (4 vCPU, 8 GB RAM, 100 GB SSD) orchestrated via Coolify, reverse-proxied by Traefik with Cloudflare DNS/SSL.

---

## 2. Global Conventions & Project File Tree

### File Structure
```text
.
├── docker-compose.yml
├── .env.example
├── SPEC.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── llm.py
│       │   └── security.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── schemas.py
│       │   ├── nodes.py
│       │   └── ci_graph.py
│       ├── services/
│       │   ├── __init__.py
│       │   └── credit_service.py
│       └── worker/
│           ├── __init__.py
│           ├── celery_app.py
│           └── tasks.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.mjs
    ├── tailwind.config.ts
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx
        │   ├── dashboard/
        │   │   └── page.tsx
        │   └── api/
        │       └── auth/
        │           └── [...nextauth]/route.ts
        ├── components/
        │   ├── ui/
        │   ├── BattlecardView.tsx
        │   ├── StreamProgress.tsx
        │   └── DemoGallery.tsx
        └── lib/
            ├── auth.ts
            └── api.ts

```

---

## 3. Environment Variables Specification (`.env.example`)

```env
# Infrastructure & Database
POSTGRES_USER=ci_admin
POSTGRES_PASSWORD=replace_with_strong_password
POSTGRES_DB=ci_database
DATABASE_URL=postgresql+asyncpg://ci_admin:replace_with_strong_password@postgres:5432/ci_database
REDIS_URL=redis://redis:6379/0

# Security & Auth
JWT_SECRET=replace_with_32_byte_random_string
NEXTAUTH_URL=https://ci.yourdomain.com
NEXTAUTH_SECRET=replace_with_32_byte_random_string
GOOGLE_CLIENT_ID=replace_with_google_oauth_client_id
GOOGLE_CLIENT_SECRET=replace_with_google_oauth_client_secret

# AI Model Factory Routing (Format: provider:model_name)
LLM_FAST_MODEL=google_genai:gemini-2.5-flash
LLM_HEAVY_MODEL=google_genai:gemini-2.5-flash
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Retrieval APIs
TAVILY_API_KEY=tvly-...
FIRECRAWL_API_KEY=fc-...

# Client-Side Public Keys
NEXT_PUBLIC_API_URL=https://ci.yourdomain.com/api

```

---

## 4. Database Schema Specification (PostgreSQL + pgvector)

### Table: `users`

* `id`: `UUID` (Primary Key, default: `uuid_generate_v4()`)
* `email`: `VARCHAR(255)` (Unique, Indexed, Non-Nullable)
* `name`: `VARCHAR(255)` (Nullable)
* `image_url`: `TEXT` (Nullable)
* `created_at`: `TIMESTAMPTZ` (Default: `CURRENT_TIMESTAMP`)

### Table: `user_credits`

* `user_id`: `UUID` (Primary Key, FK -> `users.id` ON DELETE CASCADE)
* `balance`: `INTEGER` (Non-Nullable, Default: `5`)
* `tier`: `VARCHAR(50)` (Non-Nullable, Default: `'free'`) — Allowed: `'free'`, `'starter'`, `'growth'`
* `stripe_customer_id`: `VARCHAR(100)` (Nullable)
* `updated_at`: `TIMESTAMPTZ` (Default: `CURRENT_TIMESTAMP`)

### Table: `research_jobs`

* `id`: `UUID` (Primary Key, default: `uuid_generate_v4()`)
* `user_id`: `UUID` (FK -> `users.id` ON DELETE CASCADE, Indexed)
* `target_company`: `VARCHAR(100)` (Non-Nullable)
* `competitor`: `VARCHAR(100)` (Non-Nullable)
* `status`: `VARCHAR(50)` (Non-Nullable, Default: `'queued'`) — Allowed: `'queued'`, `'planning'`, `'retrieving'`, `'verifying'`, `'synthesizing'`, `'completed'`, `'failed'`
* `cost_credits`: `INTEGER` (Non-Nullable, Default: `5`)
* `error_log`: `TEXT` (Nullable)
* `created_at`: `TIMESTAMPTZ` (Default: `CURRENT_TIMESTAMP`)
* `completed_at`: `TIMESTAMPTZ` (Nullable)

### Table: `battlecards`

* `id`: `UUID` (Primary Key, default: `uuid_generate_v4()`)
* `job_id`: `UUID` (Unique, FK -> `research_jobs.id` ON DELETE CASCADE)
* `user_id`: `UUID` (FK -> `users.id` ON DELETE CASCADE, Indexed)
* `target_company`: `VARCHAR(100)` (Non-Nullable)
* `competitor`: `VARCHAR(100)` (Non-Nullable)
* `report_data`: `JSONB` (Non-Nullable, Conforms to `BattlecardOutput` schema)
* `created_at`: `TIMESTAMPTZ` (Default: `CURRENT_TIMESTAMP`)

### Transaction Constraint

* Credit deduction must use pessimistic row locking (`SELECT balance FROM user_credits WHERE user_id = :uid FOR UPDATE;`) to guarantee balances never drop below 0 or suffer race conditions.

---

## 5. Agent Architecture & LangGraph Specification

### Core State Schema (`AgentState`)

```python
class AgentState(TypedDict):
    target: str
    competitor: str
    sub_queries: List[str]
    scraped_content: List[Dict[str, str]] # [{'url': '...', 'content': '...'}]
    verified_corpus: str
    retries: int
    is_valid: bool
    final_output: Dict[str, Any]

```

### Model Factory Contract (`app/core/llm.py`)

Must expose:

```python
def get_chat_model(role: str = "fast") -> BaseChatModel

```

* Uses `langchain.chat_models.init_chat_model`.
* Dynamically parses `LLM_FAST_MODEL` and `LLM_HEAVY_MODEL` strings formatted as `provider:model_name`.
* Compatible with `google_genai`, `openai`, and `anthropic`.

### Target Deliverable Schema (`app/agents/schemas.py`)

```python
class PricingTier(BaseModel):
    name: str = Field(description="Name of the plan tier")
    price: str = Field(description="Normalized monthly cost or 'Contact Sales'")
    limitations: List[str] = Field(description="Excluded features or user seat minimums")
    source_url: str = Field(description="Direct URL to pricing or documentation")

class ChurnDriver(BaseModel):
    pain_point: str = Field(description="Core operational failure or reason for switching")
    exact_quote: str = Field(description="Verbatim user complaint from G2/Capterra/Reddit")
    source_platform: str = Field(description="e.g. G2, Capterra, Reddit")
    source_url: str = Field(description="Direct URL to the review")
    counter_pitch: str = Field(description="Actionable sales objection script")

class BattlecardOutput(BaseModel):
    target_company: str
    competitor: str
    executive_summary: str
    pricing: List[PricingTier]
    churn_drivers: List[ChurnDriver]
    landmine_questions: List[str] = Field(description="Questions to trap the competitor on sales calls")

```

### State Transitions & Termination Criteria

1. **`plan`**: Formulates 4 distinct sub-queries for competitor pricing, G2 complaints, Reddit sentiment, and updates.
2. **`retrieve`**: Executes Tavily search (`max_results=2` per query) + Firecrawl direct scrape on competitor `/pricing` (capped at 8,000 chars).
3. **`verify`**: Evaluates whether real pricing data and verifiable user complaints exist in the corpus.
   * If valid: Sets `is_valid = True` -> Transitions to `synthesize`.
   * If invalid and `retries < 2`: Increments `retries`, adds refined gap-query -> Loops to `retrieve`.
   * If invalid and `retries >= 2`: Sets `is_valid = False` -> Forces transition to `synthesize` (flags gaps in output).
4. **`synthesize`**: Runs `get_chat_model("heavy").with_structured_output(BattlecardOutput)` and saves results.

---

## 6. API, Task Queue & Real-Time Streaming Spec

### Endpoints

* `POST /api/jobs/create`
  * **Headers:** `Authorization: Bearer <jwt_token>`
  * **Body:** `{"target_company": "Linear", "competitor": "Jira"}`
  * **Process:** Locks credit ledger -> Deducts 5 credits -> Creates job row (`status='queued'`) -> Enqueues Celery task -> Returns `{"job_id": "uuid"}`.

* `GET /api/jobs/{job_id}/stream`
  * **Output:** Server-Sent Events (`text/event-stream`).
  * **Mechanism:** Subscribes to Redis Pub/Sub channel `job_progress:{job_id}`.
  * **Event Payload Schema:**
    ```json
    {"step": "planning|retrieving|verifying|synthesizing|completed|failed", "message": "Human readable status string", "data": null}

    ```

* `GET /api/battlecards/{job_id}`
  * **Headers:** `Authorization: Bearer <jwt_token>`
  * **Output:** Complete JSON payload from the `battlecards` table.

---

## 7. Frontend UI & UX Standards

* **Framework:** Next.js 15 (App Router) with React 19, TypeScript, Tailwind CSS, Shadcn UI.
* **Auth:** Google OAuth via NextAuth / Auth.js. Sessions verified against backend using signed JWT tokens.
* **Onboarding & Demo:**
  * Displays 2 pre-computed static battlecard previews (e.g., `Linear vs Jira` and `Supabase vs Firebase`) so users can test the dashboard prior to spending credits.
  * Live credit balance indicator prominently visible in top navigation.

* **Live Progress Engine:**
  * Uses browser-native `EventSource` on `/api/jobs/{job_id}/stream`.
  * Renders a 4-step interactive timeline that checks off steps as events arrive.

* **Battlecard Report Layout:**
  * Dynamic Tabbed / Card Interface:
    1. Executive Summary & SWOT
    2. Pricing Matrix & Hidden Traps
    3. Churn Drivers & Verified Review Quotations
    4. Sales Objection Battlecard & Landmine Questions
  * Actions: "Copy as Markdown" button and CSS `@media print` optimized for clean PDF exports.

---

## 8. VPS Resource Boundaries (Contabo 8 GB RAM)

To avoid Out-Of-Memory (OOM) crashes on Contabo, Docker containers must respect these limits:

| Container | CPU Limit | Memory Reservation | Memory Hard Limit |
| --- | --- | --- | --- |
| `ci_postgres` | 0.75 | 256M | 600M |
| `ci_redis` | 0.25 | 64M | 300M |
| `ci_backend` | 0.75 | 256M | 1024M |
| `ci_celery_worker` | 1.50 | 512M | 2500M |
| `ci_frontend` | 0.75 | 256M | 1024M |
| **System Overhead** | 0.25 | Remaining Free Buffer (~2.5 GB) |  |
