from pathlib import Path


IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv"
}


EXTENSION_TO_LANGUAGE = {

    ".py": "Python",

    ".js": "JavaScript",

    ".jsx": "React / JavaScript",

    ".ts": "TypeScript",

    ".tsx": "React / TypeScript",

    ".java": "Java",

    ".cpp": "C++",

    ".c": "C",

    ".cs": "C#",

    ".go": "Go",

    ".rs": "Rust",

    ".php": "PHP",

    ".html": "HTML",

    ".css": "CSS",

}


IMPORTANT_FILES = {

    "package.json",

    "requirements.txt",

    "pyproject.toml",

    "Dockerfile",

    "docker-compose.yml",

    "README.md",

    "next.config.js",

    "next.config.ts",

    "vite.config.js",

    "vite.config.ts",

}


def scan_repository(repo_path: Path) -> dict:

    files = []

    languages = {}

    for path in repo_path.rglob("*"):

        if not path.is_file():
            continue

        relative_parts = path.relative_to(
            repo_path
        ).parts

        # Ignore unnecessary directories
        if any(
            part in IGNORED_DIRS
            for part in relative_parts
        ):
            continue

        relative_path = str(
            path.relative_to(repo_path)
        ).replace("\\", "/")

        files.append(relative_path)

        extension = path.suffix.lower()

        language = EXTENSION_TO_LANGUAGE.get(
            extension
        )

        if language:

            languages[language] = (
                languages.get(language, 0) + 1
            )

    files.sort()

    important_files = [
        file
        for file in files
        if Path(file).name in IMPORTANT_FILES
    ]

    return {

        "file_count": len(files),

        "files": files[:300],

        "languages": dict(
            sorted(
                languages.items(),
                key=lambda item: item[1],
                reverse=True
            )
        ),

        "important_files": important_files

    }