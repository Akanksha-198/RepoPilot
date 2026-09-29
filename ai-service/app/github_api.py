#github_api.py
#
# Phase 6F — GitHub API integration (repo/branch/PR read access).
# Phase 6G — Actual pull request creation.
#
# Requires a GitHub Personal Access Token with 'repo' scope
# (classic) or Contents: Read/Write + Pull requests: Read/Write
# (fine-grained), set as GITHUB_TOKEN in your .env file.
#
# This module NEVER commits or pushes -- that's git_tools.py.
# It only talks to GitHub's REST API to read repo/PR state and
# to create a pull request from a branch that has already been
# pushed.

import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

from .git_tools import _run_git, get_current_branch, PROTECTED_BRANCHES

load_dotenv()

GITHUB_API_BASE = "https://api.github.com"


def get_github_token() -> str:
    """
    Read the GitHub token from the environment.

    Raises ValueError with a clear setup message if it's missing --
    callers should catch this and show the message to the user
    rather than letting a raw exception surface.
    """

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError(
            "GITHUB_TOKEN is missing. Create a Personal Access "
            "Token at https://github.com/settings/tokens (scope: "
            "'repo' for a classic token, or 'Contents' + "
            "'Pull requests' read/write for a fine-grained token), "
            "then add this line to your .env file:\n\n"
            "GITHUB_TOKEN=your_token_here"
        )

    return token


def _auth_headers(token: str) -> dict:

    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }


def get_remote_owner_repo(
    repository_path: str
) -> dict:
    """
    Parse the 'origin' remote URL to get (owner, repo).

    Returns:
    {
        "success": bool,
        "owner": "Akanksha-198",
        "repo": "repair-test",
        "message": "" | "<error>"
    }
    """

    result = _run_git(
        ["remote", "get-url", "origin"],
        repository_path
    )

    if result.returncode != 0:

        return {
            "success": False,
            "owner": "",
            "repo": "",
            "message": (
                result.stderr.strip()
                or "No 'origin' remote is configured for this repository."
            )
        }

    url = result.stdout.strip()

    # Handles both:
    # https://github.com/owner/repo.git
    # git@github.com:owner/repo.git

    match = re.search(
        r"github\.com[:/]+([^/]+)/([^/.]+?)(\.git)?$",
        url
    )

    if not match:

        return {
            "success": False,
            "owner": "",
            "repo": "",
            "message": (
                f"Could not parse a GitHub owner/repo from "
                f"remote URL: {url}"
            )
        }

    return {
        "success": True,
        "owner": match.group(1),
        "repo": match.group(2),
        "message": ""
    }


def get_default_branch(
    owner: str,
    repo: str,
    token: str
) -> str:
    """
    Return the repository's default branch (usually 'main').
    Falls back to 'main' if the API call fails for any reason.
    """

    try:

        response = requests.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}",
            headers=_auth_headers(token),
            timeout=15
        )

        if response.status_code == 200:
            return response.json().get("default_branch", "main")

    except requests.RequestException:
        pass

    return "main"


def find_existing_pr(
    owner: str,
    repo: str,
    token: str,
    head_branch: str,
    base_branch: str
) -> dict:
    """
    Check whether an open PR already exists for head_branch -> base_branch.

    Returns:
    {"exists": bool, "url": "", "number": None}
    """

    try:

        response = requests.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
            headers=_auth_headers(token),
            params={
                "state": "open",
                "head": f"{owner}:{head_branch}",
                "base": base_branch
            },
            timeout=15
        )

        if response.status_code == 200:

            results = response.json()

            if results:

                return {
                    "exists": True,
                    "url": results[0]["html_url"],
                    "number": results[0]["number"]
                }

    except requests.RequestException:
        pass

    return {
        "exists": False,
        "url": "",
        "number": None
    }


def create_pull_request(
    repository_path: str,
    title: str,
    body: str,
    base_branch: str = ""
) -> dict:
    """
    Create a GitHub pull request from the current (already-pushed)
    branch into base_branch. If base_branch is not given, the
    repository's actual default branch is used.

    Safety / correctness checks, in order:
    1. Refuses if the current branch is protected (main/master) --
       there is nothing to PR from a protected branch.
    2. Refuses if GITHUB_TOKEN is missing, with setup instructions.
    3. Refuses if the 'origin' remote can't be parsed as a GitHub
       repo.
    4. If an open PR for this branch already exists, returns that
       PR's URL instead of creating a duplicate.

    Returns:
    {
        "success": bool,
        "message": "<human-readable result>",
        "url": "<PR URL, if successful or already existed>",
        "already_existed": bool
    }
    """

    repo_path = Path(
        repository_path
    ).resolve()

    branch = get_current_branch(
        str(repo_path)
    )

    if not branch or branch in PROTECTED_BRANCHES:

        return {
            "success": False,
            "message": (
                f"Refusing to open a pull request from protected "
                f"branch '{branch or 'unknown'}'."
            ),
            "url": "",
            "already_existed": False
        }

    try:
        token = get_github_token()
    except ValueError as error:
        return {
            "success": False,
            "message": str(error),
            "url": "",
            "already_existed": False
        }

    owner_repo = get_remote_owner_repo(
        str(repo_path)
    )

    if not owner_repo["success"]:

        return {
            "success": False,
            "message": owner_repo["message"],
            "url": "",
            "already_existed": False
        }

    owner = owner_repo["owner"]
    repo = owner_repo["repo"]

    if not base_branch:
        base_branch = get_default_branch(owner, repo, token)

    existing = find_existing_pr(
        owner,
        repo,
        token,
        branch,
        base_branch
    )

    if existing["exists"]:

        return {
            "success": True,
            "message": "A pull request for this branch already exists.",
            "url": existing["url"],
            "already_existed": True
        }

    try:

        response = requests.post(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
            headers=_auth_headers(token),
            json={
                "title": title,
                "body": body,
                "head": branch,
                "base": base_branch
            },
            timeout=15
        )

    except requests.RequestException as error:

        return {
            "success": False,
            "message": f"Network error contacting GitHub: {error}",
            "url": "",
            "already_existed": False
        }

    if response.status_code == 201:

        pr_data = response.json()

        return {
            "success": True,
            "message": "Pull request created.",
            "url": pr_data["html_url"],
            "already_existed": False
        }

    try:
        error_message = response.json().get("message", response.text)
    except ValueError:
        error_message = response.text or f"HTTP {response.status_code}"

    return {
        "success": False,
        "message": f"GitHub API error: {error_message}",
        "url": "",
        "already_existed": False
    }


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("       RepoPilot - Phase 6F/6G")
    print("          GitHub Pull Request (test)")
    print("=" * 60)

    repository_path = input(
        "\nEnter repository path:\n> "
    ).strip()

    title = input(
        "\nPR title:\n> "
    ).strip()

    body = input(
        "\nPR description:\n> "
    ).strip()

    result = create_pull_request(
        repository_path,
        title,
        body
    )

    print("\n" + "-" * 60)

    if result["success"]:
        print(f"Success: {result['message']}")
        print(f"URL: {result['url']}")
    else:
        print(f"Failed: {result['message']}")

    print("-" * 60)
