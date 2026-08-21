BACKEND  := backend
VENV_BIN := .venv/bin
COMPOSE  := docker compose

API_PORT := $(shell sed -n 's/^API_PORT=//p' .env 2>/dev/null | tail -1)
API_PORT := $(if $(API_PORT),$(API_PORT),58000)

REQUIRE_ENV = @test -f .env \
	|| { echo "error: .env is missing. Run: cp .env.example .env"; exit 1; }
REQUIRE_VENV = @test -x $(BACKEND)/$(VENV_BIN)/pytest \
	|| { echo "error: $(BACKEND)/.venv is missing or incomplete. Run:"; \
	     echo "  python -m venv $(BACKEND)/.venv"; \
	     echo "  $(BACKEND)/$(VENV_BIN)/pip install -r $(BACKEND)/requirements-dev.txt"; \
	     exit 1; }

.PHONY: dev test lint check

dev:
	$(REQUIRE_ENV)
	$(COMPOSE) up -d --build --wait
	$(COMPOSE) exec -T api alembic upgrade head
	@echo
	@echo "API      http://localhost:$(API_PORT)"
	@echo "Docs     http://localhost:$(API_PORT)/docs"
	@echo
	@echo "Logs     $(COMPOSE) logs -f api"
	@echo "Seed     $(COMPOSE) exec api python -m app.commands.seed"

test:
	$(REQUIRE_VENV)
	# Model/migration drift is invisible to the suite, which builds its schema
	# with create_all -- so it is checked here rather than only in `make check`.
	cd $(BACKEND) && $(VENV_BIN)/alembic check
	cd $(BACKEND) && $(VENV_BIN)/pytest

lint:
	$(REQUIRE_VENV)
	cd $(BACKEND) && $(VENV_BIN)/ruff check .

check:
	$(REQUIRE_VENV)
	cd $(BACKEND) && $(VENV_BIN)/python -m compileall -q app tests
	cd $(BACKEND) && $(VENV_BIN)/ruff check .
	cd $(BACKEND) && $(VENV_BIN)/alembic check
	cd $(BACKEND) && $(VENV_BIN)/pytest
