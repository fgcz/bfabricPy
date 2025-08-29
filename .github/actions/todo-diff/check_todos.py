#!/usr/bin/env python3
"""
Check for "TODO" differences between git references.
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from typing import Dict, List, Set


class TodoItem:
    def __init__(self, file_path: str, line_number: int, content: str):
        self.file_path = file_path
        self.line_number = line_number
        self.content = content.strip()

    def __eq__(self, other):
        return (
            self.file_path == other.file_path
            and self.line_number == other.line_number
            and self.content == other.content
        )

    def __hash__(self):
        return hash((self.file_path, self.line_number, self.content))

    def __repr__(self):
        return f"TodoItem({self.file_path}:{self.line_number}, '{self.content}')"


def run_command(cmd: List[str]) -> str:
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"Error: {e.stderr}", file=sys.stderr)
        return ""


def get_changed_files(base_ref: str, head_ref: str) -> Set[str]:
    """Get the list of files changed between base and head references."""
    cmd = ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"]
    output = run_command(cmd)
    # Filter out .github folder and other irrelevant directories
    changed_files = set()
    for line in output.splitlines():
        file_path = line.strip()
        if file_path and not file_path.startswith(".github/"):
            changed_files.add(file_path)
    return changed_files


def get_todos_in_ref(ref: str, files: Set[str]) -> List[TodoItem]:
    """Get all "TODO" items in the given files at the specified git reference."""
    todos = []

    for file_path in files:
        # Check if file exists at this ref
        cmd = ["git", "show", f"{ref}:{file_path}"]
        file_content = run_command(cmd)

        if not file_content:
            continue

        # Use ripgrep to find TODOs in the file content
        cmd = ["rg", "-n", "TODO"]
        try:
            result = subprocess.run(cmd, input=file_content, capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if ":" in line:
                    line_num_str, todo_content = line.split(":", 1)
                    try:
                        line_num = int(line_num_str)
                        todos.append(TodoItem(file_path, line_num, todo_content))
                    except ValueError:
                        continue
        except subprocess.CalledProcessError:
            continue

    return todos


def compare_todos(base_todos: List[TodoItem], head_todos: List[TodoItem]) -> Dict:
    """Compare "TODO" lists and return changes."""

    # Group TODOs by file and content (ignoring line numbers for matching)
    base_by_file_content = defaultdict(list)
    head_by_file_content = defaultdict(list)

    for todo in base_todos:
        key = (todo.file_path, todo.content)
        base_by_file_content[key].append(todo)

    for todo in head_todos:
        key = (todo.file_path, todo.content)
        head_by_file_content[key].append(todo)

    base_keys = set(base_by_file_content.keys())
    head_keys = set(head_by_file_content.keys())

    # Find truly added/removed TODOs (different file+content combinations)
    added_keys = head_keys - base_keys
    removed_keys = base_keys - head_keys

    added = []
    for key in added_keys:
        # Use the first occurrence for reporting (could be multiple identical TODOs in same file)
        todo = head_by_file_content[key][0]
        added.append({"file_path": todo.file_path, "line_number": todo.line_number, "content": todo.content})

    removed = []
    for key in removed_keys:
        # Use the first occurrence for reporting
        todo = base_by_file_content[key][0]
        removed.append({"file_path": todo.file_path, "line_number": todo.line_number, "content": todo.content})

    # For TODOs that exist in both base and head (same file+content), we don't report them as modified
    # since they're the same TODO, just potentially at different line numbers
    modified = []

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
    }


def generate_summary(changes: Dict) -> str:
    """Generate a human-readable summary of changes."""
    added_count = len(changes["added"])
    removed_count = len(changes["removed"])
    modified_count = len(changes["modified"])

    if added_count == 0 and removed_count == 0 and modified_count == 0:
        return 'No "TODO" changes detected'

    parts = []
    if added_count > 0:
        parts.append(f"➕ {added_count} \"TODO\"{'s' if added_count != 1 else ''} added")
    if removed_count > 0:
        parts.append(f"❌ {removed_count} \"TODO\"{'s' if removed_count != 1 else ''} removed")
    if modified_count > 0:
        parts.append(f"📝 {modified_count} \"TODO\"{'s' if modified_count != 1 else ''} modified")

    return ", ".join(parts)


def write_github_output(output_file: str, has_changes: bool, summary: str, details: Dict):
    """Write outputs for GitHub Actions."""
    with open(output_file, "a") as f:
        f.write(f"has_changes={str(has_changes).lower()}\n")
        f.write(f"summary={summary}\n")
        f.write("details<<DETAILS_EOF\n")
        f.write(json.dumps(details, indent=2))
        f.write("\nDETAILS_EOF\n")


def main():
    parser = argparse.ArgumentParser(description='Check for "TODO" differences between git references')
    parser.add_argument("--base-ref", required=True, help="Base git reference")
    parser.add_argument("--head-ref", required=True, help="Head git reference")
    parser.add_argument("--github-output", help="GitHub Actions output file")

    args = parser.parse_args()

    # Get changed files
    changed_files = get_changed_files(args.base_ref, args.head_ref)

    if not changed_files:
        print("No files changed between references")
        if args.github_output:
            write_github_output(args.github_output, False, "No files changed", {})
        return

    # Get TODOs from both references
    base_todos = get_todos_in_ref(args.base_ref, changed_files)
    head_todos = get_todos_in_ref(args.head_ref, changed_files)

    # Compare and analyze changes
    changes = compare_todos(base_todos, head_todos)
    summary = generate_summary(changes)
    has_changes = any(changes[key] for key in ["added", "removed", "modified"])

    print(f'"TODO" Analysis: {summary}')

    # Write GitHub Actions output
    if args.github_output:
        write_github_output(args.github_output, has_changes, summary, changes)

    # Print details for debugging
    if has_changes:
        print("\nDetailed changes:")
        print(json.dumps(changes, indent=2))


if __name__ == "__main__":
    main()
