"""
GLUCOVISION AI
AI-Powered Personalized Diabetes Monitoring & Glucose Prediction System
Educational Prototype Only - Not a Medical Device
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io
import math
import hashlib
import hmac
import json
import secrets
from pathlib import Path
import random
from collections import defaultdict
genai.configure(api_key="AQ.Ab8RN6K9MlT9BIPsEAIPmkmzMayTbyf7NxKvMpHM0GtcKWzk7w")

model = genai.GenerativeModel("gemini-2.5-flash")

# ─── ACCOUNT SYSTEM (freemium: free vs premium) ────────────────────────────────
# NOTE: This is a lightweight local JSON "database" suitable for a prototype /
# science-fair demo. It is NOT production-grade security (no HTTPS enforcement,
# no rate limiting, no email verification). Passwords are salted + hashed with
# PBKDF2 before storage — the plaintext password itself is never saved.
USERS_DB_PATH = Path(__file__).parent / "glucovision_users.json"


def _load_users() -> dict:
    if USERS_DB_PATH.exists():
        try:
            with open(USERS_DB_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_users(users: dict) -> None:
    with open(USERS_DB_PATH, "w") as f:
        json.dump(users, f, indent=2, default=str)


def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return pwd_hash, salt


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    test_hash, _ = _hash_password(password, salt)
    return hmac.compare_digest(test_hash, stored_hash)


def account_exists(username: str) -> bool:
    return username.strip().lower() in _load_users()


def create_account(username: str, email: str, password: str) -> tuple[bool, str]:
    """Create a new free-tier account and persist every field the sign-up
    form collected (username, email, hashed credentials, timestamps)."""
    users = _load_users()
    key = username.strip().lower()
    if not key or not password:
        return False, "Username and password are required."
    if key in users:
        return False, "That username is already taken."
    pwd_hash, salt = _hash_password(password)
    users[key] = {
        "username": username.strip(),
        "email": email.strip(),
        "password_hash": pwd_hash,
        "salt": salt,
        "premium": False,
        "created_at": datetime.now().isoformat(),
        "last_login": None,
        "profile": {},          # patient-profile data, saved separately once entered
    }
    _save_users(users)
    return True, "Account created! You can now log in."


def authenticate(username: str, password: str) -> tuple[bool, str]:
    users = _load_users()
    key = username.strip().lower()
    if key not in users:
        return False, "No account found with that username."
    record = users[key]
    if not _verify_password(password, record["salt"], record["password_hash"]):
        return False, "Incorrect password."
    record["last_login"] = datetime.now().isoformat()
    users[key] = record
    _save_users(users)
    return True, "Welcome back!"


def get_user_record(username: str) -> dict:
    return _load_users().get(username.strip().lower(), {})


def update_user_record(user_key: str, updates: dict) -> None:
    users = _load_users()
    if user_key in users:
        users[user_key].update(updates)
        _save_users(users)


def set_premium(user_key: str, value: bool) -> None:
    update_user_record(user_key, {"premium": value})


def render_auth_page():
    """Login / sign-up gate shown before any part of the app is accessible."""
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title">🩺 GlucoVision AI</div>
        <div class="hero-subtitle">Sign in to your account to continue</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="disclaimer">
        ⚠️ <strong>EDUCATIONAL PROTOTYPE ONLY.</strong>
        Accounts on this demo are stored locally and are NOT suitable for real
        medical or personally identifiable data.
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔑 Log In", "📝 Sign Up"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log In", use_container_width=True)
        if submitted:
            ok, msg = authenticate(username, password)
            if ok:
                record = get_user_record(username)
                st.session_state.authenticated = True
                st.session_state.user_key      = username.strip().lower()
                st.session_state.username      = record["username"]
                st.session_state.premium       = record.get("premium", False)
                st.session_state.profile       = record.get("profile", {}) or {}
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with tab_signup:
        st.caption("Free to join — you can upgrade to Premium any time after signing up.")
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username", key="signup_username")
            new_email    = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Choose a Password", type="password", key="signup_password")
            confirm_pw   = st.text_input("Confirm Password", type="password", key="signup_confirm")
            submitted2   = st.form_submit_button("Create Account", use_container_width=True)
        if submitted2:
            if not new_username.strip():
                st.error("Please choose a username.")
            elif new_password != confirm_pw:
                st.error("Passwords do not match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, msg = create_account(new_username, new_email, new_password)
                if ok:
                    st.success(msg + " Switch to the 🔑 Log In tab to continue.")
                else:
                    st.error(msg)


# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GlucoVision AI",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #ffffff;
}

/* Background - simple dark navy, no fancy gradient */
.stApp {
    background-color: #0d1117;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 2px solid #00d9ff;
}
section[data-testid="stSidebar"] .block-container { padding: 1rem; }

/* All labels and text - bright white, bold */
label, .stTextInput label, .stNumberInput label,
.stSelectbox label, .stSlider label, .stMultiSelect label {
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
}

p, .stMarkdown p {
    color: #e6edf3 !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}

/* Metric cards - solid borders, bright values */
.metric-card {
    background-color: #161b22;
    border: 2px solid #00d9ff;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
.metric-value {
    font-size: 1.9rem;
    font-weight: 800;
    color: #00d9ff;
    line-height: 1.2;
}
.metric-label {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #c9d1d9;
    margin-top: 0.3rem;
}
.metric-icon { font-size: 1.3rem; margin-bottom: 0.25rem; }

/* Section headers - each section gets its own bright color, not one matching brand color */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 1.2rem;
    padding-bottom: 0.6rem;
    border-bottom: 3px solid #00d9ff;
}
.section-icon {
    width: 36px; height: 36px;
    background-color: #00d9ff;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
}
.section-title {
    font-size: 1.1rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.02em;
}
/* Color variants - cycled across the 10 sections so it doesn't look like one matched brand palette */
.sh-blue   { border-bottom-color: #1e90ff; }
.sh-blue   .section-icon { background-color: #1e90ff; }
.sh-green  { border-bottom-color: #00e676; }
.sh-green  .section-icon { background-color: #00e676; }
.sh-orange { border-bottom-color: #ff9100; }
.sh-orange .section-icon { background-color: #ff9100; }
.sh-pink   { border-bottom-color: #ff2d95; }
.sh-pink   .section-icon { background-color: #ff2d95; }
.sh-purple { border-bottom-color: #a855f7; }
.sh-purple .section-icon { background-color: #a855f7; }
.sh-yellow { border-bottom-color: #ffd60a; }
.sh-yellow .section-icon { background-color: #ffd60a; }
.sh-red    { border-bottom-color: #ff3b3b; }
.sh-red    .section-icon { background-color: #ff3b3b; }
.sh-teal   { border-bottom-color: #00ffc8; }
.sh-teal   .section-icon { background-color: #00ffc8; }

/* Hero header */
.hero-header {
    text-align: center;
    padding: 1.8rem 1rem;
    background-color: #161b22;
    border-radius: 12px;
    border: 3px solid #00e676;
    margin-bottom: 1.5rem;
}
.hero-title {
    font-size: 2.7rem;
    font-weight: 800;
    color: #00d9ff;
    margin: 0;
    letter-spacing: -0.01em;
}
.hero-subtitle {
    font-size: 0.95rem;
    color: #c9d1d9;
    margin: 0.5rem 0 0;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* Disclaimer */
.disclaimer {
    background-color: #3d0a0a;
    border: 3px solid #ff3b3b;
    border-radius: 8px;
    padding: 0.8rem 1.2rem;
    margin-bottom: 1.5rem;
    font-size: 0.85rem;
    font-weight: 700;
    color: #ff8080;
}

/* Risk badges */
.risk-low   { color: #00e676; background: #0a2e1a; border: 2px solid #00e676; border-radius:6px; padding:3px 10px; font-size:0.85rem; font-weight:800; }
.risk-medium{ color: #ffd60a; background: #332700; border: 2px solid #ffd60a; border-radius:6px; padding:3px 10px; font-size:0.85rem; font-weight:800; }
.risk-high  { color: #ff3b3b; background: #3d0a0a; border: 2px solid #ff3b3b; border-radius:6px; padding:3px 10px; font-size:0.85rem; font-weight:800; }

/* Streamlit widget overrides */
.stSelectbox > div > div {
    background-color: #161b22 !important;
    border: 2px solid #30363d !important;
    color: #ffffff !important;
}
.stNumberInput > div > div > input {
    background-color: #161b22 !important;
    border: 2px solid #30363d !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}
.stTextInput > div > div > input {
    background-color: #161b22 !important;
    border: 2px solid #30363d !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}
div[data-testid="metric-container"] {
    background-color: #161b22;
    border: 2px solid #30363d;
    border-radius: 8px;
    padding: 0.5rem 1rem;
}
div[data-testid="metric-container"] label {
    color: #c9d1d9 !important;
    font-weight: 700 !important;
}
div[data-testid="metric-container"] [data-testid="metric-value"] {
    color: #00d9ff !important;
    font-weight: 800 !important;
}
.stButton > button {
    background-color: #00e676 !important;
    color: #0d1117 !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 800 !important;
    font-size: 0.95rem !important;
    padding: 0.5rem 1.5rem !important;
}
.stButton > button:hover {
    background-color: #5cffb0 !important;
}
hr { border-color: #30363d !important; border-width: 1px !important; }

/* Sidebar logo */
.sidebar-logo {
    text-align: center;
    padding: 1rem 0 1.5rem;
    border-bottom: 2px solid #00d9ff;
    margin-bottom: 1.5rem;
}
.sidebar-logo-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #00d9ff;
}
.sidebar-logo-sub {
    font-size: 0.7rem;
    color: #8b949e;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* Nav pills */
.nav-pill {
    display: block;
    padding: 0.5rem 1rem;
    margin: 0.2rem 0;
    border-radius: 6px;
    color: #c9d1d9;
    font-size: 0.88rem;
    font-weight: 700;
    cursor: pointer;
}
.nav-pill:hover { background-color: #21262d; color: #ffffff; }

/* Recommendation cards */
.rec-card {
    background-color: #161b22;
    border: 2px solid #30363d;
    border-left: 5px solid #00d9ff;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.8rem;
    font-size: 0.9rem;
    font-weight: 700;
    color: #e6edf3;
}
.rec-card.rc-0 { border-left-color: #00d9ff; }
.rec-card.rc-1 { border-left-color: #00e676; }
.rec-card.rc-2 { border-left-color: #ffd60a; }
.rec-card.rc-3 { border-left-color: #ff9100; }
.rec-card.rc-4 { border-left-color: #ff2d95; }
.rec-card.rc-5 { border-left-color: #a855f7; }
.rec-card.rc-6 { border-left-color: #1e90ff; }

/* Insight box */
.insight-box {
    background-color: #161b22;
    border: 2px solid #00d9ff;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.insight-value {
    font-size: 2rem;
    font-weight: 800;
    color: #00d9ff;
}

/* Glass card (used in export section) */
.glass-card {
    background-color: #161b22;
    border: 2px solid #30363d;
    border-radius: 10px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}
.glass-card strong { color: #00d9ff; }
</style>
""", unsafe_allow_html=True)

