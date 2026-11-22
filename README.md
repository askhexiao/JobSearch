# UniFit100 | Job Search — 免费职位订阅工具

> 面向初阶求职者（校招生 + 职场小白）的免费职位订阅推送工具。
> 订阅你关心的**职位名称 + 工作地点**，定时抓取企业公开职位，邮件推送到你的邮箱。
> **免费、开源、只推公开职位、只覆盖中国大陆。**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![零依赖](https://img.shields.io/badge/dependencies-0-green)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

---

## ✨ 它能做什么

- 🔎 **按职位 + 地点订阅**：职位名称最多 3 个、工作地点最多 4 个（或选「不限」）。
- 📬 **邮件推送**：定时抓取，**新岗位**自动推到你邮箱（阿里云 DirectMail）。
- 🖥 **网页订阅页**：填表即订阅，无需命令行。
- 🏢 **只推公开职位**：数据来自企业/官方公开渠道，投递时引导你回原官网。
- 🇨🇳 **只覆盖中国大陆**：自动排除港澳台岗位。
- 🆓 **免费 + 开源 + 零第三方依赖**：仅需 Python 3.9+。

## 🗂 数据源策略

| 类型 | 来源 | 状态 |
|---|---|---|
| 官方源（主力） | 24365 国家大学生就业服务平台（ncss.cn） | ✅ 已跑通 |
| 央企/国企 | 国聘网（iguopin.com） | ✅ 已跑通 |
| 外企补充 | Greenhouse ATS（Duolingo / Airbnb / Databricks / MongoDB / Flexport / Riot Games） | ✅ 已跑通 |
| 官方源（待接） | 各省市高校就业网 | 🚧 待接 |
| 企业官网（待补） | 字节 / 腾讯 / 阿里 / 微软 / 华为等头部雇主官网 | 🚧 待补 |
| 商业平台 | 智联 / BOSS / 应届生（有反爬 + 合规灰色） | ❌ 不碰 |

## ⚖️ 合规声明

本项目只抓取**企业公开的职位信息**，并引导用户**回到原官网投递**，不替代任何平台。

三条红线，严格遵守：

1. **不碰求职者简历/个人信息**（遵守《个人信息保护法》）。
2. **不突破技术防护**（不绕验证码、登录墙、蜜罐、封禁）。
3. **不"实质性替代"原平台**（纯订阅导流，非二次售卖）。

抓取遵循礼貌原则：请求限频、真实 User-Agent、失败重试与退避。

**完整合规说明（robots.txt 现状、个人信息处理、退订、内容版权、免责声明）见 [COMPLIANCE.md](COMPLIANCE.md)。**

> 🔒 本项目唯一收集的个人信息是**订阅邮箱**，仅用于职位推送；用户可**随时退订**，退订即删除。不抓取、不存储任何简历 / 姓名 / 电话等个人信息。

## 🚀 快速开始

零第三方依赖，仅需 **Python 3.9+**：

```bash
git clone https://github.com/<your-username>/unifit100.git
cd unifit100

# ① 抓取职位并入库（可单独运行）
python run_ncss.py                 # 24365 北京地区职位
python run_ncss.py 设计            # 指定关键词
python run_ncss.py 设计 --area 上海
python run_greenhouse.py           # 外企中国大陆岗位
python run_iguopin.py              # 国聘网央企/国企岗位

# ② 启动网页订阅页
python web_server.py               # 打开 http://127.0.0.1:8000 填表订阅
```

## 📬 订阅与邮件推送

### 工作流

1. 用户在订阅页填写：**邮箱 + 职位名称（≤5）+ 招聘类型 + 工作地点（省-市，≤5，或「不限」）+ 推送频率 + 岗位发布时长**。
2. 运行推送脚本，抓取匹配岗位 → 与历史推送去重 → **只发新岗位**。

```bash
python run_push.py --dry-run       # 先预览：抓取+匹配+去重，但不发信
cp config.example.json config.json # 填 SMTP 凭证
python run_push.py                 # 真实发送
```

建议用 `cron` / GitHub Actions 定时执行 `run_push.py`。

### 阿里云 DirectMail 配置

1. 阿里云控制台 →「邮件推送（DirectMail）」→ **发信域名**：新增并验证你的域名。
2. **发信地址**：基于已验证域名创建，如 `noreply@your-domain.com`。
3. 在该地址上**生成 SMTP 密码**（只显示一次）。
4. 填入 `config.json`（已 gitignore，**勿提交**）：

```json
{
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

> 当前邮件为**纯文本**；HTML 品牌模板（套用 `brand/` 的 logo 与字体）在 Roadmap 中。

## 📁 目录结构

```
unifit100/
├── src/
│   ├── models.py              # 统一 Job 数据模型
│   ├── db.py                  # SQLite 职位存储（unique(source,job_id) upsert）
│   ├── locations.py           # 省份码 + 城市中英文映射 + 地点匹配
│   ├── normalize.py           # 字段归一化（学历/公司性质/招聘类型）
│   ├── subscription.py        # 订阅模型 + 存储 + 匹配 + 校验
│   ├── mailer.py              # SMTP 邮件（阿里云 DirectMail）
│   └── adapters/
│       ├── base.py            # 适配器基类（限频 + 礼貌抓取 + 重试）
│       ├── ncss_24365.py      # 24365 官方平台适配器
│       ├── greenhouse.py      # Greenhouse 外企适配器（筛中国大陆）
│       └── iguopin.py         # 国聘网适配器（央企/国企）
├── web/
│   ├── index.html             # 订阅页
│   ├── style.css              # 样式
│   ├── app.js                 # 表单交互 + 校验
│   └── pca.json               # 省-市行政区划数据
├── brand/
│   ├── logo.png               # 品牌主 Logo
│   └── logo_app.png           # App 图标
├── run_ncss.py                # 入口：抓取 24365
├── run_greenhouse.py          # 入口：抓取 Greenhouse
├── run_iguopin.py             # 入口：抓取国聘网
├── run_push.py                # 入口：匹配订阅 + 邮件推送
├── web_server.py              # 入口：订阅页 HTTP 服务
├── config.example.json        # SMTP 配置模板
├── prototype.png              # 前端订阅页原型图（参考）
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
| `education` / `education_level` | 学历展示 / 枚举（专科/本科/硕士/博士） |
| `recruit_type` / `job_type` | 校招·社招·实习 / 实习·全职 |
| `company_nature` / `company_size` / `industry` | 国企·民企·外企·事业单位 / 规模 / 行业 |
| `publish_date` / `job_url` | 发布日期 / 回原官网投递链接 |
| `description` | 职位描述（纯文本） |

## ⚠️ 已知限制

- **24365 地点粒度**：除直辖市外，官方接口仅返回**省级**地点（如「广东」），暂无法细分到「深圳」。城市级抓取在 Roadmap 中。
- **职位名中英文不互通**：中文关键词（如「数据分析」）能命中 24365 中文职位，但匹配不到外企英文标题（如 "Data Analyst"）。中英职位词典在 Roadmap 中。

## 📈 当前进度

- [x] 24365 适配器（分页抓取，北京地区 100 条验证通过）
- [x] Greenhouse 适配器（6 个外企 board，105 条中国大陆岗位）
- [x] 国聘网适配器（200 条，央企/国企 71.5%，城市级地点 + 校招/社招）
- [x] 统一数据模型 + 字段标准化（薪资/地点/学历/招聘类型/公司性质）
- [x] SQLite 去重（同源 unique + 跨源 title+company+city）
- [x] 订阅模型（职位 ≤5、地点 ≤5 / 不限、招聘类型、推送频率、发布时长）
- [x] 前端订阅页（省-市联动 + 校验 + 品牌样式）
- [x] 邮件推送（阿里云 DirectMail SMTP，纯文本，含 --dry-run）
- [x] 中国大陆过滤（排除港澳台）
- [ ] 24365 城市级 / 全量分块抓取
- [ ] HTML 邮件模板（套用品牌 logo 与字体）
- [ ] 中英职位名词典（打通中外职位匹配）
- [ ] 各省高校就业网适配器
- [ ] GitHub Actions 定时任务

## 🗺 Roadmap

1. **HTML 邮件模板**：套用 `brand/` 的 logo + 字体，做品牌化邮件。
2. **城市级抓取**：24365 细化到城市维度，全量分块抓取。
3. **中英职位词典**：打通中文职位名 ↔ 外企英文职位标题。
4. **更多数据源**：各省高校就业网、头部雇主官网。
5. **GitHub Actions**：云端定时抓取 + 推送，不依赖个人电脑。

## 💬 求职咨询

本项目由 **UniFit100 | Job Search** 团队维护，长期关注校招与初阶求职。

需要**简历辅导、面试辅导、职业规划**？欢迎访问：

👉 **<https://unifit100.com/consultant>**

如果你觉得这个工具有用，请点个 ⭐ Star，让更多同学看到 🙏

## 🤝 贡献

欢迎提交 PR 补充数据源适配器（继承 `src/adapters/base.py`）或修复失效接口。请遵守上方合规红线。

## 📄 License

[MIT](LICENSE) © 2026 UniFit100
