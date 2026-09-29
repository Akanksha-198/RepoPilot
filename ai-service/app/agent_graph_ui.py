from langgraph.graph import (
    StateGraph,
    START,
    END
)

from .agent_state import AgentState

from .model import get_llm

from .retriever import retrieve_code

from .repository_tools import (
    read_repository_file
)

from .diff_tool import (
    generate_full_file_diff
)

from .file_tools import (
    apply_full_file_change
)

from .validator import (
    validate_repository
)


# ============================================================
# HELPER (NOT A GRAPH NODE)
# Ingest Repository (scan -> chunk -> embed -> store)
#
# This is called ONCE by Streamlit right after cloning a
# repository (or when the user clicks "Re-index"), NOT on
# every "Analyze" click, to avoid re-embedding the whole
# repository through the Mistral API on every request.
# ============================================================

def ingest_repository_files(
    repository_path: str,
    repository_name: str
) -> int:
    """
    Read all supported source files from the repository,
    chunk them, embed them, and store them in ChromaDB
    scoped to this repository's name so retrieval never
    mixes code from different repositories.

    Returns the number of chunks stored.
    """

    from pathlib import Path
    from .code_reader import read_source_files
    from .chunker import chunk_source_files
    from .embeddings import embed_chunks
    from .vector_store import store_embedded_chunks

    repo_path = Path(
        repository_path
    ).resolve()

    source_files = read_source_files(
        repo_path
    )

    if not source_files:
        return 0

    chunks = chunk_source_files(
        source_files
    )

    if not chunks:
        return 0

    embedded_chunks = embed_chunks(
        chunks
    )

    stored_count = store_embedded_chunks(
        embedded_chunks,
        repository_name
    )

    return stored_count


# ============================================================
# NODE 1
# Understand Task
# ============================================================

def understand_task(state: AgentState):

    llm = get_llm()

    prompt = f"""
You are RepoPilot, an AI software engineering assistant.

Understand the user's request.

User request:
{state["user_request"]}

Explain:

1. What the user wants
2. Which part of the repository is probably involved
3. What kind of engineering task this is

Do not propose code changes yet.
"""

    response = llm.invoke(prompt)

    return {
        "task_understanding": response.content
    }


# ============================================================
# NODE 2
# Retrieve Relevant Code
# ============================================================

def retrieve_relevant_code(state: AgentState):

    results = retrieve_code(
        state["user_request"],
        repository_name=state["repository_name"],
        n_results=3
    )

    return {
        "retrieved_sources": results
    }


# ============================================================
# NODE 3
# Analyze Repository
# ============================================================

def analyze_repository(state: AgentState):

    llm = get_llm()

    context = ""

    for index, source in enumerate(
        state.get("retrieved_sources", []),
        start=1
    ):

        metadata = source["metadata"]

        context += f"""
SOURCE {index}

File:
{metadata["file_path"]}

Lines:
{metadata["start_line"]}-{metadata["end_line"]}

Code:
{source["content"]}

--------------------------------
"""

    prompt = f"""
You are RepoPilot.

Analyze the repository code relevant to the user's request.

User request:
{state["user_request"]}

Task understanding:
{state["task_understanding"]}

Retrieved code:
{context}

Explain:

1. Which files are relevant
2. How the current code works
3. What part needs to change
4. Important dependencies or risks

Do not write the final code yet.
"""

    response = llm.invoke(prompt)

    return {
        "analysis": response.content
    }


# ============================================================
# NODE 4
# Create Plan
# ============================================================

def create_plan(state: AgentState):

    llm = get_llm()

    prompt = f"""
You are RepoPilot.

Create a simple implementation plan.

User request:
{state["user_request"]}

Analysis:
{state["analysis"]}

Return only a numbered list.

Create 3 to 7 steps.

Do not write code.
"""

    response = llm.invoke(prompt)

    lines = response.content.splitlines()

    plan = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line[0].isdigit():

            parts = line.split(".", 1)

            if len(parts) == 2:

                plan.append(
                    parts[1].strip()
                )

    return {
        "plan": plan
    }


# ============================================================
# NODE 5
# Generate Proposed Change
# ============================================================