# ─── FOOD DATABASE ─────────────────────────────────────────────────────────────
FOOD_DB = {
    "Cooked Rice (white) (100 g)": {"calories": 130.0, "carbs": 28.0, "protein": 2.7, "fat": 0.3},
    "Wheat Roti / Chapati (1 medium (40 g))": {"calories": 104.0, "carbs": 20.0, "protein": 3.0, "fat": 1.7},
    "Whole Wheat Flour (Atta) (100 g (raw))": {"calories": 341.0, "carbs": 72.0, "protein": 12.0, "fat": 1.7},
    "Basmati Rice (cooked) (100 g)": {"calories": 121.0, "carbs": 25.0, "protein": 2.7, "fat": 0.4},
    "Idli (2 pieces (~70 g))": {"calories": 78.0, "carbs": 16.0, "protein": 2.5, "fat": 0.4},
    "Dosa (plain) (1 medium (~80 g))": {"calories": 168.0, "carbs": 28.0, "protein": 3.9, "fat": 3.7},
    "Poha (flattened rice) (1 bowl (150 g cooked))": {"calories": 180.0, "carbs": 38.0, "protein": 3.6, "fat": 1.8},
    "Upma (semolina) (1 bowl (150 g cooked))": {"calories": 200.0, "carbs": 32.0, "protein": 4.5, "fat": 6.0},
    "Paratha (plain, with oil) (1 medium (60 g))": {"calories": 210.0, "carbs": 27.0, "protein": 4.0, "fat": 9.0},
    "Puri (1 piece (25 g))": {"calories": 101.0, "carbs": 11.0, "protein": 1.7, "fat": 5.5},
    "Toor / Arhar Dal (cooked) (1 bowl (150 g))": {"calories": 170.0, "carbs": 28.0, "protein": 10.5, "fat": 1.5},
    "Moong Dal (cooked) (1 bowl (150 g))": {"calories": 150.0, "carbs": 25.0, "protein": 10.0, "fat": 0.6},
    "Chana Dal (cooked) (1 bowl (150 g))": {"calories": 210.0, "carbs": 34.0, "protein": 12.0, "fat": 3.0},
    "Rajma (Kidney Beans, cooked) (1 bowl (150 g))": {"calories": 165.0, "carbs": 30.0, "protein": 10.5, "fat": 0.6},
    "Chole (Chickpeas, cooked) (1 bowl (150 g))": {"calories": 210.0, "carbs": 34.0, "protein": 11.0, "fat": 3.0},
    "Paneer (100 g)": {"calories": 265.0, "carbs": 1.2, "protein": 18.3, "fat": 20.8},
    "Curd / Yogurt (Dahi) (100 g)": {"calories": 60.0, "carbs": 4.7, "protein": 3.5, "fat": 3.3},
    "Milk (whole/full cream) (1 glass (200 ml))": {"calories": 134.0, "carbs": 9.6, "protein": 6.4, "fat": 8.0},
    "Buttermilk (Chaas) (1 glass (200 ml))": {"calories": 40.0, "carbs": 3.6, "protein": 2.0, "fat": 1.8},
    "Ghee (1 tsp (5 g))": {"calories": 45.0, "carbs": 0.0, "protein": 0.0, "fat": 5.0},
    "Butter (1 tsp (5 g))": {"calories": 36.0, "carbs": 0.0, "protein": 0.0, "fat": 4.1},
    "Egg (whole, boiled) (1 large (50 g))": {"calories": 78.0, "carbs": 0.6, "protein": 6.3, "fat": 5.3},
    "Chicken (cooked, breast) (100 g)": {"calories": 165.0, "carbs": 0.0, "protein": 31.0, "fat": 3.6},
    "Mutton (cooked) (100 g)": {"calories": 250.0, "carbs": 0.0, "protein": 25.0, "fat": 16.0},
    "Fish (Rohu, cooked) (100 g)": {"calories": 105.0, "carbs": 0.0, "protein": 20.0, "fat": 2.4},
    "Potato (boiled) (100 g)": {"calories": 87.0, "carbs": 20.0, "protein": 1.9, "fat": 0.1},
    "Onion (raw) (100 g)": {"calories": 40.0, "carbs": 9.3, "protein": 1.1, "fat": 0.1},
    "Tomato (raw) (100 g)": {"calories": 18.0, "carbs": 3.9, "protein": 0.9, "fat": 0.2},
    "Spinach / Palak (cooked) (100 g)": {"calories": 23.0, "carbs": 3.6, "protein": 2.9, "fat": 0.4},
    "Cauliflower (cooked) (100 g)": {"calories": 25.0, "carbs": 5.0, "protein": 1.8, "fat": 0.3},
    "Bhindi / Okra (cooked) (100 g)": {"calories": 35.0, "carbs": 7.5, "protein": 2.0, "fat": 0.2},
    "Brinjal / Baingan (cooked) (100 g)": {"calories": 25.0, "carbs": 5.9, "protein": 1.0, "fat": 0.2},
    "Green Peas (cooked) (100 g)": {"calories": 84.0, "carbs": 14.5, "protein": 5.4, "fat": 0.4},
    "Carrot (raw) (100 g)": {"calories": 41.0, "carbs": 9.6, "protein": 0.9, "fat": 0.2},
    "Cucumber (raw) (100 g)": {"calories": 15.0, "carbs": 3.6, "protein": 0.7, "fat": 0.1},
    "Banana (1 medium (120 g))": {"calories": 105.0, "carbs": 27.0, "protein": 1.3, "fat": 0.4},
    "Apple (1 medium (150 g))": {"calories": 78.0, "carbs": 21.0, "protein": 0.4, "fat": 0.3},
    "Mango (1 medium (200 g))": {"calories": 120.0, "carbs": 30.0, "protein": 1.6, "fat": 0.6},
    "Papaya (100 g)": {"calories": 43.0, "carbs": 11.0, "protein": 0.5, "fat": 0.3},
    "Orange (1 medium (130 g))": {"calories": 62.0, "carbs": 15.5, "protein": 1.2, "fat": 0.2},
    "Peanuts (roasted) (30 g (handful))": {"calories": 170.0, "carbs": 6.0, "protein": 7.7, "fat": 14.5},
    "Almonds (10 pieces (12 g))": {"calories": 70.0, "carbs": 2.6, "protein": 2.6, "fat": 6.0},
    "Cashews (10 pieces (15 g))": {"calories": 87.0, "carbs": 4.9, "protein": 2.8, "fat": 7.0},
    "Coconut (fresh) (30 g piece)": {"calories": 106.0, "carbs": 4.6, "protein": 1.0, "fat": 10.1},
    "Tea (with milk & sugar) (1 cup (150 ml))": {"calories": 55.0, "carbs": 8.5, "protein": 1.2, "fat": 1.8},
    "Coffee (with milk & sugar) (1 cup (150 ml))": {"calories": 60.0, "carbs": 9.0, "protein": 1.5, "fat": 1.8},
    "Sugar (1 tsp (5 g))": {"calories": 19.0, "carbs": 5.0, "protein": 0.0, "fat": 0.0},
    "Jaggery (Gur) (1 tsp (5 g))": {"calories": 19.0, "carbs": 4.8, "protein": 0.0, "fat": 0.0},
    "Samosa (1 piece (60 g))": {"calories": 260.0, "carbs": 24.0, "protein": 3.5, "fat": 17.0},
    "Glucose Biscuits (4 biscuits (25 g))": {"calories": 110.0, "carbs": 19.0, "protein": 1.7, "fat": 3.2},
    "Aloo Gobi (1 bowl (150 g))": {"calories": 150.0, "carbs": 18.0, "protein": 3.5, "fat": 7.0},
    "Baingan Bharta (1 bowl (150 g))": {"calories": 130.0, "carbs": 12.0, "protein": 2.5, "fat": 8.0},
    "Palak Paneer (1 bowl (150 g))": {"calories": 220.0, "carbs": 8.0, "protein": 9.0, "fat": 16.0},
    "Matar Paneer (1 bowl (150 g))": {"calories": 230.0, "carbs": 12.0, "protein": 10.0, "fat": 15.0},
    "Bhindi Masala (1 bowl (150 g))": {"calories": 140.0, "carbs": 10.0, "protein": 3.0, "fat": 9.0},
    "Dum Aloo (1 bowl (150 g))": {"calories": 200.0, "carbs": 20.0, "protein": 3.0, "fat": 12.0},
    "Aloo Methi (1 bowl (150 g))": {"calories": 160.0, "carbs": 17.0, "protein": 3.5, "fat": 8.0},
    "Lauki Sabzi (Bottle Gourd) (1 bowl (150 g))": {"calories": 90.0, "carbs": 10.0, "protein": 2.0, "fat": 4.0},
    "Kaddu Sabzi (Pumpkin) (1 bowl (150 g))": {"calories": 95.0, "carbs": 12.0, "protein": 2.0, "fat": 4.0},
    "Karela Sabzi (Bitter Gourd) (1 bowl (150 g))": {"calories": 110.0, "carbs": 9.0, "protein": 2.5, "fat": 7.0},
    "Gajar Matar (Carrot Peas) (1 bowl (150 g))": {"calories": 120.0, "carbs": 15.0, "protein": 4.0, "fat": 4.0},
    "Cabbage Sabzi (1 bowl (150 g))": {"calories": 100.0, "carbs": 11.0, "protein": 2.5, "fat": 5.0},
    "Mixed Vegetable Curry (1 bowl (150 g))": {"calories": 150.0, "carbs": 15.0, "protein": 4.0, "fat": 8.0},
    "Kofta Curry (2 kofta + gravy (150 g))": {"calories": 260.0, "carbs": 18.0, "protein": 6.0, "fat": 18.0},
    "Butter Chicken (1 bowl (200 g))": {"calories": 350.0, "carbs": 10.0, "protein": 20.0, "fat": 25.0},
    "Chicken Tikka Masala (1 bowl (200 g))": {"calories": 320.0, "carbs": 10.0, "protein": 24.0, "fat": 20.0},
    "Egg Curry (2 eggs + gravy (200 g))": {"calories": 280.0, "carbs": 10.0, "protein": 14.0, "fat": 20.0},
    "Fish Curry (1 bowl (200 g))": {"calories": 220.0, "carbs": 6.0, "protein": 20.0, "fat": 13.0},
    "Prawn Curry (1 bowl (200 g))": {"calories": 200.0, "carbs": 6.0, "protein": 18.0, "fat": 12.0},
    "Mutton Rogan Josh (1 bowl (200 g))": {"calories": 350.0, "carbs": 8.0, "protein": 22.0, "fat": 25.0},
    "Naan (1 piece (90 g))": {"calories": 260.0, "carbs": 45.0, "protein": 7.0, "fat": 6.0},
    "Kulcha (1 piece (80 g))": {"calories": 230.0, "carbs": 38.0, "protein": 6.0, "fat": 6.0},
    "Bhatura (1 piece (80 g))": {"calories": 280.0, "carbs": 35.0, "protein": 6.0, "fat": 13.0},
    "Missi Roti (1 piece (50 g))": {"calories": 120.0, "carbs": 20.0, "protein": 4.0, "fat": 3.0},
    "Thepla (1 piece (40 g))": {"calories": 110.0, "carbs": 15.0, "protein": 3.0, "fat": 4.0},
    "Chicken Biryani (1 plate (250 g))": {"calories": 450.0, "carbs": 55.0, "protein": 20.0, "fat": 15.0},
    "Veg Pulao (1 plate (200 g))": {"calories": 300.0, "carbs": 50.0, "protein": 6.0, "fat": 8.0},
    "Curd Rice (1 bowl (200 g))": {"calories": 220.0, "carbs": 35.0, "protein": 6.0, "fat": 5.0},
    "Lemon Rice (1 bowl (200 g))": {"calories": 250.0, "carbs": 40.0, "protein": 5.0, "fat": 8.0},
    "Khichdi (1 bowl (200 g))": {"calories": 220.0, "carbs": 35.0, "protein": 7.0, "fat": 5.0},
    "Jeera Rice (1 bowl (150 g))": {"calories": 220.0, "carbs": 38.0, "protein": 4.0, "fat": 5.0},
    "Sambar (1 bowl (200 g))": {"calories": 150.0, "carbs": 20.0, "protein": 6.0, "fat": 4.0},
    "Rasam (1 bowl (150 g))": {"calories": 60.0, "carbs": 8.0, "protein": 2.0, "fat": 2.0},
    "Uttapam (1 piece (100 g))": {"calories": 160.0, "carbs": 25.0, "protein": 4.0, "fat": 5.0},
    "Medu Vada (2 pieces (80 g))": {"calories": 180.0, "carbs": 18.0, "protein": 5.0, "fat": 10.0},
    "Appam (1 piece (60 g))": {"calories": 120.0, "carbs": 22.0, "protein": 2.0, "fat": 2.0},
    "Mixed Vegetable Pakora (100 g)": {"calories": 280.0, "carbs": 25.0, "protein": 5.0, "fat": 18.0},
    "Kachori (1 piece (60 g))": {"calories": 220.0, "carbs": 25.0, "protein": 4.0, "fat": 12.0},
    "Dhokla (2 pieces (80 g))": {"calories": 160.0, "carbs": 25.0, "protein": 5.0, "fat": 4.0},
    "Vada Pav (1 piece (120 g))": {"calories": 290.0, "carbs": 40.0, "protein": 7.0, "fat": 11.0},
    "Pav Bhaji (1 plate (250 g))": {"calories": 400.0, "carbs": 50.0, "protein": 8.0, "fat": 18.0},
    "Bhel Puri (1 plate (140 g))": {"calories": 220.0, "carbs": 35.0, "protein": 5.0, "fat": 7.0},
    "Sev Puri (6 pieces (120 g))": {"calories": 280.0, "carbs": 35.0, "protein": 5.0, "fat": 13.0},
    "Aloo Tikki (2 pieces (100 g))": {"calories": 220.0, "carbs": 28.0, "protein": 4.0, "fat": 10.0},
    "Sprouts Salad (Moong) (100 g)": {"calories": 150.0, "carbs": 20.0, "protein": 9.0, "fat": 3.0},
    "Oats (cooked with milk) (1 bowl (200 g))": {"calories": 180.0, "carbs": 28.0, "protein": 7.0, "fat": 4.0},
    "Cornflakes with Milk (1 bowl (150 g))": {"calories": 180.0, "carbs": 32.0, "protein": 5.0, "fat": 3.0},
    "Gulab Jamun (2 pieces (80 g))": {"calories": 300.0, "carbs": 40.0, "protein": 4.0, "fat": 14.0},
    "Jalebi (100 g)": {"calories": 350.0, "carbs": 60.0, "protein": 2.0, "fat": 12.0},
    "Kheer (1 bowl (150 g))": {"calories": 230.0, "carbs": 35.0, "protein": 5.0, "fat": 8.0},
    "Quinoa (cooked) (100 g)": {"calories": 120.0, "carbs": 21.3, "protein": 4.4, "fat": 1.9},
"Barley (cooked) (100 g)": {"calories": 123.0, "carbs": 28.2, "protein": 2.3, "fat": 0.4},
"Pearl Millet / Bajra (cooked) (100 g)": {"calories": 119.0, "carbs": 23.7, "protein": 3.5, "fat": 1.0},
"Finger Millet / Ragi (cooked) (100 g)": {"calories": 119.0, "carbs": 24.0, "protein": 3.3, "fat": 1.3},
"Jowar (cooked) (100 g)": {"calories": 123.0, "carbs": 25.0, "protein": 3.8, "fat": 1.1},
"Foxtail Millet (cooked) (100 g)": {"calories": 119.0, "carbs": 23.5, "protein": 4.0, "fat": 1.2},
"Little Millet (cooked) (100 g)": {"calories": 114.0, "carbs": 22.0, "protein": 3.6, "fat": 0.8},
"Kodo Millet (cooked) (100 g)": {"calories": 112.0, "carbs": 21.8, "protein": 3.4, "fat": 0.8},
"Barnyard Millet (cooked) (100 g)": {"calories": 118.0, "carbs": 23.0, "protein": 3.8, "fat": 0.9},
"Broken Wheat / Dalia (cooked) (100 g)": {"calories": 83.0, "carbs": 18.6, "protein": 3.1, "fat": 0.2},

"Black Gram / Urad Dal (cooked) (100 g)": {"calories": 116.0, "carbs": 20.4, "protein": 8.9, "fat": 0.6},
"Masoor Dal (cooked) (100 g)": {"calories": 116.0, "carbs": 20.1, "protein": 9.0, "fat": 0.4},
"Black Chana (cooked) (100 g)": {"calories": 164.0, "carbs": 27.4, "protein": 8.9, "fat": 2.6},
"Soybeans (boiled) (100 g)": {"calories": 173.0, "carbs": 9.9, "protein": 18.2, "fat": 9.0},
"Tofu (firm) (100 g)": {"calories": 144.0, "carbs": 2.8, "protein": 17.3, "fat": 8.7},
"Tempeh (100 g)": {"calories": 193.0, "carbs": 9.4, "protein": 20.3, "fat": 10.8},

"Greek Yogurt (plain) (100 g)": {"calories": 59.0, "carbs": 3.6, "protein": 10.0, "fat": 0.4},
"Low Fat Milk (100 ml)": {"calories": 42.0, "carbs": 5.0, "protein": 3.4, "fat": 1.0},
"Skim Milk (100 ml)": {"calories": 34.0, "carbs": 5.0, "protein": 3.4, "fat": 0.1},
"Cheddar Cheese (100 g)": {"calories": 403.0, "carbs": 1.3, "protein": 24.9, "fat": 33.1},
"Mozzarella Cheese (100 g)": {"calories": 280.0, "carbs": 3.1, "protein": 28.0, "fat": 17.0},

"Turkey Breast (cooked) (100 g)": {"calories": 135.0, "carbs": 0.0, "protein": 29.0, "fat": 1.6},
"Duck (roasted) (100 g)": {"calories": 337.0, "carbs": 0.0, "protein": 19.0, "fat": 28.0},
"Chicken Liver (cooked) (100 g)": {"calories": 167.0, "carbs": 1.1, "protein": 24.5, "fat": 6.5},
"Tuna (cooked) (100 g)": {"calories": 132.0, "carbs": 0.0, "protein": 29.9, "fat": 0.6},
"Salmon (cooked) (100 g)": {"calories": 206.0, "carbs": 0.0, "protein": 22.1, "fat": 12.4},
"Sardines (100 g)": {"calories": 208.0, "carbs": 0.0, "protein": 24.6, "fat": 11.5},
"Crab (cooked) (100 g)": {"calories": 97.0, "carbs": 0.0, "protein": 20.1, "fat": 1.5},
"Shrimp (cooked) (100 g)": {"calories": 99.0, "carbs": 0.2, "protein": 24.0, "fat": 0.3},

"Broccoli (100 g)": {"calories": 34.0, "carbs": 6.6, "protein": 2.8, "fat": 0.4},
"Beetroot (100 g)": {"calories": 43.0, "carbs": 9.6, "protein": 1.6, "fat": 0.2},
"Capsicum (Green) (100 g)": {"calories": 20.0, "carbs": 4.6, "protein": 0.9, "fat": 0.2},
"Red Bell Pepper (100 g)": {"calories": 31.0, "carbs": 6.0, "protein": 1.0, "fat": 0.3},
"Yellow Bell Pepper (100 g)": {"calories": 27.0, "carbs": 6.3, "protein": 1.0, "fat": 0.2},
"Zucchini (100 g)": {"calories": 17.0, "carbs": 3.1, "protein": 1.2, "fat": 0.3},
"Pumpkin (100 g)": {"calories": 26.0, "carbs": 6.5, "protein": 1.0, "fat": 0.1},
"Sweet Corn (boiled) (100 g)": {"calories": 96.0, "carbs": 21.0, "protein": 3.4, "fat": 1.5},
"Mushrooms (100 g)": {"calories": 22.0, "carbs": 3.3, "protein": 3.1, "fat": 0.3},
"Drumstick (Moringa Pods) (100 g)": {"calories": 37.0, "carbs": 8.5, "protein": 2.1, "fat": 0.2},
"Radish (100 g)": {"calories": 16.0, "carbs": 3.4, "protein": 0.7, "fat": 0.1},
"Turnip (100 g)": {"calories": 28.0, "carbs": 6.4, "protein": 0.9, "fat": 0.1},
"Bottle Gourd (raw) (100 g)": {"calories": 15.0, "carbs": 3.7, "protein": 0.6, "fat": 0.1},
"Ridge Gourd (100 g)": {"calories": 20.0, "carbs": 4.4, "protein": 0.7, "fat": 0.2},
"Snake Gourd (100 g)": {"calories": 18.0, "carbs": 4.3, "protein": 0.5, "fat": 0.2},
"Fenugreek Leaves (100 g)": {"calories": 43.0, "carbs": 6.0, "protein": 4.4, "fat": 0.9},
"Coriander Leaves (100 g)": {"calories": 23.0, "carbs": 3.7, "protein": 2.1, "fat": 0.5},
"Mint Leaves (100 g)": {"calories": 44.0, "carbs": 8.4, "protein": 3.3, "fat": 0.7},

"Guava (100 g)": {"calories": 68.0, "carbs": 14.3, "protein": 2.6, "fat": 1.0},
"Pineapple (100 g)": {"calories": 50.0, "carbs": 13.1, "protein": 0.5, "fat": 0.1},
"Grapes (100 g)": {"calories": 69.0, "carbs": 18.1, "protein": 0.7, "fat": 0.2},
"Watermelon (100 g)": {"calories": 30.0, "carbs": 7.6, "protein": 0.6, "fat": 0.2},
"Muskmelon (100 g)": {"calories": 34.0, "carbs": 8.2, "protein": 0.8, "fat": 0.2},
"Pear (100 g)": {"calories": 57.0, "carbs": 15.2, "protein": 0.4, "fat": 0.1},
"Kiwi (100 g)": {"calories": 61.0, "carbs": 14.7, "protein": 1.1, "fat": 0.5},
"Pomegranate (100 g)": {"calories": 83.0, "carbs": 18.7, "protein": 1.7, "fat": 1.2},
"Lychee (100 g)": {"calories": 66.0, "carbs": 16.5, "protein": 0.8, "fat": 0.4},
"Strawberries (100 g)": {"calories": 32.0, "carbs": 7.7, "protein": 0.7, "fat": 0.3},
"Blueberries (100 g)": {"calories": 57.0, "carbs": 14.5, "protein": 0.7, "fat": 0.3},
"Raspberries (100 g)": {"calories": 52.0, "carbs": 11.9, "protein": 1.2, "fat": 0.7},
"Blackberries (100 g)": {"calories": 43.0, "carbs": 9.6, "protein": 1.4, "fat": 0.5},
"Avocado (100 g)": {"calories": 160.0, "carbs": 8.5, "protein": 2.0, "fat": 14.7},
"Dates (100 g)": {"calories": 282.0, "carbs": 75.0, "protein": 2.5, "fat": 0.4},
"Raisins (100 g)": {"calories": 299.0, "carbs": 79.0, "protein": 3.1, "fat": 0.5},

"Pistachios (100 g)": {"calories": 562.0, "carbs": 28.0, "protein": 20.2, "fat": 45.4},
"Hazelnuts (100 g)": {"calories": 628.0, "carbs": 16.7, "protein": 15.0, "fat": 60.8},
"Pecans (100 g)": {"calories": 691.0, "carbs": 13.9, "protein": 9.2, "fat": 72.0},
"Macadamia Nuts (100 g)": {"calories": 718.0, "carbs": 13.8, "protein": 7.9, "fat": 75.8},
"Walnuts (100 g)": {"calories": 654.0, "carbs": 13.7, "protein": 15.2, "fat": 65.2},
"Pumpkin Seeds (100 g)": {"calories": 559.0, "carbs": 10.7, "protein": 30.2, "fat": 49.0},
"Sunflower Seeds (100 g)": {"calories": 584.0, "carbs": 20.0, "protein": 20.8, "fat": 51.5},
"Chia Seeds (100 g)": {"calories": 486.0, "carbs": 42.1, "protein": 16.5, "fat": 30.7},
"Flax Seeds (100 g)": {"calories": 534.0, "carbs": 28.9, "protein": 18.3, "fat": 42.2},
"Sesame Seeds (100 g)": {"calories": 573.0, "carbs": 23.4, "protein": 17.7, "fat": 49.7},

"Olive Oil (100 g)": {"calories": 884.0, "carbs": 0.0, "protein": 0.0, "fat": 100.0},
"Sunflower Oil (100 g)": {"calories": 884.0, "carbs": 0.0, "protein": 0.0, "fat": 100.0},
"Mustard Oil (100 g)": {"calories": 884.0, "carbs": 0.0, "protein": 0.0, "fat": 100.0},
"Coconut Oil (100 g)": {"calories": 892.0, "carbs": 0.0, "protein": 0.0, "fat": 100.0},

"Peanut Butter (100 g)": {"calories": 588.0, "carbs": 20.0, "protein": 25.0, "fat": 50.0},
"Dark Chocolate (70%) (100 g)": {"calories": 598.0, "carbs": 46.0, "protein": 7.8, "fat": 43.0},
"Honey (100 g)": {"calories": 304.0, "carbs": 82.4, "protein": 0.3, "fat": 0.0},
"Jam (100 g)": {"calories": 250.0, "carbs": 65.0, "protein": 0.3, "fat": 0.1},
"Ketchup (100 g)": {"calories": 112.0, "carbs": 27.0, "protein": 1.3, "fat": 0.2},
"Mayonnaise (100 g)": {"calories": 680.0, "carbs": 1.0, "protein": 1.0, "fat": 75.0},
"Hummus (100 g)": {"calories": 166.0, "carbs": 14.3, "protein": 7.9, "fat": 9.6},
    "Veg Burger (1 burger (~180 g))": {"calories": 420.0, "carbs": 48.0, "protein": 12.0, "fat": 20.0},
"Cheese Burger (Veg) (1 burger (~200 g))": {"calories": 510.0, "carbs": 47.0, "protein": 18.0, "fat": 28.0},
"Paneer Burger (1 burger (~200 g))": {"calories": 480.0, "carbs": 45.0, "protein": 19.0, "fat": 24.0},
"Aloo Tikki Burger (1 burger)": {"calories": 340.0, "carbs": 45.0, "protein": 8.0, "fat": 14.0},
"Mexican Veg Burger (1 burger)": {"calories": 430.0, "carbs": 46.0, "protein": 13.0, "fat": 21.0},

"Margherita Pizza (1 slice)": {"calories": 270.0, "carbs": 33.0, "protein": 12.0, "fat": 10.0},
"Veggie Pizza (1 slice)": {"calories": 285.0, "carbs": 34.0, "protein": 12.0, "fat": 11.0},
"Farmhouse Pizza (1 slice)": {"calories": 295.0, "carbs": 33.0, "protein": 13.0, "fat": 12.0},
"Paneer Pizza (1 slice)": {"calories": 320.0, "carbs": 32.0, "protein": 15.0, "fat": 14.0},
"Cheese Burst Pizza (1 slice)": {"calories": 390.0, "carbs": 34.0, "protein": 15.0, "fat": 22.0},
"Thin Crust Veg Pizza (1 slice)": {"calories": 220.0, "carbs": 28.0, "protein": 10.0, "fat": 8.0},
"Stuffed Crust Veg Pizza (1 slice)": {"calories": 410.0, "carbs": 36.0, "protein": 16.0, "fat": 23.0},

"Veg Sandwich (2 slices)": {"calories": 240.0, "carbs": 34.0, "protein": 8.0, "fat": 8.0},
"Grilled Veg Sandwich": {"calories": 320.0, "carbs": 35.0, "protein": 11.0, "fat": 15.0},
"Cheese Sandwich": {"calories": 340.0, "carbs": 32.0, "protein": 13.0, "fat": 18.0},
"Paneer Sandwich": {"calories": 360.0, "carbs": 33.0, "protein": 18.0, "fat": 17.0},
"Corn Cheese Sandwich": {"calories": 350.0, "carbs": 36.0, "protein": 11.0, "fat": 17.0},
"Veg Club Sandwich": {"calories": 430.0, "carbs": 42.0, "protein": 15.0, "fat": 22.0},

"Veg Wrap": {"calories": 310.0, "carbs": 36.0, "protein": 10.0, "fat": 14.0},
"Paneer Wrap": {"calories": 420.0, "carbs": 35.0, "protein": 20.0, "fat": 22.0},
"Cheese Wrap": {"calories": 390.0, "carbs": 34.0, "protein": 15.0, "fat": 21.0},
"Falafel Wrap": {"calories": 360.0, "carbs": 42.0, "protein": 12.0, "fat": 16.0},

"French Fries (Medium)": {"calories": 365.0, "carbs": 48.0, "protein": 4.0, "fat": 17.0},
"Peri Peri Fries": {"calories": 380.0, "carbs": 48.0, "protein": 4.0, "fat": 18.0},
"Cheese Fries": {"calories": 480.0, "carbs": 49.0, "protein": 9.0, "fat": 28.0},
"Potato Wedges": {"calories": 270.0, "carbs": 32.0, "protein": 4.0, "fat": 13.0},

"Veg Momos (6 pcs)": {"calories": 230.0, "carbs": 38.0, "protein": 8.0, "fat": 5.0},
"Fried Veg Momos (6 pcs)": {"calories": 340.0, "carbs": 40.0, "protein": 8.0, "fat": 15.0},
"Paneer Momos (6 pcs)": {"calories": 310.0, "carbs": 30.0, "protein": 14.0, "fat": 15.0},

"Veg Chow Mein (1 plate)": {"calories": 390.0, "carbs": 58.0, "protein": 10.0, "fat": 13.0},
"Hakka Noodles (Veg)": {"calories": 410.0, "carbs": 60.0, "protein": 11.0, "fat": 14.0},
"Veg Fried Rice": {"calories": 350.0, "carbs": 56.0, "protein": 8.0, "fat": 10.0},
"Schezwan Fried Rice": {"calories": 390.0, "carbs": 58.0, "protein": 8.0, "fat": 14.0},

"White Sauce Pasta": {"calories": 420.0, "carbs": 50.0, "protein": 12.0, "fat": 18.0},
"Red Sauce Pasta": {"calories": 340.0, "carbs": 56.0, "protein": 10.0, "fat": 8.0},
"Pink Sauce Pasta": {"calories": 390.0, "carbs": 53.0, "protein": 11.0, "fat": 15.0},
"Mac & Cheese": {"calories": 430.0, "carbs": 46.0, "protein": 15.0, "fat": 20.0},

"Veg Spring Roll (2 pcs)": {"calories": 280.0, "carbs": 30.0, "protein": 6.0, "fat": 15.0},
"Cheese Balls (6 pcs)": {"calories": 360.0, "carbs": 24.0, "protein": 10.0, "fat": 24.0},
"Garlic Bread (2 pcs)": {"calories": 220.0, "carbs": 28.0, "protein": 5.0, "fat": 10.0},
"Cheesy Garlic Bread": {"calories": 320.0, "carbs": 30.0, "protein": 9.0, "fat": 18.0},

"Chocolate Milkshake (300 ml)": {"calories": 360.0, "carbs": 48.0, "protein": 10.0, "fat": 14.0},
"Vanilla Milkshake (300 ml)": {"calories": 330.0, "carbs": 46.0, "protein": 9.0, "fat": 12.0},
"Strawberry Milkshake (300 ml)": {"calories": 310.0, "carbs": 44.0, "protein": 9.0, "fat": 10.0},
"Banana Shake (300 ml)": {"calories": 280.0, "carbs": 42.0, "protein": 8.0, "fat": 8.0},
"Mango Shake (300 ml)": {"calories": 320.0, "carbs": 50.0, "protein": 8.0, "fat": 8.0},
"Oreo Shake (300 ml)": {"calories": 480.0, "carbs": 62.0, "protein": 9.0, "fat": 22.0},
"KitKat Shake (300 ml)": {"calories": 510.0, "carbs": 65.0, "protein": 10.0, "fat": 23.0},
"Cold Coffee (300 ml)": {"calories": 220.0, "carbs": 28.0, "protein": 6.0, "fat": 9.0},
"Cold Coffee with Ice Cream": {"calories": 340.0, "carbs": 40.0, "protein": 8.0, "fat": 16.0},
"Lassi Sweet (250 ml)": {"calories": 180.0, "carbs": 24.0, "protein": 6.0, "fat": 7.0},
"Mango Lassi (250 ml)": {"calories": 240.0, "carbs": 36.0, "protein": 6.0, "fat": 8.0},

"Coca Cola (330 ml)": {"calories": 139.0, "carbs": 35.0, "protein": 0.0, "fat": 0.0},
"Pepsi (330 ml)": {"calories": 150.0, "carbs": 41.0, "protein": 0.0, "fat": 0.0},
"Sprite (330 ml)": {"calories": 140.0, "carbs": 38.0, "protein": 0.0, "fat": 0.0},
"Fanta Orange (330 ml)": {"calories": 160.0, "carbs": 42.0, "protein": 0.0, "fat": 0.0},
"Limca (330 ml)": {"calories": 145.0, "carbs": 37.0, "protein": 0.0, "fat": 0.0},
"Mountain Dew (330 ml)": {"calories": 170.0, "carbs": 46.0, "protein": 0.0, "fat": 0.0},
"Red Bull (250 ml)": {"calories": 112.0, "carbs": 27.0, "protein": 0.0, "fat": 0.0},
"Monster Energy (500 ml)": {"calories": 210.0, "carbs": 54.0, "protein": 0.0, "fat": 0.0},

"Fresh Orange Juice (250 ml)": {"calories": 112.0, "carbs": 26.0, "protein": 1.7, "fat": 0.5},
"Apple Juice (250 ml)": {"calories": 118.0, "carbs": 28.0, "protein": 0.2, "fat": 0.3},
"Pineapple Juice (250 ml)": {"calories": 132.0, "carbs": 32.0, "protein": 0.9, "fat": 0.2},
"Watermelon Juice (250 ml)": {"calories": 76.0, "carbs": 18.0, "protein": 1.2, "fat": 0.2},
"Lemonade (250 ml)": {"calories": 95.0, "carbs": 24.0, "protein": 0.0, "fat": 0.0},
"Coconut Water (250 ml)": {"calories": 45.0, "carbs": 9.0, "protein": 1.7, "fat": 0.2},

"Vanilla Ice Cream (100 g)": {"calories": 207.0, "carbs": 24.0, "protein": 3.5, "fat": 11.0},
"Chocolate Ice Cream (100 g)": {"calories": 216.0, "carbs": 25.0, "protein": 3.8, "fat": 12.0},
"Butterscotch Ice Cream (100 g)": {"calories": 230.0, "carbs": 27.0, "protein": 3.5, "fat": 13.0},
"Mango Ice Cream (100 g)": {"calories": 210.0, "carbs": 26.0, "protein": 3.2, "fat": 11.0},
"Kulfi (100 g)": {"calories": 240.0, "carbs": 28.0, "protein": 6.0, "fat": 12.0},

"Chocolate Cake (100 g)": {"calories": 370.0, "carbs": 53.0, "protein": 5.0, "fat": 16.0},
"Black Forest Cake (100 g)": {"calories": 300.0, "carbs": 42.0, "protein": 4.0, "fat": 13.0},
"Red Velvet Cake (100 g)": {"calories": 360.0, "carbs": 48.0, "protein": 4.0, "fat": 17.0},
"Brownie (100 g)": {"calories": 466.0, "carbs": 59.0, "protein": 5.0, "fat": 24.0},
"Chocolate Muffin (100 g)": {"calories": 377.0, "carbs": 53.0, "protein": 6.0, "fat": 16.0},
"Donut (Glazed) (1)": {"calories": 270.0, "carbs": 31.0, "protein": 4.0, "fat": 15.0},

"Plain Popcorn (30 g popped)": {"calories": 120.0, "carbs": 24.0, "protein": 3.0, "fat": 1.5},
"Butter Popcorn (30 g)": {"calories": 170.0, "carbs": 21.0, "protein": 3.0, "fat": 8.0},
"Nachos with Cheese (100 g)": {"calories": 490.0, "carbs": 54.0, "protein": 8.0, "fat": 27.0},
"Potato Chips (100 g)": {"calories": 536.0, "carbs": 53.0, "protein": 7.0, "fat": 35.0},
"Tortilla Chips (100 g)": {"calories": 497.0, "carbs": 63.0, "protein": 7.0, "fat": 24.0},

"Chocolate Cookies (100 g)": {"calories": 488.0, "carbs": 68.0, "protein": 6.0, "fat": 22.0},
"Digestive Biscuits (100 g)": {"calories": 483.0, "carbs": 64.0, "protein": 7.0, "fat": 20.0},
"Cream Biscuits (100 g)": {"calories": 510.0, "carbs": 67.0, "protein": 5.0, "fat": 25.0},

"Cornflakes (dry) (30 g)": {"calories": 113.0, "carbs": 26.0, "protein": 2.3, "fat": 0.3},
"Chocolate Cereal (30 g)": {"calories": 120.0, "carbs": 24.0, "protein": 2.5, "fat": 1.5},
"Muesli (50 g)": {"calories": 190.0, "carbs": 32.0, "protein": 6.0, "fat": 4.5},
"Granola (50 g)": {"calories": 235.0, "carbs": 32.0, "protein": 5.0, "fat": 9.0},

"Veg Hot Dog": {"calories": 360.0, "carbs": 40.0, "protein": 12.0, "fat": 16.0},
"Paneer Hot Dog": {"calories": 420.0, "carbs": 38.0, "protein": 18.0, "fat": 21.0},
"Veg Taco (2 pcs)": {"calories": 340.0, "carbs": 36.0, "protein": 10.0, "fat": 17.0},
"Veg Burrito": {"calories": 520.0, "carbs": 60.0, "protein": 16.0, "fat": 22.0},
"Paneer Burrito": {"calories": 610.0, "carbs": 58.0, "protein": 24.0, "fat": 28.0},
"Falafel Plate": {"calories": 430.0, "carbs": 45.0, "protein": 15.0, "fat": 20.0},
"Aloo Paratha (1 medium (120 g))": {"calories": 290.0, "carbs": 38.0, "protein": 7.0, "fat": 12.0},
"Gobi Paratha (1 medium (120 g))": {"calories": 250.0, "carbs": 36.0, "protein": 7.0, "fat": 9.0},
"Paneer Paratha (1 medium (140 g))": {"calories": 340.0, "carbs": 36.0, "protein": 14.0, "fat": 16.0},
"Mooli Paratha (1 medium (120 g))": {"calories": 240.0, "carbs": 35.0, "protein": 6.0, "fat": 8.0},
"Mix Veg Paratha (1 medium (120 g))": {"calories": 260.0, "carbs": 35.0, "protein": 7.0, "fat": 10.0},
"Onion Paratha (1 medium (120 g))": {"calories": 255.0, "carbs": 36.0, "protein": 6.0, "fat": 9.0},
"Methi Paratha (1 medium (120 g))": {"calories": 235.0, "carbs": 34.0, "protein": 7.0, "fat": 8.0},
"Cheese Paratha (1 medium (140 g))": {"calories": 365.0, "carbs": 34.0, "protein": 14.0, "fat": 19.0},
"Ajwain Paratha (1 medium (100 g))": {"calories": 245.0, "carbs": 33.0, "protein": 6.0, "fat": 9.0},
"Lachha Paratha (1 medium (100 g))": {"calories": 300.0, "carbs": 36.0, "protein": 6.0, "fat": 15.0},

"Paneer Bhurji (100 g)": {"calories": 265.0, "carbs": 5.0, "protein": 18.0, "fat": 19.0},
"Soya Chaap (100 g)": {"calories": 190.0, "carbs": 10.0, "protein": 22.0, "fat": 7.0},
"Malai Chaap (100 g)": {"calories": 260.0, "carbs": 11.0, "protein": 18.0, "fat": 16.0},
"Paneer Tikka (100 g)": {"calories": 260.0, "carbs": 6.0, "protein": 18.0, "fat": 18.0},
"Hara Bhara Kebab (4 pieces)": {"calories": 220.0, "carbs": 18.0, "protein": 8.0, "fat": 13.0},
"Veg Cutlet (2 pieces)": {"calories": 210.0, "carbs": 24.0, "protein": 5.0, "fat": 10.0},
"Paneer Pakora (100 g)": {"calories": 330.0, "carbs": 18.0, "protein": 14.0, "fat": 22.0},
"Veg Manchurian (Dry) (1 plate)": {"calories": 320.0, "carbs": 32.0, "protein": 8.0, "fat": 17.0},
"Gobi Manchurian (1 plate)": {"calories": 290.0, "carbs": 28.0, "protein": 6.0, "fat": 17.0},
"Chilli Paneer (1 plate)": {"calories": 360.0, "carbs": 18.0, "protein": 19.0, "fat": 23.0},

"Masala Chai (200 ml)": {"calories": 80.0, "carbs": 10.0, "protein": 2.5, "fat": 3.0},
"Black Tea (200 ml)": {"calories": 2.0, "carbs": 0.0, "protein": 0.0, "fat": 0.0},
"Green Tea (200 ml)": {"calories": 2.0, "carbs": 0.0, "protein": 0.0, "fat": 0.0},
"Lemon Tea (200 ml)": {"calories": 20.0, "carbs": 5.0, "protein": 0.0, "fat": 0.0},
"Black Coffee (200 ml)": {"calories": 2.0, "carbs": 0.0, "protein": 0.3, "fat": 0.0},
"Espresso (30 ml)": {"calories": 3.0, "carbs": 0.5, "protein": 0.2, "fat": 0.0},
"Americano (250 ml)": {"calories": 5.0, "carbs": 1.0, "protein": 0.3, "fat": 0.0},
"Cappuccino (250 ml)": {"calories": 90.0, "carbs": 9.0, "protein": 6.0, "fat": 3.5},
"Latte (250 ml)": {"calories": 140.0, "carbs": 13.0, "protein": 7.0, "fat": 6.0},
"Mocha Coffee (250 ml)": {"calories": 220.0, "carbs": 28.0, "protein": 7.0, "fat": 9.0},
"Caramel Latte (250 ml)": {"calories": 240.0, "carbs": 33.0, "protein": 7.0, "fat": 8.0},
"Hot Chocolate (250 ml)": {"calories": 230.0, "carbs": 34.0, "protein": 8.0, "fat": 8.0},

"Protein Shake (Whey) (300 ml)": {"calories": 180.0, "carbs": 8.0, "protein": 30.0, "fat": 3.0},
"Chocolate Protein Shake (300 ml)": {"calories": 210.0, "carbs": 12.0, "protein": 30.0, "fat": 4.0},
"Strawberry Protein Shake (300 ml)": {"calories": 200.0, "carbs": 11.0, "protein": 30.0, "fat": 3.5},
"Vanilla Protein Shake (300 ml)": {"calories": 195.0, "carbs": 10.0, "protein": 30.0, "fat": 3.5},

"Badam Milk (250 ml)": {"calories": 210.0, "carbs": 22.0, "protein": 8.0, "fat": 10.0},
"Rose Milk (250 ml)": {"calories": 180.0, "carbs": 28.0, "protein": 6.0, "fat": 5.0},
"Turmeric Milk (250 ml)": {"calories": 165.0, "carbs": 13.0, "protein": 8.0, "fat": 8.0},
"Soy Milk (250 ml)": {"calories": 105.0, "carbs": 8.0, "protein": 7.0, "fat": 4.0},
"Almond Milk (Unsweetened) (250 ml)": {"calories": 35.0, "carbs": 1.5, "protein": 1.2, "fat": 2.8},
"Oat Milk (250 ml)": {"calories": 120.0, "carbs": 16.0, "protein": 3.0, "fat": 5.0},

"Sugarcane Juice (250 ml)": {"calories": 183.0, "carbs": 45.0, "protein": 0.3, "fat": 0.0},
"Aam Panna (250 ml)": {"calories": 120.0, "carbs": 30.0, "protein": 0.5, "fat": 0.2},
"Jaljeera (250 ml)": {"calories": 45.0, "carbs": 10.0, "protein": 0.5, "fat": 0.1},
"Shikanji (250 ml)": {"calories": 80.0, "carbs": 20.0, "protein": 0.2, "fat": 0.1},
"Watermelon Smoothie (300 ml)": {"calories": 120.0, "carbs": 28.0, "protein": 2.0, "fat": 0.5},
"Mixed Fruit Juice (250 ml)": {"calories": 135.0, "carbs": 33.0, "protein": 1.0, "fat": 0.2},
"Guava Juice (250 ml)": {"calories": 115.0, "carbs": 26.0, "protein": 2.0, "fat": 0.3},
"Pomegranate Juice (250 ml)": {"calories": 135.0, "carbs": 33.0, "protein": 1.0, "fat": 0.2},
"Kiwi Smoothie (300 ml)": {"calories": 170.0, "carbs": 36.0, "protein": 5.0, "fat": 2.0},
"Berry Smoothie (300 ml)": {"calories": 180.0, "carbs": 35.0, "protein": 6.0, "fat": 3.0},

"Chocolate Smoothie (300 ml)": {"calories": 320.0, "carbs": 45.0, "protein": 10.0, "fat": 12.0},
"Peanut Butter Shake (300 ml)": {"calories": 430.0, "carbs": 28.0, "protein": 18.0, "fat": 28.0},
"Dry Fruit Shake (300 ml)": {"calories": 420.0, "carbs": 40.0, "protein": 14.0, "fat": 22.0},
"Dates Shake (300 ml)": {"calories": 340.0, "carbs": 55.0, "protein": 9.0, "fat": 8.0},
"Badam Shake (300 ml)": {"calories": 360.0, "carbs": 32.0, "protein": 13.0, "fat": 19.0},
"Pista Shake (300 ml)": {"calories": 350.0, "carbs": 30.0, "protein": 12.0, "fat": 20.0},

"Veg Thali (1 serving)": {"calories": 700.0, "carbs": 95.0, "protein": 22.0, "fat": 25.0},
"Mini Veg Thali (1 serving)": {"calories": 520.0, "carbs": 70.0, "protein": 16.0, "fat": 18.0},
"Dal Makhani (1 bowl)": {"calories": 280.0, "carbs": 24.0, "protein": 11.0, "fat": 16.0},
"Shahi Paneer (1 bowl)": {"calories": 340.0, "carbs": 12.0, "protein": 13.0, "fat": 27.0},
"Kadai Paneer (1 bowl)": {"calories": 290.0, "carbs": 10.0, "protein": 15.0, "fat": 21.0},
"Paneer Butter Masala (1 bowl)": {"calories": 360.0, "carbs": 12.0, "protein": 14.0, "fat": 28.0},
"Malai Kofta (1 bowl)": {"calories": 370.0, "carbs": 24.0, "protein": 9.0, "fat": 27.0},
"Navratan Korma (1 bowl)": {"calories": 290.0, "carbs": 22.0, "protein": 7.0, "fat": 19.0},
"Veg Kolhapuri (1 bowl)": {"calories": 210.0, "carbs": 18.0, "protein": 6.0, "fat": 13.0},
"Chole Bhature (1 plate)": {"calories": 620.0, "carbs": 72.0, "protein": 16.0, "fat": 30.0},
    "Maggi Noodles (1 packet (70 g))": {"calories": 320.0, "carbs": 45.0, "protein": 7.0, "fat": 13.0},
"Maggi Masala Noodles (prepared) (1 bowl)": {"calories": 350.0, "carbs": 50.0, "protein": 8.0, "fat": 14.0},
"Maggi Vegetable Atta Noodles (1 packet)": {"calories": 310.0, "carbs": 48.0, "protein": 8.0, "fat": 10.0},
"Yippee Noodles (1 packet)": {"calories": 335.0, "carbs": 49.0, "protein": 7.0, "fat": 13.0},
"Top Ramen Curry Noodles (1 packet)": {"calories": 340.0, "carbs": 49.0, "protein": 7.0, "fat": 14.0},

"Bikaneri Bhujia (100 g)": {"calories": 560.0, "carbs": 48.0, "protein": 15.0, "fat": 34.0},
"Aloo Bhujia (100 g)": {"calories": 540.0, "carbs": 52.0, "protein": 10.0, "fat": 33.0},
"Navratan Mixture (100 g)": {"calories": 545.0, "carbs": 46.0, "protein": 11.0, "fat": 36.0},
"Bombay Mix (100 g)": {"calories": 540.0, "carbs": 48.0, "protein": 11.0, "fat": 35.0},
"Chanachur (100 g)": {"calories": 535.0, "carbs": 46.0, "protein": 12.0, "fat": 35.0},
"Corn Mixture (100 g)": {"calories": 510.0, "carbs": 56.0, "protein": 9.0, "fat": 27.0},
"Salted Namkeen (100 g)": {"calories": 520.0, "carbs": 52.0, "protein": 10.0, "fat": 30.0},
"Sev (100 g)": {"calories": 570.0, "carbs": 45.0, "protein": 14.0, "fat": 38.0},
"Ratlami Sev (100 g)": {"calories": 565.0, "carbs": 44.0, "protein": 13.0, "fat": 39.0},
"Masala Peanuts (100 g)": {"calories": 610.0, "carbs": 20.0, "protein": 23.0, "fat": 50.0},

"Kurkure Masala Munch (100 g)": {"calories": 545.0, "carbs": 57.0, "protein": 6.0, "fat": 33.0},
"Kurkure Green Chutney (100 g)": {"calories": 540.0, "carbs": 58.0, "protein": 6.0, "fat": 32.0},
"Lay's Classic Chips (100 g)": {"calories": 536.0, "carbs": 53.0, "protein": 7.0, "fat": 35.0},
"Lay's American Style Cream & Onion (100 g)": {"calories": 540.0, "carbs": 54.0, "protein": 6.0, "fat": 35.0},
"Lay's Magic Masala (100 g)": {"calories": 540.0, "carbs": 54.0, "protein": 6.0, "fat": 35.0},
"Bingo Mad Angles (100 g)": {"calories": 530.0, "carbs": 58.0, "protein": 6.0, "fat": 31.0},
"Doritos Nacho Cheese (100 g)": {"calories": 500.0, "carbs": 63.0, "protein": 7.0, "fat": 25.0},
"Pringles Original (100 g)": {"calories": 536.0, "carbs": 53.0, "protein": 5.0, "fat": 35.0},

"Masala Corn Cup (1 cup)": {"calories": 180.0, "carbs": 34.0, "protein": 6.0, "fat": 2.0},
"Cheese Corn Cup (1 cup)": {"calories": 260.0, "carbs": 30.0, "protein": 9.0, "fat": 12.0},
"Sweet Corn Chaat (1 bowl)": {"calories": 190.0, "carbs": 36.0, "protein": 6.0, "fat": 2.0},

"Veg Maggi with Cheese (1 bowl)": {"calories": 430.0, "carbs": 52.0, "protein": 13.0, "fat": 19.0},
"Veg Maggi with Paneer (1 bowl)": {"calories": 450.0, "carbs": 50.0, "protein": 18.0, "fat": 20.0},
"Veg Cheese Maggi (1 bowl)": {"calories": 440.0, "carbs": 51.0, "protein": 13.0, "fat": 20.0},

"Bread Pakora (1 piece)": {"calories": 260.0, "carbs": 27.0, "protein": 7.0, "fat": 14.0},
"Cheese Bread Pakora (1 piece)": {"calories": 340.0, "carbs": 28.0, "protein": 12.0, "fat": 21.0},
"Veg Puff (1 piece)": {"calories": 310.0, "carbs": 30.0, "protein": 5.0, "fat": 19.0},
"Paneer Puff (1 piece)": {"calories": 350.0, "carbs": 29.0, "protein": 10.0, "fat": 22.0},
"Cheese Puff (1 piece)": {"calories": 360.0, "carbs": 28.0, "protein": 10.0, "fat": 24.0},

"Veg Roll (1 roll)": {"calories": 330.0, "carbs": 40.0, "protein": 8.0, "fat": 15.0},
"Paneer Kathi Roll (1 roll)": {"calories": 470.0, "carbs": 42.0, "protein": 19.0, "fat": 24.0},
"Cheese Roll (1 roll)": {"calories": 420.0, "carbs": 38.0, "protein": 14.0, "fat": 22.0},

"Veg Frankie (1 piece)": {"calories": 340.0, "carbs": 41.0, "protein": 9.0, "fat": 15.0},
"Paneer Frankie (1 piece)": {"calories": 430.0, "carbs": 39.0, "protein": 18.0, "fat": 22.0},

"Cheese Dosa (1 large)": {"calories": 310.0, "carbs": 34.0, "protein": 8.0, "fat": 16.0},
"Masala Dosa (1 large)": {"calories": 387.0, "carbs": 48.0, "protein": 8.0, "fat": 18.0},
"Mysore Masala Dosa (1 large)": {"calories": 430.0, "carbs": 50.0, "protein": 9.0, "fat": 20.0},
"Rava Dosa (1 large)": {"calories": 260.0, "carbs": 32.0, "protein": 5.0, "fat": 11.0},

"Cheese Uttapam (1 piece)": {"calories": 290.0, "carbs": 30.0, "protein": 9.0, "fat": 14.0},
"Onion Uttapam (1 piece)": {"calories": 190.0, "carbs": 28.0, "protein": 5.0, "fat": 6.0},

"Cheese Pav Bhaji (1 plate)": {"calories": 520.0, "carbs": 55.0, "protein": 12.0, "fat": 28.0},
"Extra Butter Pav Bhaji (1 plate)": {"calories": 610.0, "carbs": 56.0, "protein": 10.0, "fat": 36.0},

"Cheese Vada Pav (1 piece)": {"calories": 380.0, "carbs": 42.0, "protein": 10.0, "fat": 19.0},
"Jumbo Vada Pav (1 piece)": {"calories": 360.0, "carbs": 48.0, "protein": 8.0, "fat": 15.0},

"Cheese Dabeli (1 piece)": {"calories": 360.0, "carbs": 45.0, "protein": 9.0, "fat": 16.0},
"Dabeli (1 piece)": {"calories": 290.0, "carbs": 42.0, "protein": 6.0, "fat": 11.0},

"Veg Pizza Puff (1 piece)": {"calories": 290.0, "carbs": 28.0, "protein": 7.0, "fat": 17.0},
"Paneer Pizza (Mini)": {"calories": 520.0, "carbs": 52.0, "protein": 20.0, "fat": 26.0},

"Garlic Naan with Cheese (1 piece)": {"calories": 360.0, "carbs": 46.0, "protein": 10.0, "fat": 15.0},
"Butter Naan (1 piece)": {"calories": 310.0, "carbs": 45.0, "protein": 8.0, "fat": 10.0},

"Cheese Momos (6 pieces)": {"calories": 360.0, "carbs": 34.0, "protein": 13.0, "fat": 18.0},
"Tandoori Momos (Veg) (6 pieces)": {"calories": 300.0, "carbs": 31.0, "protein": 10.0, "fat": 15.0},

"Veg Sizzler (1 serving)": {"calories": 540.0, "carbs": 55.0, "protein": 16.0, "fat": 26.0},
"Paneer Sizzler (1 serving)": {"calories": 620.0, "carbs": 50.0, "protein": 24.0, "fat": 35.0},

"Chocolate Pastry (1 piece)": {"calories": 290.0, "carbs": 35.0, "protein": 4.0, "fat": 15.0},
"Pineapple Pastry (1 piece)": {"calories": 260.0, "carbs": 34.0, "protein": 4.0, "fat": 12.0},
"Black Forest Pastry (1 piece)": {"calories": 280.0, "carbs": 36.0, "protein": 4.0, "fat": 13.0},
"Red Velvet Pastry (1 piece)": {"calories": 310.0, "carbs": 38.0, "protein": 4.0, "fat": 16.0},

"Chocolate Croissant (1 piece)": {"calories": 410.0, "carbs": 45.0, "protein": 8.0, "fat": 22.0},
"Butter Croissant (1 piece)": {"calories": 270.0, "carbs": 31.0, "protein": 5.0, "fat": 14.0},

"Veg Pizza Sandwich": {"calories": 390.0, "carbs": 42.0, "protein": 14.0, "fat": 18.0},
"Cheese Toast (2 slices)": {"calories": 320.0, "carbs": 28.0, "protein": 12.0, "fat": 18.0},
"Garlic Toast (2 slices)": {"calories": 220.0, "carbs": 26.0, "protein": 5.0, "fat": 10.0},

"Chocolate Waffle (1 piece)": {"calories": 420.0, "carbs": 52.0, "protein": 8.0, "fat": 20.0},
"Belgian Waffle (1 piece)": {"calories": 390.0, "carbs": 48.0, "protein": 7.0, "fat": 19.0},
"Pancakes with Maple Syrup (2 pancakes)": {"calories": 350.0, "carbs": 58.0, "protein": 8.0, "fat": 10.0},

"Veg Sushi Roll (8 pieces)": {"calories": 260.0, "carbs": 48.0, "protein": 6.0, "fat": 4.0},
"Avocado Sushi Roll (8 pieces)": {"calories": 290.0, "carbs": 44.0, "protein": 5.0, "fat": 10.0},
"White Bread (1 slice (30 g))": {"calories": 80.0, "carbs": 15.0, "protein": 2.7, "fat": 1.0},
"Brown Bread (1 slice (30 g))": {"calories": 74.0, "carbs": 13.0, "protein": 3.5, "fat": 1.1},
"Whole Wheat Bread (1 slice (30 g))": {"calories": 75.0, "carbs": 13.0, "protein": 3.8, "fat": 1.0},
"Multigrain Bread (1 slice (35 g))": {"calories": 85.0, "carbs": 15.0, "protein": 4.0, "fat": 1.4},
"Garlic Bread (1 slice)": {"calories": 140.0, "carbs": 17.0, "protein": 3.0, "fat": 7.0},
"Bread Toast (2 slices)": {"calories": 160.0, "carbs": 30.0, "protein": 5.4, "fat": 2.0},
"Butter Toast (2 slices)": {"calories": 230.0, "carbs": 30.0, "protein": 5.4, "fat": 10.0},
"Jam Toast (2 slices)": {"calories": 220.0, "carbs": 40.0, "protein": 5.0, "fat": 3.0},
"Peanut Butter Toast (2 slices)": {"calories": 300.0, "carbs": 32.0, "protein": 11.0, "fat": 15.0},
"Cheese Toast (2 slices)": {"calories": 290.0, "carbs": 29.0, "protein": 12.0, "fat": 14.0},

"Bread Omelette (Veg Style) (2 slices)": {"calories": 250.0, "carbs": 28.0, "protein": 11.0, "fat": 10.0},
"Bread Butter (2 slices)": {"calories": 235.0, "carbs": 30.0, "protein": 5.0, "fat": 10.0},
"Bread Jam (2 slices)": {"calories": 220.0, "carbs": 42.0, "protein": 5.0, "fat": 2.0},
"Bread Cheese (2 slices)": {"calories": 280.0, "carbs": 28.0, "protein": 12.0, "fat": 14.0},
"French Toast (2 slices)": {"calories": 310.0, "carbs": 32.0, "protein": 11.0, "fat": 15.0},

"Plain Bun (1 bun)": {"calories": 150.0, "carbs": 28.0, "protein": 5.0, "fat": 2.0},
"Pav (1 piece)": {"calories": 90.0, "carbs": 18.0, "protein": 3.0, "fat": 1.0},
"Burger Bun (1 bun)": {"calories": 120.0, "carbs": 22.0, "protein": 4.0, "fat": 2.0},
"Hot Dog Bun (1 bun)": {"calories": 130.0, "carbs": 24.0, "protein": 4.0, "fat": 2.0},
"Bagel (1 medium)": {"calories": 250.0, "carbs": 49.0, "protein": 10.0, "fat": 1.5},

"Croissant (1 piece)": {"calories": 231.0, "carbs": 26.0, "protein": 5.0, "fat": 12.0},
"Muffin (Plain) (1 medium)": {"calories": 265.0, "carbs": 38.0, "protein": 5.0, "fat": 10.0},
"Rusk (2 pieces)": {"calories": 110.0, "carbs": 20.0, "protein": 3.0, "fat": 2.0},
"Khari Biscuit (2 pieces)": {"calories": 120.0, "carbs": 12.0, "protein": 2.0, "fat": 7.0},
"Tea Cake (1 slice)": {"calories": 180.0, "carbs": 28.0, "protein": 3.0, "fat": 7.0},

"Boiled Sweet Corn (1 cup)": {"calories": 132.0, "carbs": 29.0, "protein": 5.0, "fat": 2.0},
"Roasted Corn (1 medium)": {"calories": 110.0, "carbs": 24.0, "protein": 4.0, "fat": 1.5},
"Butter Corn (1 cup)": {"calories": 180.0, "carbs": 28.0, "protein": 5.0, "fat": 6.0},
"Boiled Chickpeas (100 g)": {"calories": 164.0, "carbs": 27.0, "protein": 9.0, "fat": 2.6},
"Boiled Black Chana (100 g)": {"calories": 164.0, "carbs": 27.0, "protein": 9.0, "fat": 2.6},

"Boiled Corn Chaat (1 bowl)": {"calories": 170.0, "carbs": 31.0, "protein": 6.0, "fat": 3.0},
"Fruit Chaat (1 bowl)": {"calories": 120.0, "carbs": 30.0, "protein": 2.0, "fat": 0.5},
"Vegetable Salad (1 bowl)": {"calories": 60.0, "carbs": 12.0, "protein": 2.5, "fat": 0.5},
"Greek Salad (1 bowl)": {"calories": 180.0, "carbs": 10.0, "protein": 6.0, "fat": 13.0},
"Caesar Salad (Veg) (1 bowl)": {"calories": 220.0, "carbs": 15.0, "protein": 7.0, "fat": 15.0},

"Plain Rice Cakes (2 cakes)": {"calories": 70.0, "carbs": 15.0, "protein": 1.5, "fat": 0.5},
"Rice Krispies (30 g)": {"calories": 116.0, "carbs": 26.0, "protein": 2.0, "fat": 0.4},
"Weetabix (2 biscuits)": {"calories": 136.0, "carbs": 26.0, "protein": 4.8, "fat": 0.8},
"Porridge (1 bowl)": {"calories": 180.0, "carbs": 30.0, "protein": 7.0, "fat": 4.0},
"Semolina Porridge (1 bowl)": {"calories": 210.0, "carbs": 35.0, "protein": 6.0, "fat": 5.0},

"Plain Pasta (cooked) (100 g)": {"calories": 157.0, "carbs": 31.0, "protein": 5.8, "fat": 0.9},
"Macaroni (cooked) (100 g)": {"calories": 158.0, "carbs": 31.0, "protein": 5.8, "fat": 1.0},
"Spaghetti (cooked) (100 g)": {"calories": 158.0, "carbs": 31.0, "protein": 5.8, "fat": 0.9},
"Rice Noodles (cooked) (100 g)": {"calories": 109.0, "carbs": 25.0, "protein": 1.8, "fat": 0.2},
"Whole Wheat Pasta (100 g cooked)": {"calories": 149.0, "carbs": 30.0, "protein": 6.0, "fat": 0.9},

"Plain Yogurt (100 g)": {"calories": 61.0, "carbs": 4.7, "protein": 3.5, "fat": 3.3},
"Low Fat Yogurt (100 g)": {"calories": 43.0, "carbs": 4.7, "protein": 4.0, "fat": 1.0},
"Flavored Yogurt (100 g)": {"calories": 95.0, "carbs": 14.0, "protein": 3.5, "fat": 2.0},
"Vanilla Yogurt (100 g)": {"calories": 97.0, "carbs": 15.0, "protein": 3.4, "fat": 2.0},
"Frozen Yogurt (100 g)": {"calories": 127.0, "carbs": 22.0, "protein": 3.5, "fat": 3.0},

"Cream Cheese (30 g)": {"calories": 102.0, "carbs": 1.6, "protein": 2.0, "fat": 10.0},
"Cottage Cheese (100 g)": {"calories": 98.0, "carbs": 3.4, "protein": 11.0, "fat": 4.3},
"Processed Cheese Slice (1 slice)": {"calories": 65.0, "carbs": 1.0, "protein": 4.0, "fat": 5.0},
"Cheese Cube (20 g)": {"calories": 80.0, "carbs": 0.5, "protein": 5.0, "fat": 6.5},
"Cheese Spread (20 g)": {"calories": 70.0, "carbs": 1.0, "protein": 2.0, "fat": 6.0},

"Boiled Potato (1 medium)": {"calories": 161.0, "carbs": 37.0, "protein": 4.0, "fat": 0.2},
"Mashed Potato (100 g)": {"calories": 110.0, "carbs": 17.0, "protein": 2.0, "fat": 4.0},
"Baked Potato (1 medium)": {"calories": 161.0, "carbs": 37.0, "protein": 4.0, "fat": 0.2},
"Sweet Potato Fries (100 g)": {"calories": 250.0, "carbs": 33.0, "protein": 2.5, "fat": 11.0},
"Hash Browns (100 g)": {"calories": 326.0, "carbs": 37.0, "protein": 3.0, "fat": 18.0},

"Boiled Pasta with Butter (1 bowl)": {"calories": 280.0, "carbs": 38.0, "protein": 7.0, "fat": 11.0},
"Vegetable Soup (1 bowl)": {"calories": 90.0, "carbs": 15.0, "protein": 3.0, "fat": 2.0},
"Tomato Soup (1 bowl)": {"calories": 80.0, "carbs": 14.0, "protein": 2.0, "fat": 2.0},
"Sweet Corn Soup (1 bowl)": {"calories": 140.0, "carbs": 25.0, "protein": 4.0, "fat": 2.0},
"Hot & Sour Soup (Veg) (1 bowl)": {"calories": 95.0, "carbs": 15.0, "protein": 3.0, "fat": 2.0}
}
INSULIN_TYPES = [
    "No Insulin",
    "Rapid-Acting (e.g., Lispro, Aspart)",
    "Short-Acting (Regular)",
    "Intermediate-Acting (NPH)",
    "Long-Acting (Glargine, Detemir)",
    "Mixed Insulin (70/30)",
]

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def calculate_bmi(weight_kg: float, height_cm: float) -> tuple[float, str]:
    """Return (bmi_value, category)."""
    if height_cm <= 0 or weight_kg <= 0:
        return 0.0, "N/A"
    bmi = weight_kg / ((height_cm / 100) ** 2)
    if bmi < 18.5:   cat = "Underweight"
    elif bmi < 25:   cat = "Normal"
    elif bmi < 30:   cat = "Overweight"
    else:            cat = "Obese"
    return round(bmi, 1), cat


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    """Smooth S-curve interpolation (cubic: 3x²-2x³) for gradual physiological onset/offset."""
    if edge0 == edge1:
        return 0.0 if x < edge0 else 1.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


