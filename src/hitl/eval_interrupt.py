from langgraph.types import Command

def run_hitl_evaluation(main_agent, study_plan: str) -> dict:
    """
    Run the main agent with human-in-the-loop for YELLOW evaluations.
    """
    thread_id = "interrupt-123"
    result = main_agent.invoke(
    {"study_plan": study_plan},
    config={"configurable": {"thread_id": thread_id}}
)
    if '__interrupt__' in result:
        # Present review information to human, collect decision:
        action = result['__interrupt__']
        print(action[0].value['action_requests'][0]['description'])  # Display the interrupt message
        # Simulate getting human review:
        decision = input("Enter decision (approve/edit/reject): ")
        context = ""
        if decision == "edit":
            context = input("Provide additional context: ")

        # Resume agent using actual human input
        resume_payload = {"decision": decision, "context": context}
        review_result = main_agent.invoke(
            Command(resume={"decisions": [resume_payload]}),
            config={"configurable": {"thread_id": thread_id}}
        )
        try:
            return review_result['structured_response'].model_dump()
        except KeyError as e:
            print(f"Error retrieving final output: {e}")
            return review_result
    else:
        print(result)