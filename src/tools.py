"""Module defining various tools for evaluation and database querying that the agent can use."""

from functools import partial
from typing import Any, Dict

import pandas as pd
from langchain_core.tools import StructuredTool, tool


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
    # Compute a weighted average of the three scores:
    # - scheduling_score: weight 0.25
    # - alignment_score: weight 0.25
    # - workload_score: weight 0.50 (more important)
    w_avg = 0.25 * scheduling_score + 0.25 * alignment_score + 0.5 * workload_score

    # Map numeric weighted average into a traffic-light color category.
    # - 0–45: red (poor)
    # - 46–75: yellow (needs review)
    # - 76–100: green (good)
    if 0 <= w_avg <= 45:
        color = "red"
    elif 46 <= w_avg <= 75:
        color = "yellow"
    else:
        color = "green"

    # Return a structured dictionary that can be parsed or wrapped into a model.
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
def ask_human_tool(reasoning:str) -> str:
    """Tool to ask human for review in HITL (Human-In-The-Loop) scenarios.

    This is a placeholder tool that agents can call to signal that
    human intervention/approval is required. Currently, it performs
    no logic and simply returns the reasoning of why the LLM needs a human.
    """
    
    return reasoning


@tool
def workload_score_tool(num_courses: int) -> int:
    """Compute a simple workload score based on the number of courses.

    Heuristics:
    - <= 6 courses  -> 80 (light workload)
    - 7–10 courses  -> 60 (moderate workload)
    - > 10 courses  -> 30 (heavy workload)
    """
    if num_courses <= 6:
        return 80  # light workload
    elif 7 <= num_courses <= 10:
        return 60  # moderate workload
    else:
        return 30  # heavy workload


# ToDo: Replace with direct DB queries instead of CSV-backed dataframes.
class DatabaseTool:
    """Base class for database tools.

    Loads CSV files into pandas DataFrames and exposes them as
    queryable tools for LangChain agents. Each CSV is accessed via
    a dedicated tool that accepts a pandas query string.
    """

    def __init__(self, dataframe_path_dict):
        """
        Initialize the DatabaseTool with a mapping from logical names to CSV file paths.

        Args:
            dataframe_path_dict: dict mapping names (e.g. "course_description")
                                 to CSV file paths.
        """
        # df_funcs maps a dataframe name to a callable that runs a query on it.
        self.df_funcs = {}
        for name, df_path in dataframe_path_dict.items():
            # Load CSV into a pandas DataFrame.
            df = pd.read_csv(df_path)
            # Create a function that will query this specific DataFrame.
            df_func = partial(self._query_dataframe, df)
            # Store it under the given name so it can be turned into a tool later.
            self.df_funcs[name] = df_func

    def _query_dataframe(self, df: pd.DataFrame, query: str) -> str:
        """Run a pandas query on a given DataFrame and return the result as a string.

        Args:
            df: The DataFrame to query.
            query: A pandas query string (bool expression).

        Returns:
            A string representation of the filtered DataFrame,
            or an error message if the query fails.
        """
        try:
            result = df.query(query).to_string()
            return result
        except Exception as e:
            # Catch any errors from an invalid query and return a readable message.
            return f"Error executing query: {e}"

    # Convenience wrappers for specific dataframes (assuming they exist in df_funcs).

    def course_description_tool(self, query: str) -> str:
        """Query the course_description dataframe using a pandas query string."""
        return self._query_dataframe(df=self.df_funcs["course_description"], query=query)

    def course_masterlist_tool(self, query: str) -> str:
        """Query the course_masterlist dataframe using a pandas query string."""
        return self._query_dataframe(df=self.df_funcs["course_masterlist"], query=query)

    def exams_tool(self, query: str) -> str:
        """Query the exams dataframe using a pandas query string."""
        return self._query_dataframe(df=self.df_funcs["exams"], query=query)

    def lectures_tool(self, query: str) -> str:
        """Query the lectures dataframe using a pandas query string."""
        return self._query_dataframe(df=self.df_funcs["lectures"], query=query)

    def tool_factory(self) -> dict[str, StructuredTool]:
        """Create LangChain StructuredTool objects for each loaded dataframe.

        Returns:
            A dictionary mapping tool names to StructuredTool instances.
            Each tool:
            - is named `<df_name>_tool`
            - accepts a single `query` argument (pandas query string)
            - returns the stringified query result.
        """
        tool_dict: dict[str, StructuredTool] = {}
        for name, func in self.df_funcs.items():
            desc = f"Query the {name} dataframe. Accepts a pandas query string."
            # Use a default argument (f=func) in the lambda to bind the current func
            # and avoid late binding issues in loops.
            tool_dict[f"{name}_tool"] = StructuredTool.from_function(
                name=f"{name}_tool",
                func=lambda query, f=func: f(query),
                description=desc,
            )
        return tool_dict
