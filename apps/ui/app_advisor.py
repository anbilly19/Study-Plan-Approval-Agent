# admin_dashboard_production.py
import ast
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="KursKraft Admin Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# API endpoints
API_BASE_URL = os.getenv("API_BASE_URL") or "http://localhost:8000"

HEALTH_URL = f"{API_BASE_URL}/health"
UPDATE_STATUS_URL = f"{API_BASE_URL}/admin/cases/{{case_id}}/status"
ALL_CASES_URL = f"{API_BASE_URL}/admin/cases"


def inject_production_css() -> None:
    """Inject production-ready CSS with proper color scheme (light + dark)."""
    st.markdown(
        """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    :root {
        color-scheme: light dark;

        --primary-color: #667eea;

        /* Backgrounds */
        --bg-primary: #f3f4ff;
        --bg-secondary: #e5e7ff;
        --bg-gradient: radial-gradient(circle at top left,#e0e7ff 0,#e5e7eb 40%,#f9fafb 100%);
        --bg-card: rgba(255, 255, 255, 0.96);

        /* Text */
        --text-primary: #111827;
        --text-secondary: #4b5563;
        --text-muted: #9ca3af;

        /* Accents */
        --accent-primary: #667eea;
        --accent-secondary: #764ba2;
        --accent-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

        /* Status colors */
        --success: #16a34a;
        --warning: #eab308;
        --danger: #dc2626;
        --info: #2563eb;

        /* Borders / shadows / inputs */
        --border: rgba(148, 163, 184, 0.45);
        --shadow: 0 18px 40px rgba(148, 163, 184, 0.35);

        --input-bg: rgba(249, 250, 251, 0.9);
        --input-border: rgba(156, 163, 175, 0.9);
    }

    @media (prefers-color-scheme: dark) {
        :root {
            --bg-primary: #050509;
            --bg-secondary: #151527;
            --bg-gradient: radial-gradient(circle at top left,#1b1b3a 0,#050509 40%,#050509 100%);
            --bg-card: rgba(255, 255, 255, 0.03);

            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
            --text-muted: #808080;

            --accent-primary: #667eea;
            --accent-secondary: #764ba2;
            --accent-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

            --success: #4caf50;
            --warning: #ffc107;
            --danger: #f44336;
            --info: #2196f3;

            --border: rgba(255, 255, 255, 0.08);
            --shadow: 0 24px 60px rgba(0, 0, 0, 0.55);

            --input-bg: rgba(255, 255, 255, 0.04);
            --input-border: rgba(255, 255, 255, 0.16);
        }
    }

    /* Global */
    html, body, [data-testid="stApp"] {
        background: var(--bg-gradient) !important;
        color: var(--text-primary) !important;
    }

    #MainMenu, footer, header, [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
        display: none !important;
        visibility: hidden !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    .block-container {
        padding: 2.5rem 3rem !important;
        max-width: 1200px !important;
    }

    [data-testid="stSidebar"] {
        background: var(--bg-card) !important;
        backdrop-filter: blur(10px) !important;
        border-right: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stSidebar"] > div {
        padding: 2rem 1.5rem !important;
    }

    /* Login page */
    .login-hero-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin-bottom: 2.5rem;
    }

    .login-hero-brand {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        font-size: 18px;
        font-weight: 600;
    }

    .login-hero-logo {
        width: 32px;
        height: 32px;
        border-radius: 999px;
        background: var(--accent-gradient);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
    }

    .login-hero-env {
        padding: 4px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid var(--border);
        font-size: 11px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-secondary);
    }

    .login-copy-title {
        font-size: 40px;
        line-height: 1.1;
        font-weight: 700;
        margin-bottom: 10px;
        color: var(--text-primary);
    }

    .login-copy-title span {
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .login-copy-subtitle {
        font-size: 16px;
        color: var(--text-secondary);
        max-width: 420px;
        margin-bottom: 24px;
    }

    .login-feature-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }

    .login-feature-pill {
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border);
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: #4f46e5;
    }

    @media (prefers-color-scheme: dark) {
        .login-feature-pill {
            color: #d2d5ff;
        }
    }

    .login-feature-dot {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: #4caf50;
    }

    .login-metric-row {
        display: flex;
        gap: 24px;
        margin-top: 26px;
        flex-wrap: wrap;
    }

    .login-metric {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .login-metric-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
    }

    .login-metric-value {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary);
    }

    .login-card-shell {
        max-width: 420px;
        margin-left: auto;
    }

    .login-card {
        background: radial-gradient(circle at top left, rgba(102, 126, 234, 0.18), transparent 55%),
                    var(--bg-card);
        backdrop-filter: blur(22px);
        border-radius: 22px;
        border: 1px solid rgba(255, 255, 255, 0.10);
        padding: 28px 26px 24px;
        box-shadow: var(--shadow);
        position: relative;
        overflow: hidden;
        color: var(--text-primary);
    }

    .login-card::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: inherit;
        border: 1px solid rgba(255, 255, 255, 0.02);
        pointer-events: none;
    }

    .login-card-heading {
        font-size: 24px;
        font-weight: 600;
        margin-bottom: 10px;
        color: var(--text-primary);
    }

    .login-card-sub {
        font-size: 13px;
        color: var(--text-secondary);
        margin-bottom: 14px;
    }

    .login-demo-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(12, 179, 104, 0.07);
        border: 1px solid rgba(12, 179, 104, 0.35);
        color: #15803d;
        font-size: 11px;
        margin-bottom: 22px;
    }

    @media (prefers-color-scheme: dark) {
        .login-demo-pill {
            color: #9ff0c3;
        }
    }

    .login-demo-pill code {
        font-family: 'Inter', monospace;
        background: rgba(0, 0, 0, 0.06);
        padding: 2px 6px;
        border-radius: 999px;
        font-size: 11px;
    }

    @media (prefers-color-scheme: dark) {
        .login-demo-pill code {
            background: rgba(0, 0, 0, 0.2);
        }
    }

    .login-legal-text {
        margin-top: 10px;
        color: var(--text-muted);
        font-size: 11px;
        text-align: left;
    }

    /* Inputs */
    .stTextInput > div > div,
    .stSelectbox > div > div,
    .stTextArea > div > div {
        background: var(--input-bg) !important;
        border-radius: 10px !important;
        border: 1px solid var(--input-border) !important;
        transition: border 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
    }

    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea textarea {
        color: var(--text-primary) !important;
        font-size: 14px !important;
        padding: 10px 12px !important;
    }

    .stTextInput > div > div > input::placeholder,
    .stTextArea textarea::placeholder {
        color: var(--text-muted) !important;
    }

    .stTextInput > div > div:focus-within,
    .stSelectbox > div > div:focus-within,
    .stTextArea > div > div:focus-within {
        border-color: rgba(129, 140, 248, 0.9) !important;
        box-shadow: 0 0 0 1px rgba(129, 140, 248, 0.4) !important;
        background: var(--input-bg) !important;
    }

    .stSelectbox input {
        caret-color: transparent !important;
    }

    label {
        color: var(--text-secondary) !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        margin-bottom: 6px !important;
    }

    /* Buttons */
    .stButton > button {
        background: var(--accent-gradient) !important;
        color: white !important;
        border: none !important;
        border-radius: 999px !important;
        padding: 10px 26px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
        width: 100%;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 14px 30px rgba(102, 126, 234, 0.35) !important;
    }

    .btn-success > button {
        background: linear-gradient(135deg, #22c55e, #16a34a) !important;
    }

    .btn-danger > button {
        background: linear-gradient(135deg, #ef4444, #dc2626) !important;
    }

    .btn-secondary > button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
    }

    /* Dashboard hero */
    .hero-section {
        text-align:center;
        background: linear-gradient(
            135deg,
            rgba(102, 126, 234, 0.12),
            rgba(8, 12, 40, 0.06)
        );
        border-radius: 20px;
        padding: 24px 24px 22px;
        margin: 10px 0 34px;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.4);
    }

    @media (prefers-color-scheme: dark) {
        .hero-section {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.16), rgba(8, 12, 40, 0.8));
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
    }

    .hero-section::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at top right, rgba(255, 255, 255, 0.2) 0, transparent 55%);
        opacity: 0.35;
        pointer-events: none;
    }

    .hero-title {
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 4px;
        color: var(--text-primary);
    }

    .hero-subtitle {
        font-size: 14px;
        color: var(--text-secondary);
    }

    /* Stats */
    .stats-container {
        display: flex;
        gap: 14px;
        margin: 26px 0 32px;
        flex-wrap: wrap;
    }

    .stat-item {
        background: var(--bg-card);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px 18px;
        flex: 1 1 0;
        min-width: 150px;
        display: flex;
        flex-direction: column;
        gap: 2px;
        position: relative;
        color: var(--text-primary);
    }

    .stat-number {
        font-size: 22px;
        font-weight: 700;
    }

    .stat-label {
        font-size: 12px;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Case cards */
    .case-card {
        background: var(--bg-card);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 22px 22px;
        margin: 16px 0;
        position: relative;
        color: var(--text-primary);
    }

    .case-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 8px;
    }

    .case-id {
        font-size: 16px;
        color: var(--accent-primary);
        font-weight: 700;
    }

    .case-meta {
        color: var(--text-secondary);
        font-size: 13px;
        margin-top: 4px;
    }

    .case-status {
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }

    .status-pending {
        background: rgba(234, 179, 8, 0.12);
        color: var(--warning);
        border: 1px solid rgba(234, 179, 8, 0.5);
    }

    .status-under-review {
        background: rgba(37, 99, 235, 0.12);
        color: var(--info);
        border: 1px solid rgba(37, 99, 235, 0.5);
    }

    .status-approved {
        background: rgba(34, 197, 94, 0.14);
        color: var(--success);
        border: 1px solid rgba(34, 197, 94, 0.55);
    }

    .status-rejected {
        background: rgba(239, 68, 68, 0.14);
        color: var(--danger);
        border: 1px solid rgba(239, 68, 68, 0.55);
    }

    .case-detail {
        color: var(--text-secondary);
        font-size: 14px;
        margin: 6px 0;
    }

    .case-detail strong {
        color: var(--text-primary);
    }

    .empty-state {
        text-align: center;
        padding: 48px 20px;
        background: var(--bg-card);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border);
        border-radius: 18px;
        margin: 16px 0;
        color: var(--text-primary);
    }

    .empty-icon {
        font-size: 48px;
        margin-bottom: 14px;
        opacity: 0.5;
    }

    .empty-title {
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 6px;
    }

    .empty-text {
        color: var(--text-secondary);
        font-size: 14px;
    }

    .section-title {
        font-size: 24px;
        font-weight: 700;
        margin: 24px 0 14px;
        color: var(--text-primary);
    }

    /* DataFrames */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }

    .stFormSubmitButton {
        width: 100%;
    }

    .stForm {
        width: 100%;
    }

    /* AI evaluation actions: put buttons side-by-side with natural width */
    .ai-actions .stButton > button {
        width: auto !important;
        min-width: 170px;
        padding-left: 24px !important;
        padding-right: 24px !important;
    }

    .ai-actions [data-testid="column"] {
        display: flex;
        justify-content: flex-start;
    }
</style>
""",
        unsafe_allow_html=True,
    )


