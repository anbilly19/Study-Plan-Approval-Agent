"""Main agent creation module.

Defines factory functions for:
- A standard (non-HITL) main agent pipeline.
- An interrupt-capable main agent pipeline with Human-In-The-Loop (HITL) synthesis.
"""

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from ..object_models import ScoreEvaluation, StudyPlanEvaluation
from ..tools import ask_human_tool, weighted_score_tool, workload_score_tool
from .study_eval_agent import EvalAgents


def create_main_agent(
    eval_agents: EvalAgents,
    model_name: str,
    main_agent_prompt,
    synth_prompt,
):
    """Create the main (non-HITL) agent for study plan evaluation.

    This pipeline:
        1. Uses a main agent to call sub-agent tools (e.g., scheduling/alignment agents,
           workload score tool).
        2. Produces a structured ScoreEvaluation (scheduling_score, alignment_score,
           workload_score).
        3. Feeds that into a synthesizer agent which calls weighted_score_tool and
           returns a StudyPlanEvaluation.

    Args:
        eval_agents: Container holding sub-agent definitions and tools.
        model_name: OpenAI model name to use (e.g. "gpt-4o").
        main_agent_prompt: A ChatPromptTemplate (or runnable prompt) to drive the main agent.
        synth_prompt: A ChatPromptTemplate (or runnable prompt) to drive the synthesis agent.

    Returns:
        A LangChain runnable pipeline:
            main_agent_prompt -> main_agent -> synth_prompt -> synthesizer
    """
    # Shared LLM configuration used by both main and synthesizer agents.
    llm = ChatOpenAI(model=model_name, temperature=0.1, max_retries=2)

    # Main evaluation agent:
    # - Can call workload_score_tool and the tools exposed by eval_agents (e.g. scheduling/alignment).
    # - Returns a ScoreEvaluation pydantic model via structured output.
    main_agent = create_agent(
        model=llm,
        tools=[
            workload_score_tool,
            *eval_agents.get_tools(),
        ],
        response_format=ScoreEvaluation,
        # Example of possible future setup with sub-agent middleware:
        # middleware=[
        #     SubAgentMiddleware(
        #         default_model='groq:llama-3.3-70b-versatile',
        #         subagents=[eval_agents.scheduling_agent, eval_agents.alignment_agent],
        #         system_prompt="You are a main agent that delegates tasks to sub-agents for evaluating study plans."
        #     ),
        # ],
    )

    # Synthesizer agent:
    # - Calls weighted_score_tool using the scores from the main agent.
    # - Returns a StudyPlanEvaluation pydantic model.
    synthesizer = create_agent(
        model=llm,
        tools=[weighted_score_tool],
        response_format=StudyPlanEvaluation,
    )

    # Chain the prompt → main agent → synthesis prompt → synthesizer.
    chain = main_agent_prompt | main_agent | synth_prompt | synthesizer
    return chain


def create_interrupt_main_agent(
    eval_agents: EvalAgents,
    model_name: str,
    interrupt_agent_prompt,
    synth_prompt,
):
    """Create the main agent with Human-In-The-Loop (HITL) interrupt capability.

    This pipeline:
        1. Uses an interrupt-capable main agent to compute ScoreEvaluation.
        2. Feeds that into a synthesizer agent that:
            - Can call weighted_score_tool and ask_human_tool.
            - Uses HumanInTheLoopMiddleware to trigger interrupts when ask_human_tool
              is invoked.
        3. The calling code (e.g., run_hitl_evaluation) handles the interrupt and then
           resumes the graph with human decisions.

    Args:
        eval_agents: Container holding sub-agent definitions and tools.
        model_name: OpenAI model name to use.
        interrupt_agent_prompt: Prompt template for the interrupt-capable main agent.
        synth_prompt: Prompt template for the synthesis step in HITL mode.

    Returns:
        A tuple:
            (chain_with_interrupt, synthesizer)
        where:
            - chain_with_interrupt is the full pipeline
              (interrupt_agent_prompt -> interrupt_agent -> synth_prompt -> synthesizer)
            - synthesizer is returned separately so external code can resume execution
              with a Command object after an interrupt.
    """
    # Shared LLM configuration.
    llm = ChatOpenAI(model=model_name, temperature=0.1, max_retries=2)

    # Interrupt-capable agent:
    # - Same basic role as the main agent, but used in the HITL pipeline.
    interrupt_agent = create_agent(
        model=llm,
        tools=[*eval_agents.get_tools(), workload_score_tool],
        response_format=ScoreEvaluation,
    )

    # Synthesizer agent with Human-In-The-Loop middleware:
    # - HumanInTheLoopMiddleware traps calls to ask_human_tool and surfaces them
    #   as interrupts (__interrupt__ entry).
    # - InMemorySaver checkpointing is used for testing; in production, use persistent storage.
    synthesizer = create_agent(
        model=llm,
        middleware=[
            HumanInTheLoopMiddleware(interrupt_on={"ask_human_tool": True}),  # Only interrupt when this tool is called.
        ],
        checkpointer=InMemorySaver(),
        response_format=StudyPlanEvaluation,
        tools=[weighted_score_tool, ask_human_tool],
    )

    # Full pipeline with interrupt support.
    chain_with_interrupt = interrupt_agent_prompt | interrupt_agent | synth_prompt | synthesizer
    return chain_with_interrupt, synthesizer
