"""Main entry point for running the study plan evaluation with optional HITL."""

import getpass
import os
import warnings
from pprint import pprint

from dotenv import load_dotenv
from pydantic.json_schema import PydanticJsonSchemaWarning

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

# To suppress all PydanticJsonSchemaWarning warnings
warnings.filterwarnings("ignore", category=PydanticJsonSchemaWarning)
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")


if not api_key:

    api_key = getpass.getpass("Enter your Groq API key: ")

    with open(".env", "a") as f:
        f.write(f"\nGROQ_API_KEY={api_key}")

    os.environ["GROQ_API_KEY"] = api_key


llama_70b = "llama-3.3-70b-versatile"
llama_8b = "llama-3.1-8b-instant"
context_parent = f"{os.getcwd()}/src/context_tables"


def run_evaluation(chain, study_plan: str):
    result = chain.invoke({"study_plan": study_plan})
    # Parse results into StudyPlanEvaluation
    return result


dataframe_path_dict = {
    "exams": f"{context_parent}/exams.csv",
    "lectures": f"{context_parent}/lectures.csv",
    "course_description": f"{context_parent}/course_description.csv",
    "course_masterlist": f"{context_parent}/course_masterlist.csv",
}

db_tools = DatabaseTool(dataframe_path_dict)
eval_agents = EvalAgents(
    db_tools,
    scheduling_prompt=scheduling_prompt,
    alignment_prompt=alignment_prompt,
    model_name=llama_70b,
)

hitl = True

if __name__ == "__main__":
    # Example usage with a test study plan
    print("Running Study Plan Evaluation...")
    if hitl:
        print("Running with Human-in-the-Loop Interrupt...")
        main_agent = create_interrupt_main_agent(
            eval_agents,
            model_name=llama_70b,
            interrupt_agent_prompt=interrupt_agent_prompt,
        )
        evaluation = run_hitl_evaluation(main_agent, yellow_case)
        pprint(evaluation)
    else:
        main_agent = create_main_agent(eval_agents, model_name=llama_70b, main_agent_prompt=main_agent_prompt)
        evaluation = run_evaluation(main_agent, green_case)
        pprint(evaluation["structured_response"].model_dump())
