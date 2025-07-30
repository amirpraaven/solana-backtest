.PHONY: help install dev-install test test-cov lint format clean run-dev run-prod docker-build docker-up docker-down db-init db-migrate

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov pytest-mock black isort flake8 mypy

test: ## Run tests
	pytest tests/

test-cov: ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

lint: ## Run linters
	flake8 src/ tests/
	mypy src/
	isort --check-only src/ tests/
	black --check src/ tests/

format: ## Format code
	isort src/ tests/
	black src/ tests/

clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

run-dev: ## Run development server
	uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run production server
	uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 4

docker-build: ## Build Docker image
	docker-compose build

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

db-init: ## Initialize database
	docker-compose up -d postgres
	sleep 5
	docker-compose exec postgres psql -U postgres -f /docker-entrypoint-initdb.d/init.sql

db-shell: ## Open database shell
	docker-compose exec postgres psql -U postgres -d solana_backtest

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

migrate: ## Run database migrations (placeholder)
	@echo "Database migrations not implemented yet"

env-setup: ## Copy .env.example to .env
	cp .env.example .env
	@echo "Please edit .env with your API keys and configuration"

check-env: ## Check if required environment variables are set
	@test -n "$$HELIUS_API_KEY" || (echo "HELIUS_API_KEY not set" && exit 1)
	@test -n "$$BIRDEYE_API_KEY" || (echo "BIRDEYE_API_KEY not set" && exit 1)
	@echo "Environment variables OK"