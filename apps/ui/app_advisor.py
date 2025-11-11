import random
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Technical University of Germany",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Global CSS
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .stApp { background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); }

    #MainMenu, footer, header { visibility: hidden; }

    .hero-section {
        text-align: center;
        padding: 100px 20px 80px;
        background: linear-gradient(180deg, rgba(138, 43, 226, 0.12) 0%, transparent 100%);
        border-radius: 20px;
        margin: 20px 0 40px;
    }
    .hero-title {
        font-size: 72px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 20px; line-height: 1.2;
    }
    .hero-subtitle { font-size: 24px; color: #a0a0a0; font-weight: 300; margin-bottom: 40px; }

    .feature-card, .course-card, .login-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 40px;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .feature-card::before, .course-card::before, .login-card::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        opacity: 0; transition: opacity 0.3s ease;
    }
    .feature-card:hover::before, .course-card:hover::before, .login-card:hover::before { opacity: 1; }
    .feature-card:hover, .course-card:hover, .login-card:hover {
        transform: translateY(-4px);
        border-color: rgba(255, 255, 255, 0.2);
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.18);
    }

    .course-card { border-radius: 15px; padding: 25px; margin: 15px 0; }
    .course-code { font-size: 14px; color: #667eea; font-weight: 600; margin-bottom: 8px; }
    .course-name { font-size: 20px; color: #ffffff; font-weight: 600; margin-bottom: 10px; }
    .course-info { font-size: 14px; color: #a0a0a0; margin-bottom: 5px; }

    .stats-container { display: flex; justify-content: space-around; margin: 60px 0; flex-wrap: wrap; }
    .stat-item { text-align: center; padding: 20px; }
    .stat-number {
        font-size: 48px; font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .stat-label { font-size: 16px; color: #a0a0a0; margin-top: 10px; }

    .section-title { font-size: 48px; font-weight: 700; color: #ffffff; text-align: center; margin: 80px 0 60px; }

    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border: none; border-radius: 50px;
        padding: 12px 40px; font-weight: 600; font-size: 16px; transition: all 0.3s ease;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
    .stSelectbox > div > div, .stTextInput > div > div > input, .stPassword > div > div > input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important; color: #fff !important;
    }
    label, .stCheckbox, .stSelectbox, .stTextInput, .stPassword { color: #d0d0d0 !important; }

    .login-heading {
        font-size: 34px; font-weight: 700; color: #fff; margin: 0 0 8px;
        letter-spacing: 0.3px;
    }
    .login-sub {
        margin: 0 0 18px; color: #a0a0a0; font-size: 14px;
    }
    .hint-pill {
        display: inline-block; padding: 6px 10px; border-radius: 999px;
        background: rgba(102,126,234,0.12); color: #cfd5ff; font-size: 12px;
        border: 1px solid rgba(102, 126, 234, 0.25);
    }
</style>
""",
    unsafe_allow_html=True,
)

# Authentication setup
CREDENTIALS = {"1": "1"}

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0
if "lock_until" not in st.session_state:
    st.session_state.lock_until = None


# Lockout check
def locked_out():
    if st.session_state.lock_until is None:
        return False
    return datetime.now() < st.session_state.lock_until


# Login view
def login_view():
    st.markdown(
        """
        <div class="hero-section">
            <div class="hero-title">Technical University of Germany</div>
            <div class="hero-subtitle">Wer nicht vorwärts geht, der kommt zurück. - Johann Wolfgang von Goethe</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    colL, colC, colR = st.columns([1, 1, 1])
    with colC:
        st.markdown(
            """
            <div class="login-card">
                <div class="login-heading">Welcome back</div>
                <div class="login-sub">
                    Sign in to continue.
                    <div style="margin-top:10px;">
                        <span class="hint-pill">Demo login → <b>user:</b> 1 &nbsp;&nbsp; <b>pass:</b> 1</span>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        if locked_out():
            unlock_at = st.session_state.lock_until.strftime("%H:%M:%S")
            st.error(f"Too many attempts. Try again at {unlock_at}.")
            st.markdown("</div>", unsafe_allow_html=True)
            st.stop()

        with st.form("login_form", clear_on_submit=False):
            user = st.text_input("Username", value="", placeholder="Enter username", key="login_user")
            pwd = st.text_input("Password", value="", type="password", placeholder="Enter password", key="login_pwd")
            login = st.form_submit_button("Sign in")

            if login:
                if CREDENTIALS.get(user) == pwd:
                    st.session_state.auth_ok = True
                    st.session_state.auth_user = user
                    st.session_state.login_attempts = 0
                    st.success("Signed in successfully!")
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    if st.session_state.login_attempts >= 5:
                        st.session_state.lock_until = datetime.now() + timedelta(minutes=2)
                        st.error("Too many failed attempts. Locked for 2 minutes.")
                    else:
                        remaining = 5 - st.session_state.login_attempts
                        st.error(f"Invalid credentials. {remaining} attempt(s) left.")

        st.markdown(
            """
                <div style="margin-top:14px;color:#8c8c8c;font-size:12px;">
                    By continuing, you agree to the Terms and acknowledge the Privacy Policy.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Logout sidebar
def logout_button():
    with st.sidebar:
        st.markdown("### Account")
        st.write(f"Signed in as **{st.session_state.auth_user}**")
        if st.button("Logout"):
            st.session_state.auth_ok = False
            st.session_state.auth_user = None
            st.session_state.login_attempts = 0
            st.session_state.lock_until = None
            st.rerun()


# Auth gate
if not st.session_state.auth_ok:
    login_view()
    st.stop()
else:
    logout_button()

# Session state initialization
if "selected_courses" not in st.session_state:
    st.session_state.selected_courses = []
if "semester" not in st.session_state:
    st.session_state.semester = "Fall 2025"
if "major" not in st.session_state:
    st.session_state.major = "Computer Science"
if "minor" not in st.session_state:
    st.session_state.minor = "Mathematics"
if "approval_requested" not in st.session_state:
    st.session_state.approval_requested = False

# App hero
st.markdown(
    """
<div class="hero-section">
    <div class="hero-title">KursKraft</div>
    <div class="hero-subtitle">Smart course planning for successful students</div>
</div>
""",
    unsafe_allow_html=True,
)

# Sample course data
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

# Stats section
total_credits = sum(course["credits"] for course in st.session_state.selected_courses)

col1, col2 = st.columns(2)
with col1:
    st.session_state.major = st.selectbox(
        "🎓 Select Major",
        list(courses_data.keys()),
        index=list(courses_data.keys()).index(st.session_state.major) if st.session_state.major in courses_data else 0,
    )
with col2:
    st.session_state.minor = st.selectbox(
        "📚 Select Minor",
        list(courses_data.keys()),
        index=list(courses_data.keys()).index(st.session_state.minor) if st.session_state.minor in courses_data else 0,
    )

st.markdown(
    f"""
<div class="stats-container">
    <div class="stat-item">
        <div class="stat-number">{len(st.session_state.selected_courses)}</div>
        <div class="stat-label">Courses Selected</div>
    </div>
    <div class="stat-item">
        <div class="stat-number">{total_credits}</div>
        <div class="stat-label">Total Credits</div>
    </div>
    <div class="stat-item">
        <div class="stat-number">{st.session_state.semester}</div>
        <div class="stat-label">Current Semester</div>
    </div>
    <div class="stat-item">
        <div class="stat-number">1.0</div>
        <div class="stat-label">Target GPA</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# Course browser controls
st.markdown('<div class="section-title">Browse Available Courses</div>', unsafe_allow_html=True)

fc1, fc2, fc3 = st.columns(3)
with fc1:
    selected_dept = st.selectbox("🎯 Department", ["All"] + list(courses_data.keys()))
with fc2:
    semester_select = st.selectbox("📅 Semester", ["Fall 2025", "Spring 2026", "Summer 2026"])
    st.session_state.semester = semester_select
with fc3:
    num_subjects = st.number_input("📋 Number of Subjects", min_value=1, max_value=10, value=3, step=1)
    if st.button("🎲 Random Select", key="random_select"):
        available_courses = []
        depts_to_use = courses_data.keys() if selected_dept == "All" else [selected_dept]
        for dept in depts_to_use:
            available_courses.extend(courses_data[dept])
        if len(available_courses) >= num_subjects:
            st.session_state.selected_courses = random.sample(available_courses, num_subjects)  # nosec B311
            st.rerun()
        else:
            st.warning(f"Only {len(available_courses)} courses available. Cannot select {num_subjects}.")

# Course browser listing
departments_to_show = courses_data.keys() if selected_dept == "All" else [selected_dept]
for dept in departments_to_show:
    st.markdown(
        f'<h2 style="color: #667eea; margin-top: 40px; margin-bottom: 20px;">📚 {dept}</h2>', unsafe_allow_html=True
    )
    courses = courses_data[dept]
    for course in courses:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(
                f"""
                <div class="course-card">
                    <div class="course-code">{course['code']}</div>
                    <div class="course-name">{course['name']}</div>
                    <div class="course-info">⏰ {course['time']}</div>
                    <div class="course-info">👨‍🏫 {course['professor']}</div>
                    <div class="course-info">💳 {course['credits']} Credits | 💺 {course['seats']} seats available</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown('<div style="margin-top: 35px;"></div>', unsafe_allow_html=True)
            add_key = f"add_{course['code']}_{course['time']}"
            remove_key = f"remove_{course['code']}_{course['time']}"
            if course not in st.session_state.selected_courses:
                if st.button("➕ Add", key=add_key):
                    st.session_state.selected_courses.append(course)
                    st.rerun()
            else:
                if st.button("✓ Added", key=remove_key, type="secondary"):
                    st.session_state.selected_courses.remove(course)
                    st.rerun()

# API endpoints
HEALTH_URL = "http://127.0.0.1:8000/health"
POST_URL = "http://127.0.0.1:8000/approval"


# Payload builder
def build_payload():
    return {
        "semester": st.session_state.semester,
        "major": st.session_state.major,
        "minor": st.session_state.minor,
        "total_courses": len(st.session_state.selected_courses),
        "total_credits": sum(c["credits"] for c in st.session_state.selected_courses),
        "courses": [
            {
                "code": c["code"],
                "name": c["name"],
                "time": c["time"],
                "professor": c["professor"],
                "credits": c["credits"],
                "seats": c["seats"],
            }
            for c in st.session_state.selected_courses
        ],
    }


# Health and submission call
def call_fastapi_health_and_post(payload: dict, timeout_sec: int = 6):
    health_result, post_result = None, None
    try:
        r = requests.get(HEALTH_URL, timeout=timeout_sec)
        health_result = {"ok": r.ok, "status_code": r.status_code, "text": r.text}
    except Exception as e:
        health_result = {"ok": False, "error": str(e)}
    try:
        r2 = requests.post(POST_URL, json=payload, timeout=timeout_sec)
        try:
            post_body = r2.json()
        except Exception:
            post_body = r2.text
        post_result = {"ok": r2.ok, "status_code": r2.status_code, "body": post_body}
    except Exception as e:
        post_result = {"ok": False, "error": str(e)}
    return health_result, post_result


# Schedule section
if st.session_state.selected_courses:
    st.markdown('<div class="section-title">My Course Schedule</div>', unsafe_allow_html=True)
    cc1, cc2 = st.columns([3, 1])
    with cc1:
        schedule_data = [
            {
                "Course Code": c["code"],
                "Course Name": c["name"],
                "Time": c["time"],
                "Professor": c["professor"],
                "Credits": c["credits"],
            }
            for c in st.session_state.selected_courses
        ]
        df = pd.DataFrame(schedule_data)
        st.dataframe(df, width="stretch", hide_index=True)

    with cc2:
        st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title" style="color:#fff;font-weight:700;">Summary</div>
                <div class="feature-description">
                    <strong>Major:</strong> {st.session_state.major}<br>
                    <strong>Minor:</strong> {st.session_state.minor}<br>
                    <strong>Total Courses:</strong> {len(st.session_state.selected_courses)}<br>
                    <strong>Total Credits:</strong> {sum(x['credits'] for x in st.session_state.selected_courses)}<br>
                    <strong>Semester:</strong> {st.session_state.semester}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("📥 Export", key="export", width="stretch"):
                export_df = pd.DataFrame(schedule_data)
                csv_data = export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download CSV",
                    csv_data,
                    file_name=f"KursKraft_{st.session_state.semester.replace(' ', '_').lower()}.csv",
                    mime="text/csv",
                    width="stretch",
                )
                st.success("✅ Schedule exported!")
        with b2:
            if st.button("🗑️ Clear", key="clear", width="stretch"):
                st.session_state.selected_courses = []
                st.rerun()
        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

        if st.button("📋 Request for Approval", key="approval", width="stretch", type="primary"):
            if len(st.session_state.selected_courses) > 0:
                st.session_state.approval_requested = True
                with st.spinner("Contacting advisor service and sending your selection..."):
                    payload = build_payload()
                    health_res, post_res = call_fastapi_health_and_post(payload)
                st.success("✅ Approval request submitted!")
                st.balloons()
                st.info(
                    f"📧 Your course schedule for {st.session_state.semester} has been sent to your academic advisor for"
                    "review."
                )

                # st.markdown("#### Service Health")
                # if health_res.get("ok"):
                #     st.success(f"Health OK (status {health_res.get('status_code')}) — {health_res.get('text')}")
                # else:
                #     st.error(f"Health check failed: {health_res}")

                # st.markdown("#### Submission Response")
                # if post_res.get("ok"):
                #     st.success(f"Submission accepted (status {post_res.get('status_code')}).")
                #     st.json(post_res.get("body"))
                # else:
                #     st.error(f"Submission failed: {post_res}")
            else:
                st.warning("⚠️ Please add courses before requesting approval.")

# Tips and footer
st.markdown('<div class="section-title">Planning Tips</div>', unsafe_allow_html=True)
t1, t2, t3 = st.columns(3)
for col, tip in zip(
    [t1, t2, t3],
    [
        {
            "icon": "⚡",
            "title": "Balance Your Load",
            "description": "Aim for 12-15 credits per semester. Mix challenging courses with lighter ones.",
        },
        {
            "icon": "📅",
            "title": "Check Prerequisites",
            "description": "Make sure you've completed required courses before enrolling in advanced classes.",
        },
        {
            "icon": "🎯",
            "title": "Plan Ahead",
            "description": "Map out your 4-year plan early to ensure you meet all graduation requirements.",
        },
    ],
):
    with col:
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-icon">{tip['icon']}</div>
                <div class="feature-title" style="color:#fff;font-weight:700;">{tip['title']}</div>
                <div class="feature-description">{tip['description']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    """
<div style="text-align: center; padding: 40px 20px; color: #808080; border-top: 1px solid rgba(255, 255, 255, 0.1);
margin-top: 80px;"><p>© 2025 Technical University of Germany. All rights reserved.</p>
<p style="margin-top: 10px; font-size: 14px;">Built with 💜 for grades, by students.</p>
</div>
""",
    unsafe_allow_html=True,
)
