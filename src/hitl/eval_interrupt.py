import uuid

from langgraph.types import Command


def run_hitl_evaluation(main_agent, study_plan: str, synth) -> dict:
    """Run the main agent with human-in-the-loop for YELLOW evaluations.

    This function:
    - Executes the interrupt-capable main agent.
    - Detects whether the agent requests human intervention (via __interrupt__).
    - Displays the interrupt message to the user.
    - Collects human decisions (approve / reject / edit).
    - Builds an appropriate Command object to resume the graph.
    - Invokes the synthesis step with the human-adjusted decision.
    """
    # Each HITL interaction uses a unique thread identifier (required by LangGraph for session state).
    thread_id = str(uuid.uuid4())

    # Run the initial agent evaluation.
    # If the agent detects a "YELLOW" case, it will return a __interrupt__ key.
    result = main_agent.invoke(
        {"study_plan": study_plan},
        config={"configurable": {"thread_id": thread_id}},
    )

    messages = result.get("messages", [])
    for msg in messages:
        msg.pretty_print()
    # Check for interrupt request (this field exists when the agent wants human help).
    if "__interrupt__" in result:
        action = result["__interrupt__"]
        print("action", action)

        print("Human review required:")
        # Usually the interrupt contains a tool call request or explanatory description.
        print(action[0].value["action_requests"][0]["description"])

        # In a real application, this would come from UI input rather than the terminal.
        decision = input("Enter your decision (approve/edit/reject): ").strip().lower()

        # Build the appropriate resume Command object based on human decision.
        if decision == "approve":
            # Human approves the agent’s suggested action or scores.
            resume = Command(resume={"decisions": [{"type": "approve"}]})

        elif decision == "reject":
            # Human fully rejects the evaluation; informative message can be provided.
            resume = Command(
                resume={"decisions": [{"type": "reject", "message": "Study plan requires major revisions."}]}
            )

        elif decision == "edit":
            # Human modifies the tool call arguments manually (new scores).
            resume = Command(
                resume={
                    "decisions": [
                        {
                            "type": "edit",
                            "edited_action": {
                                "name": "weighted_score_tool",
                                "args": {
                                    "scheduling_score": input("Enter new scheduling score (0-100): "),
                                    "alignment_score": input("Enter new alignment score (0-100): "),
                                    "workload_score": input("Enter new workload score (0-100): "),
                                },
                            },
                        }
                    ]
                }
            )

        else:
            # Default fallback when user types something unexpected.
            print("Invalid decision. Defaulting to 'approve'.")
            resume = Command(resume={"decisions": [{"type": "approve"}]})

        # Resume the synthesis process with the human decision attached.
        result = synth.invoke(resume, config={"configurable": {"thread_id": thread_id}})

    return result
