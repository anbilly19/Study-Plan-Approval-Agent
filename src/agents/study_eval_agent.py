"""Module defining evaluation agents for study plans."""

from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_groq import ChatGroq
from object_models import SubAgentEvaluation
from tools import DatabaseTool


class EvalAgents:
    """Class encapsulating evaluation agents for study plans."""

    def __init__(
        self,
        db_tools: DatabaseTool,
        scheduling_prompt,
        alignment_prompt,
        model_name: str,
    ):
        llm = ChatGroq(model=model_name, temperature=0.0, max_retries=2)
        tool_dict = db_tools.tool_factory()
        self.scheduling_prompt = scheduling_prompt
        self.alignment_prompt = alignment_prompt
        self.scheduling_agent = create_agent(
            model=llm, tools=[tool_dict["exams_tool"], tool_dict["lectures_tool"]],
            response_format=SubAgentEvaluation
        )  # Add relevant table tools
        # self.scheduling_agent = {
        #             "name": "schedule_evaluator",
        #             "description": "Use the exams_tool and lectures_tool to provide scheduling evaluation for the given study plan.",
        #             "system_prompt":scheduling_prompt,
        #             "tools": [tool_dict["exams_tool"], tool_dict["lectures_tool"]],
        #             "model": "groq:llama-3.3-70b-versatile",
        #         }
        self.alignment_agent = create_agent(
            model=llm,
            tools=[
                tool_dict["course_description_tool"],
                tool_dict["course_masterlist_tool"],
            ],
            response_format=SubAgentEvaluation
        )  
        # Add relevant table tools
        # self.alignment_agent = {
        #             "name": "alignment_evaluator",
        #             "description": "Use the course_masterlist_tool and course_description_tool to provide alignment evaluation for the given study plan.",
        #             "system_prompt":alignment_prompt,
        #             "tools": [tool_dict["course_description_tool"], tool_dict["course_masterlist_tool"]],
        #             "model": "groq:llama-3.3-70b-versatile",
        #         }
        
        

    def call_scheduling_agent(self, study_plan: str) -> dict:
        chain = self.scheduling_prompt | self.scheduling_agent
        result = chain.invoke({"study_plan": study_plan})
        # Ensure the output structure matches StudyPlanEvaluation (score and reasoning)
        return result

    def call_alignment_agent(self, study_plan: str) -> dict:
        chain = self.alignment_prompt | self.alignment_agent
        result = chain.invoke({"study_plan": study_plan})
        # Ensure the output structure matches StudyPlanEvaluation (score and reasoning)
        return result

    def get_tools(self):
        return [
            StructuredTool.from_function(
                name="alignment_evaluator",
                func=lambda plan: self.call_alignment_agent(plan),
                description="Evaluates courses alignment with major/minor.",
                return_direct=True
            ),
            StructuredTool.from_function(
                name="schedule_evaluator",
                func=lambda plan: self.call_scheduling_agent(plan),
                description="Assesses study plan schedule for breaks and conflicts.",
                return_direct=True
            ),
        ]
