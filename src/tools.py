# """Module defining various tools for evaluation and database querying."""

# from functools import partial

# import pandas as pd
# from langchain_core.tools import StructuredTool, tool
# from langgraph.types import interrupt


# @tool
# def weighted_score_tool(scheduling_score: int, alignment_score: int, workload_score: int) -> str:
#     """Calculate the weighted average score and return a color code based on the score."""
#     w_avg = 0.4 * scheduling_score + 0.4 * alignment_score + 0.2 * workload_score
#     if 0 <= w_avg <= 45:
#         return "red"
#     elif 46 <= w_avg <= 75:
#         return "yellow"
#     else:
#         return "green"


# @tool
# def weighted_score_tool_with_interrupt(scheduling_score: int, alignment_score: int, workload_score: int) -> str:
#     """Calculate the weighted average score."""
#     w_avg = 0.4 * scheduling_score + 0.5 * alignment_score + 0.1 * workload_score

#     if 0 <= w_avg <= 45:
#         return "red"
#     elif 45 < w_avg <= 75:
#         # Pause and request human review
#         human_input = interrupt(
#             "Review required: The evaluation outcome is YELLOW.\n"
#             "Please review reasoning, scores, and add additional context if needed. Decisions: [approve, edit, reject]."
#         )
#         # Incorporate human input for final output (assume human_input is a dict with 'decision' and optional 'context')
#         if human_input["decision"] == "approve":
#             return "green"
#         elif human_input["decision"] == "edit":
#             # Recalculate based on human context (for simplicity, assume human provides new scores)
#             new_scheduling_score = human_input.get("scheduling_score", scheduling_score)
#             new_alignment_score = human_input.get("alignment_score", alignment_score)
#             new_workload_score = human_input.get("workload_score", workload_score)
#             return (
#                 f"Re-evaluate based on new scores: {new_scheduling_score}, {new_alignment_score}, {new_workload_score}"
#             )
#         elif human_input["decision"] == "reject":
#             return "red"
#         else:
#             return "Invalid Choice"
#     else:
#         return "green"


# class DatabaseTool:
#     """Base class for database tools."""

#     def __init__(self, dataframe_path_dict):

#         self.df_funcs = {}
#         for name, df_path in dataframe_path_dict.items():
#             df = pd.read_csv(df_path)
#             df_func = partial(self._query_dataframe, df)
#             self.df_funcs[name] = df_func

#     def _query_dataframe(self, df: pd.DataFrame, query: str) -> str:
#         try:
#             result = df.query(query).to_string()
#             return result
#         except Exception as e:
#             return f"Error executing query: {e}"

#     def course_description_tool(self, query: str) -> str:

#         return self._query_dataframe(df=self.df_funcs["course_description"], query=query)

#     def course_masterlist_tool(self, query: str) -> str:

#         return self._query_dataframe(df=self.df_funcs["course_masterlist"], query=query)

#     def exams_tool(self, query: str) -> str:

#         return self._query_dataframe(df=self.df_funcs["exams"], query=query)

#     def lectures_tool(self, query: str) -> str:

#         return self._query_dataframe(df=self.df_funcs["lectures"], query=query)

#     def tool_factory(self) -> dict[str, StructuredTool]:
#         tool_dict: dict[str, StructuredTool] = {}
#         for name, func in self.df_funcs.items():
#             desc = f"Query the {name} dataframe. Accepts a pandas query string."
#             tool_dict[f"{name}_tool"] = StructuredTool.from_function(
#                 name=f"{name}_tool",
#                 func=lambda query, f=func: f(query),
#                 description=desc,
#             )
#         return tool_dict


# tools.py
"""Module defining various tools for evaluation and database querying."""
from functools import partial
from typing import Optional, Dict, Any

import pandas as pd
from langchain_core.tools import StructuredTool, tool
from langgraph.types import interrupt


# -----------------------------
# Pure scorer (no HITL)
# -----------------------------
@tool
def weighted_score_tool(
    scheduling_score: int,
    alignment_score: int,
    workload_score: int,
) -> Dict[str, Any]:
    """
    Calculate weighted average and return structured result.
    Weights: 0.4 sched, 0.4 align, 0.2 workload (pure, no HITL).
    """
    w_avg = 0.4 * scheduling_score + 0.4 * alignment_score + 0.2 * workload_score
    if 0 <= w_avg <= 45:
        color = "red"
    elif 46 <= w_avg <= 75:
        color = "yellow"
    else:
        color = "green"
    return {
        "weighted_avg": round(float(w_avg), 2),
        "color": color,
        "scores": {
            "scheduling_score": scheduling_score,
            "alignment_score": alignment_score,
            "workload_score": workload_score,
        },
        "notes": "auto-decision (no HITL)",
    }


