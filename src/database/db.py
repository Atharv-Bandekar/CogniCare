import sqlite3
import datetime
from src.config import DB_PATH, DEMO_USER_NAME


def get_connection():
    """Each thread gets its own SQLite connection to prevent race conditions."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables and ensures the default demo user exists."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            response TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sentiment_label TEXT,
            sentiment_score REAL,
            engagement_level TEXT,
            engagement_score REAL,
            recommended_activity TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    """)

    conn.commit()

    cur.execute("SELECT id FROM users WHERE name = ?", (DEMO_USER_NAME,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users (name, created_at) VALUES (?, ?)",
            (DEMO_USER_NAME, datetime.datetime.now().isoformat()),
        )
        conn.commit()

    conn.close()


def get_demo_user_id():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE name = ?", (DEMO_USER_NAME,))
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


def log_conversation(user_id, question, response):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (user_id, timestamp, question, response) VALUES (?, ?, ?, ?)",
        (user_id, datetime.datetime.now().isoformat(), question, response),
    )
    conn.commit()
    conversation_id = cur.lastrowid
    conn.close()
    return conversation_id


def log_insight(conversation_id, sentiment_label, sentiment_score,
                engagement_level, engagement_score, recommended_activity):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO agent_insights
           (conversation_id, sentiment_label, sentiment_score,
            engagement_level, engagement_score, recommended_activity, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (conversation_id, sentiment_label, sentiment_score, engagement_level,
         engagement_score, recommended_activity, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def fetch_history():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.timestamp, c.question, c.response,
               i.sentiment_label, i.sentiment_score,
               i.engagement_level, i.recommended_activity
        FROM conversations c
        LEFT JOIN agent_insights i ON i.conversation_id = c.id
        ORDER BY c.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows