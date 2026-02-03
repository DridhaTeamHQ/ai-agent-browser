"""
Memory Module - Simple SQLite blacklist to prevent duplicate processing.

Tracks:
- Processed URLs (success)
- Failed URLs (with reason)
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path
from utils.logger import get_logger


class AgentMemory:
    """
    Persistent memory for the agent.
    
    Database: core/memory/agent.db
    Table: article_history
    """
    
    DB_PATH = Path("core/memory/agent.db")
    
    def __init__(self):
        self.logger = get_logger("memory")
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_conn(self):
        return sqlite3.connect(self.DB_PATH)
    
    def _init_db(self):
        """Initialize database table."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS article_history (
                        url TEXT PRIMARY KEY,
                        status TEXT NOT NULL,  -- 'success', 'failed', 'blacklisted'
                        reason TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            self.logger.error(f"DB init failed: {e}")
    
    def is_processed(self, url: str) -> bool:
        """Check if URL has been processed (success or failure)."""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM article_history WHERE url = ?", (url,)
                )
                return cursor.fetchone() is not None
        except Exception:
            return False

    def is_success(self, url: str) -> bool:
        """Check if URL was successfully published (skip only these to allow retrying failed)."""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM article_history WHERE url = ? AND status = 'success'", (url,)
                )
                return cursor.fetchone() is not None
        except Exception:
            return False
    
    def mark_success(self, url: str):
        """Mark URL as successfully processed."""
        self._record(url, "success")
    
    def mark_failed(self, url: str, reason: str):
        """Mark URL as failed."""
        self._record(url, "failed", reason)
    
    def blacklist(self, url: str, reason: str):
        """Blacklist a URL (skip forever)."""
        self._record(url, "blacklisted", reason)
    
    def _record(self, url: str, status: str, reason: str = None):
        """Record status in DB."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO article_history (url, status, reason, timestamp)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (url, status, reason)
                )
                conn.commit()
            self.logger.info(f"💾 Memory: {url[:30]}... -> {status}")
        except Exception as e:
            self.logger.error(f"Failed to record memory: {e}")
