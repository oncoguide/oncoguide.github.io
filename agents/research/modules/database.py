"""SQLite database wrapper for the research agent."""

import os
import shutil
import sqlite3
from datetime import datetime

from .utils import now_iso


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS search_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                run_type TEXT NOT NULL,
                topic_id TEXT,
                queries_total INTEGER DEFAULT 0,
                raw_results INTEGER DEFAULT 0,
                after_dedup INTEGER DEFAULT 0,
                after_enrichment INTEGER DEFAULT 0,
                discarded INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE NOT NULL,
                topic_id TEXT NOT NULL,
                title_original TEXT,
                snippet_original TEXT,
                source_language TEXT,
                title_english TEXT,
                summary_english TEXT,
                relevance_score INTEGER,
                source_url TEXT,
                source_domain TEXT,
                source_platform TEXT,
                date_published TEXT,
                date_found TEXT,
                run_id INTEGER REFERENCES search_runs(id)
            );

            CREATE INDEX IF NOT EXISTS idx_findings_topic ON findings(topic_id);
            CREATE INDEX IF NOT EXISTS idx_findings_score ON findings(relevance_score);
            CREATE INDEX IF NOT EXISTS idx_findings_platform ON findings(source_platform);
            CREATE INDEX IF NOT EXISTS idx_findings_date ON findings(date_found);

            CREATE TABLE IF NOT EXISTS search_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER REFERENCES search_runs(id),
                query_text TEXT,
                search_engine TEXT,
                query_language TEXT,
                results_count INTEGER DEFAULT 0,
                new_findings INTEGER DEFAULT 0,
                status TEXT,
                error_message TEXT,
                executed_at TEXT
            );
        """)
        self.conn.commit()

    def start_run(self, run_type: str, topic_id: str = None) -> int:
        cur = self.execute(
            "INSERT INTO search_runs (run_date, run_type, topic_id) VALUES (?, ?, ?)",
            (now_iso(), run_type, topic_id),
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, stats: dict):
        cols = ["queries_total", "raw_results", "after_dedup", "after_enrichment",
                "discarded", "duration_seconds"]
        sets = ", ".join(f"{c} = ?" for c in cols if c in stats)
        vals = [stats[c] for c in cols if c in stats]
        if sets:
            vals.append(run_id)
            self.execute(f"UPDATE search_runs SET {sets} WHERE id = ?", vals)
            self.conn.commit()

    def insert_finding(self, finding: dict) -> int | None:
        """Insert a finding. Returns id or None if duplicate."""
        try:
            cur = self.execute(
                """INSERT INTO findings
                (content_hash, topic_id, title_original, snippet_original,
                 source_language, title_english, summary_english, relevance_score,
                 source_url, source_domain, source_platform, date_published,
                 date_found, run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    finding["content_hash"], finding["topic_id"],
                    finding["title_original"], finding["snippet_original"],
                    finding["source_language"], finding["title_english"],
                    finding["summary_english"], finding["relevance_score"],
                    finding["source_url"], finding["source_domain"],
                    finding["source_platform"], finding["date_published"],
                    finding["date_found"], finding["run_id"],
                ),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None  # duplicate content_hash

    def get_findings_by_topic(self, topic_id: str, limit: int = 100) -> list[dict]:
        """Get findings for a topic, sorted by relevance_score desc."""
        rows = self.execute(
            """SELECT * FROM findings WHERE topic_id = ?
               ORDER BY relevance_score DESC LIMIT ?""",
            (topic_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def has_finding(self, topic_id: str, content_hash: str = None, url: str = None) -> bool:
        """Check if finding already exists by content_hash OR URL."""
        if content_hash:
            row = self.execute(
                "SELECT 1 FROM findings WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            if row:
                return True
        if url:
            row = self.execute(
                "SELECT 1 FROM findings WHERE topic_id = ? AND source_url = ?",
                (topic_id, url),
            ).fetchone()
            if row:
                return True
        return False

    def log_search(self, run_id: int, query: str, engine: str, language: str,
                   results_count: int, new_findings: int, status: str,
                   error_msg: str = None):
        self.execute(
            """INSERT INTO search_log
            (run_id, query_text, search_engine, query_language, results_count,
             new_findings, status, error_message, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, query, engine, language, results_count, new_findings,
             status, error_msg, now_iso()),
        )
        self.conn.commit()

    def backup(self, backup_dir: str, max_backups: int = 10):
        """Backup database file. Rotate old backups."""
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(backup_dir, f"research_{ts}.db")
        shutil.copy2(self.db_path, dest)

        # Rotate
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith("research_")],
        )
        while len(backups) > max_backups:
            os.remove(os.path.join(backup_dir, backups.pop(0)))

    def close(self):
        self.conn.close()
