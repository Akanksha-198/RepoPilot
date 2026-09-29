# C:\Users\Akanksha\Desktop\GenAI\Projects\RepoPilot\app\failure_analyzer.py

from .model import get_llm


def analyze_failure(
    validation_result: dict
) -> str:
    """
    Analyze a repository validation failure using the LLM.

    The LLM only analyzes the failure.
    It does not modify any files.
    """

    status = validation_result.get("status", "")

    # --------------------------------------------------
    # CASE 1: VALIDATION PASSED
    # --------------------------------------------------

    if status == "passed" or validation_result.get("success", False):

        return (
            "Validation passed. "
            "There is no failure to analyze."
        )

    # --------------------------------------------------
    # CASE 2: VALIDATION WAS SKIPPED
    # --------------------------------------------------

    if status == "skipped":

        reason = validation_result.get(
            "reason",
            "No validation was performed."
        )

        return (
            "Validation was skipped. "
            "There is no validation failure to analyze.\n\n"
            f"Reason: {reason}"
        )

    # --------------------------------------------------
    # CASE 3: VALIDATION FAILED
    # --------------------------------------------------

    results = validation_result.get(
        "results",
        []
    )

    if not results:

        return (
            "Validation failed, but no "
            "validation output was available."
        )

    # --------------------------------------------------
    # COLLECT VALIDATION ERROR INFORMATION
    # --------------------------------------------------

    error_context = ""

    for index, result in enumerate(
        results,
        start=1
    ):

        error_context += f"""
VALIDATION {index}

Command:
{" ".join(result.get("command", []))}

Return code:
{result.get("return_code")}

Standard output:
{result.get("stdout", "")}

Standard error:
{result.get("stderr", "")}

--------------------------------
"""

    # --------------------------------------------------
    # ASK MISTRAL TO ANALYZE THE FAILURE
    # --------------------------------------------------

    llm = get_llm()

    prompt = f"""
You are RepoPilot, an AI software engineering assistant.

A repository validation step failed.

Analyze the failure and explain it clearly.

Validation information:

{error_context}

Provide:

1. What failed
2. The likely cause
3. Which file or part of the project may be responsible
4. What should be checked next
5. A possible fix approach

IMPORTANT:

- Do not claim that you fixed anything.
- Do not modify files.
- Do not invent information that is not present
  in the validation output.
- Clearly state when the available information
  is insufficient.
"""

    response = llm.invoke(
        prompt
    )

    return response.content