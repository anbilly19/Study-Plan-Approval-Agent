"""Module defining evaluation agents for study plans.

This module constructs two sub-agents:
1. Scheduling Agent   – evaluates scheduling feasibility (conflicts, breaks, exams).
2. Alignment Agent    – evaluates alignment with major/minor and academic goals.

Both sub-agents:
- Use database-backed StructuredTools (e.g., querying course descriptions or exam tables).
- Return SubAgentEvaluation (score + reasoning) via structured output.
"""

from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from ..object_models import SubAgentEvaluation
from ..tools import DatabaseTool


class EvalAgents:
    """Encapsulates sub-agents responsible for evaluating a study plan.

    Responsibilities:
        - Build scheduling and alignment evaluation agents.
        - Provide wrappers for invoking these agents.
        - Expose them as LangChain tools that the main agent can call.
    """

    def __init__(
        self,
        db_tools: DatabaseTool,
        scheduling_prompt,
        alignment_prompt,
        model_name: str,
    ):
        # Shared LLM used by both sub-agents.
        llm = ChatOpenAI(model=model_name, temperature=0.0, max_retries=2)

        # Convert the DataFrame-backed CSVs into StructuredTools.
        tool_dict = db_tools.tool_factory()

        # Cache prompts for later use.
        self.scheduling_prompt = scheduling_prompt
        self.alignment_prompt = alignment_prompt

        # Scheduling Agent

        # Uses:
        #   - exams_tool
        #   - lectures_tool
        # to analyze conflicts, exam clustering, and time distribution.
        self.scheduling_agent = create_agent(
            model=llm,
            tools=[
                tool_dict["exams_tool"],
                tool_dict["lectures_tool"],
            ],
            response_format=SubAgentEvaluation,  # Outputs: score + reasoning
        )

        # Alignment Agent

        # Uses:
        #   - course_description_tool
        #   - course_masterlist_tool
        # to verify relevance of chosen courses to academic goals.
        self.alignment_agent = create_agent(
            model=llm,
            tools=[
                tool_dict["course_description_tool"],
                tool_dict["course_masterlist_tool"],
            ],
            response_format=SubAgentEvaluation,
        )

    # Direct callable wrappers for each sub-agent

    def call_scheduling_agent(self, study_plan: str) -> dict:
        """Invoke the scheduling agent with its prompt and structured_output."""
        chain = self.scheduling_prompt | self.scheduling_agent
        result = chain.invoke({"study_plan": study_plan})
        return result  # result is a SubAgentEvaluation

    def call_alignment_agent(self, study_plan: str) -> dict:
        """Invoke the alignment agent with its prompt and structured_output."""
        chain = self.alignment_prompt | self.alignment_agent
        result = chain.invoke({"study_plan": study_plan})
        return result  # result is a SubAgentEvaluation

    # Tools exported to the main agent

    def get_tools(self):
        """Return both evaluation agents as LangChain tools the main agent can call.

        Each tool:
            - Calls the corresponding agent pipeline.
            - Returns SubAgentEvaluation directly.
            - Is invoked via tool call, not natural language.
        """
        def call_alignment(plan: str) -> dict:
            return self.call_alignment_agent(plan)

        def call_scheduling(plan: str) -> dict:
            return self.call_scheduling_agent(plan)

        return [
            StructuredTool.from_function(
                name="alignment_evaluator",
                func=call_alignment,
                description="Evaluates whether the study plan aligns with the student's goals and major/minor requirements.",
                return_direct=True,
            ),
            StructuredTool.from_function(
                name="schedule_evaluator",
                func=call_scheduling,
                description="Evaluates whether the study plan avoids conflicts, has reasonable spacing, and balances lectures/exams.",
                return_direct=True,
            ),
        ]
