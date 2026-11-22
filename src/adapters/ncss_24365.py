# -*- coding: utf-8 -*-
"""24365 国家大学生就业服务平台（ncss.cn）适配器。

官方公开 JSON 接口，免登录、无需 cookie：
    GET https://www.ncss.cn/student/jobs/jobslist/ajax/

参数说明（与官网一致）：
    - areaCode : 省级行政区划代码（GB/T 2260 前两位），北京=11、上海=31、广东=44
    - jobName  : 职位关键词
    - offset   : 页码（从 1 开始），每页上限 20 条
    - sourcesName=0 : 仅官方来源职位
"""
from __future__ import annotations

import json
import time
import urllib.parse
from datetime import datetime, timezone

from .base import BaseAdapter
from ..locations import AREA_CODES, city_area_code, provinces_with_cities
from ..models import Job
from ..normalize import normalize_company_nature, normalize_education, normalize_recruit_type

API_URL = "https://www.ncss.cn/student/jobs/jobslist/ajax/"
REFERER = "https://www.ncss.cn/student/jobs/index.html"
DETAIL_URL = "https://www.ncss.cn/student/jobs/{job_id}/detail.html"
PAGE_SIZE = 20  # 官网单页上限


class NCSSAdapter(BaseAdapter):
    name = "24365"

    def fetch(self, keyword: str = "", area: str = "北京", max_pages: int = 100) -> list:
        """按省级地区抓取（直辖市/省级查询用）。"""
        if area not in AREA_CODES:
            raise ValueError(f"未知地区 '{area}'，可选：{', '.join(AREA_CODES.keys())}")
        return self._fetch(keyword, AREA_CODES[area], max_pages, province=area, city="")

    def fetch_by_city(self, keyword: str = "", city_name: str = "", province: str = "", max_pages: int = 100) -> list:
        """按市级地区抓取（6 位城市码），并标记城市名。"""
        code = city_area_code(city_name)
        if not code:
            return []
        return self._fetch(keyword, code, max_pages, province=province, city=city_name)

    def _fetch(self, keyword: str, area_code: str, max_pages: int, province: str = "", city: str = "") -> list:
        jobs: list[Job] = []
        for page in range(1, max_pages + 1):
            url = API_URL + "?" + urllib.parse.urlencode({
                "jobType": "",
                "areaCode": area_code,
                "jobName": keyword,
                "monthPay": "",
                "industrySectors": "",
                "property": "",
                "categoryCode": "",
                "memberLevel": "",
                "recruitType": "",
                "offset": page,
                "limit": PAGE_SIZE,
                "keyUnits": "",
                "degreeCode": "",
                "sourcesName": "0",
                "sourcesType": "",
                "_": int(time.time() * 1000),
            })
            data = self.get_json(url, referer=REFERER)
            if not data.get("flag"):
                break
            items = (data.get("data") or {}).get("list") or []
            if not items:
                break
            for item in items:
                job = self._normalize(item, province, city)
                if job is not None:
                    jobs.append(job)
            if len(items) < PAGE_SIZE:
                break
        return jobs

    def fetch_all(self, keyword: str = "", max_pages: int = 100) -> list:
        """按市级地区分块抓取全部职位（合并去重，直辖市按省级）。"""
        municipalities = {"北京", "上海", "天津", "重庆"}
        jobs: list[Job] = []
        seen: set = set()
        for prov, cities in provinces_with_cities():
            if prov in {"台湾", "香港", "澳门"}:
                continue
            if prov in municipalities:
                batch = self.fetch(keyword=keyword, area=prov, max_pages=max_pages)
            else:
                batch = []
                for city in cities:
                    cn = city[:-1] if city.endswith("市") else city
                    batch.extend(self.fetch_by_city(keyword=keyword, city_name=cn, province=prov, max_pages=max_pages))
            for job in batch:
                if job.job_id not in seen:
                    seen.add(job.job_id)
                    jobs.append(job)
            print(f"  {prov}: {len(batch)} 条")
        return jobs

    def _normalize(self, item: dict, province_override: str = "", city_override: str = "") -> Job | None:
        job_id = item.get("jobId")
        if not job_id:
            return None

        low, high = item.get("lowMonthPay"), item.get("highMonthPay")
        salary = ""
        salary_min = salary_max = 0
        if low is not None and high is not None:
            if low == 0 and high == 0:
                salary = "面议"
            else:
                if low == high:
                    salary = f"{_fmt_pay(low)}K"
                else:
                    salary = f"{_fmt_pay(low)}-{_fmt_pay(high)}K"
                salary_min = int(float(low) * 1000)
                salary_max = int(float(high) * 1000)

        publish_date = ""
        pub = item.get("publishDate")
        if pub:
            try:
                publish_date = datetime.fromtimestamp(pub / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            except (ValueError, OSError, OverflowError):
                pass

        title = item.get("jobName") or ""
        job_type = "实习" if ("实习" in title or "intern" in title.lower()) else "全职"
        education = item.get("degreeName") or ""

        province = province_override or (item.get("areaCodeName") or "")
        if city_override:
            location = city_override
            location_city = city_override
        else:
            location = province
            location_city = ""

        return Job(
            source=self.name,
            job_id=str(job_id),
            title=title,
            company=item.get("recName") or "",
            location=location,
            location_province=province,
            location_city=location_city,
            salary=salary,
            salary_min=salary_min,
            salary_max=salary_max,
            education=education,
            education_level=normalize_education(education),
            job_type=job_type,
            recruit_type=normalize_recruit_type(title, job_type),
            industry=item.get("industrySectorsName") or item.get("industryName") or "",
            company_nature=normalize_company_nature(item.get("recProperty") or ""),
            company_size=item.get("recScale") or "",
            head_count=int(item.get("headCount") or 0),
            publish_date=publish_date,
            job_url=DETAIL_URL.format(job_id=job_id),
            description="",
        )


def _fmt_pay(value) -> str:
    """月薪以 K 计，整数去小数。"""
    try:
        return f"{float(value):g}"
    except (ValueError, TypeError):
        return str(value)
