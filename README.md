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
python -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt

make dev
```

API docs: <http://localhost:58000/docs>. To create the Zeen tenant and its admin
user, run the seed once:

```bash
docker compose exec api python -m app.commands.seed
```

## Development commands

Run from the repository root — no need to `cd` anywhere.

| Command | What it does |
|---|---|
| `make dev` | Starts Postgres, Redis and the API, waits for health, applies migrations |
| `make test` | Runs the full test suite |
| `make lint` | Runs `ruff` static checks |
| `make check` | Full gate: compile, lint, migration drift (`alembic check`), tests |

`test`, `lint` and `check` run on the host from `backend/.venv` and expect the
datastores to be running, so start with `make dev`. They are deliberately not
run inside the API container: the suite creates its own database from
`TEST_DATABASE_URL`, which addresses Postgres on the host-published port.

Any failing step exits non-zero, and `make check` stops at the first failure.

The test suite runs against a real PostgreSQL database — the constraints it
checks (composite uniqueness, the role check, `ON DELETE CASCADE`) are database
behaviour that SQLite would not reproduce. It creates and drops
`TEST_DATABASE_URL` automatically.

The image excludes `.env` on purpose, so the API container is configured by
`env_file: .env` in `docker-compose.yml`. Everything the app reads must live in
the repository-root `.env`.

Host ports are namespaced (`55432` Postgres, `56379` Redis, `58000` API) so this
stack does not collide with other local projects. Migrations do not run on
container boot; `make dev` applies them.

---

## Architecture

```
app/
  api/v1.py        Router aggregation - the only place routes are mounted
  core/            Cross-cutting concerns, no dependency on feature modules
    config          Typed settings; refuses weak secrets in production
    database        Async engine, explicit pool sizing, session dependency
    repository      Tenant-scoped repository base for tenant-owned models
    responses       {success, message, data, meta} envelope
    pagination      ?page=&page_size= convention for list endpoints
    exceptions      AppError hierarchy -> error envelope
    cache           Async Redis client
    rate_limit      Fixed-window limiter (per-account and per-IP)
    logging         Request-id correlation
    request_context Sanitised request id, client IP
  auth/            Login, registration, refresh/rotation, logout, permissions
  tenants/         Tenant model and repository
  users/           User model and repository
  models/          Declarative base, timestamps, Alembic model registry
  commands/        Operational entry points (seed)
```

**Layering.** `router -> service -> repository`. Routers resolve dependencies and
wrap results in the envelope. Services own the business transaction and commit.
Repositories are plain classes that run queries - no business rules, no commits,
no base class. Add an abstraction when a third caller needs it, not before.

### Tenancy

Shared database, shared schema, `tenant_id` column. Every user query is keyed on
`(tenant_id, email)`, never email alone, and the composite unique index
`uq_users_tenant_email` is what makes that exact.

The authenticated tenant comes from the **user row** — never from a header, a
query parameter, a request body, or the JWT's `tid` claim. `test_tenancy.py`
covers all four of those override attempts.

Tenant-owned models (catalogue, inventory, orders, carts…) extend
`TenantScopedRepository` in `core/repository.py`. It cannot be constructed
without a tenant id, every read starts from a tenant-filtered `SELECT`, and
`add()` overwrites whatever `tenant_id` the caller set — so a value taken from a
request body cannot place a row in another tenant. `users` and `tenants` do
**not** use it: authentication has to find a user before a tenant is known.

### Authorization

Roles map to permissions in code (`auth/permissions.py`); there is no
database-driven permission model and no permission CRUD. Routes declare what
they need:

```python
@router.post("/products", dependencies=[Depends(require_permission(Permission.CATALOGUE_CREATE))])
```

| Role | Scope | Holds |
|---|---|---|
| `PLATFORM_ADMIN` | `tenant_id IS NULL` | platform operations only |
| `TENANT_ADMIN` | one tenant | all tenant permissions |
| `STAFF` | one tenant | read catalogue, move stock and orders |
| `CUSTOMER` | one tenant | no back-office permission |

The role is read from the **database row**, never from the JWT `role` claim, so
a forged or stale token cannot grant it (`test_rbac.py`). Public registration
always creates a `CUSTOMER` — the role is not accepted from the request body.

### Pagination

List endpoints take `?page=1&page_size=20` (`page_size` capped at 100) via the
`page_params` dependency, and return the page window in `meta`:

```json
{ "success": true, "message": "OK", "data": [],
  "meta": { "page": 1, "page_size": 20, "total_items": 0, "total_pages": 0 } }