def generate_proposed_changes(state: AgentState):

    llm = get_llm()

    context = ""

    for source in state.get(
        "retrieved_sources",
        []
    ):

        metadata = source["metadata"]

        context += f"""
FILE:
{metadata["file_path"]}

CODE:
{source["content"]}

--------------------------------
"""

    prompt = f"""
You are RepoPilot, an AI software engineering assistant.

The user wants to make this change:

{state["user_request"]}

Repository analysis:
{state["analysis"]}

Relevant repository code:
{context}

Your task is to propose the required code modification.

Return EXACTLY this structure:

FILE:
<repository relative file path>

NEW_CODE:
<complete replacement content for that file>

REASON:
<short explanation>

IMPORTANT:

- Identify the correct repository file.
- The FILE path must be a path from the repository root.
- NEW_CODE must contain the COMPLETE CONTENT of the modified file.
- Do NOT provide OLD_CODE.
- Do NOT use markdown code fences.
- Do NOT modify files.
- Do not invent files that are not supported by the repository context.
"""

    response = llm.invoke(prompt)

    text = response.content

    file_path = ""
    new_code = ""
    reason = ""

    # --------------------------------------------------------
    # Parse FILE
    # --------------------------------------------------------

    if "FILE:" in text:

        file_path = (
            text
            .split("FILE:", 1)[1]
            .split("NEW_CODE:", 1)[0]
            .strip()
        )

    # --------------------------------------------------------
    # Parse NEW_CODE
    # --------------------------------------------------------

    if "NEW_CODE:" in text:

        new_code = (
            text
            .split("NEW_CODE:", 1)[1]
            .split("REASON:", 1)[0]
            .strip()
        )

    # --------------------------------------------------------
    # Parse REASON
    # --------------------------------------------------------

    if "REASON:" in text:

        reason = (
            text
            .split("REASON:", 1)[1]
            .strip()
        )

    return {
        "proposed_changes": [
            {
                "file_path": file_path,
                "old_content": "",
                "new_content": new_code,
                "reason": reason
            }
        ]
    }

# ============================================================
# NODE 6
# Verify Against Actual File + Generate Diff
# ============================================================

def create_change_diff(state: AgentState):

    # --------------------------------------------------------
    # STEP -1
    # If Node 5 already determined no change is needed, honor
    # that verdict as-is -- don't overwrite it with the generic
    # "failed" message below, which is for genuine parse
    # failures, not this legitimate case.
    # --------------------------------------------------------

    existing_change_result = state.get(
        "change_result",
        {}
    )

    if existing_change_result.get("status") == "no_change_needed":
        return {
            "diff": "",
            "change_result": existing_change_result
        }

    proposed_changes = state.get(
        "proposed_changes",
        []
    )

    if not proposed_changes:
        return {
            "diff": "",
            "change_result": {
                "status": "failed",
                "message": (
                    "No proposed change was generated. "
                    "This usually means the AI's response could "
                    "not be parsed -- try rephrasing the task."
                )
            }
        }

    change = proposed_changes[0]

    file_path = change.get(
        "file_path",
        ""
    ).strip()

    # --------------------------------------------------------
    # STEP 0
    # Validate the AI-proposed file path
    # --------------------------------------------------------

    if not file_path:
        return {
            "diff": "",
            "change_result": {
                "status": "failed",
                "message": (
                    "The AI did not specify a file to modify."
                )
            }
        }

    from pathlib import Path

    repository_path = Path(
        state["repository_path"]
    ).resolve()

    target_path = (
        repository_path / file_path
    ).resolve()

    # --------------------------------------------------------
    # SECURITY CHECK
    # The proposed file must remain inside repository
    # --------------------------------------------------------

    try:
        target_path.relative_to(
            repository_path
        )

    except ValueError:

        return {
            "diff": "",
            "change_result": {
                "status": "failed",
                "message": (
                    "Unsafe proposed file path. "
                    "The target file must remain "
                    "inside the repository."
                )
            }
        }

    # --------------------------------------------------------
    # EXISTENCE CHECK
    # Prevent AI from inventing files such as index.html
    # --------------------------------------------------------

    if not target_path.exists():

        return {
            "diff": "",
            "change_result": {
                "status": "failed",
                "message": (
                    f"Repository file not found: "
                    f"{file_path}"
                )
            }
        }

    if not target_path.is_file():

        return {
            "diff": "",
            "change_result": {
                "status": "failed",
                "message": (
                    f"Proposed path is not a file: "
                    f"{file_path}"
                )
            }
        }

    # --------------------------------------------------------
    # STEP 1
    # Read the ACTUAL file from disk
    # --------------------------------------------------------

    actual_file = read_repository_file(
        state["repository_path"],
        file_path
    )

    actual_content = actual_file["content"]

    # --------------------------------------------------------
    # STEP 2
    # Filesystem is the source of truth
    #
    # We DO NOT use old_content generated by the AI.
    # --------------------------------------------------------

    old_content = actual_content

    # --------------------------------------------------------
    # STEP 3
    # Get AI-generated new content
    # --------------------------------------------------------

    new_content = change.get(
        "new_content",
        ""
    )

    if not new_content.strip():

        return {
            "diff": "",
            "change_result": {
                "status": "failed",
                "message": (
                    "The AI did not generate "
                    "new file content."
                )
            }
        }

    # --------------------------------------------------------
    # STEP 4
    # Generate diff between:
    #
    # actual file on disk
    #          VS
    # AI proposed new file
    # --------------------------------------------------------

    diff = generate_full_file_diff(
        state["repository_path"],
        file_path,
        old_content,
        new_content
    )

    # --------------------------------------------------------
    # STEP 5
    # Store the ACTUAL old content
    #
    # This will later be used when applying the change.
    # --------------------------------------------------------

    updated_change = {
        **change,
        "file_path": file_path,
        "old_content": old_content
    }

    return {
        "proposed_changes": [
            updated_change
        ],
        "diff": diff
    }


