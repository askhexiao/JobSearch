# -*- coding: utf-8 -*-
"""统一 Job 数据模型。

所有数据源（24365 / Greenhouse / 国聘等）都归一化到这个模型。
- source + job_id 组合唯一（同源去重）
- dedup_key() 用于跨源去重（公司 + 职位 + 城市）
"""
from __future__ import annotations

from dataclasses import dataclass, fields

from .normalize import detect_language


@dataclass
class Job:
    source: str = ""             # 数据源标识，如 "24365" / "greenhouse"
    job_id: str = ""             # 数据源内唯一 ID
    title: str = ""              # 职位名称
    language: str = ""           # 语言标签：英文 / 中文 / 空
    company: str = ""            # 公司名称
    location: str = ""           # 展示用地点字符串
    location_province: str = ""  # 省（规范化，如"广东"）
    location_city: str = ""      # 市（中文，如"深圳"）
    location_district: str = ""  # 区县
    location_city_en: str = ""   # 市（英文，如"Shenzhen"）
    salary: str = ""             # 展示用薪资字符串
    salary_min: int = 0          # 元/月（0=面议/未知）
    salary_max: int = 0          # 元/月（0=面议/未知）
    education: str = ""          # 展示用学历
    education_level: str = ""    # 枚举：不限/专科/本科/硕士/博士
    job_type: str = ""           # 实习 / 全职
    recruit_type: str = ""       # 校招 / 社招 / 实习
    industry: str = ""           # 行业 / 部门
    company_nature: str = ""     # 标准化：国企/民企/外企/事业单位/其他
    company_size: str = ""       # 公司规模
    head_count: int = 0          # 招聘人数
    publish_date: str = ""       # 发布日期 YYYY-MM-DD
    deadline: str = ""           # 截止日期 YYYY-MM-DD（无则空）
    job_url: str = ""            # 回原官网投递链接
    description: str = ""        # 职位描述（纯文本）

    def __post_init__(self):
        if not self.language:
            self.language = detect_language(self.title)

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def dedup_key(self) -> str:
        """跨源去重键：规范化 公司 + 职位名 + 城市。"""
        company = (self.company or "").strip().lower()
        title = (self.title or "").strip().lower()
        loc = (self.location_city or self.location_province or "").strip().lower()
        return f"{company}|{title}|{loc}"


# 供 db.py 使用的列名（与 Job 字段保持一致）。
FIELD_NAMES = [f.name for f in fields(Job)]
