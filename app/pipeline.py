from pathlib import Path


from .github_Tool import (
    clone_repository,
    repository_name
)


from .scanner import (
    scan_repository
)


from .code_reader import (
    read_source_files
)


from .chunker import (
    chunk_source_files
)


from .model import (
    generate_repository_overview
)


def analyze_repository(
    github_url: str,
    clone_location: str
) -> dict:

    """
    RepoPilot Phase 2B Pipeline

    Complete flow:

    GitHub URL
        ↓
    Repository name
        ↓
    Clone repository
        ↓
    Scan repository
        ↓
    Read source files
        ↓
    Create code chunks
        ↓
    Generate Mistral AI overview
        ↓
    Return result
    """

    # ==========================================
    # STEP 1
    # Get repository name
    # ==========================================

    print(
        "\nGetting repository information..."
    )

    repo_name = repository_name(
        github_url
    )

    print(
        f"Repository: {repo_name}"
    )


    # ==========================================
    # STEP 2
    # Clone repository
    # ==========================================

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


    # ==========================================
    # STEP 3
    # Scan repository
    # ==========================================

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


    # ==========================================
    # STEP 4
    # Read source files
    # ==========================================

    print(
        "\nReading source files..."
    )

    source_files = read_source_files(
        repo_path
    )

    print(
        f"Source files read: "
        f"{len(source_files)}"
    )


    # ==========================================
    # STEP 5
    # Create code chunks
    # ==========================================

    print(
        "\nCreating code chunks..."
    )

    chunks = chunk_source_files(
        source_files
    )

    print(
        f"Chunks created: "
        f"{len(chunks)}"
    )


    # ==========================================
    # STEP 6
    # Show chunk information
    # ==========================================

    print(
        "\n" + "-" * 60
    )

    print(
        "                 Code Chunks"
    )

    print(
        "-" * 60
    )


    for chunk in chunks:

        metadata = chunk[
            "metadata"
        ]


        print(
            f"\n📄 File: "
            f"{metadata['file_path']}"
        )


        print(
            f"   Chunk: "
            f"{metadata['chunk_index']}"
        )


        print(
            f"   Lines: "
            f"{metadata['start_line']}"
            f"-"
            f"{metadata['end_line']}"
        )


        print(
            "   Preview:"
        )


        preview = chunk[
            "content"
        ][:200]


        print(
            preview
        )


    # ==========================================
    # STEP 7
    # Generate AI overview
    # ==========================================

    print(
        "\nGenerating AI overview..."
    )

    ai_overview = (
        generate_repository_overview(
            repo_name,
            scan_data
        )
    )


    # ==========================================
    # STEP 8
    # Return complete result
    # ==========================================

    return {

        "repository": repo_name,

        "path": str(
            repo_path
        ),

        "scan": scan_data,

        "source_files": source_files,

        "chunks": chunks,

        "ai_overview": ai_overview

    }


# ==========================================
# TERMINAL TESTING
# ==========================================

if __name__ == "__main__":

    print(
        "\n" + "=" * 60
    )

    print(
        "                 RepoPilot"
    )

    print(
        "          Phase 2B - Code Chunking"
    )

    print(
        "=" * 60
    )


    # ==========================================
    # User input
    # ==========================================

    github_url = input(
        "\nEnter GitHub repository URL: "
    ).strip()


    clone_location = input(
        "Enter local clone location: "
    ).strip()


    # ==========================================
    # Run pipeline
    # ==========================================

    try:

        result = analyze_repository(
            github_url,
            clone_location
        )


        # ==========================================
        # Final Analysis
        # ==========================================

        print(
            "\n" + "=" * 60
        )

        print(
            "             RepoPilot Analysis"
        )

        print(
            "=" * 60
        )


        # ==========================================
        # Repository information
        # ==========================================

        print(
            f"\nRepository: "
            f"{result['repository']}"
        )


        print(
            f"Local Path: "
            f"{result['path']}"
        )


        # ==========================================
        # Scanner information
        # ==========================================

        scan = result[
            "scan"
        ]


        print(
            f"\nTotal Files: "
            f"{scan['file_count']}"
        )


        print(
            f"Source Files: "
            f"{len(result['source_files'])}"
        )


        print(
            f"Code Chunks: "
            f"{len(result['chunks'])}"
        )


        # ==========================================
        # Languages
        # ==========================================

        print(
            "\nLanguages:"
        )


        if scan["languages"]:

            for language, count in (
                scan["languages"].items()
            ):

                print(
                    f"  {language}: "
                    f"{count} files"
                )

        else:

            print(
                "  No programming languages detected."
            )


        # ==========================================
        # Important files
        # ==========================================

        print(
            "\nImportant Files:"
        )


        if scan["important_files"]:

            for file in (
                scan["important_files"]
            ):

                print(
                    f"  {file}"
                )

        else:

            print(
                "  No predefined important files found."
            )


        # ==========================================
        # Source files
        # ==========================================

        print(
            "\n" + "-" * 60
        )

        print(
            "              Source Files"
        )

        print(
            "-" * 60
        )


        for file in result[
            "source_files"
        ]:

            print(
                f"\n📄 {file['path']}"
            )

            print(
                f"   Extension: "
                f"{file['extension']}"
            )


        # ==========================================
        # Code chunks
        # ==========================================

        print(
            "\n" + "-" * 60
        )

        print(
            "                 Code Chunks"
        )

        print(
            "-" * 60
        )


        for chunk in result[
            "chunks"
        ]:

            metadata = chunk[
                "metadata"
            ]


            print(
                f"\n📄 "
                f"{metadata['file_path']}"
            )


            print(
                f"   Chunk: "
                f"{metadata['chunk_index']}"
            )


            print(
                f"   Lines: "
                f"{metadata['start_line']}"
                f"-"
                f"{metadata['end_line']}"
            )


            print(
                "   Preview:"
            )


            print(
                chunk["content"][:200]
            )


        # ==========================================
        # AI overview
        # ==========================================

        print(
            "\n" + "=" * 60
        )

        print(
            "           AI Repository Overview"
        )

        print(
            "=" * 60
        )


        print(
            result["ai_overview"]
        )


        # ==========================================
        # Success
        # ==========================================

        print(
            "\n" + "=" * 60
        )

        print(
            "       Phase 2B completed successfully!"
        )

        print(
            "=" * 60
        )


    except Exception as error:

        print(
            "\nERROR:"
        )

        print(
            error
        )