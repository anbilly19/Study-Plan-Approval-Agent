# src/main.py
"""Main entry point for running the study plan evaluation with optional HITL."""

import os
import warnings
from typing import Optional

from dotenv import load_dotenv
from langgraph.graph import StateGraph
from pydantic.json_schema import PydanticJsonSchemaWarning

from .graph import build_study_plan_graph
from .tools import ToolRegistry

# Suppress noisy schema warnings from Pydantic when generating JSON Schema.
warnings.filterwarnings("ignore", category=PydanticJsonSchemaWarning)

# Load environment variables from .env (API keys, LangSmith, etc.).
load_dotenv()

# Default model names (can be overridden when calling evaluate_study_plan).
LLAMA_70B = "llama-3.3-70b-versatile"
LLAMA_8B = "llama-3.1-8b-instant"

# Base path where CSV context tables live (used by DatabaseTool).
CONTEXT_PARENT = f"{os.getcwd()}/src/context_tables"


def _context_paths(base: Optional[str] = None) -> dict:
    """Return a mapping from logical context names to CSV file paths.

    Args:
        base: Optional base directory; if not provided, uses CONTEXT_PARENT.

    Returns:
        Dict mapping names like "exams" to their corresponding CSV file paths.
    """
    base = base or CONTEXT_PARENT
    return {
        "exams": f"{base}/exams.csv",
        "lectures": f"{base}/lectures.csv",
        "course_description": f"{base}/course_description.csv",
        "course_masterlist": f"{base}/course_masterlist.csv",
    }


def init_graph(
    model_name: str = LLAMA_70B,
    context_parent: Optional[str] = None,
    enable_hitl: bool = True,
    scheduling_prompt=None,
    alignment_prompt=None,
) -> StateGraph:
    """Build and cache StateGraph once (reusable by FastAPI or other callers).

    This function:
    - Resolves CSV paths for context tables.
    - Wraps them in a ToolRegistry.
    - Instantiates StateGraph with prompts and model name.
    - Caches the result in a module-level variable.

    Args:
        model_name: LLM to use for the evaluation agents.
        context_parent: Optional override for the context tables directory.
        enable_hitl: Whether to enable HITL paths in the graph.
        scheduling_prompt: Prompt template for scheduling evaluation.
        alignment_prompt: Prompt template for alignment evaluation.

    Returns:
        A shared StateGraph instance.
    """
    # Build DatabaseTool over CSV-backed context tables.
    df_paths = _context_paths(context_parent)
    tool_registry = ToolRegistry(df_paths)

    # Build graph
    graph = build_study_plan_graph(
        tool_registry=tool_registry,
        model_name=model_name,
        scheduling_prompt=scheduling_prompt,
        alignment_prompt=alignment_prompt,
        enable_hitl=enable_hitl,
    )
    return graph
