"""Evaluation tools with class-based structure."""

from functools import partial
from typing import Any, Dict
import pandas as pd
from langchain_core.tools import StructuredTool


class EvaluationTools:
    """Centralized class for all evaluation tools."""
    
    def __init__(self):
        """Initialize evaluation tools."""
        pass
    
    @staticmethod
    def _workload_score_impl(num_courses: int) -> int:
        """Internal implementation for workload scoring.
        
        Scoring criteria:
        - 6 or fewer courses: 80 points (light workload)
        - 7 to 10 courses: 60 points (moderate workload)
        - More than 10 courses: 30 points (heavy workload)
        """
        if num_courses <= 6:
            return 80
        elif 7 <= num_courses <= 10:
            return 60
        else:
            return 30
    
    @staticmethod
    def _weighted_score_impl(
        scheduling_score: int,
        alignment_score: int,
        workload_score: int
    ) -> Dict[str, Any]:
        """Internal implementation for weighted score calculation.
        
        Weights: 25% scheduling, 25% alignment, 50% workload.
        Thresholds: 0-45=red, 46-75=yellow, 76-100=green
        """
        w_avg = 0.25 * scheduling_score + 0.25 * alignment_score + 0.5 * workload_score
        
        if w_avg <= 45:
            color = "red"
        elif w_avg <= 75:
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
            }
        }
    
    def create_workload_tool(self) -> StructuredTool:
        """Create the workload scoring tool.
        
        Returns:
            StructuredTool that computes workload score from course count
        """
        return StructuredTool.from_function(
            name="workload_score_tool",
            func=self._workload_score_impl,
            description="""Compute workload score based on number of courses.
            
            Scoring criteria:
            - 6 or fewer courses: 80 points (light workload, well-balanced)
            - 7 to 10 courses: 60 points (moderate workload, manageable)
            - More than 10 courses: 30 points (heavy workload, may be overwhelming)
            
            Args:
                num_courses: Total number of courses in the study plan
            
            Returns:
                Workload score from 0-100
            """,
        )
    
    def create_weighted_score_tool(self) -> StructuredTool:
        """Create the weighted scoring tool.
        
        Returns:
            StructuredTool that calculates weighted average and color code
        """
        return StructuredTool.from_function(
            name="weighted_score_tool",
            func=self._weighted_score_impl,
            description="""Calculate weighted average score and determine color code.
            
            Weights: 25% scheduling, 25% alignment, 50% workload.
            Thresholds: 0-45=red, 46-75=yellow, 76-100=green.
            
            Args:
                scheduling_score: Score from scheduling evaluation (0-100)
                alignment_score: Score from alignment evaluation (0-100)
                workload_score: Score from workload evaluation (0-100)
            
            Returns:
                Dictionary with weighted_avg, color, and component scores
            """,
        )
    
    def get_all_evaluation_tools(self) -> Dict[str, StructuredTool]:
        """Get all evaluation tools as a dictionary.
        
        Returns:
            Dictionary mapping tool names to StructuredTool objects
        """
        return {
            "workload_score_tool": self.create_workload_tool(),
            "weighted_score_tool": self.create_weighted_score_tool(),
        }


class DatabaseTool:
    """CSV-backed database query tools."""
    
    def __init__(self, dataframe_path_dict: dict):
        """Initialize database tools with CSV file paths.
        
        Args:
            dataframe_path_dict: Mapping from logical names to CSV file paths
        """
        self.df_funcs = {}
        self.dataframes = {}
        
        for name, df_path in dataframe_path_dict.items():
            df = pd.read_csv(df_path)
            self.dataframes[name] = df
            self.df_funcs[name] = partial(self._query_dataframe, df)
    
    def _query_dataframe(self, df: pd.DataFrame, query: str) -> str:
        """Execute a pandas query on a dataframe.
        
        Args:
            df: DataFrame to query
            query: Pandas query string
        
        Returns:
            String representation of query results or error message
        """
        try:
            return df.query(query).to_string()
        except Exception as e:
            return f"Error executing query: {e}"
    
    def tool_factory(self) -> Dict[str, StructuredTool]:
        """Create LangChain StructuredTool objects for each dataframe.
        
        Returns:
            Dictionary mapping tool names to StructuredTool objects
        """
        tool_dict = {}
        def make_query_func(f):
            def query_func(query: str) -> str:
                return f(query)
            return query_func
        for name, func in self.df_funcs.items():
            desc = f"Query the {name} dataframe using pandas query syntax. Returns matching rows."
            tool_dict[f"{name}_tool"] = StructuredTool.from_function(
                name=f"{name}_tool",
            func=make_query_func(func),
                description=desc,
            )
        return tool_dict


class ToolRegistry:
    """Central registry for all tools used in the study plan evaluation system."""
    
    def __init__(self, dataframe_path_dict: dict):
        """Initialize the tool registry.
        
        Args:
            dataframe_path_dict: Mapping from logical names to CSV file paths
        """
        self.evaluation_tools = EvaluationTools()
        self.database_tools = DatabaseTool(dataframe_path_dict)
    
    def get_database_tools(self) -> Dict[str, StructuredTool]:
        """Get all database query tools.
        
        Returns:
            Dictionary of database tools (exams, lectures, courses, etc.)
        """
        return self.database_tools.tool_factory()
    
    def get_evaluation_tools(self) -> Dict[str, StructuredTool]:
        """Get all evaluation tools.
        
        Returns:
            Dictionary of evaluation tools (workload, weighted scoring)
        """
        return self.evaluation_tools.get_all_evaluation_tools()
    
    def get_scheduling_tools(self) -> list[StructuredTool]:
        """Get tools for scheduling evaluation.
        
        Returns:
            List of tools needed for scheduling node
        """
        db_tools = self.get_database_tools()
        return [
            db_tools["exams_tool"],
            db_tools["lectures_tool"],
        ]
    
    def get_alignment_tools(self) -> list[StructuredTool]:
        """Get tools for alignment evaluation.
        
        Returns:
            List of tools needed for alignment node
        """
        db_tools = self.get_database_tools()
        return [
            db_tools["course_description_tool"],
            db_tools["course_masterlist_tool"],
        ]
    
    def get_workload_tools(self) -> list[StructuredTool]:
        """Get tools for workload evaluation.
        
        Returns:
            List of tools needed for workload node
        """
        eval_tools = self.get_evaluation_tools()
        return [eval_tools["workload_score_tool"]]
    
    def get_synthesis_tools(self) -> list[StructuredTool]:
        """Get tools for synthesis evaluation.
        
        Returns:
            List of tools needed for synthesis node
        """
        eval_tools = self.get_evaluation_tools()
        return [eval_tools["weighted_score_tool"]]
