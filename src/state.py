"""State schema for the study plan evaluation graph."""

from typing import TypedDict, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class SubAgentEvaluation(BaseModel):
    """Evaluation from a single sub-agent (scheduling or alignment)."""
    score: int | str = Field(description="Score out of 100 from this agent")
    reasoning: str = Field(description="Brief reasoning for the score")
    
    @field_validator("score", mode="before")
    def coerce_score(cls, v):
        return int(v)


class StudyPlanState(TypedDict):
    """Central state for the study plan evaluation workflow."""
    
    # Input
    study_plan: str
    
    # Intermediate evaluations (scores 0-100)
    scheduling_score: Optional[int]
    scheduling_reasoning: Optional[str]
    alignment_score: Optional[int]
    alignment_reasoning: Optional[str]
    workload_score: Optional[int]
    
    # Synthesis results
    weighted_avg: Optional[float]
    color: Optional[Literal["red", "yellow", "green"]]
    
    # Final output
    final_evaluation: Optional["StudyPlanEvaluation"]
    
    # HITL control
    human_decision: Optional[str]  # "approve", "reject", or "edit"
    human_override_scores: Optional[dict]  # For manual score adjustment


class StudyPlanEvaluation(BaseModel):
    """Final structured evaluation result."""
    weighted_avg: float = Field(description="Weighted average score")
    color: Literal["red", "yellow", "green"] = Field(description="Traffic light status")
    overall_recommendation: str = Field(description="Final recommendation text")
    reasoning: str = Field(description="Detailed reasoning behind evaluation")
    scores: dict = Field(description="Individual component scores")
