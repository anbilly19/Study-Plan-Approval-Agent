import os
from agents.study_eval_agent import EvalAgents
from agents.main_agent import create_main_agent, create_interrupt_main_agent

from hitl.eval_interrupt import run_hitl_evaluation
from prompts.prompt import main_agent_prompt, interrupt_agent_prompt, red_case, yellow_case, green_case, scheduling_prompt, alignment_prompt
from tools import DatabaseTool
from pprint import pprint
import getpass
import warnings
from pydantic.json_schema import PydanticJsonSchemaWarning

# To suppress all PydanticJsonSchemaWarning warnings
warnings.filterwarnings('ignore', category=PydanticJsonSchemaWarning)
if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = getpass.getpass("Enter your Groq API key: ")

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
    "course_masterlist": f"{context_parent}/course_masterlist.csv"
    }

db_tools = DatabaseTool(dataframe_path_dict)
eval_agents = EvalAgents(
    db_tools,
    scheduling_prompt=scheduling_prompt,
    alignment_prompt=alignment_prompt,
    model_name=llama_70b
)

hitl=True

if __name__ == "__main__":
    # Example usage with a test study plan
    if hitl:
        main_agent = create_interrupt_main_agent(eval_agents, model_name=llama_70b, interrupt_agent_prompt=interrupt_agent_prompt)
        evaluation = run_hitl_evaluation(main_agent, yellow_case)
        pprint(evaluation)
    else:
        main_agent = create_main_agent(eval_agents, model_name=llama_70b, main_agent_prompt=main_agent_prompt)
        evaluation = run_evaluation(main_agent, green_case)
        pprint(evaluation['structured_response'].model_dump())