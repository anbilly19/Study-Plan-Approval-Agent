"""Node functions for the study plan evaluation graph."""

import hashlib
import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field, field_validator

from .state import StudyPlanEvaluation, StudyPlanState, SubAgentEvaluation


class EvaluationNodes:
    """Container for all graph node functions."""

    def __init__(
        self,
        tool_registry,
        model_name: str,
        scheduling_prompt: ChatPromptTemplate,
        alignment_prompt: ChatPromptTemplate,
    ):
        self.tool_registry = tool_registry
        self.model_name = model_name
        self.scheduling_prompt = scheduling_prompt
        self.alignment_prompt = alignment_prompt
        self.llm = ChatGroq(model=model_name, temperature=0.0, max_retries=2)

        base_dir = os.getenv("LANGGRAPH_MEMORY_DIR") or os.path.dirname(__file__)
        self.memory_path = os.getenv("LANGGRAPH_MEMORY_PATH") or os.path.join(base_dir, "hitl_memory.jsonl")

    def _normalize_text(self, text: str) -> str:
        t = text.lower()
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _tokenize(self, text: str) -> List[str]:
        t = self._normalize_text(text)
        t = re.sub(r"[^a-z0-9\s\-_/]", " ", t)
        raw = t.split()
        stop = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "of",
            "in",
            "on",
            "for",
            "with",
            "is",
            "are",
            "be",
            "this",
            "that",
            "it",
            "as",
            "at",
            "by",
            "from",
            "was",
            "were",
            "will",
            "would",
            "should",
            "could",
            "can",
        }
        toks = [x for x in raw if len(x) >= 3 and x not in stop]
        return toks

    def _case_repr(self, study_plan: str) -> Dict[str, Any]:
        norm = self._normalize_text(study_plan)
        h = hashlib.sha1(norm.encode("utf-8")).hexdigest()  # nosec B324
        toks = self._tokenize(study_plan)
        counts = Counter(toks)
        top_tokens = [t for t, _ in counts.most_common(40)]
        return {"hash": h, "tokens": top_tokens, "norm": norm}

    def _load_memory_entries(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.memory_path):
            return []

        entries: List[Dict[str, Any]] = []
        try:
            with open(self.memory_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []

        return entries[-2000:]

    def _similarity(self, a_norm: str, a_tokens: List[str], b_norm: str, b_tokens: List[str]) -> float:
        a_set = set(a_tokens)
        b_set = set(b_tokens)
        jacc = (len(a_set & b_set) / len(a_set | b_set)) if (a_set or b_set) else 0.0
        seq = SequenceMatcher(None, a_norm, b_norm).ratio() if (a_norm and b_norm) else 0.0
        return 0.7 * jacc + 0.3 * seq

    def _find_best_match(
        self, case: Dict[str, Any], entries: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        best = None
        best_score = 0.0

        for e in entries:
            e_case = e.get("case") or {}
            if not isinstance(e_case, dict):
                continue

            if e_case.get("hash") and e_case.get("hash") == case["hash"]:
                return e, 1.0

            score = self._similarity(
                case["norm"],
                case["tokens"],
                self._normalize_text(e_case.get("norm", "")),
                e_case.get("tokens") or [],
            )
            if score > best_score:
                best = e
                best_score = score

        return best, best_score

    def _append_memory_entry(
        self,
        study_plan: str,
        action: str,
        override_scores: Optional[dict],
    ) -> Optional[str]:
        os.makedirs(os.path.dirname(self.memory_path) or ".", exist_ok=True)
        entry_id = str(uuid.uuid4())
        case = self._case_repr(study_plan)

        entry = {
            "id": entry_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "case": {"hash": case["hash"], "tokens": case["tokens"], "norm": case["norm"]},
            "decision": {"action": action, "override_scores": override_scores},
        }

        try:
            with open(self.memory_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            return None

        return entry_id

    def memory_node(self, state: StudyPlanState) -> dict:
        if state.get("human_decision"):
            return {}

        study_plan = state["study_plan"]
        case = self._case_repr(study_plan)
        entries = self._load_memory_entries()
        match, score = self._find_best_match(case, entries)

        if not match:
            return {
                "memory_used": False,
                "memory_match_score": None,
                "memory_match_id": None,
            }

        if score < 0.85:
            return {
                "memory_used": False,
                "memory_match_score": score,
                "memory_match_id": match.get("id"),
            }

        decision = match.get("decision") or {}
        action = (decision.get("action") or "").lower().strip()
        override = decision.get("override_scores")

        update: Dict[str, Any] = {
            "memory_used": True,
            "memory_match_score": score,
            "memory_match_id": match.get("id"),
            "human_decision": action,
            "human_decision_source": "memory",
        }
        if isinstance(override, dict) and override:
            update["human_override_scores"] = override
        if action == "reject":
            update["color"] = "red"
        return update

    def scheduling_node(self, state: StudyPlanState) -> dict:
        agent = create_agent(
            model=self.llm,
            tools=self.tool_registry.get_scheduling_tools(),
            response_format=SubAgentEvaluation,
        )
        chain = self.scheduling_prompt | agent
        result = chain.invoke({"study_plan": state["study_plan"]})["structured_response"]
        return {
            "scheduling_score": result.score,
            "scheduling_reasoning": result.reasoning,
        }

    def alignment_node(self, state: StudyPlanState) -> dict:
        agent = create_agent(
            model=self.llm,
            tools=self.tool_registry.get_alignment_tools(),
            response_format=SubAgentEvaluation,
        )
        chain = self.alignment_prompt | agent
        result = chain.invoke({"study_plan": state["study_plan"]})["structured_response"]
        return {
            "alignment_score": result.score,
            "alignment_reasoning": result.reasoning,
        }

    def workload_node(self, state: StudyPlanState) -> dict:
        class WorkloadEvaluation(BaseModel):
            workload_score: int = Field(description="Workload score as an INTEGER (0-100)")
            num_courses: int = Field(description="Number of courses detected as an INTEGER")

            @field_validator("workload_score", "num_courses", mode="before")
            @classmethod
            def coerce_to_int(cls, v):
                if isinstance(v, str):
                    return int(v)
                return v

        workload_agent = create_agent(
            model=self.llm,
            tools=self.tool_registry.get_workload_tools(),
            response_format=WorkloadEvaluation,
        )
        workload_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a workload evaluation agent.

Your task:
1. Analyze the study plan and count the number of courses
2. Use the workload_score_tool to calculate the workload score
3. Return the result with both the score and course count

CRITICAL: Return score as INTEGER, not string.""",
                ),
                ("human", "Study Plan:\n{study_plan}"),
            ]
        )
        chain = workload_prompt | workload_agent
        result = chain.invoke({"study_plan": state["study_plan"]})["structured_response"]
        return {
            "workload_score": result.workload_score,
        }

    def synthesis_node(self, state: StudyPlanState) -> dict:
        synthesis_agent = create_agent(
            model=self.llm,
            tools=self.tool_registry.get_synthesis_tools(),
            response_format=StudyPlanEvaluation,
        )
        human_decision = state.get("human_decision")
        decision_source = state.get("human_decision_source")
        memory_used = bool(state.get("memory_used"))
        memory_match_score = state.get("memory_match_score")

        is_post_decision = human_decision is not None

        if state.get("human_override_scores"):
            scores = state["human_override_scores"]
            score_source = "human-adjusted" if decision_source == "human" else "memory-adjusted"
        else:
            scores = {
                "scheduling_score": state["scheduling_score"],
                "alignment_score": state["alignment_score"],
                "workload_score": state["workload_score"],
            }
            if not is_post_decision:
                score_source = "agent-generated"
            else:
                score_source = "memory-approved" if decision_source == "memory" else "human-approved"

        if is_post_decision:
            if decision_source == "memory":
                synthesis_prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            """You are a study plan synthesis agent. Your task:
1. Use the weighted_score_tool to calculate the final weighted average from the three component scores
2. Generate a comprehensive evaluation that EXPLICITLY MENTIONS that a prior similar-case
decision was retrievedfrom memory (not a new live human review)

CRITICAL: The reasoning field MUST include:
- A clear statement that memory retrieval was used to avoid a new human review
- The prior human decision that was retrieved (approved/rejected/edited)
- The memory match strength (if provided) and why it was considered similar
- If scores were edited, mention the original vs. adjusted scores
- The rationale combining automated analysis with the retrieved human decision

Color meanings:
- GREEN (76-100): Plan approved, well-balanced
- YELLOW (46-75): Plan needs review, possible issues
- RED (0-45): Plan rejected, significant problems

Return a StudyPlanEvaluation with all required fields.""",
                        ),
                        (
                            "human",
                            """Evaluate this study plan using a prior similar-case decision retrieved from memory.

Component Scores ({score_source}):
- Scheduling Score: {scheduling_score}/100
Reasoning: {scheduling_reasoning}
- Alignment Score: {alignment_score}/100
Reasoning: {alignment_reasoning}
- Workload Score: {workload_score}/100

RETRIEVED DECISION: {human_decision}
MEMORY MATCH SCORE: {memory_match_score}

{human_context}

Use weighted_score_tool to calculate the final result.

Your reasoning MUST explicitly state:
1. That this evaluation used memory retrieval instead of a new human review
2. What decision was retrieved ({human_decision})
3. How this affected the final recommendation
4. The combined perspective of automated analysis and the retrieved human decision""",
                        ),
                    ]
                )
            else:
                synthesis_prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            """You are a study plan synthesis agent. Your task:
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

    Return a StudyPlanEvaluation with all required fields.""",
                        ),
                        (
                            "human",
                            """Evaluate this study plan AFTER HUMAN REVIEW.

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
    4. The combined perspective of automated analysis and human judgment""",
                        ),
                    ]
                )
            if human_decision == "edit":
                original_scores = {
                    "scheduling": state["scheduling_score"],
                    "alignment": state["alignment_score"],
                    "workload": state["workload_score"],
                }
                actor = "The human reviewer" if decision_source == "human" else "A prior human review"

                if scores is None:
                    raise ValueError("original_scores must not be None")

                human_context = f"""Original Scores: Scheduling={original_scores['scheduling']},"
                f"Alignment={original_scores['alignment']},"
                f" Workload={original_scores['workload']} Adjusted Scores: Scheduling={scores['scheduling_score']}, "
                f"Alignment={scores['alignment_score']}, Workload={scores['workload_score']}"
                f"{actor} modified the scores based on expert judgment."""
            elif human_decision == "approve":
                human_context = (
                    "The human reviewer approved the automated evaluation, confirming the assessment is accurate."
                    if decision_source == "human"
                    else (
                        "A prior human review approved a highly similar case; "
                        "that approval was reused to avoid a new review."
                    )
                )
            elif human_decision == "reject":
                human_context = (
                    "The human reviewer rejected the study plan, overriding the automated"
                    "assessment due to critical concerns."
                    if decision_source == "human"
                    else (
                        "A prior human review rejected a highly similar case; "
                        "that rejection was reused to avoid a new review."
                    )
                )
            else:

                if state is None:
                    raise ValueError("state must not be None")

                if scores is None:
                    raise ValueError("scores must not be None")

                human_context = ""
            chain = synthesis_prompt | synthesis_agent
            result = chain.invoke(
                {
                    "score_source": score_source,
                    "scheduling_score": (scores or {}).get("scheduling_score", 0),
                    "scheduling_reasoning": (state or {}).get("scheduling_reasoning", "N/A"),
                    "alignment_score": (scores or {}).get("alignment_score", 0),
                    "alignment_reasoning": (state or {}).get("alignment_reasoning", "N/A"),
                    "workload_score": (scores or {}).get("workload_score", 0),
                    "human_decision": human_decision,
                    "human_context": human_context,
                    "memory_match_score": memory_match_score if memory_used else None,
                }
            )
        else:
            synthesis_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a study plan synthesis agent. Your task:
    1. Use the weighted_score_tool to calculate the final weighted average from the three component scores
    2. Based on the tool's output and reasoning from sub-agents, generate:
    - overall_recommendation: Clear 2-3 sentence recommendation for the student
    - reasoning: Detailed explanation incorporating all evaluations

    Color meanings:
    - GREEN (76-100): Plan approved, well-balanced
    - YELLOW (46-75): Plan needs review, possible issues
    - RED (0-45): Plan rejected, significant problems

    Return a StudyPlanEvaluation with all required fields.""",
                    ),
                    (
                        "human",
                        """Evaluate this study plan using the scores below.

    Component Scores ({score_source}):
    - Scheduling Score: {scheduling_score}/100
    Reasoning: {scheduling_reasoning}
    - Alignment Score: {alignment_score}/100
    Reasoning: {alignment_reasoning}
    - Workload Score: {workload_score}/100

    Use weighted_score_tool to calculate the final result, then provide your synthesis.""",
                    ),
                ]
            )
            chain = synthesis_prompt | synthesis_agent
            result = chain.invoke(
                {
                    "score_source": score_source,
                    "scheduling_score": (scores or {}).get("scheduling_score", 0),
                    "scheduling_reasoning": (state or {}).get("scheduling_reasoning", "N/A"),
                    "alignment_score": (scores or {}).get("alignment_score", 0),
                    "alignment_reasoning": (state or {}).get("alignment_reasoning", "N/A"),
                    "workload_score": (scores or {}).get("workload_score", 0),
                }
            )
        structured = result["structured_response"]
        if human_decision == "reject":
            structured.color = "red"
        return {
            "weighted_avg": structured.weighted_avg,
            "color": structured.color,
            "final_evaluation": result,
        }

    def human_review_node(self, state: StudyPlanState):
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
                "data": "If action='edit', provide new scores as dict",
            },
        }
        human_review: dict = interrupt(interrupt_payload)
        action = (human_review.get("action", "approve") or "approve").lower().strip()
        data = human_review.get("data")

        override_scores = data if (action == "edit" and isinstance(data, dict)) else None
        stored_id = self._append_memory_entry(
            study_plan=state["study_plan"],
            action=action,
            override_scores=override_scores,
        )

        base_update = {
            "human_decision_source": "human",
            "memory_used": False,
            "memory_match_score": None,
            "memory_match_id": stored_id,
        }

        if action == "approve":
            return Command(
                goto="synthesis",
                update={**base_update, "human_decision": "approve"},
            )

        if action == "edit" and override_scores:
            return Command(
                goto="synthesis",
                update={
                    **base_update,
                    "human_override_scores": override_scores,
                    "human_decision": "edit",
                },
            )

        if action == "reject":
            return Command(
                goto="synthesis",
                update={**base_update, "human_decision": "reject", "color": "red"},
            )

        return Command(
            goto="synthesis",
            update={**base_update, "human_decision": "approve"},
        )
