import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# # Add the project root to the Python path
# project_root = Path(__file__).parent.parent.parent
# sys.path.insert(0, str(project_root))
from src.db.queries import fetch_cases, fetch_courses, save_approval_to_db, update_case_status

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StatusUpdate(BaseModel):
    status: str  # "Approved" or "Rejected"
    notes: str | None = None


@app.get("/health")
def health_check():
    print("Health check endpoint called")
    return {"decision": "yellow"}


@app.post("/approval")
async def approval_endpoint(request: Request):
    try:
        data = await request.json()
        print(json.dumps(data, indent=4))
        inserted_rows = save_approval_to_db(data)
        print(inserted_rows, "rows inserted/updated in the database")

        return {"message": "Approval data received", "received_items": len(data.get("courses", []))}
    except Exception as e:
        print("Error while reading JSON:", e)
        return {"error": str(e)}


@app.get("/courses")
def get_courses():
    print("Courses endpoint called")
    courses_data = fetch_courses()
    return {"courses": courses_data}


@app.get("/admin/cases")
def get_cases():
    print("Cases endpoint called")
    return fetch_cases()


@app.patch("/admin/cases/{case_id}/status")
async def update_case_status_endpoint(case_id: str, payload: StatusUpdate):
    try:
        # Normalise / validate status label if needed
        new_status = payload.status.strip().capitalize()  # "approved" → "Approved"
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
        # invalid status etc.
        raise HTTPException(status_code=400, detail=str(ve))

    except HTTPException:
        # re-raise cleanly
        raise

    except Exception as e:
        # fallback
        print("Error while updating case status:", e)
        raise HTTPException(status_code=500, detail="Internal server error")
