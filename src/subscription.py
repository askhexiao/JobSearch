# -*- coding: utf-8 -*-
"""订阅模型 + SQLite 存储 + 职位匹配。

订阅规则：
- 职位名称最多 MAX_TITLES 个
- 工作地点最多 MAX_LOCATIONS 个；选择「不限」时地点列表置空
- 仅中国大陆岗位（匹配由 locations.location_matches 保证）
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .locations import location_matches
from .models import Job

MAX_TITLES = 3
MAX_LOCATIONS = 4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    email              TEXT PRIMARY KEY,
    titles             TEXT DEFAULT '[]',
    locations          TEXT DEFAULT '[]',
    location_unlimited INTEGER DEFAULT 0,
    created_at         TEXT DEFAULT '',
    updated_at         TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sent_jobs (
    email   TEXT NOT NULL,
    job_key TEXT NOT NULL,
    sent_at TEXT DEFAULT '',
    UNIQUE(email, job_key)
);
"""


@dataclass
class Subscription:
    email: str = ""
    titles: list = field(default_factory=list)       # ≤ MAX_TITLES
    locations: list = field(default_factory=list)     # ≤ MAX_LOCATIONS；不限时为空
    location_unlimited: bool = False
    created_at: str = ""
    updated_at: str = ""

    def to_row(self) -> dict:
        return {
            "email": self.email,
            "titles": json.dumps(self.titles, ensure_ascii=False),
            "locations": json.dumps(self.locations, ensure_ascii=False),
            "location_unlimited": int(self.location_unlimited),
        }


def validate_subscription(email, titles, locations, location_unlimited) -> tuple:
    """校验并规范化订阅参数。

    返回 (Subscription, error)：成功时 error 为 None，失败时 Subscription 为 None。
    """
    email = (email or "").strip().lower()
    titles = [t.strip() for t in (titles or []) if t and t.strip()]
    locations = [l.strip() for l in (locations or []) if l and l.strip()]
    location_unlimited = bool(location_unlimited)

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return None, "请输入有效的邮箱地址"

    if len(titles) > MAX_TITLES:
        return None, f"职位名称最多 {MAX_TITLES} 个"

    if location_unlimited:
        locations = []
        if not titles:
            return None, "选择「不限」时请至少填写一个职位名称"
    else:
        if len(locations) > MAX_LOCATIONS:
            return None, f"工作地点最多 {MAX_LOCATIONS} 个"
        if not titles and not locations:
            return None, "请至少填写一个职位名称或工作地点"

    sub = Subscription(
        email=email,
        titles=titles,
        locations=locations,
        location_unlimited=location_unlimited,
    )
    return sub, None


def job_key(job: Job) -> str:
    return f"{job.source}:{job.job_id}"


def matches(sub: Subscription, job: Job) -> bool:
    """订阅是否匹配某职位（职位名子串 + 地点匹配）。"""
    if sub.titles:
        title = job.title.lower()
        if not any(t and t.lower() in title for t in sub.titles):
            return False
    if not sub.location_unlimited and sub.locations:
        if not any(location_matches(loc, job.location) for loc in sub.locations):
            return False
    return True


class SubscriptionStore:
    """订阅与已发送记录的 SQLite 存储。"""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def upsert(self, sub: Subscription) -> None:
        now = datetime.now(timezone.utc).isoformat()
        row = sub.to_row()
        existing = self.get(sub.email)
        if existing is None:
            self.conn.execute(
                "INSERT INTO subscriptions (email, titles, locations, location_unlimited, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (row["email"], row["titles"], row["locations"], row["location_unlimited"], now, now),
            )
        else:
            self.conn.execute(
                "UPDATE subscriptions SET titles=?, locations=?, location_unlimited=?, updated_at=? WHERE email=?",
                (row["titles"], row["locations"], row["location_unlimited"], now, sub.email),
            )
        self.conn.commit()

    def get(self, email: str) -> Subscription | None:
        row = self.conn.execute(
            "SELECT * FROM subscriptions WHERE email=?", (email,)
        ).fetchone()
        return self._row_to_sub(row) if row else None

    def all(self) -> list:
        rows = self.conn.execute("SELECT * FROM subscriptions ORDER BY created_at").fetchall()
        return [self._row_to_sub(r) for r in rows]

    def delete(self, email: str) -> None:
        self.conn.execute("DELETE FROM subscriptions WHERE email=?", (email,))
        self.conn.execute("DELETE FROM sent_jobs WHERE email=?", (email,))
        self.conn.commit()

    def mark_sent(self, email: str, key: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR IGNORE INTO sent_jobs (email, job_key, sent_at) VALUES (?, ?, ?)",
            (email, key, now),
        )
        self.conn.commit()

    def is_sent(self, email: str, key: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sent_jobs WHERE email=? AND job_key=?", (email, key)
        ).fetchone()
        return row is not None

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _row_to_sub(row) -> Subscription:
        def _loads(s):
            try:
                return json.loads(s or "[]")
            except json.JSONDecodeError:
                return []

        return Subscription(
            email=row["email"],
            titles=_loads(row["titles"]),
            locations=_loads(row["locations"]),
            location_unlimited=bool(row["location_unlimited"]),
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )
