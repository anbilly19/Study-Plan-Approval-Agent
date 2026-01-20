"""LangGraph workflow for study plan evaluation."""

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes import EvaluationNodes
from .state import StudyPlanState
from .tools import ToolRegistry


def should_request_human_review(state: StudyPlanState) -> Literal["human_review", "end"]:
    color = state.get("color")
    if color == "yellow" and not state.get("human_decision"):
        return "human_review"
    return "end"


def build_study_plan_graph(
    tool_registry: ToolRegistry,
    model_name: str,
    scheduling_prompt,
    alignment_prompt,
    enable_hitl: bool = False,
) -> StateGraph:
    nodes = EvaluationNodes(
        tool_registry=tool_registry,
        model_name=model_name,
        scheduling_prompt=scheduling_prompt,
        alignment_prompt=alignment_prompt,
    )
    graph = StateGraph(StudyPlanState)
    graph.add_node("memory", nodes.memory_node)
    graph.add_node("scheduling", nodes.scheduling_node)
    graph.add_node("alignment", nodes.alignment_node)
    graph.add_node("workload", nodes.workload_node)
    graph.add_node("synthesis", nodes.synthesis_node)
    if enable_hitl:
        graph.add_node("human_review", nodes.human_review_node)
    graph.set_entry_point("memory")
    graph.add_edge("memory", "scheduling")
    graph.add_edge("scheduling", "alignment")
    graph.add_edge("alignment", "workload")
    graph.add_edge("workload", "synthesis")
    if enable_hitl:
        graph.add_conditional_edges(
            "synthesis",
            should_request_human_review,
            {
                "human_review": "human_review",
                "end": END,
            },
        )
    else:
        graph.add_edge("synthesis", END)
    checkpointer = MemorySaver() if enable_hitl else None
    return graph.compile(checkpointer=checkpointer)
