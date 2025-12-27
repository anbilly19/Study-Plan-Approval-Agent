"""Node functions for the study plan evaluation graph."""

from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from langgraph.types import Command, interrupt

from .state import StudyPlanState, SubAgentEvaluation, StudyPlanEvaluation


class EvaluationNodes:
    """Container for all graph node functions."""
    
    def __init__(
        self,
        tool_registry,
        model_name: str,
        scheduling_prompt: ChatPromptTemplate,
        alignment_prompt: ChatPromptTemplate,
    ):
        """Initialize evaluation nodes."""
        self.tool_registry = tool_registry
        self.model_name = model_name
        self.scheduling_prompt = scheduling_prompt
        self.alignment_prompt = alignment_prompt
        self.llm = ChatGroq(model=model_name, temperature=0.0, max_retries=2)
    
    def scheduling_node(self, state: StudyPlanState) -> dict:
        """Evaluate scheduling: conflicts, exam spacing, time distribution."""
        agent = create_agent(
            model=self.llm,
            tools=self.tool_registry.get_scheduling_tools(),
            response_format=SubAgentEvaluation,
        )
        chain = self.scheduling_prompt | agent
        result = chain.invoke({"study_plan": state["study_plan"]})['structured_response']
        
        return {
            "scheduling_score": result.score,
            "scheduling_reasoning": result.reasoning,
        }
    
    def alignment_node(self, state: StudyPlanState) -> dict:
        """Evaluate alignment: major/minor fit, academic goals."""
        agent = create_agent(
            model=self.llm,
            tools=self.tool_registry.get_alignment_tools(),
            response_format=SubAgentEvaluation,
        )
        
        chain = self.alignment_prompt | agent
        result = chain.invoke({"study_plan": state["study_plan"]})['structured_response']
        
        return {
            "alignment_score": result.score,
            "alignment_reasoning": result.reasoning,
        }
    
    def workload_node(self, state: StudyPlanState) -> dict:
        """Evaluate workload using LLM with workload_score_tool."""
        
        class WorkloadEvaluation(BaseModel):
            """Workload evaluation result."""
            workload_score: int = Field(description="Workload score as an INTEGER (0-100)")
            num_courses: int = Field(description="Number of courses detected as an INTEGER")
            
            @field_validator('workload_score', 'num_courses', mode='before')
            @classmethod
            def coerce_to_int(cls, v):
                """Coerce string to integer."""
                if isinstance(v, str):
                    return int(v)
                return v
        
        workload_agent = create_agent(
            model=self.llm,
            tools=self.tool_registry.get_workload_tools(),
            response_format=WorkloadEvaluation,
        )
        
        workload_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a workload evaluation agent. 

Your task:
1. Analyze the study plan and count the number of courses
2. Use the workload_score_tool to calculate the workload score
3. Return the result with both the score and course count

