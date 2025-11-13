"""Main agent creation module."""

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from deepagents.middleware.subagents import SubAgentMiddleware
from agents.study_eval_agent import EvalAgents
from object_models import StudyPlanEvaluation, ScoreEvaluation
from tools import weighted_score_tool, workload_score_tool, ask_human_tool


def create_main_agent(eval_agents: EvalAgents, model_name: str, main_agent_prompt: str, synth_prompt: str):
    """Create the main agent for study plan evaluation.

    Args:
        eval_agents (EvalAgents): The evaluation agents to use.
        model_name (str): The name of the model to use.
        main_agent_prompt (str): The prompt for the main agent.

    Returns:
        _type_: _description_
    """
    llm = ChatGroq(model=model_name, temperature=0.1, max_retries=2)
    main_agent = create_agent(
        model=llm,
        tools=[workload_score_tool,
                *eval_agents.get_tools()
               ],
        response_format=ScoreEvaluation,
        # middleware=[
        #     SubAgentMiddleware(
        #         default_model='groq:llama-3.3-70b-versatile',
        #         subagents=[eval_agents.scheduling_agent,eval_agents.alignment_agent],
        #         system_prompt="You are a main agent that delegates tasks to sub-agents for evaluating study plans."
        #     ),
        # ],
    )
    synthezier = create_agent(
        model=llm,
        tools=[weighted_score_tool],
        response_format=StudyPlanEvaluation,
    )
    chain = main_agent_prompt | main_agent | synth_prompt | synthezier
    return chain


def create_interrupt_main_agent(eval_agents: EvalAgents, model_name: str, interrupt_agent_prompt: str, synth_prompt: str):
    """_Create the main agent with human-in-the-loop interrupt capability.

    Args:
        eval_agents (EvalAgents): The evaluation agents to use.
        model_name (str): The name of the model to use.
        interrupt_agent_prompt (str): The prompt for the interrupt agent.

    Returns:
        _type_: _description_
    """
    llm = ChatGroq(model=model_name, temperature=0.1, max_retries=2)

    interrupt_agent = create_agent(
        model=llm,
        tools=[*eval_agents.get_tools(), workload_score_tool],
        response_format=ScoreEvaluation,
    )
    synthezier = create_agent(
        model=llm,
         middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={"ask_human_tool": True}  # Only calls interrupt inside tool
            ),
        ],
        checkpointer=InMemorySaver(),  # InMemory for testing; use persistent in production
        response_format=StudyPlanEvaluation,
        tools=[weighted_score_tool, ask_human_tool],
    )


    chain_with_interrupt = interrupt_agent_prompt | interrupt_agent | synth_prompt | synthezier
    return chain_with_interrupt, synthezier
