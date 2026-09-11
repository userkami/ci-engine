# Deploy CI Engine with Coolify

Use a **Git-based Application** with the **Docker Compose** build pack.
Repository: https://github.com/userkami/ci-engine
Compose file: `/docker-compose.coolify.yml`. Base directory: `/`.
The deployment must use a branch containing these deployment changes.

## Domain and Google login

1. Point your chosen hostname's DNS A record to the VPS IP. Only add an AAAA record if IPv6 is configured on the VPS.
2. In Coolify, load the Compose file and assign **only frontend** a domain such as `https://ci.example.com:3000`. The `:3000` selects the internal container port; users visit `https://ci.example.com`.
3. Set `NEXTAUTH_URL=https://ci.example.com` (no port 3000).
4. In Google Cloud, configure a Web application OAuth client with origin `https://ci.example.com` and redirect URI `https://ci.example.com/api/auth/callback/google`. If the consent screen is in testing mode, add your sign-in account as a test user.

## Coolify environment variables

Set these as runtime variables; the frontend does not need secrets at build time.
Do not commit real secrets or upload your local `.env` to Git.

| Variable | Value |
| --- | --- |
| `POSTGRES_PASSWORD` | Independently generated 64-character hexadecimal secret. Hex avoids URL escaping problems in DATABASE_URL. |
| `JWT_SECRET` | Independently generated 64-character hexadecimal secret. |
| `INTERNAL_API_SECRET` | Independently generated 64-character hexadecimal secret, shared by frontend and backend through Compose. |
| `NEXTAUTH_SECRET` | Independently generated 64-character hexadecimal secret. |
| `NEXTAUTH_URL` | Public HTTPS origin, without trailing slash. |
| `GOOGLE_CLIENT_ID` | Google Web OAuth client ID. |
| `GOOGLE_CLIENT_SECRET` | Matching Google client secret. |
| `GEMINI_API_KEY` | Required with the default Gemini models. |
| `TAVILY_API_KEY` | Required for research. |
| `FIRECRAWL_API_KEY` | Optional; retrieval can use Tavily content. |

Generate each secret separately in your password manager, or on the VPS with `openssl rand -hex 32`.
Optional `LLM_FAST_MODEL` and `LLM_HEAVY_MODEL` default to `google_genai:gemini-2.5-flash`.
If selecting OpenAI or Anthropic, supply the matching `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` instead.
Database and Redis connection URLs and `BACKEND_PROXY_URL` are already set in Compose.

## Deploy and verify

Deploy after saving the domain and variables. The backend runs `alembic upgrade head` before starting the API; the worker waits for the API health check.
Check that all services start, then visit `/api/health` on the public domain and sign in with Google.
Run one research job (it spends five credits and uses paid provider APIs). Confirm live progress, the final report, and Markdown export.
Check the public `/api/auth/provision` and `/api/backend/auth/provision` paths are unavailable; backend provisioning requires the internal secret even on the private network.

Only the frontend receives a domain. No service publishes a host port. Keep PostgreSQL, Redis, and backend without domains, and do not attach unrelated applications to their network.
Allow the standard HTTP/HTTPS ports to reach Coolify's proxy.

## Operations and limitations

Named volumes persist PostgreSQL and Redis data across redeploys. Set up PostgreSQL backups outside the VPS and test restore before relying on the app for important data. Do not delete the volumes to redeploy.
Changing POSTGRES_PASSWORD after first initialization does not change the existing database user's password; rotate it in PostgreSQL and update Coolify together.
The configured runtime memory limits total about 5.4 GB. Leave room for Coolify, the OS, and image builds; 8 GB RAM is a reasonable starting point, but build memory is additional.

This deployment preparation is not a complete production reliability audit. Billing/top-ups and saved-job history are not implemented. Worker retry/credit transaction edge cases and citation validation described in the project review still need work. Start with a limited pilot and verify provider costs and report quality.

References: [Coolify Docker Compose](https://coolify.io/docs/applications/builds/docker-compose), [domain configuration](https://coolify.io/docs/applications/configuration/general).
