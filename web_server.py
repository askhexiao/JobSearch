# -*- coding: utf-8 -*-
"""零依赖 HTTP 服务：订阅页 + 订阅接口。

用法:
    python web_server.py            # 默认 http://127.0.0.1:8000
    python web_server.py --port 8000
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.db import JobStore
from src.locations import LOCATION_CHOICES
from src.mailer import Mailer
from src.pusher import push_subscription
from src.subscription import SubscriptionStore, validate_subscription

WEB_DIR = ROOT / "web"
BRAND_DIR = ROOT / "brand"
DB_PATH = ROOT / "unifit100.db"
CONFIG_PATH = ROOT / "config.json"

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".woff2": "font/woff2",
}


def _load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


class Handler(BaseHTTPRequestHandler):
    server_version = "UniFit100/1.0"
    BASE_PATH = ""  # 部署子路径（如 "/jobs"）；本地开发为空

    def _rel(self, path: str) -> str | None:
        """去掉 base 前缀；不在 base 下返回 None。"""
        if not self.BASE_PATH:
            return path
        if path == self.BASE_PATH:
            return "/"
        if path.startswith(self.BASE_PATH + "/"):
            return path[len(self.BASE_PATH):]
        return None

    def _home(self) -> str:
        return (self.BASE_PATH + "/") if self.BASE_PATH else "/"

    def _serve_index(self) -> None:
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        html = html.replace("__BASE_HREF__", self._home())
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    # ---------- 响应工具 ----------
    def _send(self, status: int, body: bytes, ctype: str, cache: str = "no-store") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json({"error": "not found"}, 404)
            return
        ctype = _MIME.get(path.suffix.lower(), "application/octet-stream")
        # 静态资源可缓存（CSS/JS/字体/图片），避免每次刷新重下 3.69MB 字体
        self._send(200, path.read_bytes(), ctype, cache="public, max-age=86400")

    def _handle_get_subscription(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        email = (query.get("email") or [""])[0].strip().lower()
        if not email:
            self._send_json({"error": "缺少 email 参数"}, 400)
            return
        store = SubscriptionStore(DB_PATH)
        sub = store.get(email)
        store.close()
        if sub is None:
            self._send_json({"error": "未找到该订阅"}, 404)
            return
        self._send_json({
            "email": sub.email,
            "titles": sub.titles,
            "locations": sub.locations,
            "location_unlimited": sub.location_unlimited,
            "recruit_type": sub.recruit_type,
            "employer_db": sub.employer_db,
            "frequency": sub.frequency,
            "publish_within": sub.publish_within,
            "unsubscribed_at": sub.unsubscribed_at,
        })

    def _handle_unsubscribe(self) -> None:
        """退订：软删除（标记退订时间），保留订阅记录与已发送历史。"""
        query = parse_qs(urlparse(self.path).query)
        email = (query.get("email") or [""])[0].strip().lower()
        if not email:
            self._send_json({"error": "缺少 email 参数"}, 400)
            return
        store = SubscriptionStore(DB_PATH)
        sub = store.get(email)
        if sub is None:
            msg = "未找到该订阅。"
        elif sub.unsubscribed_at:
            msg = "你已退订，无需重复操作。"
        else:
            store.unsubscribe(email)
            msg = "已退订，将不再收到推送。"
        store.close()
        home = self._home()
        html = (
            "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>UniFit100 退订</title></head>"
            "<body style='font-family:-apple-system,PingFang SC,sans-serif;max-width:480px;"
            "margin:60px auto;text-align:center;color:#1f2937'>"
            "<h2 style='color:#1a3c6e'>UniFit100 | Job Search</h2>"
            f"<p>{msg}</p>"
            f"<p><a href='{home}' style='color:#2f6fb0'>返回订阅页</a></p>"
            "</body></html>"
        )
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    # ---------- GET ----------
    def do_GET(self) -> None:
        path = self._rel(urlparse(self.path).path)
        if path is None:
            self._send_json({"error": "not found"}, 404)
            return
        if path in ("/", "/index.html", "/manage"):
            self._serve_index()
        elif path == "/logo.png":
            self._send_file(BRAND_DIR / "logo.png")
        elif path == "/api/locations":
            self._send_json({"locations": LOCATION_CHOICES})
        elif path == "/api/subscription":
            self._handle_get_subscription()
        elif path == "/unsubscribe":
            self._handle_unsubscribe()
        elif path.startswith("/static/"):
            # 仅允许 web/ 目录内的静态资源，防目录穿越。
            rel = path[len("/static/"):]
            target = (WEB_DIR / rel).resolve()
            if WEB_DIR.resolve() in target.parents or target.parent == WEB_DIR.resolve():
                self._send_file(target)
            else:
                self._send_json({"error": "forbidden"}, 403)
        else:
            self._send_json({"error": "not found"}, 404)

    # ---------- POST ----------
    def do_POST(self) -> None:
        path = self._rel(urlparse(self.path).path)
        if path is None:
            self._send_json({"error": "not found"}, 404)
            return
        if path != "/api/subscribe":
            self._send_json({"error": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, ValueError):
            self._send_json({"ok": False, "error": "请求体不是有效 JSON"}, 400)
            return

        sub, err = validate_subscription(payload)
        if err:
            self._send_json({"ok": False, "error": err}, 400)
            return

        store = SubscriptionStore(DB_PATH)
        mode = (payload.get("mode") or "subscribe").strip()

        # 首次订阅时，若邮箱已订阅（且活跃）则拦截，避免重复订阅
        existing = store.get(sub.email)
        if mode != "update" and existing is not None and not existing.unsubscribed_at:
            store.close()
            self._send_json({"ok": True, "message": "检测到您的邮箱已订阅，无需重复操作哦"})
            return

        store.upsert(sub)

        # 即时推送首封（已配置 SMTP 时）
        try:
            config = _load_config()
            mailer = Mailer(config)
            if mailer.configured:
                pool = JobStore(DB_PATH).all_jobs()
                base = (config or {}).get("web_base_url", "http://127.0.0.1:8000")
                push_subscription(sub, pool, mailer, store, base, dry_run=False)
        except Exception as exc:
            sys.stderr.write(f"[web] 即时推送失败：{exc}\n")

        store.close()
        message = "订阅信息已更新！" if mode == "update" else "订阅成功！即将为您推送职位"
        self._send_json({"ok": True, "message": message})

    def log_message(self, fmt, *args):  # 精简日志
        sys.stderr.write("[web] %s\n" % (fmt % args))


def main() -> int:
    parser = argparse.ArgumentParser(description="UniFit100 订阅页服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--base-path", default="", help="部署子路径，如 /jobs")
    args = parser.parse_args()

    base = args.base_path.strip()
    if base and not base.startswith("/"):
        base = "/" + base
    base = base.rstrip("/")
    Handler.BASE_PATH = base

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}{base}"
    print(f"UniFit100 订阅页已启动：{url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
