from pydantic import BaseModel, Field



class ScoreEvaluation(BaseModel):
    """Full evaluation of a student's semester study plan by multiple agents."""

    scheduling_score: int = Field(description="Score out of 100 given by the Scheduling Agent.")
    alignment_score: int = Field(description="Score out of 100 given by the Alignment Agent.")
    workload_score: int = Field(description="Score out of 100 given by the Workload Agent.")

class SubAgentEvaluation(BaseModel):
    """Evaluation of study plan alignment with student's goals."""

    score: int = Field(description="Score out of 100 given by the Sub Agent.")
    reasoning: str = Field(description="Brief reasoning from Sub Agent.")

class StudyPlanEvaluation(BaseModel):
    """Final evaluation of a student's semester study plan."""
    weighted_avg: float = Field(description="Weighted average score combining all evaluations.")
    color: str = Field(description="Color code (green, yellow, red) representing overall evaluation.")
    overall_recommendation: str = Field(description="Overall recommendation for the study plan.")