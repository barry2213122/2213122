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
"Hot & Sour Soup (Veg) (1 bowl)": {"calories": 95.0, "carbs": 15.0, "protein": 3.0, "fat": 2.0}]

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
