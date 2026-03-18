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
                authority_score INTEGER DEFAULT 0,
                source_url TEXT,
                source_domain TEXT,
                source_platform TEXT,
                date_published TEXT,
                date_found TEXT,
                run_id INTEGER REFERENCES search_runs(id),
                lifecycle_stage TEXT,
                is_seeded INTEGER DEFAULT 0,
                seed_source TEXT
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

            -- v6: Pipeline checkpoint/resume
            CREATE TABLE IF NOT EXISTS pipeline_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL,
                run_id INTEGER REFERENCES search_runs(id),
                phase INTEGER NOT NULL,
                phase_name TEXT NOT NULL,
                status TEXT NOT NULL,
                output_ref TEXT,
                cost_usd REAL DEFAULT 0,
                duration_seconds REAL DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_pipeline_state_topic
                ON pipeline_state(topic_id, phase);

            -- v6: Monitoring runs
            CREATE TABLE IF NOT EXISTS monitor_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                since_date TEXT,
                findings_scanned INTEGER DEFAULT 0,
                new_findings INTEGER DEFAULT 0,
                alerts_generated INTEGER DEFAULT 0,
                tech_updates INTEGER DEFAULT 0,
                new_techs_discovered INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                duration_seconds REAL DEFAULT 0
            );

            -- v6: Alerts from monitoring
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_run_id INTEGER REFERENCES monitor_runs(id),
                topic_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                finding_ids TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_topic
                ON alerts(topic_id, acknowledged);

            -- v6: Tracked entities per topic
            CREATE TABLE IF NOT EXISTS tracked_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                canonical_name TEXT NOT NULL,
                aliases TEXT,
                guide_sections TEXT,
                last_updated TEXT,
                auto_discovered INTEGER DEFAULT 0,
                UNIQUE(topic_id, entity_type, canonical_name)
            );

            -- v6: Archive for old findings
            CREATE TABLE IF NOT EXISTS findings_archive (
                id INTEGER PRIMARY KEY,
                content_hash TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                title_original TEXT,
                snippet_original TEXT,
                source_language TEXT,
                title_english TEXT,
                summary_english TEXT,
                relevance_score INTEGER,
                authority_score INTEGER DEFAULT 0,
                source_url TEXT,
                source_domain TEXT,
                source_platform TEXT,
                date_published TEXT,
                date_found TEXT,
                run_id INTEGER,
                lifecycle_stage TEXT,
                is_seeded INTEGER DEFAULT 0,
                seed_source TEXT,
                archived_at TEXT NOT NULL,
                archive_reason TEXT
            );
        """)
        self.conn.commit()

        # Migrations for existing databases
        self._migrate()

        # Create indexes that depend on migrated columns (after migrations run)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_authority ON findings(authority_score)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_lifecycle ON findings(lifecycle_stage)")
        self.conn.commit()

    def _migrate(self):
        """Apply schema migrations for existing databases."""
        cols = [row[1] for row in self.conn.execute("PRAGMA table_info(findings)").fetchall()]
        # v4 -> v5: authority_score
        if "authority_score" not in cols:
            self.conn.execute("ALTER TABLE findings ADD COLUMN authority_score INTEGER DEFAULT 0")
        # v5 -> v6: lifecycle columns
        if "lifecycle_stage" not in cols:
            self.conn.execute("ALTER TABLE findings ADD COLUMN lifecycle_stage TEXT")
        if "is_seeded" not in cols:
            self.conn.execute("ALTER TABLE findings ADD COLUMN is_seeded INTEGER DEFAULT 0")
        if "seed_source" not in cols:
            self.conn.execute("ALTER TABLE findings ADD COLUMN seed_source TEXT")
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
                 authority_score, source_url, source_domain, source_platform,
                 date_published, date_found, run_id,
                 lifecycle_stage, is_seeded, seed_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    finding["content_hash"], finding["topic_id"],
                    finding["title_original"], finding["snippet_original"],
                    finding["source_language"], finding["title_english"],
                    finding["summary_english"], finding["relevance_score"],
                    finding.get("authority_score", 0),
                    finding["source_url"], finding["source_domain"],
                    finding["source_platform"], finding["date_published"],
                    finding["date_found"], finding["run_id"],
                    finding.get("lifecycle_stage"),
                    finding.get("is_seeded", 0),
                    finding.get("seed_source"),
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

    def count_findings(self, topic_id: str) -> int:
        """Count findings for a topic."""
        return self.conn.execute(
            "SELECT COUNT(*) FROM findings WHERE topic_id = ?", (topic_id,)
        ).fetchone()[0]

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

    # ── v6: Pipeline state ─────────────────────────────────────────────

    def save_pipeline_state(self, topic_id: str, run_id: int, phase: int,
                            phase_name: str, status: str, output_ref: str = None,
                            cost_usd: float = 0, duration_seconds: float = 0,
                            error: str = None):
        self.execute(
            """INSERT INTO pipeline_state
            (topic_id, run_id, phase, phase_name, status, output_ref,
             cost_usd, duration_seconds, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (topic_id, run_id, phase, phase_name, status, output_ref,
             cost_usd, duration_seconds, error, now_iso()),
        )
        self.conn.commit()

    def get_last_completed_phase(self, topic_id: str) -> int | None:
        row = self.execute(
            """SELECT MAX(phase) as max_phase FROM pipeline_state
            WHERE topic_id = ? AND status = 'complete'""",
            (topic_id,),
        ).fetchone()
        return row["max_phase"] if row and row["max_phase"] is not None else None

    # ── v6: Monitoring ───────────────────────────────────────────────

    def start_monitor_run(self, topic_id: str, since_date: str) -> int:
        cur = self.execute(
            """INSERT INTO monitor_runs (run_date, topic_id, since_date)
            VALUES (?, ?, ?)""",
            (now_iso(), topic_id, since_date),
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_monitor_run(self, run_id: int, stats: dict):
        cols = ["findings_scanned", "new_findings", "alerts_generated",
                "tech_updates", "new_techs_discovered", "cost_usd", "duration_seconds"]
        sets = ", ".join(f"{c} = ?" for c in cols if c in stats)
        vals = [stats[c] for c in cols if c in stats]
        if sets:
            vals.append(run_id)
            self.execute(f"UPDATE monitor_runs SET {sets} WHERE id = ?", vals)
            self.conn.commit()

    # ── v6: Alerts ───────────────────────────────────────────────────

    def save_alert(self, monitor_run_id: int, topic_id: str, severity: str,
                   category: str, title: str, description: str,
                   finding_ids: str = None):
        self.execute(
            """INSERT INTO alerts
            (monitor_run_id, topic_id, severity, category, title, description,
             finding_ids, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (monitor_run_id, topic_id, severity, category, title, description,
             finding_ids, now_iso()),
        )
        self.conn.commit()

    def get_unacknowledged_alerts(self, topic_id: str) -> list[dict]:
        rows = self.execute(
            """SELECT * FROM alerts
            WHERE topic_id = ? AND acknowledged = 0
            ORDER BY CASE severity
                WHEN 'critical' THEN 1 WHEN 'major' THEN 2 ELSE 3
            END""",
            (topic_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def acknowledge_alert(self, alert_id: int):
        self.execute(
            "UPDATE alerts SET acknowledged = 1, acknowledged_at = ? WHERE id = ?",
            (now_iso(), alert_id),
        )
        self.conn.commit()

    # ── v6: Tracked entities ─────────────────────────────────────────

    def save_tracked_entity(self, topic_id: str, entity_type: str,
                            canonical_name: str, aliases: str = None,
                            guide_sections: str = None):
        self.execute(
            """INSERT INTO tracked_entities
            (topic_id, entity_type, canonical_name, aliases, guide_sections, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic_id, entity_type, canonical_name)
            DO UPDATE SET aliases = excluded.aliases,
                         guide_sections = excluded.guide_sections,
                         last_updated = excluded.last_updated""",
            (topic_id, entity_type, canonical_name, aliases, guide_sections, now_iso()),
        )
        self.conn.commit()

    def get_tracked_entities(self, topic_id: str) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM tracked_entities WHERE topic_id = ? ORDER BY entity_type, canonical_name",
            (topic_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── v6: Findings archive ─────────────────────────────────────────

    def archive_old_findings(self, topic_id: str, max_age_days: int = 180,
                             min_relevance: int = 3) -> int:
        """Move low-relevance old findings to archive. Returns count archived."""
        cutoff = datetime.now()
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        rows = self.execute(
            """SELECT * FROM findings
            WHERE topic_id = ? AND relevance_score < ?
              AND date_found < date(?, '-' || ? || ' days')""",
            (topic_id, min_relevance, cutoff_str, max_age_days),
        ).fetchall()
        count = 0
        for row in rows:
            d = dict(row)
            self.execute(
                """INSERT INTO findings_archive
                (id, content_hash, topic_id, title_original, snippet_original,
                 source_language, title_english, summary_english, relevance_score,
                 authority_score, source_url, source_domain, source_platform,
                 date_published, date_found, run_id, lifecycle_stage, is_seeded,
                 seed_source, archived_at, archive_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d["id"], d["content_hash"], d["topic_id"], d["title_original"],
                 d["snippet_original"], d["source_language"], d["title_english"],
                 d["summary_english"], d["relevance_score"], d["authority_score"],
                 d["source_url"], d["source_domain"], d["source_platform"],
                 d["date_published"], d["date_found"], d["run_id"],
                 d.get("lifecycle_stage"), d.get("is_seeded", 0), d.get("seed_source"),
                 now_iso(), f"relevance<{min_relevance}, age>{max_age_days}d"),
            )
            self.execute("DELETE FROM findings WHERE id = ?", (d["id"],))
            count += 1
        self.conn.commit()
        return count

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
