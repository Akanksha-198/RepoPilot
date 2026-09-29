from pathlib import Path
import shutil


def backup_file(file_path: Path) -> Path:
    """
    Create a backup of the original file.
    """

    backup_path = file_path.with_suffix(
        file_path.suffix + ".backup"
    )

    shutil.copy2(
        file_path,
        backup_path
    )

    return backup_path


def apply_full_file_change(
    repository_path: str,
    file_path: str,
    old_content: str,
    new_content: str
) -> dict:
    """
    Safely replace the complete contents of a repository file.

    Safety checks:
    1. File must stay inside repository.
    2. File must exist.
    3. Current file content must exactly match old_content.
    4. Original file is backed up before modification.
    """

    repo_path = Path(
        repository_path
    ).resolve()

    file_path = file_path.strip()

    if (
        file_path.startswith("`")
        and file_path.endswith("`")
    ):
        file_path = file_path[1:-1].strip()

    target_path = (
        repo_path / file_path
    ).resolve()

    # --------------------------------------------------
    # SAFETY CHECK 1
    # --------------------------------------------------

    try:

        target_path.relative_to(
            repo_path
        )

    except ValueError:

        raise ValueError(
            "Unsafe file path. "
            "The target file must remain "
            "inside the repository."
        )

    # --------------------------------------------------
    # SAFETY CHECK 2
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
    # READ CURRENT FILE
    # --------------------------------------------------

    current_content = (
        target_path.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------
    # SAFETY CHECK 3
    # --------------------------------------------------
    # Make sure nobody changed the file
    # after the proposal was generated.
    # --------------------------------------------------

    if current_content != old_content:

        raise ValueError(
            "The current file content does not "
            "match the expected old content. "
            "The file may have changed. "
            "Refusing to modify it."
        )

    # --------------------------------------------------
    # BACKUP
    # --------------------------------------------------

    backup_path = backup_file(
        target_path
    )

    # --------------------------------------------------
    # APPLY CHANGE
    # --------------------------------------------------

    target_path.write_text(
        new_content,
        encoding="utf-8"
    )

    return {
        "status": "modified",
        "file_path": file_path,
        "backup_path": str(
            backup_path
        ),
        "message": (
            "File change applied successfully."
        )
    }


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("          RepoPilot - Phase 4C")
    print("          Safe Patch Application")
    print("=" * 60)

    print(
        "\nFile modification tool loaded successfully."
    )