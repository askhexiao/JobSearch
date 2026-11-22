# -*- coding: utf-8 -*-
"""Greenhouse ATS 外企适配器。

Greenhouse 对外提供公开、免鉴权的 Job Board JSON API：
    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

本项目只保留「中国大陆」相关岗位，并引导用户回原官网投递。
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse

from .base import BaseAdapter
from ..locations import parse_english_location
from ..models import Job
from ..normalize import normalize_recruit_type

API_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

# 默认抓取的 board（实测含中国大陆岗位的外企）。
BOARDS = [
    "duolingo",
    "airbnb",
    "databricks",
    "mongodb",
    "flexport",
    "riotgames",
    "godaddy",
]

# 中国大陆城市关键词（命中即视为大陆岗位）。
MAINLAND_CITY_KEYWORDS = [
    "Beijing", "Shanghai", "Shenzhen", "Guangzhou", "Hangzhou",
    "Chengdu", "Nanjing", "Wuhan", "Suzhou", "Tianjin", "Xi'an", "Xian",
    "Qingdao", "Chongqing", "Changsha", "Dalian", "Xiamen", "Fuzhou",
    "Kunming", "Zhengzhou", "Hefei", "Jinan", "Ningbo", "Dongguan",
    "Foshan", "Zhuhai", "Harbin", "Shenyang", "Wuxi", "Nantong",
    "Changzhou", "Wenzhou", "Zhongshan", "Hohhot", "Urumqi", "Sanya",
]

# 港澳台（须排除，只保留中国大陆）。
EXCLUDE_KEYWORDS = ["Hong Kong", "Macau", "Macao", "Taiwan", "Taipei"]

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class GreenhouseAdapter(BaseAdapter):
    name = "greenhouse"

    def fetch(self, boards: list = None, china_only: bool = True) -> list:
        """抓取指定 board 的职位。

        Args:
            boards: board_token 列表，默认 BOARDS。
            china_only: True 时仅保留中国大陆岗位。
        """
        boards = boards or BOARDS
        jobs: list[Job] = []
        for board in boards:
            url = API_URL.format(board_token=board) + "?" + urllib.parse.urlencode({
                "content": "true",
            })
            data = self.get_json(url)
            items = data.get("jobs") or []
            for item in items:
                location = (item.get("location") or {}).get("name", "")
                if china_only and not _is_china(location):
                    continue
                job = self._normalize(item, board)
                if job is not None:
                    jobs.append(job)
        return jobs

    def _normalize(self, item: dict, board_token: str) -> Job | None:
        jid = item.get("id")
        if jid is None:
            return None

        departments = item.get("departments") or []
        dept = departments[0].get("name", "") if departments else ""

        published = item.get("first_published") or item.get("updated_at") or ""
        publish_date = published[:10] if published else ""

        title = item.get("title") or ""
        job_type = "实习" if ("intern" in title.lower()) else "全职"
        location = (item.get("location") or {}).get("name", "")
        province, city_cn, city_en = parse_english_location(location)

        return Job(
            source=self.name,
            job_id=f"{board_token}:{jid}",
            title=title,
            company=item.get("company_name") or board_token,
            location=location,
            location_province=province,
            location_city=city_cn,
            location_city_en=city_en,
            salary="",
            education="",
            job_type=job_type,
            recruit_type=normalize_recruit_type(title, job_type),
            industry=dept,
            company_nature="外企",
            company_size="",
            head_count=0,
            publish_date=publish_date,
            job_url=item.get("absolute_url", ""),
            description=_clean_html(item.get("content") or ""),
        )


def _is_china(location: str) -> bool:
    """判断是否中国大陆岗位（排除港澳台）。"""
    if not location:
        return False
    if any(k in location for k in MAINLAND_CITY_KEYWORDS):
        return True
    if any(k in location for k in EXCLUDE_KEYWORDS):
        return False
    return "China" in location


def _clean_html(raw: str) -> str:
    """把 Greenhouse 返回的 HTML 转成纯文本（含双重转义处理）。"""
    if not raw:
        return ""
    text = raw
    for _ in range(2):  # content 常见双重 HTML 转义
        text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()
