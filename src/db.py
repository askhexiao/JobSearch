# -*- coding: utf-8 -*-
"""SQLite 存储层。

unique(source, job_id) upsert：同一来源的同一岗位重复抓取时只更新，不重复插入。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .models import Job, FIELD_NAMES

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    job_id          TEXT NOT NULL,
    title           TEXT DEFAULT '',
    company         TEXT DEFAULT '',
    location        TEXT DEFAULT '',
    salary          TEXT DEFAULT '',
    education       TEXT DEFAULT '',
    job_type        TEXT DEFAULT '',
    industry        TEXT DEFAULT '',
    company_nature  TEXT DEFAULT '',
    company_size    TEXT DEFAULT '',
    head_count      INTEGER DEFAULT 0,
    publish_date    TEXT DEFAULT '',
    job_url         TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    raw             TEXT DEFAULT '',
    first_seen_at   TEXT DEFAULT '',
    last_seen_at    TEXT DEFAULT '',
    UNIQUE(source, job_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location);
CREATE INDEX IF NOT EXISTS idx_jobs_company  ON jobs(company);
"""


class JobStore:
    """极简 SQLite 存储封装。"""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def upsert(self, job: Job) -> bool:
        """插入或更新一条职位。

        返回 True 表示「新插入」，False 表示「已存在（仅更新）」。
        """
        now = datetime.now(timezone.utc).isoformat()
        data = job.to_dict()
        values = [data.get(name, "") for name in FIELD_NAMES]

        exists = (
            self.conn.execute(
                "SELECT 1 FROM jobs WHERE source = ? AND job_id = ?",
                (job.source, job.job_id),
            ).fetchone()
            is not None
        )

        if exists:
            sets = ", ".join(f"{name} = ?" for name in FIELD_NAMES)
            self.conn.execute(
                f"UPDATE jobs SET {sets}, last_seen_at = ? WHERE source = ? AND job_id = ?",
                (*values, now, job.source, job.job_id),
            )
        else:
            cols = ", ".join(FIELD_NAMES)
            marks = ", ".join("?" for _ in FIELD_NAMES)
            self.conn.execute(
                f"INSERT INTO jobs ({cols}, first_seen_at, last_seen_at) "
                f"VALUES ({marks}, ?, ?)",
                (*values, now, now),
            )
        self.conn.commit()
        return not exists

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]

    def count_by_source(self) -> dict:
        rows = self.conn.execute(
            "SELECT source, COUNT(*) AS c FROM jobs GROUP BY source ORDER BY c DESC"
        ).fetchall()
        return {row["source"]: row["c"] for row in rows}

    def close(self) -> None:
        self.conn.close()
