#git_tools.py
#
# Phase 6A — Git status (read-only).
# Phase 6B — Feature branches.
#
# Phase 6B adds the ONLY git-mutating operation so far:
# creating and checking out a feature branch. It still never
# commits and never pushes -- those are 6D/6E.

import re
import subprocess
from datetime import datetime
from pathlib import Path

PROTECTED_BRANCHES = {"main", "master"}


def _run_git(
    args: list[str],
    repository_path: str
) -> subprocess.CompletedProcess:

    return subprocess.run(
        ["git", *args],
        cwd=repository_path,
        capture_output=True,
        text=True
    )


def get_current_branch(
    repository_path: str
) -> str:
    """
    Return the name of the currently checked-out branch.

    Returns an empty string if this is not a git repository
    or the branch cannot be determined (e.g. detached HEAD).
    """

    result = _run_git(
        ["branch", "--show-current"],
        repository_path
    )

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def get_git_status(
    repository_path: str
) -> dict:
    """
    Return the working-tree status of the repository.

    Returns:

    {
        "is_git_repo": bool,
        "branch": "main",
        "staged": ["file1.py"],
        "modified": ["file2.js"],
        "untracked": ["file3.txt"],
        "clean": bool,
        "error": "" | "<message if something went wrong>"
    }

    Staging-area semantics (git status --porcelain):

    XY <path>

    X = index (staged) status
    Y = working tree status

    "??" means untracked.
    """

    repo_path = Path(
        repository_path
    ).resolve()

    if not (repo_path / ".git").exists():

        return {
            "is_git_repo": False,
            "branch": "",
            "staged": [],
            "modified": [],
            "untracked": [],
            "clean": True,
            "error": (
                "This folder is not a git repository "
                "(no .git directory found)."
            )
        }

    result = _run_git(
        ["status", "--porcelain"],
        str(repo_path)
    )

    if result.returncode != 0:

        return {
            "is_git_repo": True,
            "branch": "",
            "staged": [],
            "modified": [],
            "untracked": [],
            "clean": True,
            "error": (
                result.stderr.strip()
                or "git status failed."
            )
        }

    branch = get_current_branch(
        str(repo_path)
    )

    staged = []
    modified = []
    untracked = []

    for line in result.stdout.splitlines():

        if not line:
            continue

        index_status = line[0]
        worktree_status = line[1]
        file_path = line[3:].strip()

        if index_status == "?" and worktree_status == "?":

            untracked.append(file_path)
            continue

        if index_status != " ":

            staged.append(file_path)

        if worktree_status != " ":

            modified.append(file_path)

    return {
        "is_git_repo": True,
        "branch": branch,
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "clean": not (staged or modified or untracked),
        "error": ""
    }


def slugify_task(user_request: str) -> str:
    """
    Turn a user request into a short, safe branch-name fragment.

    "check index.js and remove the error" -> "check-index-js-and-remove"
    """

    words = re.sub(
        r"[^a-zA-Z0-9]+",
        "-",
        user_request.strip().lower()
    ).strip("-")

    parts = words.split("-")[:5]

    slug = "-".join(parts)

    return slug or "task"


