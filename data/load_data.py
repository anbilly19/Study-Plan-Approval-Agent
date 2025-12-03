import csv
import sqlite3
from pathlib import Path

# -------------------------
# Demo data dictionaries
# -------------------------

fallback_courses_data = {
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

DEMO_CASES = [
    {
        "case_id": "CASE-2025-001",
        "student_id": "1",
        "student_name": "John Doe",
        "status": "Under Review",
        "semester": "Fall 2025",
        "major": "Computer Science",
        "minor": "Mathematics",
        "total_courses": 3,
        "total_credits": 11,
        "submitted_date": "2025-11-08 14:30:00",
        "last_updated": "2025-11-10 09:15:00",
        "courses": [
            {"code": "CS 201", "name": "Data Structures", "credits": 4},
            {"code": "CS 301", "name": "Algorithms", "credits": 4},
            {"code": "MATH 250", "name": "Linear Algebra", "credits": 3},
        ],
        "notes": "Application is currently being reviewed by the academic committee.",
    },
    {
        "case_id": "CASE-2025-002",
        "student_id": "2",
        "student_name": "Jane Smith",
        "status": "Pending",
        "semester": "Fall 2025",
        "major": "Physics",
        "minor": "Mathematics",
        "total_courses": 4,
        "total_credits": 15,
        "submitted_date": "2025-11-09 10:20:00",
        "last_updated": "2025-11-09 10:20:00",
        "courses": [
            {"code": "PHYS 201", "name": "General Physics II", "credits": 4},
            {"code": "MATH 201", "name": "Calculus II", "credits": 4},
            {"code": "MATH 250", "name": "Linear Algebra", "credits": 3},
            {"code": "CS 101", "name": "Introduction to Programming", "credits": 4},
        ],
        "notes": "Awaiting initial review.",
    },
    {
        "case_id": "CASE-2025-003",
        "student_id": "3",
        "student_name": "Alice Johnson",
        "status": "Approved",
        "semester": "Spring 2025",
        "major": "Computer Science",
        "minor": "English",
        "total_courses": 4,
        "total_credits": 13,
        "submitted_date": "2025-02-15 11:00:00",
        "last_updated": "2025-02-18 14:30:00",
        "courses": [
            {"code": "CS 350", "name": "Database Systems", "credits": 3},
            {"code": "CS 301", "name": "Algorithms", "credits": 4},
            {"code": "ENG 201", "name": "Literature Analysis", "credits": 3},
            {"code": "MATH 101", "name": "Calculus I", "credits": 3},
        ],
        "notes": "Approved by Dr. Schmidt. All prerequisites met.",
    },
    {
        "case_id": "CASE-2025-004",
        "student_id": "4",
        "student_name": "Bob Williams",
        "status": "Rejected",
        "semester": "Fall 2025",
        "major": "Mathematics",
        "minor": "Computer Science",
        "total_courses": 2,
        "total_credits": 6,
        "submitted_date": "2025-11-07 16:45:00",
        "last_updated": "2025-11-08 10:00:00",
        "courses": [
            {"code": "MATH 250", "name": "Linear Algebra", "credits": 3},
            {"code": "CS 101", "name": "Introduction to Programming", "credits": 3},
        ],
        "notes": "Insufficient course load. Minimum 12 credits required for full-time enrollment.",
    },
]

# -------------------------
# Paths
# -------------------------

BASE_DIR = Path(__file__).resolve().parent  # data/
DB_PATH = BASE_DIR / "dev_template.db"
SCHEMA_PATH = BASE_DIR.parent / "src" / "db" / "schema.sql"
CONTEXT_DIR = BASE_DIR / "context_tables"


# -------------------------
# Helpers
# -------------------------


def run_schema(conn):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)


def clear_tables(conn):
    conn.execute("DELETE FROM course_enroll_request;")
    conn.execute("DELETE FROM student;")
    conn.execute("DELETE FROM professor;")
    conn.execute("DELETE FROM exam;")
    conn.execute("DELETE FROM lecture;")
    conn.execute("DELETE FROM course;")
    conn.commit()


def read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


# -------------------------
# Load from CSVs
# -------------------------


