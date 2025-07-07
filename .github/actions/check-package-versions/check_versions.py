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

    :param package_dir: Directory containing the package
    :return: Package version string or None if not found
    """
    if not os.path.isdir(package_dir):
        print(f"Warning: Package directory {package_dir} not found")
        return None

    try:
        # Change to package directory and run hatch version
        orig_dir = os.getcwd()
        os.chdir(package_dir)
        try:
            version = subprocess.check_output(["hatch", "version"], text=True).strip()
            return version
        except Exception as e:
            print(f"Error getting version for {package_dir}: {e}")
            return None
        finally:
            os.chdir(orig_dir)
    except Exception as e:
        print(f"Error accessing directory {package_dir}: {e}")
        return None


def get_pypi_info(package_name: str, pypi_url: str = "https://pypi.org") -> dict:
    """
    Get package information from PyPI.

    :param package_name: Name of the package
    :param pypi_url: Base URL of the PyPI repository
    :return: Dict with 'current_version' and 'releases' keys, or empty dict if not found
    """
    api_url = f"{pypi_url}/pypi/{package_name}/json"

    try:
        response = requests.get(api_url)

        # If package doesn't exist on PyPI at all
        if response.status_code == 404:
            return {}

        # If request was successful
        if response.status_code == 200:
            data = response.json()
            return {
                "current_version": data.get("info", {}).get("version", "unknown"),
                "releases": list(data.get("releases", {}).keys()),
            }

        # Handle other response codes
        print(f"Error: Received status code {response.status_code} from PyPI")
        return {}

    except requests.RequestException as e:
        print(f"Error checking PyPI info: {e}")
        return {}


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
    pypi_info = get_pypi_info(package_name, pypi_url)

    if not pypi_info:
        print(f"Package {package_name} not found on PyPI, will be released")
        return True

    releases = pypi_info.get("releases", [])
    if version in releases:
        print(f"Package {package_name} version {version} already exists on PyPI, skipping")
        return False
    else:
        print(f"Package {package_name} version {version} not found on PyPI, will be released")
        return True


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
    packages: list[str],
    pypi_url: str = "https://pypi.org",
    force_packages: list[str] = None,
    include_versions: bool = False,
) -> list[str] | dict:
    """
    Check which packages need to be released.

    Args:
        packages: list of packages to check
        pypi_url: Base URL of the PyPI repository
        force_packages: list of packages to force release
        include_versions: if True, return dict with version info

    Returns:
        list of packages that need to be released, or dict with version info if include_versions=True
    """
    packages_to_release = []
    version_info = {}

    # If specific packages are forced, use those
    if force_packages:
        for pkg in force_packages:
            if pkg in packages:
                packages_to_release.append(pkg)
                print(f"Forcing release of {pkg}")
                if include_versions:
                    local_version = get_local_version(pkg)
                    pypi_info = get_pypi_info(pkg, pypi_url)
                    version_info[pkg] = {
                        "local_version": local_version,
                        "current_version": pypi_info.get("current_version", "Not found"),
                    }
            else:
                print(f"Warning: Package {pkg} not found in available packages")

        if include_versions:
            return {"packages_to_release": packages_to_release, "version_info": version_info}
        return packages_to_release

    # Otherwise, check each package version against PyPI
    for pkg in packages:
        local_version = get_local_version(pkg)
        if local_version:
            print(f"Package {pkg} local version: {local_version}")

            if include_versions:
                pypi_info = get_pypi_info(pkg, pypi_url)
                version_info[pkg] = {
                    "local_version": local_version,
                    "current_version": pypi_info.get("current_version", "Not found"),
                }

            if check_pypi_version(pkg, local_version, pypi_url):
                packages_to_release.append(pkg)

    if include_versions:
        return {"packages_to_release": packages_to_release, "version_info": version_info}
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
    parser.add_argument("--include-versions", action="store_true", help="Include version information in output")

    args = parser.parse_args()

    # Parse input arguments
    packages = args.packages.split(",")
    force_packages = args.force.split(",") if args.force else None
    priority_order = args.priority.split(",")

    # Check which packages need to be released
    result = check_packages(packages, args.pypi_url, force_packages, args.include_versions)

    if args.include_versions:
        packages_to_release = result["packages_to_release"]
        version_info = result["version_info"]

        # Sort packages based on priority
        sorted_packages = sort_packages(packages_to_release, priority_order)

        print(f"Packages to release: {sorted_packages}")

        # Return results in GitHub Actions format if requested
        if args.github_output:
            with open(args.github_output, "a") as f:
                packages_json = json.dumps(sorted_packages)
                f.write(f"packages_to_release={packages_json}\n")

                # Also output version info
                version_info_json = json.dumps(version_info)
                f.write(f"version_info={version_info_json}\n")

        # Print JSON output for programmatic use
        print(json.dumps({"packages_to_release": sorted_packages, "version_info": version_info}))
    else:
        packages_to_release = result

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
