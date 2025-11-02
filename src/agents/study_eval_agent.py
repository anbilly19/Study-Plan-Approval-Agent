
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from tools import DatabaseTool
from langchain_core.tools import StructuredTool

class EvalAgents:    
    """Class encapsulating evaluation agents for study plans."""
    def __init__(self, db_tools: DatabaseTool, scheduling_prompt, alignment_prompt, model_name:str):
        llm = ChatGroq(model=model_name,
            temperature=0.0,
            max_retries=2)
        tool_dict = db_tools.tool_factory()
        self.scheduling_agent = create_agent(model=llm, tools=[tool_dict["exams_tool"],tool_dict["lectures_tool"]])  # Add relevant table tools
        self.alignment_agent = create_agent(model=llm, tools=[tool_dict["course_description_tool"],tool_dict["course_masterlist_tool"]])  # Add relevant table tools
        self.scheduling_prompt = scheduling_prompt
        self.alignment_prompt = alignment_prompt


    def call_scheduling_agent(self, study_plan: str) -> dict:
        chain = self.scheduling_prompt | self.scheduling_agent
        result = chain.invoke({"study_plan": study_plan})
        # Ensure the output structure matches StudyPlanEvaluation (score and reasoning)
        return {
            "score": result.get("score"),
            "reasoning": result.get("reasoning")
        }

    def call_alignment_agent(self, study_plan: str) -> dict:
        chain = self.alignment_prompt | self.alignment_agent
        result = chain.invoke({"study_plan": study_plan})
        # Ensure the output structure matches StudyPlanEvaluation (score and reasoning)
        return {
            "score": result.get("score"),
            "reasoning": result.get("reasoning")
        }
    
    def get_tools(self):
        return [
            StructuredTool.from_function(
                name="alignment_evaluator",
                func=lambda plan: self.call_alignment_agent(plan),
                description="Evaluates courses alignment with major/minor.",
            ),
            StructuredTool.from_function(
                name="schedule_evaluator",
                func=lambda plan: self.call_scheduling_agent(plan),
                description="Assesses study plan schedule for breaks and conflicts.",
            )
        ]