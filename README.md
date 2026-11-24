# Job Search by UniFit100 · 免费职位订阅工具

> 面向**所有求职者**的免费职位订阅推送工具。订阅你关心的**职位名称 + 工作地点**，定时抓取企业公开职位，邮件推送到你的邮箱。
> **免费、开源、只推公开职位、只覆盖中国大陆。**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![零依赖](https://img.shields.io/badge/dependencies-0-green)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

> **English** — A free, open-source job-subscription tool for **mainland China**. Subscribe by job title + location, and get new openings delivered to your inbox. Zero third-party dependencies (Python 3.9+). Live demo: <https://unifit100.com/jobs> · Resume & interview coaching: <https://unifit100.com/consultant> · Contributors welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## ✨ 它能做什么

- 🔎 **按职位 + 地点订阅**：职位名称最多 5 个、工作地点最多 5 个（或选「不限」）。
- 📬 **邮件推送**：订阅后即时推送首封，之后按「每天 1 次 / 每周 1 次」定时推送**新岗位**。
- 🖥 **网页订阅页**：填表即订阅，支持**管理订阅**（改配置 / 退订），无需命令行。
- 🏢 **只推公开职位**：数据来自企业/官方公开渠道，投递时引导你回原官网。
- 🇨🇳 **只覆盖中国大陆**：自动排除港澳台岗位。
- 🆓 **免费 + 开源 + 零第三方依赖**：仅需 Python 3.9+。

## 🗂 数据源策略

| 类型 | 来源 | 状态 |
|---|---|---|
| 官方源（样例） | 24365 国家大学生就业服务平台（ncss.cn） | ✅ 已跑通（城市级） |
| 央企/国企（样例） | 国聘网（iguopin.com） | ✅ 已跑通 |
| 外企（样例） | Greenhouse ATS（Duolingo / Airbnb / Databricks / MongoDB / Flexport / Riot Games / GoDaddy） | ✅ 已跑通 |
| 更多源（共创） | 外企 ATS、国内大厂公开接口、政府/高校就业平台 | 🎯 认领见 [Issues](https://github.com/askhexiao/JobSearch-CN/issues) |
| 商业平台 | 智联 / BOSS / 应届生（有反爬 + 合规灰色） | ❌ 不碰 |

## ⚖️ 合规声明

本项目只抓取**企业公开的职位信息**，并引导用户**回到原官网投递**，不替代任何平台。

三条红线，严格遵守：

1. **不碰求职者简历/个人信息**（遵守《个人信息保护法》）。
2. **不突破技术防护**（不绕验证码、登录墙、蜜罐、封禁）。
3. **不"实质性替代"原平台**（纯订阅导流，非二次售卖）。

抓取遵循礼貌原则：请求限频、真实 User-Agent、失败重试与退避。

**完整合规说明（robots.txt 现状、个人信息处理、退订、内容版权、风险提示、免责声明、侵权下架机制）见 [COMPLIANCE.md](COMPLIANCE.md)。**

> 🔒 本项目唯一收集的个人信息是**订阅邮箱**，仅用于职位推送；用户可**随时退订**，退订后立即停止推送。不抓取、不存储任何简历 / 姓名 / 电话等个人信息。

> ⚠️ **风险提示**：数据来自企业公开渠道，版权归原发布方；本项目仅供学习研究，不构成求职建议。数据源平台可能依据其服务条款要求停止抓取，若发生将立即停用对应源并下架数据。详情见 [COMPLIANCE.md](COMPLIANCE.md)。

## 🚀 快速开始

零第三方依赖，仅需 **Python 3.9+**：

```bash
git clone https://github.com/askhexiao/JobSearch-CN.git
cd JobSearch

# ① 抓取职位并入库
python run_scrape.py               # 全量抓取：24365(城市级+关键词) + 国聘 + 外企
python run_scrape.py --light       # 轻量抓取：24365 城市级 + 国聘 + 外企（适合每日定时）

# ② 启动网页订阅页
python web_server.py               # 打开 http://127.0.0.1:8000 填表订阅
```

## 📬 订阅与邮件推送

### 工作流

1. 用户在订阅页填写：**邮箱 + 职位名称（≤5）+ 招聘类型（校招/社招）+ 工作地点（省-市，≤5，或「不限」）+ 推送频率（每天/每周）+ 职位发布时长（1周/1个月/3个月/6个月）**。
2. 订阅后**即时推送首封**；之后定时「抓取入库 → 读库匹配 → 去重推送」，**只发新岗位**：

```bash
python run_scrape.py               # ① 抓取入库
python run_push.py --dry-run       # ② 预览推送（读库匹配）
cp config.example.json config.json # 填 SMTP 凭证
python run_push.py                 # ③ 真实发送
```

**推送时间**：每天 10:00 推「每天1次」订阅，每周三 10:00 推「每周1次」订阅，用 `--frequency` 过滤：

```bash
# 每天 10:00 推送「每天1次」订阅
0 10 * * * cd /path/to/JobSearch && python3 run_push.py --frequency 每天1次

# 每周三 10:00 推送「每周1次」订阅
0 10 * * 3 cd /path/to/JobSearch && python3 run_push.py --frequency 每周1次
```

### 阿里云 DirectMail 配置

1. 阿里云控制台 →「邮件推送（DirectMail）」→ **发信域名**：新增并验证你的域名。
2. **发信地址**：基于已验证域名创建，如 `noreply@your-domain.com`。
3. 在该地址上**生成 SMTP 密码**（只显示一次）。
4. 填入 `config.json`（已 gitignore，**勿提交**）：

```json
{
  "web_base_url": "https://你的域名/jobs",
  "smtp": {
    "host": "smtpdm.aliyun.com",
    "port": 465,
    "ssl": true,
    "username": "noreply@your-domain.com",
    "password": "你的SMTP密码",
    "from_name": "UniFit100",
    "from_addr": "noreply@your-domain.com"
  }
}
```

> 邮件为 **HTML 格式**：含「管理订阅」链接、英文岗位标注「英文招聘」、近期岗位标 `[新]`，按发布日期倒序。

### 部署到阿里云

完整部署指南（Nginx 子路径反代 + systemd + cron + HTTPS）见 [DEPLOY.md](DEPLOY.md)。

## 📁 目录结构

```
JobSearch/
├── src/
│   ├── models.py              # 统一 Job 数据模型
│   ├── db.py                  # SQLite 职位存储（unique(source,job_id) upsert）
│   ├── locations.py           # 省份码 + 城市中英文映射 + 地点匹配
│   ├── normalize.py           # 字段归一化 + 中英职位词典 + 语言检测
│   ├── subscription.py        # 订阅模型 + 存储 + 匹配 + 校验 + 软退订
│   ├── mailer.py              # SMTP 邮件（阿里云 DirectMail）
│   ├── pusher.py              # 匹配 + 去重 + 渲染邮件 + 推送
│   └── adapters/
│       ├── base.py            # 适配器基类（限频 + 礼貌抓取 + 重试）
│       ├── ncss_24365.py      # 24365 官方平台适配器（城市级）
│       ├── greenhouse.py      # Greenhouse 外企适配器（筛中国大陆）
│       └── iguopin.py         # 国聘网适配器（央企/国企）
├── web/
│   ├── index.html             # 订阅页 + 管理订阅页
│   ├── style.css              # 样式（含 FrankSong 子集字体）
│   ├── app.js                 # 表单交互 + 校验
│   ├── pca.json               # 省-市行政区划数据
│   └── fangsong.woff2         # 方正新报宋（子集化，106KB）
├── brand/
│   ├── logo.png               # 品牌主 Logo
│   └── logo_app.png           # App 图标
├── run_scrape.py              # 入口：全量/轻量抓取三源
├── run_ncss.py                # 入口：抓取 24365
├── run_greenhouse.py          # 入口：抓取 Greenhouse
├── run_iguopin.py             # 入口：抓取国聘网
├── run_push.py                # 入口：匹配订阅 + 邮件推送
├── web_server.py              # 入口：订阅页 HTTP 服务（支持子路径部署）
├── config.example.json        # SMTP 配置模板
├── COMPLIANCE.md              # 合规说明与免责声明
├── DEPLOY.md                  # 阿里云部署指南
├── LICENSE                    # MIT
└── unifit100.db               # 本地 SQLite（运行后生成，已 gitignore）
```

## 🧾 数据字段

统一后的职位模型（`src/models.py`）：

| 字段 | 说明 |
|---|---|
| `source` / `job_id` | 数据源 + 源内唯一 ID，构成去重唯一键 |
| `title` / `company` / `location` | 职位 / 公司 / 工作地点（展示） |
| `salary` / `salary_min` / `salary_max` | 薪资展示 / 元/月区间（0=面议） |
| `location_province` / `location_city` / `location_city_en` | 省 / 市 / 英文市（标准化） |
| `education` / `education_level` | 学历展示 / 枚举 |
| `recruit_type` / `job_type` | 校招·社招·实习 / 实习·全职 |
| `company_nature` / `company_size` / `industry` | 国企·民企·外企·事业单位 / 规模 / 行业 |
| `publish_date` / `job_url` | 发布日期 / 回原官网投递链接 |
| `language` | 岗位语言（中文 / 英文） |
| `description` | 职位描述（纯文本） |

## 📈 当前进度

- [x] 24365 适配器（全国 31 省 + 城市级，3631 条）
- [x] Greenhouse 适配器（7 个外企 board，106 条中国大陆岗位）
- [x] 国聘网适配器（201 条，央企/国企，城市级地点）
- [x] 统一数据模型 + 字段标准化（薪资/地点/学历/招聘类型/公司性质）
- [x] SQLite 去重（同源 unique + 跨源 title+company+city）
- [x] 订阅模型（职位 ≤5、地点 ≤5 / 不限、招聘类型、推送频率、发布时长）
- [x] 前端订阅页 + 管理订阅页（省-市联动 + 校验 + 品牌样式 + 软退订）
- [x] HTML 邮件推送（管理订阅链接 + 英文标签 + 新岗位置顶）
- [x] 中国大陆过滤（排除港澳台）
- [x] 城市级抓取（24365 细分到城市维度）
- [x] 中英职位词典（打通中文职位名 ↔ 外企英文标题）
- [x] 订阅即时首封推送 + 定时推送（cron）
- [x] 子路径部署（`--base-path`，如 `/jobs`）
- [x] 开源共创启动（CONTRIBUTING.md + 职位源申请模板 + 认领 issue）
- [ ] 更多数据源（通过共创认领，见 [Issues](https://github.com/askhexiao/JobSearch-CN/issues)）
- [ ] GitHub Actions 定时任务（当前用 cron，可选迁移）

## 🗺 Roadmap

1. **更多数据源（开源共创）**：通过 [CONTRIBUTING.md](CONTRIBUTING.md) 的认领流程，扩展外企 ATS、国内大厂公开接口、政府/高校就业平台。见 [Issues](https://github.com/askhexiao/JobSearch-CN/issues)。
2. **GitHub Actions**：云端定时抓取 + 推送，不依赖个人服务器（当前用阿里云 cron）。
3. **中英职位词典扩充**：覆盖更多外企英文职位标题。

## 💬 求职咨询

本工具面向**所有求职者**免费开放。**UniFit100 咨询工作室**则专注为**校招生与初阶求职者**提供简历 / 面试 / 职业规划辅导。

需要**简历辅导、面试辅导、职业规划**？欢迎访问：

👉 **<https://unifit100.com/consultant>**

如果你觉得这个工具有用，请点个 ⭐ Star，让更多求职者看到 🙏

## 🤝 开源共创

想新增一个职位数据源？欢迎认领！

- 📖 **先读 [CONTRIBUTING.md](CONTRIBUTING.md)**：三条合规红线 + 适配器模板 + 自测命令 + PR 审查清单。
- 🎯 **认领任务**：在 [Issues](https://github.com/askhexiao/JobSearch-CN/issues) 找 `good first issue` 标签的「新职位源」，或按模板提一个「新职位源申请」。
- 🔴 **红线**：只接**公开接口**（免登录 / 免签名 / 免验证码 / 免加密）；凡需要签名、登录、验证码的接口一律拒绝，不提交绕过方案。

提交 PR 前请本地自测通过，并在 PR 描述里附上审查清单（见 CONTRIBUTING.md）。

## 📄 License

[MIT](LICENSE) © 2026 UniFit100
