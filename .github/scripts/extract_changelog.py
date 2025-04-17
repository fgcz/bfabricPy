#!/usr/bin/env python3
"""
Script to extract changelog entries for a specific version from a markdown changelog file.
This script can be used both in GitHub Actions workflows and for local testing.
"""

import argparse
import os
import re
import sys


def extract_changelog_entry(changelog_path: str, version: str) -> str:
    """
    Extract the changelog entry for a specific version from a markdown changelog file.

    Args:
        changelog_path: Path to the changelog file
        version: Version to extract the changelog for

    Returns:
        Extracted changelog entry or empty string if not found
    """
    # Check if changelog file exists
    if not os.path.isfile(changelog_path):
        print(f"Warning: Changelog file {changelog_path} not found")
        return ""

    try:
        # Read the changelog file
        with open(changelog_path, "r") as f:
            content = f.read()

        # Regular expression to extract the section for the specific version
        # This matches from the heading for the specified version until the next heading or end of file
        pattern = rf"^## \[{re.escape(version)}\].*?(?=^## \[|\Z)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            return match.group(0).strip()
        else:
            print(f"Warning: No changelog entry found for version {version}")
            return ""

    except Exception as e:
        print(f"Error extracting changelog: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(description="Extract changelog entry for a specific version")
    parser.add_argument("--changelog", type=str, required=True, help="Path to the changelog file")
    parser.add_argument("--version", type=str, required=True, help="Version to extract the changelog for")
    parser.add_argument("--output", type=str, help="Path to output file (if not provided, prints to stdout)")
    parser.add_argument("--github-output", type=str, help="Path to GitHub output file for setting outputs")
    parser.add_argument("--default-message", type=str, help="Default message if no changelog entry is found")

    args = parser.parse_args()

    # Extract the changelog entry
    changelog_entry = extract_changelog_entry(args.changelog, args.version)

    # Use default message if no changelog entry is found and default message is provided
    if not changelog_entry and args.default_message:
        changelog_entry = args.default_message.replace("{version}", args.version)

    # Output the changelog entry
    if args.output:
        with open(args.output, "w") as f:
            f.write(changelog_entry)
    else:
        print(changelog_entry)

    # Set GitHub Actions output if requested
    if args.github_output:
        with open(args.github_output, "a") as f:
            # Escape multiline output for GitHub Actions
            escaped_entry = changelog_entry.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
            f.write(f"changelog_entry={escaped_entry}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
