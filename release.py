import subprocess
import re
import tomllib
import sys
from pathlib import Path


def get_remote_tags() -> list[str]:
    # executes: git ls-remote --tags origin
    out = subprocess.run(["git", "ls-remote", "--tags", "origin"], check=True, capture_output=True)
    return [line.split("\t")[-1].split("/")[-1] for line in out.stdout.decode().split("\n") if line]


def get_local_tags() -> list[str]:
    # executes: git tag
    out = subprocess.run(["git", "tag"], check=True, capture_output=True)
    return out.stdout.decode().split("\n")


def get_existing_releases(remote: bool) -> list[str]:
    tags = get_remote_tags() if remote else get_local_tags()

    # e.g. 1.2.21
    pattern = re.compile(r"^\d+\.\d+\.\d+$")
    return [tag for tag in tags if pattern.match(tag)]


def get_most_recent_release(remote: bool) -> str:
    sorted_releases = sorted(get_existing_releases(remote=remote), key=lambda x: tuple(map(int, x.split("."))))
    return sorted_releases[-1]


def get_current_pyproject_toml_version() -> str:
    pyproject_toml_path = Path("pyproject.toml")
    pyproject_toml = tomllib.loads(pyproject_toml_path.read_text())
    return pyproject_toml["project"]["version"]


def check_version() -> str:
    released_remote = get_most_recent_release(remote=True)
    released_local = get_most_recent_release(remote=False)
    current = get_current_pyproject_toml_version()
    if released_remote == current:
        print(f"Version {current} is already released remotely. Please bump the version in pyproject.toml")
        sys.exit(1)
    elif released_local == current:
        print(f"Version {current} is already released locally. Please bump the version in pyproject.toml")
        sys.exit(1)
    else:
        return current


def checkout_branch(branch: str) -> None:
    subprocess.run(["git", "checkout", branch], check=True)


def create_and_push_tag(version: str) -> None:
    subprocess.run(["git", "tag", version], check=True)
    subprocess.run(["git", "push", "origin", version], check=True)


def merge_and_push_current_branch(branch: str) -> None:
    subprocess.run(["git", "merge", branch], check=True)
    subprocess.run(["git", "push", "origin"], check=True)


def publish_docs() -> None:
    subprocess.run(["mkdocs", "gh-deploy"], check=True)


def main() -> None:
    checkout_branch("main")
    version = check_version()
    create_and_push_tag(version)
    checkout_branch("stable")
    merge_and_push_current_branch("main")
    checkout_branch("main")
    publish_docs()


if __name__ == "__main__":
    main()
