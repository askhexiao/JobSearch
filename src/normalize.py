# -*- coding: utf-8 -*-
"""字段归一化：学历 / 公司性质 / 招聘类型。"""
from __future__ import annotations


def normalize_education(raw: str) -> str:
    """学历归一化为枚举：不限/专科/本科/硕士/博士（取最低要求）。"""
    r = (raw or "").strip()
    if not r or "不限" in r:
        return "不限"
    if "博士" in r:
        return "博士"
    if "硕士" in r:
        return "硕士"
    if "本科" in r:
        return "本科"
    if "专科" in r or "大专" in r or "高职" in r:
        return "专科"
    return "不限"


def normalize_company_nature(raw: str) -> str:
    """公司性质归一化为枚举：国企/民企/外企/事业单位/其他。"""
    r = (raw or "").strip()
    if not r:
        return "其他"
    if "外商" in r or "外资" in r or "外企" in r or "合资" in r or "港澳台" in r:
        return "外企"
    if "国有" in r or "央企" in r or "国资" in r:
        return "国企"
    if "民营" in r or "私营" in r:
        return "民企"
    if "机关" in r or "事业" in r or "非营利" in r or "非盈利" in r:
        return "事业单位"
    return "其他"


_CAMPUS_TITLE_KEYWORDS = [
    "校招", "秋招", "春招", "应届", "校园", "届", "管培", "毕业生", "培训生",
    "intern", "campus", "graduate", "trainee", "new grad",
]


def normalize_recruit_type(title: str, job_type: str = "") -> str:
    """招聘类型归一化为枚举：校招 / 社招 / 实习。"""
    t = (title or "").lower()
    if job_type == "实习" or "实习" in title or "intern" in t:
        return "实习"
    if "往届" in title or "社招" in title:
        return "社招"
    if any(k in t for k in _CAMPUS_TITLE_KEYWORDS):
        return "校招"
    return "社招"
