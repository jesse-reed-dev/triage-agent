import sqlite3
import os

# ─── Config ───────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seen_issues.db")


# ─── Setup ────────────────────────────────────────────────────────────────────

def init_db():
    """
    Creates the database file and table if they don't exist yet.
    Safe to call every run — CREATE TABLE IF NOT EXISTS is a no-op if it's already there.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_issues (
            repo TEXT NOT NULL,
            issue_number INTEGER NOT NULL,
            seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (repo, issue_number)
        )
    """)
    conn.commit()
    conn.close()


# ─── Queries ──────────────────────────────────────────────────────────────────

def has_seen(repo: str, issue_number: int) -> bool:
    """
    Returns True if this issue has already been recorded.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT 1 FROM seen_issues WHERE repo = ? AND issue_number = ?",
        (repo, issue_number),
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def mark_seen(repo: str, issue_number: int) -> None:
    """
    Records an issue as seen so it won't show up again tomorrow.
    INSERT OR IGNORE means it silently does nothing if the row already exists,
    instead of throwing a duplicate-key error.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO seen_issues (repo, issue_number) VALUES (?, ?)",
        (repo, issue_number),
    )
    conn.commit()
    conn.close()