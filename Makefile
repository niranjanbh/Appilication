# Kyros Platform — top-level Makefile
#
# This Makefile is the canonical entry point for all common dev workflows.
# Every target here is referenced from CLAUDE.md and the strategy docs.
# Add new targets sparingly; many shell commands are better off as scripts.

# ─── Configuration ───────────────────────────────────────────────────────────

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# Compose files
COMPOSE := docker compose
COMPOSE_TEST := docker compose -f docker-compose.test.yml

# Backend container shorthand (one-shot, removed on exit)
BACKEND_RUN := $(COMPOSE) run --rm backend-api

# Helpers
SAY = @printf "\033[1;36m→ %s\033[0m\n"
OK  = @printf "\033[1;32m✓ %s\033[0m\n"

# ─── Bootstrapping ───────────────────────────────────────────────────────────

.PHONY: bootstrap
bootstrap: ## First-clone setup: build, start postgres+redis, migrate, seed, then up
	@if [ ! -f backend/.env ]; then \
		cp backend/.env.example backend/.env; \
		echo "→ Created backend/.env from example. Edit it before first launch if you have real keys."; \
	fi
	$(SAY) "Building backend image (dev target)..."
	$(COMPOSE) build backend-api
	$(SAY) "Starting postgres + redis..."
	$(COMPOSE) up -d postgres redis
	$(SAY) "Waiting for postgres health..."
	@until $(COMPOSE) ps postgres | grep -q "healthy"; do sleep 1; done
	$(SAY) "Running migrations..."
	$(BACKEND_RUN) alembic upgrade head
	$(SAY) "Seeding development data..."
	$(BACKEND_RUN) python scripts/seed_dev.py
	$(SAY) "Starting all services..."
	$(COMPOSE) up -d
	@echo
	$(OK) "Kyros backend ready."
	@echo "    API:        http://localhost:8000"
	@echo "    Docs:       http://localhost:8000/docs"
	@echo "    Mailhog UI: http://localhost:8025"
	@echo "    Logs:       make logs"

.PHONY: build
build: ## Rebuild the backend image
	$(COMPOSE) build backend-api

# ─── Day-to-day ──────────────────────────────────────────────────────────────

.PHONY: dev
dev: ## Start all services in foreground (Ctrl-C stops)
	$(COMPOSE) up

.PHONY: up
up: ## Start all services detached
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop services (preserves volumes)
	$(COMPOSE) down

.PHONY: restart
restart: ## Restart backend + workers
	$(COMPOSE) restart backend-api celery-worker celery-beat

.PHONY: logs
logs: ## Tail logs from backend + workers
	$(COMPOSE) logs -f --tail=100 backend-api celery-worker celery-beat

.PHONY: logs-all
logs-all: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

.PHONY: ps
ps: ## Show service status
	$(COMPOSE) ps

# ─── Database ────────────────────────────────────────────────────────────────

.PHONY: migrate
migrate: ## Apply pending Alembic migrations
	$(BACKEND_RUN) alembic upgrade head

.PHONY: migrate-create
migrate-create: ## Generate a new migration (usage: make migrate-create m="add foo column")
	@if [ -z "$(m)" ]; then echo "ERROR: provide a message with m=\"...\""; exit 1; fi
	$(BACKEND_RUN) alembic revision --autogenerate -m "$(m)"
	@echo "→ Open the new migration in backend/alembic/versions/ and review before applying."

.PHONY: migrate-history
migrate-history: ## Show migration history
	$(BACKEND_RUN) alembic history --verbose

.PHONY: migrate-current
migrate-current: ## Show current migration head
	$(BACKEND_RUN) alembic current

.PHONY: migrate-downgrade-one
migrate-downgrade-one: ## Downgrade one migration (dev only; will refuse without confirmation)
	@printf "About to downgrade ONE migration in the dev DB. Continue? [y/N] "
	@read ans && [ "$$ans" = "y" ] || (echo "Aborted." && exit 1)
	$(BACKEND_RUN) alembic downgrade -1

