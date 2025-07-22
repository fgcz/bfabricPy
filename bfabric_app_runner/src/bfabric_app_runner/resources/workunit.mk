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
.PHONY: help dispatch inputs process stage run-all clean check-runner

# Interpolated variables (when the Makefile was prepared):
PYTHON_VERSION := @PYTHON_VERSION@
APP_RUNNER_DEP_STRING := @APP_RUNNER_DEP_STRING@
USE_EXTERNAL_RUNNER := @USE_EXTERNAL_RUNNER@

# General set up
CONFIG_FILE := app_env.yml

# Dynamic runner command - uses exact version by default, optionally uses external runner
RUNNER_CMD := $(shell \
	if [ "$(USE_EXTERNAL_RUNNER)" = "true" ] && command -v bfabric-app-runner >/dev/null 2>&1; then \
		echo 'bfabric-app-runner'; \
	elif command -v uv >/dev/null 2>&1; then \
		echo 'uv tool run -p $(PYTHON_VERSION) $(APP_RUNNER_DEP_STRING)'; \
	else \
		echo 'bfabric-app-runner'; \
	fi)

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
	  printf "  make check-runner            - Verify bfabric-app-runner is available\n" && \
	  printf "\n" && \
	  printf "Other commands:\n" && \
	  printf "  make clean                   - Remove specified work directory\n" && \
	  printf "  make help                    - Show this help message\n" && \
	  printf "\n" && \
	  printf "Current settings:\n" && \
	  printf "  RUNNER_CMD = $(RUNNER_CMD)\n" && \
	  printf "  USE_EXTERNAL_RUNNER = $(USE_EXTERNAL_RUNNER) (set to 'true' to use external bfabric-app-runner from PATH)\n"

# Check if runner exists and is executable
check-runner:
	@if ! $(RUNNER_CMD) --version >/dev/null 2>&1; then \
		echo "❌ bfabric-app-runner not available."; \
		echo "💡 Install bfabric-app-runner or ensure 'uv' is available."; \
		exit 1; \
	else \
		echo "✓ Using runner command: $(RUNNER_CMD)"; \
	fi


# Step 1: Initial dispatch
dispatch: check-runner
	@$(MAKE) --always-make chunks.yml

chunks.yml: $(CONFIG_FILE)
	@echo "Step 1/4: Running initial dispatch..."
	$(RUNNER_CMD) action dispatch --config "$(CONFIG_FILE)"
	@echo "✓ Dispatch completed"

# Step 2: Prepare inputs
inputs: check-runner chunks.yml
	@echo "Step 2/4: Preparing inputs..."
	$(RUNNER_CMD) action inputs --config "$(CONFIG_FILE)"
	@echo "✓ Inputs prepared"

# Step 3: Process chunks
process: check-runner chunks.yml
	@echo "Step 3/4: Processing chunks..."
	$(RUNNER_CMD) action process --config "$(CONFIG_FILE)"
	@echo "✓ Processing completed"

# Step 4: Stage results
stage: check-runner chunks.yml
	@echo "Step 4/4: Staging results..."
	$(RUNNER_CMD) action outputs --config "$(CONFIG_FILE)"
	@echo "✓ Results staged"

# Run all steps in one command
run-all: check-runner chunks.yml
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
