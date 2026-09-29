from dotenv import load_dotenv
import os

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()


def get_llm():

    api_key = os.getenv(
        "MISTRAL_API_KEY"
    )

    if not api_key:
        raise ValueError(
            "MISTRAL_API_KEY is missing. "
            "Please add it to your .env file."
        )

    model = ChatMistralAI(
        model="ministral-8b-latest",
        temperature=0.9,
        api_key=api_key
    )

    return model


def generate_repository_overview(
    repository_name: str,
    scan_data: dict
):

    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages(
        [

            (
                "system",

                """
You are RepoPilot.

You are a software repository analyst.

Your job is to explain a repository
using ONLY the metadata provided by
the application.

Do not invent files,
dependencies,
frameworks,
or architecture.
"""
            ),

            (
                "human",

                """
Repository name:
{repository_name}

Detected languages:
{languages}

Important files:
{important_files}

Total files:
{file_count}

Give a beginner-friendly repository overview.

Include:

1. Project type
2. Detected technologies
3. Important files
4. What we should inspect next

If the information is insufficient,
clearly say that.
"""
            )

        ]
    )

    chain = prompt | llm

    response = chain.invoke({

        "repository_name": repository_name,

        "languages": scan_data[
            "languages"
        ],

        "important_files": scan_data[
            "important_files"
        ],

        "file_count": scan_data[
            "file_count"
        ]

    })

    return response.content