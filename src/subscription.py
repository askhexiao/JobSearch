# -*- coding: utf-8 -*-
"""订阅模型 + SQLite 存储 + 职位匹配。

订阅字段（对应原型图 + 发布时长设置）：
- 职位名称（≤5，2 个默认值可编辑）
- 招聘类型：校招 / 社招
- 订阅邮箱
- 工作地点（≤5，「不限」表示不限地点）
- 意向雇主（优质雇主数据库）
- 推送频率：每周 1 次 / 每天 1 次
- 岗位发布时长：最近 1 周 / 2 周 / 1 个月 / 3 个月 / 不限
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from .locations import location_matches
from .models import Job
from .normalize import normalize_recruit_type, title_aliases

MAX_TITLES = 5
MAX_LOCATIONS = 5
UNLIMITED = "不限"
RECRUIT_TYPES = ["校招", "社招"]
FREQUENCIES = ["每周1次", "每天1次"]
DEFAULT_EMPLOYER_DB = "UniFit100 优质雇主数据库 - 2027"

# 岗位发布时长：选项 -> 天数（None 表示不限）。
PUBLISH_WITHIN_OPTIONS = {
    "最近1周": 7,
    "最近2周": 14,
    "最近1个月": 30,
    "最近3个月": 90,
    "不限": None,
}
DEFAULT_PUBLISH_WITHIN = "最近1个月"

# 校招判定（优先用标准化 recruit_type，旧数据回退标题启发式）。

_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    email              TEXT PRIMARY KEY,
    titles             TEXT DEFAULT '[]',
    locations          TEXT DEFAULT '[]',
    location_unlimited INTEGER DEFAULT 0,
    recruit_type       TEXT DEFAULT '校招',
    employer_db        TEXT DEFAULT '',
    frequency          TEXT DEFAULT '每周1次',
    publish_within     TEXT DEFAULT '最近1个月',
    created_at         TEXT DEFAULT '',
    updated_at         TEXT DEFAULT '',
    unsubscribed_at    TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sent_jobs (
    email   TEXT NOT NULL,
    job_key TEXT NOT NULL,
    sent_at TEXT DEFAULT '',
    UNIQUE(email, job_key)
);
"""

# 旧库升级：按列增量迁移（幂等）。
_NEW_COLUMNS = {
    "recruit_type": "TEXT DEFAULT '校招'",
    "employer_db": "TEXT DEFAULT ''",
    "frequency": "TEXT DEFAULT '每周1次'",
    "publish_within": "TEXT DEFAULT '最近1个月'",
    "unsubscribed_at": "TEXT DEFAULT ''",
}


@dataclass
class Subscription:
    email: str = ""
    titles: list = field(default_factory=list)        # ≤ MAX_TITLES
    locations: list = field(default_factory=list)      # ≤ MAX_LOCATIONS；不限时为空
    location_unlimited: bool = False
    recruit_type: str = "校招"                          # 校招 / 社招
    employer_db: str = DEFAULT_EMPLOYER_DB
    frequency: str = "每周1次"                           # 每周1次 / 每天1次
    publish_within: str = DEFAULT_PUBLISH_WITHIN         # 岗位发布时长
    created_at: str = ""
    updated_at: str = ""
    unsubscribed_at: str = ""                             # 退订时间（空=活跃）

    def to_row(self) -> dict:
        return {
            "email": self.email,
            "titles": json.dumps(self.titles, ensure_ascii=False),
            "locations": json.dumps(self.locations, ensure_ascii=False),
            "location_unlimited": int(self.location_unlimited),
            "recruit_type": self.recruit_type,
            "employer_db": self.employer_db,
            "frequency": self.frequency,
            "publish_within": self.publish_within,
        }


def _clean_list(value) -> list:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if x and str(x).strip()]


def validate_subscription(payload: dict) -> tuple:
    """校验并规范化订阅参数（payload 为前端表单 JSON）。

    返回 (Subscription, error)：成功时 error 为 None。
    """
    email = (payload.get("email") or "").strip().lower()
    titles = _clean_list(payload.get("titles"))
    locations = _clean_list(payload.get("locations"))
    recruit_type = (payload.get("recruit_type") or "").strip()
    employer_db = (payload.get("employer_db") or "").strip() or DEFAULT_EMPLOYER_DB
    frequency = (payload.get("frequency") or "").strip()
    publish_within = (payload.get("publish_within") or "").strip() or DEFAULT_PUBLISH_WITHIN

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return None, "请输入有效的邮箱地址"

    if len(titles) > MAX_TITLES:
        return None, f"职位名称最多 {MAX_TITLES} 个"

    if recruit_type not in RECRUIT_TYPES:
        return None, "请选择招聘类型（校招/社招）"

    if frequency not in FREQUENCIES:
        return None, "请选择推送频率"

    if publish_within not in PUBLISH_WITHIN_OPTIONS:
        return None, "请选择岗位发布时长"

    location_unlimited = UNLIMITED in locations
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
        recruit_type=recruit_type,
        employer_db=employer_db,
        frequency=frequency,
        publish_within=publish_within,
    )
    return sub, None


