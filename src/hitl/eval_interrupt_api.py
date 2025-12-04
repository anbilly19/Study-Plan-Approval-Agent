# src/hitl/eval_interrupt_api.py

import uuid
from typing import Any, Dict, Optional

from langgraph.types import Command


def _format_interrupt_result(result: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
    """
    Extract and normalize interrupt information from LangGraph's HumanInTheLoopMiddleware.

    When the model triggers an interrupt (usually by calling ask_human_tool), the
    result contains a `__interrupt__` structure. This function converts that raw
    payload into a clean JSON shape that the API can return.

    Args:
        result: Full result returned by the agent invocation.
        thread_id: The active thread ID assigned for this HITL session.

    Returns:
        Dict containing:
            - status="interrupt"
            - thread_id
            - action: human-facing description of what is being requested
            - result: raw agent output (messages, tool calls, etc.) for debugging/UI
    """
    interrupt_list = result["__interrupt__"]

    # LangGraph gives a list of NodeInterrupt objects; we typically only need the first one.
    first_interrupt_obj = interrupt_list[0]

    # The `.value` field holds a dictionary of:
    #   { "action_requests": [...], "review_configs": [...] }
    first_interrupt = first_interrupt_obj.value

    # Extract human-facing description if available.
    action_requests = first_interrupt.get("action_requests", [])
    description = "Human review required."
    action_name = None

    if action_requests:
        first_action_request = action_requests[0]
        description = first_action_request.get("description", description)
        action_name = first_action_request.get("name")

    # Standardized interrupt response for the API.
    return {
        "status": "interrupt",
        "thread_id": thread_id,
        "action": {
            "name": action_name,
            "description": description,
            "details": first_interrupt,  # raw data for debugging/frontend logic
        },
        "result": result,  # the full agent output so far
    }


def hitl_start(
    main_agent,
    study_plan: str,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Start a HITL (Human-in-the-Loop) evaluation run.

    This invokes the interrupt-capable agent pipeline with a study plan.
    Based on the agent's behavior, this function returns either:

    A) A completed evaluation
        {
          "status": "complete",
          "thread_id": "...",
          "result": {...}
        }

    B) A request for human input (interrupt)
        {
          "status": "interrupt",
          "thread_id": "...",
          "action": {...},
          "result": {...}
        }

    Args:
        main_agent: The interrupt-ready LangGraph chain created in create_interrupt_main_agent().
        study_plan: User-provided study plan text.
        thread_id: Optional — useful for continuing an already-started thread. If not provided,
                   a new UUID is generated to isolate this HITL session.

    Returns:
        A dictionary with status + thread_id + result (or interrupt info).
    """
    # Generate a fresh thread ID if none is provided.
    thread_id = thread_id or str(uuid.uuid4())

    # Invoke the main agent; LangGraph handles the tool calls and interruptions.
    result = main_agent.invoke(
        {"study_plan": study_plan},
        config={"configurable": {"thread_id": thread_id}},
    )

    # No interrupt → final evaluation complete.
    if "__interrupt__" not in result:
        return {
            "status": "complete",
            "thread_id": thread_id,
            "result": result,
        }

    # Interrupt occurred → return detailed interrupt instructions.
    return _format_interrupt_result(result, thread_id)


def hitl_resume(
    synth_agent,
    thread_id: str,
    decision_type: str,
    edited_scores: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resume a HITL evaluation run using the human's decision.

    This function takes the human feedback ("approve", "reject", or "edit") and
    resumes execution of the synthesis agent using a LangGraph Command, which
    instructs the graph HOW to apply that decision.

    Supported decisions:

    - "approve": Continue as-is.
    - "reject": Stop and mark the evaluation as rejected (with optional message).
    - "edit": Modify the scoring tool's arguments and re-run evaluation.

    Args:
        synth_agent: The synthesis agent returned by create_interrupt_main_agent().
        thread_id: The HITL session identifier — ensures we resume the correct graph state.
        decision_type: One of {"approve", "reject", "edit"}.
        edited_scores: Required when decision_type="edit".
                       Example: {"scheduling_score": 80, "alignment_score": 75, "workload_score": 60}
        message: Optional rejection explanation.

    Returns:
        A dict with:
            - status="complete" and final result
        OR
            - status="interrupt" if another human review is still required
    """
    decision_type = decision_type.lower()

    # Build the proper LangGraph Command() depending on human decision.
    if decision_type == "approve":
        resume_cmd = Command(resume={"decisions": [{"type": "approve"}]})

    elif decision_type == "reject":
        resume_cmd = Command(
            resume={
                "decisions": [
                    {
                        "type": "reject",
                        "message": message or "Study plan requires major revisions.",
                    }
                ]
            }
        )

    elif decision_type == "edit":
        if not edited_scores:
            raise ValueError("edited_scores must be provided when decision_type='edit'.")

        resume_cmd = Command(
            resume={
                "decisions": [
                    {
                        "type": "edit",
                        "edited_action": {
                            "name": "weighted_score_tool",
                            "args": edited_scores,
                        },
                    }
                ]
            }
        )

    else:
        raise ValueError("decision_type must be one of: approve, reject, edit")

    # Resume the LangGraph execution from its previous stopping point.
    result = synth_agent.invoke(
        resume_cmd,
        config={"configurable": {"thread_id": thread_id}},
    )

    # If the resumed computation triggers another human review,
    # return another structured interrupt state.
    if "__interrupt__" in result:
        return _format_interrupt_result(result, thread_id)

    # Otherwise, we finally have a complete result.
    return {
        "status": "complete",
        "thread_id": thread_id,
        "result": result,
    }
