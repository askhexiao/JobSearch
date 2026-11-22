#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量抓取三个数据源并入库（每日定时任务入口）。

用法:
    python run_scrape.py        # 抓取 24365(全省) + 国聘 + Greenhouse 并入库
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.adapters.greenhouse import GreenhouseAdapter
from src.adapters.iguopin import IguopinAdapter
from src.adapters.ncss_24365 import NCSSAdapter
from src.db import JobStore

DB_PATH = Path(__file__).resolve().parent / "unifit100.db"


def main() -> int:
    store = JobStore(DB_PATH)
    total_new = 0

    print("[24365] 全量抓取（所有省级地区）")
    ncss_jobs = NCSSAdapter().fetch_all()
    total_new += sum(1 for j in ncss_jobs if store.upsert(j))
    print(f"  -> 24365 共 {len(ncss_jobs)} 条\n")

    print("[iguopin] 抓取央企/国企岗位")
    ig_jobs = IguopinAdapter().fetch()
    total_new += sum(1 for j in ig_jobs if store.upsert(j))
    print(f"  -> iguopin 共 {len(ig_jobs)} 条\n")

    print("[greenhouse] 抓取外企中国大陆岗位")
    gh_jobs = GreenhouseAdapter().fetch(china_only=True)
    total_new += sum(1 for j in gh_jobs if store.upsert(j))
    print(f"  -> greenhouse 共 {len(gh_jobs)} 条\n")

    expired = store.delete_expired()
    print(f"[DB] 新增 {total_new} 条，清理过期 {expired} 条，数据库共 {store.count()} 条")
    print(f"[DB] 各数据源统计：{store.count_by_source()}")
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
