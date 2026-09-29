#C:\Users\Akanksha\Desktop\GenAI\Projects\RepoPilot\app\agent_graph.py

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from .task_history import create_task_history
from .agent_state import AgentState

from .model import get_llm
from .retriever import retrieve_code
from .diff_tool import generate_diff
from .file_tools import apply_code_change
from .validator import validate_repository
from .failure_analyzer import analyze_failure


# ============================================================
# NODE 1
# Understand task
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
# Retrieve relevant code
# ============================================================

def retrieve_relevant_code(state: AgentState):

    results = retrieve_code(
        state["user_request"],
        n_results=3
    )

    return {
        "retrieved_sources": results
    }


# ============================================================
# NODE 3
# Analyze repository
# ============================================================

def analyze_repository(state: AgentState):

    llm = get_llm()

    context = ""

    for index, source in enumerate(
        state["retrieved_sources"],
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
# Create implementation plan
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
# First human approval
# ============================================================

def request_approval(state: AgentState):

    print("\n" + "=" * 60)
    print("                Proposed Plan")
    print("=" * 60)

    for index, step in enumerate(
        state["plan"],
        start=1
    ):

        print(
            f"\n{index}. {step}"
        )

    approval = input(
        "\nApprove this plan? (yes/no): "
    ).strip().lower()

    approved = approval in {
        "yes",
        "y"
    }

    return {
        "approved": approved
    }


# ============================================================
# ROUTER 1
# Route after plan approval
# ============================================================

def route_after_plan_approval(state: AgentState):

    if state.get("approved", False):
        return "approved"

    return "rejected"


# ============================================================
# NODE 6
# Generate proposed change
# ============================================================

def generate_proposed_changes(
    state: AgentState
):

    if not state.get(
        "approved",
        False
    ):

        return {
            "proposed_changes": []
        }

    llm = get_llm()

    context = ""

    for index, source in enumerate(
        state["retrieved_sources"],
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

The user approved the implementation plan.

Create ONE precise code change.

User request:
{state["user_request"]}

Plan:
{state["plan"]}

Analysis:
{state["analysis"]}

Repository code:
{context}

Return EXACTLY this format:

FILE:
<repository file path>

OLD_CODE:
<exact code that must be replaced>

NEW_CODE:
<complete replacement code>

REASON:
<short explanation>

Rules:

1. Do not modify files.
2. OLD_CODE must come directly from the provided code.
3. Do not invent repository files.
4. Keep the change focused.
5. Return only one change.
"""

    response = llm.invoke(prompt)

    content = response.content

    file_path = ""
    old_code = ""
    new_code = ""
    reason = ""

    lines = content.splitlines()

    current_section = None

    sections = {
        "FILE:": "file",
        "OLD_CODE:": "old",
        "NEW_CODE:": "new",
        "REASON:": "reason"
    }

    for line in lines:

        stripped = line.strip()

        if stripped in sections:

            current_section = sections[stripped]

            continue

        if current_section == "file":

            if not file_path:

                file_path = line.strip()

        elif current_section == "old":

            old_code += line + "\n"

        elif current_section == "new":

            new_code += line + "\n"

        elif current_section == "reason":

            reason += line + "\n"

    proposed_change = {

        "file_path": file_path,

        "old_content": old_code.rstrip(),

        "new_content": new_code.rstrip(),

        "reason": reason.rstrip()

    }

    return {
        "proposed_changes": [
            proposed_change
        ]
    }


# ============================================================
# NODE 7
# Generate diff
# ============================================================

def create_change_diff(
    state: AgentState
):

    proposed_changes = state.get(
        "proposed_changes",
        []
    )

    if not proposed_changes:

        return {
            "diff": ""
        }

    repository_path = state.get(
        "repository_path",
        ""
    )

    change = proposed_changes[0]

    diff = generate_diff(

        repository_path,

        change["file_path"],

        change["old_content"],

        change["new_content"]

    )

    return {
        "diff": diff
    }


# ============================================================
# NODE 8
# Second human approval
# ============================================================

def request_change_approval(
    state: AgentState
):

    diff = state.get(
        "diff",
        ""
    )

    print("\n" + "=" * 60)
    print("              Proposed Code Diff")
    print("=" * 60)

    if not diff:

        print(
            "\nNo diff was generated."
        )

        return {
            "change_approved": False
        }

    print("\n")
    print(diff)

    approval = input(
        "\nApply this change? (yes/no): "
    ).strip().lower()

    change_approved = approval in {
        "yes",
        "y"
    }

    return {
        "change_approved": change_approved
    }


# ============================================================
# ROUTER 2
# Route after change approval
# ============================================================

def route_after_change_approval(
    state: AgentState
):

    if state.get(
        "change_approved",
        False
    ):
        return "approved"

    return "rejected"


# ============================================================
# NODE 9
# Apply approved change
# ============================================================

def apply_approved_change(
    state: AgentState
):

    if not state.get(
        "change_approved",
        False
    ):

        return {
            "change_result": {
                "status": "not_applied"
            }
        }

    proposed_changes = state.get(
        "proposed_changes",
        []
    )

    if not proposed_changes:

        return {
            "change_result": {
                "status": "not_applied",
                "reason": "No proposed change."
            }
        }

    change = proposed_changes[0]

    result = apply_code_change(

        state["repository_path"],

        change["file_path"],

        change["old_content"],

        change["new_content"]

    )

    return {
        "change_result": result
    }


# ============================================================
# NODE 10
# Validate repository
# ============================================================

def validate_change(
    state: AgentState
):

    change_result = state.get(
        "change_result",
        {}
    )

    if change_result.get(
        "status"
    ) != "modified":

        return {
            "validation_result": {
                "success": False,
                "results": [],
                "reason": (
                    "Change was not applied."
                )
            }
        }

    result = validate_repository(
        state["repository_path"]
    )

    print("\n" + "=" * 60)
    print("              Validation Result")
    print("=" * 60)

    print(
        f"\nProject type: "
        f"{result['project_type']}"
    )

    print(
        f"Validation successful: "
        f"{result['success']}"
    )

    return {
        "validation_result": result
    }


# ============================================================
# NODE 11
# Analyze validation failure
# ============================================================

def analyze_validation_failure(
    state: AgentState
):

    validation_result = state.get(
        "validation_result",
        {}
    )

    if validation_result.get(
        "success",
        False
    ):

        return {
            "failure_analysis": ""
        }

    analysis = analyze_failure(
        validation_result
    )

    print("\n" + "=" * 60)
    print("             Failure Analysis")
    print("=" * 60)

    print(
        analysis
    )

    return {
        "failure_analysis": analysis
    }


# ============================================================
# NODE 12
# Finalize result
# ============================================================

def finalize_result(
    state: AgentState
):

    validation_result = state.get(
        "validation_result",
        {}
    )

    change_result = state.get(
        "change_result",
        {}
    )

    failure_analysis = state.get(
        "failure_analysis",
        ""
    )

    validation_success = validation_result.get(
        "success",
        False
    )

    change_status = change_result.get(
        "status",
        "unknown"
    )

    plan_approved = state.get(
        "approved",
        False
    )

    change_approved = state.get(
        "change_approved",
        False
    )

    prompt = f"""
You are RepoPilot, an AI software engineering assistant.

Create a concise final summary of the repository task.

USER REQUEST:
{state.get("user_request", "")}

TASK UNDERSTANDING:
{state.get("task_understanding", "")}

PLAN APPROVED:
{plan_approved}

CHANGE APPROVED:
{change_approved}

CHANGE STATUS:
{change_status}

VALIDATION SUCCESS:
{validation_success}

VALIDATION RESULT:
{validation_result}

FAILURE ANALYSIS:
{failure_analysis}

Provide the final summary with these sections:

1. Task
2. Plan Approval
3. Change Approval
4. Change Status
5. Validation Status
6. Result
7. Next Step

Important:

- Do not claim that something was changed if the change status does not confirm it.
- Do not claim that validation passed if it did not.
- Do not invent test results.
- If validation was skipped or unavailable, clearly say so.
- If the user rejected the plan, say that the task stopped before code modification.
- If the user rejected the code change, say that the proposed change was not applied.
"""

    llm = get_llm()

    response = llm.invoke(prompt)

    return {
        "final_summary": response.content
    }


# ============================================================
# NODE 13
# Create task history
# ============================================================

def create_history(
    state: AgentState
):

    history = create_task_history(
        state
    )

    return {
        "task_history": history
    }


# ============================================================
# ROUTER 3
# Route after validation
# ============================================================

def route_after_validation(
    state: AgentState
):

    validation_result = state.get(
        "validation_result",
        {}
    )

    if validation_result.get(
        "success",
        False
    ):

        return "done"

    return "failure"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_agent_graph():

    graph = StateGraph(
        AgentState
    )

    # ========================================================
    # REGISTER NODES
    # ========================================================

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
        "request_approval",
        request_approval
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
        "request_change_approval",
        request_change_approval
    )

    graph.add_node(
        "apply_approved_change",
        apply_approved_change
    )

    graph.add_node(
        "validate_change",
        validate_change
    )

    graph.add_node(
        "analyze_validation_failure",
        analyze_validation_failure
    )

    graph.add_node(
        "finalize_result",
        finalize_result
    )

    graph.add_node(
        "create_history",
        create_history
    )

    # ========================================================
    # NORMAL FLOW
    # ========================================================

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
        "request_approval"
    )

    # ========================================================
    # PLAN APPROVAL ROUTING
    # ========================================================

    graph.add_conditional_edges(
        "request_approval",
        route_after_plan_approval,
        {
            "approved": "generate_proposed_changes",
            "rejected": "finalize_result"
        }
    )

    # ========================================================
    # CODE CHANGE FLOW
    # ========================================================

    graph.add_edge(
        "generate_proposed_changes",
        "create_change_diff"
    )

    graph.add_edge(
        "create_change_diff",
        "request_change_approval"
    )

    # ========================================================
    # CODE CHANGE APPROVAL ROUTING
    # ========================================================

    graph.add_conditional_edges(
        "request_change_approval",
        route_after_change_approval,
        {
            "approved": "apply_approved_change",
            "rejected": "finalize_result"
        }
    )

    # ========================================================
    # VALIDATION FLOW
    # ========================================================

    graph.add_edge(
        "apply_approved_change",
        "validate_change"
    )

    graph.add_conditional_edges(
        "validate_change",
        route_after_validation,
        {
            "done": "finalize_result",
            "failure": "analyze_validation_failure"
        }
    )

    graph.add_edge(
        "analyze_validation_failure",
        "finalize_result"
    )

    # ========================================================
    # FINAL FLOW
    # ========================================================

    graph.add_edge(
        "finalize_result",
        "create_history"
    )

    graph.add_edge(
        "create_history",
        END
    )

    return graph.compile()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("              RepoPilot - Phase 3K")
    print("       Safe Routing + Approval Handling")
    print("=" * 60)

    user_request = input(
        "\nWhat do you want RepoPilot to do?\n> "
    ).strip()

    repository_path = input(
        "\nEnter repository path:\n> "
    ).strip()

    graph = build_agent_graph()

    initial_state = {

        "user_request": user_request,

        "repository_name": "Todo-App",

        "repository_path": repository_path

    }

    try:

        result = graph.invoke(
            initial_state
        )

        # ==================================================
        # FINAL REPOPILOT RESULT
        # ==================================================

        print("\n" + "=" * 60)
        print("              FINAL REPOPILOT RESULT")
        print("=" * 60)

        print(
            result.get(
                "final_summary",
                "No final summary generated."
            )
        )

        # ==================================================
        # TASK HISTORY
        # ==================================================

        print("\n" + "=" * 60)
        print("              TASK HISTORY")
        print("=" * 60)

        history = result.get(
            "task_history",
            {}
        )

        print(
            f"Timestamp: "
            f"{history.get('timestamp', 'N/A')}"
        )

        print(
            f"Plan approved: "
            f"{history.get('plan_approved', False)}"
        )

        print(
            f"Change approved: "
            f"{history.get('change_approved', False)}"
        )

        print(
            f"Change status: "
            f"{history.get('change_result', {}).get('status', 'N/A')}"
        )

        print(
            f"Validation: "
            f"{history.get('validation_result', {}).get('success', 'N/A')}"
        )

        # ==================================================
        # FAILURE ANALYSIS
        # ==================================================

        if result.get(
            "failure_analysis"
        ):

            print("\n" + "=" * 60)
            print("             FAILURE ANALYSIS")
            print("=" * 60)

            print(
                result["failure_analysis"]
            )

    except Exception as error:

        print("\nERROR:")
        print(error)