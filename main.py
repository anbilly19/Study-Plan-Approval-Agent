# src/main.py
"""Main entry point for running the study plan evaluation with optional HITL."""

import os
import warnings
from pprint import pprint
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic.json_schema import PydanticJsonSchemaWarning

from .agents.main_agent import create_interrupt_main_agent, create_main_agent
from .agents.study_eval_agent import EvalAgents
from .env_setup import setup_langsmith_env
from .hitl.eval_interrupt import run_hitl_evaluation
from .prompts.prompt import (
    alignment_prompt,
    green_case,
    interrupt_agent_prompt,
    main_agent_prompt,
    scheduling_prompt,
    synth_prompt,
    synth_prompt_interrupt,
    yellow_case,
)
from .tools import DatabaseTool

# Suppress noisy schema warnings from Pydantic when generating JSON Schema.
warnings.filterwarnings("ignore", category=PydanticJsonSchemaWarning)

# Load environment variables from .env (API keys, LangSmith, etc.).
load_dotenv()

# Default model names (can be overridden when calling evaluate_study_plan).
GPT_4O = "gpt-4o"
LLAMA_8B = "llama-3.1-8b-instant"

# Base path where CSV context tables live (used by DatabaseTool).
CONTEXT_PARENT = f"{os.getcwd()}/src/context_tables"

# Global cache so EvalAgents are built only once and reused.
_eval_agents: Optional[EvalAgents] = None


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


def init_eval_agents(model_name: str = GPT_4O, context_parent: Optional[str] = None) -> EvalAgents:
    """Build and cache EvalAgents once (reusable by FastAPI or other callers).

    This function:
    - Resolves CSV paths for context tables.
    - Wraps them in a DatabaseTool.
    - Instantiates EvalAgents with prompts and model name.
    - Caches the result in a module-level variable.

    Args:
        model_name: LLM to use for the evaluation agents.
        context_parent: Optional override for the context tables directory.

    Returns:
        A shared EvalAgents instance.
    """
    global _eval_agents
    # If already initialized, return the cached instance.
    if _eval_agents is not None:
        return _eval_agents

    # Build DatabaseTool over CSV-backed context tables.
    df_paths = _context_paths(context_parent)
    db_tools = DatabaseTool(df_paths)

    # Create EvalAgents with the relevant prompts and model.
    _eval_agents = EvalAgents(
        db_tools,
        scheduling_prompt=scheduling_prompt,
        alignment_prompt=alignment_prompt,
        model_name=model_name,
    )
    return _eval_agents


def run_evaluation(chain, study_plan: str) -> Any:
    """Thin wrapper around chain.invoke kept for parity with original code.

    Args:
        chain: LangChain Runnable / agent chain.
        study_plan: The raw study plan text to evaluate.

    Returns:
        The chain's output (may be a dict, pydantic model, etc.).
    """
    return chain.invoke({"study_plan": study_plan})


def evaluate_study_plan(
    study_plan: str,
    hitl: bool = False,
    model_name: str = GPT_4O,
    use_examples: bool = False,
) -> Any:
    """Unified entrypoint that external callers (e.g., API) can use.

    Behavior:
        - If hitl=False:
            * Build main agent with create_main_agent.
            * Invoke it on the given study plan (or example text if use_examples=True).

        - If hitl=True:
            * Build interrupt-capable agent with create_interrupt_main_agent.
            * Run run_hitl_evaluation, which coordinates the HITL cycle.

    Notes:
        - HITL path is interactive; the API should only call it if there is some
          mechanism to route human decisions (e.g., UI or dedicated tools).

    Args:
        study_plan: Raw study plan text from the user.
        hitl: Whether to enable Human-In-The-Loop evaluation path.
        model_name: LLM name to use for all agents.
        use_examples: If True, ignore the provided study_plan and instead:
            * HITL=True -> use yellow_case example
            * HITL=False -> use green_case example

    Returns:
        The evaluation result structure returned by the chain/HITL runner.
    """
    # Ensure we have a shared EvalAgents instance.
    eval_agents = init_eval_agents(model_name=model_name)

    # HITL (interactive) path:
    if hitl:
        # Build an interruptable chain plus a synthesis step.
        chain, synth = create_interrupt_main_agent(
            eval_agents,
            model_name=model_name,
            interrupt_agent_prompt=interrupt_agent_prompt,
            synth_prompt=synth_prompt_interrupt,
        )
        # Use example case if requested; otherwise use user-provided plan.
        plan_text = yellow_case if use_examples else study_plan
        return run_hitl_evaluation(chain, plan_text, synth)

    # Non-HITL (fully automated) path:
    chain = create_main_agent(
        eval_agents,
        model_name=model_name,
        main_agent_prompt=main_agent_prompt,
        synth_prompt=synth_prompt,
    )
    # Use example or real study plan for evaluation.
    plan_text = green_case if use_examples else study_plan
    return run_evaluation(chain, plan_text)


# ------------- CLI behavior preserved -------------
if __name__ == "__main__":
    # CLI-only: configure LangSmith/environment. Avoid calling this on import.
    setup_langsmith_env()

    # Toggle to run HITL or non-HITL when executing this file directly.
    hitl = True  # keep your original toggle

    if hitl:
        # Run HITL evaluation on the green example case.
        out = evaluate_study_plan(study_plan=green_case, hitl=True)
    else:
        # Run automated evaluation on the green example case.
        out = evaluate_study_plan(study_plan=green_case, hitl=False)
        # If the chain returns a structured_response Pydantic model, pretty-print it.
    try:
        pprint(out["structured_response"].model_dump())
    except Exception:
        # Fallback: just pretty-print the raw output.
        pprint(out)
