from .model import get_llm
from .repository_tools import read_repository_file


def propose_repair(
    repository_path: str,
    file_path: str,
    failure_analysis: str
) -> dict:

    # --------------------------------------------------------
    # Read the actual current file
    # --------------------------------------------------------

    file_data = read_repository_file(
        repository_path,
        file_path
    )

    current_content = file_data["content"]

    # --------------------------------------------------------
    # Ask Mistral for a MINIMAL repair
    # --------------------------------------------------------

    llm = get_llm()

    prompt = f"""
You are the repair engine of RepoPilot.

Your job is to repair ONE existing repository file
after an automated validation/build/test failure.

IMPORTANT RULES:

1. Make the SMALLEST possible change required to fix
   the reported validation failure.

2. DO NOT rewrite the entire file.

3. DO NOT replace working code with a different
   implementation.

4. DO NOT redesign the application.

5. DO NOT add unrelated features.

6. Preserve all existing functionality.

7. Only modify the requested file.

8. Use the actual file content provided below.

9. The validation error is the primary evidence.
   Fix the specific error reported by validation.

10. If the failure is caused by one missing character,
    bracket, parenthesis, quote, semicolon, import, etc.,
    make only that small correction.

11. The new code must contain the COMPLETE contents
    of the same file after the repair.

12. Do NOT modify the repository yourself.

13. Do NOT invent files, functions, requirements,
    or application behavior.

14. If the available information is insufficient to
    safely determine a repair, say so instead of
    inventing a solution.

FAILURE ANALYSIS:
{failure_analysis}

FILE PATH:
{file_path}

CURRENT FILE CONTENT:
{current_content}

Return EXACTLY this format:

FILE:
{file_path}

NEW_CODE:
<complete file content after the MINIMAL repair>

REASON:
<short explanation of exactly what was changed and why>

Remember:
The goal is NOT to rewrite the file.
The goal is to make the smallest safe repair
that addresses the reported validation failure.
"""

    response = llm.invoke(prompt)

    content = response.content.strip()

    # --------------------------------------------------------
    # Parse structured response
    # --------------------------------------------------------

    if "FILE:" not in content:
        raise ValueError(
            "Repair proposal is missing FILE section."
        )

    if "NEW_CODE:" not in content:
        raise ValueError(
            "Repair proposal is missing NEW_CODE section."
        )

    if "REASON:" not in content:
        raise ValueError(
            "Repair proposal is missing REASON section."
        )

    file_section = content.split(
        "FILE:",
        1
    )[1]

    proposed_file_path = file_section.split(
        "NEW_CODE:",
        1
    )[0].strip()

    new_code_section = content.split(
        "NEW_CODE:",
        1
    )[1]

    new_code = new_code_section.split(
        "REASON:",
        1
    )[0].strip()

    reason = content.split(
        "REASON:",
        1
    )[1].strip()

    # --------------------------------------------------------
    # Validate response
    # --------------------------------------------------------

    if not proposed_file_path:
        raise ValueError(
            "Repair proposal did not specify a file path."
        )

    if not new_code:
        raise ValueError(
            "Repair proposal did not contain new file content."
        )

    if proposed_file_path != file_path:
        raise ValueError(
            "Repair proposal attempted to modify a "
            "different file than the validation error."
        )
        
    # --------------------------------------------------------
    # Safety check: reject suspiciously large rewrites
    # --------------------------------------------------------

    old_lines = current_content.splitlines()
    new_lines = new_code.splitlines()

    if len(old_lines) > 0:

        line_growth = len(new_lines) / len(old_lines)

        if line_growth > 5:
            raise ValueError(
                "Repair proposal was rejected because it "
                "rewrites too much of the original file. "
                "RepoPilot requires a minimal repair."
            )
        
        
        
        
        

    return {
        "file_path": proposed_file_path,
        "old_content": current_content,
        "new_content": new_code,
        "reason": reason
    }