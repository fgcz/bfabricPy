#!/usr/bin/env python3
import re
import sys


def extract_changelog(version, changelog_path):
    with open(changelog_path) as f:
        content = f.read()

    match = re.search(rf"^## \[{re.escape(version)}\].*?(?=^## \[|\Z)", content, re.M | re.S)

    if match:
        return match.group(0).strip()
    return ""


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: extract_changelog.py VERSION CHANGELOG_PATH")
        sys.exit(1)

    version = sys.argv[1]
    changelog_path = sys.argv[2]
    print(extract_changelog(version, changelog_path))
