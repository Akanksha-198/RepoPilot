from .retriever import retrieve_code
from .model import get_llm
from langchain_core.prompts import ChatPromptTemplate


def answer_repository_question(
    question: str,
    n_results: int = 3
) -> dict:
    """
    Answer a user's question about the repository
    using retrieved code chunks.
    """

    if not question.strip():
        raise ValueError(
            "Question cannot be empty."
        )

    # --------------------------------------------------
    # Step 1: Retrieve relevant code
    # --------------------------------------------------

    retrieved_chunks = retrieve_code(
        question,
        n_results=n_results
    )

    if not retrieved_chunks:
        return {
            "answer": (
                "I could not find relevant code "
                "in the indexed repository."
            ),
            "sources": []
        }

    # --------------------------------------------------
    # Step 2: Prepare retrieved code as context
    # --------------------------------------------------

    context_parts = []

    for index, chunk in enumerate(
        retrieved_chunks,
        start=1
    ):
        metadata = chunk["metadata"]

        file_path = metadata.get(
            "file_path",
            "Unknown file"
        )

        start_line = metadata.get(
            "start_line",
            "?"
        )

        end_line = metadata.get(
            "end_line",
            "?"
        )

        content = chunk["content"]

        context_parts.append(
            f"""
SOURCE {index}

File: {file_path}
Lines: {start_line}-{end_line}

Code:
{content}
"""
        )

    context = "\n".join(context_parts)

    # --------------------------------------------------
    # Step 3: Create RAG prompt
    # --------------------------------------------------

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You are RepoPilot, an AI software repository assistant.

Answer the user's question using ONLY the
repository code provided in the context.

Rules:

1. Do not invent code or files.
2. Do not use outside knowledge.
3. If the context does not contain enough
   information, clearly say so.
4. Mention the relevant file names.
5. Mention line numbers when available.
6. Explain the answer in beginner-friendly language.
"""
        ),
        (
            "human",
            """
User question:

{question}


Retrieved repository code:

{context}


Answer the question based only on
the retrieved repository code.
"""
        )
    ])

    # --------------------------------------------------
    # Step 4: Send context + question to Mistral
    # --------------------------------------------------

    llm = get_llm()

    chain = prompt | llm

    response = chain.invoke({
        "question": question,
        "context": context
    })

    # --------------------------------------------------
    # Step 5: Prepare source information
    # --------------------------------------------------

    sources = []

    for chunk in retrieved_chunks:

        metadata = chunk["metadata"]

        sources.append({
            "file_path": metadata.get(
                "file_path",
                "Unknown"
            ),
            "start_line": metadata.get(
                "start_line"
            ),
            "end_line": metadata.get(
                "end_line"
            ),
            "distance": chunk.get(
                "distance"
            )
        })

    return {
        "answer": response.content,
        "sources": sources
    }


# ------------------------------------------------------
# Manual test
# ------------------------------------------------------

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("       RepoPilot - Phase 2F")
    print("          RAG Question Answering")
    print("=" * 60)

    question = input(
        "\nAsk a question about the repository: "
    ).strip()

    try:

        result = answer_repository_question(
            question,
            n_results=3
        )

        print("\n" + "-" * 60)
        print("                  Answer")
        print("-" * 60)

        print(
            f"\n{result['answer']}"
        )

        print("\n" + "-" * 60)
        print("                  Sources")
        print("-" * 60)

        if result["sources"]:

            for index, source in enumerate(
                result["sources"],
                start=1
            ):

                print(
                    f"\nSource {index}"
                )

                print(
                    f"File: "
                    f"{source['file_path']}"
                )

                print(
                    f"Lines: "
                    f"{source['start_line']}"
                    f"-"
                    f"{source['end_line']}"
                )

                print(
                    f"Distance: "
                    f"{source['distance']}"
                )

        else:

            print(
                "\nNo sources found."
            )

        print("\n" + "=" * 60)
        print("       Phase 2F test completed!")
        print("=" * 60)

    except Exception as error:

        print("\nERROR:")

        print(error)