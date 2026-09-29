
#C:\Users\Akanksha\Desktop\GenAI\Projects\RepoPilot\app\vector_store.py
import chromadb


COLLECTION_NAME = "repopilot_code_v1"


def get_chroma_client():
    """
    Create a persistent ChromaDB client.

    Data will be stored inside:
    ./chroma_db
    """

    client = chromadb.PersistentClient(
        path="./chroma_db"
    )

    return client


def get_collection():
    """
    Get or create the RepoPilot
    code collection.
    """

    client = get_chroma_client()

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    return collection


def store_embedded_chunks(
    embedded_chunks: list[dict],
    repository_name: str
):
    """
    Store real repository code chunks
    and their embeddings inside ChromaDB.
    """

    if not embedded_chunks:
        print("\nNo chunks to store.")

        return 0

    collection = get_collection()

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for chunk in embedded_chunks:

        metadata = chunk["metadata"]

        file_path = metadata["file_path"]
        chunk_index = metadata["chunk_index"]

        # Create a unique ID for every chunk
        chunk_id = (
            f"{repository_name}"
            f"::{file_path}"
            f"::{chunk_index}"
        )

        ids.append(chunk_id)

        documents.append(
            chunk["content"]
        )

        embeddings.append(
            chunk["embedding"]
        )

        # Add repository information
        # to metadata
        chunk_metadata = {
            **metadata,
            "repository": repository_name
        }

        metadatas.append(
            chunk_metadata
        )

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(ids)


def get_collection_count():

    collection = get_collection()

    return collection.count()


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("       RepoPilot - Phase 2D")
    print("       Real Vector Store")
    print("=" * 60)

    collection = get_collection()

    print("\nChromaDB initialized.")

    print(f"Collection: {collection.name}")

    print(
        f"Existing documents: "
        f"{collection.count()}"
    )

    print("\n" + "=" * 60)