# ============================================================
# NODE 7
# Apply Approved Change
# ============================================================

def apply_approved_change(state: AgentState):

    if not state.get(
        "change_approved",
        False
    ):

        return {
            "change_result": {
                "status": "not_applied",
                "message": "Change was rejected."
            }
        }

    proposed_changes = state.get(
        "proposed_changes",
        []
    )

    if not proposed_changes:

        return {
            "change_result": {
                "status": "failed",
                "message": "No proposed change available."
            }
        }

    change = proposed_changes[0]

    result = apply_full_file_change(
        state["repository_path"],
        change["file_path"],
        change["old_content"],
        change["new_content"]
    )

    return {
        "change_result": result
    }


# ============================================================
# NODE 8
# Validate Change
# ============================================================

def validate_change(state: AgentState):

    repository_path = state[
        "repository_path"
    ]

    validation_result = validate_repository(
        repository_path
    )

    return {
        "validation_result": validation_result
    }



# ============================================================
# NODE 9
# Generate Repair Diff
# ============================================================

def create_repair_diff(state: AgentState):
    """
    Generate a diff for an AI-proposed repair.

    IMPORTANT:
    This function does NOT modify the repository.
    It only creates a repair proposal and diff for human review.
    """

    validation_result = state.get(
        "validation_result",
        {}
    )

    # --------------------------------------------------------
    # STEP 1
    # Make sure validation actually failed
    # --------------------------------------------------------

    if validation_result.get("success", False):
        return {
            "failure_analysis": "",
            "repair_proposal": {},
            "repair_diff": "",
            "repair_result": {
                "status": "not_needed",
                "message": "Validation passed. No repair is needed."
            }
        }

    # --------------------------------------------------------
    # STEP 2
    # Analyze the validation failure
    # --------------------------------------------------------

    from .failure_analyzer import analyze_failure

    failure_analysis = analyze_failure(
        validation_result
    )

    # --------------------------------------------------------
    # STEP 3
    # Get the file involved in the failure
    # --------------------------------------------------------

    results = validation_result.get(
        "results",
        []
    )

    if not results:
        return {
            "failure_analysis": failure_analysis,
            "repair_proposal": {},
            "repair_diff": "",
            "repair_result": {
                "status": "failed",
                "message": (
                    "No validation output was available "
                    "to generate a repair."
                )
            }
        }

    # --------------------------------------------------------
    # STEP 4
    # For Phase 5D.1 we use the known repair file
    # from the validation output.
    #
    # Later we will make this automatic.
    # --------------------------------------------------------

    import re

    stderr = results[0].get(
        "stderr",
        ""
    )

    match = re.search(
        r"([A-Za-z0-9_./\\-]+\.(?:js|jsx|ts|tsx|py)):(\d+)",
        stderr
    )

    if not match:
        return {
            "failure_analysis": failure_analysis,
            "repair_proposal": {},
            "repair_diff": "",
            "repair_result": {
                "status": "failed",
                "message": (
                    "Could not identify the source file "
                    "from the validation output."
                )
            }
        }

    file_path = match.group(1)

    # Convert Windows absolute path into repository-relative path
    from pathlib import Path

    repository_path = Path(
        state["repository_path"]
    ).resolve()

    error_file = Path(
        file_path
    ).resolve()

    try:
        relative_file = error_file.relative_to(
            repository_path
        )
    except ValueError:
        return {
            "failure_analysis": failure_analysis,
            "repair_proposal": {},
            "repair_diff": "",
            "repair_result": {
                "status": "failed",
                "message": (
                    "The validation error points to a file "
                    "outside the repository."
                )
            }
        }

    file_path = str(
        relative_file
    ).replace("\\", "/")

    # --------------------------------------------------------
    # STEP 5
    # Generate repair proposal
    # --------------------------------------------------------

    from .repair_proposer import propose_repair

    repair_proposal = propose_repair(
        repository_path=state["repository_path"],
        file_path=file_path,
        failure_analysis=failure_analysis
    )

    # --------------------------------------------------------
    # STEP 6
    # Generate diff
    # --------------------------------------------------------

    diff = generate_full_file_diff(
        state["repository_path"],
        repair_proposal["file_path"],
        repair_proposal["old_content"],
        repair_proposal["new_content"]
    )

    return {
        "failure_analysis": failure_analysis,
        "repair_proposal": repair_proposal,
        "repair_diff": diff,
        "repair_result": {
            "status": "ready_for_review",
            "message": (
                "Repair proposal generated. "
                "Human approval is required before applying it."
            )
        }
    }


