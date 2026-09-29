

import os

from dotenv import load_dotenv
from mistralai.client import Mistral


load_dotenv()

EMBEDDING_MODEL = "codestral-embed"


def get_embedding_client():
    api_key = os.getenv("MISTRAL_API_KEY")

    if not api_key:
        raise ValueError(
            "MISTRAL_API_KEY is missing. "
            "Please add it to your .env file."
        )

    return Mistral(api_key=api_key)


def generate_embedding(text: str) -> list[float]:
    """
    Generate an embedding vector
    for one text/code chunk.
    """

    # Check the input first
    if not text or not text.strip():
        raise ValueError(
            "Cannot generate embedding for empty text."
        )

    client = get_embedding_client()

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        inputs=[text]
    )

    embedding = response.data[0].embedding

    return embedding

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Generate embeddings for all code chunks
    and attach each embedding to its chunk.
    """

    if not chunks:
        return []

    texts = []

    for chunk in chunks:

        content = chunk["content"]

        if not content or not content.strip():
            raise ValueError(
                "Found an empty chunk. "
                "Cannot generate embedding."
            )

        texts.append(content)

    client = get_embedding_client()

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        inputs=texts
    )

    embeddings = [
        item.embedding
        for item in response.data
    ]

    if len(embeddings) != len(chunks):
        raise RuntimeError(
            "Number of embeddings does not match "
            "number of chunks."
        )

    embedded_chunks = []

    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        embedded_chunk = {
            "content": chunk["content"],
            "metadata": chunk["metadata"],
            "embedding": embedding
        }

        embedded_chunks.append(
            embedded_chunk
        )

    return embedded_chunks