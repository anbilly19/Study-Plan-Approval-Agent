from langchain_core.tools import StructuredTool
from langchain_core.tools import tool
import pandas as pd
from functools import partial
from langgraph.types import interrupt

@tool
def weighted_score_tool(scheduling_score:int, alignment_score:int, workload_score: int) -> str:
    """
    Calculate the weighted average score and return a color code based on the score."""
    w_avg = (0.4*scheduling_score + 0.4*alignment_score + 0.2*workload_score)
    if 0 <= w_avg <= 45:
        return "red"
    elif 46 <= w_avg <= 75:
        return "yellow"
    else:
        return "green"

@tool
def weighted_score_tool_with_interrupt(scheduling_score:int, alignment_score:int, workload_score: int) -> str:
    """
    Calculate the weighted average score and return a color code based on the score.
    """
    w_avg = 0.4 * scheduling_score + 0.5 * alignment_score + 0.1 * workload_score
    
    if 0 <= w_avg <= 45:
        return "red"
    elif 46 <= w_avg <= 75:
        # Pause and request human review
        human_input = interrupt(
            "Review required: The evaluation outcome is YELLOW.\n"
            "Please review reasoning, scores, and add additional context if needed. Decisions: [approve, edit, reject]."
        )
        # Incorporate human input for final output (assume human_input is a dict with 'decision' and optional 'context')
        if human_input['decision'] == "approve":
            return "green"
        elif human_input['decision'] == "edit":
            # Recalculate based on human context (for simplicity, assume human provides new scores)
            new_scheduling_score = human_input.get('scheduling_score', scheduling_score)
            new_alignment_score = human_input.get('alignment_score', alignment_score)
            new_workload_score = human_input.get('workload_score', workload_score)
            return f"Revaluate based on new scores: {new_scheduling_score}, {new_alignment_score}, {new_workload_score}"
        elif human_input['decision'] == "reject":
            return "red"
    else:
        return "green"

class DatabaseTool:
    """Base class for database tools."""
    def __init__(self, dataframe_path_dict: dict[pd.DataFrame]):
        
        self.df_funcs = {}
        for name, df_path in dataframe_path_dict.items():
            df = pd.read_csv(df_path)
            df_func = partial(self._query_dataframe, df)
            self.df_funcs[name] = df_func

    def _query_dataframe(self,df: pd.DataFrame, query: str) -> str:
        try:
            result = df.query(query).to_string()
            return result
        except Exception as e:
            return f"Error executing query: {e}"
        
    def course_description_tool(self, query: str) -> str:
        
        return self._query_dataframe(df=self.df_func["course_description"],query=query)

    def course_masterlist_tool(self,  query: str) -> str:
       
        return self._query_dataframe(df=self.df_func["course_masterlist"],query=query)

    def exams_tool(self,  query: str) -> str:
       
        return self._query_dataframe(df=self.df_func["exams"],query=query)
 
    def lectures_tool(self,   query: str) -> str:
    
        return self._query_dataframe(df=self.df_func["lectures"],query=query)
    
    
    def tool_factory(self) -> dict[StructuredTool]:
        tool_dict = {}
        for name, func in self.df_funcs.items():
            tool_dict[f"{name}_tool"] = StructuredTool.from_function(
                name=f"{name}_tool",
                func=lambda query, f=func: f(query),
                description=f"Query the {name} dataframe. Accepts a pandas query string.",
            )
        return tool_dict