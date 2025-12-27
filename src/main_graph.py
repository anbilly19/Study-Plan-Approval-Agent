"""Main entry point for study plan evaluation system."""
import warnings
import os
import uuid
from typing import Optional
from dotenv import load_dotenv

from langgraph.types import Command

from pydantic.json_schema import PydanticJsonSchemaWarning
from graph import build_study_plan_graph
from tools import ToolRegistry
from state import StudyPlanState, StudyPlanEvaluation
from prompts.prompt import (
    green_case,
    red_case,
    yellow_case,
    _scheduling_prompt,
    _alignment_prompt,
)

load_dotenv()
# Suppress noisy schema warnings from Pydantic when generating JSON Schema.
warnings.filterwarnings("ignore", category=PydanticJsonSchemaWarning)
LLAMA_70B = "llama-3.3-70b-versatile"
CONTEXT_PARENT = f"{os.getcwd()}/src/context_tables"


def evaluate_study_plan(
    study_plan: str,
    enable_hitl: bool = False,
    model_name: str = LLAMA_70B,
    scheduling_prompt = None,
    alignment_prompt = None,
    context_parent: Optional[str] = None,
) -> dict:
    """Evaluate a study plan using the LangGraph workflow.
    
    Args:
        study_plan: Raw study plan text
        enable_hitl: Enable Human-In-The-Loop for yellow cases
        model_name: LLM model name
        scheduling_prompt: Prompt template for scheduling evaluation
        alignment_prompt: Prompt template for alignment evaluation
        context_parent: Optional override for context tables directory
    
    Returns:
        Final state dict with evaluation results
    """
    
    # Initialize tool registry with database paths
    df_paths = {
        "exams": f"{context_parent or CONTEXT_PARENT}/exams.csv",
        "lectures": f"{context_parent or CONTEXT_PARENT}/lectures.csv",
        "course_description": f"{context_parent or CONTEXT_PARENT}/course_description.csv",
        "course_masterlist": f"{context_parent or CONTEXT_PARENT}/course_masterlist.csv",
    }
    tool_registry = ToolRegistry(df_paths)
    
    # Build graph
    app = build_study_plan_graph(
        tool_registry=tool_registry,
        model_name=model_name,
        scheduling_prompt=scheduling_prompt, 
        alignment_prompt=alignment_prompt,
        enable_hitl=enable_hitl,
    )
    # Initial state
    initial_state: StudyPlanState = {"study_plan": study_plan}
    
    if enable_hitl:
        return _run_with_hitl(app, initial_state)
    else:
        # Run without HITL
        result = app.invoke(initial_state)
        return result



def _run_with_hitl(app, initial_state: StudyPlanState) -> dict:
    """Execute graph with Human-In-The-Loop support."""
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initial invoke - will run until interrupt() is called
    result = app.invoke(initial_state, config)
    
    # Check if there's an interrupt
    if "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0]
        payload = interrupt_data.value
        
        # Display evaluation summary from interrupt payload
        eval_summary = payload.get("evaluation_summary", {})
        print(f"\n📊 Evaluation Summary:")
        print(f"  Weighted Average: {eval_summary.get('weighted_avg')}")
        print(f"  Color: {eval_summary.get('color', '').upper()}")
        print(f"\n  Scheduling Score: {eval_summary.get('scheduling_score')}/100")
        print(f"    Reasoning: {eval_summary.get('scheduling_reasoning')}")
        print(f"\n  Alignment Score: {eval_summary.get('alignment_score')}/100")
        print(f"    Reasoning: {eval_summary.get('alignment_reasoning')}")
        print(f"\n  Workload Score: {eval_summary.get('workload_score')}/100")
        
        
        # Collect human decision
        decision = input("\nYour decision: ").strip().lower()
        
        # Build human response based on decision
        if decision == "edit":
            override_scores = {
                "scheduling_score": int(input("  Scheduling score (0-100): ")),
                "alignment_score": int(input("  Alignment score (0-100): ")),
                "workload_score": int(input("  Workload score (0-100): ")),
            }
            human_response = {
                "action": "edit",
                "data": override_scores
            }
         
        elif decision == "reject":
            human_response = {
                "action": "reject"
            }
           
        
        else:  # approve or default
            human_response = {
                "action": "approve"
            }
            
        
        # Resume by passing Command(resume=human_response)
        # This becomes the return value of interrupt() inside the node
        final_result = app.invoke(Command(resume=human_response), config)
        
        return final_result
    
    # No interrupt - return result directly (red or green case)
    return result


def _print_evaluation_summary(result: dict) -> None:
    """Print a summary of the final evaluation."""
    
    if result.get("final_evaluation"):
        eval_obj = result["final_evaluation"] if isinstance(result["final_evaluation"],StudyPlanEvaluation) else result["final_evaluation"]["structured_response"]
        print(f"\n📊 Weighted Average: {eval_obj.weighted_avg:.2f}/100")
        print(f"🚦 Status: {eval_obj.color.upper()}")
        print(f"\n💡 Recommendation:\n   {eval_obj.overall_recommendation}")
        print(f"\n📝 Reasoning:\n   {eval_obj.reasoning}")
    else:
        print("\n⚠️  Evaluation incomplete")


if __name__ == "__main__":
    
    # Toggle between test cases
    use_hitl = True
    
    
    result = evaluate_study_plan(
        study_plan=yellow_case,
        enable_hitl=use_hitl,
        scheduling_prompt=_scheduling_prompt,
        alignment_prompt=_alignment_prompt
    )
    
    for msg in result["final_evaluation"].get("messages", []):
        msg.pretty_print()
    
    # Print evaluation summary
    _print_evaluation_summary(result)