def load_courses(conn, masterlist_rows, desc_rows):
    desc_by_id = {row["course_id"]: row for row in desc_rows}

    for row in masterlist_rows:
        course_id = row["course_id"]
        department = row.get("Department")
        level = row.get("Course Level")

        desc_row = desc_by_id.get(course_id)
        if desc_row is not None:
            full_name = desc_row.get("Full Name") or course_id
            description = desc_row.get("Description")
        else:
            full_name = row.get("Possible Full Name") or course_id
            description = None

        conn.execute(
            """
            INSERT INTO course (course_id, department, level, full_name, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (course_id, department, level, full_name, description),
        )

    conn.commit()


def load_lectures(conn, lectures_rows):
    for row in lectures_rows:
        credits_raw = row.get("credits", "")
        try:
            credits = int(credits_raw) if credits_raw != "" else 0
        except ValueError:
            credits = 0

        conn.execute(
            """
            INSERT INTO lecture (course_id, day, slot, credits)
            VALUES (?, ?, ?, ?)
            """,
            (row["course_id"], row["day"], row["slot"], credits),
        )

    conn.commit()


def load_exams(conn, exam_rows):
    for row in exam_rows:
        conn.execute(
            """
            INSERT INTO exam (course_id, date, slot)
            VALUES (?, ?, ?)
            """,
            (row["course_id"], row["date"], row["slot"]),
        )
    conn.commit()


# -------------------------
# Seed students & requests
# -------------------------


def seed_students_from_demo_cases(conn):
    """
    Insert students from DEMO_CASES.

    We trust the provided student_id values (1, 2, 3, 4).
    """
    for case in DEMO_CASES:
        student_id = int(case["student_id"])
        name = case["student_name"]
        # Seed a dummy email
        email_local = name.lower().replace(" ", ".")
        email = f"{email_local}@example.edu"

        conn.execute(
            """
            INSERT OR IGNORE INTO student (student_id, name, email)
            VALUES (?, ?, ?)
            """,
            (student_id, name, email),
        )

    conn.commit()


def build_fallback_index():
    """Build an index: course_code -> (department, time, professor, seats, credits) using fallback_courses_data."""
    index = {}
    for dept, courses in fallback_courses_data.items():
        for c in courses:
            code = c["code"]
            index[code] = {
                "department": dept,
                "time": c["time"],
                "professor": c["professor"],
                "seats": c["seats"],
                "credits": c["credits"],
            }
    return index


def build_course_index(conn):
    """Map course_id (code) -> basic info from the course table."""
    cur = conn.execute("SELECT course_id, department, full_name FROM course")
    index = {}
    for course_id, department, full_name in cur.fetchall():
        index[course_id] = {
            "department": department,
            "full_name": full_name,
        }
    return index


def seed_course_enroll_requests(conn):
    fallback_index = build_fallback_index()
    course_index = build_course_index(conn)

    for case in DEMO_CASES:
        case_id = case["case_id"]
        student_id = int(case["student_id"])
        semester = case["semester"]
        major = case.get("major")
        minor = case.get("minor")
        status = case["status"]
        submitted_date = case.get("submitted_date")
        last_updated = case.get("last_updated")
        notes = case.get("notes")

        for course in case["courses"]:
            code = course["code"]
            name = course["name"]
            credits_from_case = course.get("credits", 0)

            fb = fallback_index.get(code, {})
            fb_department = fb.get("department")
            fb_time = fb.get("time") or "TBA"
            fb_prof = fb.get("professor")
            fb_seats = fb.get("seats")
            fb_credits = fb.get("credits")

            # Prefer credits from DEMO_CASES; fall back to fallback_courses_data
            credits = credits_from_case or fb_credits or 0

            # Try to resolve course_id to existing course row
            if code in course_index:
                course_id = code
                department = course_index[code]["department"] or fb_department
            else:
                course_id = None
                department = fb_department

            conn.execute(
                """
                INSERT OR REPLACE INTO course_enroll_request (
                    case_id,
                    student_id,
                    semester,
                    major,
                    minor,
                    course_id,
                    course_code,
                    course_name,
                    department,
                    credits,
                    time,
                    professor_name,
                    seats,
                    status,
                    submitted_date,
                    last_updated,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    student_id,
                    semester,
                    major,
                    minor,
                    course_id,
                    code,
                    name,
                    department,
                    credits,
                    fb_time,
                    fb_prof,
                    fb_seats,
                    status,
                    submitted_date,
                    last_updated,
                    notes,
                ),
            )

    conn.commit()


# -------------------------
# Main
# -------------------------


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        run_schema(conn)
        clear_tables(conn)

        # Load CSV-based tables
        course_masterlist = read_csv(CONTEXT_DIR / "course_masterlist.csv")
        course_description = read_csv(CONTEXT_DIR / "course_description.csv")
        lectures = read_csv(CONTEXT_DIR / "lectures.csv")
        exams = read_csv(CONTEXT_DIR / "exams.csv")

        load_courses(conn, course_masterlist, course_description)
        load_lectures(conn, lectures)
        load_exams(conn, exams)

        # Seed demo students and enrollment requests
        seed_students_from_demo_cases(conn)
        seed_course_enroll_requests(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
