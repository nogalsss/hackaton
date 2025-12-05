# db_users.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "ramos_uc.db"

def get_connection():
    # check_same_thread=False para poder usar la conexión en callbacks de Streamlit
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def update_user(user_id, new_username=None, new_email=None):

    DB_PATH = Path("ramos_uc.db")

    def get_connection():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    if new_username is None and new_email is None:
        return

    conn = get_connection()
    cur = conn.cursor()

    fields = []
    values = []

    if new_username:
        fields.append("username = ?")
        values.append(new_username)
    if new_email is not None:
        fields.append("email = ?")
        values.append(new_email)

    values.append(user_id)

    with conn:
        cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)

    conn.close()


def init_users_table():
    conn = get_connection()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                password TEXT NOT NULL
            );
            """
        )
    conn.close()

def create_user(username: str, email: str, password: str):
    """Crea usuario. Devuelve (ok, error_msg)."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password),
            )
        return True, None
    except sqlite3.IntegrityError:
        # username repetido
        return False, "Ese nombre de usuario ya existe 😬"
    finally:
        conn.close()

def get_user(username: str, password: str):
    """Devuelve fila de usuario si username+password coinciden, sino None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, email FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    row = cur.fetchone()
    conn.close()
    return row
