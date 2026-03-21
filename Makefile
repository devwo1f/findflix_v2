.PHONY: help up down dev logs backend-logs ml-logs test seed migrate clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

dev: ## Start in development mode with hot-reload
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

logs: ## Tail all service logs
	docker compose logs -f

backend-logs: ## Tail backend logs
	docker compose logs -f backend

ml-logs: ## Tail ML service logs
	docker compose logs -f ml_service

test-backend: ## Run backend tests
	cd backend && python -m pytest -v

test-ml: ## Run ML service tests
	cd ml_service && python -m pytest -v

test-app: ## Run Flutter tests
	cd app && flutter test

test: test-backend test-ml test-app ## Run all tests

seed: ## Seed the database
	docker compose exec backend python -m app.db.seed

migrate: ## Run database migrations
	docker compose exec backend alembic upgrade head

clean: ## Remove all containers and volumes
	docker compose down -v --remove-orphans

flutter-run-web: ## Run Flutter app on web
	cd app && flutter run -d chrome

flutter-run-ios: ## Run Flutter app on iOS
	cd app && flutter run -d ios

flutter-build-web: ## Build Flutter web app
	cd app && flutter build web
