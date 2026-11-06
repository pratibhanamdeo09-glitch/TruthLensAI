"""History save karne ke liye chhota SQLite database."""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "truthlens.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                source      TEXT    NOT NULL,          -- 'text' ya 'url'
                url         TEXT,
                title       TEXT,
                snippet     TEXT,
                prediction  TEXT    NOT NULL,          -- 'REAL' ya 'FAKE'
                confidence  REAL    NOT NULL,
                client_id   TEXT                       -- har browser/phone ki alag ID
            )
        """)
        # Purane database mein client_id column nahi tha, to add karo
        cols = [r["name"] for r in c.execute("PRAGMA table_info(checks)")]
        if "client_id" not in cols:
            c.execute("ALTER TABLE checks ADD COLUMN client_id TEXT")


def save_check(client_id, source, prediction, confidence, snippet, url=None, title=None):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO checks (client_id, source, url, title, snippet, prediction, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (client_id, source, url, title, snippet, prediction, confidence),
        )
        return cur.lastrowid


def get_history(client_id, limit=50):
    with _conn() as c:
        rows = c.execute(
            "SELECT id, created_at, source, url, title, snippet, prediction, confidence "
            "FROM checks WHERE client_id = ? ORDER BY id DESC LIMIT ?",
            (client_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats(client_id):
    with _conn() as c:
        t = c.execute("""
            SELECT COUNT(*) AS total,
                   SUM(prediction = 'FAKE') AS fake,
                   SUM(prediction = 'REAL') AS real,
                   ROUND(AVG(confidence), 1) AS avg_confidence
            FROM checks WHERE client_id = ?
        """, (client_id,)).fetchone()
        daily = c.execute("""
            SELECT date(created_at) AS day,
                   SUM(prediction = 'FAKE') AS fake,
                   SUM(prediction = 'REAL') AS real
            FROM checks
            WHERE client_id = ? AND date(created_at) >= date('now', 'localtime', '-13 days')
            GROUP BY day ORDER BY day
        """, (client_id,)).fetchall()
    return {
        "total": t["total"] or 0,
        "fake": t["fake"] or 0,
        "real": t["real"] or 0,
        "avg_confidence": t["avg_confidence"] or 0,
        "daily": [dict(r) for r in daily],
    }


def clear_history(client_id):
    with _conn() as c:
        c.execute("DELETE FROM checks WHERE client_id = ?", (client_id,))
