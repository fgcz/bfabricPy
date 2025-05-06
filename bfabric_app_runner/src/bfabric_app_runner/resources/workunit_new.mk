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

SHELL := /bin/bash

#.PHONY: help dispatch inputs process stage run-all clean

.PHONY: help

RUNNER_CMD := $$APP_RUNNER_UV_BIN run --isolated --no-project -p $$APP_RUNNER_UV_PYTHON_VERSION --with $$APP_RUNNER_UV_DEPS_STRING

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
	@echo "  RUNNER_CMD = $(RUNNER_CMD)"
	@echo "  WORK_DIR = $(WORK_DIR) (default: work)"
	@echo "  APP_DEF = $(APP_DEF) (default: $(APP_DEF_DEFAULT))"
	@echo "  WORKUNIT_DEF = $(WORKUNIT_DEF) (default: $(WORKUNIT_DEF_DEFAULT))"

# Step 1: Initial dispatch
dispatch:
	@echo "Step 1/4: Running initial dispatch..."
	set -a && . .env && set +a && \
	$(RUNNER_CMD) app dispatch "$(APP_DEF)" "$(CURRENT_DIR)" "$(WORKUNIT_DEF)"
	@echo "✓ Dispatch completed - chunks.yml created"
