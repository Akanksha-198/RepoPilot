#retriever.py
from .embeddings import generate_embedding
from .vector_store import get_collection
 
 
 
def retrieve_code(
    question: str,
    repository_name: str,
    n_results: int = 3
) -> list[dict]:
 
    """
    Search ChromaDB for code chunks
    relevant to the user's question,
    scoped to a single repository.
    """
 
    if not question.strip():
        raise ValueError(
            "Question cannot be empty."
        )
 
    if not repository_name.strip():
        raise ValueError(
            "repository_name cannot be empty."
        )
 
    # Step 1:
    # Convert user question into an embedding
 
    query_embedding = generate_embedding(
        question
    )
 
    # Step 2:
    # Get our ChromaDB collection
 
    collection = get_collection()
 
    # Step 3:
    # Search for similar code chunks,
    # restricted to this repository only
 
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"repository": repository_name}
    )
 
    retrieved_chunks = []
 
    # Step 4:
    # Convert ChromaDB result into
    # a simple Python structure
 
    documents = results.get(
        "documents",
        [[]]
    )[0]
 
    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]
 
    distances = results.get(
        "distances",
        [[]]
    )[0]
 
    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):
 
        retrieved_chunks.append({
            "content": document,
            "metadata": metadata,
            "distance": distance
        })
 
    return retrieved_chunks
 
 
if __name__ == "__main__":
 
    print("\n" + "=" * 60)
    print("       RepoPilot - Phase 2E")
    print("          Code Retriever")
    print("=" * 60)
 
    repository_name = input(
        "\nRepository name to search within: "
    ).strip()
 
    question = input(
        "\nAsk a question about the repository: "
    ).strip()
 
    try:
 
        results = retrieve_code(
            question,
            repository_name=repository_name,
            n_results=3
        )
 
        print("\n" + "-" * 60)
        print("             Retrieved Code")
        print("-" * 60)
 
        if not results:
 
            print(
                "\nNo relevant code found."
            )
 
        else:
 
            for index, result in enumerate(
                results,
                start=1
            ):
 
                metadata = result["metadata"]
 
                print(
                    f"\nResult {index}"
                )
 
                print(
                    f"File: "
                    f"{metadata['file_path']}"
                )
 
                print(
                    f"Chunk: "
                    f"{metadata['chunk_index']}"
                )
 
                print(
                    f"Lines: "
                    f"{metadata['start_line']}"
                    f"-"
                    f"{metadata['end_line']}"
                )
 
                print(
                    f"Distance: "
                    f"{result['distance']}"
                )
 
                print("\nCode:")
 
                print(
                    result["content"]
                )
 
        print("\n" + "=" * 60)
        print("       Phase 2E retrieval test complete!")
        print("=" * 60)
 
    except Exception as error:
 
        print("\nERROR:")
 
        print(error)
 