# AI evaluation state (inline, per-case)
if "ai_modal_case_id" not in st.session_state:
    st.session_state.ai_modal_case_id = None
if "ai_modal_result" not in st.session_state:
    st.session_state.ai_modal_result = None

# Session state defaults
ADMIN_CREDENTIALS = {"1": "1"}

defaults = {
    "admin_auth": False,
    "admin_user": None,
    "admin_login_attempts": 0,
    "admin_lock_until": None,
    "expanded_case": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# API helpers
def fetch_all_cases(timeout: int = 6) -> dict:
    try:
        response = requests.get(ALL_CASES_URL, timeout=timeout)
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "body": response.json() if response.ok else response.text,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def update_case_status(case_id: str, status: str, timeout: int = 6) -> dict:
    try:
        response = requests.patch(
            UPDATE_STATUS_URL.format(case_id=case_id),
            json={"status": status},
            timeout=timeout,
        )
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "body": response.json() if response.ok else response.text,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def evaluate_with_ai(case_id: str, timeout: int = 6) -> dict:
    """Call the /health endpoint as a placeholder for the advisor service."""
    try:
        time.sleep(5)  # Simulate processing delay
        response = requests.get(HEALTH_URL, timeout=timeout)
        body = response.json() if "application/json" in response.headers.get("content-type", "") else response.text
        return {"ok": response.ok, "status_code": response.status_code, "body": body}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Demo fallback
DEMO_CASES: list[dict] = []


# Authentication helpers
def is_locked_out() -> bool:
    if st.session_state.admin_lock_until is None:
        return False
    return datetime.now() < st.session_state.admin_lock_until


def render_login() -> None:
    inject_production_css()

    st.markdown(
        """
<div class="login-hero-bar">
    <div class="login-hero-brand">
        <div class="login-hero-logo">🎓</div>
        <div>Technical University of Germany</div>
    </div>
    <div class="login-hero-env">Control Center • Internal</div>
</div>
""",
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.4, 1])

    with col_left:
        st.markdown(
            """
<div>
  <div class="login-copy-title">
    Keep every <span>course request</span><br/>on a short leash.
  </div>
  <div class="login-copy-subtitle">
    Review student course combinations, approve or reject cases,
    and keep the semester running smoothly, all from one place.
  </div>

  <div class="login-feature-row">
    <div class="login-feature-pill">
      <span class="login-feature-dot"></span>
      Real-time case overview
    </div>
    <div class="login-feature-pill">
      ⚡ One-click approvals
    </div>
    <div class="login-feature-pill">
      🔐 Restricted to admins
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            """
<div class="login-card-shell">
  <div class="login-card">
    <div class="login-card-heading">Sign in to continue</div>
    <div class="login-card-sub">Use your admin credentials to access the dashboard.</div>
    <div class="login-demo-pill">
      Demo access
      <code>user: 1</code>
      <code>pass: 1</code>
    </div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        if is_locked_out():
            unlock_time = st.session_state.admin_lock_until.strftime("%H:%M:%S")
            st.error(f"Too many attempts. Try again at {unlock_time}")
            st.markdown(
                """
    <div class="login-legal-text">
      Login is temporarily locked for security reasons.
    </div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.stop()

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter username", key="user")
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password",
                key="pass",
            )
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            submitted = st.form_submit_button("Sign in")

            if submitted:
                if ADMIN_CREDENTIALS.get(username) == password:
                    st.session_state.admin_auth = True
                    st.session_state.admin_user = username
                    st.session_state.admin_login_attempts = 0
                    st.success("✅ Welcome back.")
                    st.rerun()
                else:
                    st.session_state.admin_login_attempts += 1
                    if st.session_state.admin_login_attempts >= 5:
                        st.session_state.admin_lock_until = datetime.now() + timedelta(minutes=5)
                        st.error("🔒 Account locked for 5 minutes")
                    else:
                        remaining = 5 - st.session_state.admin_login_attempts
                        st.error(f"❌ Invalid credentials ({remaining} attempts left)")

        st.markdown(
            """
    <div class="login-legal-text">
      By continuing you confirm that you are an authorized administrator
      and agree to internal usage policies.
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )


# Main app
inject_production_css()

if not st.session_state.admin_auth:
    render_login()
    st.stop()

with st.sidebar:
    st.markdown("### 👤 Account")
    st.markdown(f"**{st.session_state.admin_user}**")
    if st.button("🚪 Sign out"):
        st.session_state.admin_auth = False
        st.session_state.admin_user = None
        st.session_state.expanded_case = None
        st.session_state.ai_modal_case_id = None
        st.session_state.ai_modal_result = None
        st.rerun()

st.markdown(
    """
<div class="hero-section">
    <div class="hero-title">KursKraft: Admin Dashboard</div>
    <div class="hero-subtitle">Manage course approval requests efficiently</div>
</div>
""",
    unsafe_allow_html=True,
)

api_response = fetch_all_cases()
if api_response.get("ok") and api_response.get("body"):
    all_cases = api_response["body"]
else:
    st.info("📡 Using demo data. Connect to API endpoint for live cases.")
    all_cases = DEMO_CASES

# Stats
total = len(all_cases)
pending = len([c for c in all_cases if c["status"] == "Pending"])
reviewing = len([c for c in all_cases if c["status"] == "Under Review"])
approved = len([c for c in all_cases if c["status"] == "Approved"])
rejected = len([c for c in all_cases if c["status"] == "Rejected"])

stats_html = '<div class="stats-container">'
for value, label in [
    (total, "Total Cases"),
    (pending, "Pending"),
    (reviewing, "Under Review"),
    (approved, "Approved"),
    (rejected, "Rejected"),
]:
    stats_html += f"""
  <div class="stat-item">
    <div class="stat-number">{value}</div>
    <div class="stat-label">{label}</div>
  </div>
"""
stats_html += "</div>"
st.markdown(stats_html, unsafe_allow_html=True)

# Filters
filter_col = st.container()
with filter_col:
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "Pending", "Under Review", "Approved", "Rejected"],
            key="sf",
        )

    with col2:
        semesters = ["All"] + sorted({c["semester"] for c in all_cases})
        semester_filter = st.selectbox("Semester", semesters, key="semf")

    with col3:
        search_query = st.text_input(
            "Search",
            placeholder="Case ID or student...",
            key="search",
        )

