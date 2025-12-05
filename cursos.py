# cursos.py
import sqlite3
from pathlib import Path

DB_PATH = Path("ramos_uc.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_courses_by_codes(codes):
    if not codes:
        return []
    conn = get_connection()
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(codes))
    query = f"""
        SELECT code
        FROM course_summary
        WHERE code IN ({placeholders})
        ORDER BY code
    """
    cur.execute(query, codes)
    rows = cur.fetchall()
    conn.close()
    return [r["code"] for r in rows]

def get_all_courses():
    """
    Devuelve una lista con TODOS los códigos de ramos de la tabla course_summary.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT code FROM course_summary ORDER BY code")
    rows = cur.fetchall()
    conn.close()
    return [r["code"] for r in rows]

def get_course_names_map(codes):
    """
    Por ahora la tabla course_summary no tiene columna 'name',
    así que usamos el propio código como 'nombre'.
    """
    if not codes:
        return {}
    
    # Simplemente devolvemos {code: code}
    return {code: code for code in codes}
