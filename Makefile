# K8s IntelliBot - Development Makefile

.PHONY: help install install-dev run test lint format clean docker-build docker-run

# Default target
help:
	@echo "K8s IntelliBot - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  run           Run the interactive CLI"
	@echo "  test          Run test suite"
	@echo "  lint          Run linters"
	@echo "  format        Format code with black"
	@echo "  clean         Clean build artifacts"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run in Docker container"
	@echo "  validate      Validate cluster connection"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -e ".[dev]"

# Running
run:
	python -m src.main

run-debug:
	python -m src.main --debug

run-dry:
	python -m src.main --dry-run

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html

# Code quality
lint:
	ruff check src/ tests/
	black --check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

# Cleaning
clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Docker
docker-build:
	docker build -t k8s-intellibot:latest .

docker-run:
	docker-compose up k8s-bot

docker-dev:
	docker-compose --profile dev up k8s-bot-dev

docker-clean:
	docker-compose down -v
	docker rmi k8s-intellibot:latest k8s-intellibot:dev 2>/dev/null || true

# Validation
validate:
	python -m src.main validate

# Single query
ask:
	@echo "Usage: make ask QUERY='your question here'"
	@if [ -n "$(QUERY)" ]; then python -m src.main ask "$(QUERY)"; fi

# Contexts
contexts:
	python -m src.main contexts
