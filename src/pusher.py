# -*- coding: utf-8 -*-
"""推送逻辑：匹配、去重、渲染邮件、发送。"""
from __future__ import annotations

import html as html_lib
from datetime import date, timedelta

from .subscription import job_key, matches

CONSULT_URL = "https://unifit100.com/consultant"
MAX_JOBS_PER_EMAIL = 20
RECENT_DAYS = 7  # 发布时间在最近 N 天内标记为「新」


def _city_label(loc: str) -> str:
    """把地点路径简化为城市名：'广东省-深圳市'->'深圳'、'北京市-市辖区'->'北京'。"""
    if loc == "不限":
        return "不限"
    if "-" in loc:
        prov, city = loc.split("-", 1)
        if city == "市辖区":
            return prov[:-1] if prov.endswith("市") else prov
        return city[:-1] if city.endswith("市") else city
    return loc


def _sub_summary(sub) -> str:
    """订阅摘要：职位 · 招聘类型 · 地点 · 发布时长。"""
    parts = [("、".join(sub.titles)) if sub.titles else "不限职位"]
    parts.append(sub.recruit_type)
    if sub.location_unlimited:
        parts.append("不限地点")
    elif sub.locations:
        parts.append("、".join(_city_label(l) for l in sub.locations))
    parts.append(sub.publish_within)
    return " · ".join(parts)


def render_email(sub, jobs, web_base_url: str) -> str:
    """渲染 HTML 邮件（底部「管理订阅」为可点击文字链接）。"""
    summary = _sub_summary(sub)
    manage_url = f"{web_base_url}/manage?email={sub.email}"

    lines = [
        "UniFit100 | Job Search",
        "",
        f"Hi，你订阅的职位有新岗位（共 {len(jobs)} 个）：",
        "",
        f"【订阅】{summary}",
        "",
        "——",
    ]
    for idx, j in enumerate(jobs[:MAX_JOBS_PER_EMAIL], 1):
        title = j.title
        if j.publish_date and j.publish_date >= (date.today() - timedelta(days=RECENT_DAYS)).isoformat():
            title = f"{title} [新]"
        lines.append(f"{idx}. {title}")

        parts = [j.company, j.location, j.salary]
        if j.language == "英文":
            parts.append("英文招聘")
        parts.append(j.publish_date)
        meta = " | ".join(p for p in parts if p)
        lines.append(meta)

        lines.append(f"投递 → {j.job_url}")
        lines.append("")
    if len(jobs) > MAX_JOBS_PER_EMAIL:
        lines.append(f"（仅展示前 {MAX_JOBS_PER_EMAIL} 个，共 {len(jobs)} 个）")
        lines.append("")
    lines.append("——")
    lines.append("UniFit100 | Job Search · 免费的职位订阅工具")
    lines.append(f"职业规划 / 面试辅导免费预约：{CONSULT_URL}")

    body = "".join(html_lib.escape(line) + "<br>" for line in lines)
    body += f'<a href="{manage_url}">管理订阅</a>'
    return (
        '<html><body style="font-family:-apple-system,'
        "'PingFang SC',sans-serif;font-size:14px;color:#1f2937;line-height:1.7\">"
        + body + "</body></html>"
    )


def push_subscription(sub, pool, mailer, sub_store, web_base_url: str, dry_run: bool = False) -> int:
    """为单个订阅匹配岗位、跨源去重、发送邮件。返回发送的岗位数。"""
    matched = [j for j in pool if matches(sub, j)]
    seen: set = set()
    deduped = []
    for j in matched:
        k = j.dedup_key()
        if k not in seen:
            seen.add(k)
            deduped.append(j)
    new_jobs = [j for j in deduped if not sub_store.is_sent(sub.email, job_key(j))]
    new_jobs.sort(key=lambda j: j.publish_date or "", reverse=True)
    if not new_jobs:
        return 0

    subject = f"职位订阅更新 - 新岗位 {len(new_jobs)} 个 | UniFit100"
    body = render_email(sub, new_jobs, web_base_url)
    if dry_run:
        print(f"[dry-run] {sub.email}：{len(new_jobs)} 个新岗位（未发送）")
    else:
        mailer.send(sub.email, subject, body)
        for j in new_jobs:
            sub_store.mark_sent(sub.email, job_key(j))
    return len(new_jobs)
