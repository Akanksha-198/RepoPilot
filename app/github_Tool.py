from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse


def repository_name(github_url: str) -> str:
    """Extract repository name from a GitHub URL."""

    parsed_url = urlparse(github_url)

    path = parsed_url.path.strip("/")

    if not path:
        raise ValueError("Invalid GitHub URL")

    name = path.split("/")[-1]

    if name.endswith(".git"):
        name = name[:-4]

    name = re.sub(
        r"[^a-zA-Z0-9]+",
        "-",
        name
    )

    return name


def clone_repository(
    github_url: str,
    clone_location: Path
) -> Path:

    """
    Clone a GitHub repository into
    the user-selected local directory.
    """

    # Create the destination directory
    clone_location.mkdir(
        parents=True,
        exist_ok=True
    )

    # Get repository name
    repo_name = repository_name(
        github_url
    )

    # Final repository path
    repo_path = clone_location / repo_name

    # If repository already exists
    if repo_path.exists():

        return repo_path

    command = [
        "git",
        "clone",
        "--depth",
        "1",
        github_url,
        str(repo_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:

        error = result.stderr.strip()

        raise RuntimeError(
            error or
            "Failed to clone repository."
        )

    return repo_path