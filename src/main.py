# src/main.py
"""Main entry point for running the study plan evaluation with optional HITL."""
import os
import warnings
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic.json_schema import PydanticJsonSchemaWarning
from pprint import pprint

from agents.main_agent import create_interrupt_main_agent, create_main_agent
from agents.study_eval_agent import EvalAgents
from hitl.eval_interrupt import run_hitl_evaluation
from prompts.prompt import (
    alignment_prompt,
    green_case,
    interrupt_agent_prompt,
    main_agent_prompt,
    scheduling_prompt,
    yellow_case,
)
from tools import DatabaseTool

# --- constants (shared) ---
warnings.filterwarnings("ignore", category=PydanticJsonSchemaWarning)
load_dotenv()

LLAMA_70B = "llama-3.3-70b-versatile"
LLAMA_8B = "llama-3.1-8b-instant"
CONTEXT_PARENT = f"{os.getcwd()}/context_tables"

# global cache so API can reuse without rebuilding
_eval_agents: Optional[EvalAgents] = None


def _context_paths(base: Optional[str] = None) -> dict:
    base = base or CONTEXT_PARENT
    return {
        "exams": f"{base}/exams.csv",
        "lectures": f"{base}/lectures.csv",
        "course_description": f"{base}/course_description.csv",
        "course_masterlist": f"{base}/course_masterlist.csv",
    }


def init_eval_agents(model_name: str = LLAMA_70B, context_parent: Optional[str] = None) -> EvalAgents:
    """Build and cache EvalAgents once (reusable by FastAPI)."""
    global _eval_agents
    if _eval_agents is not None:
        return _eval_agents

    df_paths = _context_paths(context_parent)
    db_tools = DatabaseTool(df_paths)
    _eval_agents = EvalAgents(
        db_tools,
        scheduling_prompt=scheduling_prompt,
        alignment_prompt=alignment_prompt,
        model_name=model_name,
    )
    return _eval_agents


def run_evaluation(chain, study_plan: str) -> Any:
    """Thin wrapper kept for parity with your original code."""
    return chain.invoke({"study_plan": study_plan})


def evaluate_study_plan(
    study_plan: str,
    hitl: bool = False,
    model_name: str = LLAMA_70B,
    use_examples: bool = False,
) -> Any:
    """
    Unified entry the API can call.
    - If hitl=False: create_main_agent -> invoke(study_plan)
    - If hitl=True:  create_interrupt_main_agent -> run_hitl_evaluation(...)
      NOTE: HITL path is interactive; API should not call this directly unless you
      route human decisions separately (e.g., via tools.weighted_score_tool_with_interrupt).
    - If use_examples=True, uses your green/yellow example texts instead of provided study_plan.
    """
    eval_agents = init_eval_agents(model_name=model_name)

    if hitl:
        chain = create_interrupt_main_agent(
            eval_agents,
            model_name=model_name,
            interrupt_agent_prompt=interrupt_agent_prompt,
        )
        plan_text = yellow_case if use_examples else study_plan
        return run_hitl_evaluation(chain, plan_text)

    # non-HITL
    chain = create_main_agent(
        eval_agents,
        model_name=model_name,
        main_agent_prompt=main_agent_prompt,
    )
    plan_text = green_case if use_examples else study_plan
    return run_evaluation(chain, plan_text)


# ------------- CLI behavior preserved -------------
if __name__ == "__main__":
    # CLI-only: allow entering key interactively (avoid this during imports)
    import getpass

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        api_key = getpass.getpass("Enter your Groq API key: ")
        with open(".env", "a") as f:
            f.write(f"\nGROQ_API_KEY={api_key}")
        os.environ["GROQ_API_KEY"] = api_key

    hitl = True  # keep your original toggle

    if hitl:
        out = evaluate_study_plan(study_plan=yellow_case, hitl=True, use_examples=True)
        pprint(out)
    else:
        out = evaluate_study_plan(study_plan=green_case, hitl=False, use_examples=True)
        # if it's a pydantic model with structured_response, you can still dump it:
        try:
            pprint(out["structured_response"].model_dump())
        except Exception:
            pprint(out)