def create_feature_branch(
    repository_path: str,
    user_request: str = ""
) -> dict:
    """
    Ensure RepoPilot is working on a feature branch, never on
    main/master directly.

    Behavior:

    - If the current branch is already a non-protected branch
      (e.g. an earlier RepoPilot branch), stay on it -- do NOT
      create a new branch for every single task.
    - If the current branch is main/master (or unknown), create
      a new branch named:

        repopilot/<task-slug>-<timestamp>

      and check it out.

    Returns:

    {
        "success": bool,
        "branch": "<branch now checked out>",
        "created_new": bool,
        "error": "" | "<message>"
    }
    """

    repo_path = Path(
        repository_path
    ).resolve()

    if not (repo_path / ".git").exists():

        return {
            "success": False,
            "branch": "",
            "created_new": False,
            "error": (
                "This folder is not a git repository "
                "(no .git directory found)."
            )
        }

    current_branch = get_current_branch(
        str(repo_path)
    )

    # --------------------------------------------------------
    # Already on a safe (non-protected) branch -- reuse it.
    # --------------------------------------------------------

    if current_branch and current_branch not in PROTECTED_BRANCHES:

        return {
            "success": True,
            "branch": current_branch,
            "created_new": False,
            "error": ""
        }

    # --------------------------------------------------------
    # On main/master (or branch unknown, e.g. detached HEAD)
    # -- create and checkout a new feature branch.
    # --------------------------------------------------------

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    task_slug = slugify_task(
        user_request
    )

    new_branch_name = f"repopilot/{task_slug}-{timestamp}"

    result = _run_git(
        ["checkout", "-b", new_branch_name],
        str(repo_path)
    )

    if result.returncode != 0:

        return {
            "success": False,
            "branch": current_branch,
            "created_new": False,
            "error": (
                result.stderr.strip()
                or "Failed to create the feature branch."
            )
        }

    return {
        "success": True,
        "branch": new_branch_name,
        "created_new": True,
        "error": ""
    }


# ============================================================
# PHASE 6C — Real Git Diff (read-only)
#
# This is DISTINCT from diff_tool.py's generate_full_file_diff():
# that one compares the AI's proposed new content against the
# old file content BEFORE writing, as part of human review.
#
# This one asks git itself, AFTER the file has been written to
# disk, what changed relative to the last commit (HEAD). It is
# an independent audit trail -- if it ever disagrees with what
# RepoPilot's diff tool showed during review, something touched
# the file that RepoPilot didn't account for.
# ============================================================

def get_git_diff(
    repository_path: str,
    file_path: str = ""
) -> dict:
    """
    Return git's own diff of unstaged changes in the working tree,
    compared against the last commit (HEAD).

    If file_path is given, the diff is limited to that one file.
    Otherwise it covers the whole working tree.

    Returns:

    {
        "diff": "<unified diff text, or '' if no changes>",
        "error": "" | "<message if something went wrong>"
    }
    """

    repo_path = Path(
        repository_path
    ).resolve()

    if not (repo_path / ".git").exists():

        return {
            "diff": "",
            "error": (
                "This folder is not a git repository "
                "(no .git directory found)."
            )
        }

    args = ["diff"]

    if file_path:
        args.append("--")
        args.append(file_path)

    result = _run_git(
        args,
        str(repo_path)
    )

    if result.returncode != 0:

        return {
            "diff": "",
            "error": (
                result.stderr.strip()
                or "git diff failed."
            )
        }

    return {
        "diff": result.stdout,
        "error": ""
    }


# ============================================================
# PHASE 6D — Commit (validated changes only)
#
# This is the first operation in git_tools.py that permanently
# writes to git history. Safety rules enforced here, independent
# of anything the caller already checked:
#
# 1. NEVER commit on a protected branch (main/master), even if
#    the caller believes it already switched branches.
# 2. Only the exact file paths passed in are staged -- never a
#    blanket `git add -A`. Backup files (.backup) must never be
#    passed in by the caller.
# 3. If staging the given files results in nothing actually
#    staged (e.g. the file matches HEAD already), refuse rather
#    than create an empty commit.
# ============================================================

