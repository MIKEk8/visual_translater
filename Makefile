# Screen Translator v2.0 - Makefile
# Cross-platform development automation

.PHONY: help install install-dev test test-unit test-integration test-coverage lint lint-fix build build-debug security clean ci setup docs

# Default target
help:
	@echo "Screen Translator v2.0 - Development Commands"
	@echo "=============================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup          - Initial project setup (install + dev dependencies)"
	@echo "  install        - Install production dependencies"
	@echo "  install-dev    - Install development dependencies"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint           - Run code quality checks"
	@echo "  lint-fix       - Fix code quality issues automatically"
	@echo "  security       - Run security scans"
	@echo ""
	@echo "Build Commands:"
	@echo "  build          - Build release executable"
	@echo "  build-debug    - Build debug executable"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  clean          - Clean build artifacts and cache"
	@echo "  ci             - Run full CI pipeline"
	@echo ""
	@echo "Documentation Commands:"
	@echo "  docs           - Generate documentation"
	@echo ""
	@echo "Alternative: Use build.py directly for more options"
	@echo "  python build.py --help"

# Setup commands
setup: install-dev
	@echo "✅ Project setup complete!"

install:
	python build.py install

install-dev:
	python build.py install --dev

# Testing commands
test:
	python build.py test

test-unit:
	python build.py test --type unit

test-integration:
	python build.py test --type integration

test-coverage:
	python build.py test --coverage

test-new:
	python run_tests.py all

test-core:
	python run_tests.py core

test-services:
	python run_tests.py services

test-models:
	python run_tests.py models

test-utils:
	python run_tests.py utils

# Code quality commands
lint:
	python build.py lint

lint-fix:
	python build.py lint --fix

security:
	python build.py security

# Build commands
build:
	python build.py build

build-debug:
	python build.py build --mode debug

# Maintenance commands
clean:
	python build.py clean

ci:
	python build.py ci

# Documentation commands (placeholder)
docs:
	@echo "📚 Documentation is in docs/ directory"
	@echo "Main files:"
	@echo "  docs/README.md       - User documentation"
	@echo "  docs/ARCHITECTURE.md - Technical architecture"
	@echo "  docs/ROADMAP.md      - Development roadmap"
	@echo "  docs/CHANGELOG.md    - Version history"

# Development workflow shortcuts
dev-setup: setup
	@echo "🚀 Development environment ready!"
	@echo ""
	@echo "Quick start:"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Check code quality"
	@echo "  make build         - Build application"
	@echo "  python main.py     - Run application"

dev-check: lint test
	@echo "✅ Development checks passed!"

dev-build: lint test build
	@echo "✅ Full development build completed!"

# Windows compatibility (if using GNU Make on Windows)
ifeq ($(OS),Windows_NT)
    PYTHON = python
else
    PYTHON = python3
endif

# Override python command if needed
ifdef PYTHON_CMD
    PYTHON = $(PYTHON_CMD)
endif