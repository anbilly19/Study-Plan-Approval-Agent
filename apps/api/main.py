import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agents.main_agent import create_interrupt_main_agent
from src.db.queries import fetch_cases, fetch_courses, save_approval_to_db, update_case_status
from src.env_setup import setup_langsmith_env
from src.hitl.eval_interrupt_api import hitl_resume, hitl_start
from src.main import LLAMA_70B, init_eval_agents
from src.prompts.prompt import interrupt_agent_prompt, synth_prompt_interrupt

# HITL-related imports


app = FastAPI()

# Allow all CORS origins (frontend development convenience)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request models for non-HITL endpoints
class StatusUpdate(BaseModel):
    """Payload for updating case status in admin UI."""

    status: str  # "Approved" or "Rejected"
    notes: str | None = None


# Request models for HITL API endpoints
class HitlStartRequest(BaseModel):
    """
    Payload for starting HITL evaluation.

    - study_plan: Free-text study plan from user or example.
    - model_name: Optional override for LLM model.
    - thread_id: Optional; used only if resuming an abandoned thread.
    """

    study_plan: str
    model_name: str | None = None
    thread_id: str | None = None


class HitlDecision(BaseModel):
    """
    Payload for submitting a human decision to resume an interrupted HITL chain.

    decision: "approve", "reject", "edit"
    edited_scores: Required only for "edit"
    """

    thread_id: str
    decision: str
    edited_scores: dict | None = None
    message: str | None = None


# Globals for HITL agent initialization

_interrupt_chain = None  # The main interrupt-capable chain (schedule/alignment/workload)
_synth_agent = None  # The synthesizer agent used after HITL decisions
_langsmith_setup_done = False
_default_model = LLAMA_70B


def _ensure_hitl_initialized(model_name: str | None = None):
    """
    Lazy initialization strategy for HITL agents.

    - Ensures LangSmith env vars are set once.
    - Ensures EvalAgents + interrupt-capable chain are built once.
    - Stores agents globally so FastAPI doesn't reconstruct them on every request.

    Returns:
        (interrupt_chain, synth_agent)
    """
    global _interrupt_chain, _synth_agent, _langsmith_setup_done

    # Use default model unless overridden explicitly
    if model_name is None:
        model_name = _default_model

    # Initialize tracing/logging environment if not done already
    if not _langsmith_setup_done:
        setup_langsmith_env()
        _langsmith_setup_done = True

    # Build agents only once
    if _interrupt_chain is None or _synth_agent is None:
        eval_agents = init_eval_agents(model_name=model_name)

        # create_interrupt_main_agent returns:
        #   - interrupt-capable chain (with scheduling, alignment, workload tools)
        #   - synthesizer agent (with HITL middleware)
        _interrupt_chain, _synth_agent = create_interrupt_main_agent(
            eval_agents=eval_agents,
            model_name=model_name,
            interrupt_agent_prompt=interrupt_agent_prompt,
            synth_prompt=synth_prompt_interrupt,
        )

    return _interrupt_chain, _synth_agent


# Health & utility endpoints


@app.get("/health")
def health_check():
    """Endpoint used for basic health check for deployment monitoring."""
    return {"status": "ok"}


# Approval & Admin endpoints


@app.post("/approval")
async def approval_endpoint(request: Request):
    """
    Endpoint used to store course approval results (unrelated to HITL).

    Accepts a generic JSON payload with course selections and inserts into DB.
    """
    try:
        data = await request.json()
        print("Approval payload:")
        print(json.dumps(data, indent=4))

        inserted_rows = save_approval_to_db(data)
        print(inserted_rows, "rows inserted/updated in the database")

        return {"message": "Approval data received", "received_items": len(data.get("courses", []))}
    except Exception as e:
        print("Error while reading JSON:", e)
        return {"error": str(e)}


@app.get("/courses")
def get_courses():
    """Endpoint used to return list of courses (used by frontend drop-downs/forms)."""
    print("Courses endpoint called")
    courses_data = fetch_courses()
    return {"courses": courses_data}


@app.get("/admin/cases")
def get_cases():
    """Endpoint used to return all pending admin cases requiring evaluation."""
    print("Cases endpoint called")
    return fetch_cases()


@app.patch("/admin/cases/{case_id}/status")
async def update_case_status_endpoint(case_id: str, payload: StatusUpdate):
    """Endpoint used to allow admin to update case approval status in the database."""
    try:
        # Normalize text to consistent format
        new_status = payload.status.strip().capitalize()
        notes = payload.notes

        updated_rows = update_case_status(case_id, new_status, notes)

        if updated_rows == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No pending rows found for case_id '{case_id}'",
            )

        return {
            "message": "Case status updated successfully",
            "case_id": case_id,
            "new_status": new_status,
            "updated_rows": updated_rows,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        print("Error while updating case status:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# HITL (Human-in-the-Loop) API


@app.post("/admin/agent/evaluate/hitl/start")
async def start_hitl_evaluation(payload: HitlStartRequest):
    """
    Start the interrupt-capable evaluation chain.

    This endpoint:
      - Builds/initializes the HITL evaluation agents (if not already loaded)
      - Runs the main interrupt-capable evaluation chain
      - Returns one of:
            A) status="complete" → No human review needed (green/red)
            B) status="interrupt" → Human review required (yellow case)
    """
    try:
        print("HITL start payload:")
        print(json.dumps(payload.model_dump(), indent=4))

        if not payload.study_plan:
            raise HTTPException(status_code=400, detail="Field 'study_plan' is required.")

        # Build/reuse agents
        interrupt_chain, _ = _ensure_hitl_initialized(model_name=payload.model_name)

        # Invoke chain (using eval_interrupt_api logic)
        response = hitl_start(
            main_agent=interrupt_chain,
            study_plan=payload.study_plan,
            thread_id=payload.thread_id,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        print("Error in /admin/agent/evaluate/hitl/start:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/admin/agent/evaluate/hitl/decision")
async def hitl_decision_endpoint(payload: HitlDecision):
    """
    Submit a human decision in response to an interrupt.

    Supports:
      - Approve:
            { "thread_id": "...", "decision": "approve" }

      - Reject:
            { "thread_id": "...", "decision": "reject", "message": "Reason" }

      - Edit (override scoring):
            {
              "thread_id": "...",
              "decision": "edit",
              "edited_scores": {
                  "scheduling_score": 80,
                  "alignment_score": 75,
                  "workload_score": 60
              }
            }

    The HITL resume logic determines whether:
      - The evaluation is now complete, OR
      - Another human interrupt is needed (rare but possible).
    """
    try:
        print("HITL decision payload:")
        print(payload)

        decision = payload.decision.strip().lower()
        if decision not in {"approve", "reject", "edit"}:
            raise HTTPException(
                status_code=400,
                detail="decision must be one of: 'approve', 'reject', 'edit'",
            )

        if decision == "edit" and not payload.edited_scores:
            raise HTTPException(
                status_code=400,
                detail="edited_scores must be provided when decision='edit'",
            )

        # Ensure synthesizer agent exists
        _, synth_agent = _ensure_hitl_initialized()

        # Resume HITL flow
        response = hitl_resume(
            synth_agent=synth_agent,
            thread_id=payload.thread_id,
            decision_type=decision,
            edited_scores=payload.edited_scores,
            message=payload.message,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        print("Error in /admin/agent/evaluate/hitl/decision:", e)
        raise HTTPException(status_code=500, detail="Internal server error")
