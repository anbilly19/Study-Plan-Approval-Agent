"""These are Pydantic models that define the structured outputs you expect from agents."""

from pydantic import BaseModel, Field


class ScoreEvaluation(BaseModel):
    """
    Full evaluation of a student's semester study plan by multiple agents.

    Returned by the main agent before synthesis.
    This model aggregates the raw numeric scores produced independently
    by different evaluation agents: Scheduling, Alignment, and Workload.
    """

    # Score from agent checking course timing, conflicts, and distribution.
    scheduling_score: int = Field(description="Score out of 100 given by the Scheduling Agent.")

    # Score from agent evaluating how well the plan matches the student's goals.
    alignment_score: int = Field(description="Score out of 100 given by the Alignment Agent.")

    # Score from agent analyzing total workload balance.
    workload_score: int = Field(description="Score out of 100 given by the Workload Agent.")


class SubAgentEvaluation(BaseModel):
    """
    Evaluation of the study plan from a single sub-agent’s perspective.

    Useful for detailed inspection of individual agent reasoning. (scheduling and alignment).
    """

    # Numerical evaluation (0–100) from this specific agent.
    score: int = Field(description="Score out of 100 given by the Sub Agent.")

    # Short explanation describing why the agent gave this score.
    reasoning: str = Field(description="Brief reasoning from Sub Agent.")


class StudyPlanEvaluation(BaseModel):
    """
    Final evaluation of a student's semester study plan.

    This model represents the synthesized result after considering all
    agent evaluations and applying weighting/rules to generate the
    final recommendation, color-coded status and a detailed reasoning.
    """

    # Combined weighted average based on all agent scores.
    weighted_avg: float = Field(description="Weighted average score combining all evaluations.")

    # Traffic-light style indicator for overall plan quality.
    # Expected values: 'green', 'yellow', 'red'.
    color: str = Field(description="Color code (green, yellow, red) representing overall evaluation.")

    # Natural-language recommendation summarizing the evaluation.
    overall_recommendation: str = Field(description="Overall recommendation for the study plan.")

    reasoning: str = Field(description="Detailed reasoning behind the final evaluation.")
