"""Module defining various tools for evaluation and database querying."""

from functools import partial
from typing import Any, Dict

import pandas as pd
from langchain_core.tools import StructuredTool, tool


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

    Weights: 0.25 sched, 0.25 align, 0.5 workload (pure, no HITL).
    """
    w_avg = 0.25 * scheduling_score + 0.25 * alignment_score + 0.5 * workload_score
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
    }


@tool
def ask_human_tool() -> None:
    """Tool to ask human for review in HITL scenarios."""
    pass
    return None


@tool
def workload_score_tool(num_courses: int) -> int:
    """Compute a simple workload score based on the number of courses."""
    if num_courses <= 6:
        return 80  # light workload
    elif 7 <= num_courses <= 10:
        return 60  # moderate workload
    else:
        return 30  # heavy workload


# ToDo: Replace with DB queries
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