# ============================================================
# NODE 10
# Apply Approved Repair
# ============================================================

def apply_approved_repair(state: AgentState):
    """
    Apply an AI-generated repair only after
    explicit human approval.
    """

    # --------------------------------------------------------
    # STEP 1
    # Check human approval
    # --------------------------------------------------------

    if not state.get("repair_approved", False):
        return {
            "repair_result": {
                "status": "not_applied",
                "message": "Repair was rejected."
            }
        }

    # --------------------------------------------------------
    # STEP 2
    # Get repair proposal
    # --------------------------------------------------------

    repair_proposal = state.get(
        "repair_proposal",
        {}
    )

    if not repair_proposal:
        return {
            "repair_result": {
                "status": "failed",
                "message": "No repair proposal is available."
            }
        }

    # --------------------------------------------------------
    # STEP 3
    # Validate required repair fields
    # --------------------------------------------------------

    file_path = repair_proposal.get(
        "file_path",
        ""
    ).strip()

    old_content = repair_proposal.get(
        "old_content",
        ""
    )

    new_content = repair_proposal.get(
        "new_content",
        ""
    )

    if not file_path:
        return {
            "repair_result": {
                "status": "failed",
                "message": "Repair proposal does not specify a file."
            }
        }

    if not new_content.strip():
        return {
            "repair_result": {
                "status": "failed",
                "message": "Repair proposal does not contain new file content."
            }
        }

    # --------------------------------------------------------
    # STEP 4
    # Apply the approved repair
    #
    # apply_full_file_change() already:
    # - checks the repository path
    # - verifies old content
    # - creates a backup
    # - writes the new content
    # --------------------------------------------------------

    result = apply_full_file_change(
        state["repository_path"],
        file_path,
        old_content,
        new_content
    )

    return {
        "repair_result": result
    }



# ============================================================
# BUILD GRAPH
# ============================================================

def build_ui_agent_graph():

    graph = StateGraph(
        AgentState
    )

    graph.add_node(
        "understand_task",
        understand_task
    )

    graph.add_node(
        "retrieve_code",
        retrieve_relevant_code
    )

    graph.add_node(
        "analyze_repository",
        analyze_repository
    )

    graph.add_node(
        "create_plan",
        create_plan
    )

    graph.add_node(
        "generate_proposed_changes",
        generate_proposed_changes
    )

    graph.add_node(
        "create_change_diff",
        create_change_diff
    )

    graph.add_node(
        "apply_approved_change",
        apply_approved_change
    )

    graph.add_node(
        "validate_change",
        validate_change
    )

    # --------------------------------------------------------
    # Main analysis flow
    # --------------------------------------------------------

    graph.add_edge(
        START,
        "understand_task"
    )

    graph.add_edge(
        "understand_task",
        "retrieve_code"
    )

    graph.add_edge(
        "retrieve_code",
        "analyze_repository"
    )

    graph.add_edge(
        "analyze_repository",
        "create_plan"
    )

    graph.add_edge(
        "create_plan",
        "generate_proposed_changes"
    )

    graph.add_edge(
        "generate_proposed_changes",
        "create_change_diff"
    )

    # --------------------------------------------------------
    # STOP HERE
    #
    # Streamlit will decide whether to apply.
    # --------------------------------------------------------

    graph.add_edge(
        "create_change_diff",
        END
    )

    return graph.compile()


# ============================================================
# APPLY GRAPH
# ============================================================

def build_apply_graph():

    graph = StateGraph(
        AgentState
    )

    graph.add_node(
        "apply_approved_change",
        apply_approved_change
    )

    graph.add_node(
        "validate_change",
        validate_change
    )

    graph.add_edge(
        START,
        "apply_approved_change"
    )

    graph.add_edge(
        "apply_approved_change",
        "validate_change"
    )

    graph.add_edge(
        "validate_change",
        END
    )

    return graph.compile()


# ============================================================
# REPAIR APPLY GRAPH
# ============================================================

def build_repair_apply_graph():
    """
    Apply an approved repair and validate the repository again.
    """

    graph = StateGraph(
        AgentState
    )

    graph.add_node(
        "apply_approved_repair",
        apply_approved_repair
    )

    graph.add_node(
        "validate_change",
        validate_change
    )

    graph.add_edge(
        START,
        "apply_approved_repair"
    )

    graph.add_edge(
        "apply_approved_repair",
        "validate_change"
    )

    graph.add_edge(
        "validate_change",
        END
    )

    return graph.compile()