# -----------------------------
# Scorer with optional HITL
# -----------------------------
@tool
def weighted_score_tool_with_interrupt(
    scheduling_score: int,
    alignment_score: int,
    workload_score: int,
    # --- NEW: non-interactive controls for API calls ---
    decision: Optional[str] = None,              # "auto" | "approve" | "edit" | "reject" | None
    new_scheduling_score: Optional[int] = None,  # only used when decision == "edit"
    new_alignment_score: Optional[int] = None,
    new_workload_score: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Weighted average with 'yellow' pause for HITL by default.
    If 'decision' is provided, runs fully NON-INTERACTIVE (no interrupt()) — safe for FastAPI.
    Weights: 0.4 sched, 0.5 align, 0.1 workload (your original design).
    """
    def compute(scheduling_score: int, alignment_score: int, workload_score: int) -> Dict[str, Any]:
        w = 0.4 * scheduling_score + 0.5 * alignment_score + 0.1 * workload_score
        if 0 <= w <= 45:
            c = "red"
        elif 45 < w <= 75:
            c = "yellow"
        else:
            c = "green"
        return {"weighted_avg": round(float(w), 2), "color": c}

    base = {
        "scheduling_score": scheduling_score,
        "alignment_score": alignment_score,
        "workload_score": workload_score,
    }
    calc = compute(**base)

    # ---------- NON-INTERACTIVE PATH for API ----------
    if decision is not None:
        d = decision.lower().strip()
        if d == "edit":
            eff = {
                "scheduling_score": new_scheduling_score if new_scheduling_score is not None else base["scheduling_score"],
                "alignment_score":  new_alignment_score  if new_alignment_score  is not None else base["alignment_score"],
                "workload_score":   new_workload_score   if new_workload_score   is not None else base["workload_score"],
            }
            new_calc = compute(**eff)
            return {**new_calc, "scores": eff, "decision": "edit", "notes": "edited by user (non-interactive)"}

        if d == "approve":
            return {**calc, "scores": base, "decision": "approve", "notes": "approved by user (non-interactive)"}

        if d == "reject":
            return {"weighted_avg": calc["weighted_avg"], "color": "red", "scores": base, "decision": "reject", "notes": "rejected by user (non-interactive)"}

        # "auto" or unknown → just return computed calc
        return {**calc, "scores": base, "decision": d if d else "auto", "notes": "auto-evaluated (non-interactive)"}

    # ---------- INTERACTIVE PATH (only when running inside a LangGraph graph) ----------
    if calc["color"] == "yellow":
        human_input = interrupt(
            "Review required: The evaluation outcome is YELLOW.\n"
            "Please review reasoning, scores, and add additional context if needed.\n"
            "Decisions: [approve, edit, reject]. You may also provide edited scores."
        )
        if not isinstance(human_input, dict) or "decision" not in human_input:
            return {**calc, "scores": base, "decision": "invalid", "notes": "HITL returned invalid payload"}

        d = str(human_input["decision"]).lower().strip()
        if d == "approve":
            return {**calc, "scores": base, "decision": "approve", "notes": "approved via HITL"}
        if d == "reject":
            return {"weighted_avg": calc["weighted_avg"], "color": "red", "scores": base, "decision": "reject", "notes": "rejected via HITL"}
        if d == "edit":
            eff = {
                "scheduling_score": int(human_input.get("scheduling_score", base["scheduling_score"])),
                "alignment_score":  int(human_input.get("alignment_score",  base["alignment_score"])),
                "workload_score":   int(human_input.get("workload_score",   base["workload_score"])),
            }
            new_calc = compute(**eff)
            return {**new_calc, "scores": eff, "decision": "edit", "notes": "edited via HITL"}

        return {**calc, "scores": base, "decision": "invalid", "notes": "HITL invalid decision"}

    # green / red straight-through
    return {**calc, "scores": base, "decision": "auto", "notes": "no HITL needed"}


# -----------------------------
# DatabaseTool (unchanged)
# -----------------------------
class DatabaseTool:
    """Base class for database tools."""

    def __init__(self, dataframe_path_dict):
        self.df_funcs = {}
        for name, df_path in dataframe_path_dict.items():
            df = pd.read_csv(df_path)
            df_func = partial(self._query_dataframe, df)
            self.df_funcs[name] = df_func

    def _query_dataframe(self, df: pd.DataFrame, query: str) -> str:
        try:
            result = df.query(query).to_string()
            return result
        except Exception as e:
            return f"Error executing query: {e}"

    def course_description_tool(self, query: str) -> str:
        return self._query_dataframe(df=self.df_funcs["course_description"], query=query)

    def course_masterlist_tool(self, query: str) -> str:
        return self._query_dataframe(df=self.df_funcs["course_masterlist"], query=query)

    def exams_tool(self, query: str) -> str:
        return self._query_dataframe(df=self.df_funcs["exams"], query=query)

    def lectures_tool(self, query: str) -> str:
        return self._query_dataframe(df=self.df_funcs["lectures"], query=query)

    def tool_factory(self) -> dict[str, StructuredTool]:
        tool_dict: dict[str, StructuredTool] = {}
        for name, func in self.df_funcs.items():
            desc = f"Query the {name} dataframe. Accepts a pandas query string."
            tool_dict[f"{name}_tool"] = StructuredTool.from_function(
                name=f"{name}_tool",
                func=lambda query, f=func: f(query),
                description=desc,
            )
        return tool_dict
