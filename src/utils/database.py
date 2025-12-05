"""
Database handler for Person Radar.
Manages SQLite database for storing tracked content.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'radar.db')


def get_db_path() -> str:
    """Get the absolute path to the database file."""
    return os.path.abspath(DATABASE_PATH)


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database with required tables."""
    os.makedirs(os.path.dirname(get_db_path()), exist_ok=True)

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_name TEXT NOT NULL,
                content_type TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                description TEXT,
                thumbnail_url TEXT,
                date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_published TIMESTAMP,
                viewed INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0.5,
                source_channel TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_person_name ON content(person_name)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_date_found ON content(date_found)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_viewed ON content(viewed)
        """)


def add_content(
    person_name: str,
    content_type: str,
    title: str,
    url: str,
    description: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    date_published: Optional[datetime] = None,
    quality_score: float = 0.5,
    source_channel: Optional[str] = None
) -> Optional[int]:
    """
    Add new content to the database.
    Returns the id of the new row, or None if it already exists.
    """
    with get_connection() as conn:
        try:
            cursor = conn.execute("""
                INSERT INTO content (
                    person_name, content_type, title, url, description,
                    thumbnail_url, date_published, quality_score, source_channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                person_name, content_type, title, url, description,
                thumbnail_url, date_published, quality_score, source_channel
            ))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # URL already exists
            return None


def get_content_by_person(
    person_name: str,
    days: int = 7,
    include_viewed: bool = True
) -> list[dict]:
    """Get content for a specific person from the last N days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    with get_connection() as conn:
        if include_viewed:
            cursor = conn.execute("""
                SELECT * FROM content
                WHERE person_name = ? AND date_found >= ?
                ORDER BY date_found DESC
            """, (person_name, cutoff_date))
        else:
            cursor = conn.execute("""
                SELECT * FROM content
                WHERE person_name = ? AND date_found >= ? AND viewed = 0
                ORDER BY date_found DESC
            """, (person_name, cutoff_date))

        return [dict(row) for row in cursor.fetchall()]


def get_all_content(days: int = 7, include_viewed: bool = True) -> list[dict]:
    """Get all content from the last N days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    with get_connection() as conn:
        if include_viewed:
            cursor = conn.execute("""
                SELECT * FROM content
                WHERE date_found >= ?
                ORDER BY date_found DESC
            """, (cutoff_date,))
        else:
            cursor = conn.execute("""
                SELECT * FROM content
                WHERE date_found >= ? AND viewed = 0
                ORDER BY date_found DESC
            """, (cutoff_date,))

        return [dict(row) for row in cursor.fetchall()]


def get_content_grouped_by_person(days: int = 7) -> dict[str, list[dict]]:
    """Get all content grouped by person name."""
    content = get_all_content(days=days)
    grouped = {}

    for item in content:
        person = item['person_name']
        if person not in grouped:
            grouped[person] = []
        grouped[person].append(item)

    return grouped


def mark_as_viewed(content_id: int) -> bool:
    """Mark a content item as viewed."""
    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE content SET viewed = 1 WHERE id = ?
        """, (content_id,))
        return cursor.rowcount > 0


def mark_as_unviewed(content_id: int) -> bool:
    """Mark a content item as not viewed."""
    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE content SET viewed = 0 WHERE id = ?
        """, (content_id,))
        return cursor.rowcount > 0


def content_exists(url: str) -> bool:
    """Check if content with the given URL already exists."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT 1 FROM content WHERE url = ?
        """, (url,))
        return cursor.fetchone() is not None


def cleanup_old_content(days: int = 30):
    """Remove content older than N days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    with get_connection() as conn:
        cursor = conn.execute("""
            DELETE FROM content WHERE date_found < ?
        """, (cutoff_date,))
        return cursor.rowcount


def get_stats() -> dict:
    """Get database statistics."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]
        viewed = conn.execute("SELECT COUNT(*) FROM content WHERE viewed = 1").fetchone()[0]
        unviewed = conn.execute("SELECT COUNT(*) FROM content WHERE viewed = 0").fetchone()[0]

        by_type = {}
        for row in conn.execute("SELECT content_type, COUNT(*) FROM content GROUP BY content_type"):
            by_type[row[0]] = row[1]

        by_person = {}
        for row in conn.execute("SELECT person_name, COUNT(*) FROM content GROUP BY person_name"):
            by_person[row[0]] = row[1]

        return {
            'total': total,
            'viewed': viewed,
            'unviewed': unviewed,
            'by_type': by_type,
            'by_person': by_person
        }


if __name__ == '__main__':
    # Initialize database when run directly
    init_database()
    print(f"Database initialized at: {get_db_path()}")