.PHONY: migrate-prod
migrate-prod: ## Run migrations against production (requires explicit confirmation + env)
	@printf "About to apply migrations to PRODUCTION. Have you reviewed the migration files? [y/N] "
	@read ans && [ "$$ans" = "y" ] || (echo "Aborted." && exit 1)
	@if [ -z "$$KYROS_PROD_MIGRATE" ]; then \
		echo "ERROR: set KYROS_PROD_MIGRATE=1 to confirm this is intentional."; exit 1; \
	fi
	./infra/scripts/run-migration-prod.sh

.PHONY: seed
seed: ## Populate dev fixtures (idempotent)
	$(BACKEND_RUN) python scripts/seed_dev.py

.PHONY: create-super-admin
create-super-admin: ## Interactively create the first super admin user
	$(BACKEND_RUN) python scripts/create_super_admin.py

# ─── Testing ─────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run pytest in the test compose environment
	$(SAY) "Starting test services..."
	$(COMPOSE_TEST) up -d
	$(SAY) "Waiting for postgres-test..."
	@until $(COMPOSE_TEST) exec -T postgres-test pg_isready -U kyros >/dev/null 2>&1; do sleep 1; done
	$(SAY) "Running migrations on test DB..."
	cd backend && \
		KYROS_DATABASE_URL="postgresql+asyncpg://kyros:test@localhost:55432/kyros_test" \
		KYROS_JWT_SECRET="test_jwt_secret_minimum_32_characters_long_xxxx" \
		KYROS_OTP_SECRET="test_otp_secret_minimum_32_characters_long_yyyy" \
		uv run alembic upgrade head
	$(SAY) "Running tests..."
	cd backend && \
		KYROS_DATABASE_URL="postgresql+asyncpg://kyros:test@localhost:55432/kyros_test" \
		KYROS_REDIS_URL="redis://localhost:56379/0" \
		uv run pytest -v
	$(SAY) "Tearing down test services..."
	$(COMPOSE_TEST) down
	$(OK) "Tests passed."

.PHONY: test-watch
test-watch: ## Run pytest in watch mode (test compose must be up — see test-up)
	cd backend && \
		KYROS_DATABASE_URL="postgresql+asyncpg://kyros:test@localhost:55432/kyros_test" \
		KYROS_REDIS_URL="redis://localhost:56379/0" \
		uv run ptw

.PHONY: test-up
test-up: ## Bring up the test compose services (leave them up for fast iteration)
	$(COMPOSE_TEST) up -d

.PHONY: test-down
test-down: ## Tear down test compose
	$(COMPOSE_TEST) down

.PHONY: test-rbac
test-rbac: ## Run only the RBAC matrix test (fast feedback for endpoint scoping)
	cd backend && \
		KYROS_DATABASE_URL="postgresql+asyncpg://kyros:test@localhost:55432/kyros_test" \
		KYROS_REDIS_URL="redis://localhost:56379/0" \
		uv run pytest tests/integration/api/test_rbac_matrix.py -v

.PHONY: test-migrations
test-migrations: ## Run migration round-trip tests
	cd backend && \
		KYROS_DATABASE_URL="postgresql+asyncpg://kyros:test@localhost:55432/kyros_test" \
		uv run pytest tests/migration/ -v

# ─── Code quality ────────────────────────────────────────────────────────────

.PHONY: ruff
ruff: ## Run ruff on the backend
	cd backend && uv run ruff check app tests scripts

.PHONY: ruff-fix
ruff-fix: ## Run ruff with --fix on the backend
	cd backend && uv run ruff check --fix app tests scripts

.PHONY: format
format: ## Format backend code with ruff
	cd backend && uv run ruff format app tests scripts

.PHONY: mypy
mypy: ## Run mypy strict on the backend
	cd backend && uv run mypy app

.PHONY: lint
lint: ruff mypy ## Run all backend linters

