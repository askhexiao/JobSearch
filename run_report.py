#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每周订阅数据周报：汇总订阅情况，正文 + Excel 附件发送给管理员。

用法:
    python run_report.py            # 生成并发送（正文 + Excel 附件）
    python run_report.py --dry-run  # 只打印预览，不发送
"""
from __future__ import annotations

import argparse
import html as html_lib
import io
import json
import re
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.mailer import Mailer

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "unifit100.db"
CONFIG_PATH = ROOT / "config.json"
REPORT_EMAIL = "unifit100@qq.com"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _loads(s) -> list:
    try:
        return json.loads(s or "[]")
    except json.JSONDecodeError:
        return []


def _city_label(loc: str) -> str:
    if loc == "不限":
        return "不限"
    if "-" in loc:
        prov, city = loc.split("-", 1)
        if city == "市辖区":
            return prov[:-1] if prov.endswith("市") else prov
        return city[:-1] if city.endswith("市") else city
    return loc


def _loc_text(row) -> str:
    if row["location_unlimited"]:
        return "不限地点"
    locs = _loads(row["locations"])
    return "、".join(_city_label(l) for l in locs) if locs else "不限地点"


# ---------- 最小 .xlsx 生成（零依赖：zipfile + XML，inline strings）----------
def _xml_escape(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _make_xlsx(headers, rows) -> bytes:
    def cell(col, ridx, text):
        return f'<c r="{col}{ridx}" t="inlineStr"><is><t>{_xml_escape(text)}</t></is></c>'

    sheet_rows = ['<row r="1">' + "".join(cell(_col_letter(i + 1), 1, h) for i, h in enumerate(headers)) + "</row>"]
    for ridx, row in enumerate(rows, 2):
        sheet_rows.append(f'<row r="{ridx}">' + "".join(cell(_col_letter(i + 1), ridx, v) for i, v in enumerate(row)) + "</row>")

    sheet_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 '<sheetData>' + "".join(sheet_rows) + "</sheetData></worksheet>")

    workbook_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<sheets><sheet name="订阅数据" sheetId="1" r:id="rId1"/></sheets></workbook>')

    workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                     'Target="worksheets/sheet1.xml"/></Relationships>')

    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                     '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                     '</Types>')

    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def collect_data() -> tuple[str, list, list]:
    """读取订阅数据，返回 (html正文, Excel表头, Excel行)。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE unsubscribed_at = ''").fetchone()[0]
    unsub = total - active
    daily = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE unsubscribed_at = '' AND frequency = '每天1次'").fetchone()[0]
    weekly = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE unsubscribed_at = '' AND frequency = '每周1次'").fetchone()[0]
    jobs = {r["source"]: r["c"] for r in conn.execute("SELECT source, COUNT(*) c FROM jobs GROUP BY source")}
    subs = conn.execute("SELECT * FROM subscriptions ORDER BY (unsubscribed_at = '') DESC, created_at").fetchall()
    conn.close()

    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "UniFit100 | Job Search · 数据周报",
        "",
        f"统计日期：{today}",
        "",
        "【汇总】",
        f"· 订阅总数：{total}（活跃 {active} · 已退订 {unsub}）",
        f"· 推送频率：每天 1 次 {daily} · 每周 1 次 {weekly}",
        f"· 岗位库：{' · '.join(f'{k} {v}' for k, v in jobs.items()) or '空'}",
        "",
        "📎 订阅数据明细见附件 Excel。",
        "",
        "——",
        "UniFit100 | Job Search · 免费职位订阅工具",
        "职业规划 / 面试辅导免费预约：https://unifit100.com/consultant",
    ]
    body = "".join(html_lib.escape(line) + "<br>" for line in lines)
    html = (
        '<html><body style="font-family:-apple-system,'
        "'PingFang SC',sans-serif;font-size:14px;color:#1f2937;line-height:1.7\">"
        + body + "</body></html>"
    )

    headers = ["邮箱", "职位名称", "招聘类型", "工作地点", "推送频率", "职位发布时长", "状态", "订阅时间"]
    rows = []
    for r in subs:
        rows.append([
            r["email"],
            "、".join(_loads(r["titles"])) or "（未填职位）",
            r["recruit_type"],
            _loc_text(r),
            r["frequency"],
            r["publish_within"],
            "活跃" if not r["unsubscribed_at"] else "已退订",
            (r["created_at"] or "")[:10],
        ])
    return html, headers, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="订阅数据周报")
    parser.add_argument("--dry-run", action="store_true", help="只打印预览，不发送")
    args = parser.parse_args()

    html, headers, rows = collect_data()
    xlsx = _make_xlsx(headers, rows)
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"订阅数据_{today}.xlsx"

    if args.dry_run:
        print(re.sub(r"</?[^>]+>", "", html.replace("<br>", "\n")))
        print(f"\n[附件] {filename}（{len(rows)} 行数据，{len(xlsx)} bytes）")
        for row in rows:
            print(" | ".join(str(c) for c in row))
        return 0

    config = load_config()
    mailer = Mailer(config)
    if not mailer.configured:
        print("[错误] SMTP 未配置，无法发送周报。")
        return 1
    mailer.send_attachment(REPORT_EMAIL, "数据周报 | UniFit100", html, filename, xlsx, XLSX_MIME)
    print(f"数据周报已发送到 {REPORT_EMAIL}（附件 {filename}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
