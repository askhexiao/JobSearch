# -*- coding: utf-8 -*-
"""地点与地区码：省级行政区划代码 + 主要城市中英文映射。

用于：
- 24365 抓取（areaCode = 省级前两位，见 AREA_CODES）
- 订阅地点匹配（中文省份/城市 ↔ 外企英文城市，见 location_matches）
"""
from __future__ import annotations

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

# 主要城市：中文名 -> (所属省份, 英文名)。用于跨源地点匹配。
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

# 非中国大陆地区（订阅与前端均不提供）。
_NON_MAINLAND = {"台湾", "香港", "澳门"}

_CITY_TO_PROVINCE = {c: p for c, (p, _e) in CITIES.items()}
_CITY_EN = {c: e for c, (_p, e) in CITIES.items()}

# 省份 -> 其下主要城市（中英文），用于省份订阅匹配外企岗位。
_PROVINCE_CITIES: dict[str, set] = {}
for _city, (_prov, _en) in CITIES.items():
    _PROVINCE_CITIES.setdefault(_prov, set()).update({_city, _en})

# 前端地点选项（省份 + 城市，不含「全国」「不限」与港澳台）。
LOCATION_CHOICES = sorted(
    (set(AREA_CODES.keys()) | set(CITIES.keys())) - {"全国"} - _NON_MAINLAND
)


def province_of(location: str) -> str:
    """返回地点所属省份；本身是省份则返回自身；未知返回空串。"""
    if location in CITIES:
        return CITIES[location][0]
    if location in AREA_CODES:
        return location
    return ""


def location_tokens(location: str) -> set:
    """返回该地点可匹配的所有字符串（中文/英文/所属省份及下辖城市）。"""
    tokens = {location}
    if location in CITIES:
        prov, en = CITIES[location]
        tokens.add(prov)
        tokens.add(en)
    elif location in AREA_CODES:
        tokens.update(_PROVINCE_CITIES.get(location, set()))
    return tokens


def location_matches(location: str, job_location: str) -> bool:
    """订阅地点是否匹配岗位地点字符串（大小写不敏感、子串匹配）。"""
    if not job_location:
        return False
    jl = job_location.lower()
    return any(t and t.lower() in jl for t in location_tokens(location))
