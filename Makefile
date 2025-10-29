# Makefile for Kindle OCR System
# Provides convenient commands for development, testing, and deployment

.PHONY: help build up down restart logs test migrate backup deploy clean

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(BLUE)Kindle OCR System - Makefile Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install Python dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)Dependencies installed successfully!$(NC)"

dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Development environment started!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Streamlit: http://localhost:8501"
	@echo "Docs: http://localhost:8000/docs"

dev-logs: ## View development logs
	docker-compose logs -f

dev-down: ## Stop development environment
	@echo "$(YELLOW)Stopping development environment...$(NC)"
	docker-compose down
	@echo "$(GREEN)Development environment stopped!$(NC)"

##@ Production

build: ## Build production Docker images
	@echo "$(BLUE)Building production images...$(NC)"
	docker-compose -f docker-compose.prod.yml build
	@echo "$(GREEN)Build complete!$(NC)"

up: ## Start production environment
	@echo "$(BLUE)Starting production environment...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)Production environment started!$(NC)"
	@$(MAKE) status

down: ## Stop production environment
	@echo "$(YELLOW)Stopping production environment...$(NC)"
	docker-compose -f docker-compose.prod.yml down
	@echo "$(GREEN)Production environment stopped!$(NC)"

restart: ## Restart production environment
	@$(MAKE) down
	@$(MAKE) up

logs: ## View production logs (all services)
	docker-compose -f docker-compose.prod.yml logs -f

logs-api: ## View API logs only
	docker-compose -f docker-compose.prod.yml logs -f api

logs-worker: ## View worker logs only
	docker-compose -f docker-compose.prod.yml logs -f worker

logs-beat: ## View beat scheduler logs only
	docker-compose -f docker-compose.prod.yml logs -f beat

status: ## Show production service status
	@echo "$(BLUE)Service Status:$(NC)"
	docker-compose -f docker-compose.prod.yml ps

##@ Database

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(NC)"

migrate-create: ## Create new migration (usage: make migrate-create MESSAGE="description")
	@echo "$(BLUE)Creating new migration...$(NC)"
	docker-compose -f docker-compose.prod.yml exec api alembic revision --autogenerate -m "$(MESSAGE)"
	@echo "$(GREEN)Migration created!$(NC)"

migrate-down: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	docker-compose -f docker-compose.prod.yml exec api alembic downgrade -1
	@echo "$(GREEN)Rollback complete!$(NC)"

migrate-history: ## Show migration history
	docker-compose -f docker-compose.prod.yml exec api alembic history

db-shell: ## Open PostgreSQL shell
	docker-compose -f docker-compose.prod.yml exec postgres psql -U kindle_user -d kindle_ocr

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest tests/ -v
	@echo "$(GREEN)Tests complete!$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest tests/integration/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated: htmlcov/index.html$(NC)"

lint: ## Run code linting
	@echo "$(BLUE)Running linter...$(NC)"
	flake8 app/ --max-line-length=100
	@echo "$(GREEN)Linting complete!$(NC)"

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	black app/ tests/
	@echo "$(GREEN)Formatting complete!$(NC)"

##@ Backup & Restore

backup: ## Create database backup
	@echo "$(BLUE)Creating database backup...$(NC)"
	@mkdir -p backups
	docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U kindle_user kindle_ocr | gzip > backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)Backup created in backups/ directory$(NC)"

