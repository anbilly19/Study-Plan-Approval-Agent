"""State schema for the study plan evaluation graph."""

from typing import Literal, Optional, TypedDict

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

    study_plan: str
    scheduling_score: Optional[int]
    scheduling_reasoning: Optional[str]
    alignment_score: Optional[int]
    alignment_reasoning: Optional[str]
    workload_score: Optional[int]
    weighted_avg: Optional[float]
    color: Optional[Literal["red", "yellow", "green"]]
    final_evaluation: Optional["StudyPlanEvaluation"]
    human_decision: Optional[str]  # "approve", "reject", or "edit"
    human_override_scores: Optional[dict]

    human_decision_source: Optional[Literal["human", "memory"]]
    memory_used: Optional[bool]
    memory_match_score: Optional[float]
    memory_match_id: Optional[str]


class StudyPlanEvaluation(BaseModel):
    """Final structured evaluation result."""

    weighted_avg: float = Field(description="Weighted average score")
    color: Literal["red", "yellow", "green"] = Field(description="Traffic light status")
    overall_recommendation: str = Field(description="Final recommendation text")
    reasoning: str = Field(description="Detailed reasoning behind evaluation")
    scores: dict = Field(description="Individual component scores")
