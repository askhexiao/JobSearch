# UniFit100 | Job Search — 免费职位订阅工具

> 面向初阶求职者（校招生 + 职场小白）的免费职位订阅推送工具。
> 订阅你关心的**职位名称 + 工作地点**，我们定时抓取企业公开职位，邮件推送到你的邮箱。
> **免费、开源、只推公开职位。**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![零依赖](https://img.shields.io/badge/dependencies-0-green)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

---

## ✨ 它能做什么

- 🔎 **按职位 + 地点订阅**：只想看「北京的设计岗」「上海的数据分析」，交给它定时抓。
- 📬 **邮件推送**：新岗位直接推到你邮箱（开发中，见 Roadmap）。
- 🏢 **只推公开职位**：数据来自企业/官方公开渠道，投递时引导你回原官网。
- 🆓 **免费 + 开源 + 零第三方依赖**：仅需 Python 3.9+，`git clone` 即可跑。

## 🗂 数据源策略

| 类型 | 来源 | 状态 |
|---|---|---|
| 官方源（主力） | 24365 国家大学生就业服务平台（ncss.cn） | ✅ 已跑通 |
| 外企补充 | Greenhouse ATS（Duolingo / Airbnb / Databricks / MongoDB / Flexport / Riot Games） | ✅ 已跑通 |
| 官方源（待接） | 国聘网（央企）、各省市高校就业网 | 🚧 待接 |
| 企业官网（待补） | 字节 / 腾讯 / 阿里 / 微软 / 华为等头部雇主官网 | 🚧 待补 |
| 商业平台 | 智联 / BOSS / 应届生（有反爬 + 合规灰色） | ❌ 不碰 |

## ⚖️ 合规声明

本项目只抓取**企业公开的职位信息**，并引导用户**回到原官网投递**，不替代任何平台。

三条红线，严格遵守：

1. **不碰求职者简历/个人信息**（遵守《个人信息保护法》）。
2. **不突破技术防护**（不绕验证码、登录墙、蜜罐、封禁）。
3. **不"实质性替代"原平台**（纯订阅导流，非二次售卖）。

抓取遵循礼貌原则：请求限频、真实 User-Agent、失败重试与退避。

## 🚀 快速开始

零第三方依赖，仅需 **Python 3.9+**：

```bash
git clone https://github.com/<your-username>/unifit100.git
cd unifit100

# 抓取 24365 北京地区职位并入库
python run_ncss.py

# 抓取指定关键词（如"设计"）
python run_ncss.py 设计

# 关键词 + 地区
python run_ncss.py 设计 --area 上海

# 抓取 Greenhouse 外企的中国大陆岗位
python run_greenhouse.py
```

运行后本地生成 `unifit100.db`（SQLite），重复抓取按 `(source, job_id)` 去重更新。

### 地区代码

`--area` 支持省级行政区（GB/T 2260 前两位），例如：

```
全国 北京 天津 上海 重庆 河北 山西 内蒙古 辽宁 吉林 黑龙江
江苏 浙江 安徽 福建 江西 山东 河南 湖北 湖南 广东 广西 海南
四川 贵州 云南 西藏 陕西 甘肃 青海 宁夏 新疆 香港 澳门 台湾
```

## 📁 目录结构

```
unifit100/
├── src/
│   ├── models.py              # 统一 Job 数据模型
│   ├── db.py                  # SQLite 存储层（unique(source,job_id) upsert）
│   └── adapters/
│       ├── base.py            # 适配器基类（限频 + 礼貌抓取 + 重试）
│       ├── ncss_24365.py      # 24365 官方平台适配器
│       └── greenhouse.py      # Greenhouse 外企适配器（筛中国大陆岗位）
├── run_ncss.py                # 入口：抓取 24365
├── run_greenhouse.py          # 入口：抓取 Greenhouse
├── prototype.png              # 前端订阅页原型图（开发中）
├── LICENSE                    # MIT
└── unifit100.db               # 本地 SQLite（运行后生成，已 gitignore）
```

## 🧾 数据字段

统一后的职位模型（`src/models.py`）：

| 字段 | 说明 |
|---|---|
| `source` / `job_id` | 数据源 + 源内唯一 ID，构成去重唯一键 |
| `title` / `company` / `location` | 职位 / 公司 / 工作地点 |
| `salary` / `education` / `job_type` | 薪资 / 学历 / 全职·实习 |
| `industry` / `company_nature` / `company_size` | 行业 / 公司性质 / 规模 |
| `publish_date` / `job_url` | 发布日期 / 回原官网投递链接 |
| `description` | 职位描述（纯文本） |

## 📈 当前进度

- [x] 24365 适配器（北京地区 100 条验证通过，分页抓取）
- [x] Greenhouse 适配器（6 个外企 board，105 条中国大陆岗位）
- [x] 统一数据模型 + SQLite 去重 upsert
- [ ] 推送去重（同一岗位多渠道转载，按 title+company 去重）
- [ ] 24365 全量分块抓取（按城市/关键词切分，枚举全部岗位）
- [ ] 订阅模型 + 邮件推送（阿里云 DirectMail）
- [ ] 前端订阅页（按 [prototype.png](prototype.png)）
- [ ] 国聘网 + 高校就业网适配器

## 🗺 Roadmap

1. **邮件订阅推送**：订阅关键词 + 地点 → 定时抓取 → 邮件送达。
2. **前端订阅页**：网页填写订阅，无需命令行。
3. **更多数据源**：国聘网（央企）、各省高校就业网。
4. **GitHub Actions 定时任务**：云端自动抓取，不依赖个人电脑。

## 💬 求职咨询

本项目由 **UniFit100 | Job Search** 团队维护，长期关注校招与初阶求职。

需要**简历辅导、面试辅导、职业规划**？欢迎访问：

👉 **<https://unifit100.com/consultant>**

如果你觉得这个工具有用，请点个 ⭐ Star，让更多同学看到 🙏

## 🤝 贡献

欢迎提交 PR 补充数据源适配器（继承 `src/adapters/base.py`）或修复失效接口。请遵守上方合规红线。

## 📄 License

[MIT](LICENSE) © 2026 UniFit100
