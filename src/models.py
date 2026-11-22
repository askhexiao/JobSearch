# -*- coding: utf-8 -*-
"""统一 Job 数据模型。

所有数据源（24365 / Greenhouse / 后续适配器）都归一化到这个模型，
source + job_id 组合唯一，用于跨源去重 upsert。
"""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class Job:
    """跨数据源统一的职位模型。

    source + job_id 构成唯一键（见 db.py 的 UNIQUE(source, job_id)）。
    """

    source: str = ""            # 数据源标识，如 "24365" / "greenhouse"
    job_id: str = ""            # 数据源内唯一 ID
    title: str = ""             # 职位名称
    company: str = ""           # 公司名称
    location: str = ""          # 工作地点（城市/地区）
    salary: str = ""            # 薪资区间（展示文本）
    education: str = ""         # 学历要求
    job_type: str = ""          # 全职 / 实习 等
    industry: str = ""          # 行业 / 部门
    company_nature: str = ""    # 公司性质（国企/民企/外企等）
    company_size: str = ""      # 公司规模
    head_count: int = 0         # 招聘人数
    publish_date: str = ""      # 发布日期 YYYY-MM-DD
    job_url: str = ""           # 回原官网投递链接
    description: str = ""       # 职位描述（纯文本）
    raw: str = ""               # 原始 JSON 文本（调试/追溯用）

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


# 供 db.py 使用的列名（与 Job 字段保持一致）。
FIELD_NAMES = [f.name for f in fields(Job)]
