#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取国聘网（iguopin.com）职位并入库。

用法:
    python run_iguopin.py             # 抓取全部（服务端上限 200 条）
    python run_iguopin.py 数据分析    # 抓取关键词职位
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.adapters.iguopin import IguopinAdapter
from src.db import JobStore

DB_PATH = Path(__file__).resolve().parent / "unifit100.db"
CONSULT_URL = "https://unifit100.com/consultant"


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取国聘网职位并入库")
    parser.add_argument("keyword", nargs="?", default="", help="职位关键词")
    parser.add_argument("--max-pages", type=int, default=20, help="最大翻页数（每页 10 条）")
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite 数据库路径")
    args = parser.parse_args()

    adapter = IguopinAdapter()
    print(f"[iguopin] 抓取中：关键词={args.keyword or '（全部）'}")
    jobs = adapter.fetch(keyword=args.keyword, max_pages=args.max_pages)
    print(f"[iguopin] 抓取到 {len(jobs)} 条职位")

    store = JobStore(args.db)
    new_count = sum(1 for job in jobs if store.upsert(job))
    expired = store.delete_expired()
    print(f"[DB] 新增 {new_count} 条，清理过期 {expired} 条，数据库共 {store.count()} 条")
    print(f"[DB] 各数据源统计：{store.count_by_source()}")
    store.close()

    print()
    print("UniFit100 | Job Search —— 免费职位订阅工具")
    print(f"求职咨询 / 简历辅导：{CONSULT_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
