# -*- coding: utf-8 -*-
"""字段归一化：学历 / 公司性质 / 招聘类型。"""
from __future__ import annotations

import re


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
    if "国有" in r or "国企" in r or "央企" in r or "中央" in r or "国资" in r:
        return "国企"
    if "民营" in r or "私营" in r or "个体" in r:
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


# 中英职位词典：中文职位关键词 -> 英文等价词（用于匹配外企英文职位标题）。
TITLE_ALIASES = {
    "产品经理": ["product manager", "product management"],
    "项目经理": ["project manager"],
    "设计师": ["designer", "design"],
    "设计": ["design"],
    "工程师": ["engineer"],
    "开发": ["developer", "development", "software engineer"],
    "测试": ["test", "qa"],
    "算法": ["algorithm", "machine learning"],
    "数据分析": ["data analyst", "data"],
    "数据": ["data"],
    "前端": ["frontend", "front-end"],
    "后端": ["backend", "back-end"],
    "运维": ["devops", "operations"],
    "运营": ["operations", "operation"],
    "销售": ["sales"],
    "市场": ["marketing"],
    "财务": ["finance", "financial"],
    "会计": ["accountant", "accounting"],
    "人力资源": ["hr", "human resources", "people", "recruiter"],
    "人力": ["hr", "human resources", "people", "recruiter"],
    "行政": ["administrative", "admin"],
    "客服": ["customer service", "support"],
    "采购": ["procurement", "purchasing", "sourcing"],
    "法务": ["legal", "counsel"],
    "审计": ["audit", "auditor"],
    "咨询": ["consultant", "consulting", "advisor"],
    "顾问": ["consultant", "advisor"],
    "教师": ["teacher"],
    "翻译": ["translator", "translation", "interpreter"],
    "编辑": ["editor", "content"],
    "文案": ["copywriter", "content"],
    "策划": ["planning", "planner"],
    "美术": ["artist", "art"],
    "动画": ["animation", "animator"],
    "品牌": ["brand", "branding"],
    "公关": ["public relations", "pr"],
    "商务": ["business development", "business"],
    "实习生": ["intern", "internship"],
    "实习": ["intern", "internship"],
}


def title_aliases(title: str) -> list:
    """返回中文职位关键词的可匹配串（含英文等价词），用于匹配外企英文标题。"""
    t = (title or "").strip()
    aliases = [t]
    if not t:
        return aliases
    for cn in sorted(TITLE_ALIASES, key=len, reverse=True):
        if cn in t:
            for en in TITLE_ALIASES[cn]:
                if en not in aliases:
                    aliases.append(en)
    return aliases


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def detect_language(text: str) -> str:
    """判断文本语言：含中文 -> 中文；仅英文/数字 -> 英文；否则空。"""
    t = (text or "").strip()
    if not t:
        return ""
    if _CJK_RE.search(t):
        return "中文"
    if re.search(r"[A-Za-z]", t):
        return "英文"
    return ""