backup-list: ## List available backups
	@echo "$(BLUE)Available backups:$(NC)"
	@ls -lh backups/*.sql.gz 2>/dev/null || echo "No backups found"

restore: ## Restore database from backup (usage: make restore BACKUP=backups/backup_20240101_120000.sql.gz)
	@echo "$(YELLOW)Restoring database from $(BACKUP)...$(NC)"
	@if [ -z "$(BACKUP)" ]; then echo "$(RED)Error: BACKUP parameter required$(NC)"; exit 1; fi
	gunzip -c $(BACKUP) | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U kindle_user kindle_ocr
	@echo "$(GREEN)Database restored!$(NC)"

##@ Deployment

deploy: ## Full deployment (build, migrate, start)
	@echo "$(BLUE)Starting full deployment...$(NC)"
	@$(MAKE) build
	@$(MAKE) up
	@sleep 10
	@$(MAKE) migrate
	@$(MAKE) status
	@echo "$(GREEN)Deployment complete!$(NC)"

scale-workers: ## Scale worker count (usage: make scale-workers COUNT=5)
	@echo "$(BLUE)Scaling workers to $(COUNT)...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d --scale worker=$(COUNT)
	@echo "$(GREEN)Workers scaled to $(COUNT)!$(NC)"

health-check: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo "API Health:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "$(RED)API not responding$(NC)"
	@echo "\nStreamlit Health:"
	@curl -s http://localhost:8501/_stcore/health || echo "$(RED)Streamlit not responding$(NC)"

##@ Monitoring

monitor: ## Open monitoring dashboards
	@echo "$(BLUE)Monitoring Dashboards:$(NC)"
	@echo "Grafana:    http://localhost:3000"
	@echo "Prometheus: http://localhost:9090"

metrics: ## Show Celery metrics
	docker-compose -f docker-compose.prod.yml exec worker celery -A app.tasks.celery_app inspect stats

celery-status: ## Show Celery worker status
	docker-compose -f docker-compose.prod.yml exec worker celery -A app.tasks.celery_app status

celery-purge: ## Purge all Celery tasks
	@echo "$(YELLOW)Purging all Celery tasks...$(NC)"
	docker-compose -f docker-compose.prod.yml exec worker celery -A app.tasks.celery_app purge -f
	@echo "$(GREEN)Tasks purged!$(NC)"

##@ Cleanup

clean: ## Clean up temporary files
	@echo "$(YELLOW)Cleaning up temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache/ .coverage htmlcov/
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-all: clean ## Clean everything (includes Docker volumes)
	@echo "$(RED)WARNING: This will delete all data including databases!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose -f docker-compose.prod.yml down -v; \
		rm -rf uploads/ captures/ logs/ backups/; \
		echo "$(GREEN)All data cleaned!$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled.$(NC)"; \
	fi

prune: ## Remove unused Docker resources
	@echo "$(YELLOW)Pruning Docker resources...$(NC)"
	docker system prune -f
	@echo "$(GREEN)Docker resources pruned!$(NC)"

##@ Documentation

docs: ## Generate API documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@echo "API documentation available at: http://localhost:8000/docs"
	@echo "ReDoc available at: http://localhost:8000/redoc"

api-test: ## Test API endpoints
	@echo "$(BLUE)Testing API endpoints...$(NC)"
	curl -X GET http://localhost:8000/health
	@echo ""

##@ Development Utilities

shell: ## Open Python shell in container
	docker-compose -f docker-compose.prod.yml exec api python

bash: ## Open bash shell in API container
	docker-compose -f docker-compose.prod.yml exec api bash

worker-shell: ## Open bash shell in worker container
	docker-compose -f docker-compose.prod.yml exec worker bash

psql: ## Open PostgreSQL interactive shell
	@$(MAKE) db-shell

redis-cli: ## Open Redis CLI
	docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $${REDIS_PASSWORD}

##@ Quick Start

quickstart: ## Quick start for new deployment
	@echo "$(BLUE)Quick Start - Kindle OCR System$(NC)"
	@echo "1. Creating .env file..."
	@if [ ! -f .env ]; then cp .env.example .env 2>/dev/null || echo "$(YELLOW)Please create .env file manually$(NC)"; fi
	@echo "2. Building images..."
	@$(MAKE) build
	@echo "3. Starting services..."
	@$(MAKE) up
	@echo "4. Running migrations..."
	@sleep 10
	@$(MAKE) migrate
	@echo ""
	@echo "$(GREEN)Quick start complete!$(NC)"
	@echo "$(BLUE)Access your application at:$(NC)"
	@echo "  API:       http://localhost:8000"
	@echo "  Docs:      http://localhost:8000/docs"
	@echo "  Streamlit: http://localhost:8501"
	@echo "  Grafana:   http://localhost:3000"