INSULIN_ACTION_PROFILE = {
    "No Insulin":                           {"onset": 0,   "peak": 0,   "end": 1},
    "Rapid-Acting (e.g., Lispro, Aspart)":  {"onset": 15,  "peak": 75,  "end": 240},
    "Short-Acting (Regular)":               {"onset": 45,  "peak": 150, "end": 420},
    "Intermediate-Acting (NPH)":            {"onset": 150, "peak": 480, "end": 900},
    "Long-Acting (Glargine, Detemir)":      {"onset": 90,  "peak": 360, "end": 1380},
    "Mixed Insulin (70/30)":                {"onset": 30,  "peak": 180, "end": 720},
}

# How quickly the body's OWN insulin response clears a glucose excursion.
# Type 1 = no endogenous insulin at all; Type 2/Pre = partial; No DM = full.
CARB_RESPONSE_PROFILE = {
    "No Diabetes":      {"peak": 45,  "decay": 90},
    "Prediabetes":      {"peak": 50,  "decay": 115},
    "Type 2 Diabetes":  {"peak": 60,  "decay": 130},
    "Type 1 Diabetes":  {"peak": 60,  "decay": 165},
}


def _cumulative_insulin_fraction(minutes: float, onset: float, peak: float, end: float) -> float:
    """Fraction of a dose's total glucose-lowering effect delivered by `minutes` post-injection."""
    if minutes <= onset: return 0.0
    if minutes <= peak:  return 0.5 * _smoothstep(onset, peak, minutes)
    if minutes <= end:   return 0.5 + 0.5 * _smoothstep(peak, end, minutes)
    return 1.0


