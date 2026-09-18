from pathlib import Path

from .github_Tool import (
    clone_repository,
    repository_name
)

from .scanner import (
    scan_repository
)

from .model import (
    generate_repository_overview
)


def analyze_repository(
    github_url: str,
    clone_location: str
) -> dict:

    """
    RepoPilot Phase 1 Pipeline

    GitHub URL
        ↓
    Repository name
        ↓
    Clone repository
        ↓
    Scan repository
        ↓
    Mistral AI overview
        ↓
    Return result
    """

    # --------------------------------
    # Step 1: Repository name
    # --------------------------------

    repo_name = repository_name(
        github_url
    )

    print(
        f"\nRepository: {repo_name}"
    )


    # --------------------------------
    # Step 2: Clone repository
    # --------------------------------

    print(
        "\nCloning repository..."
    )

    clone_location = Path(
        clone_location
    )

    repo_path = clone_repository(
        github_url,
        clone_location
    )

    print(
        f"Repository path: {repo_path}"
    )


    # --------------------------------
    # Step 3: Scan repository
    # --------------------------------

    print(
        "\nScanning repository..."
    )

    scan_data = scan_repository(
        repo_path
    )

    print(
        f"Files found: "
        f"{scan_data['file_count']}"
    )


    # --------------------------------
    # Step 4: Mistral AI
    # --------------------------------

    print(
        "\nGenerating AI overview..."
    )

    ai_overview = (
        generate_repository_overview(
            repo_name,
            scan_data
        )
    )


    # --------------------------------
    # Step 5: Return result
    # --------------------------------

    return {

        "repository": repo_name,

        "path": str(repo_path),

        "scan": scan_data,

        "ai_overview": ai_overview

    }


# ==========================================
# Terminal testing
# ==========================================

if __name__ == "__main__":

    github_url = input(
        "\nEnter GitHub repository URL: "
    ).strip()

    clone_location = input(
        "Enter local clone location: "
    ).strip()

    try:

        result = analyze_repository(
            github_url,
            clone_location
        )

        print(
            "\n" + "=" * 60
        )

        print(
            "             RepoPilot Analysis"
        )

        print(
            "=" * 60
        )

        print(
            f"\nRepository: "
            f"{result['repository']}"
        )

        print(
            f"Path: "
            f"{result['path']}"
        )

        scan = result["scan"]

        print(
            f"\nTotal Files: "
            f"{scan['file_count']}"
        )

        print("\nLanguages:")

        for language, count in (
            scan["languages"].items()
        ):

            print(
                f"  {language}: "
                f"{count} files"
            )

        print("\nImportant Files:")

        for file in (
            scan["important_files"]
        ):

            print(
                f"  {file}"
            )

        print(
            "\nAI Overview:"
        )

        print(
            result["ai_overview"]
        )

        print(
            "\n" + "=" * 60
        )

        print(
            "Pipeline completed successfully!"
        )

        print(
            "=" * 60
        )

    except Exception as error:

        print(
            f"\nERROR: {error}"
        )