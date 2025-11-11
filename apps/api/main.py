import json

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    print("Health check endpoint called")
    return {"status": "healthy"}


@app.post("/approval")
async def approval_endpoint(request: Request):
    try:
        data = await request.json()
        print(json.dumps(data, indent=4))
        return {"message": "Approval data received", "received_items": len(data.get("courses", []))}
    except Exception as e:
        print("Error while reading JSON:", e)
        return {"error": str(e)}
