# Developer command interface.
#
#   make dev     start the application (Postgres, Redis, API) and migrate
#   make test    run the test suite
#   make lint    run static checks
#   make check   run the full validation gate
#
# There is no second development environment here: the application runs through
# the existing docker-compose.yml, and the backend tooling runs from the
# existing backend/.venv. Settings are read from the repository-root .env by
# pydantic-settings, so no target needs to export environment variables.
#
# `test`, `lint` and `check` run on the host and expect the datastores to be up
# (`make dev`). They are not run inside the API container because the test suite
# creates its own database from TEST_DATABASE_URL, which addresses Postgres on
# the host-published port.

BACKEND  := backend
VENV_BIN := .venv/bin
COMPOSE  := docker compose

# The published API port, taken from .env so this never invents a port.
API_PORT := $(shell sed -n 's/^API_PORT=//p' .env 2>/dev/null | tail -1)
API_PORT := $(if $(API_PORT),$(API_PORT),58000)

# Fail early with an actionable message rather than a stack trace. .env is
# gitignored, so it is missing on a fresh clone; .venv likewise.
REQUIRE_ENV = @test -f .env \
	|| { echo "error: .env is missing. Run: cp .env.example .env"; exit 1; }
REQUIRE_VENV = @test -x $(BACKEND)/$(VENV_BIN)/pytest \
	|| { echo "error: $(BACKEND)/.venv is missing or incomplete. Run:"; \
	     echo "  python -m venv $(BACKEND)/.venv"; \
	     echo "  $(BACKEND)/$(VENV_BIN)/pip install -r $(BACKEND)/requirements-dev.txt"; \
	     exit 1; }

.PHONY: dev test lint check

## Start Postgres, Redis and the API, then bring the schema up to date.
dev:
	$(REQUIRE_ENV)
	$(COMPOSE) up -d --build --wait
	$(COMPOSE) exec -T api alembic upgrade head
	@echo
	@echo "API      http://localhost:$(API_PORT)"
	@echo "Docs     http://localhost:$(API_PORT)/docs"
	@echo "Health   http://localhost:$(API_PORT)/health/live"
	@echo
	@echo "Logs     $(COMPOSE) logs -f api"
	@echo "Seed     $(COMPOSE) exec api python -m app.commands.seed"

## Run the whole test suite. Requires the datastores from `make dev`.
test:
	$(REQUIRE_VENV)
	cd $(BACKEND) && $(VENV_BIN)/pytest

## Static checks.
lint:
	$(REQUIRE_VENV)
	cd $(BACKEND) && $(VENV_BIN)/ruff check .

## The full gate: compile, lint, migration drift, tests. Stops at the first
## failure - make aborts a recipe as soon as a line exits non-zero.
check:
	$(REQUIRE_VENV)
	cd $(BACKEND) && $(VENV_BIN)/python -m compileall -q app tests
	cd $(BACKEND) && $(VENV_BIN)/ruff check .
	cd $(BACKEND) && $(VENV_BIN)/alembic check
	cd $(BACKEND) && $(VENV_BIN)/pytest
