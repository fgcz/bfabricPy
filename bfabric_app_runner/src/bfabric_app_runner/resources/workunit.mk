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

RUNNER_CMD := @APP_RUNNER_CMD@
CONFIG_FILE := app_env.yml

.PHONY: help dispatch inputs process stage run-all clean

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
	  printf "Other commands:\n" && \
	  printf "  make clean                   - Remove specified work directory\n" && \
	  printf "  make help                    - Show this help message\n" && \
	  printf "\n" && \
	  printf "Current settings:\n" && \
	  printf "  RUNNER_CMD = $(RUNNER_CMD)\n"

# Step 1: Initial dispatch
dispatch:
	@$(MAKE) --always-make chunks.yml

chunks.yml:
	@echo "step 1/4: running initial dispatch..."
	$(RUNNER_CMD) action dispatch --config "$(CONFIG_FILE)"
	@echo "✓ dispatch completed for '$(WORK_DIR)'."

# Step 2: Prepare inputs
inputs: chunks.yml
	@echo "Step 2/4: Preparing inputs in directory '$(WORK_DIR)'..."
	$(RUNNER_CMD) action inputs --config "$(CONFIG_FILE)"
	@echo "✓ Inputs prepared for '$(WORK_DIR)'"

# Step 3: Process chunks
process: chunks.yml
	@echo "Step 3/4: Processing chunks in directory '$(WORK_DIR)'..."
	$(RUNNER_CMD) action process --config "$(CONFIG_FILE)"
	@echo "✓ Processing completed for '$(WORK_DIR)'"

# Step 4: Stage results
stage: chunks.yml
	@echo "Step 4/4: Staging results from directory '$(WORK_DIR)'..."
	$(RUNNER_CMD) action outputs --config "$(CONFIG_FILE)"
	@echo "✓ Results staged for '$(WORK_DIR)'"

# Run all steps in one command
run-all: chunks.yml
	@echo "Run steps 2-4 in a single command..."
	$(RUNNER_CMD) action run-all --config "$(CONFIG_FILE)"
	@echo "✓ All steps completed"

# Clean generated files
clean:
	@echo "Cleaning directory '$(WORK_DIR)'..."
	rm -rf "$(WORK_DIR)"
	@echo "✓ Clean completed for '$(WORK_DIR)'"
