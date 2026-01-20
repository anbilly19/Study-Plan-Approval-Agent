import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Get the project root directory (2 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "dev_template.db"


def fetch_cases():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            cer.case_id,
            cer.student_id,
            s.name AS student_name,
            cer.status,
            cer.semester,
            cer.major,
            cer.minor,
            cer.course_code,
            cer.course_name,
            cer.credits,
            cer.submitted_date,
            cer.last_updated,
            cer.notes
        FROM course_enroll_request cer
        JOIN student s ON cer.student_id = s.student_id
        ORDER BY cer.case_id, cer.course_code
    """
    ).fetchall()

    conn.close()

    cases = defaultdict(
        lambda: {
            "case_id": None,
            "student_id": None,
            "student_name": None,
            "status": None,
            "semester": None,
            "major": None,
            "minor": None,
            "total_courses": 0,
            "total_credits": 0,
            "submitted_date": None,
            "last_updated": None,
            "courses": [],
            "notes": None,
        }
    )

    for row in rows:
        cid = row["case_id"]
        case = cases[cid]

        # Set case-level fields once
        case["case_id"] = cid
        case["student_id"] = str(row["student_id"])
        case["student_name"] = row["student_name"]
        case["status"] = row["status"]
        case["semester"] = row["semester"]
        case["major"] = row["major"]
        case["minor"] = row["minor"]
        case["submitted_date"] = row["submitted_date"]
        case["last_updated"] = row["last_updated"]
        case["notes"] = row["notes"]

        # Add course entry
        case["courses"].append(
            {
                "code": row["course_code"],
                "name": row["course_name"],
                "credits": row["credits"],
            }
        )

    final_cases = []
    for _cid, case in cases.items():
        case["total_courses"] = len(case["courses"])
        case["total_credits"] = sum(c["credits"] for c in case["courses"])
        final_cases.append(case)

    return final_cases


def fetch_courses():
    """Build a dict like course list per department from the course + lecture + professor tables."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                c.department,
                c.course_id,
                c.full_name,
                l.credits,
                (l.day || ' ' || l.slot) AS time,
                COALESCE(p.name, 'None') AS professor,
                COALESCE(c.seats, 0) AS seats
            FROM course AS c
            JOIN lecture AS l
              ON l.course_id = c.course_id
            LEFT JOIN professor AS p
              ON p.professor_id = l.professor_id
            ORDER BY c.department, c.course_id
            """
        )

        rows = cur.fetchall()

        courses_data = {}
        for row in rows:
            dept = row["department"] or "Unknown"
            courses_data.setdefault(dept, []).append(
                {
                    "code": row["course_id"],
                    "name": row["full_name"],
                    "credits": int(row["credits"]) if row["credits"] is not None else 0,
                    "time": row["time"],
                    "professor": row["professor"],
                    "seats": int(row["seats"]) if row["seats"] is not None else 0,
                }
            )

        return courses_data

    finally:
        conn.close()


def resolve_course_from_db(conn, course_code: str):
    """
    Resolve a canonical course row from the database by course_code.

    Given a course_code like 'FIN-300', look up the canonical course row in the DB.
    If found → return (course_id, department, full_name).
    If not → return (None, None, None).
    """
    sql = """
        SELECT course_id, department, full_name
        FROM course
        WHERE course_id = ?
    """

    cur = conn.cursor()
    cur.execute(sql, (course_code,))
    row = cur.fetchone()

    if row:
        return row["course_id"], row["department"], row["full_name"]

    return None, None, None


def get_next_case_number(conn, normalized_semester: str) -> int:
    """Generate the next sequential case ID based on existing CASE-Fall2025-00X entries."""
    sql = """
        SELECT case_id
        FROM course_enroll_request
        WHERE case_id LIKE ?
        ORDER BY case_id DESC
        LIMIT 1
    """

    pattern = f"CASE-{normalized_semester}-%"

    cur = conn.cursor()
    cur.execute(sql, (pattern,))
    row = cur.fetchone()

    if not row:
        return 1  # first ID for this semester

    last_case_id = row["case_id"]  # e.g. "CASE-Fall2025-007"
    last_number = int(last_case_id.split("-")[-1])  # → 7

    return last_number + 1


def save_approval_to_db(data: dict) -> int:
    courses = data.get("courses", [])
    if not courses:
        return 0

    student_id = data.get("student_id")
    try:
        student_id = int(student_id) if student_id is not None else None
    except Exception:
        student_id = 1

    semester = data.get("semester")
    if not semester:
        raise ValueError("semester is required")

    major = data.get("major")
    minor = data.get("minor")

    submitted_date = datetime.now().isoformat()
    last_updated = submitted_date
    status = "Pending"

    insert_sql = """
        INSERT INTO course_enroll_request (
            case_id, student_id, semester, major, minor,
            course_id, course_code, course_name, department,
            credits, time, professor_name, seats,
            status, submitted_date, last_updated, notes
        )
        VALUES (?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?)
    """

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 🔑 so row["case_id"] etc. work
    cur = conn.cursor()
    inserted = 0

    try:
        # 👉 One case_id for the whole approval request
        normalized_semester = semester.replace(" ", "")
        next_case_number = get_next_case_number(conn, normalized_semester)
        case_id = f"CASE-{normalized_semester}-{next_case_number:03d}"

        for course in courses:
            course_code = course.get("code")

            # Pull catalog data from course table
            db_course_id, db_department, db_full_name = resolve_course_from_db(conn, course_code)

            course_name = db_full_name if db_full_name else course.get("name")
            department = db_department
            course_id = db_course_id

            time_str = course.get("time")
            professor_name = course.get("professor")
            credits = course.get("credits")
            credits = int(credits) if credits is not None else None

            seats = course.get("seats")
            seats = int(seats) if seats is not None else None
            notes = None

            cur.execute(
                insert_sql,
                (
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
                    time_str,
                    professor_name,
                    seats,
                    status,
                    submitted_date,
                    last_updated,
                    notes,
                ),
            )
            inserted += 1

        conn.commit()

    finally:
        conn.close()

    return inserted


def update_case_status(case_id: str, new_status: str, notes: str | None = None) -> int:
    """
    Update the status of a case (all its course rows) to Approved or Rejected.

    Returns number of rows updated.
    """
    allowed_statuses = {"Approved", "Rejected", "Under Review"}
    if new_status not in allowed_statuses:
        raise ValueError(f"Invalid status '{new_status}'. Allowed: {allowed_statuses}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        now = datetime.now().isoformat()

        cur.execute(
            """
            UPDATE course_enroll_request
               SET status = ?,
                   last_updated = ?,
                   notes = COALESCE(?, notes)
             WHERE case_id = ?
            """,
            (new_status, now, notes, case_id),
        )

        affected = cur.rowcount
        conn.commit()
        return affected

    finally:
        conn.close()
