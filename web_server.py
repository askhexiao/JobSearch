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

from src.locations import LOCATION_CHOICES
from src.subscription import SubscriptionStore, validate_subscription

WEB_DIR = ROOT / "web"
BRAND_DIR = ROOT / "brand"
DB_PATH = ROOT / "unifit100.db"

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "UniFit100/1.0"

    # ---------- 响应工具 ----------
    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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
        self._send(200, path.read_bytes(), ctype)

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
        html = (
            "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>UniFit100 退订</title></head>"
            "<body style='font-family:-apple-system,PingFang SC,sans-serif;max-width:480px;"
            "margin:60px auto;text-align:center;color:#1f2937'>"
            "<h2 style='color:#1a3c6e'>UniFit100 | Job Search</h2>"
            f"<p>{msg}</p>"
            "<p><a href='/' style='color:#2f6fb0'>返回订阅页</a></p>"
            "</body></html>"
        )
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    # ---------- GET ----------
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_file(WEB_DIR / "index.html")
        elif path == "/logo.png":
            self._send_file(BRAND_DIR / "logo.png")
        elif path == "/api/locations":
            self._send_json({"locations": LOCATION_CHOICES})
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
        path = urlparse(self.path).path
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
        store.upsert(sub)
        store.close()
        self._send_json({"ok": True, "message": "订阅成功！新岗位将邮件推送给你。"})

    def log_message(self, fmt, *args):  # 精简日志
        sys.stderr.write("[web] %s\n" % (fmt % args))


def main() -> int:
    parser = argparse.ArgumentParser(description="UniFit100 订阅页服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"UniFit100 订阅页已启动：http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
