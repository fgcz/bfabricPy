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
# The WORK_DIR parameter defaults to "work" if not specified.
# Example with custom directory:
#     make inputs WORK_DIR=work_folder_1
#     make process WORK_DIR=work_folder_1
#     make stage WORK_DIR=work_folder_1
#
# Use `make help` to see all available commands

# Configuration
RUNNER_VERSION := @RUNNER_VERSION@
RUNNER_CMD := uv run -p 3.13 --with "bfabric-app-runner==$(RUNNER_VERSION)" bfabric-app-runner

# Input files
APP_DEF := $(realpath app_version.yml)
WORKUNIT_DEF := $(realpath workunit_definition.yml)
CURRENT_DIR := $(shell pwd)

# Default work directory (can be overridden via command line)
WORK_DIR ?= work

.PHONY: help dispatch inputs process stage run-all clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make run-all                 - Run all steps in a single command (recommended for most cases)"
	@echo ""
	@echo "Step-by-step execution:"
	@echo "  make dispatch                - Step 1: Initial step (creates chunks.yml)"
	@echo "  make inputs [WORK_DIR=dir]   - Step 2: Prepare input files"
	@echo "  make process [WORK_DIR=dir]  - Step 3: Process chunks in specified directory"
	@echo "  make stage [WORK_DIR=dir]    - Step 4: Stage results to server/storage"
	@echo ""
	@echo "Other commands:"
	@echo "  make clean [WORK_DIR=dir]    - Remove specified work directory"
	@echo "  make help                    - Show this help message"
	@echo ""
	@echo "Current settings:"
	@echo "  WORK_DIR = $(WORK_DIR) (default: work)"

# Step 1: Initial dispatch
dispatch:
	@echo "Step 1/4: Running initial dispatch..."
	$(RUNNER_CMD) app dispatch "$(APP_DEF)" "$(CURRENT_DIR)" "$(WORKUNIT_DEF)"
	@echo "✓ Dispatch completed - chunks.yml created"

# Step 2: Prepare inputs
inputs:
	@echo "Step 2/4: Preparing inputs in directory '$(WORK_DIR)'..."
	$(RUNNER_CMD) inputs prepare "$(WORK_DIR)/inputs.yml"
	@echo "✓ Inputs prepared for '$(WORK_DIR)'"

# Step 3: Process chunks
process:
	@echo "Step 3/4: Processing chunks in directory '$(WORK_DIR)'..."
	$(RUNNER_CMD) chunk process "$(APP_DEF)" "$(WORK_DIR)"
	@echo "✓ Processing completed for '$(WORK_DIR)'"

# Step 4: Stage results
stage:
	@echo "Step 4/4: Staging results from directory '$(WORK_DIR)'..."
	$(RUNNER_CMD) chunk outputs "$(APP_DEF)" "$(WORK_DIR)" "$(WORKUNIT_DEF)"
	@echo "✓ Results staged for '$(WORK_DIR)'"

# Run all steps in one command
run-all:
	@echo "Running all steps in a single command..."
	$(RUNNER_CMD) app run "$(APP_DEF)" "." "$(WORKUNIT_DEF)"
	@echo "✓ All steps completed"

# Clean generated files
clean:
	@echo "Cleaning directory '$(WORK_DIR)'..."
	rm -rf "$(WORK_DIR)"
	@echo "✓ Clean completed for '$(WORK_DIR)'"
