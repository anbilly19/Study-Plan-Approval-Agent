PRAGMA foreign_keys = ON;

-- =========================
-- Core tables
-- =========================

CREATE TABLE IF NOT EXISTS course (
    course_id   TEXT PRIMARY KEY,          -- e.g. "CS 101"
    department  TEXT,                      -- e.g. "Computer Science"
    level       TEXT,                      -- e.g. "Introductory"
    full_name   TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS professor (
    professor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    email        TEXT
);

CREATE TABLE IF NOT EXISTS student (
    student_id INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS lecture (
    lecture_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id  TEXT NOT NULL,
    day        TEXT NOT NULL,
    slot       TEXT NOT NULL,
    credits    INTEGER NOT NULL,
    FOREIGN KEY (course_id) REFERENCES course(course_id)
);

CREATE TABLE IF NOT EXISTS exam (
    exam_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    date      TEXT NOT NULL,
    slot      TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES course(course_id)
);

-- One row = one course in a case (a student's application)
-- Composite PK: (case_id, course_code) — no surrogate request_id

CREATE TABLE IF NOT EXISTS course_enroll_request (
    case_id        TEXT NOT NULL,         -- e.g. "CASE-2025-001"
    student_id     INTEGER NOT NULL,      -- FK -> student
    semester       TEXT NOT NULL,         -- e.g. "Fall 2025"
    major          TEXT,                  -- snapshot per request
    minor          TEXT,                  -- snapshot per request

    course_id      TEXT,                  -- FK -> course (if we can resolve it)
    course_code    TEXT NOT NULL,         -- e.g. "CS 201"
    course_name    TEXT NOT NULL,         -- e.g. "Data Structures"
    department     TEXT,                  -- e.g. "Computer Science"
    credits        INTEGER NOT NULL,
    time           TEXT NOT NULL,         -- e.g. "MWF 9:00-10:00 AM"
    professor_name TEXT,
    seats          INTEGER,

    status         TEXT NOT NULL,         -- "Under Review", "Pending", etc.
    submitted_date TEXT,
    last_updated   TEXT,
    notes          TEXT,

    PRIMARY KEY (case_id, course_code),

    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (course_id)  REFERENCES course(course_id)
);

CREATE INDEX IF NOT EXISTS idx_lecture_course
    ON lecture (course_id);

CREATE INDEX IF NOT EXISTS idx_exam_course
    ON exam (course_id);

CREATE INDEX IF NOT EXISTS idx_enroll_student
    ON course_enroll_request (student_id);

CREATE INDEX IF NOT EXISTS idx_enroll_semester
    ON course_enroll_request (semester);