# ─── Frontend ────────────────────────────────────────────────────────────────

.PHONY: install-frontend
install-frontend: ## Install all frontend deps (mobile, doctor-portal, website)
	cd mobile && pnpm install
	cd doctor-portal && pnpm install
	cd website && pnpm install

.PHONY: typecheck-frontend
typecheck-frontend: ## TypeScript check all three frontends
	cd mobile && pnpm typecheck
	cd doctor-portal && pnpm typecheck
	cd website && pnpm typecheck

.PHONY: build-frontend
build-frontend: ## Build all three frontends
	cd doctor-portal && pnpm build
	cd website && pnpm build
	# mobile build is per-platform (eas build); not run by default

.PHONY: build-web
build-web: ## Export the patient web portal (RNW) as a static site to mobile/dist/
	$(SAY) "Building patient web portal (React Native Web)…"
	cd mobile && pnpm build:web
	$(OK) "Static site written to mobile/dist/ — deploy to app.kyrosclinic.com via S3+CloudFront"
	@echo "  Deployment: aws s3 sync mobile/dist/ s3://kyros-web-portal --delete"
	@echo "  Then invalidate the CloudFront distribution cache."

.PHONY: openapi
openapi: ## Regenerate openapi.json from the running backend
	$(BACKEND_RUN) python scripts/generate_openapi.py
	@echo "→ openapi.json written to backend/openapi.json"
	@echo "→ Next: make generate-clients (to regenerate TS types for frontends)"

.PHONY: postman
postman: ## Regenerate the Postman collection from openapi.json
	@if [ ! -f backend/openapi.json ]; then echo "Run 'make openapi' first."; exit 1; fi
	cd backend && python3 scripts/openapi_to_postman.py

.PHONY: generate-clients
generate-clients: ## Regenerate TS API clients for frontends from openapi.json
	@if [ ! -f backend/openapi.json ]; then echo "Run 'make openapi' first."; exit 1; fi
	cd mobile && pnpm generate:api
	cd doctor-portal && pnpm generate:api

# ─── Shells ──────────────────────────────────────────────────────────────────

.PHONY: shell-backend
shell-backend: ## Open a bash shell inside the backend container
	$(COMPOSE) exec backend-api bash

.PHONY: shell-db
shell-db: ## Open psql against the dev database
	$(COMPOSE) exec postgres psql -U kyros -d kyros

.PHONY: shell-redis
shell-redis: ## Open redis-cli against dev Redis
	$(COMPOSE) exec redis redis-cli

.PHONY: shell-worker
shell-worker: ## Open a bash shell inside the celery worker container
	$(COMPOSE) exec celery-worker bash

# ─── Build prompts ───────────────────────────────────────────────────────────

.PHONY: extract-prompts
extract-prompts: ## Re-extract P1–P30 build prompts from the build spec
	python scripts/extract-build-prompts.py
	@echo "→ Per-prompt files refreshed in docs/build-prompts/"

# ─── Cleanup ─────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove pycache, build artifacts (non-destructive)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +
	find . -type d -name .mypy_cache -prune -exec rm -rf {} +

.PHONY: reset
reset: ## ⚠️ Destroy ALL volumes (dev DB + Redis) and re-bootstrap. Requires confirmation.
	@printf "\033[1;31mThis will DELETE the local dev database and Redis state. Continue? [y/N] \033[0m"
	@read ans && [ "$$ans" = "y" ] || (echo "Aborted." && exit 1)
	$(COMPOSE) down -v
	$(MAKE) bootstrap

# ─── Help ────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@echo "Kyros Platform — Makefile targets"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "Common flows:"
	@echo "  First time:        make bootstrap"
	@echo "  Daily work:        make dev      (or make up && make logs)"
	@echo "  After pull:        make migrate"
	@echo "  Run tests:         make test"
	@echo "  Extract prompts:   make extract-prompts"
	@echo "  Reset everything:  make reset"
