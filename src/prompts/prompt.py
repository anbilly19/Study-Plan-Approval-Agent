"""
This module loads and constructs prompt templates for various agents.

Loads prompt text files from src/prompts/templates/.
Builds ChatPromptTemplate objects for all agents.

Prompts included:
- Scheduling Agent
- Alignment Agent
- Main Agent (standard and interrupt-capable)
- Synthesis prompts (standard and interrupt-capable)
"""

import os

from langchain_core.prompts import ChatPromptTemplate


def load_prompt(path):
    """Load a text file and return its contents.

    This utility reads a file from disk and returns the full content as a string.
    """
    with open(path, "r") as f:
        return f.read()


# Load all prompt template files from the templates directory

# Directory where all prompt template .txt files are stored.
prompt_parent = f"{os.getcwd()}/src/prompts/templates/"

# Load raw prompt text files for each agent component.
scheduling_prompt_text = load_prompt(f"{prompt_parent}/schedule_prompt.txt")
alignment_prompt_text = load_prompt(f"{prompt_parent}/alignment_prompt.txt")

main_agent_prompt_text = load_prompt(f"{prompt_parent}/vanilla_main.txt")
interrupt_agent_prompt_text = load_prompt(f"{prompt_parent}/interrupt_main.txt")


# Construct ChatPromptTemplate objects for LangChain agents

# Scheduling Agent prompt:
# - Simple single-message prompt where the "human" role provides the full instruction text.
scheduling_prompt = ChatPromptTemplate.from_messages(("human", scheduling_prompt_text))

# Alignment Agent prompt:
alignment_prompt = ChatPromptTemplate.from_messages(("human", alignment_prompt_text))


# Interrupt-capable main agent prompt:
# - Includes a "system" instruction containing the template text.
# - "human" message injects the dynamic study_plan.
interrupt_agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", interrupt_agent_prompt_text),
        ("human", "Given a study plan: \n{study_plan}\n"),
    ]
)

# Regular main agent prompt (non-HITL):
main_agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", main_agent_prompt_text),
        ("human", "Given a study plan: \n{study_plan}\n"),
    ]
)


# Synthesis prompts (final stage after agent evaluations)

# Non-interrupt synthesis prompt:
# - Advises the model to call weighted_score_tool.
# - Provides structured_response JSON from agents for final judgment.
synth_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert academic advisor. Call the weighted score tool to synthesize final evaluation. "
            "Extract scheduling_score, alignment_score and workload_score from evaluations and"
            "provide an overall recommendation.",
        ),
        (
            "human",
            "Based on the following scores and evaluations, provide a final assessment of the study plan:"
            "\n{structured_response}\n",
        ),
    ]
)

# Interrupt-enabled synthesis prompt:
# - Allows calling ask_human when evaluation is YELLOW.
# - Asks the model to incorporate user feedback during HITL evaluation.
synth_prompt_interrupt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an academic advisor assistant. Call the weighted score tool to synthesize evaluation."
            "Extract scheduling_score, alignment_score and workload_score from evaluations and provide an overall"
            "recommendation. When human feedback is provided, consider it in your assessment. "
            "Call the ask_human tool if the evaluation is YELLOW to get human review.",
        ),
        (
            "human",
            "Based on the following scores and evaluations, provide a final assessment of the study plan:"
            "\n{structured_response}\n",
        ),
    ]
)

# Pre-loaded example study plans for debugging / testing

green_case = load_prompt(f"{prompt_parent}/green_case.txt")  # Good plan
yellow_case = load_prompt(f"{prompt_parent}/yellow_structured.txt")  # Needs review
red_case = load_prompt(f"{prompt_parent}/red_structured.txt")  # Bad plan
