# -*- coding: utf-8 -*-
"""国聘网（iguopin.com）适配器 —— 央企/国企 + 校招/社招。

公开 POST JSON 接口，免登录：
    POST https://gp-api.iguopin.com/api/jobs/v1/list
参数：page（页码，从 1 起）、pageSize（服务端上限 10）、job_name（关键词，可选）。
服务端 total 上限 200，即最多 20 页 × 10 条。
"""
from __future__ import annotations

import json
from datetime import date

from .base import BaseAdapter
from ..locations import AREA_CODES, CITIES
from ..models import Job
from ..normalize import normalize_company_nature, normalize_education, normalize_recruit_type

API_URL = "https://gp-api.iguopin.com/api/jobs/v1/list"
REFERER = "https://www.iguopin.com/"
DETAIL_URL = "https://www.iguopin.com/job/detail?id={job_id}"
PAGE_SIZE = 10  # 服务端单页上限

_NON_MAINLAND = {"香港", "澳门", "台湾"}
_PROVINCE_BY_CODE = {code: name for name, code in AREA_CODES.items() if code}


class IguopinAdapter(BaseAdapter):
    name = "iguopin"

    def fetch(self, keyword: str = "", max_pages: int = 20) -> list:
        """抓取国聘职位（服务端 total 上限 200，20 页 × 10）。"""
        jobs: list[Job] = []
        for page in range(1, max_pages + 1):
            payload = {"page": page, "pageSize": PAGE_SIZE}
            if keyword:
                payload["job_name"] = keyword
            data = self.post_json(API_URL, payload, referer=REFERER)
            if data.get("code") != 200:
                break
            items = (data.get("data") or {}).get("list") or []
            if not items:
                break
            for item in items:
                job = self._normalize(item)
                if job is not None:
                    jobs.append(job)
            if len(items) < PAGE_SIZE:
                break
        return jobs

    def _normalize(self, item: dict) -> Job | None:
        jid = item.get("job_id")
        if not jid:
            return None

        title = item.get("job_name") or ""

        # 薪资（元/月）
        min_wage = int(item.get("min_wage") or 0)
        max_wage = int(item.get("max_wage") or 0)
        salary_min = salary_max = 0
        salary = ""
        if item.get("is_negotiable") or (min_wage == 0 and max_wage == 0):
            salary = "面议"
        else:
            salary_min, salary_max = min_wage, max_wage
            salary = f"{salary_min}-{salary_max}元/月" if salary_min != salary_max else f"{salary_min}元/月"

        # 地点（省/市/区 + 英文城市）
        province, city, district, city_en = _parse_location(item.get("district_list"))
        if province in _NON_MAINLAND:
            return None  # 只覆盖中国大陆
        location = ""
        if city:
            location = f"{city}-{district}" if district else city

        recruit_type = _recruit_type(item, title)
        education = item.get("education_cn") or ""
        ci = item.get("company_info") or {}

        # 截止日期：已过期的岗位不收录（只留当前在招）
        deadline = (item.get("end_time") or "")[:10]
        if deadline and deadline < date.today().isoformat():
            return None

        return Job(
            source=self.name,
            job_id=str(jid),
            title=title,
            company=item.get("company_name") or "",
            location=location,
            location_province=province,
            location_city=city,
            location_district=district,
            location_city_en=city_en,
            salary=salary,
            salary_min=salary_min,
            salary_max=salary_max,
            education=education,
            education_level=normalize_education(education),
            job_type="实习" if recruit_type == "实习" else "全职",
            recruit_type=recruit_type,
            industry=ci.get("industry_cn") or item.get("category_cn") or "",
            company_nature=normalize_company_nature(ci.get("nature_cn") or ""),
            company_size=ci.get("scale_cn") or "",
            head_count=int(item.get("amount") or 0),
            publish_date=(item.get("start_time") or "")[:10],
            deadline=deadline,
            job_url=DETAIL_URL.format(job_id=jid),
            description=(item.get("contents") or "").strip(),
        )


def _parse_location(district_list) -> tuple:
    """从 district_list 提取 (省, 市, 区, 英文市)。"""
    province = city = district = city_en = ""
    if not district_list:
        return province, city, district, city_en
    loc = district_list[0] or {}
    prov_code = str(loc.get("province") or "")
    province = _PROVINCE_BY_CODE.get(prov_code[:2], "")
    area_cn = loc.get("area_cn") or ""
    parts = [p for p in area_cn.split("-") if p]
    if parts:
        city = parts[0]
        if len(parts) >= 2:
            district = parts[1]
        if city in CITIES:
            city_en = CITIES[city][1]
    return province, city, district, city_en


def _recruit_type(item: dict, title: str) -> str:
    """招聘类型：优先 nature_cn（校招/社招/实习），回退 recruitment_type_cn / 标题。"""
    nature = item.get("nature_cn") or ""
    if nature in ("校招", "社招", "实习"):
        return nature
    rt = item.get("recruitment_type_cn") or ""
    if "校园" in rt:
        return "校招"
    if "社会" in rt:
        return "社招"
    return normalize_recruit_type(title)
