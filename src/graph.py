"""LangGraph workflow for study plan evaluation."""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import StudyPlanState
from .nodes import EvaluationNodes
from .tools import ToolRegistry


def should_request_human_review(state: StudyPlanState) -> Literal["human_review", "end"]:
    """Router: yellow → human review, red/green → end."""
    color = state.get("color")
    
    if color == "yellow":
        return "human_review"
    else:
        return "end"  # Return string "end" that maps to END in conditional_edges


def build_study_plan_graph(
    tool_registry: ToolRegistry,
    model_name: str,
    scheduling_prompt,
    alignment_prompt,
    enable_hitl: bool = False,
) -> StateGraph:
    """Build the complete LangGraph workflow.
    
    Graph structure (HITL enabled):
    
    START → scheduling → alignment → workload → synthesis → [router]
                                                               ↓
                                           yellow → human_review (interrupt() inside)
                                                       ↓ (Command routing)
                                              edit → synthesis (recalc)
                                              approve/reject → END
                                           
                                           red/green → END
    """
    
    # Initialize node functions with tool registry
    nodes = EvaluationNodes(
        tool_registry=tool_registry,
        model_name=model_name,
        scheduling_prompt=scheduling_prompt,
        alignment_prompt=alignment_prompt,
    )
    
    # Create the graph
    graph = StateGraph(StudyPlanState)
    
    # Add all nodes
    graph.add_node("scheduling", nodes.scheduling_node)
    graph.add_node("alignment", nodes.alignment_node)
    graph.add_node("workload", nodes.workload_node)
    graph.add_node("synthesis", nodes.synthesis_node)
    
    if enable_hitl:
        graph.add_node("human_review", nodes.human_review_node)
    
    # Define edges: linear evaluation pipeline
    graph.set_entry_point("scheduling")
    graph.add_edge("scheduling", "alignment")
    graph.add_edge("alignment", "workload")
    graph.add_edge("workload", "synthesis")
    
    # Conditional routing after synthesis
    if enable_hitl:
        graph.add_conditional_edges(
            "synthesis",
            should_request_human_review,
            {
                "human_review": "human_review",
                "end": END,  # Map string "end" to END constant
            }
        )
        # human_review_node returns Command with goto
        # Command can goto "synthesis" (edit) or END (approve/reject)
    else:
        graph.add_edge("synthesis", END)
    
    # Compile with checkpointer (required for interrupt())
    checkpointer = MemorySaver() if enable_hitl else None
    
    return graph.compile(checkpointer=checkpointer)