```

Build them with `paginated()`. Cursor pagination solves a different problem and
can be added for a specific endpoint that actually needs it.

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

- `GET /health/live` — liveness. Touches no dependency, so a brief datastore
  outage does not get the process restarted. This is what the container
  healthcheck uses.
- `GET /health/ready` — readiness. **Only PostgreSQL decides**: it returns 503
  when the database is unreachable, so a load balancer stops routing here.
  Redis is reported as `degraded` rather than failing readiness — rate limiting
  degrades on its own, and pulling every instance out of the load balancer over
  it would cause the outage it is trying to avoid. The response also reports
  connection-pool saturation (`size`, `checked_out`, `overflow`).

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

**Rate limiting.** Login carries **two** budgets, because they stop different
attacks: per (IP, tenant, account) stops one account being brute-forced, and
per (IP, tenant) stops one source spraying a password across many accounts —
which the per-account counter cannot see, since each account has its own. A
successful login clears only the account budget. The limiter fails **open** if
Redis is unreachable: a cache outage degrades brute-force protection rather than
taking authentication down.

**Behind a proxy.** The client IP is taken from `request.client`, never by
parsing `X-Forwarded-For` — that header is attacker-controlled, and trusting it
would let one source rotate its apparent IP past the limiter. Uvicorn rewrites
`request.client` from forwarded headers only for peers listed in
`FORWARDED_ALLOW_IPS` (default `127.0.0.1`). **Set it to your load balancer's
address on deploy**, or every request will share one rate-limit bucket.

**Observability.** One structured log line per request carries method, path,
status and `duration_ms`, correlated by request id — that is request rate,
latency and error rate in one place. Uvicorn's own access log is silenced so
requests are not logged twice.

**Tokens.** Access and refresh tokens are signed with **separate** secrets, so a
leaked access secret cannot mint refresh tokens. Tokens carry `tid`, but the
tenant is always re-validated server-side — the claim is never the authority.

## Authentication

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/register` | Create a `CUSTOMER` in a tenant |
| `POST /api/v1/auth/login` | Exchange credentials for an access/refresh pair |
| `POST /api/v1/auth/refresh` | Rotate a refresh token |
| `POST /api/v1/auth/logout` | Revoke a refresh token |
| `GET /api/v1/auth/me` | The authenticated user |

`tenant_slug` is a **body field** on `login` and `register` — a user is
identified by (tenant, email), so the tenant is part of the credential.

**Refresh token rotation.** Tokens are stored as SHA-256 hashes in
`refresh_tokens` (never in the clear) and are **single-use**: refreshing spends
the presented token and issues a new pair. Replaying an already-rotated token
means two parties hold it, and since the server cannot tell the legitimate
client from a thief, **every session for that user is revoked**. Logout is
deliberately silent about unknown, expired or already-revoked tokens so it
cannot become an oracle for which tokens are valid.

SHA-256 rather than Argon2 for these: the token is already 256+ bits of signed
random data, so there is nothing to brute-force, and revocation needs a
deterministic lookup key that a salted hash could not provide.

## Environment variables

Everything is read from the environment; see `.env.example` for the full set
with comments. The ones that matter most:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…`. Compose overrides it with in-network hostnames |
| `REDIS_URL` | Rate limiting and readiness reporting only — never business data |
| `JWT_SECRET` / `JWT_REFRESH_SECRET` | Must differ. In production, must be ≥32 chars and not a placeholder, or the app refuses to start |
| `CORS_ORIGINS` | Comma-separated. Empty means none; `*` is refused in production |
| `DOCS_ENABLED` | Unset means "on outside production". Set explicitly to force either way |
| `FORWARDED_ALLOW_IPS` | Trusted proxy address. Leave unset unless behind a load balancer |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | **Per worker process** — see the pool note above |
| `DB_STATEMENT_TIMEOUT_SECONDS` | Server-side cap so one query cannot hold a pooled connection open |

## Known gaps

- **Platform admins cannot log in.** `login` resolves a user by (tenant, email)
  and a `PLATFORM_ADMIN` has no tenant, so the tenant-scoped login endpoint
  cannot authenticate one. There are no platform operations yet; when they are
  built they will need their own login path.
- **No caching layer.** Redis is wired up but only backs the readiness probe and
  the rate limiter. Every authenticated request still costs one database query
  to load the user (a single joined query, not two).
- **No CI pipeline.** `make check` is the complete gate and passes, but nothing
  runs it automatically on push.
- **`requirements.txt` is not a lockfile.** Direct dependencies are pinned;
  transitive ones are not. Generate a real lock (`pip-compile` / `uv`) before
  production.
