#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每周订阅情况周报：汇总订阅数据并邮件发送给管理员。

用法:
    python run_report.py            # 生成并发送周报
    python run_report.py --dry-run  # 只打印预览，不发送
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.mailer import Mailer

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "unifit100.db"
CONFIG_PATH = ROOT / "config.json"
REPORT_EMAIL = "unifit100@qq.com"  # 周报收件邮箱


def load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _loads(s) -> list:
    try:
        return json.loads(s or "[]")
    except json.JSONDecodeError:
        return []


def _city_label(loc: str) -> str:
    if loc == "不限":
        return "不限"
    if "-" in loc:
        prov, city = loc.split("-", 1)
        if city == "市辖区":
            return prov[:-1] if prov.endswith("市") else prov
        return city[:-1] if city.endswith("市") else city
    return loc


def _loc_text(row) -> str:
    if row["location_unlimited"]:
        return "不限地点"
    locs = _loads(row["locations"])
    return "、".join(_city_label(l) for l in locs) if locs else "不限地点"


def build_report() -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE unsubscribed_at = ''").fetchone()[0]
    unsub = total - active
    daily = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE unsubscribed_at = '' AND frequency = '每天1次'").fetchone()[0]
    weekly = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE unsubscribed_at = '' AND frequency = '每周1次'").fetchone()[0]
    jobs = {r["source"]: r["c"] for r in conn.execute("SELECT source, COUNT(*) c FROM jobs GROUP BY source")}
    subs = conn.execute("SELECT * FROM subscriptions ORDER BY (unsubscribed_at = '') DESC, created_at").fetchall()
    conn.close()

    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "UniFit100 | Job Search · 订阅周报",
        "",
        f"统计日期：{today}",
        "",
        "【汇总】",
        f"· 订阅总数：{total}（活跃 {active} · 已退订 {unsub}）",
        f"· 推送频率：每天 1 次 {daily} · 每周 1 次 {weekly}",
        f"· 岗位库：{' · '.join(f'{k} {v}' for k, v in jobs.items()) or '空'}",
        "",
        "【订阅明细】",
    ]
    if not subs:
        lines.append("（暂无订阅）")
    for i, r in enumerate(subs, 1):
        status = "活跃" if not r["unsubscribed_at"] else "已退订"
        titles = "、".join(_loads(r["titles"])) or "（未填职位）"
        date = (r["created_at"] or "")[:10]
        lines.append(f"{i}. {r['email']} [{status}] · 订阅于 {date}")
        lines.append(f"   {titles} | {r['recruit_type']} | {_loc_text(r)} | {r['frequency']} | {r['publish_within']}")
    lines.append("")
    lines.append("——")
    lines.append("UniFit100 | Job Search · 免费职位订阅工具")
    lines.append("职业规划 / 面试辅导免费预约：https://unifit100.com/consultant")

    body = "".join(html_lib.escape(line) + "<br>" for line in lines)
    return (
        '<html><body style="font-family:-apple-system,'
        "'PingFang SC',sans-serif;font-size:14px;color:#1f2937;line-height:1.7\">"
        + body + "</body></html>"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="订阅周报")
    parser.add_argument("--dry-run", action="store_true", help="只打印预览，不发送")
    args = parser.parse_args()

    html = build_report()
    if args.dry_run:
        print(re.sub(r"</?[^>]+>", "", html.replace("<br>", "\n")))
        return 0

    config = load_config()
    mailer = Mailer(config)
    if not mailer.configured:
        print("[错误] SMTP 未配置，无法发送周报。")
        return 1
    subject = f"UniFit100 订阅周报 · {datetime.now().strftime('%Y-%m-%d')}"
    mailer.send(REPORT_EMAIL, subject, html)
    print(f"周报已发送到 {REPORT_EMAIL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
