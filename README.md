# TWS E-Commerce API

Multi-tenant e-commerce SaaS backend. FastAPI, async SQLAlchemy on PostgreSQL,
Redis for caching and rate limiting.

> **Note:** a separate, further-along version of this project lives in
> `../ecommerce_1` (catalogue, cart, orders, inventory, payments). It is
> synchronous SQLAlchemy; this repository is the async rebuild. The shared core
> primitives here were ported from it.

---

## Quick start

```bash
cp .env.example .env                 # then edit the JWT secrets
docker compose up -d postgres redis

cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

alembic upgrade head
python -m app.commands.seed          # creates the Zeen tenant + admin user
uvicorn app.main:app --reload
```

API docs: <http://localhost:8000/docs>

To run the whole stack in Docker instead:

```bash
cp .env.example .env                              # then edit the JWT secrets
docker compose up -d --build                      # API on http://localhost:58000
docker compose exec api alembic upgrade head      # migrations do not run on boot
docker compose exec api python -m app.commands.seed
```

The image excludes `.env` on purpose, so the API container is configured by
`env_file: .env` in `docker-compose.yml`. Everything the app reads must live in
the repository-root `.env`.

Host ports are namespaced (`55432` Postgres, `56379` Redis, `58000` API) so this
stack does not collide with other local projects.

## Tests

```bash
cd backend && pytest
```

The suite runs against a real PostgreSQL database — the constraints it checks
(composite uniqueness, the role check, `ON DELETE CASCADE`) are database
behaviour that SQLite would not reproduce. It creates and drops
`TEST_DATABASE_URL` automatically, so Postgres must be running.

```bash
ruff check .        # lint
```

---

## Architecture

```
app/
  api/v1.py        Router aggregation - the only place routes are mounted
  core/            Cross-cutting primitives, no dependency on feature modules
    config          Typed settings; refuses weak secrets in production
    database        Async engine, explicit pool sizing, session dependency
    repository      BaseRepository / TenantScopedRepository
    responses       {success, message, data, meta} envelope
    exceptions      AppError hierarchy -> error envelope
    tenant_context  The resolved tenant for a request
    cache           Async Redis client
    rate_limit      Fixed-window limiter
    logging         Request-id correlation
    pagination      Shared page/page_size inputs
  auth/            Login, registration, refresh, guards
  tenants/         Tenant model, repository, public resolution
  users/           User model and repository
  models/base.py   Declarative base + naming convention + timestamps
```

**Layering.** `router -> service -> repository`. Routers resolve dependencies and
wrap results in the envelope. Services own the business transaction and commit.
Repositories do data access only and never commit.

### Tenancy

Tenant isolation is structural, not conventional:

- `TenantScopedRepository` cannot be constructed without a `TenantContext`.
- Every read starts from a tenant-filtered `SELECT`.
- Every write stamps the context's tenant id over whatever the caller supplied.
- A row belonging to another tenant is indistinguishable from a missing row, so
  ids cannot be used to probe for existence across tenants.

Authenticated requests take the tenant from the **authenticated user**, never
from a header. `X-Tenant-Slug` resolves the tenant for *public* storefront
traffic only, and cannot widen an authenticated caller's scope.

New tenant-owned models should extend `TenantScopedRepository`. That is the one
rule that keeps cross-tenant leaks from becoming likely as the schema grows.

### Responses

Success:

```json
{ "success": true, "message": "OK", "data": {}, "meta": null }
```

Error (every path, including validation and unhandled exceptions):

```json
{ "success": false, "message": "...",
  "error": { "code": "NOT_FOUND", "details": [], "request_id": "..." } }
```

Build responses with `ok()` / `paginated()`. Raise `AppError` subclasses in
services; the handlers in `main.py` convert them. Nothing returns a stack trace
to a client, and `request_id` correlates a response with its server-side logs.

### Health

- `GET /health` — liveness. Touches no dependency, so a brief datastore outage
  does not get the process restarted.
- `GET /health/ready` — readiness. Checks PostgreSQL and Redis; returns 503 when
  either is down, so a load balancer stops routing to this instance.

---

## Operational notes

**Password hashing.** Argon2id costs ~250–340ms of CPU per call and runs in a
worker thread (`anyio.to_thread`), never inline on the event loop. Inline, a
single login would freeze every other in-flight request on that worker. Argon2
releases the GIL, so hashes do run in parallel — but only sub-linearly (measured
~2.2x across 8 threads, since Argon2 is memory-bandwidth bound). If login
throughput becomes a bottleneck, tune the Argon2 cost parameters or isolate auth
onto its own worker pool; do not move hashing back onto the loop.

**Connection pool.** `DB_POOL_SIZE + DB_MAX_OVERFLOW` connections **per worker
process**. Four Uvicorn workers at the defaults is 60 connections against a
default `max_connections` of 100. Size these deliberately and put PgBouncer in
front before scaling out.

**Rate limiting.** Login is throttled per (client IP, tenant, account). The
limiter fails **open** if Redis is unreachable: a cache outage degrades
brute-force protection rather than taking authentication down. Behind a reverse
proxy, run Uvicorn with `--proxy-headers` or the client IP will be the proxy's.

**Tokens.** Access and refresh tokens are signed with **separate** secrets, so a
leaked access secret cannot mint refresh tokens. Tokens carry `tid`, but the
tenant is always re-validated server-side — the claim is never the authority.

## Known gaps

- **Refresh tokens are stateless.** There is no server-side revocation and no
  logout: a refresh token stays valid until it expires. Rotation with reuse
  detection needs a `refresh_tokens` table and is not implemented here.
- **No caching layer.** Redis is wired up but only backs the readiness probe and
  the rate limiter. Every authenticated request still costs one database query
  to load the user (a single joined query, not two).
- **No CI pipeline.** `pytest` and `ruff` both pass but nothing runs them
  automatically.
- **`requirements.txt` is not a lockfile.** Direct dependencies are pinned;
  transitive ones are not. Generate a real lock (`pip-compile` / `uv`) before
  production.
