#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取 Greenhouse 外企职位（仅中国大陆）并入库。

用法:
    python run_greenhouse.py              # 抓取默认 6 个外企 board 的中国岗位
    python run_greenhouse.py --all        # 抓取全部岗位（不限地区）
    python run_greenhouse.py --board duolingo airbnb
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.adapters.greenhouse import GreenhouseAdapter, BOARDS
from src.db import JobStore

DB_PATH = Path(__file__).resolve().parent / "unifit100.db"
CONSULT_URL = "https://unifit100.com/consultant"


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取 Greenhouse 外企职位并入库")
    parser.add_argument("--board", nargs="*", default=None, help="board_token 列表（默认内置 6 个）")
    parser.add_argument("--all", action="store_true", help="抓取全部岗位（默认只保留中国大陆岗位）")
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite 数据库路径")
    args = parser.parse_args()

    adapter = GreenhouseAdapter()
    boards = args.board or BOARDS
    print(f"[greenhouse] 抓取中：{len(boards)} 个 board，仅中国={not args.all}")
    jobs = adapter.fetch(boards=boards, china_only=not args.all)
    print(f"[greenhouse] 抓取到 {len(jobs)} 条职位")

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
