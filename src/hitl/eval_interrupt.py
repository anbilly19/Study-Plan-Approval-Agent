from langgraph.types import Command
import uuid

def run_hitl_evaluation(main_agent, study_plan: str, synth) -> dict:
    """Run the main agent with human-in-the-loop for YELLOW evaluations."""
    thread_id = str(uuid.uuid4())
    result = main_agent.invoke({"study_plan": study_plan}, config={"configurable": {"thread_id": thread_id}})
    if "__interrupt__" in result:
        # Present review information to human, collect decision:
        action = result["__interrupt__"]
        print(action[0].value["action_requests"][0]["description"])  # Display the interrupt message
        # Simulate human decision (in real scenario, collect input from user)
        decision = input("Enter your decision (approve/edit/reject): ").strip().lower()
        if (decision == "approve"):
            resume = Command(resume={"decisions": [{"type": "approve"}]})
        elif decision == "reject":
            resume = Command(resume={"decisions": [{"type": "reject", "message": "Study plan requires major revisions."}]})
        elif decision == "edit":
            resume=Command(resume= { "decisions": [
                {
                    "type": "edit",
                    "edited_action": {
                        "name": "weighted_score_tool",
                        "args": {
                            "scheduling_score": input(
                                "Enter new scheduling score (0-100): "
                            ),
                            "alignment_score": input(
                                "Enter new alignment score (0-100): "
                            ),
                            "workload_score": input(
                                "Enter new workload score (0-100): "
                            ),
                        },
                    },
                }
            ]
        })
        else:
            print("Invalid decision. Defaulting to 'approve'.")
            resume = Command(resume={"decisions": [{"type": "approve"}]})
        # Resume the agent with human decision
        result = synth.invoke(resume, config={"configurable": {"thread_id": thread_id}})
    return result
