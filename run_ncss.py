#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取 24365 国家大学生就业服务平台职位并入库。

用法:
    python run_ncss.py                     # 抓取北京地区职位并入库
    python run_ncss.py 设计                # 抓取"设计"关键词职位
    python run_ncss.py 设计 --area 上海    # 关键词 + 地区
    python run_ncss.py --area 广东         # 只按地区
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.adapters.ncss_24365 import NCSSAdapter, AREA_CODES
from src.db import JobStore

DB_PATH = Path(__file__).resolve().parent / "unifit100.db"
CONSULT_URL = "https://unifit100.com/consultant"


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取 24365 职位并入库")
    parser.add_argument("keyword", nargs="?", default="", help="职位关键词，如 '设计'")
    parser.add_argument("--area", "-a", default="北京", help="工作地区（默认 北京）")
    parser.add_argument("--max-pages", type=int, default=100, help="最大翻页数（每页 20 条）")
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite 数据库路径")
    args = parser.parse_args()

    if args.area not in AREA_CODES:
        print(f"错误：未知地区 '{args.area}'，可选：{', '.join(AREA_CODES.keys())}")
        return 1

    adapter = NCSSAdapter()
    print(f"[24365] 抓取中：地区={args.area}，关键词={args.keyword or '（不限）'}")
    jobs = adapter.fetch(keyword=args.keyword, area=args.area, max_pages=args.max_pages)
    print(f"[24365] 抓取到 {len(jobs)} 条职位")

    store = JobStore(args.db)
    new_count = sum(1 for job in jobs if store.upsert(job))
    print(f"[DB] 新增 {new_count} 条，数据库共 {store.count()} 条")
    print(f"[DB] 各数据源统计：{store.count_by_source()}")
    store.close()

    print()
    print("UniFit100 | Job Search —— 免费职位订阅工具")
    print(f"求职咨询 / 简历辅导：{CONSULT_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