def commit_changes(
    repository_path: str,
    file_paths: list[str],
    commit_message: str
) -> dict:
    """
    Stage and commit ONLY the given file paths.

    Returns:

    {
        "success": bool,
        "message": "<human-readable result>",
        "branch": "<branch committed to, if successful>",
        "commit_hash": "<short hash, if successful>"
    }
    """

    repo_path = Path(
        repository_path
    ).resolve()

    if not (repo_path / ".git").exists():

        return {
            "success": False,
            "message": (
                "This folder is not a git repository "
                "(no .git directory found)."
            ),
            "branch": "",
            "commit_hash": ""
        }

    branch = get_current_branch(
        str(repo_path)
    )

    # --------------------------------------------------------
    # SAFETY CHECK 1
    # Never commit on a protected branch, no matter what the
    # caller believes already happened.
    # --------------------------------------------------------

    if not branch or branch in PROTECTED_BRANCHES:

        return {
            "success": False,
            "message": (
                f"Refusing to commit: current branch is "
                f"'{branch or 'unknown'}'. RepoPilot will not "
                f"commit directly to a protected branch. "
                f"Create a feature branch first."
            ),
            "branch": branch,
            "commit_hash": ""
        }

    if not file_paths:

        return {
            "success": False,
            "message": "No files were specified to commit.",
            "branch": branch,
            "commit_hash": ""
        }

    if not commit_message.strip():

        return {
            "success": False,
            "message": "Commit message cannot be empty.",
            "branch": branch,
            "commit_hash": ""
        }

    # --------------------------------------------------------
    # SAFETY CHECK 2
    # Stage ONLY the exact files given -- never `git add -A`.
    # --------------------------------------------------------

    add_result = _run_git(
        ["add", "--", *file_paths],
        str(repo_path)
    )

    if add_result.returncode != 0:

        return {
            "success": False,
            "message": (
                add_result.stderr.strip()
                or "git add failed."
            ),
            "branch": branch,
            "commit_hash": ""
        }

    # --------------------------------------------------------
    # SAFETY CHECK 3
    # Confirm something was actually staged before committing.
    # Prevents creating an empty, meaningless commit.
    # --------------------------------------------------------

    staged_check = _run_git(
        ["diff", "--cached", "--name-only"],
        str(repo_path)
    )

    if not staged_check.stdout.strip():

        return {
            "success": False,
            "message": (
                "Nothing to commit -- the specified file(s) "
                "have no staged changes relative to HEAD."
            ),
            "branch": branch,
            "commit_hash": ""
        }

    commit_result = _run_git(
        ["commit", "-m", commit_message],
        str(repo_path)
    )

    if commit_result.returncode != 0:

        return {
            "success": False,
            "message": (
                commit_result.stderr.strip()
                or "git commit failed."
            ),
            "branch": branch,
            "commit_hash": ""
        }

    hash_result = _run_git(
        ["rev-parse", "--short", "HEAD"],
        str(repo_path)
    )

    commit_hash = (
        hash_result.stdout.strip()
        if hash_result.returncode == 0
        else ""
    )

    return {
        "success": True,
        "message": f"Committed to branch '{branch}'.",
        "branch": branch,
        "commit_hash": commit_hash
    }


# ============================================================
# PHASE 6E — Push (separate approval) + safe undo/revert
#
# Push is its own explicit human approval step, separate from
# commit, per the master plan.
#
# Rollback design:
# - Before push: "undo" is a plain git reset -- 100% safe,
#   nothing has left this machine yet.
# - After push: "undo" via history rewrite (force-push) is NOT
#   offered here, since it's risky for a beginner-friendly tool.
#   Instead, "revert" creates a NEW commit that reverses the
#   last one -- always safe, never rewrites history.
# ============================================================

def get_last_commit_info(
    repository_path: str
) -> dict:
    """
    Return info about the most recent commit on the current
    branch, and whether it has already been pushed to its
    upstream (origin) branch.

    Returns:

    {
        "has_commit": bool,
        "branch": "repopilot/...",
        "hash": "abc1234",
        "message": "RepoPilot: ...",
        "pushed": bool
    }
    """

    repo_path = Path(
        repository_path
    ).resolve()

    branch = get_current_branch(
        str(repo_path)
    )

    if not branch:

        return {
            "has_commit": False,
            "branch": "",
            "hash": "",
            "message": "",
            "pushed": False
        }

    log_result = _run_git(
        ["log", "-1", "--pretty=%h %s"],
        str(repo_path)
    )

    if log_result.returncode != 0 or not log_result.stdout.strip():

        return {
            "has_commit": False,
            "branch": branch,
            "hash": "",
            "message": "",
            "pushed": False
        }

    parts = log_result.stdout.strip().split(
        " ",
        1
    )

    commit_hash = parts[0]

    commit_message = (
        parts[1]
        if len(parts) > 1
        else ""
    )

    # ----------------------------------------------------
    # Determine if this exact commit has already been
    # pushed, by comparing local HEAD to the upstream
    # tracking branch's HEAD (if one exists).
    # ----------------------------------------------------

    pushed = False

    upstream_check = _run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        str(repo_path)
    )

    if upstream_check.returncode == 0:

        local_head = _run_git(
            ["rev-parse", "HEAD"],
            str(repo_path)
        ).stdout.strip()

        upstream_head_result = _run_git(
            ["rev-parse", "@{u}"],
            str(repo_path)
        )

        upstream_head = (
            upstream_head_result.stdout.strip()
            if upstream_head_result.returncode == 0
            else ""
        )

        pushed = bool(
            upstream_head
            and local_head == upstream_head
        )

    return {
        "has_commit": True,
        "branch": branch,
        "hash": commit_hash,
        "message": commit_message,
        "pushed": pushed
    }


