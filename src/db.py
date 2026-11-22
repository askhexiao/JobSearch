# -*- coding: utf-8 -*-
"""SQLite 存储层。

unique(source, job_id) upsert：同一来源的同一岗位重复抓取时只更新，不重复插入。
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

from .models import Job, FIELD_NAMES

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source            TEXT NOT NULL,
    job_id            TEXT NOT NULL,
    title             TEXT DEFAULT '',
    company           TEXT DEFAULT '',
    location          TEXT DEFAULT '',
    location_province TEXT DEFAULT '',
    location_city     TEXT DEFAULT '',
    location_district TEXT DEFAULT '',
    location_city_en  TEXT DEFAULT '',
    salary            TEXT DEFAULT '',
    salary_min        INTEGER DEFAULT 0,
    salary_max        INTEGER DEFAULT 0,
    education         TEXT DEFAULT '',
    education_level   TEXT DEFAULT '',
    job_type          TEXT DEFAULT '',
    recruit_type      TEXT DEFAULT '',
    industry          TEXT DEFAULT '',
    company_nature    TEXT DEFAULT '',
    company_size      TEXT DEFAULT '',
    head_count        INTEGER DEFAULT 0,
    publish_date      TEXT DEFAULT '',
    deadline          TEXT DEFAULT '',
    job_url           TEXT DEFAULT '',
    description       TEXT DEFAULT '',
    first_seen_at     TEXT DEFAULT '',
    last_seen_at      TEXT DEFAULT '',
    UNIQUE(source, job_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location);
CREATE INDEX IF NOT EXISTS idx_jobs_company  ON jobs(company);
"""

# 旧库升级：按列增量迁移（幂等）。
_NEW_COLUMNS = {
    "location_province": "TEXT DEFAULT ''",
    "location_city": "TEXT DEFAULT ''",
    "location_district": "TEXT DEFAULT ''",
    "location_city_en": "TEXT DEFAULT ''",
    "salary_min": "INTEGER DEFAULT 0",
    "salary_max": "INTEGER DEFAULT 0",
    "education_level": "TEXT DEFAULT ''",
    "recruit_type": "TEXT DEFAULT ''",
    "deadline": "TEXT DEFAULT ''",
}


class JobStore:
    """极简 SQLite 存储封装。"""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(jobs)")}
        for name, ddl in _NEW_COLUMNS.items():
            if name not in cols:
                self.conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {ddl}")
        # 依赖新列的索引在迁移后创建
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_recruit_type ON jobs(recruit_type)")

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

    def all_jobs(self) -> list:
        """读取库内全部职位，返回 list[Job]。"""
        rows = self.conn.execute("SELECT * FROM jobs").fetchall()
        return [Job(**{name: row[name] for name in FIELD_NAMES}) for row in rows]

    def delete_expired(self) -> int:
        """删除已过截止日期的岗位，返回删除条数。"""
        today = date.today().isoformat()
        cur = self.conn.execute(
            "DELETE FROM jobs WHERE deadline != '' AND deadline < ?", (today,)
        )
        self.conn.commit()
        return cur.rowcount

    def close(self) -> None:
        self.conn.close()
