import streamlit as st
import pandas as pd
import sqlite3
import datetime
import random
import altair as alt
from passlib.hash import sha256_crypt

# Database setup
conn = sqlite3.connect('calorie_dashboard.db', check_same_thread=False)
c = conn.cursor()

# Create tables if not exist
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    username TEXT,
    date TEXT,
    calories INTEGER,
    protein INTEGER,
    carbs INTEGER,
    fats INTEGER,
    water INTEGER,
    exercise TEXT,
    weight REAL,
    height REAL,
    FOREIGN KEY(username) REFERENCES users(username)
)''')
c.execute('''CREATE TABLE IF NOT EXISTS goals (
    username TEXT PRIMARY KEY,
    daily_calories INTEGER,
    protein_goal INTEGER,
    carbs_goal INTEGER,
    fats_goal INTEGER,
    water_goal INTEGER,
    FOREIGN KEY(username) REFERENCES users(username)
)''')
conn.commit()

# Motivational quotes
quotes = [
    "You've got this! One step at a time.",
    "Progress, not perfection.",
    "Eat clean, train mean, live lean.",
    "Your body is a reflection of your lifestyle.",
    "Sweat is fat crying."
]

# Session state for auth
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

def hash_password(password):
    return sha256_crypt.hash(password)

def verify_password(stored, provided):
    return sha256_crypt.verify(provided, stored)

def register_user(username, password):
    hashed = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    if result and verify_password(result[0], password):
        return True
    return False

def calculate_bmi(weight, height):
    if height > 0:
        return weight / (height / 100) ** 2
    return 0

def get_user_entries(username):
    c.execute("SELECT * FROM entries WHERE username = ? ORDER BY date DESC", (username,))
    return pd.DataFrame(c.fetchall(), columns=['id', 'username', 'date', 'calories', 'protein', 'carbs', 'fats', 'water', 'exercise', 'weight', 'height'])

def get_user_goals(username):
    c.execute("SELECT * FROM goals WHERE username = ?", (username,))
    result = c.fetchone()
    if result:
        return {'daily_calories': result[1], 'protein': result[2], 'carbs': result[3], 'fats': result[4], 'water': result[5]}
    return {'daily_calories': 2000, 'protein': 150, 'carbs': 250, 'fats': 70, 'water': 3000}

# App
st.set_page_config(page_title="Supreme Calorie Dashboard", layout="wide")

# Dark mode toggle
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

def toggle_dark_mode():
    st.session_state.dark_mode = not st.session_state.dark_mode

st.button("Toggle Dark Mode", on_click=toggle_dark_mode)

if st.session_state.dark_mode:
    st.markdown("""<style>
    section[data-testid="stSidebar"] {background-color: #1E1E1E;}
    div.stButton > button {background-color: #333; color: white;}
    .stTextInput > div > div > input {background-color: #333; color: white;}
    body {background-color: #121212; color: white;}
    </style>""", unsafe_allow_html=True)

# Auth
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Logged in!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    with tab2:
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Register"):
            if register_user(new_username, new_password):
                st.success("Registered! Please login.")
            else:
                st.error("Username taken")
else:
    username = st.session_state.username
    st.sidebar.title(f"Welcome, {username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    # Main Dashboard
    st.title("Supreme Calorie & Fitness Dashboard 🎯")
    st.subheader(random.choice(quotes))

    # Sidebar for inputs
    with st.sidebar:
        st.header("Daily Entry")
        today = datetime.date.today().isoformat()
        calories = st.number_input("Calories", min_value=0)
        protein = st.number_input("Protein (g)", min_value=0)
        carbs = st.number_input("Carbs (g)", min_value=0)
        fats = st.number_input("Fats (g)", min_value=0)
        water = st.number_input("Water (ml)", min_value=0)
        exercise = st.text_area("Exercise Log")
        weight = st.number_input("Weight (kg)", min_value=0.0)
        height = st.number_input("Height (cm)", min_value=0.0)
        
        if st.button("Save Entry"):
            bmi = calculate_bmi(weight, height)
            c.execute('''INSERT INTO entries (username, date, calories, protein, carbs, fats, water, exercise, weight, height)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (username, today, calories, protein, carbs, fats, water, exercise, weight, height))
            conn.commit()
            st.success("Entry saved!")

        st.header("Set Goals")
        goals = get_user_goals(username)
        daily_cal_goal = st.number_input("Daily Calories Goal", value=goals['daily_calories'])
        protein_goal = st.number_input("Protein Goal (g)", value=goals['protein'])
        carbs_goal = st.number_input("Carbs Goal (g)", value=goals['carbs'])
        fats_goal = st.number_input("Fats Goal (g)", value=goals['fats'])
        water_goal = st.number_input("Water Goal (ml)", value=goals['water'])
        
        if st.button("Save Goals"):
            c.execute('''REPLACE INTO goals (username, daily_calories, protein_goal, carbs_goal, fats_goal, water_goal)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (username, daily_cal_goal, protein_goal, carbs_goal, fats_goal, water_goal))
            conn.commit()
            st.success("Goals updated!")

    # Main content
    df = get_user_entries(username)
    
    if not df.empty:
        # Progress Charts
        st.header("Progress Overview")
        col1, col2 = st.columns(2)
        
        with col1:
            chart_data = df[['date', 'calories']].copy()
            chart_data['goal'] = get_user_goals(username)['daily_calories']
            calorie_chart = alt.Chart(chart_data).mark_line().encode(
                x='date:T',
                y='calories:Q',
                color=alt.value('blue')
            ) + alt.Chart(chart_data).mark_line().encode(
                x='date:T',
                y='goal:Q',
                color=alt.value('red')
            )
            st.altair_chart(calorie_chart, use_container_width=True)
        
        with col2:
            macro_data = df[['date', 'protein', 'carbs', 'fats']].melt('date')
            macro_chart = alt.Chart(macro_data).mark_bar().encode(
                x='date:T',
                y='value:Q',
                color='variable:N'
            )
            st.altair_chart(macro_chart, use_container_width=True)
        
        # BMI Calculator
        st.header("BMI Calculator")
        latest_weight = df['weight'].iloc[0] if 'weight' in df else 0
        latest_height = df['height'].iloc[0] if 'height' in df else 0
        bmi = calculate_bmi(latest_weight, latest_height)
        st.write(f"Your BMI: {bmi:.2f}")
        if bmi < 18.5:
            st.info("Underweight")
        elif bmi < 25:
            st.success("Normal")
        elif bmi < 30:
            st.warning("Overweight")
        else:
            st.error("Obese")

        # History View
        st.header("Entry History")
        st.dataframe(df.drop(columns=['id', 'username']))

        # Export
        csv = df.to_csv(index=False)
        st.download_button("Export to CSV", csv, "calorie_data.csv", "text/csv")

        # Reminders (simple text-based)
        st.header("Reminders")
        if df['calories'].iloc[0] < get_user_goals(username)['daily_calories'] * 0.8:
            st.warning("You're under your calorie goal today! Eat up!")
        if df['water'].iloc[0] < get_user_goals(username)['water_goal']:
            st.info("Don't forget to drink more water!")

        # Exercise Log View
        st.header("Recent Exercises")
        for idx, row in df.head(5).iterrows():
            st.write(f"{row['date']}: {row['exercise']}")

    else:
        st.info("No entries yet. Add your first one in the sidebar!")