def push_branch(
    repository_path: str
) -> dict:
    """
    Push the current branch to origin, setting up tracking
    if it isn't already tracked (git push -u origin <branch>).

    Refuses on a protected branch.
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
                f"Refusing to push: current branch is "
                f"'{branch or 'unknown'}'. RepoPilot will not "
                f"push a protected branch."
            ),
            "branch": branch
        }

    result = _run_git(
        ["push", "-u", "origin", branch],
        str(repo_path)
    )

    if result.returncode != 0:

        return {
            "success": False,
            "message": (
                result.stderr.strip()
                or "git push failed."
            ),
            "branch": branch
        }

    return {
        "success": True,
        "message": f"Pushed branch '{branch}' to origin.",
        "branch": branch
    }


def undo_last_commit(
    repository_path: str
) -> dict:
    """
    Undo the most recent LOCAL commit with `git reset --mixed
    HEAD~1`. This keeps the file changes in the working tree,
    unstaged -- nothing is lost, only the commit itself is
    removed.

    ONLY allowed when:
    - not on a protected branch
    - the commit has NOT already been pushed (use revert instead)
    - there is a previous commit to reset back to
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
            "message": "Refusing to undo on a protected branch."
        }

    commit_info = get_last_commit_info(
        str(repo_path)
    )

    if not commit_info["has_commit"]:

        return {
            "success": False,
            "message": "There is no commit to undo."
        }

    if commit_info["pushed"]:

        return {
            "success": False,
            "message": (
                "This commit has already been pushed to GitHub. "
                "Undo would rewrite shared history -- use "
                "Revert instead, which is always safe."
            )
        }

    log_check = _run_git(
        ["log", "--oneline", "-2"],
        str(repo_path)
    )

    if len(log_check.stdout.strip().splitlines()) < 2:

        return {
            "success": False,
            "message": (
                "No earlier commit to return to -- cannot undo "
                "the very first commit in this repository."
            )
        }

    reset_result = _run_git(
        ["reset", "--mixed", "HEAD~1"],
        str(repo_path)
    )

    if reset_result.returncode != 0:

        return {
            "success": False,
            "message": (
                reset_result.stderr.strip()
                or "git reset failed."
            )
        }

    return {
        "success": True,
        "message": (
            f"Last commit undone on branch '{branch}'. "
            f"Your file changes are back in the working tree, "
            f"unstaged."
        )
    }


