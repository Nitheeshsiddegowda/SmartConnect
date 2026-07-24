"""
db.py
-----
Thin wrapper around Python's built-in sqlite3 module.
No ORM is used on purpose -- the whole schema is plain SQL so it is easy
to read, easy to port to MySQL / PostgreSQL later, and needs zero extra
dependencies beyond the standard library.
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "smartconnect.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_db():
    """Return a new connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create instance folder + all tables (idempotent)."""
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    conn = get_db()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def query(sql, params=(), one=False):
    """SELECT helper."""
    conn = get_db()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=(), many=False):
    """INSERT / UPDATE / DELETE helper. Returns lastrowid."""
    conn = get_db()
    if many:
        cur = conn.executemany(sql, params)
    else:
        cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id