def _carb_excursion_fraction(minutes: float, peak: float, decay: float) -> float:
    """Relative glucose excursion (0→1→0) at a given time after eating."""
    if minutes <= peak:
        return _smoothstep(0, peak, minutes)
    return 1.0 - _smoothstep(peak, peak + decay, minutes)


def _estimate_bmr(weight_kg: float, age: int = 35, gender: str = "Male") -> float:
    """
    Mifflin-St Jeor BMR estimate (kcal/day) — how many calories the body
    burns at rest just to keep organs functioning. This energy comes from
    glucose in the blood, so it continuously lowers blood glucose even
    without any activity or insulin. Using a fixed height of 170cm as a
    neutral default since height doesn't shift the result dramatically.
    """
    weight_kg = max(weight_kg, 30.0)
    if gender == "Female":
        bmr = 10 * weight_kg + 6.25 * 170 - 5 * age - 161
    else:
        bmr = 10 * weight_kg + 6.25 * 170 - 5 * age + 5
    return max(1200.0, bmr)


def glucose_prediction_model(
    current_glucose: float,
    carbs_g: float,
    diabetes_type: str,
    insulin_type: str,
    insulin_dose: float,
    time_since_injection_hr: float = 0.0,
    weight_kg: float = 70.0,
    age: int = 35,
    gender: str = "Male",
    calories_kcal: float = 0.0,
    time_since_meal_hr: float = 0.0,
    exercise_type: str = "No Exercise",
    exercise_duration_min: float = 0.0,
) -> dict:
    """
    Educational glucose prediction model — 30 / 60 / 90 / 120 min timepoints.

    Five competing physiological effects:

    1. CARB EXCURSION — carbs raise glucose; curve position depends on
       time_since_meal_hr (if you ate 1 hr ago you are already past the peak).
    2. BMR BURN — resting metabolism consumes glucose; liver offsets ~92% via
       glycogen, so net blood glucose drop is small but real.
    3. EXERCISE — muscles absorb glucose directly without insulin during
       activity, plus an afterburn effect for hours post-workout. Magnitude
       now scales with how long you actually exercised (duration_factor),
       not just which intensity bucket you picked.
    4. INJECTED INSULIN — onset/peak/end curves per insulin type, offset by
       time already elapsed since injection.
    5. WEIGHT-ADJUSTED SENSITIVITY — insulin effect scales with body weight.
    """

    weight_kg = weight_kg if weight_kg and weight_kg > 0 else 70.0

    # ── 1. Carb excursion ────────────────────────────────────────────────────
    carb_factor = {
        "No Diabetes":     1.1,
        "Prediabetes":     1.6,
        "Type 2 Diabetes": 2.2,
        "Type 1 Diabetes": 3.0,
    }.get(diabetes_type, 1.6)

    carb_peak_rise = carbs_g * carb_factor
    carb_profile   = CARB_RESPONSE_PROFILE.get(diabetes_type, CARB_RESPONSE_PROFILE["Prediabetes"])
    meal_elapsed_min = time_since_meal_hr * 60.0

    def _carb_delta_at(future_min: float) -> float:
        """Change in carb excursion from NOW to NOW+future_min.
        Negative if we are already past the peak and coming back down."""
        at_future = _carb_excursion_fraction(
            meal_elapsed_min + future_min, carb_profile["peak"], carb_profile["decay"])
        at_now    = _carb_excursion_fraction(
            meal_elapsed_min, carb_profile["peak"], carb_profile["decay"])
        return carb_peak_rise * (at_future - at_now)

    # ── 2. BMR burn ──────────────────────────────────────────────────────────
    bmr_kcal_day = _estimate_bmr(weight_kg, age, gender)
    # FIX: glucose isn't confined to blood plasma alone — it's buffered across
    # extracellular fluid (~2 dL per kg body weight, ~14 L for a 70kg person),
    # roughly 3x the old blood-plasma-only volume. Using too small a volume
    # made a tiny daily calorie deficit look like a 50+ mg/dL crash by 2
    # hours, which instantly tripped the safety floor below and made every
    # other effect (exercise, time) invisible regardless of duration/timepoint.
    glucose_distribution_dl = max(60.0, weight_kg * 2.0)
    HEPATIC_COMP = 0.03   # liver replaces ~97% of burned glucose from glycogen

    def _bmr_drop(minutes: float) -> float:
        kcal  = bmr_kcal_day * (minutes / 1440)
        grams = (kcal / 4.0) * HEPATIC_COMP
        return (grams * 1000) / glucose_distribution_dl

    # ── 3. Exercise effect ───────────────────────────────────────────────────
    # Active glucose uptake rate (mg/dL per minute of exercise), by intensity.
    # Calibrated: 30 min light = ~9 mg/dL; moderate = ~21; intense = ~36.
    exercise_rate = {
        "No Exercise":                      0.0,
        "Light (walking, yoga)":            0.30,
        "Moderate (jogging, cycling)":      0.70,
        "Intense (running, gym, sports)":   1.20,
    }.get(exercise_type, 0.0)

    # Post-exercise afterburn: muscles keep absorbing glucose for hours to
    # refill glycogen. Modelled as a decaying extra uptake that halves every
    # 90 minutes. We assume exercise ended ~1 hour before 'now'.
    #
    # FIX: previously `exercise_duration_min` was only checked against 0 to
    # decide whether to apply any effect at all — the actual number of
    # minutes exercised never entered the magnitude calculation, so sliding
    # the duration input around had zero effect on the prediction. Now the
    # afterburn magnitude scales with `duration_factor`: 30 min is treated
    # as the baseline (matches the old fixed effect), more minutes produce
    # a proportionally bigger afterburn, capped at 90 min so an extreme
    # duration doesn't produce an unrealistic runaway drop.
    def _exercise_drop(future_min: float) -> float:
        if exercise_duration_min <= 0 or exercise_type == "No Exercise":
            return 0.0
        hours_post = 1.0 + (future_min / 60.0)   # 1 hr elapsed + future window
        duration_factor = min(exercise_duration_min, 90.0) / 30.0
        afterburn = exercise_rate * 0.30 * duration_factor * (0.5 ** (hours_post / 1.5))
        return afterburn * future_min

    # ── 4. Injected insulin ──────────────────────────────────────────────────
    insulin_factor_map = {
        "No Insulin":                           0,
        "Rapid-Acting (e.g., Lispro, Aspart)": 45,
        "Short-Acting (Regular)":               35,
        "Intermediate-Acting (NPH)":            25,
        "Long-Acting (Glargine, Detemir)":      20,
        "Mixed Insulin (70/30)":                30,
    }
    weight_adj           = max(0.6, min(1.6, 70.0 / weight_kg))
    factor_per_unit      = insulin_factor_map.get(insulin_type, 0) * weight_adj
    total_insulin_effect = factor_per_unit * (insulin_dose or 0)
    ins_profile          = INSULIN_ACTION_PROFILE.get(insulin_type, INSULIN_ACTION_PROFILE["No Insulin"])
    elapsed_min          = max(0.0, time_since_injection_hr) * 60.0

    # ── 5. Combine all effects ───────────────────────────────────────────────
    predictions = {}
    for t in (30, 60, 90, 120):
        carb_delta = _carb_delta_at(t)

        already_delivered = _cumulative_insulin_fraction(
            elapsed_min, ins_profile["onset"], ins_profile["peak"], ins_profile["end"])
        delivered_by_t = _cumulative_insulin_fraction(
            elapsed_min + t, ins_profile["onset"], ins_profile["peak"], ins_profile["end"])
        insulin_delta = total_insulin_effect * max(0.0, delivered_by_t - already_delivered)

        bmr_delta      = _bmr_drop(t)
        exercise_delta = _exercise_drop(t)

        predicted = current_glucose + carb_delta - insulin_delta - bmr_delta - exercise_delta

        # Floor: liver prevents glucose dropping below ~88-95% of fasting
        # baseline unless active insulin is genuinely causing hypoglycemia
        fasting_floor = current_glucose * 0.88 if insulin_delta > 5 else current_glucose * 0.95
        predicted = max(fasting_floor, predicted)
        predictions[t] = round(min(600.0, predicted), 1)

    return predictions