def revert_last_commit(
    repository_path: str
) -> dict:
    """
    Safely undo the last commit by creating a NEW commit that
    reverses its changes (git revert --no-edit HEAD). This
    never rewrites history, so it is safe to use even after
    the commit has been pushed.
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
            "message": "Refusing to revert on a protected branch.",
            "commit_hash": ""
        }

    result = _run_git(
        ["revert", "--no-edit", "HEAD"],
        str(repo_path)
    )

    if result.returncode != 0:

        return {
            "success": False,
            "message": (
                result.stderr.strip()
                or "git revert failed."
            ),
            "commit_hash": ""
        }

    hash_result = _run_git(
        ["rev-parse", "--short", "HEAD"],
        str(repo_path)
    )

    commit_hash = (
        hash_result.stdout.strip()
        if hash_result.returncode == 0
        else ""
    )

    return {
        "success": True,
        "message": f"Reverted the last commit on branch '{branch}'.",
        "commit_hash": commit_hash
    }


# ============================================================
# HOUSEKEEPING — Ignore backup files
#
# RepoPilot never commits *.backup files by design (see
# commit_changes above), but they can still show up as noise
# in git status/diff if they were tracked before RepoPilot
# started managing this repo (e.g. committed manually). This
# is a one-time cleanup: add *.backup to .gitignore and stop
# tracking any that are already tracked -- their content on
# disk is left untouched.
# ============================================================

def ignore_backup_files(
    repository_path: str
) -> dict:
    """
    Ensure *.backup is in .gitignore, untrack any *.backup
    files that are currently tracked, and commit that
    housekeeping change on the current (non-protected) branch.
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
                f"Refusing to run on protected branch "
                f"'{branch or 'unknown'}'. Switch to a feature "
                f"branch first."
            )
        }

    gitignore_path = repo_path / ".gitignore"

    existing_content = (
        gitignore_path.read_text(encoding="utf-8")
        if gitignore_path.exists()
        else ""
    )

    already_ignored = any(
        line.strip() == "*.backup"
        for line in existing_content.splitlines()
    )

    changed_anything = False

    if not already_ignored:

        new_content = existing_content

        if new_content and not new_content.endswith("\n"):
            new_content += "\n"

        new_content += "*.backup\n"

        gitignore_path.write_text(
            new_content,
            encoding="utf-8"
        )

        changed_anything = True

    # ----------------------------------------------------
    # Untrack any already-tracked *.backup files (content
    # on disk is left alone -- git rm --cached only removes
    # them from git's index, not from the filesystem).
    # ----------------------------------------------------

    tracked_check = _run_git(
        ["ls-files", "--", "*.backup"],
        str(repo_path)
    )

    tracked_backups = [
        line.strip()
        for line in tracked_check.stdout.splitlines()
        if line.strip()
    ]

    if tracked_backups:

        untrack_result = _run_git(
            ["rm", "--cached", "--", *tracked_backups],
            str(repo_path)
        )

        if untrack_result.returncode != 0:

            return {
                "success": False,
                "message": (
                    untrack_result.stderr.strip()
                    or "Failed to untrack backup files."
                )
            }

        changed_anything = True

    if not changed_anything:

        return {
            "success": True,
            "message": "Backup files are already ignored — nothing to do."
        }

    # ----------------------------------------------------
    # Stage and commit the housekeeping change.
    # ----------------------------------------------------

    add_result = _run_git(
        ["add", "--", ".gitignore"],
        str(repo_path)
    )

    if add_result.returncode != 0:

        return {
            "success": False,
            "message": (
                add_result.stderr.strip()
                or "Failed to stage .gitignore."
            )
        }

    commit_result = _run_git(
        [
            "commit", "-m",
            "chore: ignore backup files (RepoPilot housekeeping)"
        ],
        str(repo_path)
    )

    if commit_result.returncode != 0:

        return {
            "success": False,
            "message": (
                commit_result.stderr.strip()
                or "Failed to commit housekeeping change."
            )
        }

    return {
        "success": True,
        "message": (
            f"Backup files are now ignored on branch '{branch}'. "
            f"{len(tracked_backups)} previously tracked backup "
            f"file(s) untracked (content kept on disk)."
        )
    }


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("       RepoPilot - Phase 6A")
    print("          Git Status (read-only)")
    print("=" * 60)

    repository_path = input(
        "\nEnter repository path:\n> "
    ).strip()

    status = get_git_status(
        repository_path
    )

    print("\n" + "-" * 60)

    if status["error"]:
        print(f"Error: {status['error']}")

    else:
        print(f"Branch: {status['branch']}")
        print(f"Clean: {status['clean']}")
        print(f"Staged: {status['staged']}")
        print(f"Modified: {status['modified']}")
        print(f"Untracked: {status['untracked']}")

    print("-" * 60)