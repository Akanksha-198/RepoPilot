from pathlib import Path


# Directories that should not be read
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
}


# Source-code extensions RepoPilot currently understands
SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".html",
    ".css",
}


def should_ignore(relative_path: Path) -> bool:
    """
    Check whether the relative path
    contains an ignored directory.
    """

    return any(
        part in IGNORED_DIRS
        for part in relative_path.parts
    )


def read_source_files(repo_path: Path) -> list:
    """
    Read supported source files
    from the cloned repository.

    Returns:

    [
        {
            "path": "src/app.js",
            "extension": ".js",
            "content": "..."
        }
    ]
    """

    source_files = []

    for path in repo_path.rglob("*"):

        # Only process files
        if not path.is_file():
            continue

        # Get path relative to repository
        relative_path = path.relative_to(
            repo_path
        )

        # Ignore unnecessary directories
        if should_ignore(relative_path):
            continue

        # Only process supported source files
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:

            content = path.read_text(
                encoding="utf-8"
            )

            source_files.append(
                {
                    "path": str(
                        relative_path
                    ).replace("\\", "/"),

                    "extension": path.suffix.lower(),

                    "content": content
                }
            )

        except UnicodeDecodeError:

            print(
                f"Skipping non-text file: {path}"
            )

        except Exception as error:

            print(
                f"Could not read {path}: {error}"
            )

    return source_files