def health_score(
    glucose: float,
    bmi: float,
    diabetes_type: str,
    predicted_peak: float,
    carbs: float,
) -> tuple[float, str]:
    """Compute a 0–100 health score and risk category."""
    score = 100.0

    # Glucose penalty
    if glucose < 70 or glucose > 180:   score -= 25
    elif glucose < 80 or glucose > 140: score -= 12
    elif glucose < 90 or glucose > 120: score -= 5

    # Predicted peak penalty
    if predicted_peak > 200: score -= 20
    elif predicted_peak > 160: score -= 10

    # BMI penalty
    if bmi < 16 or bmi >= 35:   score -= 20
    elif bmi < 18.5 or bmi >= 30: score -= 10
    elif bmi < 17 or bmi >= 27: score -= 4

    # Diabetes type penalty
    dm_penalty = {"No Diabetes": 0, "Prediabetes": 8, "Type 2 Diabetes": 15, "Type 1 Diabetes": 18}
    score -= dm_penalty.get(diabetes_type, 0)

    # High-carb meal penalty
    if carbs > 80: score -= 10
    elif carbs > 50: score -= 5

    score = max(0, min(100, score))

    if score >= 75:  risk = "Low Risk"
    elif score >= 50: risk = "Medium Risk"
    else:             risk = "High Risk"

    return round(score, 1), risk


def get_recommendations(diabetes_type, glucose, predicted_peak, bmi, bmi_cat, carbs) -> list[str]:
    """Generate personalised AI recommendations."""
    recs = []

    # Glucose-based
    if glucose < 70:
        recs.append("⚠️ Current glucose appears low (hypoglycemia range). Consider consuming fast-acting carbohydrates like juice or glucose tablets immediately.")
    elif glucose > 180:
        recs.append("🔴 Current glucose is elevated. Ensure adequate hydration and consult your healthcare provider about medication adjustments.")
    elif 80 <= glucose <= 120:
        recs.append("✅ Your current glucose reading is within a healthy range. Maintain this with consistent meal timing and activity.")

    # Predicted peak
    if predicted_peak > 200:
        recs.append("📈 Glucose is predicted to rise significantly. A 15–20 minute post-meal walk can reduce peak glucose by up to 30%.")
    elif predicted_peak > 160:
        recs.append("📊 Moderate glucose rise predicted. Monitor closely and consider light physical activity after eating.")

    # Diabetes-specific
    if diabetes_type == "Type 1 Diabetes":
        recs.append("💉 As a Type 1 diabetic, consistent carb-counting and insulin-to-carb ratio management is essential. Discuss your I:C ratio with your endocrinologist.")
    elif diabetes_type == "Type 2 Diabetes":
        recs.append("🥗 For Type 2 management, reducing refined carbohydrates and increasing dietary fibre can significantly improve glucose control.")
    elif diabetes_type == "Prediabetes":
        recs.append("🌿 Prediabetes can often be reversed with lifestyle changes. Aim for 150 minutes of moderate exercise per week and reduce sugar intake.")
    else:
        recs.append("✅ No diabetes detected. Maintain a balanced diet and active lifestyle to prevent future risk.")

    # BMI-based
    if bmi_cat == "Obese":
        recs.append("⚖️ BMI indicates obesity, which significantly increases insulin resistance. A 5–10% weight reduction can improve glucose sensitivity meaningfully.")
    elif bmi_cat == "Overweight":
        recs.append("⚖️ Slightly elevated BMI noted. Regular cardiovascular exercise (30 min/day) can help improve metabolic health.")
    elif bmi_cat == "Underweight":
        recs.append("⚖️ BMI indicates underweight status. Adequate caloric intake with balanced nutrition is important for metabolic function.")

    # Carb-based
    if carbs > 80:
        recs.append("🍽️ High carbohydrate intake detected. Consider splitting this meal into smaller portions and pairing carbs with protein and healthy fats to blunt glucose spikes.")
    elif carbs > 50:
        recs.append("🥦 Moderate carb load. Including non-starchy vegetables can help slow carbohydrate absorption.")

    # General wellness
    recs.append("💧 Staying well-hydrated (8–10 glasses of water daily) supports kidney function and glucose regulation.")
    recs.append("😴 Quality sleep (7–9 hours) is crucial for glucose regulation. Poor sleep is linked to increased insulin resistance.")

    return recs[:7]  # Cap at 7 recommendations


