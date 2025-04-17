#!/usr/bin/env python3
"""
Script to check if packages need to be released by comparing local versions with PyPI versions.
This script can be used both in GitHub Actions workflows and for local testing.
"""

import argparse
import json
import os
import subprocess
import sys

import requests


def get_local_version(package_dir: str) -> str | None:
    """
    Get the local version of a package using Hatch.

    Args:
        package_dir: Directory containing the package

    Returns:
        Package version string or None if not found
    """
    if not os.path.isdir(package_dir):
        print(f"Warning: Package directory {package_dir} not found")
        return None

    try:
        # Change to package directory and run hatch version
        orig_dir = os.getcwd()
        os.chdir(package_dir)
        version = subprocess.check_output(["hatch", "version"], text=True).strip()
        os.chdir(orig_dir)
        return version
    except subprocess.CalledProcessError as e:
        print(f"Error getting version for {package_dir}: {e}")
        return None
    except FileNotFoundError:
        print("Error: hatch command not found. Please install hatch.")
        return None


def check_pypi_version(package_name: str, version: str, pypi_url: str = "https://pypi.org") -> bool:
    """
    Check if a specific version of a package exists on PyPI.

    Args:
        package_name: Name of the package
        version: Version to check
        pypi_url: Base URL of the PyPI repository

    Returns:
        True if the version needs to be released (doesn't exist on PyPI), False otherwise
    """
    api_url = f"{pypi_url}/pypi/{package_name}/json"

    try:
        response = requests.get(api_url)

        # If package doesn't exist on PyPI at all
        if response.status_code == 404:
            print(f"Package {package_name} not found on PyPI, will be released")
            return True

        # If request was successful
        if response.status_code == 200:
            data = response.json()
            releases = data.get("releases", {}).keys()

            if version in releases:
                print(f"Package {package_name} version {version} already exists on PyPI, skipping")
                return False
            else:
                print(f"Package {package_name} version {version} not found on PyPI, will be released")
                return True

        # Handle other response codes
        print(f"Error: Received status code {response.status_code} from PyPI")
        return False

    except requests.RequestException as e:
        print(f"Error checking PyPI version: {e}")
        return False


def sort_packages(packages_to_release: list[str], priority_order: list[str]) -> list[str]:
    """
    Sort packages based on priority order.

    Args:
        packages_to_release: list of packages to release
        priority_order: list of packages in order of priority

    Returns:
        Sorted list of packages to release
    """
    return sorted(
        packages_to_release, key=lambda x: priority_order.index(x) if x in priority_order else len(priority_order)
    )


def check_packages(
    packages: list[str], pypi_url: str = "https://pypi.org", force_packages: list[str] | None = None
) -> list[str]:
    """
    Check which packages need to be released.

    Args:
        packages: list of packages to check
        pypi_url: Base URL of the PyPI repository
        force_packages: list of packages to force release

    Returns:
        list of packages that need to be released
    """
    packages_to_release = []

    # If specific packages are forced, use those
    if force_packages:
        for pkg in force_packages:
            if pkg in packages:
                packages_to_release.append(pkg)
                print(f"Forcing release of {pkg}")
            else:
                print(f"Warning: Package {pkg} not found in available packages")
        return packages_to_release

    # Otherwise, check each package version against PyPI
    for pkg in packages:
        local_version = get_local_version(pkg)
        if local_version:
            print(f"Package {pkg} local version: {local_version}")

            if check_pypi_version(pkg, local_version, pypi_url):
                packages_to_release.append(pkg)

    return packages_to_release


def main():
    parser = argparse.ArgumentParser(description="Check which packages need to be released")
    parser.add_argument("--packages", type=str, required=True, help="Comma-separated list of packages to check")
    parser.add_argument("--pypi-url", type=str, default="https://pypi.org", help="Base URL of the PyPI repository")
    parser.add_argument("--force", type=str, help="Comma-separated list of packages to force release")
    parser.add_argument(
        "--priority",
        type=str,
        default="bfabric,bfabric_scripts,bfabric_app_runner",
        help="Comma-separated list of packages in priority order",
    )
    parser.add_argument("--github-output", type=str, help="Path to GitHub output file for setting outputs")

    args = parser.parse_args()

    # Parse input arguments
    packages = args.packages.split(",")
    force_packages = args.force.split(",") if args.force else None
    priority_order = args.priority.split(",")

    # Check which packages need to be released
    packages_to_release = check_packages(packages, args.pypi_url, force_packages)

    # Sort packages based on priority
    sorted_packages = sort_packages(packages_to_release, priority_order)

    # Output results
    result = {"packages_to_release": sorted_packages}
    print(f"Packages to release: {sorted_packages}")

    # Return results in GitHub Actions format if requested
    if args.github_output:
        with open(args.github_output, "a") as f:
            packages_json = json.dumps(sorted_packages)
            f.write(f"packages_to_release={packages_json}\n")

    # Also print JSON output for programmatic use
    print(json.dumps(result))

    # Return success if there are packages to release
    return 0 if packages_to_release else 1


if __name__ == "__main__":
    sys.exit(main())
