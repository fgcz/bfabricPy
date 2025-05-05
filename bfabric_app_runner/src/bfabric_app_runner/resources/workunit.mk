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

RUNNER_CMD := bfabric-app-runner-uv exec --work-dir .

.PHONY: help dispatch inputs process stage run-all clean

# Default target
help:
	@set -a && . .env && set +a && \
	  printf "Available commands:\n" && \
	  printf "  make run-all                 - Run all steps in a single command (recommended for most cases)\n" && \
	  printf "\n" && \
	  printf "Step-by-step execution:\n" && \
	  printf "  make dispatch                - Step 1: Initial step (creates chunks.yml)\n" && \
	  printf "  make inputs [WORK_DIR=dir]   - Step 2: Prepare input files\n" && \
	  printf "  make process [WORK_DIR=dir]  - Step 3: Process chunks in specified directory\n" && \
	  printf "  make stage [WORK_DIR=dir]    - Step 4: Stage results to server/storage\n" && \
	  printf "\n" && \
	  printf "Other commands:\n" && \
	  printf "  make clean [WORK_DIR=dir]    - Remove specified work directory\n" && \
	  printf "  make help                    - Show this help message\n" && \
	  printf "\n" && \
	  printf "Current settings:\n" && \
	  printf "  RUNNER_CMD = $(RUNNER_CMD)\n"

# Step 1: Initial dispatch
dispatch:
	@echo "Step 1/4: Running initial dispatch..."
	set -a && . .env && set +a && \
	$(RUNNER_CMD) run dispatch
	@echo "✓ Dispatch completed - chunks.yml created"

# Step 2: Prepare inputs
inputs:
	@echo "Step 2/4: Preparing inputs in directory '$(WORK_DIR)'..."
	set -a && . .env && set +a && \
	$(RUNNER_CMD) run inputs
	@echo "✓ Inputs prepared for '$(WORK_DIR)'"

# Step 3: Process chunks
process:
	@echo "Step 3/4: Processing chunks in directory '$(WORK_DIR)'..."
	set -a && . .env && set +a && \
	$(RUNNER_CMD) run process
	@echo "✓ Processing completed for '$(WORK_DIR)'"

# Step 4: Stage results
stage:
	@echo "Step 4/4: Staging results from directory '$(WORK_DIR)'..."
	set -a && . .env && set +a && \
	$(RUNNER_CMD) run outputs
	@echo "✓ Results staged for '$(WORK_DIR)'"

# Run all steps in one command
run-all:
	@echo "Running all steps in a single command..."
	set -a && . .env && set +a && \
	$(RUNNER_CMD) run run
	@echo "✓ All steps completed"

# Clean generated files
clean:
	@echo "Cleaning directory '$(WORK_DIR)'..."
	rm -rf "$(WORK_DIR)"
	@echo "✓ Clean completed for '$(WORK_DIR)'"
