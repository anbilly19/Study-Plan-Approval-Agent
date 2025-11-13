# src/api/app.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# --- use your modularized main.py ---
from main import init_eval_agents, evaluate_study_plan, LLAMA_70B
# --- scoring tool from tools.py is a LangChain StructuredTool (must call .invoke) ---
from tools import weighted_score_tool_with_interrupt

# ------------------------------------
# App setup
# ------------------------------------
load_dotenv()
if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("Set GROQ_API_KEY before starting the API")

app = FastAPI(title="Study Plan Evaluator API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# Warm up agents once
@app.on_event("startup")
def _warm():
    init_eval_agents(model_name=LLAMA_70B)


# ------------------------------------
# Models
# ------------------------------------
class EvaluateRequest(BaseModel):
    study_plan: str


class Scores(BaseModel):
    alignment_score: int = Field(ge=0, le=100)
    scheduling_score: int = Field(ge=0, le=100)
    workload_score: int = Field(ge=0, le=100)


class EvaluateResponse(BaseModel):
    token: str
    scores: Scores
    color: str
    reasons: Any | None = None
    raw: Any | None = None


class HitlInitRequest(BaseModel):
    study_plan: str


class HitlDecisionRequest(BaseModel):
    token: str
    decision: str = Field(..., description="approve | edit | reject | auto")
    new_alignment_score: Optional[int] = Field(default=None, ge=0, le=100)
    new_scheduling_score: Optional[int] = Field(default=None, ge=0, le=100)
    new_workload_score: Optional[int] = Field(default=None, ge=0, le=100)


# Store partial HITL state per token (scores, reasons, raw)
app.state.hitl_cache: Dict[str, Dict[str, Any]] = {}


# ------------------------------------
# Helpers
# ------------------------------------
def _as_dict(x: Any) -> Dict[str, Any]:
    if hasattr(x, "model_dump"):
        return x.model_dump()
    return x if isinstance(x, dict) else {"value": x}


def _extract_scores_color_reasons(result: Any) -> Tuple[Dict[str, int], Optional[str], Any]:
    blob = _as_dict(result)
    if "structured_response" in blob:
        blob = _as_dict(blob["structured_response"])

    # where scores might live
    candidates = [blob]
    if isinstance(blob.get("scores"), dict):
        candidates.insert(0, blob["scores"])

    scores: Dict[str, int] = {}
    for c in candidates:
        if not isinstance(c, dict):
            continue
        for k in ("alignment_score", "scheduling_score", "workload_score"):
            if k in c:
                scores[k] = int(c[k])
        if len(scores) == 3:
            break

    if len(scores) != 3:
        raise ValueError("Could not extract alignment/scheduling/workload scores from agent output.")

    color = None
    for k in ("color", "verdict", "status", "traffic_light"):
        if k in blob:
            color = str(blob[k]).lower()
            break

    reasons = None
    for k in ("reasons", "reason", "notes", "explanation", "why", "rationale"):
        if k in blob:
            reasons = blob[k]
            break

    return scores, color, reasons


def _call_score_tool(
    decision: str,
    scores: Dict[str, int],
    new_scores: Optional[Dict[str, Optional[int]]] = None,
) -> Dict[str, Any]:
    """
    Correctly call the LangChain StructuredTool via .invoke(payload).
    """
    payload: Dict[str, Any] = {
        "scheduling_score": scores["scheduling_score"],
        "alignment_score":  scores["alignment_score"],
        "workload_score":   scores["workload_score"],
        "decision": decision,
    }
    if new_scores:
        if new_scores.get("new_scheduling_score") is not None:
            payload["new_scheduling_score"] = new_scores["new_scheduling_score"]
        if new_scores.get("new_alignment_score") is not None:
            payload["new_alignment_score"] = new_scores["new_alignment_score"]
        if new_scores.get("new_workload_score") is not None:
            payload["new_workload_score"] = new_scores["new_workload_score"]

    out = weighted_score_tool_with_interrupt.invoke(payload)
    return _as_dict(out)


# ------------------------------------
# Endpoints
# ------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest):
    """
    Non-HITL evaluation (same logic as your main.py non-interactive path).
    """
    sp = req.study_plan.strip()
    if not sp:
        raise HTTPException(status_code=400, detail="study_plan is empty")

    try:
        result = evaluate_study_plan(study_plan=sp, hitl=False, model_name=LLAMA_70B)
        scores, color, reasons = _extract_scores_color_reasons(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"agent_failed: {e}")

    # compute traffic-light if missing
    if not color:
        t = _call_score_tool("auto", scores)
        color = str(t.get("color", "yellow")).lower()

    token = str(uuid4())
    return EvaluateResponse(
        token=token,
        scores=Scores(**scores),
        color=color,
        reasons=reasons,
        raw=result,
    )


@app.post("/evaluate/hitl-init", response_model=EvaluateResponse)
def evaluate_hitl_init(req: HitlInitRequest):
    """
    Run the HITL agent once to get initial scores/reasons (no interactive pause).
    The human decision is posted to /evaluate/hitl-decision with the returned token.
    """
    sp = req.study_plan.strip()
    if not sp:
        raise HTTPException(status_code=400, detail="study_plan is empty")

    try:
        result = evaluate_study_plan(study_plan=sp, hitl=False, model_name=LLAMA_70B)
        scores, color, reasons = _extract_scores_color_reasons(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"agent_failed: {e}")

    token = str(uuid4())
    app.state.hitl_cache[token] = {"scores": scores, "reasons": reasons, "raw": result}

    if not color:
        t = _call_score_tool("auto", scores)
        color = str(t.get("color", "yellow")).lower()

    return EvaluateResponse(
        token=token,
        scores=Scores(**scores),
        color=color,
        reasons=reasons,
        raw=result,
    )


@app.post("/evaluate/hitl-decision")
def evaluate_hitl_decision(req: HitlDecisionRequest):
    """
    Apply a human decision (approve/edit/reject/auto) to the cached HITL result.
    """
    entry = app.state.hitl_cache.pop(req.token, None)
    if not entry:
        raise HTTPException(status_code=404, detail="Unknown or expired token")

    base = entry["scores"]
    reasons = entry.get("reasons")
    
    out = _call_score_tool(
        req.decision,
        base,
        {
            "new_alignment_score":  req.new_alignment_score,
            "new_scheduling_score": req.new_scheduling_score,
            "new_workload_score":   req.new_workload_score,
        },
    )

    if req.decision.lower() == "reject":
        # Prefer the cached LLM reason strings if present
        alignment_reasoning = None
        scheduling_reasoning = None
        overall_recommendation = None
        if isinstance(reasons, dict):
            alignment_reasoning = reasons.get("alignment_reasoning") or reasons.get("alignment_reasoning".replace("_", " "))
            scheduling_reasoning = reasons.get("scheduling_reasoning") or reasons.get("scheduling_reasoning".replace("_", " "))
            overall_recommendation = reasons.get("overall_recommendation") or reasons.get("overall_recommendation".replace("_", " "))

        # Use the scores the tool says were used (falls back to cached base)
        eff = out.get("scores", base)

        return {
            "alignment_reasoning": alignment_reasoning,
            "alignment_score":     eff.get("alignment_score"),
            "overall_recommendation": overall_recommendation,
            "scheduling_reasoning":   scheduling_reasoning,
            "scheduling_score":       eff.get("scheduling_score"),
            "weighted_color":         "red",  # force red on reject, like CLI
            "workload_score":         eff.get("workload_score"),
        }

    # For approve/edit/auto, return the regular tool output
    return out
    return out
