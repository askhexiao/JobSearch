# 贡献指南（CONTRIBUTING）

> 想给 **UniFit100 | Job Search** 新增一个职位来源？先花 3 分钟读完这里，尤其第一条红线。

---

## ⚠️ 一、合规红线（先读，不可触碰）

本项目最看重合规。**任何贡献都必须满足三条红线**（详见 [COMPLIANCE.md](COMPLIANCE.md)）：

1. **不碰个人信息** —— 不抓取、不存储简历 / 姓名 / 电话等任何个人数据。
2. **不突破技术防护** —— 只接「公开接口」：**免登录、免签名、免 token、免验证码、免加密**。
   - ❌ 凡需要签名、登录、验证码、蜜罐、加密、伪造 token 才能拿到数据的，**一律拒绝，不要提交任何绕过方案**。
3. **不实质性替代原平台** —— 纯订阅导流，投递链接必须回原官网。

> **判定口诀**：「不用登录、不用破解、浏览器直接能打开看到的岗位数据」才能接。其余一律不碰。

---

## 二、什么是「一个职位源」

一个职位源 = 一个公开接口 + 一个适配器文件，把该接口的岗位归一化成统一的 `Job` 模型，只保留中国大陆岗位。

已接入的源在 `src/adapters/`：

| 文件 | 来源 | 类型 |
|---|---|---|
| `ncss_24365.py` | 24365 政府平台 | 公开 JSON |
| `iguopin.py` | 国聘网 | 公开 POST |
| `greenhouse.py` | Greenhouse ATS | 官方 Job Board API |
| `microsoft.py` | 微软（Eightfold） | 公开 GET |
| `alibaba.py` | 阿里巴巴社招 | 公开 POST（浏览器同款 CSRF） |
| `workday.py` | Workday 平台（NVIDIA/Intel 等一批） | 公开 POST |

---

## 三、新增一个职位源（适配器模板）

1. 在 `src/adapters/` 下新建 `{source}.py`。
2. 继承 `BaseAdapter`，实现 `fetch()` 返回 `list[Job]`。
3. 在 `run_scrape.py` 里 import 并注册一个抓取步骤。
4. 本地自测通过后提交 PR。

### 最小模板

```python
# -*- coding: utf-8 -*-
"""XXX 招聘适配器（公开接口）。"""
from .base import BaseAdapter
from ..locations import parse_english_location   # 英文地点 -> (省, 市中文, 市英文)
from ..models import Job
from ..normalize import normalize_recruit_type   # 职位名 -> 校招/社招/实习

class XxxAdapter(BaseAdapter):
    name = "xxx"   # 数据源唯一标识，用于去重

    def fetch(self) -> list:
        jobs = []
        # 用 self.get_json / self.post_json 调接口（已内置限频+重试+退避）
        data = self.get_json("https://example.com/api/jobs")
        for item in data.get("list", []):
            job = self._normalize(item)
            if job is not None:
                jobs.append(job)
        return jobs

    def _normalize(self, item: dict) -> Job | None:
        jid = item.get("id")
        if not jid:
            return None
        # 地点：只保留中国大陆，港澳台跳过
        province, city_cn, city_en = parse_english_location(item.get("location", ""))
        return Job(
            source=self.name,
            job_id=f"xxx:{jid}",
            title=item.get("title", ""),
            company="示例公司",
            location=item.get("location", ""),
            location_province=province,
            location_city=city_cn,
            location_city_en=city_en,
            publish_date=item.get("date", ""),
            job_url=item.get("url", ""),   # 必须回原官网投递
        )
```

### 5 条硬性要求

1. **只用公开接口**（见红线，宁可少接一个源，也不碰签名/登录）。
2. **只保留中国大陆岗位**：过滤港澳台（`Hong Kong` / `Macau` / `Taiwan` / `Taipei`）。
3. **礼貌抓取**：用 `BaseAdapter` 的 `get_json` / `post_json`（自带限频 + 重试 + 退避），不要自己写高频循环。
4. **回原官网投递**：`job_url` 必须是原官网职位详情链接，不能是转存/镜像。
5. **字段尽量填全**：`title` / `company` / `location_city` / `publish_date` / `job_url` 至少要齐全；`salary` / `education` / `description` 有就填。

---

## 四、提交前自测

```bash
cd /path/to/JobSearch
PYTHONDONTWRITEBYTECODE=1 python3 -c "
from src.adapters.your_source import YourAdapter
jobs = YourAdapter().fetch()
print(len(jobs), '条')
for j in jobs[:5]:
    print(j.title, '|', j.location_city, '|', j.job_url)
"
```

确认：能跑通、只有大陆岗位、链接回原官网。

---

## 五、PR 审查清单

提交 PR 时，请在描述里附上（复制下面这段勾选）：

```
- [ ] 接口公开（免登录/免签名/免验证码），附一条 curl 或说明
- [ ] 只保留中国大陆岗位（已过滤港澳台）
- [ ] 礼貌抓取（用 BaseAdapter 限频+重试）
- [ ] 投递链接回原官网
- [ ] 本地自测通过（附输出截图/文本）
- [ ] 已在 run_scrape.py 注册
```

---

## 六、待接入职位源（可认领）

想接但还没接的方向，认领前**先开一个 issue「新职位源申请」**，避免和别人重复：

- [ ] Greenhouse 更多 board（有中国大陆办公室的外企）
- [ ] Lever / Ashby 里含中国大陆岗位的公司
- [ ] 更多 Workday 企业（芯片 / 新能源车企 / 外企）
- [ ] 有公开接口的国内大厂（逐个验证接口是否免签名）
- [ ] 飞书招聘（keyless 公开接口，字节系）
- [ ] 其它政府 / 高校就业平台（公开 JSON）

> 认领方式：先提 issue 说明「源 URL + 接口是否公开 + 预期岗位量」，得到维护者确认后再实现，避免白做。

---

## 七、联系方式

- 提 issue（推荐）：本项目 GitHub 仓库
- 邮箱：<query@unifit100.com>
- 咨询官网：<https://unifit100.com/consultant>
