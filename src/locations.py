# -*- coding: utf-8 -*-
"""地点与地区码：省级行政区划代码 + 城市中英文映射 + 省-市-县路径匹配。

地点值有两种形态：
- 单名称（兼容旧数据）：如「广东」「深圳」
- 省-市-县路径（前端联动选择器）：如「广东省-深圳市-南山区」
"""
from __future__ import annotations

import json
from pathlib import Path

# 省级行政区划代码（GB/T 2260 前两位）——24365 areaCode 参数。
AREA_CODES = {
    "全国": "", "北京": "11", "天津": "12", "河北": "13", "山西": "14",
    "内蒙古": "15", "辽宁": "21", "吉林": "22", "黑龙江": "23",
    "上海": "31", "江苏": "32", "浙江": "33", "安徽": "34", "福建": "35",
    "江西": "36", "山东": "37", "河南": "41", "湖北": "42", "湖南": "43",
    "广东": "44", "广西": "45", "海南": "46", "重庆": "50", "四川": "51",
    "贵州": "52", "云南": "53", "西藏": "54", "陕西": "61", "甘肃": "62",
    "青海": "63", "宁夏": "64", "新疆": "65", "台湾": "71", "香港": "81",
    "澳门": "82",
}

# 主要城市：中文名 -> (所属省份, 英文名)。用于外企英文地点匹配。
CITIES = {
    "北京": ("北京", "Beijing"), "上海": ("上海", "Shanghai"),
    "天津": ("天津", "Tianjin"), "重庆": ("重庆", "Chongqing"),
    "深圳": ("广东", "Shenzhen"), "广州": ("广东", "Guangzhou"),
    "东莞": ("广东", "Dongguan"), "佛山": ("广东", "Foshan"),
    "珠海": ("广东", "Zhuhai"), "杭州": ("浙江", "Hangzhou"),
    "宁波": ("浙江", "Ningbo"), "南京": ("江苏", "Nanjing"),
    "苏州": ("江苏", "Suzhou"), "无锡": ("江苏", "Wuxi"),
    "成都": ("四川", "Chengdu"), "武汉": ("湖北", "Wuhan"),
    "西安": ("陕西", "Xian"), "青岛": ("山东", "Qingdao"),
    "济南": ("山东", "Jinan"), "长沙": ("湖南", "Changsha"),
    "大连": ("辽宁", "Dalian"), "厦门": ("福建", "Xiamen"),
    "福州": ("福建", "Fuzhou"), "合肥": ("安徽", "Hefei"),
    "郑州": ("河南", "Zhengzhou"), "昆明": ("云南", "Kunming"),
    "沈阳": ("辽宁", "Shenyang"), "哈尔滨": ("黑龙江", "Harbin"),
    "石家庄": ("河北", "Shijiazhuang"), "太原": ("山西", "Taiyuan"),
    "南昌": ("江西", "Nanchang"), "贵阳": ("贵州", "Guiyang"),
    "南宁": ("广西", "Nanning"), "海口": ("海南", "Haikou"),
    "兰州": ("甘肃", "Lanzhou"), "银川": ("宁夏", "Yinchuan"),
    "西宁": ("青海", "Xining"), "乌鲁木齐": ("新疆", "Urumqi"),
    "呼和浩特": ("内蒙古", "Hohhot"), "拉萨": ("西藏", "Lhasa"),
}

_NON_MAINLAND = {"台湾", "香港", "澳门"}
_MUNICIPALITIES = {"北京", "上海", "天津", "重庆"}

_CITY_TO_PROVINCE = {c: p for c, (p, _e) in CITIES.items()}
_CITY_EN = {c: e for c, (_p, e) in CITIES.items()}

# 省份 -> 其下主要城市（中英文），用于「只选省份」时匹配外企岗位。
_PROVINCE_CITIES: dict[str, set] = {}
for _city, (_prov, _en) in CITIES.items():
    _PROVINCE_CITIES.setdefault(_prov, set()).update({_city, _en})

# 英文城市名 -> 中文（用于从外企英文地点反推中文）。
_CITY_BY_EN = {e: c for c, (_p, e) in CITIES.items()}


def parse_english_location(raw: str) -> tuple:
    """从英文地点串提取 (省, 市中文, 市英文)；无匹配时返回空串。"""
    if not raw:
        return "", "", ""
    rl = raw.lower()
    for en, cn in _CITY_BY_EN.items():
        if en.lower() in rl:
            return CITIES[cn][0], cn, en
    return "", "", ""

