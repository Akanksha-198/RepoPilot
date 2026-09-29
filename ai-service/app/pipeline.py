from pathlib import Path

from .embeddings import (
    embed_chunks
)

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

from .vector_store import (
    store_embedded_chunks,
    get_collection_count
)


def analyze_repository(
    github_url: str,
    clone_location: str
) -> dict:

    """
    RepoPilot Pipeline

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
    Generate embeddings
        ↓
    Store embeddings in ChromaDB
        ↓
    Generate Mistral AI overview
        ↓
    Return complete result
    """

    print("\nGetting repository information...")

    repo_name = repository_name(github_url)

    print(f"Repository: {repo_name}")


    print("\nCloning repository...")

    clone_location = Path(clone_location)

    repo_path = clone_repository(
        github_url,
        clone_location
    )

    print(f"Repository path: {repo_path}")


    print("\nScanning repository...")

    scan_data = scan_repository(repo_path)

    print(
        f"Files found: "
        f"{scan_data['file_count']}"
    )


    print("\nReading source files...")

    source_files = read_source_files(repo_path)

    print(
        f"Source files read: "
        f"{len(source_files)}"
    )


    print("\nCreating code chunks...")

    chunks = chunk_source_files(source_files)

    print(
        f"Chunks created: "
        f"{len(chunks)}"
    )


    print("\n" + "-" * 60)
    print("                 Code Chunks")
    print("-" * 60)

    for chunk in chunks:

        metadata = chunk["metadata"]

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

        print("   Preview:")

        preview = chunk["content"][:200]

        print(preview)


    # --------------------------------------------------
    # PHASE 2C
    # Generate embeddings
    # --------------------------------------------------

    print("\nGenerating code embeddings...")

    embedded_chunks = embed_chunks(chunks)

    print(
        f"Embeddings generated: "
        f"{len(embedded_chunks)}"
    )


    print("\n" + "-" * 60)
    print("             Embedding Information")
    print("-" * 60)

    if embedded_chunks:

        first_embedding = (
            embedded_chunks[0]["embedding"]
        )

        print(
            f"\nVector Dimension: "
            f"{len(first_embedding)}"
        )

        print("\nFirst 5 values:")

        print(
            first_embedding[:5]
        )

    else:

        print(
            "\nNo embeddings were generated."
        )


    # --------------------------------------------------
    # PHASE 2D
    # Store embeddings in ChromaDB
    # --------------------------------------------------

    print(
        "\nStoring embeddings in ChromaDB..."
    )

    stored_count = store_embedded_chunks(
        embedded_chunks,
        repo_name
    )

    print(
        f"Chunks stored in ChromaDB: "
        f"{stored_count}"
    )

    print(
        f"Total documents in ChromaDB: "
        f"{get_collection_count()}"
    )


    # --------------------------------------------------
    # AI Repository Overview
    # --------------------------------------------------

    print("\nGenerating AI overview...")

    ai_overview = generate_repository_overview(
        repo_name,
        scan_data
    )


    return {
        "repository": repo_name,
        "path": str(repo_path),
        "scan": scan_data,
        "source_files": source_files,
        "chunks": chunks,
        "embedded_chunks": embedded_chunks,
        "stored_chunks": stored_count,
        "ai_overview": ai_overview
    }


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("                 RepoPilot")
    print("       Phase 2D - ChromaDB")
    print("=" * 60)


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


        print("\n" + "=" * 60)
        print("             RepoPilot Analysis")
        print("=" * 60)


        print(
            f"\nRepository: "
            f"{result['repository']}"
        )

        print(
            f"Local Path: "
            f"{result['path']}"
        )


        scan = result["scan"]


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

        print(
            f"Embedded Chunks: "
            f"{len(result['embedded_chunks'])}"
        )

        print(
            f"Stored in ChromaDB: "
            f"{result['stored_chunks']}"
        )


        print("\nLanguages:")

        if scan["languages"]:

            for language, count in scan["languages"].items():

                print(
                    f"  {language}: "
                    f"{count} files"
                )

        else:

            print(
                "  No programming languages detected."
            )


        print("\nImportant Files:")

        if scan["important_files"]:

            for file in scan["important_files"]:

                print(
                    f"  {file}"
                )

        else:

            print(
                "  No predefined important files found."
            )


        print("\n" + "-" * 60)
        print("              Source Files")
        print("-" * 60)


        for file in result["source_files"]:

            print(
                f"\n📄 {file['path']}"
            )

            print(
                f"   Extension: "
                f"{file['extension']}"
            )


        print("\n" + "-" * 60)
        print("                 Code Chunks")
        print("-" * 60)


        for chunk in result["chunks"]:

            metadata = chunk["metadata"]

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

            print("   Preview:")

            print(
                chunk["content"][:200]
            )


        print("\n" + "-" * 60)
        print("             ChromaDB Information")
        print("-" * 60)


        print(
            f"\nStored Chunks: "
            f"{result['stored_chunks']}"
        )

        print(
            f"Total ChromaDB Documents: "
            f"{get_collection_count()}"
        )


        print("\n" + "=" * 60)
        print("           AI Repository Overview")
        print("=" * 60)

        print(
            result["ai_overview"]
        )


        print("\n" + "=" * 60)
        print("       Phase 2D completed successfully!")
        print("=" * 60)


    except Exception as error:

        print("\nERROR:")

        print(error)