"""Main agent creation module."""

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver

from agents.study_eval_agent import EvalAgents
from object_models import StudyPlanEvaluation
from tools import weighted_score_tool, weighted_score_tool_with_interrupt


def create_main_agent(eval_agents: EvalAgents, model_name: str, main_agent_prompt: str):
    """Create the main agent for study plan evaluation.

    Args:
        eval_agents (EvalAgents): The evaluation agents to use.
        model_name (str): The name of the model to use.
        main_agent_prompt (str): The prompt for the main agent.

    Returns:
        _type_: _description_
    """
    llm = ChatGroq(model=model_name, temperature=0.0, max_retries=2)
    main_agent = create_agent(
        model=llm,
        tools=[*eval_agents.get_tools(), weighted_score_tool],
        response_format=StudyPlanEvaluation,
    )
    chain = main_agent_prompt | main_agent
    return chain


def create_interrupt_main_agent(eval_agents: EvalAgents, model_name: str, interrupt_agent_prompt: str):
    """_Create the main agent with human-in-the-loop interrupt capability.

    Args:
        eval_agents (EvalAgents): The evaluation agents to use.
        model_name (str): The name of the model to use.
        interrupt_agent_prompt (str): The prompt for the interrupt agent.

    Returns:
        _type_: _description_
    """
    llm = ChatGroq(model=model_name, temperature=0.0, max_retries=2)

    interrupt_agent = create_agent(
        model=llm,
        tools=[weighted_score_tool_with_interrupt, *eval_agents.get_tools()],
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={"weighted_score_tool_with_interrupt": True}  # Only calls interrupt inside tool
            ),
        ],
        checkpointer=InMemorySaver(),  # InMemory for testing; use persistent in production
        response_format=StudyPlanEvaluation,
    )

    chain_with_interrupt = interrupt_agent_prompt | interrupt_agent
    return chain_with_interrupt
