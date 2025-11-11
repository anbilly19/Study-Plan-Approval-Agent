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


@app.get("/courses")
def get_courses():
    print("Courses endpoint called")
    courses_data = {
        "Computer Science": [
            {
                "code": "CS 101",
                "name": "Introduction to Programming",
                "credits": 3,
                "time": "MWF 9:00-10:00 AM",
                "professor": "Dr. Johnson",
                "seats": 45,
            },
            {
                "code": "CS 201",
                "name": "Data Structures",
                "credits": 4,
                "time": "TTh 11:00-12:30 PM",
                "professor": "Dr. Smith",
                "seats": 35,
            },
            {
                "code": "CS 301",
                "name": "Algorithms",
                "credits": 4,
                "time": "MWF 2:00-3:00 PM",
                "professor": "Dr. Lee",
                "seats": 28,
            },
            {
                "code": "CS 350",
                "name": "Database Systems",
                "credits": 3,
                "time": "TTh 1:00-2:30 PM",
                "professor": "Dr. Garcia",
                "seats": 30,
            },
        ],
        "Mathematics": [
            {
                "code": "MATH 101",
                "name": "Calculus I",
                "credits": 4,
                "time": "MWF 10:00-11:00 AM",
                "professor": "Dr. Brown",
                "seats": 50,
            },
            {
                "code": "MATH 201",
                "name": "Calculus II",
                "credits": 4,
                "time": "TTh 9:00-10:30 AM",
                "professor": "Dr. Wilson",
                "seats": 42,
            },
            {
                "code": "MATH 250",
                "name": "Linear Algebra",
                "credits": 3,
                "time": "MWF 1:00-2:00 PM",
                "professor": "Dr. Martinez",
                "seats": 38,
            },
        ],
        "Physics": [
            {
                "code": "PHYS 101",
                "name": "General Physics I",
                "credits": 4,
                "time": "TTh 2:00-3:30 PM",
                "professor": "Dr. Anderson",
                "seats": 40,
            },
            {
                "code": "PHYS 201",
                "name": "General Physics II",
                "credits": 4,
                "time": "MWF 11:00-12:00 PM",
                "professor": "Dr. Taylor",
                "seats": 35,
            },
        ],
        "English": [
            {
                "code": "ENG 101",
                "name": "English Composition",
                "credits": 3,
                "time": "TTh 10:00-11:30 AM",
                "professor": "Dr. Davis",
                "seats": 25,
            },
            {
                "code": "ENG 201",
                "name": "Literature Analysis",
                "credits": 3,
                "time": "MWF 3:00-4:00 PM",
                "professor": "Dr. Moore",
                "seats": 30,
            },
        ],
    }
    return {"courses": courses_data}