def generate_pdf_report(
    patient: dict,
    nutrition: dict,
    glucose_now: float,
    predictions: dict,
    score: float,
    risk: str,
    recommendations: list[str],
    bmi: float,
    bmi_cat: str,
) -> bytes:
    """Generate a professional PDF health report using ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    elements = []

    # ── Color palette ──
    CYAN   = colors.HexColor('#00d9ff')
    PURPLE = colors.HexColor('#1e90ff')
    DARK   = colors.HexColor('#0f172a')
    SLATE  = colors.HexColor('#1e293b')
    LIGHT  = colors.HexColor('#e2e8f0')
    MUTED  = colors.HexColor('#64748b')
    RED    = colors.HexColor('#ff3b3b')
    GREEN  = colors.HexColor('#00e676')
    AMBER  = colors.HexColor('#ffd60a')

    risk_color = {"Low Risk": GREEN, "Medium Risk": AMBER, "High Risk": RED}.get(risk, AMBER)

    # ── Styles ──
    title_style = ParagraphStyle('Title', parent=styles['Title'],
        fontSize=26, textColor=CYAN, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'],
        fontSize=9, textColor=MUTED, alignment=TA_CENTER, spaceAfter=2)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'],
        fontSize=13, textColor=CYAN, fontName='Helvetica-Bold',
        spaceBefore=16, spaceAfter=8, borderPad=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#334155'),
        spaceAfter=6, leading=16)
    rec_style = ParagraphStyle('Rec', parent=styles['Normal'],
        fontSize=9.5, textColor=colors.HexColor('#1e293b'),
        spaceAfter=5, leading=15, leftIndent=10)
    disclaimer_style = ParagraphStyle('Dis', parent=styles['Normal'],
        fontSize=8, textColor=RED, alignment=TA_CENTER,
        spaceBefore=10, spaceAfter=4, fontName='Helvetica-Bold')

    def spacer(h=0.3): return Spacer(1, h*cm)
    def hr(): return HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=8, spaceBefore=4)

    # ══ HEADER ══
    elements.append(Paragraph("🩺 GLUCOVISION AI", title_style))
    elements.append(Paragraph("AI-Powered Personalized Diabetes Monitoring & Glucose Prediction", subtitle_style))
    elements.append(Paragraph(f"Report Generated: {datetime.now().strftime('%B %d, %Y  |  %H:%M')}", subtitle_style))
    elements.append(spacer(0.4))
    elements.append(hr())

    # ── DISCLAIMER ──
    elements.append(Paragraph(
        "⚠️  EDUCATIONAL PROTOTYPE ONLY — NOT INTENDED FOR DIAGNOSIS, TREATMENT, OR MEDICAL DECISION MAKING",
        disclaimer_style))
    elements.append(hr())

    # ══ PATIENT INFORMATION ══
    elements.append(Paragraph("PATIENT PROFILE", section_style))
    p = patient
    patient_data = [
        ['Full Name', p.get('name','N/A'),   'Age',    f"{p.get('age','N/A')} years"],
        ['Gender',   p.get('gender','N/A'),  'Weight', f"{p.get('weight','N/A')} kg"],
        ['Height',   f"{p.get('height','N/A')} cm", 'Diabetes Status', p.get('diabetes','N/A')],
        ['BMI',      f"{bmi}",               'BMI Category', bmi_cat],
    ]
    t = Table(patient_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#eff6ff')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#eff6ff')),
        ('TEXTCOLOR',  (0,0), (0,-1), PURPLE),
        ('TEXTCOLOR',  (2,0), (2,-1), PURPLE),
        ('FONTNAME',   (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',   (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING',    (0,0), (-1,-1), 6),
    ]))
    elements.append(t)
    elements.append(spacer())

    # ══ GLUCOSE METRICS ══
    elements.append(Paragraph("GLUCOSE MONITORING", section_style))

    def glucose_status(value):
        """Return (status_label, status_color) for a glucose reading."""
        if value < 70:
            return 'Low', RED
        elif value <= 140:
            return 'Normal', GREEN
        elif value <= 180:
            return 'Moderate', AMBER
        else:
            return 'High', RED

    rows_meta = [
        ('Current Glucose',    glucose_now),
        ('Predicted @ 30 min', predictions.get(30,  glucose_now)),
        ('Predicted @ 60 min', predictions.get(60,  glucose_now)),
        ('Predicted @ 90 min', predictions.get(90,  glucose_now)),
        ('Predicted @ 120 min',predictions.get(120, glucose_now)),
    ]

    glucose_data = [['Metric', 'Value', 'Status']]
    status_colors = []  # parallel list of colors for each data row's Status cell
    for label, val in rows_meta:
        status_label, status_color = glucose_status(val)
        glucose_data.append([label, f"{val} mg/dL", status_label])
        status_colors.append(status_color)

    gt = Table(glucose_data, colWidths=[5*cm, 5.5*cm, 7.5*cm])
    gt_style = [
        ('BACKGROUND', (0,0), (-1,0), DARK),
        ('TEXTCOLOR',  (0,0), (-1,0), CYAN),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING',    (0,0), (-1,-1), 7),
        ('ALIGN',      (1,0), (2,-1), 'CENTER'),
        ('FONTNAME',   (2,1), (2,-1), 'Helvetica-Bold'),
    ]
    # Color each Status cell to match its row (row index i+1 since row 0 is the header)
    for i, status_color in enumerate(status_colors):
        gt_style.append(('TEXTCOLOR', (2, i+1), (2, i+1), status_color))
    gt.setStyle(TableStyle(gt_style))
    elements.append(gt)
    elements.append(spacer())

    # ══ NUTRITION SUMMARY ══
    elements.append(Paragraph("NUTRITION SUMMARY", section_style))
    nut_data = [
        ['Nutrient', 'Amount', 'Daily % (approx.)'],
        ['Total Calories', f"{nutrition.get('calories',0):.0f} kcal",
         f"{nutrition.get('calories',0)/2000*100:.0f}%"],
        ['Carbohydrates', f"{nutrition.get('carbs',0):.1f} g",
         f"{nutrition.get('carbs',0)/300*100:.0f}%"],
        ['Protein',        f"{nutrition.get('protein',0):.1f} g",
         f"{nutrition.get('protein',0)/50*100:.0f}%"],
        ['Fat',            f"{nutrition.get('fat',0):.1f} g",
         f"{nutrition.get('fat',0)/65*100:.0f}%"],
    ]
    nt = Table(nut_data, colWidths=[5*cm, 5.5*cm, 7.5*cm])
    nt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), DARK),
        ('TEXTCOLOR',  (0,0), (-1,0), CYAN),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING',    (0,0), (-1,-1), 7),
        ('ALIGN',      (1,0), (2,-1), 'CENTER'),
    ]))
    elements.append(nt)
    elements.append(spacer())

    # ══ HEALTH SCORE ══
    elements.append(Paragraph("HEALTH ANALYTICS", section_style))
    score_data = [
        ['Health Score', f"{score} / 100", 'Risk Category', risk],
    ]
    st2 = Table(score_data, colWidths=[4*cm, 5*cm, 4*cm, 5*cm])
    st2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4') if risk=='Low Risk'
            else (colors.HexColor('#fffbeb') if risk=='Medium Risk' else colors.HexColor('#fef2f2'))),
        ('FONTNAME',   (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 11),
        ('TEXTCOLOR',  (1,0), (1,0), GREEN if risk=='Low Risk' else (AMBER if risk=='Medium Risk' else RED)),
        ('TEXTCOLOR',  (3,0), (3,0), GREEN if risk=='Low Risk' else (AMBER if risk=='Medium Risk' else RED)),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING',    (0,0), (-1,-1), 10),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(st2)
    elements.append(spacer())

    # ══ RECOMMENDATIONS ══
    elements.append(Paragraph("AI HEALTH RECOMMENDATIONS", section_style))
    for i, rec in enumerate(recommendations, 1):
        clean = rec.replace('⚠️','').replace('🔴','').replace('✅','').replace('📈','') \
                   .replace('📊','').replace('💉','').replace('🥗','').replace('🌿','') \
                   .replace('⚖️','').replace('🍽️','').replace('🥦','').replace('💧','') \
                   .replace('😴','').strip()
        elements.append(Paragraph(f"{i}. {clean}", rec_style))

    elements.append(spacer(0.5))
    elements.append(hr())

    # ══ FOOTER ══
    elements.append(Paragraph(
        "⚠️ DISCLAIMER: This report is generated by an educational AI prototype. "
        "It is NOT a medical diagnosis and should NOT be used for medical decision-making. "
        "Always consult a qualified healthcare professional for medical advice.",
        disclaimer_style))
    elements.append(Paragraph(
        "GlucoVision AI — Educational Prototype | Science Fair Project",
        subtitle_style))

    doc.build(elements)
    buf.seek(0)
    return buf.read()


# ─── PLOTLY CHART HELPERS ─────────────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor='rgba(10,14,26,0)',
    plot_bgcolor='rgba(10,14,26,0)',
    font=dict(family='Inter', color='#94a3b8', size=11),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor='rgba(0,217,255,0.15)', linecolor='rgba(0,217,255,0.25)', zerolinecolor='rgba(0,0,0,0)'),
    yaxis=dict(gridcolor='rgba(0,217,255,0.15)', linecolor='rgba(0,217,255,0.25)', zerolinecolor='rgba(0,0,0,0)'),
)


def glucose_trend_chart(glucose_now: float, predictions: dict) -> go.Figure:
    times = [0, 30, 60, 90, 120]
    values = [glucose_now] + [predictions[t] for t in [30, 60, 90, 120]]
    labels = ['Now', '30m', '60m', '90m', '2hr']

    fig = go.Figure()

    # Normal range band
    fig.add_hrect(y0=70, y1=140, fillcolor='rgba(0,230,118,0.12)',
                  line_color='rgba(0,230,118,0.25)', annotation_text='Normal', annotation_position='right')

    # Prediction line
    fig.add_trace(go.Scatter(
        x=labels, y=values, mode='lines+markers',
        line=dict(color='#00d9ff', width=3, shape='spline'),
        marker=dict(size=9, color='#00d9ff', line=dict(color='#e2e8f0', width=2)),
        fill='tozeroy',
        fillcolor='rgba(0,217,255,0.12)',
        name='Glucose',
    ))
    fig.update_layout(**CHART_LAYOUT, title=dict(
        text='Glucose Trend Forecast', font=dict(size=14, color='#e2e8f0'), x=0.5))
    fig.update_yaxes(title_text='mg/dL')
    fig.update_xaxes(title_text='Time')
    return fig


def nutrition_pie_chart(carbs: float, protein: float, fat: float) -> go.Figure:
    if carbs + protein + fat == 0:
        carbs, protein, fat = 1, 1, 1
    fig = go.Figure(go.Pie(
        labels=['Carbohydrates', 'Protein', 'Fat'],
        values=[carbs, protein, fat],
        hole=0.55,
        marker=dict(colors=['#1e90ff', '#00d9ff', '#a855f7'],
                    line=dict(color='#0a0e1a', width=2)),
        textfont=dict(color='#e2e8f0', size=11),
    ))
    fig.update_layout(**CHART_LAYOUT, title=dict(
        text='Macronutrient Breakdown', font=dict(size=14, color='#e2e8f0'), x=0.5),
        showlegend=True,
        legend=dict(orientation='h', y=-0.1, font=dict(color='#94a3b8')))
    return fig


def risk_gauge(score: float, risk: str) -> go.Figure:
    color = '#00e676' if risk == 'Low Risk' else ('#ffd60a' if risk == 'Medium Risk' else '#ff3b3b')
    fig = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=score,
        domain={'x': [0,1], 'y': [0,1]},
        number={'font': {'size': 36, 'color': color, 'family': 'Space Grotesk'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#475569', 'tickfont': {'color': '#475569'}},
            'bar': {'color': color, 'thickness': 0.25},
            'bgcolor': 'rgba(15,23,42,0.5)',
            'borderwidth': 0,
            'steps': [
                {'range': [0,  50], 'color': 'rgba(255,59,59,0.15)'},
                {'range': [50, 75], 'color': 'rgba(255,214,10,0.15)'},
                {'range': [75, 100],'color': 'rgba(0,230,118,0.15)'},
            ],
            'threshold': {'line': {'color': color, 'width': 3},
                          'thickness': 0.8, 'value': score},
        },
        title={'text': 'Health Score', 'font': {'color': '#94a3b8', 'size': 13}},
    ))
    fig.update_layout(**CHART_LAYOUT, height=260)
    fig.update_layout(margin=dict(l=20, r=20, t=30, b=0))
    return fig


def calorie_summary_chart(food_log: list) -> go.Figure:
    if not food_log:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title=dict(text='No foods selected yet', font=dict(color='#475569'), x=0.5))
        return fig

    labels = [f['name'][:20] for f in food_log]
    cals   = [f['calories'] for f in food_log]
    fig = go.Figure(go.Bar(
        x=cals, y=labels, orientation='h',
        marker=dict(
            color=cals, colorscale='Viridis',
            line=dict(color='rgba(0,0,0,0)'),
        ),
        text=[f'{c:.0f} kcal' for c in cals],
        textposition='outside',
        textfont=dict(color='#e2e8f0'),
    ))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text='Calorie Breakdown by Food', font=dict(size=14, color='#e2e8f0'), x=0.5),
        xaxis_title='Calories (kcal)',
        height=max(250, 60*len(food_log)))
    return fig


def classify_three_month_glucose(avg_glucose: float) -> tuple[str, float, str, str]:
    """
    Estimate a long-term glucose classification from a 3-month average
    reading, using the standard ADA relationship between average glucose
    and HbA1c (the real blood test doctors use, since glucose binds to
    hemoglobin and red blood cells live ~3 months):

        eAG (mg/dL) = 28.7 × HbA1c(%) − 46.7   →   HbA1c = (eAG + 46.7) / 28.7

    Standard diagnostic cut-offs (ADA): Normal <5.7%, Prediabetes 5.7–6.4%,
    Diabetes ≥6.5%. This is an educational ESTIMATE based on self-reported
    readings, not an actual lab HbA1c blood test.
    """
    estimated_a1c = round((avg_glucose + 46.7) / 28.7, 2)
    if estimated_a1c < 5.7:
        return "Likely Normal", estimated_a1c, "risk-low", "🟢"
    elif estimated_a1c < 6.5:
        return "Likely Prediabetes", estimated_a1c, "risk-medium", "🟡"
    else:
        return "Likely Diabetes Range", estimated_a1c, "risk-high", "🔴"


def three_month_trend_chart(dates, values) -> go.Figure:
    """Plot self-reported glucose readings over time against standard
    reference bands, so the trend and classification are visually linked."""
    fig = go.Figure()

    fig.add_hrect(y0=40,  y1=117, fillcolor='rgba(0,230,118,0.10)', line_color='rgba(0,230,118,0.2)',
                  annotation_text='Normal range', annotation_position='right',
                  annotation_font_color='#00e676', annotation_font_size=10)
    fig.add_hrect(y0=117, y1=140, fillcolor='rgba(255,214,10,0.10)', line_color='rgba(255,214,10,0.2)',
                  annotation_text='Prediabetes range', annotation_position='right',
                  annotation_font_color='#ffd60a', annotation_font_size=10)
    fig.add_hrect(y0=140, y1=300, fillcolor='rgba(255,59,59,0.10)', line_color='rgba(255,59,59,0.2)',
                  annotation_text='Diabetes range', annotation_position='right',
                  annotation_font_color='#ff3b3b', annotation_font_size=10)

    fig.add_trace(go.Scatter(
        x=dates, y=values, mode='lines+markers',
        line=dict(color='#00d9ff', width=3),
        marker=dict(size=9, color='#00d9ff', line=dict(color='#ffffff', width=1.5)),
        name='Glucose Reading',
    ))
    fig.update_layout(**CHART_LAYOUT, title=dict(
        text='3-Month Glucose History', font=dict(size=14, color='#ffffff'), x=0.5))
    fig.update_yaxes(title_text='mg/dL')
    fig.update_xaxes(title_text='Date')
    return fig


# ─── PREMIUM FEATURES ───────────────────────────────────────────────────────────

def render_diet_plan(diabetes_type: str, bmi_cat: str, risk: str):
    """Rule-based AI diet plan built from the same health report (diabetes
    status, BMI category, risk level) computed earlier in the app."""
    st.markdown("#### 🥗 Personalised AI Diet Plan")
    st.caption("Generated from your health report: diabetes status, BMI category, and risk level.")

    if risk == "High Risk" or diabetes_type in ("Type 1 Diabetes", "Type 2 Diabetes"):
        plan_label = "Low-Carb Plan"
        pool = [k for k, v in FOOD_DB.items() if v["carbs"] <= 15]
    elif risk == "Medium Risk" or bmi_cat in ("Overweight", "Obese"):
        plan_label = "Moderate-Carb Plan"
        pool = [k for k, v in FOOD_DB.items() if 8 <= v["carbs"] <= 25]
    else:
        plan_label = "Balanced Plan"
        pool = list(FOOD_DB.keys())

    if not pool:
        pool = list(FOOD_DB.keys())

    seed = abs(hash(st.session_state.get("user_key", "guest"))) % (2**32)
    rng = np.random.default_rng(seed=seed)
    meal_slots = {
        "🌅 Breakfast": 2,
        "🍛 Lunch": 2,
        "🌙 Dinner": 2,
        "🍎 Snack": 1,
    }
    st.markdown(f"**Plan Type:** {plan_label} &nbsp;|&nbsp; **Based on:** {diabetes_type}, {bmi_cat} BMI, {risk}")
    for meal, n in meal_slots.items():
        n = min(n, len(pool))
        items = rng.choice(pool, size=n, replace=False)
        st.markdown(f"**{meal}**")
        for it in items:
            info = FOOD_DB[it]
            st.markdown(f"- {it} — {info['calories']:.0f} kcal, {info['carbs']:.0f}g carbs, {info['protein']:.0f}g protein")

    st.info("💡 This is a rule-based educational suggestion, not a clinical diet prescription. Consult a registered dietitian for a medically supervised plan.")


def render_mbti_calculator():
    """Simple 4-question MBTI-style personality self-assessment."""
    st.markdown("#### 🧠 MBTI Personality Calculator")
    st.caption("Understanding your personality style can help tailor how you approach health routines.")

    q1 = st.radio("At a party, you tend to:",
                  ["Mingle with lots of people (E)", "Stick with a few close friends (I)"], key="mbti_q1")
    q2 = st.radio("You prefer information that is:",
                  ["Concrete and factual (S)", "Abstract and theoretical (N)"], key="mbti_q2")
    q3 = st.radio("When deciding, you rely more on:",
                  ["Logic and consistency (T)", "Values and people impact (F)"], key="mbti_q3")
    q4 = st.radio("You prefer your days to be:",
                  ["Planned and structured (J)", "Flexible and spontaneous (P)"], key="mbti_q4")

    if st.button("🔮 Calculate My MBTI Type", key="mbti_calc_btn"):
        mbti = ("E" if "(E)" in q1 else "I") + ("S" if "(S)" in q2 else "N") + \
               ("T" if "(T)" in q3 else "F") + ("J" if "(J)" in q4 else "P")
        trait_desc = {
            "E": "outgoing, energised by others", "I": "reflective, energised by solitude",
            "S": "detail-oriented and practical", "N": "idea-driven and big-picture",
            "T": "logical and objective", "F": "empathetic and values-driven",
            "J": "structured and routine-loving", "P": "flexible and spontaneous",
        }
        st.success(f"### Your Type: {mbti}")
        st.write(", ".join(trait_desc[c] for c in mbti).capitalize() + ".")
        tip = ("Structured types often do well with fixed meal and medication schedules — "
               "try recurring reminders." if mbti[3] == "J" else
               "Flexible types may do better pairing glucose checks with an existing daily "
               "habit, rather than a rigid schedule.")
        st.info(f"💡 Wellness tip: {tip}")


def render_sleep_quality():
    """Sleep quality score — sleep affects insulin sensitivity and glucose control."""
    st.markdown("#### 😴 Sleep Quality Analyzer")
    st.caption("Sleep quality strongly affects insulin sensitivity and glucose control.")

    hours     = st.slider("Average hours of sleep per night", 0.0, 12.0, 7.0, 0.5, key="sleep_hours")
    wakeups   = st.number_input("Times you wake up during the night", 0, 10, 1, key="sleep_wakeups")
    refreshed = st.slider("How refreshed do you feel on waking? (1=Exhausted, 10=Fully Refreshed)",
                          1, 10, 6, key="sleep_refreshed")

    if st.button("💤 Calculate Sleep Score", key="sleep_calc_btn"):
        score = 100.0
        if hours < 6 or hours > 9: score -= 25
        elif hours < 7 or hours > 8.5: score -= 10
        score -= wakeups * 6
        score += (refreshed - 5) * 4
        score = max(0, min(100, round(score)))

        st.metric("😴 Sleep Quality Score", f"{score}/100")
        if score >= 75:
            st.success("✅ Good sleep quality. Consistent sleep supports stable glucose levels.")
        elif score >= 50:
            st.warning("⚠️ Moderate sleep quality. A consistent bedtime and less screen time before bed may help.")
        else:
            st.error("🚨 Poor sleep quality detected. Sleep deprivation can raise insulin resistance — consider consulting a doctor if this persists.")


def render_stress_assessment():
    """Short Likert-scale stress assessment — chronic stress raises cortisol,
    which can elevate blood glucose."""
    st.markdown("#### 💆 Stress Level Assessment")
    st.caption("Chronic stress raises cortisol, which can elevate blood glucose.")

    questions = [
        "I feel overwhelmed by daily responsibilities.",
        "I have trouble relaxing.",
        "I feel anxious about my health.",
        "I have difficulty concentrating.",
        "I feel irritable or on edge.",
    ]
    total = 0
    for i, q in enumerate(questions):
        total += st.slider(q, 1, 5, 3, key=f"stress_q{i}")

    if st.button("🧘 Calculate Stress Score", key="stress_calc_btn"):
        pct = round((total / (5 * 5)) * 100)
        st.metric("💆 Stress Level", f"{pct}%")
        if pct < 40:
            st.success("✅ Low stress levels. Keep up your current coping strategies.")
        elif pct < 70:
            st.warning("⚠️ Moderate stress. Consider mindfulness, light exercise, or breathing exercises.")
        else:
            st.error("🚨 High stress levels detected. Elevated stress can worsen glucose control — consider speaking with a healthcare provider or counsellor.")


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo">
            <div style="font-size:2.2rem; margin-bottom:0.3rem">🩺</div>
            <div class="sidebar-logo-title">GlucoVision AI</div>
            <div class="sidebar-logo-sub">Glucose Prediction System</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📋 Navigation")
        sections = [
            ("👤", "Patient Profile"),
            ("💉", "Insulin Management"),
            ("🍽️", "Food Intelligence"),
            ("🔬", "Digital Twin"),
            ("📈", "AI Predictions"),
            ("📊", "Visualizations"),
            ("🧠", "Health Analytics"),
            ("💡", "Recommendations"),
            ("🔮", "Future Insights"),
            ("📄", "Export Report"),
        ]
        for icon, name in sections:
            st.markdown(f'<div class="nav-pill">{icon} &nbsp;{name}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 👤 My Account")
        st.markdown(f"**{st.session_state.get('username', '')}**")
        if st.session_state.get("premium"):
            st.markdown('<span class="risk-low">⭐ PREMIUM MEMBER</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="risk-medium">🆓 FREE PLAN</span>', unsafe_allow_html=True)
            if st.button("⭐ Upgrade to Premium", key="upgrade_btn_sidebar", use_container_width=True):
                set_premium(st.session_state.user_key, True)
                st.session_state.premium = True
                st.success("🎉 You're now Premium!")
                st.rerun()
        if st.button("🚪 Log Out", key="logout_btn", use_container_width=True):
            for k in ("authenticated", "username", "user_key", "premium", "profile"):
                st.session_state.pop(k, None)
            st.rerun()

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.72rem; color:#475569; text-align:center; padding:0.5rem 0;">
            <strong style="color:#ff3b3b">⚠️ Educational Prototype</strong><br>
            Not a medical device.<br>
            Always consult your doctor.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.7rem; color:#334155; text-align:center;">
            GlucoVision AI v1.0<br>
            Science Fair Edition 2025
        </div>
        """, unsafe_allow_html=True)


# ─── MAIN APP ─────────────────────────────────────────────────────────────────

