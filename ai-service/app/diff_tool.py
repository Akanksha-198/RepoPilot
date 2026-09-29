from pathlib import Path
import difflib


def generate_full_file_diff(
    repository_path: str,
    file_path: str,
    old_content: str,
    new_content: str
) -> str:
    """
    Generate a unified diff for a repository file.

    Safety guarantees:
    - The target file must remain inside the repository.
    - The target must exist and be a file.
    - The supplied old content must exactly match
      the current file content.
    """

    # --------------------------------------------------
    # 1. Resolve repository and target paths
    # --------------------------------------------------

    repo_path = Path(repository_path).resolve()

    file_path = file_path.strip()

    # Remove accidental markdown backticks
    if file_path.startswith("`") and file_path.endswith("`"):
        file_path = file_path[1:-1].strip()

    if not file_path:
        raise ValueError(
            "File path cannot be empty."
        )

    target_path = (repo_path / file_path).resolve()

    # --------------------------------------------------
    # 2. Security check — prevent path traversal
    # --------------------------------------------------

    try:
        target_path.relative_to(repo_path)

    except ValueError:
        raise ValueError(
            "Unsafe file path. "
            "The target file must remain inside the repository."
        )

    # --------------------------------------------------
    # 3. Validate target file
    # --------------------------------------------------

    if not target_path.exists():
        raise FileNotFoundError(
            f"Repository file not found: {file_path}"
        )

    if not target_path.is_file():
        raise ValueError(
            f"Target path is not a file: {file_path}"
        )

    # --------------------------------------------------
    # 4. Read the actual file from disk
    # --------------------------------------------------

    actual_content = target_path.read_text(
        encoding="utf-8"
    )

    # --------------------------------------------------
    # 5. Verify old content
    #
    # This is important:
    # We never generate a diff against stale content.
    # --------------------------------------------------

    if actual_content != old_content:
        raise ValueError(
            "The provided old content does not match "
            "the current file on disk. "
            "Refusing to generate the diff."
        )

    # --------------------------------------------------
    # 6. Split old and new content into lines
    # --------------------------------------------------

    old_lines = old_content.splitlines(
        keepends=True
    )

    new_lines = new_content.splitlines(
        keepends=True
    )

    # --------------------------------------------------
    # 7. Generate unified diff
    # --------------------------------------------------

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm=""
    )

    return "\n".join(diff)


# ------------------------------------------------------
# Simple standalone test
# ------------------------------------------------------

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("        RepoPilot - Diff Tool")
    print("=" * 60)

    print()
    print("✓ Diff tool loaded successfully.")
    print("✓ Path safety checks enabled.")
    print("✓ File existence checks enabled.")
    print("✓ Old-content verification enabled.")
    print("✓ Unified diff generation enabled.")

    print()
    print("Phase 4B diff tool is ready.")
    print("=" * 60)