#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定时推送：读库匹配 → 去重 → 邮件发送。

用法:
    python run_push.py             # 真实发送（需 config.json）
    python run_push.py --dry-run   # 只打印要发送的内容，不真正发信
    python run_push.py --frequency 每天1次   # 只推送指定频率的订阅

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
from src.pusher import push_subscription
from src.subscription import SubscriptionStore

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "unifit100.db"
CONFIG_PATH = ROOT / "config.json"


def load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[警告] 读取 config.json 失败：{exc}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="按订阅匹配库内岗位并邮件推送")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不发送")
    parser.add_argument("--frequency", choices=["每天1次", "每周1次", "all"], default="all", help="只推送指定频率的订阅（默认 all）")
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
    if args.frequency != "all":
        subs = [s for s in subs if s.frequency == args.frequency]
    if not subs:
        print("暂无订阅（或该频率下无订阅）。请通过前端订阅页（python web_server.py）添加订阅。")
        sub_store.close()
        return 0
    print(f"共 {len(subs)} 个订阅（频率={args.frequency}）\n")

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
        count = push_subscription(sub, pool, mailer, sub_store, web_base_url, dry_run)
        if count:
            action = "已发送" if not dry_run else "dry-run"
            print(f"[{action}] {sub.email}：{count} 个新岗位")
        else:
            print(f"[跳过] {sub.email}：无新岗位")

    job_store.close()
    sub_store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
