# onboarding.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "ramos_uc.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_onboarding_table():
    conn = get_connection()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS onboarding (
                user_id INTEGER PRIMARY KEY,
                selected_ramos TEXT,
                availability TEXT,
                mood TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
    conn.close()

def save_onboarding(user_id, selected_ramos, availability, mood):
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO onboarding (user_id, selected_ramos, availability, mood)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, selected_ramos, availability, mood),
        )
    conn.close()

def get_onboarding(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM onboarding WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row
def update_availability(user_id, availability):
    """
    Actualiza solo la disponibilidad del usuario en la tabla onboarding.
    """
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE onboarding SET availability = ? WHERE user_id = ?",
            (availability, user_id),
        )
    conn.close()


def update_mood(user_id, mood):
    """
    Actualiza solo el mood del usuario en la tabla onboarding.
    """
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE onboarding SET mood = ? WHERE user_id = ?",
            (mood, user_id),
        )
    conn.close()

def init_weekly_availability_table():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weekly_availability (
                user_id INTEGER,
                week TEXT,
                days TEXT,
                PRIMARY KEY (user_id, week)
            );
        """)
    conn.close()

def save_weekly_availability(user_id, week, days):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO weekly_availability (user_id, week, days)
            VALUES (?, ?, ?)
        """, (user_id, week, days))
    conn.close()

def get_weekly_availability(user_id, week):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT days FROM weekly_availability WHERE user_id = ? AND week = ?
    """, (user_id, week))
    row = cur.fetchone()
    conn.close()
    return row["days"] if row else ""

def init_daily_mood_table():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_mood (
                user_id INTEGER,
                date TEXT,
                mood TEXT,
                PRIMARY KEY (user_id, date)
            );
        """)
    conn.close()

from datetime import date

def save_daily_mood(user_id, mood):
    today = str(date.today())
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO daily_mood(user_id, date, mood)
            VALUES (?, ?, ?)
        """, (user_id, today, mood))
    conn.close()

def get_daily_mood(user_id):
    today = str(date.today())
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT mood FROM daily_mood WHERE user_id = ? AND date = ?", (user_id, today))
    row = cur.fetchone()
    conn.close()
    return row["mood"] if row else None