def job_key(job: Job) -> str:
    return f"{job.source}:{job.job_id}"


def is_campus(job: Job) -> bool:
    if job.recruit_type:
        return job.recruit_type in ("校招", "实习")
    return normalize_recruit_type(job.title, job.job_type) in ("校招", "实习")


def _within_days(publish_date: str, days: int) -> bool:
    """发布日期是否在最近 days 天内；无日期或格式异常时不拦截（宽松）。"""
    if not publish_date:
        return True
    try:
        d = datetime.strptime(publish_date[:10], "%Y-%m-%d").date()
    except ValueError:
        return True
    return (date.today() - d).days <= days


def matches(sub: Subscription, job: Job) -> bool:
    """订阅是否匹配某职位（职位名 + 地点 + 招聘类型 + 发布时长）。"""
    if sub.titles:
        title = (job.title or "").lower()
        if not any(a and a.lower() in title for t in sub.titles for a in title_aliases(t)):
            return False
    if not sub.location_unlimited and sub.locations:
        locs = [l for l in sub.locations if l != UNLIMITED]
        if locs and not any(location_matches(loc, job.location) for loc in locs):
            return False
    campus = is_campus(job)
    if sub.recruit_type == "校招" and not campus:
        return False
    if sub.recruit_type == "社招" and campus:
        return False
    days = PUBLISH_WITHIN_OPTIONS.get(sub.publish_within)
    if days is not None and not _within_days(job.publish_date, days):
        return False
    return True


class SubscriptionStore:
    """订阅与已发送记录的 SQLite 存储。"""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(subscriptions)")}
        for name, ddl in _NEW_COLUMNS.items():
            if name not in cols:
                self.conn.execute(f"ALTER TABLE subscriptions ADD COLUMN {name} {ddl}")

    def upsert(self, sub: Subscription) -> None:
        now = datetime.now(timezone.utc).isoformat()
        row = sub.to_row()
        if self.get(sub.email) is None:
            self.conn.execute(
                "INSERT INTO subscriptions "
                "(email, titles, locations, location_unlimited, recruit_type, employer_db, frequency, publish_within, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row["email"], row["titles"], row["locations"], row["location_unlimited"],
                 row["recruit_type"], row["employer_db"], row["frequency"], row["publish_within"], now, now),
            )
        else:
            self.conn.execute(
                "UPDATE subscriptions SET titles=?, locations=?, location_unlimited=?, "
                "recruit_type=?, employer_db=?, frequency=?, publish_within=?, updated_at=?, unsubscribed_at='' WHERE email=?",
                (row["titles"], row["locations"], row["location_unlimited"],
                 row["recruit_type"], row["employer_db"], row["frequency"], row["publish_within"], now, sub.email),
            )
        self.conn.commit()

    def get(self, email: str) -> Subscription | None:
        row = self.conn.execute("SELECT * FROM subscriptions WHERE email=?", (email,)).fetchone()
        return self._row_to_sub(row) if row else None

    def all(self) -> list:
        rows = self.conn.execute(
            "SELECT * FROM subscriptions WHERE unsubscribed_at = '' ORDER BY created_at"
        ).fetchall()
        return [self._row_to_sub(r) for r in rows]

    def unsubscribe(self, email: str) -> bool:
        """软退订：标记退订时间，保留订阅与已发送记录。返回是否原本活跃。"""
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "UPDATE subscriptions SET unsubscribed_at = ? WHERE email = ? AND unsubscribed_at = ''",
            (now, email),
        )
        self.conn.commit()
        return cur.rowcount > 0

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
            recruit_type=row["recruit_type"] or "校招",
            employer_db=row["employer_db"] or DEFAULT_EMPLOYER_DB,
            frequency=row["frequency"] or "每周1次",
            publish_within=row["publish_within"] or DEFAULT_PUBLISH_WITHIN,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            unsubscribed_at=row["unsubscribed_at"] or "",
        )
