#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量抓取三个数据源并入库（每日定时任务入口）。

策略：
  ① 24365 城市级基础抓取（无关键词，覆盖各城市近期岗位）
  ② 24365 关键词×城市抓取（覆盖具体职位名，突破单城市 top-N 上限）
  ③ 国聘网（央企/国企）
  ④ Greenhouse 外企（中国大陆）

用法:
    python run_scrape.py
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

# 常见职位关键词（用于 关键词×城市 抓取，覆盖主流职能）。
KEYWORDS = [
    "工程师", "设计师", "产品经理", "数据分析", "算法",
    "前端", "后端", "测试", "运维", "开发",
    "运营", "销售", "市场", "财务", "会计",
    "人力", "行政", "客服", "采购", "教师",
]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="全量抓取三个数据源并入库")
    parser.add_argument("--light", action="store_true", help="轻量模式：跳过关键词×城市抓取（适合每日定时）")
    args = parser.parse_args()

    store = JobStore(DB_PATH)
    total_new = 0
    ncss = NCSSAdapter()

    # ① 城市级基础抓取
    print("[24365] 城市级基础抓取（无关键词）")
    for j in ncss.fetch_all():
        if store.upsert(j):
            total_new += 1

    # ② 关键词 × 城市抓取（轻量模式跳过）
    if not args.light:
        for idx, kw in enumerate(KEYWORDS, 1):
            print(f"\n[24365] 关键词×城市 [{idx}/{len(KEYWORDS)}]: {kw}")
            for j in ncss.fetch_all(keyword=kw):
                if store.upsert(j):
                    total_new += 1

    # ③ 国聘
    print("\n[iguopin] 抓取央企/国企岗位")
    for j in IguopinAdapter().fetch():
        if store.upsert(j):
            total_new += 1

    # ④ Greenhouse
    print("\n[greenhouse] 抓取外企中国大陆岗位")
    for j in GreenhouseAdapter().fetch(china_only=True):
        if store.upsert(j):
            total_new += 1

    expired = store.delete_expired()
    print(f"\n[DB] 新增 {total_new} 条，清理过期 {expired} 条，数据库共 {store.count()} 条")
    print(f"[DB] 各数据源统计：{store.count_by_source()}")
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
