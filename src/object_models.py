from pydantic import BaseModel, Field


class StudyPlanEvaluation(BaseModel):
    """Full evaluation of a student's semester study plan by multiple agents."""

    scheduling_score: int = Field(description="Score out of 100 given by the Scheduling Agent.")
    alignment_score: int = Field(description="Score out of 100 given by the Alignment Agent.")
    weighted_color: str = Field(description="Final approval color code (red/yellow/green) given by main agent.")
    scheduling_reasoning: str = Field(description="Brief reasoning from Scheduling Agent.")
    alignment_reasoning: str = Field(description="Brief reasoning from Alignment Agent.")
    overall_recommendation: str = Field(description="Joint summary or recommendation by main agent (optional).")
    workload_score: int = Field(description="Score out of 100 given by the Workload Agent.")
