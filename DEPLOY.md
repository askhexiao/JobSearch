# 部署指南（阿里云）

本文档说明如何把 **UniFit100 | Job Search** 部署到阿里云并对外提供服务。

## 架构

```
用户浏览器
   │  HTTPS
   ▼
Nginx（80/443，unifit100.com/jobs）
   │  反向代理（保留 /jobs 前缀）
   ▼
web_server.py（127.0.0.1:8000，--base-path /jobs，systemd 守护）
   │
   ├─ web/ 静态页面（订阅页 + 管理页）
   ├─ unifit100.db（SQLite）
   └─ config.json（SMTP 凭证，git 忽略）

定时任务（cron）
   ├─ 每天 10:00   run_push.py --frequency 每天1次
   ├─ 每周三 10:00 run_push.py --frequency 每周1次
   └─ 每天 08:00   run_scrape.py（抓取入库）
```

## 前提

- 阿里云 ECS 或**轻量应用服务器**（2C2G 起步即可，本工具零依赖、极轻量）。
- 系统建议 **Ubuntu 22.04**（自带 Python 3）。
- 域名已**ICP 备案**（大陆服务器硬性要求；`unifit100.com` 已上线，说明备案已完成，子域名自动覆盖，无需重新备案）。
- 能 SSH 登录服务器。

## 一、准备服务器

1. 购买后记录**公网 IP**。
2. 控制台 → 安全组：放行 **80（HTTP）**、**443（HTTPS）**、**22（SSH）**。
3. SSH 登录：
   ```bash
   ssh root@<服务器IP>
   ```
4. 确认 Python 版本（需 3.9+）：
   ```bash
   python3 --version
   ```

## 二、域名与备案

1. 用**子路径**部署：`unifit100.com/jobs`（同域名，无需额外备案，也无需新增 DNS 解析）。
2. `unifit100.com` 已上线，只需在**现有 Nginx** 里新增一个 `/jobs/` location。

## 三、上传代码

**方式 A：scp 上传（当前即可用）**
```bash
# 本地执行
scp -r JobSearch/ root@<服务器IP>:/opt/unifit100/
```

**方式 B：git clone（发布到 GitHub 后）**
```bash
# 服务器执行
cd /opt
git clone https://github.com/askhexiao/JobSearch.git unifit100
```

## 四、配置

```bash
cd /opt/unifit100/JobSearch
cp config.example.json config.json
chmod 600 config.json          # 含 SMTP 密码，收紧权限
vim config.json
```

`config.json` 需填写：

```json
{
  "smtp_host": "smtpdm.aliyun.com",
  "smtp_port": 465,
  "smtp_user": "jobs@notify.unifit100.com",
  "smtp_password": "你的SMTP密码",
  "sender": "jobs@notify.unifit100.com",
  "web_base_url": "https://unifit100.com/jobs"
}
```

> `web_base_url` 用于邮件里「管理订阅」链接，部署后务必改成正式域名。

## 五、运行服务（systemd 守护）

创建 `/etc/systemd/system/unifit100.service`：

```ini
[Unit]
Description=UniFit100 Job Search
After=network.target

[Service]
WorkingDirectory=/opt/unifit100/JobSearch
ExecStart=/usr/bin/python3 web_server.py --host 127.0.0.1 --port 8000 --base-path /jobs
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动并设为开机自启：

```bash
systemctl daemon-reload
systemctl enable --now unifit100
systemctl status unifit100   # 看到 active (running) 即成功
```

## 六、Nginx 反向代理 + HTTPS

`unifit100.com` 已有 Nginx 配置（咨询页），只需在其 `server` 块内**新增**一个 location：

```nginx
# 加入 unifit100.com 的现有 server 块内（listen 443 ssl 的那个）
location /jobs/ {
    proxy_pass http://127.0.0.1:8000;   # 无尾斜杠，保留 /jobs 前缀
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

重载：

```bash
nginx -t && systemctl reload nginx
```

> 若 `unifit100.com` 的 HTTPS 证书已就绪，`/jobs` 自动复用同一证书，无需再签。若无 HTTPS，先在阿里云申请免费 SSL 证书配到现有 server 块。

## 七、定时任务（cron）

```bash
crontab -e
```

```cron
# 每天 08:00 抓取（给 10:00 推送留出时间）
0 8 * * * cd /opt/unifit100/JobSearch && /usr/bin/python3 run_scrape.py >> /var/log/unifit100.log 2>&1

# 每天 10:00 推送「每天1次」订阅
0 10 * * * cd /opt/unifit100/JobSearch && /usr/bin/python3 run_push.py --frequency 每天1次 >> /var/log/unifit100.log 2>&1

# 每周三 10:00 推送「每周1次」订阅
0 10 * * 3 cd /opt/unifit100/JobSearch && /usr/bin/python3 run_push.py --frequency 每周1次 >> /var/log/unifit100.log 2>&1
```

## 八、首次抓取入库

部署后先手动跑一次全量抓取，把职位库建立起来：

```bash
cd /opt/unifit100/JobSearch
nohup python3 run_scrape.py > /tmp/scrape.log 2>&1 &
```

> 全量抓取耗时较长（约 2~3 小时）且会触发数据源限流。**首次跑一次即可**；之后每天 cron 的抓取建议改为增量（见「后续优化」）。

## 九、验证

1. 浏览器访问 `https://unifit100.com/jobs/` → 应显示订阅页。
2. 提交订阅 → 应立即收到一封邮件（即时首封推送）。
3. 点邮件底部「管理订阅」→ 能打开管理页、能修改、能退订。
4. `https://unifit100.com/jobs/manage?email=xxx` 直接进入管理页。

## 注意事项

- **config.json 绝不上传 Git**（含 SMTP 密码），已在 `.gitignore`。
- **数据备份**：`unifit100.db` 定期备份（例如每天 `cp unifit100.db unifit100.db.bak`）。
- **日志**：`/var/log/unifit100.log` 观察抓取/推送是否正常。
- **安全组**：只需对外开 80/443，**8000 端口不要对外**（只让 Nginx 本机反代）。

## 后续优化（建议）

1. **增量抓取**：`run_scrape.py` 目前是全量（慢、易限流），生产建议改为「每天增量拉取最近 N 天」，把全量只作为首次初始化。
2. **GitHub Actions 定时**：也可用 GitHub Actions 替代服务器 cron（需先发布到 GitHub）。
3. **监控告警**：抓取/推送失败时邮件或短信告警。
