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
from ..locations import AREA_CODES
from ..models import Job

API_URL = "https://www.ncss.cn/student/jobs/jobslist/ajax/"
REFERER = "https://www.ncss.cn/student/jobs/index.html"
DETAIL_URL = "https://www.ncss.cn/student/jobs/{job_id}/detail.html"
PAGE_SIZE = 20  # 官网单页上限


class NCSSAdapter(BaseAdapter):
    name = "24365"

    def fetch(self, keyword: str = "", area: str = "北京", max_pages: int = 100) -> list:
        """抓取职位。

        Args:
            keyword: 职位关键词，空串表示不限。
            area: 地区名（见 AREA_CODES），默认北京。
            max_pages: 最大翻页数（安全上限，每页 20 条）。
        """
        if area not in AREA_CODES:
            raise ValueError(f"未知地区 '{area}'，可选：{', '.join(AREA_CODES.keys())}")
        area_code = AREA_CODES[area]

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
                job = self._normalize(item)
                if job is not None:
                    jobs.append(job)
            if len(items) < PAGE_SIZE:
                break
        return jobs

    def _normalize(self, item: dict) -> Job | None:
        job_id = item.get("jobId")
        if not job_id:
            return None

        low, high = item.get("lowMonthPay"), item.get("highMonthPay")
        salary = ""
        if low is not None and high is not None:
            if low == 0 and high == 0:
                salary = "面议"
            elif low == high:
                salary = f"{_fmt_pay(low)}K"
            else:
                salary = f"{_fmt_pay(low)}-{_fmt_pay(high)}K"

        publish_date = ""
        pub = item.get("publishDate")
        if pub:
            try:
                publish_date = datetime.fromtimestamp(pub / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            except (ValueError, OSError, OverflowError):
                pass

        title = item.get("jobName") or ""
        job_type = "实习" if ("实习" in title or "intern" in title.lower()) else "全职"

        return Job(
            source=self.name,
            job_id=str(job_id),
            title=title,
            company=item.get("recName") or "",
            location=item.get("areaCodeName") or "",
            salary=salary,
            education=item.get("degreeName") or "",
            job_type=job_type,
            industry=item.get("industrySectorsName") or item.get("industryName") or "",
            company_nature=item.get("recProperty") or "",
            company_size=item.get("recScale") or "",
            head_count=int(item.get("headCount") or 0),
            publish_date=publish_date,
            job_url=DETAIL_URL.format(job_id=job_id),
            description="",
            raw=json.dumps(item, ensure_ascii=False),
        )


def _fmt_pay(value) -> str:
    """月薪以 K 计，整数去小数。"""
    try:
        return f"{float(value):g}"
    except (ValueError, TypeError):
        return str(value)
