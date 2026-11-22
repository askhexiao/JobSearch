#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定时推送：读库匹配 → 去重 → 邮件发送。

用法:
    python run_push.py             # 真实发送（需 config.json）
    python run_push.py --dry-run   # 只打印要发送的内容，不真正发信

推送前请先运行抓取脚本（python run_scrape.py）把最新岗位入库。
未配置 config.json 时自动进入 dry-run 模式。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.db import JobStore
from src.mailer import Mailer
from src.subscription import SubscriptionStore, job_key, matches

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "unifit100.db"
CONFIG_PATH = ROOT / "config.json"
CONSULT_URL = "https://unifit100.com/consultant"
MAX_JOBS_PER_EMAIL = 20


def load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[警告] 读取 config.json 失败：{exc}")
        return None


def _city_label(loc: str) -> str:
    """把地点路径简化为城市名：'广东省-深圳市'->'深圳'、'北京市-市辖区'->'北京'。"""
    if loc == "不限":
        return "不限"
    if "-" in loc:
        prov, city = loc.split("-", 1)
        if city == "市辖区":
            return prov[:-1] if prov.endswith("市") else prov
        return city[:-1] if city.endswith("市") else city
    return loc


def _sub_summary(sub) -> str:
    """订阅摘要：职位 · 招聘类型 · 地点 · 发布时长。"""
    parts = [("、".join(sub.titles)) if sub.titles else "不限职位"]
    parts.append(sub.recruit_type)
    if sub.location_unlimited:
        parts.append("不限地点")
    elif sub.locations:
        parts.append("、".join(_city_label(l) for l in sub.locations))
    parts.append(sub.publish_within)
    return " · ".join(parts)


def render_email(sub, jobs, web_base_url: str) -> str:
    summary = _sub_summary(sub)
    lines = [
        "UniFit100 | Job Search",
        "",
        f"Hi，你订阅的职位有新岗位（共 {len(jobs)} 个）：",
        "",
        f"【订阅】{summary}",
        "",
        "——",
    ]
    for idx, j in enumerate(jobs[:MAX_JOBS_PER_EMAIL], 1):
        title = j.title
        if j.language == "英文":
            title = f"{title}（英文）"
        lines.append(f"{idx}. {title}")
        lines.append(f"   {j.company} | {j.location} | {j.salary or '薪资面议'} | {j.publish_date}")
        lines.append(f"   投递 → {j.job_url}")
        lines.append("")
    if len(jobs) > MAX_JOBS_PER_EMAIL:
        lines.append(f"（仅展示前 {MAX_JOBS_PER_EMAIL} 个，共 {len(jobs)} 个）")
        lines.append("")
    lines.append("——")
    lines.append("UniFit100 | Job Search · 免费职位订阅工具")
    lines.append(f"求职咨询 / 简历辅导：{CONSULT_URL}")
    lines.append(f"退订：{web_base_url}/unsubscribe?email={sub.email}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="按订阅匹配库内岗位并邮件推送")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不发送")
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite 数据库路径")
    args = parser.parse_args()

    config = load_config()
    web_base_url = (config or {}).get("web_base_url", "http://127.0.0.1:8000")
    dry_run = args.dry_run or config is None
    if config is None and not args.dry_run:
        print("未找到 config.json，自动进入 dry-run 模式（不发送邮件）。")
        print("如需真实发送：cp config.example.json config.json 并填入 SMTP 凭证。\n")

    mailer = Mailer(config) if config else None
    if not dry_run and (mailer is None or not mailer.configured):
        print("[警告] SMTP 未配置，转为 dry-run 模式。")
        dry_run = True

    sub_store = SubscriptionStore(args.db)
    subs = sub_store.all()
    if not subs:
        print("暂无订阅。请通过前端订阅页（python web_server.py）添加订阅。")
        sub_store.close()
        return 0
    print(f"共 {len(subs)} 个订阅\n")

    # 读库：三数据源（24365 + 国聘 + Greenhouse）全量岗位。
    job_store = JobStore(args.db)
    job_store.delete_expired()
    pool = job_store.all_jobs()
    if not pool:
        print("职位库为空，请先运行 python run_scrape.py 抓取岗位。")
        job_store.close()
        sub_store.close()
        return 0
    print(f"职位库共 {len(pool)} 条：{job_store.count_by_source()}\n")

    for sub in subs:
        matched = [j for j in pool if matches(sub, j)]
        # 跨源去重：同一「公司 + 职位 + 城市」只保留一条（多渠道转载去重）
        seen_keys = set()
        deduped = []
        for j in matched:
            k = j.dedup_key()
            if k in seen_keys:
                continue
            seen_keys.add(k)
            deduped.append(j)
        new_jobs = [j for j in deduped if not sub_store.is_sent(sub.email, job_key(j))]

        if not new_jobs:
            print(f"[跳过] {sub.email}：无新岗位")
            continue

        subject = f"【UniFit100】新岗位 {len(new_jobs)} 个"
        body = render_email(sub, new_jobs, web_base_url)
        if dry_run:
            print(f"[dry-run] {sub.email}：{len(new_jobs)} 个新岗位（未发送）")
            print(body[:600])
            print("……\n")
        else:
            mailer.send(sub.email, subject, body)
            print(f"[已发送] {sub.email}：{len(new_jobs)} 个新岗位")
            for j in new_jobs:
                sub_store.mark_sent(sub.email, job_key(j))

    job_store.close()
    sub_store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
