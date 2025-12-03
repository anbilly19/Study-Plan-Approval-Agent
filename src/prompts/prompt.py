import os

from langchain_core.prompts import ChatPromptTemplate


def load_prompt(path):
    with open(path, "r") as f:
        return f.read()


prompt_parent = f"{os.getcwd()}/src/prompts/templates/"
scheduling_prompt_text = load_prompt(f"{prompt_parent}/schedule_prompt.txt")
alignment_prompt_text = load_prompt(f"{prompt_parent}/alignment_prompt.txt")

main_agent_prompt_text = load_prompt(f"{prompt_parent}/vanilla_main.txt")
interrupt_agent_prompt_text = load_prompt(f"{prompt_parent}/interrupt_main.txt")

# Scheduling agent prompt
scheduling_prompt = ChatPromptTemplate.from_messages(("human", scheduling_prompt_text))

# Alignment agent prompt
alignment_prompt = ChatPromptTemplate.from_messages(("human", alignment_prompt_text))

interrupt_agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", interrupt_agent_prompt_text),
        ("human", "Given a study plan: \n{study_plan}\n"),
    ]
)

main_agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", main_agent_prompt_text),
        ("human", "Given a study plan: \n{study_plan}\n"),
    ]
)
synth_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are an expert academic advisor. Call the weighted score tool to synthesize final evaluation. "
        "Extract scheduling_score, alignment_score and workload_score from evaluations and provide an overall recommendation."),
        (
            "human",
            "Based on the following scores and evaluations, provide a final assessment of the study plan:\n{structured_response}\n",
        ),
    ]
)
synth_prompt_interrupt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are an academic advisor assisstant. Call the weighted score tool to synthesize evaluation. "
        "Extract scheduling_score, alignment_score and workload_score from evaluations and provide an overall recommendation."
        " When human feedback is provided, consider it in your assessment."
        "Call the ask_human tool if the evaluation is YELLOW to get human review."),
        (
            "human",
            "Based on the following scores and evaluations, provide a final assessment of the study plan:\n{structured_response}\n",
        ),
    ]
)
# input prompts for testing different cases
green_case = load_prompt(f"{prompt_parent}/green_case.txt")
yellow_case = load_prompt(f"{prompt_parent}/yellow_structured.txt")
red_case = load_prompt(f"{prompt_parent}/red_structured.txt")
