from pathlib import Path


def resolve_repository_file(
    repository_path: str,
    file_path: str
) -> Path:
    """
    Safely resolve a repository-relative file path.

    The returned file must:
    1. Exist
    2. Be a file
    3. Stay inside the repository
    """

    repo_path = Path(
        repository_path
    ).resolve()

    file_path = file_path.strip()

    # Remove markdown backticks if the LLM returns:
    # `index.js`
    if (
        file_path.startswith("`")
        and file_path.endswith("`")
    ):
        file_path = file_path[
            1:-1
        ].strip()

    target_path = (
        repo_path / file_path
    ).resolve()

    # --------------------------------------------------
    # SECURITY CHECK
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
    # EXISTENCE CHECK
    # --------------------------------------------------

    if not target_path.exists():

        raise FileNotFoundError(
            f"Repository file not found: "
            f"{file_path}"
        )

    # --------------------------------------------------
    # FILE CHECK
    # --------------------------------------------------

    if not target_path.is_file():

        raise ValueError(
            f"Target path is not a file: "
            f"{file_path}"
        )

    return target_path


def read_repository_file(
    repository_path: str,
    file_path: str
) -> dict:
    """
    Read the actual file from the repository.

    Returns repository-relative path
    and complete file content.
    """

    target_path = resolve_repository_file(
        repository_path,
        file_path
    )

    repo_path = Path(
        repository_path
    ).resolve()

    relative_path = target_path.relative_to(
        repo_path
    )

    content = target_path.read_text(
        encoding="utf-8"
    )

    return {
        "file_path": str(
            relative_path
        ).replace("\\", "/"),

        "content": content
    }


if __name__ == "__main__":

    print(
        "Repository file tools loaded successfully."
    )