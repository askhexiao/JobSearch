# -*- coding: utf-8 -*-
"""适配器基类：礼貌抓取。

内置限频（两次请求最小间隔）、超时、重试、真实 User-Agent。
所有适配器只需实现 fetch() 并返回 list[Job]。
"""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 UniFit100-JobSearch/1.0"
)


class FetchError(RuntimeError):
    """网络请求失败。"""


class BaseAdapter:
    name = "base"

    def __init__(
        self,
        min_interval: float = 1.0,
        timeout: float = 20.0,
        max_retries: int = 3,
        user_agent: str = DEFAULT_UA,
    ):
        self.min_interval = min_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        """礼貌抓取：确保两次请求之间至少间隔 min_interval 秒。"""
        wait = self.min_interval - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def get_json(self, url: str, referer: str = None) -> dict:
        """GET 一个 JSON 接口，带重试与指数退避。"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
        }
        if referer:
            headers["Referer"] = referer

        last_err = None
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    return json.loads(body)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
                last_err = exc
                time.sleep(1.0 * (attempt + 1))
        raise FetchError(f"请求失败（已重试 {self.max_retries} 次）: {url} -> {last_err}")

    def post_json(self, url: str, payload: dict, referer: str = None) -> dict:
        """POST 一个 JSON 接口，带重试与指数退避。"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        }
        if referer:
            headers["Referer"] = referer

        last_err = None
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="replace"))
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
                last_err = exc
                time.sleep(1.0 * (attempt + 1))
        raise FetchError(f"请求失败（已重试 {self.max_retries} 次）: {url} -> {last_err}")

    def fetch(self):
        raise NotImplementedError
