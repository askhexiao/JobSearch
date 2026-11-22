# -*- coding: utf-8 -*-
"""SMTP 纯文本邮件发送（阿里云 DirectMail）。

零第三方依赖，用标准库 smtplib + email。
SMTP 服务器默认 smtpdm.aliyun.com:465（SSL）。
"""
from __future__ import annotations

import smtplib
import ssl
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

DEFAULT_SMTP_HOST = "smtpdm.aliyun.com"
DEFAULT_SMTP_PORT = 465


class Mailer:
    def __init__(self, config: dict):
        smtp = config.get("smtp", {}) if config else {}
        self.host = smtp.get("host", DEFAULT_SMTP_HOST)
        self.port = int(smtp.get("port", DEFAULT_SMTP_PORT))
        self.use_ssl = bool(smtp.get("ssl", True))
        self.username = smtp.get("username", "")
        self.password = smtp.get("password", "")
        self.from_name = smtp.get("from_name", "UniFit100")
        self.from_addr = smtp.get("from_addr", self.username)

    @property
    def configured(self) -> bool:
        return bool(self.username and self.password)

    def send(self, to: str, subject: str, text_body: str) -> None:
        if not self.configured:
            raise RuntimeError("SMTP 未配置（缺少 username/password）")

        msg = MIMEText(text_body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((str(Header(self.from_name, "utf-8")), self.from_addr))
        msg["To"] = to

        context = ssl.create_default_context()
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=30)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.starttls(context=context)
        try:
            server.login(self.username, self.password)
            server.sendmail(self.from_addr, [to], msg.as_string())
        finally:
            try:
                server.quit()
            except Exception:
                pass