CRITICAL: Return score as INTEGER, not string."""),
            ("human", "Study Plan:\n{study_plan}")
        ])
        
        chain = workload_prompt | workload_agent
        result = chain.invoke({"study_plan": state["study_plan"]})['structured_response']
        
        return {
            "workload_score": result.workload_score,
        }
    
    def synthesis_node(self, state: StudyPlanState) -> dict:
        """Calculate weighted score and generate final evaluation using LLM.
        
        The LLM uses weighted_score_tool to compute the weighted average,
        then generates a natural language recommendation.
        
        If human_decision exists, the reasoning is updated to reflect human intervention.
        """
        
        synthesis_agent = create_agent(
            model=self.llm,
            tools=self.tool_registry.get_synthesis_tools(),
            response_format=StudyPlanEvaluation,
        )
        
        # Check if this is a recalculation after human review
        human_decision = state.get("human_decision")
        is_post_hitl = human_decision is not None
        
        # Determine which scores to use (human override or original)
        if state.get("human_override_scores"):
            scores = state["human_override_scores"]
            score_source = "human-adjusted"
        else:
            scores = {
                "scheduling_score": state["scheduling_score"],
                "alignment_score": state["alignment_score"],
                "workload_score": state["workload_score"],
            }
            score_source = "agent-generated" if not is_post_hitl else "human-approved"
        
        # Build synthesis prompt based on whether this is post-HITL
        if is_post_hitl:
            # Post-HITL: Include human decision context
            synthesis_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a study plan synthesis agent. Your task:

    1. Use the weighted_score_tool to calculate the final weighted average from the three component scores
    2. Generate a comprehensive evaluation that EXPLICITLY MENTIONS the human review decision

    CRITICAL: The reasoning field MUST include:
    - A clear statement that human review was conducted
    - The human's decision (approved/rejected/edited)
    - How the human decision affected the final evaluation
    - If scores were edited, mention the original vs. adjusted scores
    - The rationale combining agent analysis and human judgment

    Color meanings:
    - GREEN (76-100): Plan approved, well-balanced
    - YELLOW (46-75): Plan needs review, possible issues
    - RED (0-45): Plan rejected, significant problems

    Return a StudyPlanEvaluation with all required fields."""),
                ("human", """Evaluate this study plan AFTER HUMAN REVIEW.

    Component Scores ({score_source}):
    - Scheduling Score: {scheduling_score}/100
    Reasoning: {scheduling_reasoning}

    - Alignment Score: {alignment_score}/100
    Reasoning: {alignment_reasoning}

    - Workload Score: {workload_score}/100

    HUMAN DECISION: {human_decision}
    {human_context}

    Use weighted_score_tool to calculate the final result.

    Your reasoning MUST explicitly state:
    1. That this evaluation includes human review
    2. What the human decided ({human_decision})
    3. How this affected the final recommendation
    4. The combined perspective of automated analysis and human judgment""")
            ])
            
            # Build human context string
            if human_decision == "edit":
                original_scores = {
                    "scheduling": state["scheduling_score"],
                    "alignment": state["alignment_score"],
                    "workload": state["workload_score"]
                }
                human_context = f"""
    Original Scores: Scheduling={original_scores['scheduling']}, Alignment={original_scores['alignment']}, Workload={original_scores['workload']}
    Adjusted Scores: Scheduling={scores['scheduling_score']}, Alignment={scores['alignment_score']}, Workload={scores['workload_score']}

    The human reviewer modified the scores based on their expert judgment."""
            elif human_decision == "approve":
                human_context = "The human reviewer approved the automated evaluation, confirming the assessment is accurate."
            elif human_decision == "reject":
                human_context = "The human reviewer rejected the study plan, overriding the automated assessment due to critical concerns."
            else:
                human_context = ""
            
            chain = synthesis_prompt | synthesis_agent
            result = chain.invoke({
                "score_source": score_source,
                "scheduling_score": scores["scheduling_score"],
                "scheduling_reasoning": state.get("scheduling_reasoning", "N/A"),
                "alignment_score": scores["alignment_score"],
                "alignment_reasoning": state.get("alignment_reasoning", "N/A"),
                "workload_score": scores["workload_score"],
                "human_decision": human_decision,
                "human_context": human_context,
            })
        
        else:
            # Initial synthesis (no human review yet)
            synthesis_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a study plan synthesis agent. Your task:

    1. Use the weighted_score_tool to calculate the final weighted average from the three component scores
    2. Based on the tool's output and reasoning from sub-agents, generate:
    - overall_recommendation: Clear 2-3 sentence recommendation for the student
    - reasoning: Detailed explanation incorporating all evaluations

    Color meanings:
    - GREEN (76-100): Plan approved, well-balanced
    - YELLOW (46-75): Plan needs review, possible issues
    - RED (0-45): Plan rejected, significant problems

    Return a StudyPlanEvaluation with all required fields."""),
                ("human", """Evaluate this study plan using the scores below.

    Component Scores ({score_source}):
    - Scheduling Score: {scheduling_score}/100
    Reasoning: {scheduling_reasoning}

    - Alignment Score: {alignment_score}/100
    Reasoning: {alignment_reasoning}

    - Workload Score: {workload_score}/100

    Use weighted_score_tool to calculate the final result, then provide your synthesis.""")
            ])
            
            chain = synthesis_prompt | synthesis_agent
            result = chain.invoke({
                "score_source": score_source,
                "scheduling_score": scores["scheduling_score"],
                "scheduling_reasoning": state.get("scheduling_reasoning", "N/A"),
                "alignment_score": scores["alignment_score"],
                "alignment_reasoning": state.get("alignment_reasoning", "N/A"),
                "workload_score": scores["workload_score"],
            })
        
        return {
            "weighted_avg": result["structured_response"].weighted_avg,
            "color": result["structured_response"].color,
            "final_evaluation": result,
        }

    
    def human_review_node(self, state: StudyPlanState):
        """Human-in-the-loop review node using interrupt().
        
        This node pauses execution with interrupt() and waits for human input.
        After receiving input via Command(resume=...), it routes accordingly.
        """
        
        print("\n" + "="*60)
        print("🧑 HUMAN_REVIEW_NODE: Preparing interrupt")
        print("="*60)
        
        # Prepare the interrupt payload with evaluation details
        interrupt_payload = {
            "message": "Human review required for YELLOW case evaluation",
            "evaluation_summary": {
                "weighted_avg": state["weighted_avg"],
                "color": state["color"],
                "scheduling_score": state["scheduling_score"],
                "scheduling_reasoning": state.get("scheduling_reasoning", "N/A"),
                "alignment_score": state["alignment_score"],
                "alignment_reasoning": state.get("alignment_reasoning", "N/A"),
                "workload_score": state["workload_score"],
            },
            "instructions": {
                "action": "Choose: 'approve', 'edit', or 'reject'",
                "data": "If action='edit', provide new scores as dict"
            }
        }
        
        # interrupt() pauses execution here
        human_review: dict = interrupt(interrupt_payload)
        
        print("\n" + "="*60)
        print("🧑 HUMAN_REVIEW_NODE: Resumed with human input")
        print("="*60)
        
        # Process human decision
        action = human_review.get("action", "approve")
        data = human_review.get("data")
        
        print(f"✓ Received action: {action}")
        if data:
            print(f"✓ Received data: {data}")
        
        if action == "approve":
            # Approved - recalculate with human_decision flag to update reasoning
            print("✓ Human approved - routing to synthesis to update reasoning")
            return Command(
                goto="synthesis",
                update={"human_decision": "approve"}
            )
        
        elif action == "edit" and data:
            # Human provided new scores - update state and recalculate in synthesis
            print("✏️  Human edited scores - routing to synthesis for recalculation")
            return Command(
                goto="synthesis",
                update={
                    "human_override_scores": data,
                    "human_decision": "edit"
                }
            )
        
        elif action == "reject":
            # Rejected - route to synthesis to generate rejection with human context
            print("❌ Human rejected - routing to synthesis to update with rejection reasoning")
            return Command(
                goto="synthesis",
                update={
                    "human_decision": "reject",
                    "color": "red"  # Force red color
                }
            )
        
        else:
            # Default fallback - approve
            print("⚠️  Unknown action, defaulting to approve")
            return Command(
                goto="synthesis",
                update={"human_decision": "approve"}
            )
