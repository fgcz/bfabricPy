# Makefile for bfabric-app-runner operations
#
# Quick Start Guide:
# -----------------
# For most cases, just run:
#     make run-all
#
# For step-by-step execution:
# 1. make dispatch              # Creates chunks.yml
# 2. make inputs WORK_DIR=dir   # Prepares input files
# 3. make process WORK_DIR=dir  # Processes the chunks in specified directory
# 4. make stage WORK_DIR=dir    # Stages results to server/storage
#
# Use `make help` to see all available commands

SHELL := /bin/bash
.PHONY: help dispatch inputs process stage run-all clean setup-runner check-runner clean-venv

# Interpolated variables (when the Makefile was prepared):
PYTHON_VERSION := @PYTHON_VERSION@
APP_RUNNER_DEP_STRING := @APP_RUNNER_DEP_STRING@

# General set up
CONFIG_FILE := app_env.yml
VENV_DIR := .venv

RUNNER_CMD := PATH="$(VENV_DIR)/bin:$$PATH" bfabric-app-runner

# Default target
help:
	@printf "Available commands:\n" && \
	  printf "  make run-all                 - Run all steps in a single command (recommended for most cases)\n" && \
	  printf "\n" && \
	  printf "Step-by-step execution:\n" && \
	  printf "  make dispatch                - Step 1: Initial step (creates chunks.yml)\n" && \
	  printf "  make inputs                  - Step 2: Prepare input files\n" && \
	  printf "  make process                 - Step 3: Process chunks in specified directory\n" && \
	  printf "  make stage                   - Step 4: Stage results to server/storage\n" && \
	  printf "\n" && \
	  printf "Environment management:\n" && \
	  printf "  make setup-runner            - Manually setup Python virtual environment\n" && \
	  printf "  make clean-venv             - Remove virtual environment\n" && \
	  printf "\n" && \
	  printf "Other commands:\n" && \
	  printf "  make clean                   - Remove specified work directory\n" && \
	  printf "  make help                    - Show this help message\n" && \
	  printf "\n" && \
	  printf "Current settings:\n" && \
	  printf "  RUNNER_CMD = $(RUNNER_CMD)\n" && \
	  printf "  PYTHON_VERSION = $(PYTHON_VERSION)\n" && \
	  printf "  VENV_DIR = $(VENV_DIR)\n"

# Check if runner exists and is executable, install if needed
check-runner:
	@if ! $(RUNNER_CMD) --version >/dev/null 2>&1; then \
		echo "❌ bfabric-app-runner not found in PATH or venv."; \
		echo "💡 Run 'make setup-runner' to install it locally."; \
		exit 1; \
	else \
		echo "✓ Using bfabric-app-runner from PATH"; \
	fi

# Setup the virtual environment and install the runner
setup-runner:
	@echo "🐍 Creating Python $(PYTHON_VERSION) virtual environment with uv in $(VENV_DIR)..."
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "❌ Error: uv not found. Please install uv first:"; \
		echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo "   or: pip install uv"; \
		exit 1; \
	fi
	uv venv $(VENV_DIR) --python $(PYTHON_VERSION)
	@echo "📦 Installing bfabric-app-runner..."
	uv pip install --python $(VENV_DIR)/bin/python $(APP_RUNNER_DEP_STRING)
	@echo "✅ bfabric-app-runner installed successfully in $(VENV_DIR)"

# Step 1: Initial dispatch
dispatch: check-runner
	@$(MAKE) --always-make chunks.yml

chunks.yml: check-runner
	@echo "Step 1/4: Running initial dispatch..."
	$(RUNNER_CMD) action dispatch --config "$(CONFIG_FILE)"
	@echo "✓ Dispatch completed"

# Step 2: Prepare inputs
inputs: chunks.yml
	@echo "Step 2/4: Preparing inputs..."
	$(RUNNER_CMD) action inputs --config "$(CONFIG_FILE)"
	@echo "✓ Inputs prepared"

# Step 3: Process chunks
process: chunks.yml
	@echo "Step 3/4: Processing chunks..."
	$(RUNNER_CMD) action process --config "$(CONFIG_FILE)"
	@echo "✓ Processing completed"

# Step 4: Stage results
stage: chunks.yml
	@echo "Step 4/4: Staging results..."
	$(RUNNER_CMD) action outputs --config "$(CONFIG_FILE)"
	@echo "✓ Results staged"

# Run all steps in one command
run-all: chunks.yml
	@echo "Running steps 2-4 in a single command..."
	$(RUNNER_CMD) action run-all --config "$(CONFIG_FILE)"
	@echo "✓ All steps completed"

# Clean generated files
clean:
	@if [ -n "$(WORK_DIR)" ]; then \
		echo "Cleaning directory '$(WORK_DIR)'..."; \
		rm -rf "$(WORK_DIR)"; \
		echo "✓ Clean completed for '$(WORK_DIR)'"; \
	else \
		echo "⚠️  WORK_DIR not specified. Use: make clean WORK_DIR=<directory>"; \
	fi

# Clean virtual environment
clean-venv:
	@echo "🧹 Removing virtual environment..."
	rm -rf $(VENV_DIR)
	@echo "✓ Virtual environment removed"
