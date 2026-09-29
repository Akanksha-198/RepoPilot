#task_history.py



from datetime import datetime


def create_task_history(state: dict) -> dict:

    return {

        "timestamp": datetime.now().isoformat(),

        "user_request": state.get(
            "user_request",
            ""
        ),

        "task_understanding": state.get(
            "task_understanding",
            ""
        ),

        "plan": state.get(
            "plan",
            []
        ),

        "plan_approved": state.get(
            "approved",
            False
        ),

        "proposed_changes": state.get(
            "proposed_changes",
            []
        ),

        "change_approved": state.get(
            "change_approved",
            False
        ),

        "change_result": state.get(
            "change_result",
            {}
        ),

        "validation_result": state.get(
            "validation_result",
            {}
        ),

        "failure_analysis": state.get(
            "failure_analysis",
            ""
        ),

        "final_summary": state.get(
            "final_summary",
            ""
        )

    }