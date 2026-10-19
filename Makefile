.PHONY: help env setup build up down logs ps migrate seed test lint fmt backend-shell db-shell reset fe-install fe-dev fe-lint fe-typecheck fe-build fe-test fe-test-coverage fe-e2e fe-e2e-up

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.example (if missing)
	@test -f .env || (cp .env.example .env && echo "Created .env — review it, then 'make up'")

setup: env ## Create backend venv and install dev dependencies
	cd backend && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

build: ## Build all images
	docker compose build

up: env ## Start the full stack (build if needed)
	docker compose up -d --build

down: ## Stop the stack
	docker compose down

logs: ## Tail logs
	docker compose logs -f --tail=100

ps: ## Show service status
	docker compose ps

migrate: ## Run database migrations
	docker compose run --rm migrate

seed: ## Seed demo data (idempotent)
	docker compose run --rm backend python -m app.seed

test: ## Run backend tests (needs a Postgres on TEST_PG_PORT, default 5432)
	cd backend && ./.venv/bin/python -m pytest -q

lint: ## Ruff check (backend)
	cd backend && ./.venv/bin/ruff check app tests

fmt: ## Ruff format + fix (backend)
	cd backend && ./.venv/bin/ruff format app tests && ./.venv/bin/ruff check --fix app tests

backend-shell: ## Shell inside the backend container
	docker compose exec backend sh

db-shell: ## psql inside the database container
	docker compose exec db psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-railway}

reset: ## Stop and delete volumes (destroys all data)
	docker compose down -v

fe-install: ## Install frontend dependencies (npm)
	cd frontend && npm install

fe-dev: ## Run the frontend dev server (needs the stack up for the API)
	cd frontend && npm run dev

fe-lint: ## ESLint (frontend)
	cd frontend && npm run lint

fe-typecheck: ## TypeScript check (frontend)
	cd frontend && npm run typecheck

fe-build: ## Production build (frontend, standalone output)
	cd frontend && npm run build

fe-test: ## Vitest unit/component tests (frontend)
	cd frontend && npm run test

fe-test-coverage: ## Vitest with coverage thresholds (frontend)
	cd frontend && npm run test:coverage

fe-e2e-up: ## Start the stack for E2E on :8095 (permissive rate limits)
	HTTP_PORT=8095 HTTPS_PORT=8495 docker compose up -d --build

fe-e2e: ## Playwright E2E against the stack on :8095 (see fe-e2e-up)
	cd frontend && npm run e2e