def main():
    if not st.session_state.get("authenticated"):
        render_auth_page()
        return

    render_sidebar()

    # ── Hero Header ──
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title">🩺 GlucoVision AI</div>
        <div class="hero-subtitle">AI-Powered Personalized Diabetes Monitoring & Glucose Prediction System</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Disclaimer ──
    st.markdown("""
    <div class="disclaimer">
        ⚠️ <strong>EDUCATIONAL PROTOTYPE ONLY.</strong>
        This application is designed for science fair demonstration purposes.
        It is NOT intended for diagnosis, treatment, or any medical decision-making.
        Always consult a qualified healthcare professional for medical advice.
    </div>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 1 · PATIENT PROFILE
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-blue">
        <div class="section-icon">👤</div>
        <div class="section-title">SECTION 1 — Patient Profile</div>
    </div>
    """, unsafe_allow_html=True)

    saved_profile   = st.session_state.get("profile", {}) or {}
    gender_options   = ["Select Gender", "Male", "Female", "Other", "Prefer not to say"]
    diabetes_options = ["Select Status", "No Diabetes", "Prediabetes", "Type 1 Diabetes", "Type 2 Diabetes"]

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            name   = st.text_input("Full Name", value=saved_profile.get("name", ""), placeholder="Enter your name")
            age    = st.number_input("Age (years)", min_value=0, max_value=120,
                                     value=int(saved_profile.get("age", 0)),
                                     help="Enter your age in years")
            gender = st.selectbox("Gender", gender_options,
                                  index=gender_options.index(saved_profile["gender"])
                                  if saved_profile.get("gender") in gender_options else 0)
        with col2:
            weight = st.number_input("Weight (kg)", min_value=0.0, max_value=250.0,
                                     value=float(saved_profile.get("weight", 0.0)), step=0.5,
                                     help="Enter your weight in kilograms")
            height = st.number_input("Height (cm)", min_value=0.0, max_value=250.0,
                                     value=float(saved_profile.get("height", 0.0)), step=0.5,
                                     help="Enter your height in centimetres")
        with col3:
            diabetes_type = st.selectbox(
                "Diabetes Status", diabetes_options,
                index=diabetes_options.index(saved_profile["diabetes_type"])
                if saved_profile.get("diabetes_type") in diabetes_options else 0
            )

        bmi, bmi_cat = calculate_bmi(weight, height)
        bmi_color = {'Normal':'#00e676','Underweight':'#ffd60a','Overweight':'#ffd60a','Obese':'#ff3b3b'}.get(bmi_cat,'#94a3b8')

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("⚖️ BMI", f"{bmi}")
        col_b.metric("🏷️ BMI Category", bmi_cat)
        col_c.metric("🧬 Diabetes Status", diabetes_type.split()[0])

        if st.button("💾 Save Profile to My Account", key="save_profile_btn"):
            profile_to_save = {
                "name": name, "age": age, "gender": gender, "weight": weight,
                "height": height, "diabetes_type": diabetes_type,
                "bmi": bmi, "bmi_cat": bmi_cat, "updated_at": datetime.now().isoformat(),
            }
            update_user_record(st.session_state.user_key, {"profile": profile_to_save})
            st.session_state.profile = profile_to_save
            st.success("✅ Profile saved to your account — it'll be pre-filled next time you log in.")

        # ── 3-Month Glucose Trend & Classification (optional, HbA1c-style estimate) ──
        st.markdown("#### 📊 3-Month Glucose Trend Analysis <span style='font-size:0.7rem; color:#8b949e; font-weight:600'>(Optional)</span>", unsafe_allow_html=True)
        st.caption("Add glucose readings spread across the past ~3 months to estimate a long-term classification — similar to how a real HbA1c blood test works, since it reflects average glucose over that period.")

        if "glucose_history_df" not in st.session_state:
            st.session_state.glucose_history_df = pd.DataFrame({
                "Date": pd.Series(dtype="datetime64[ns]"),
                "Glucose (mg/dL)": pd.Series(dtype="float"),
            })

        edited_history = st.data_editor(
            st.session_state.glucose_history_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Date": st.column_config.DateColumn(
                    "Date", max_value=datetime.now().date(),
                    help="Date the reading was taken"),
                "Glucose (mg/dL)": st.column_config.NumberColumn(
                    "Glucose (mg/dL)", min_value=40, max_value=600,
                    help="Blood glucose reading in mg/dL"),
            },
            key="glucose_history_editor",
        )

        valid_readings = edited_history.dropna(subset=["Glucose (mg/dL)"])
        valid_readings = valid_readings[valid_readings["Glucose (mg/dL)"] > 0]

        three_month_avg = None
        three_month_a1c = None
        three_month_classification = None

        if len(valid_readings) > 0:
            three_month_avg = float(valid_readings["Glucose (mg/dL)"].mean())
            three_month_classification, three_month_a1c, risk_css_3mo, risk_icon_3mo = \
                classify_three_month_glucose(three_month_avg)

            col_3mo1, col_3mo2, col_3mo3 = st.columns(3)
            col_3mo1.metric("📈 3-Month Avg Glucose", f"{three_month_avg:.0f} mg/dL")
            col_3mo2.metric("🧪 Estimated HbA1c", f"{three_month_a1c}%")
            with col_3mo3:
                st.markdown(f"""
                <div style="padding-top:1.7rem; text-align:center">
                    <span class="{risk_css_3mo}">{risk_icon_3mo} {three_month_classification}</span>
                </div>
                """, unsafe_allow_html=True)

            if len(valid_readings) < 3:
                st.info("ℹ️ Add a few more readings spread across the past 3 months for a more reliable estimate.")

            if diabetes_type not in ("Select Status", "") and three_month_classification is not None:
                selected_simple = diabetes_type.replace("Type 1 ", "").replace("Type 2 ", "")
                if (("Normal" in three_month_classification and diabetes_type != "No Diabetes") or
                    ("Diabetes Range" in three_month_classification and diabetes_type in ("No Diabetes", "Prediabetes")) or
                    ("Prediabetes" in three_month_classification and diabetes_type not in ("Prediabetes",))):
                    st.warning(f"⚠️ This estimate ({three_month_classification}) differs from your selected status above ({diabetes_type}). Consider discussing this with a healthcare provider.")

            trend_sorted = valid_readings.sort_values("Date")
            st.plotly_chart(
                three_month_trend_chart(trend_sorted["Date"], trend_sorted["Glucose (mg/dL)"]),
                use_container_width=True, config={'displayModeBar': False}
            )

            st.caption("⚠️ This is an educational estimate based on the standard average-glucose-to-HbA1c relationship, calculated from self-reported readings — it is **not** an actual lab HbA1c test. Please consult a healthcare provider for real diagnosis.")
        else:
            st.caption("Add at least one glucose reading above (use the **+** row at the bottom of the table) to see your 3-month trend analysis.")

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 2 · INSULIN MANAGEMENT
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-red">
        <div class="section-icon">💉</div>
        <div class="section-title">SECTION 2 — Insulin Management</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if diabetes_type == "No Diabetes":
            insulin_type = "No Insulin"
            st.info("💡 No insulin required — patient has no diabetes.")
            st.write(f"**Insulin Type:** {insulin_type}")
        else:
            insulin_type = st.selectbox("Insulin Type", INSULIN_TYPES)

    with col2:
        if insulin_type == "No Insulin" or diabetes_type == "No Diabetes":
            insulin_dose = 0.0
            st.write("")
            st.write("**Insulin Dose:** N/A")
        else:
            insulin_dose = st.number_input("Insulin Dose (units)", min_value=0.0, max_value=100.0,
                                           value=0.0, step=0.5, help="Enter your insulin dose in units")
    with col3:
        if insulin_type == "No Insulin" or diabetes_type == "No Diabetes":
            time_since_injection = 0.0
            st.write("**Time Since Last Injection:** N/A")
        else:
            time_since_injection = st.number_input("Time Since Last Injection (hours)",
                                                    min_value=0.0, max_value=24.0, value=0.0, step=0.5,
                                                    help="Enter hours since your last injection")

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 3 · FOOD INTELLIGENCE SYSTEM
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-orange">
        <div class="section-icon">🍽️</div>
        <div class="section-title">SECTION 3 — Food Intelligence System</div>
    </div>
    """, unsafe_allow_html=True)

    st.info("🍽️ **Enter what you are eating RIGHT NOW (this one meal only)** — not your full day. The glucose prediction is based on this single meal's effect over the next 2 hours.")

    selected_foods = st.multiselect(
        "Select Foods Consumed",
        options=list(FOOD_DB.keys()),
        default=[],
        help="Select all foods you have consumed in this meal."
    )

    food_log = []
    total_cal = total_carbs = total_protein = total_fat = 0.0

    if selected_foods:
        st.markdown("**🔢 Set Quantity for Each Food:**")
        cols = st.columns(min(len(selected_foods), 3))
        for i, food_name in enumerate(selected_foods):
            with cols[i % 3]:
                qty = st.number_input(f"× {food_name.split('(')[0].strip()}", min_value=0.5, max_value=10.0,
                                      value=1.0, step=0.5, key=f"qty_{i}")
                fd = FOOD_DB[food_name]
                food_log.append({
                    'name': food_name.split('(')[0].strip(),
                    'qty': qty,
                    'calories': fd['calories'] * qty,
                    'carbs':    fd['carbs']    * qty,
                    'protein':  fd['protein']  * qty,
                    'fat':      fd['fat']      * qty,
                })
                total_cal     += fd['calories'] * qty
                total_carbs   += fd['carbs']    * qty
                total_protein += fd['protein']  * qty
                total_fat     += fd['fat']      * qty

        # Nutrition Summary
        st.markdown("**📊 Nutrition Summary:**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔥 Calories",      f"{total_cal:.0f} kcal")
        c2.metric("🍞 Carbohydrates", f"{total_carbs:.1f} g")
        c3.metric("💪 Protein",       f"{total_protein:.1f} g")
        c4.metric("🥑 Fat",           f"{total_fat:.1f} g")
    else:
        st.info("👆 Please select at least one food to see nutrition data.")

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 4 · METABOLIC DIGITAL TWIN
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-teal">
        <div class="section-icon">🔬</div>
        <div class="section-title">SECTION 4 — Metabolic Digital Twin</div>
    </div>
    """, unsafe_allow_html=True)

    current_glucose = st.slider(
        "🩸 Current Blood Glucose Level (mg/dL)",
        min_value=40, max_value=400, value=40, step=1,
        help="Drag the slider to enter your current fasting or post-meal glucose reading."
    )

    col_extra1, col_extra2, col_extra3 = st.columns(3)
    with col_extra1:
        time_since_meal_hr = st.number_input(
            "⏱️ Time Since Eating (hours)",
            min_value=0.0, max_value=12.0, value=0.0, step=0.25,
            help="How many hours ago did you eat this meal? 0 = just finished eating now."
        )
    with col_extra2:
        exercise_type = st.selectbox(
            "🏃 Exercise Done Today",
            ["No Exercise", "Light (walking, yoga)", "Moderate (jogging, cycling)", "Intense (running, gym, sports)"],
            help="Exercise directly lowers blood glucose by making muscles absorb it without insulin."
        )
    with col_extra3:
        exercise_duration_min = st.number_input(
            "⏳ Exercise Duration (minutes)",
            min_value=0, max_value=300, value=0, step=5,
            help="How many minutes of exercise did you do? Used to calculate how much glucose your muscles absorbed.",
            disabled=(exercise_type == "No Exercise")
        )

    predictions = glucose_prediction_model(
        current_glucose, total_carbs, diabetes_type, insulin_type, insulin_dose,
        time_since_injection_hr=time_since_injection, weight_kg=weight,
        age=int(age) if age and age > 0 else 35,
        gender=gender if gender not in ("Select Gender",) else "Male",
        calories_kcal=total_cal,
        time_since_meal_hr=time_since_meal_hr,
        exercise_type=exercise_type,
        exercise_duration_min=float(exercise_duration_min),
    )
    predicted_60 = predictions[60]

    hs, risk = health_score(current_glucose, bmi, diabetes_type, max(predictions.values()), total_carbs)

    # Twin panel — 6 metric cards
    st.markdown("**🖥️ Patient Digital Overview:**")
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    glucose_color = '#00e676' if 70 <= current_glucose <= 140 else ('#ffd60a' if current_glucose <= 180 else '#ff3b3b')
    pred_color    = '#00e676' if 70 <= predicted_60 <= 140    else ('#ffd60a' if predicted_60 <= 180    else '#ff3b3b')
    score_color   = '#00e676' if hs >= 75 else ('#ffd60a' if hs >= 50 else '#ff3b3b')

    for col, icon, value, label, color in [
        (c1, '🩸', f'{current_glucose}', 'Current Glucose', glucose_color),
        (c2, '📈', f'{predicted_60}',   'Predicted (60m)', pred_color),
        (c3, '🔥', f'{total_cal:.0f}',  'Calories (kcal)',  '#1e90ff'),
        (c4, '🍞', f'{total_carbs:.0f}','Carbs (g)',         '#a855f7'),
        (c5, '⚖️', f'{bmi}',            'BMI',               '#00d9ff'),
        (c6, '💯', f'{hs}',             'Health Score',      score_color),
    ]:
        col.markdown(f"""
        <div class="metric-card" style="border-color:{color}">
            <div class="metric-icon">{icon}</div>
            <div class="metric-value" style="color:{color}">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 5 · AI GLUCOSE PREDICTION TABLE
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-green">
        <div class="section-icon">📈</div>
        <div class="section-title">SECTION 5 — AI Glucose Prediction</div>
    </div>
    """, unsafe_allow_html=True)

    def glucose_status_label(value):
        """Same Low/Normal/Moderate/High thresholds used in the PDF report."""
        if value < 70:
            return '🔴 Low'
        elif value <= 140:
            return '🟢 Normal'
        elif value <= 180:
            return '🟡 Moderate'
        else:
            return '🟠 High'

    pred_df = pd.DataFrame({
        'Timepoint':      ['Now', '30 Minutes', '60 Minutes', '90 Minutes', '120 Minutes'],
        'Glucose (mg/dL)':[current_glucose, predictions[30], predictions[60], predictions[90], predictions[120]],
        'Status': [glucose_status_label(v) for v in
                   [current_glucose, predictions[30], predictions[60], predictions[90], predictions[120]]]
    })
    st.dataframe(pred_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 6 · ADVANCED VISUALIZATIONS
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-purple">
        <div class="section-icon">📊</div>
        <div class="section-title">SECTION 6 — Advanced Visualizations</div>
    </div>
    """, unsafe_allow_html=True)

    # Row 1: Glucose trend + Nutrition pie
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.plotly_chart(glucose_trend_chart(current_glucose, predictions),
                        use_container_width=True, config={'displayModeBar': False})
    with col_chart2:
        st.plotly_chart(nutrition_pie_chart(total_carbs, total_protein, total_fat),
                        use_container_width=True, config={'displayModeBar': False})

    # Row 2: Calorie summary
    st.plotly_chart(calorie_summary_chart(food_log),
                    use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 7 · AI HEALTH ANALYTICS
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-pink">
        <div class="section-icon">🧠</div>
        <div class="section-title">SECTION 7 — AI Health Analytics</div>
    </div>
    """, unsafe_allow_html=True)

    risk_css = {'Low Risk': 'risk-low', 'Medium Risk': 'risk-medium', 'High Risk': 'risk-high'}[risk]
    risk_icon = {'Low Risk': '🟢', 'Medium Risk': '🟡', 'High Risk': '🔴'}[risk]

    col_h1, col_h2, col_h3 = st.columns(3)
    col_h1.metric("🧮 Health Score", f"{hs} / 100")
    col_h2.metric("🎯 Risk Category", f"{risk_icon} {risk}")
    col_h3.metric("🩺 Diabetes Type", diabetes_type)

    # Risk gauge — single visual for the health score (replaces the old flat bar)
    col_gauge, col_space = st.columns([1, 1.5])
    with col_gauge:
        st.plotly_chart(risk_gauge(hs, risk),
                        use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 8 · AI RECOMMENDATIONS
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-yellow">
        <div class="section-icon">💡</div>
        <div class="section-title">SECTION 8 — AI Health Recommendations</div>
    </div>
    """, unsafe_allow_html=True)

    recs = get_recommendations(diabetes_type, current_glucose,
                               max(predictions.values()), bmi, bmi_cat, total_carbs)

    st.markdown(f"**Personalised for:** {name} &nbsp;|&nbsp; **Status:** {diabetes_type} &nbsp;|&nbsp; **Risk:** <span class='{risk_css}'>{risk_icon} {risk}</span>", unsafe_allow_html=True)
    st.write("")
    for i, rec in enumerate(recs):
        st.markdown(f'<div class="rec-card rc-{i % 7}">{rec}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════════
    # SECTION 9 · FUTURE HEALTH INSIGHT
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="section-header sh-purple">
        <div class="section-icon">🔮</div>
        <div class="section-title">SECTION 9 — Future Health Insight</div>
    </div>
    """, unsafe_allow_html=True)

    pred_120 = predictions[120]
    pct_change = ((pred_120 - current_glucose) / current_glucose) * 100 if current_glucose > 0 else 0
    direction  = "increase" if pct_change > 0 else "decrease"
    direction_icon = "📈" if pct_change > 0 else "📉"
    trend_color = '#ff3b3b' if (pct_change > 15 or pred_120 > 180) else ('#ffd60a' if pct_change > 5 else '#00e676')

    st.markdown(f"""
    <div class="insight-box">
        <div style="font-size:0.8rem; color:#64748b; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.5rem">
            {direction_icon} 2-Hour Glucose Forecast
        </div>
        <div class="insight-value" style="color:{trend_color}">{abs(pct_change):.1f}% {direction}</div>
        <div style="font-size:0.85rem; color:#94a3b8; margin-top:0.5rem; line-height:1.6">
            Based on current inputs, your glucose is predicted to
            <strong style="color:{trend_color}">{direction} by {abs(pct_change):.1f}%</strong>
            in the next 2 hours.<br>
            Current: <strong style="color:#00d9ff">{current_glucose} mg/dL</strong>
            → Predicted: <strong style="color:{trend_color}">{pred_120} mg/dL</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Contextual insight sentences
    if diabetes_type == "No Diabetes" and pct_change > 10:
        st.info("ℹ️ Even without diabetes, a significant post-meal glucose rise is normal. Your body will naturally bring levels back to baseline within 2–3 hours.")
    elif diabetes_type in ["Type 1 Diabetes", "Type 2 Diabetes"] and pred_120 > 180:
        st.warning("⚠️ Glucose is predicted to remain elevated. Consider consulting your healthcare team about adjusting carbohydrate intake or insulin dosage.")
    elif pred_120 < 70:
        st.error("🚨 Glucose may drop into hypoglycemia range. Monitor closely and have fast-acting carbohydrates (juice, glucose tablets) available.")

    st.markdown("---")
# SECTION 10 · EXPORT REPORT (PDF)
st.markdown("""
<div class="section-header sh-blue">
    <div class="section-icon">📄</div>
    <div class="section-title">SECTION 10 — Export Health Report</div>
</div>
""", unsafe_allow_html=True)

col_exp1, col_exp2 = st.columns([2, 1])
with col_exp1:
    st.markdown("""
    <div class="glass-card" style="padding:1.2rem">
        <strong style="color:#00d9ff">📥 Download PDF Health Report</strong><br>
        <span style="font-size:0.85rem; color:#64748b">
        Your personalised health report includes patient profile, nutrition summary,
        glucose predictions, health score, and AI recommendations.
        </span>
    </div>
    """, unsafe_allow_html=True)

with col_exp2:
    if st.button("📥 Generate & Download PDF", key="pdf_btn"):
        with st.spinner("🔄 Generating your personalised health report..."):
            patient_info = {
                'name': name, 'age': age, 'gender': gender,
                'weight': weight, 'height': height, 'diabetes': diabetes_type,
            }
            nutrition_summary = {
                'calories': total_cal, 'carbs': total_carbs,
                'protein': total_protein, 'fat': total_fat,
            }
            pdf_bytes = generate_pdf_report(
                patient=patient_info,
                nutrition=nutrition_summary,
                glucose_now=current_glucose,
                predictions=predictions,
                score=hs,
                risk=risk,
                recommendations=recs,
                bmi=bmi,
                bmi_cat=bmi_cat,
            )
            st.download_button(
                label="⬇️ Click to Download PDF",
                data=pdf_bytes,
                file_name=f"GlucoVision_Report_{name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                key="pdf_download",
            )
            st.success("✅ PDF generated successfully!")

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 11 · PREMIUM AI NUTRITION COACH
# ════════════════════════════════════════════════════════════════════════════

def _diet_seed(diabetes_type, bmi_cat, risk):
    raw = f"{diabetes_type}|{bmi_cat}|{risk}"
    return int(hashlib.md5(raw.encode("utf-8")).hexdigest(), 16) % (10**8)

def _safe_lower(x):
    return str(x).strip().lower()

def _normalize_food_item(item):
    if isinstance(item, dict):
        name = item.get("food_name") or item.get("name") or item.get("food") or item.get("item") or item.get("title") or "Food"
        category = item.get("category") or item.get("food_category") or item.get("type") or item.get("group") or "General"
        serving = item.get("serving_size") or item.get("serving") or item.get("portion") or item.get("portion_size") or "1 serving"
        calories = item.get("calories") or item.get("kcal") or item.get("energy") or 0
        protein = item.get("protein") or item.get("protein_g") or 0
        carbs = item.get("carbohydrates") or item.get("carbs") or item.get("carb") or item.get("carbohydrate") or 0
        fiber = item.get("fiber") or item.get("fibre") or 0
        gi = item.get("gi") or item.get("glycemic_index") or item.get("glycaemic_index")
        return {
            "name": str(name),
            "category": str(category),
            "serving": str(serving),
            "calories": float(calories) if calories not in [None, ""] else 0.0,
            "protein": float(protein) if protein not in [None, ""] else 0.0,
            "carbs": float(carbs) if carbs not in [None, ""] else 0.0,
            "fiber": float(fiber) if fiber not in [None, ""] else 0.0,
            "gi": float(gi) if gi not in [None, ""] else None,
        }
    vals = list(item) if hasattr(item, "__iter__") else [str(item)]
    return {
        "name": str(vals[0]) if len(vals) > 0 else "Food",
        "category": str(vals[1]) if len(vals) > 1 else "General",
        "serving": str(vals[2]) if len(vals) > 2 else "1 serving",
        "calories": float(vals[3]) if len(vals) > 3 and vals[3] not in [None, ""] else 0.0,
        "protein": float(vals[4]) if len(vals) > 4 and vals[4] not in [None, ""] else 0.0,
        "carbs": float(vals[5]) if len(vals) > 5 and vals[5] not in [None, ""] else 0.0,
        "fiber": float(vals[6]) if len(vals) > 6 and vals[6] not in [None, ""] else 0.0,
        "gi": float(vals[7]) if len(vals) > 7 and vals[7] not in [None, ""] and str(vals[7]) != "" else None,
    }

def _food_category(food):
    text = f"{food['name']} {food['category']}".lower()
    if any(k in text for k in ["egg", "paneer", "tofu", "lentil", "dal", "beans", "chicken", "fish", "curd", "yogurt", "milk", "soy", "sprout"]):
        return "protein"
    if any(k in text for k in ["salad", "spinach", "broccoli", "cauliflower", "cucumber", "tomato", "leafy", "vegetable", "veg", "greens"]):
        return "veg"
    if any(k in text for k in ["oats", "brown rice", "quinoa", "millet", "roti", "whole", "grain", "barley", "bread", "cereal"]):
        return "complex_carb"
    if any(k in text for k in ["nuts", "seeds", "almond", "walnut", "chia", "flax", "peanut", "pistachio"]):
        return "fat_snack"
    if any(k in text for k in ["apple", "guava", "berries", "orange", "pear", "papaya", "fruit"]):
        return "fruit"
    return "other"

def _goal_profile(diabetes_type, bmi_cat, risk):
    d = _safe_lower(diabetes_type)
    b = _safe_lower(bmi_cat)
    r = _safe_lower(risk)
    profile = {
        "calorie_mult": 1.0,
        "protein_mult": 1.0,
        "carb_mult": 1.0,
        "fiber_mult": 1.0,
        "water_l": 2.5,
        "goal_text": "Balanced nutrition.",
        "avoid": [],
        "prefer": [],
        "carb_cap": "moderate",
        "priority": [],
    }

    if "under" in b:
        profile.update({
            "calorie_mult": 1.2,
            "protein_mult": 1.25,
            "carb_mult": 1.1,
            "fiber_mult": 1.0,
            "goal_text": "Healthy weight gain with nutrient-dense meals.",
            "prefer": ["protein", "complex_carb", "fat_snack", "fruit"],
            "priority": ["calories", "protein"],
        })
    elif "normal" in b:
        profile.update({
            "calorie_mult": 1.0,
            "protein_mult": 1.05,
            "carb_mult": 1.0,
            "fiber_mult": 1.0,
            "goal_text": "Maintain balance with steady energy.",
            "prefer": ["protein", "veg", "complex_carb", "fruit"],
            "priority": ["balance"],
        })
    elif "over" in b:
        profile.update({
            "calorie_mult": 0.9,
            "protein_mult": 1.2,
            "carb_mult": 0.85,
            "fiber_mult": 1.25,
            "goal_text": "Support fat loss with controlled carbohydrates.",
            "prefer": ["protein", "veg", "complex_carb"],
            "avoid": ["fried", "sugary"],
            "priority": ["fiber", "protein", "calories"],
        })
    elif "obese" in b:
        profile.update({
            "calorie_mult": 0.8,
            "protein_mult": 1.25,
            "carb_mult": 0.75,
            "fiber_mult": 1.35,
            "goal_text": "Create a lower-calorie, high-fibre plan for weight loss.",
            "prefer": ["protein", "veg", "complex_carb"],
            "avoid": ["fried", "sugary", "refined"],
            "priority": ["fiber", "protein", "low_calorie"],
        })

    if "high" in r:
        profile.update({
            "carb_mult": profile["carb_mult"] * 0.8,
            "fiber_mult": profile["fiber_mult"] * 1.25,
            "goal_text": profile["goal_text"] + " Emphasis on low-GI foods and fibre.",
            "avoid": list(set(profile["avoid"] + ["sugary", "refined", "sweet"])),
            "prefer": list(set(profile["prefer"] + ["veg", "protein", "complex_carb"])),
            "carb_cap": "low",
            "priority": ["low_gi", "fiber", "carb_control"],
        })
    elif "low" in r:
        profile["goal_text"] = profile["goal_text"] + " Keep meals balanced and sustainable."

    if "type 1" in d or "type1" in d:
        profile["goal_text"] = profile["goal_text"] + " Use steady carbohydrate portions."
        profile["carb_cap"] = "moderate"
    elif "type 2" in d or "type2" in d:
        profile["goal_text"] = profile["goal_text"] + " Focus on fibre-rich, lower-GI choices."
        profile["avoid"] = list(set(profile["avoid"] + ["refined", "sugary"]))
    else:
        profile["goal_text"] = profile["goal_text"] + " Use broad healthy eating patterns."

    return profile

def _food_score(food, profile, meal_name, rng):
    cal = food["calories"]
    pro = food["protein"]
    carb = food["carbs"]
    fiber = food["fiber"]
    cat = _food_category(food)
    text = f"{food['name']} {food['category']}".lower()

    score = 0.0
    score += pro * 3.4 * profile["protein_mult"]
    score += fiber * 3.0 * profile["fiber_mult"]
    score -= cal * 0.018 / max(profile["calorie_mult"], 0.7)
    score -= max(carb - fiber, 0) * 0.9

    if cat == "protein":
        score += 10
    elif cat == "veg":
        score += 9
    elif cat == "complex_carb":
        score += 6
    elif cat == "fruit":
        score += 4
    elif cat == "fat_snack":
        score += 2

    if any(k in text for k in profile["prefer"]):
        score += 10
    if any(k in text for k in profile["avoid"]):
        score -= 14
    if any(k in text for k in ["fried", "chips", "soda", "dessert", "cake", "pastry", "sweet"]):
        score -= 20

    if profile["carb_cap"] == "low":
        score -= carb * 0.7
        if fiber >= 3:
            score += 5
    elif profile["carb_cap"] == "moderate":
        score -= max(carb - 35, 0) * 0.4

    meal_targets = {
        "Breakfast": {"protein": 1.2, "carb": 1.1, "cal": 1.0},
        "Morning Snack": {"protein": 0.8, "carb": 0.7, "cal": 0.7},
        "Lunch": {"protein": 1.3, "carb": 1.2, "cal": 1.2},
        "Evening Snack": {"protein": 0.9, "carb": 0.8, "cal": 0.75},
        "Dinner": {"protein": 1.25, "carb": 0.9, "cal": 1.0},
    }.get(meal_name, {"protein": 1.0, "carb": 1.0, "cal": 1.0})

    score += pro * meal_targets["protein"] * 0.8
    score += fiber * 0.5
    if meal_name in ["Breakfast", "Lunch"] and cat in ["protein", "complex_carb", "fruit", "veg"]:
        score += 2
    score += rng.uniform(-1.0, 1.0)
    return score

def _select_meal_foods(food_items, profile, seed):
    rng = random.Random(seed)
    foods = [_normalize_food_item(x) for x in food_items if x is not None]
    meal_names = ["Breakfast", "Morning Snack", "Lunch", "Evening Snack", "Dinner"]
    scored = {}
    for meal in meal_names:
        scored[meal] = sorted([(_food_score(f, profile, meal, rng), f) for f in foods], key=lambda x: x[0], reverse=True)

    chosen = []
    desired = {"Breakfast": 3, "Morning Snack": 1, "Lunch": 3, "Evening Snack": 1, "Dinner": 3}
    used = set()
    for meal in meal_names:
        picks = []
        for s, f in scored[meal]:
            key = (f["name"], f["serving"])
            if key in used:
                continue
            picks.append((s, f))
            used.add(key)
            if len(picks) == desired[meal]:
                break
        if not picks and scored[meal]:
            picks = scored[meal][:1]
        chosen.append((meal, picks))
    return chosen

def _meal_reason(food, profile, meal_name):
    cat = _food_category(food)
    reasons = []
    if food["protein"] >= 8:
        reasons.append("high protein")
    if food["fiber"] >= 3:
        reasons.append("fibre support")
    if food["calories"] < 180:
        reasons.append("light calories")
    if cat == "protein":
        reasons.append("supports satiety")
    if cat == "veg":
        reasons.append("micronutrient-rich")
    if cat == "complex_carb":
        reasons.append("slow-release energy")
    if profile["carb_cap"] == "low" and food["carbs"] <= 25:
        reasons.append("controlled carbohydrates")
    if "weight loss" in profile["goal_text"].lower() and food["calories"] <= 220:
        reasons.append("helps calorie control")
    if "weight gain" in profile["goal_text"].lower() and food["calories"] >= 150:
        reasons.append("supports healthy calories")
    if not reasons:
        reasons.append("balanced fit for the meal window")
    return ", ".join(reasons[:3]).capitalize()

def _targets(profile, diabetes_type, bmi_cat, risk):
    base_cal = 1800
    b = _safe_lower(bmi_cat)
    d = _safe_lower(diabetes_type)
    r = _safe_lower(risk)

    if "under" in b:
        base_cal = 2300
    elif "normal" in b:
        base_cal = 1900
    elif "over" in b:
        base_cal = 1700
    elif "obese" in b:
        base_cal = 1500

    if "type 1" in d or "type1" in d:
        base_cal += 100
    if "high" in r:
        base_cal -= 150

    protein = 75
    carb = 190
    fiber = 28

    if "under" in b:
        protein = 95
        carb = 240
        fiber = 26
    elif "over" in b or "obese" in b:
        protein = 90
        carb = 150
        fiber = 35

    if "high" in r:
        carb = max(120, carb - 30)
        fiber += 8

    return {
        "calories": int(base_cal),
        "protein": int(protein),
        "carbs": int(carb),
        "fiber": int(fiber),
        "water": float(profile["water_l"]),
    }

def _render_card(title, subtitle, body, accent="#4CAF50"):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(17,24,39,0.92));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 22px;
        padding: 18px 18px 16px 18px;
        box-shadow: 0 12px 30px rgba(0,0,0,0.18);
        margin-bottom: 12px;
    ">
        <div style="font-size:18px;font-weight:800;color:{accent};margin-bottom:4px;">{title}</div>
        <div style="font-size:13px;color:#B7C2D2;margin-bottom:10px;">{subtitle}</div>
        <div style="font-size:14px;color:#E8EEF7;line-height:1.6;">{body}</div>
    </div>
    """, unsafe_allow_html=True)