filtered_cases = all_cases
if status_filter != "All":
    filtered_cases = [c for c in filtered_cases if c["status"] == status_filter]
if semester_filter != "All":
    filtered_cases = [c for c in filtered_cases if c["semester"] == semester_filter]
if search_query:
    q = search_query.lower()
    filtered_cases = [c for c in filtered_cases if q in c["case_id"].lower() or q in c["student_name"].lower()]

st.markdown(
    f'<div class="section-title">📁 Cases ({len(filtered_cases)})</div>',
    unsafe_allow_html=True,
)

if not filtered_cases:
    st.markdown(
        """
<div class="empty-state">
    <div class="empty-icon">🔍</div>
    <div class="empty-title">No cases found</div>
    <div class="empty-text">Try adjusting your filters</div>
</div>
""",
        unsafe_allow_html=True,
    )
else:
    for case in filtered_cases:
        status_class = case["status"].lower().replace(" ", "-")
        case_key = case["case_id"]
        is_expanded = st.session_state.expanded_case == case_key

        st.markdown(
            f"""
<div class="case-card">
  <div class="case-header">
    <div>
      <div class="case-id">📄 {case['case_id']}</div>
      <div class="case-meta">
        👤 {case['student_name']} • ID: {case['student_id']} •
        📚 {case['total_courses']} courses ({case['total_credits']} credits) •
        🎓 {case['major']}
      </div>
    </div>
    <div class="case-status status-{status_class}">{case['status']}</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
        if st.button(
            "View Details" if not is_expanded else "Hide Details",
            key=f"tog_{case_key}",
            use_container_width=True,
        ):
            st.session_state.expanded_case = case_key if not is_expanded else None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        if is_expanded:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div class="case-detail"><strong>Semester:</strong> {case["semester"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="case-detail"><strong>Major:</strong> {case["major"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    (
                        f'<div class="case-detail"><strong>Total Courses:</strong> '
                        f'{case["total_courses"]} ({case["total_credits"]} credits)</div>'
                    ),
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f'<div class="case-detail"><strong>Minor:</strong> {case["minor"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="case-detail"><strong>Submitted:</strong> {case["submitted_date"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="case-detail"><strong>Last Updated:</strong> {case["last_updated"]}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**📖 Enrolled Courses**")
            courses_df = pd.DataFrame(case["courses"])
            st.dataframe(courses_df, hide_index=True, use_container_width=True)

            if case.get("notes"):
                st.info(f"**Notes:** {case['notes']}")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Actions**")

            col1, col2, col3 = st.columns(3)

            # Approve
            with col1:
                st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                if st.button("✅ Approve", key=f"app_{case_key}", use_container_width=True):
                    with st.spinner("Approving..."):
                        result = update_case_status(case["case_id"], "Approved")
                    if result.get("ok"):
                        st.success(f"✅ Case {case['case_id']} approved!")
                        st.balloons()
                        st.rerun()
                    else:
                        error_text = (
                            result.get("body")
                            if isinstance(result.get("body"), str)
                            else result.get("error", "Unknown error")
                        )

                        st.error(f"❌ Failed: {error_text}")
                st.markdown("</div>", unsafe_allow_html=True)

            # Reject
            with col2:
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                if st.button("❌ Reject", key=f"rej_{case_key}", use_container_width=True):
                    with st.spinner("Rejecting..."):
                        result = update_case_status(case["case_id"], "Rejected")
                    if result.get("ok"):
                        st.warning(f"⚠️ Case {case['case_id']} rejected")
                        st.rerun()
                    else:
                        error_text = (
                            result.get("body")
                            if isinstance(result.get("body"), str)
                            else result.get("error", "Unknown error")
                        )

                    st.error(f"❌ Failed: {error_text}")
                st.markdown("</div>", unsafe_allow_html=True)

            # AI Evaluate
            with col3:
                st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
                if st.button("🤖 AI Evaluate", key=f"ai_{case_key}", use_container_width=True):
                    with st.spinner("Evaluating..."):
                        result = evaluate_with_ai(case["case_id"])

                    st.session_state.ai_modal_case_id = case["case_id"]
                    st.session_state.ai_modal_result = result
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # Inline AI evaluation result (only for this case)
            if st.session_state.ai_modal_case_id == case_key and st.session_state.ai_modal_result is not None:
                st.markdown("### 🤖 AI Evaluation Result")

                result = st.session_state.ai_modal_result
                if result.get("ok"):
                    body = result.get("body")
                    if isinstance(body, (dict, list)):
                        st.json(body)
                    else:
                        st.write(body)
                else:
                    st.error(result.get("error") or result.get("body") or "Unknown error")

                st.markdown("---")
                st.markdown("### ✏️ Enter Evaluation Scores")

                default_scores = "{'alignment_score': 0, 'scheduling_score': 0, 'workload_score': 0}"

                scores_input = st.text_area(
                    "AI Evaluation Details:",
                    value=default_scores,
                    key=f"ai_scores_{case_key}",
                    height=120,
                    help="Enter evaluation scores in Python dict or JSON format.",
                )

                # Button row with special CSS wrapper so they sit side by side
                st.markdown('<div class="ai-actions">', unsafe_allow_html=True)
                colA, colB = st.columns([1, 1])

                # Submit Evaluation
                with colA:
                    if st.button("💾 Submit Evaluation", key=f"save_eval_{case_key}"):
                        try:
                            # Safely parse the text into a Python dict
                            scores_dict = ast.literal_eval(scores_input)

                            alignment = scores_dict.get("alignment_score")
                            scheduling = scores_dict.get("scheduling_score")
                            workload = scores_dict.get("workload_score")

                            if not all(isinstance(x, (int, float)) for x in [alignment, scheduling, workload]):
                                st.error(
                                    "Please provide numeric values for "
                                    "'alignment_score', 'scheduling_score', and 'workload_score'."
                                )
                            else:
                                # Decision logic
                                if alignment > 70 and scheduling > 70 and workload > 70:
                                    decision_payload = {"decision": "Green"}
                                else:
                                    decision_payload = {"decision": "Red"}

                                # Update the AI result box with the decision
                                time.sleep(5)
                                st.session_state.ai_modal_result = {
                                    "ok": True,
                                    "body": decision_payload,
                                }

                                st.success("AI Evaluation updated.")
                                st.rerun()

                        except Exception as e:
                            st.error(f"Could not parse evaluation scores: {e}")

                # Clear AI result
                with colB:
                    if st.button("Clear AI Result", key=f"clear_ai_{case_key}"):
                        st.session_state.ai_modal_case_id = None
                        st.session_state.ai_modal_result = None
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

footer_html = """
<div style="
    text-align: center;
    padding: 40px 20px;
    color: #808080;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    margin-top: 80px;
">
    <p>© 2025 Technical University of Germany. All rights reserved.</p>
    <p style="margin-top: 10px; font-size: 14px;">Built with 💜 for grades.</p>
</div>
"""

st.markdown(footer_html, unsafe_allow_html=True)
