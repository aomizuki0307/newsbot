.PHONY: help setup run test lint clean

# Default target
help:
	@echo "newsbot - AI-powered article aggregation and generation tool"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup    - Install dependencies and setup environment"
	@echo "  make run      - Run the newsbot application"
	@echo "  make test     - Run unit tests with pytest"
	@echo "  make lint     - Run code linting with ruff"
	@echo "  make clean    - Clean generated files and cache"

# Setup: Install dependencies
setup:
	@echo "Setting up newsbot..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	@if not exist .env (copy .env.sample .env && echo ".env file created. Please configure it with your API keys.")
	@echo "Setup complete!"

# Run the application
run:
	@echo "Running newsbot..."
	python main.py

# Run tests
test:
	@echo "Running tests..."
	pytest -q

# Lint code
lint:
	@echo "Linting code..."
	ruff check src/ tests/ main.py

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@if exist cache.json del /f cache.json
	@if exist draft.md del /f draft.md
	@if exist newsbot.log del /f newsbot.log
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist src\__pycache__ rmdir /s /q src\__pycache__
	@if exist tests\__pycache__ rmdir /s /q tests\__pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@echo "Clean complete!"