def render_diet_plan(diabetes_type, bmi_cat, risk):
    profile = _goal_profile(diabetes_type, bmi_cat, risk)
    seed = _diet_seed(diabetes_type, bmi_cat, risk)
    food_items = FOOD_DB if isinstance(FOOD_DB, list) else list(FOOD_DB.values()) if isinstance(FOOD_DB, dict) else []
    meal_picks = _select_meal_foods(food_items, profile, seed)
    targets = _targets(profile, diabetes_type, bmi_cat, risk)

    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fiber": 0.0}
    shopping = []
    avoid_set = set()
    meal_rows = []
    meal_time_labels = {"Breakfast": "7:30 AM", "Morning Snack": "10:30 AM", "Lunch": "1:30 PM", "Evening Snack": "4:30 PM", "Dinner": "7:30 PM"}

    st.markdown("""
    <style>
    .gv-wrap {background: linear-gradient(180deg, #07111f 0%, #0b1630 45%, #07111f 100%); padding: 8px; border-radius: 26px;}
    .gv-title {font-size: 30px; font-weight: 900; color: #F7FAFF; letter-spacing: 0.2px;}
    .gv-sub {font-size: 14px; color: #B6C4D9; margin-top: 4px;}
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown(f"""
        <div class="gv-wrap">
            <div class="gv-title">🥗 Premium AI Nutrition Coach</div>
            <div class="gv-sub">Personalized from health report signals, food scores, and meal-window balancing.</div>
        </div>
        """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("BMI", bmi_cat)
    with c2:
        st.metric("Diabetes Type", diabetes_type)
    with c3:
        st.metric("Risk Level", risk)
    with c4:
        st.metric("Day Target", f"{targets['calories']} kcal")

    st.progress(min(1.0, 0.45 + (targets["calories"] / 3000.0)))

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("Protein Target", f"{targets['protein']} g")
    with c6:
        st.metric("Carb Target", f"{targets['carbs']} g")
    with c7:
        st.metric("Fiber Target", f"{targets['fiber']} g")
    with c8:
        st.metric("Water Target", f"{targets['water']} L")

    st.markdown("## Daily Meal Plan")
    for meal, picks in meal_picks:
        with st.container():
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, rgba(37,99,235,0.18), rgba(16,185,129,0.12));
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 20px;
                padding: 16px;
                margin: 10px 0 14px 0;
            ">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-size:20px;font-weight:800;color:#F3F7FF;">{meal}</div>
                    <div style="font-size:13px;color:#A9B7CC;">{meal_time_labels.get(meal, "")}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            cols = st.columns(max(1, len(picks)))
            for idx, (_, food) in enumerate(picks):
                with cols[idx]:
                    st.markdown(f"""
                    <div style="
                        background: rgba(8,15,28,0.96);
                        border: 1px solid rgba(255,255,255,0.08);
                        border-radius: 18px;
                        padding: 16px;
                        min-height: 240px;
                        box-shadow: 0 10px 28px rgba(0,0,0,0.16);
                    ">
                        <div style="font-size:16px;font-weight:800;color:#7EE0A6;margin-bottom:6px;">{food['name']}</div>
                        <div style="font-size:12px;color:#9FB0C8;margin-bottom:10px;">{food['category']}</div>
                        <div style="font-size:13px;color:#E8EEF7;line-height:1.75;">
                            <b>Serving:</b> {food['serving']}<br>
                            <b>Calories:</b> {round(food['calories'],1)} kcal<br>
                            <b>Protein:</b> {round(food['protein'],1)} g<br>
                            <b>Carbohydrates:</b> {round(food['carbs'],1)} g<br>
                            <b>Reason:</b> {_meal_reason(food, profile, meal)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                meal_rows.append({
                    "Meal": meal,
                    "Meal Time": meal_time_labels.get(meal, ""),
                    "Food Name": food["name"],
                    "Serving Size": food["serving"],
                    "Calories": round(food["calories"], 1),
                    "Protein": round(food["protein"], 1),
                    "Carbohydrates": round(food["carbs"], 1),
                    "Reason why AI selected this meal": _meal_reason(food, profile, meal),
                })
                totals["calories"] += food["calories"]
                totals["protein"] += food["protein"]
                totals["carbs"] += food["carbs"]
                totals["fiber"] += food["fiber"]
                shopping.append(food["name"])
                if any(k in f"{food['name']} {food['category']}".lower() for k in ["fried", "soda", "cake", "pastry", "chips", "sweet", "refined", "white bread"]):
                    avoid_set.add(food["name"])

    st.markdown("## AI Health Analysis")
    analysis = []
    analysis.append(f"Your plan is built for {bmi_cat}, {diabetes_type}, and {risk} risk.")
    analysis.append(profile["goal_text"])
    if "high" in _safe_lower(risk):
        analysis.append("The plan prioritizes low-GI, fibre-rich meals and tighter carbohydrate control.")
    elif "low" in _safe_lower(risk):
        analysis.append("The plan keeps meals balanced with steady energy and practical variety.")
    if "under" in _safe_lower(bmi_cat):
        analysis.append("Higher-calorie, protein-forward foods are favored to support healthy weight gain.")
    elif "over" in _safe_lower(bmi_cat) or "obese" in _safe_lower(bmi_cat):
        analysis.append("Lower-calorie, high-satiety foods are favored to support weight reduction.")
    _render_card("AI Analysis", "Personalized nutrition logic", " ".join(analysis), accent="#60A5FA")

    c9, c10, c11, c12 = st.columns(4)
    with c9:
        st.metric("Calories Target", f"{targets['calories']} kcal")
    with c10:
        st.metric("Protein Target", f"{targets['protein']} g")
    with c11:
        st.metric("Carb Target", f"{targets['carbs']} g")
    with c12:
        st.metric("Fiber Target", f"{targets['fiber']} g")

    st.markdown("## Today's Goal")
    st.markdown(profile["goal_text"])

    st.markdown("## Foods To Avoid")
    avoid_candidates = sorted(list(avoid_set))[:8]
    if not avoid_candidates:
        avoid_candidates = ["Sugary drinks", "Deep-fried snacks", "Refined flour foods", "Desserts"]
    st.markdown("".join([f"- {x}\n" for x in avoid_candidates]))

    st.markdown("## Better Alternatives")
    alt_map = [
        ("White bread", "Whole grain roti or multigrain toast"),
        ("Sugary drinks", "Infused water or unsweetened buttermilk"),
        ("Fried snacks", "Roasted chana or sprouts chaat"),
        ("Refined cereals", "Oats, millets, or brown rice"),
        ("Desserts", "Fruit with nuts or plain yogurt"),
    ]
    st.markdown("\n".join([f"- {a} → {b}" for a, b in alt_map]))

    st.markdown("## Shopping List")
    shopping_counter = Counter([_safe_lower(x) for x in shopping])
    shopping_items = [k.title() for k, v in shopping_counter.most_common()]
    st.markdown("".join([f"- {item}\n" for item in shopping_items]))

    st.markdown("## Water Schedule")
    water_schedule = [
        "Upon waking: 1 glass.",
        "Mid-morning: 1 glass.",
        "Before lunch: 1 glass.",
        "Mid-afternoon: 1 glass.",
        "Before dinner: 1 glass.",
        "Evening: 1 glass.",
    ]
    st.markdown("".join([f"- {x}\n" for x in water_schedule]))

    st.markdown("## AI Summary")
    summary = f"The AI selected {len(meal_rows)} meal items across five eating windows, emphasizing {profile['goal_text'].lower()} Expected totals are about {round(totals['calories'])} kcal, {round(totals['protein'])} g protein, {round(totals['carbs'])} g carbohydrates, and {round(totals['fiber'])} g fibre."
    _render_card("Today's Goal", "Complete daily guidance", summary, accent="#34D399")
    return meal_rows