# 前端旧版地点候选（省份 + 城市，不含「全国」「不限」与港澳台）。
LOCATION_CHOICES = sorted(
    (set(AREA_CODES.keys()) | set(CITIES.keys())) - {"全国"} - _NON_MAINLAND
)

# 行政区划后缀（长优先）与伪层级（如直辖市的「市辖区」）。
_ADMIN_SUFFIXES = sorted(
    ["特别行政区", "壮族自治区", "回族自治区", "维吾尔自治区", "自治区", "自治州", "自治县", "地区", "省", "市", "区", "县", "旗", "盟", "林区"],
    key=len, reverse=True,
)
_PSEUDO = {"市辖区", "省直辖县级行政区划", "直辖县级行政区划", "自治区直辖县级行政区划"}


def _strip_admin_suffix(name: str) -> str:
    name = (name or "").strip()
    if name in _PSEUDO:
        return name
    for s in _ADMIN_SUFFIXES:
        if name.endswith(s) and len(name) > len(s):
            return name[: -len(s)]
    return name


def _components(location: str) -> list:
    """把地点（路径或单名称）拆成规范化后的省/市/县组件。"""
    parts = [p.strip() for p in (location or "").split("-") if p.strip()]
    return [n for n in (_strip_admin_suffix(p) for p in parts) if n and n not in _PSEUDO]


def province_of(location: str) -> str:
    """返回地点所属省份名；本身是省份返回自身；未知返回空串。"""
    comps = _components(location)
    if not comps:
        return ""
    first = comps[0]
    if first in AREA_CODES:
        return first
    if first in CITIES:
        return CITIES[first][0]
    return ""


def location_tokens(location: str) -> set:
    """返回该地点可匹配的所有字符串（中文/英文/所属省份）。"""
    tokens = {location}
    comps = _components(location)
    if not comps:
        return tokens

    prov = comps[0]
    tokens.add(prov)
    if prov in CITIES:
        _p, en = CITIES[prov]
        tokens.add(_p)   # 所属省份（兼容单城市格式，匹配 24365 省级地点）
        tokens.add(en)   # 英文

    if prov in _MUNICIPALITIES:
        if len(comps) >= 2:
            tokens.add(comps[1])  # 县区
    else:
        if len(comps) >= 2:
            city = comps[1]
            tokens.add(city)
            if city in CITIES:
                tokens.add(CITIES[city][1])
        else:
            # 只选了省份 -> 展开其下主要城市（匹配外企英文城市）
            if prov in AREA_CODES:
                tokens.update(_PROVINCE_CITIES.get(prov, set()))
        if len(comps) >= 3:
            tokens.add(comps[2])

    return tokens


def location_matches(location: str, job_location: str) -> bool:
    """订阅地点是否匹配岗位地点字符串（大小写不敏感、子串匹配）。"""
    if not job_location:
        return False
    jl = job_location.lower()
    return any(t and t.lower() in jl for t in location_tokens(location))


# ---------- 省-市行政区划数据（用于 24365 市级筛选） ----------

_PCA_PATH = Path(__file__).resolve().parent.parent / "web" / "pca.json"
_PCA_CACHE: list | None = None
_CITY_CODES_CACHE: dict | None = None


def _load_pca() -> list:
    global _PCA_CACHE
    if _PCA_CACHE is None:
        try:
            _PCA_CACHE = json.loads(_PCA_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _PCA_CACHE = []
    return _PCA_CACHE


def city_codes() -> dict:
    """城市名 -> 6 位行政区划码（24365 市级筛选 areaCode 用）。"""
    global _CITY_CODES_CACHE
    if _CITY_CODES_CACHE is None:
        codes: dict = {}
        for prov in _load_pca():
            for city in prov.get("children", []):
                name = city.get("name", "")
                code4 = str(city.get("code", ""))
                if not name or not code4:
                    continue
                code6 = code4 + "00"
                codes[name] = code6
                if name.endswith("市"):
                    codes[name[:-1]] = code6
        _CITY_CODES_CACHE = codes
    return _CITY_CODES_CACHE


def city_area_code(city_name: str) -> str:
    """城市名 -> 6 位行政区划码；未知返回空串。"""
    return city_codes().get((city_name or "").strip(), "")


def provinces_with_cities() -> list:
    """返回 [(省份规范化名, [城市全名...])]，用于市级分块抓取。"""
    out = []
    for prov in _load_pca():
        pnorm = _strip_admin_suffix(prov.get("name", ""))
        cities = [c.get("name", "") for c in prov.get("children", []) if c.get("name")]
        out.append((pnorm, cities))
    return out
