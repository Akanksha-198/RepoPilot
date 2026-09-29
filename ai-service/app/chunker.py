from pathlib import Path


# ==========================================
# Chunk configuration
# ==========================================

DEFAULT_CHUNK_SIZE = 80
DEFAULT_OVERLAP = 10


# ==========================================
# Chunk one source file
# ==========================================

def chunk_source_file(
    source_file: dict,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
) -> list:

    """
    Split one source file into smaller chunks.

    Example:

    200-line file

    Chunk 0 → lines 1-80
    Chunk 1 → lines 71-150
    Chunk 2 → lines 141-200
    """

    content = source_file["content"]

    file_path = source_file["path"]

    extension = source_file["extension"]


    # --------------------------------------
    # Convert code into lines
    # --------------------------------------

    lines = content.splitlines()


    # Empty file
    if not lines:
        return []


    # --------------------------------------
    # Validate configuration
    # --------------------------------------

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0"
        )


    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative"
        )


    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )


    # --------------------------------------
    # Create chunks
    # --------------------------------------

    chunks = []

    start = 0

    chunk_index = 0


    while start < len(lines):

        # Calculate end of current chunk
        end = min(
            start + chunk_size,
            len(lines)
        )


        # Extract lines
        chunk_lines = lines[
            start:end
        ]


        # Convert lines back to text
        chunk_content = "\n".join(
            chunk_lines
        )


        # ----------------------------------
        # Create chunk object
        # ----------------------------------

        chunks.append(
            {
                "content": chunk_content,

                "metadata": {

                    "file_path": file_path,

                    "extension": extension,

                    "chunk_index": chunk_index,

                    "start_line": start + 1,

                    "end_line": end

                }
            }
        )


        # ----------------------------------
        # Move to next chunk
        # ----------------------------------

        next_start = end - overlap


        # Safety check
        if next_start <= start:
            break


        start = next_start

        chunk_index += 1


    return chunks


# ==========================================
# Chunk complete repository
# ==========================================

def chunk_source_files(
    source_files: list,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
) -> list:

    """
    Create chunks from all source files.

    Returns one flat list containing
    chunks from every source file.
    """

    all_chunks = []


    for source_file in source_files:

        file_chunks = chunk_source_file(
            source_file,
            chunk_size,
            overlap
        )


        all_chunks.extend(
            file_chunks
        )


    return all_chunks
  
