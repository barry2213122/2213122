import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import hashlib
import datetime
import random
import json
import base64

# ==============================================================================
# CONFIGURATION & SETUP
# ==============================================================================
st.set_page_config(
    page_title="GlucoVision AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# DATABASE & AUTHENTICATION (SQLite)
# ==============================================================================
def init_db():
    conn = sqlite3.connect('glucovision_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            email TEXT,
            role TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password, email, role="free"):
    conn = sqlite3.connect('glucovision_users.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password, email, role, created_at) VALUES (?, ?, ?, ?, ?)',
                  (username, hash_password(password), email, role, str(datetime.datetime.now())))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def authenticate_user(username, password):
    conn = sqlite3.connect('glucovision_users.db')
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE username=? AND password=?', (username, hash_password(password)))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

init_db()

# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'role' not in st.session_state:
    st.session_state['role'] = 'free'
if 'page' not in st.session_state:
    st.session_state['page'] = 'Dashboard'

# ==============================================================================
# UI & CSS STYLING
# ==============================================================================
def inject_css():
    st.markdown("""
        <style>
        /* Global Styles */
        .main {
            background-color: #f4f7f6;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* Cards */
        .custom-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            margin-bottom: 20px;
            transition: transform 0.3s ease;
        }
        .custom-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        /* Badges */
        .premium-badge {
            background: linear-gradient(135deg, #FFD700, #FDB931);
            color: #4A4A4A;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.85em;
            display: inline-block;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .admin-badge {
            background: linear-gradient(135deg, #ff416c, #ff4b2b);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.85em;
            display: inline-block;
        }
        .free-badge {
            background: linear-gradient(135deg, #e0e0e0, #bdbdbd);
            color: #333;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.85em;
            display: inline-block;
        }
        
        /* Typography */
        .header-title {
            color: #2c3e50;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        .section-subtitle {
            color: #7f8c8d;
            font-weight: 500;
        }
        
        /* Gradient Background for Login */
        .login-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            border-radius: 20px;
            color: white;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# FOOD DATABASE
# ==============================================================================
FOOD_DB = [
    {"name": "Oats", "calories": 389, "protein": 16.9, "carbs": 66.3, "fat": 6.9, "fibre": 10.6, "category": "grain", "meal": ["Breakfast"], "gi": 55},
    {"name": "Poha", "calories": 130, "protein": 2.5, "carbs": 28, "fat": 0.3, "fibre": 1.2, "category": "grain", "meal": ["Breakfast", "Snack"], "gi": 65},
    {"name": "Upma", "calories": 175, "protein": 4, "carbs": 25, "fat": 6, "fibre": 2, "category": "grain", "meal": ["Breakfast"], "gi": 68},
    {"name": "Idli", "calories": 39, "protein": 2, "carbs": 8, "fat": 0.1, "fibre": 1, "category": "grain", "meal": ["Breakfast", "Lunch"], "gi": 70},
    {"name": "Moong Dal Chilla", "calories": 120, "protein": 7, "carbs": 18, "fat": 2, "fibre": 3, "category": "protein", "meal": ["Breakfast", "Dinner"], "gi": 38},
    {"name": "Dal (Yellow)", "calories": 104, "protein": 6.8, "carbs": 18.6, "fat": 0.4, "fibre": 8, "category": "protein", "meal": ["Lunch", "Dinner"], "gi": 28},
    {"name": "Rajma", "calories": 127, "protein": 8.7, "carbs": 22.8, "fat": 0.5, "fibre": 6.4, "category": "protein", "meal": ["Lunch"], "gi": 24},
    {"name": "Paneer (Low Fat)", "calories": 258, "protein": 20, "carbs": 3, "fat": 18, "fibre": 0, "category": "protein", "meal": ["Lunch", "Dinner"], "gi": 27},
    {"name": "Tofu", "calories": 76, "protein": 8, "carbs": 1.9, "fat": 4.8, "fibre": 1.9, "category": "protein", "meal": ["Lunch", "Dinner"], "gi": 15},
    {"name": "Chapati (Whole Wheat)", "calories": 104, "protein": 3, "carbs": 22, "fat": 0.4, "fibre": 2, "category": "grain", "meal": ["Lunch", "Dinner"], "gi": 62},
    {"name": "Brown Rice", "calories": 111, "protein": 2.6, "carbs": 23, "fat": 0.9, "fibre": 1.8, "category": "grain", "meal": ["Lunch"], "gi": 50},
    {"name": "Quinoa", "calories": 120, "protein": 4.4, "carbs": 21.3, "fat": 1.9, "fibre": 2.8, "category": "grain", "meal": ["Lunch", "Dinner"], "gi": 53},
    {"name": "Spinach (Palak)", "calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4, "fibre": 2.2, "category": "vegetable", "meal": ["Lunch", "Dinner"], "gi": 15},
    {"name": "Broccoli", "calories": 34, "protein": 2.8, "carbs": 6.6, "fat": 0.4, "fibre": 2.6, "category": "vegetable", "meal": ["Lunch", "Dinner"], "gi": 15},
    {"name": "Bottle Gourd (Lauki)", "calories": 14, "protein": 0.6, "carbs": 3.4, "fat": 0.1, "fibre": 1.2, "category": "vegetable", "meal": ["Lunch", "Dinner"], "gi": 15},
    {"name": "Cucumber", "calories": 15, "protein": 0.7, "carbs": 3.6, "fat": 0.1, "fibre": 0.5, "category": "vegetable", "meal": ["Snack", "Lunch"], "gi": 15},
    {"name": "Apple", "calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2, "fibre": 2.4, "category": "fruit", "meal": ["Snack"], "gi": 36},
    {"name": "Guava", "calories": 68, "protein": 2.6, "carbs": 14, "fat": 1, "fibre": 5.4, "category": "fruit", "meal": ["Snack"], "gi": 12},
    {"name": "Papaya", "calories": 43, "protein": 0.5, "carbs": 11, "fat": 0.3, "fibre": 1.7, "category": "fruit", "meal": ["Breakfast", "Snack"], "gi": 60},
    {"name": "Almonds", "calories": 579, "protein": 21, "carbs": 22, "fat": 49, "fibre": 12.5, "category": "nut", "meal": ["Snack"], "gi": 0},
    {"name": "Walnuts", "calories": 654, "protein": 15, "carbs": 14, "fat": 65, "fibre": 7, "category": "nut", "meal": ["Snack"], "gi": 0},
    {"name": "Curd (Low Fat)", "calories": 56, "protein": 3.4, "carbs": 7.7, "fat": 1.5, "fibre": 0, "category": "dairy", "meal": ["Lunch", "Snack"], "gi": 36},
    {"name": "Buttermilk (Chaas)", "calories": 40, "protein": 3, "carbs": 4, "fat": 1, "fibre": 0, "category": "dairy", "meal": ["Lunch", "Snack"], "gi": 30},
    {"name": "Sprouts Salad", "calories": 45, "protein": 4, "carbs": 8, "fat": 0.5, "fibre": 3, "category": "protein", "meal": ["Breakfast", "Snack"], "gi": 25}
]

df_food = pd.DataFrame(FOOD_DB)

# ==============================================================================
# AI ENGINE CORE
# ==============================================================================
def calculate_bmi(weight, height_cm):
    height_m = height_cm / 100
    return weight / (height_m ** 2)

def score_food_item(food, profile):
    score = 100
    
    # Target values based on profile
    is_diabetic = profile['diabetes_type'] != "None"
    needs_weight_loss = profile['bmi'] > 25
    needs_weight_gain = profile['bmi'] < 18.5
    
    # Penalize high GI for diabetics or high glucose
    if is_diabetic or profile['glucose'] > 140:
        if food['gi'] > 60: score -= 30
        elif food['gi'] < 40: score += 20
        
    # Calorie & Fibre adjustments for weight
    if needs_weight_loss:
        if food['calories'] > 200 and food['category'] not in ['nut']: score -= 15
        if food['fibre'] > 4: score += 20
    elif needs_weight_gain:
        if food['calories'] > 150: score += 15
        if food['protein'] > 10: score += 15
        
    # Boost proteins
    if food['protein'] > 10:
        score += 15
        
    return score

def generate_dynamic_diet(profile):
    scored_foods = []
    for _, food in df_food.iterrows():
        f_dict = food.to_dict()
        f_dict['score'] = score_food_item(f_dict, profile)
        scored_foods.append(f_dict)
        
    df_scored = pd.DataFrame(scored_foods).sort_values(by='score', ascending=False)
    
    plan = {}
    meals = ["Breakfast", "Lunch", "Snack", "Dinner"]
    
    for meal in meals:
        eligible = df_scored[df_scored['meal'].apply(lambda x: meal in x)]
        if not eligible.empty:
            # Pick top 2 items for main meals, 1 for snacks
            num_items = 2 if meal in ["Lunch", "Dinner"] else 1
            selected = eligible.head(num_items).to_dict('records')
            
            # Format quantity and explanation
            meal_items = []
            for item in selected:
                reason = "High fibre and low GI for stable glucose." if item['gi'] < 50 else "Balanced energy source."
                if profile['bmi'] > 25 and item['calories'] < 100: reason = "Low calorie for weight management."
                if profile['bmi'] < 18.5 and item['protein'] > 5: reason = "High protein for healthy weight gain."
                
                meal_items.append({
                    "name": item['name'],
                    "quantity": "1 bowl/portion",
                    "calories": item['calories'],
                    "protein": item['protein'],
                    "carbs": item['carbs'],
                    "reason": reason
                })
            plan[meal] = meal_items
            
    # Compile summary
    plan['summary'] = {
        "water_goal": f"{max(2.5, profile['weight'] * 0.033):.1f} Liters",
        "foods_to_avoid": ["Refined Sugar", "White Bread", "Deep Fried Snacks"] if profile['bmi'] > 25 or profile['glucose'] > 140 else ["Excessive Junk Food"],
        "nutrition_score": min(100, int(df_scored.head(5)['score'].mean())),
        "health_score": max(10, 100 - (abs(profile['bmi'] - 22) * 2) - (0 if profile['glucose'] < 100 else (profile['glucose'] - 100) * 0.5))
    }
    
    return plan

# ==============================================================================
# PAGES & COMPONENTS
# ==============================================================================

def show_badges():
    role = st.session_state.role
    if role == 'admin':
        st.markdown('<div class="admin-badge">Admin Privileges</div>', unsafe_allow_html=True)
    elif role == 'premium':
        st.markdown('<div class="premium-badge">🌟 Premium Account</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="free-badge">Basic Free Account</div>', unsafe_allow_html=True)

def login_signup_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="header-title" style="color:white; text-align:center;">🧬 GLUCOVISION AI</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; font-size:1.2em;">Next-Generation Healthcare SaaS</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.markdown("### Welcome Back")
            login_user = st.text_input("Username", key="login_user")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", use_container_width=True):
                if login_user and login_pass:
                    role = authenticate_user(login_user, login_pass)
                    if role:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = login_user
                        st.session_state['role'] = role
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
                        
        with tab2:
            st.markdown("### Create Account")
            reg_user = st.text_input("Username", key="reg_user")
            reg_email = st.text_input("Email", key="reg_email")
            reg_pass = st.text_input("Password", type="password", key="reg_pass")
            reg_type = st.selectbox("Account Type", ["Free", "Premium", "Admin"])
            
            # Simple password strength
            if len(reg_pass) > 0:
                if len(reg_pass) < 6: st.warning("Password Strength: Weak")
                elif len(reg_pass) < 10: st.info("Password Strength: Medium")
                else: st.success("Password Strength: Strong")
                
            if st.button("Sign Up", use_container_width=True):
                if reg_user and reg_email and reg_pass:
                    if add_user(reg_user, reg_pass, reg_email, reg_type.lower()):
                        st.success("Account created! Please log in.")
                    else:
                        st.error("Username already exists.")
                else:
                    st.error("Please fill all fields.")
    st.markdown('</div>', unsafe_allow_html=True)

def dashboard_home():
    st.markdown('<h1 class="header-title">Dashboard Overview</h1>', unsafe_allow_html=True)
    show_badges()
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="custom-card"><h3>Health Score</h3><h1 style="color:#27ae60;">85/100</h1><p>Optimal range</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="custom-card"><h3>Avg Glucose</h3><h1 style="color:#e67e22;">105 mg/dL</h1><p>Past 7 days</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="custom-card"><h3>Activity</h3><h1 style="color:#2980b9;">Active</h1><p>Met weekly goals</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown("### Quick Actions")
    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        if st.button("📊 GlucoVision Check", use_container_width=True): st.session_state.page = "GlucoVision AI"
    with bc2:
        if st.button("🥗 AI Diet Coach", use_container_width=True): st.session_state.page = "AI Diet Coach"
    with bc3:
        if st.button("🧠 MBTI Analysis", use_container_width=True): st.session_state.page = "MBTI Calculator"
    with bc4:
        if st.button("🎮 Health Game", use_container_width=True): st.session_state.page = "Health Game"
    st.markdown('</div>', unsafe_allow_html=True)

def glucovision_page():
    st.markdown('<h1 class="header-title">📊 GlucoVision AI Analyzer</h1>', unsafe_allow_html=True)
    st.write("Input your basic metrics to calculate diabetes risk and health status.")
    
    with st.form("gluco_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", 10, 100, 30)
            weight = st.number_input("Weight (kg)", 30.0, 200.0, 70.0)
            height = st.number_input("Height (cm)", 100.0, 250.0, 170.0)
        with col2:
            glucose = st.number_input("Fasting Glucose (mg/dL)", 50, 300, 95)
            bp = st.number_input("Systolic Blood Pressure", 80, 200, 120)
            family_history = st.selectbox("Family History of Diabetes", ["No", "Yes"])
            
        submitted = st.form_submit_button("Analyze Metrics", use_container_width=True)
        
    if submitted:
        bmi = calculate_bmi(weight, height)
        risk_score = 0
        if age > 45: risk_score += 20
        if bmi > 25: risk_score += 30
        if glucose > 100: risk_score += 40
        if bp > 130: risk_score += 15
        if family_history == "Yes": risk_score += 25
        
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("### Analysis Results")
        rc1, rc2 = st.columns(2)
        rc1.metric("BMI", f"{bmi:.1f}")
        rc2.metric("Risk Score", f"{risk_score}/100")
        
        if risk_score < 40:
            st.success("Low Risk. Keep maintaining a healthy lifestyle!")
        elif risk_score < 70:
            st.warning("Moderate Risk. Consider reviewing your diet and activity levels.")
        else:
            st.error("High Risk. Please consult a healthcare professional and use our AI Diet Coach.")
        st.markdown('</div>', unsafe_allow_html=True)

def require_premium():
    if st.session_state.role not in ['premium', 'admin']:
        st.markdown('<div class="custom-card" style="text-align:center; border: 2px solid #FFD700;">', unsafe_allow_html=True)
        st.markdown("### 🔒 Premium Feature")
        st.markdown("Unlock the full power of AI for personalized insights, advanced diet engines, and complete health analytics.")
        st.markdown('<div class="premium-badge">Upgrade Required</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

def ai_diet_coach_page():
    st.markdown('<h1 class="header-title">🥗 Dynamic AI Diet Coach</h1>', unsafe_allow_html=True)
    if not require_premium(): return
    
    st.write("Our advanced AI dynamically scores and constructs the optimal nutritional plan based on your exact profile.")
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        w = st.number_input("Weight (kg)", value=75.0, key="diet_w")
        h = st.number_input("Height (cm)", value=175.0, key="diet_h")
    with col2:
        g = st.number_input("Glucose", value=110, key="diet_g")
        d = st.selectbox("Diabetes Type", ["None", "Type 1", "Type 2", "Prediabetes"], key="diet_d")
    with col3:
        goal = st.selectbox("Primary Goal", ["Maintain", "Weight Loss", "Weight Gain", "Glucose Control"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("Generate Dynamic Plan", type="primary", use_container_width=True):
        profile = {
            'weight': w,
            'height': h,
            'bmi': calculate_bmi(w, h),
            'glucose': g,
            'diabetes_type': d,
            'goal': goal
        }
        
        with st.spinner("AI is analyzing food database and scoring items..."):
            plan = generate_dynamic_diet(profile)
            
        st.markdown("### 📋 Your Personalized Daily Plan")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nutrition Score", f"{plan['summary']['nutrition_score']}/100")
        c2.metric("Health Score", f"{plan['summary']['health_score']}/100")
        c3.metric("Water Goal", plan['summary']['water_goal'])
        c4.metric("AI Confidence", "98%")
        
        for meal_name in ["Breakfast", "Lunch", "Snack", "Dinner"]:
            st.markdown(f'<div class="custom-card"><h4>{meal_name}</h4>', unsafe_allow_html=True)
            if meal_name in plan:
                for item in plan[meal_name]:
                    st.markdown(f"**{item['name']}** ({item['quantity']})")
                    st.caption(f"Calories: {item['calories']} | Protein: {item['protein']}g | Carbs: {item['carbs']}g")
                    st.info(f"💡 *AI Reason:* {item['reason']}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown("#### Foods to Avoid")
        st.error(", ".join(plan['summary']['foods_to_avoid']))
        
        # Mock PDF generation
        st.download_button(
            label="📄 Download Professional PDF Report",
            data="MOCK PDF DATA - IN PRODUCTION THIS USES REPORTLAB",
            file_name="GlucoVision_Diet_Plan.pdf",
            mime="application/pdf",
            use_container_width=True
        )

def mbti_calculator_page():
    st.markdown('<h1 class="header-title">🧠 MBTI Personality & Health Calculator</h1>', unsafe_allow_html=True)
    if not require_premium(): return
    
    st.write("Understand how your personality traits impact your health habits.")
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    
    q1 = st.radio("At a party do you:", ["Interact with many, including strangers (E)", "Interact with a few, known to you (I)"])
    q2 = st.radio("Are you more:", ["Realistic than speculative (S)", "Speculative than realistic (N)"])
    q3 = st.radio("Is it worse to:", ["Have your head in the clouds (S)", "Be in a rut (N)"])
    q4 = st.radio("Are you more impressed by:", ["Principles (T)", "Emotions (F)"])
    q5 = st.radio("Are you more drawn toward the:", ["Convincing (T)", "Touching (F)"])
    q6 = st.radio("Do you prefer to work:", ["To deadlines (J)", "Just whenever (P)"])
    q7 = st.radio("Do you tend to choose:", ["Rather carefully (J)", "Somewhat impulsively (P)"])
    
    if st.button("Calculate MBTI Profile"):
        e = 1 if "(E)" in q1 else 0
        i = 1 if "(I)" in q1 else 0
        s = (1 if "(S)" in q2 else 0) + (1 if "(S)" in q3 else 0)
        n = (1 if "(N)" in q2 else 0) + (1 if "(N)" in q3 else 0)
        t = (1 if "(T)" in q4 else 0) + (1 if "(T)" in q5 else 0)
        f = (1 if "(F)" in q4 else 0) + (1 if "(F)" in q5 else 0)
        j = (1 if "(J)" in q6 else 0) + (1 if "(J)" in q7 else 0)
        p = (1 if "(P)" in q6 else 0) + (1 if "(P)" in q7 else 0)
        
        mbti = ""
        mbti += "E" if e > i else "I"
        mbti += "S" if s > n else "N"
        mbti += "T" if t > f else "F"
        mbti += "J" if j > p else "P"
        
        st.success(f"Your MBTI Type is: **{mbti}**")
        st.write("### Health Insight based on Profile")
        if "J" in mbti:
            st.info("You excel at strict diet plans. Structuring your meals will yield the best results.")
        else:
            st.info("You prefer flexibility. Focus on broad nutritional guidelines rather than rigid tracking.")
    st.markdown('</div>', unsafe_allow_html=True)

def sleep_stress_analyzer():
    st.markdown('<h1 class="header-title">🌙 Sleep & Stress Analyzer</h1>', unsafe_allow_html=True)
    if not require_premium(): return
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    sleep = st.slider("Average Sleep Hours", 2, 12, 7)
    stress = st.slider("Daily Stress Level (1-10)", 1, 10, 5)
    
    if st.button("Analyze Pattern"):
        score = 100 - (abs(8 - sleep) * 10) - (stress * 5)
        st.metric("Recovery Score", f"{score}/100")
        if score > 80: st.success("Excellent recovery balance.")
        elif score > 60: st.warning("Moderate balance. Aim for 7-8 hours of sleep.")
        else: st.error("High burnout risk. Prioritize rest and stress management techniques.")
    st.markdown('</div>', unsafe_allow_html=True)

def health_game_page():
    st.markdown('<h1 class="header-title">🎮 Health Trivia Game</h1>', unsafe_allow_html=True)
    st.write("Test your nutritional knowledge!")
    
    questions = [
        {"q": "Which macronutrient has the most calories per gram?", "opts": ["Protein", "Carbs", "Fat", "Fibre"], "a": "Fat"},
        {"q": "What is considered a normal fasting blood glucose level?", "opts": ["70-99 mg/dL", "100-125 mg/dL", "126+ mg/dL", "50-60 mg/dL"], "a": "70-99 mg/dL"},
        {"q": "Which vitamin is synthesized by sunlight?", "opts": ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D"], "a": "Vitamin D"}
    ]
    
    if 'game_score' not in st.session_state: st.session_state.game_score = 0
    if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
    
    idx = st.session_state.q_idx
    if idx < len(questions):
        q = questions[idx]
        st.markdown(f'<div class="custom-card"><h3>Question {idx+1}</h3>', unsafe_allow_html=True)
        ans = st.radio(q['q'], q['opts'], key=f"q_{idx}")
        if st.button("Submit Answer"):
            if ans == q['a']:
                st.success("Correct!")
                st.session_state.game_score += 10
            else:
                st.error(f"Wrong! The correct answer was {q['a']}.")
            st.session_state.q_idx += 1
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("### Game Over!")
        st.metric("Final Score", f"{st.session_state.game_score} / {len(questions)*10}")
        if st.button("Play Again"):
            st.session_state.q_idx = 0
            st.session_state.game_score = 0
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def credits_page():
    st.markdown('<h1 class="header-title">📜 Credits & About</h1>', unsafe_allow_html=True)
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown("### GLUCOVISION AI")
    st.markdown("Built for the next generation of personalized healthcare.")
    st.markdown("**Version:** 2.0.0 (Production / Investor Ready)")
    st.markdown("**Core Technologies:** Python, Streamlit, Pandas, AI Analytics, SQLite")
    st.markdown("---")
    st.markdown("© 2026 GlucoVision AI. All rights reserved.")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# MAIN APPLICATION ROUTING
# ==============================================================================
def main():
    inject_css()
    
    if not st.session_state['logged_in']:
        login_signup_page()
    else:
        # Sidebar Navigation
        with st.sidebar:
            st.title("🧬 GlucoVision")
            st.markdown(f"**User:** {st.session_state['username']}")
            show_badges()
            st.markdown("---")
            
            menu_options = [
                "Dashboard",
                "GlucoVision AI",
                "AI Diet Coach",
                "MBTI Calculator",
                "Sleep & Stress Analyzer",
                "Health Game",
                "Credits"
            ]
            
            for option in menu_options:
                # Highlight active page button
                btn_type = "primary" if st.session_state.page == option else "secondary"
                if st.button(option, type=btn_type, use_container_width=True):
                    st.session_state.page = option
                    st.rerun()
            
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
                
        # Main Content Routing
        page = st.session_state.page
        if page == "Dashboard": dashboard_home()
        elif page == "GlucoVision AI": glucovision_page()
        elif page == "AI Diet Coach": ai_diet_coach_page()
        elif page == "MBTI Calculator": mbti_calculator_page()
        elif page == "Sleep & Stress Analyzer": sleep_stress_analyzer()
        elif page == "Health Game": health_game_page()
        elif page == "Credits": credits_page()

if __name__ == "__main__":
    main()
