#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/smtp_config.py —— SMTP 配置管理（作者端专用）
========================================================
保存到 tools/smtp_config.json（已在 .gitignore 中排除）
支持 QQ / 163 / Gmail / 企业邮箱
"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "smtp_config.json"


DEFAULTS = {
    "server":      "smtp.qq.com",
    "port":        465,
    "use_ssl":     True,
    "user":        "",
    "password":    "",       # QQ/163 需用「授权码」，不是登录密码
    "sender_name": "得鹿梦鱼",
}


PRESETS = {
    "QQ 邮箱":     {"server": "smtp.qq.com",      "port": 465, "use_ssl": True},
    "163 邮箱":    {"server": "smtp.163.com",     "port": 465, "use_ssl": True},
    "126 邮箱":    {"server": "smtp.126.com",     "port": 465, "use_ssl": True},
    "Gmail":      {"server": "smtp.gmail.com",   "port": 465, "use_ssl": True},
    "Outlook":    {"server": "smtp.office365.com","port": 587, "use_ssl": False},
    "自定义":      {"server": "",                 "port": 465, "use_ssl": True},
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.is_file():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[SMTP] 保存失败: {e}")


def is_configured(cfg: dict = None) -> bool:
    cfg = cfg or load_config()
    return bool(cfg.get("server") and cfg.get("user") and cfg.get("password"))


# ------------------------------------------------------------------
# 邮件发送
# ------------------------------------------------------------------
def send_email(cfg: dict, to_addr: str, subject: str,
               body: str, timeout: float = 15.0) -> tuple[bool, str]:
    """
    发送邮件。

    Returns:
        (True, "OK") 或 (False, "错误原因")
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header
    from email.utils import formataddr

    if not is_configured(cfg):
        return False, "SMTP 未配置完整（缺服务器/用户名/密码）"

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        sender_name = cfg.get("sender_name", "") or ""
        msg["From"] = formataddr((str(Header(sender_name, "utf-8")),
                                   cfg["user"]))
        msg["To"] = to_addr

        host = cfg["server"]
        port = int(cfg.get("port", 465))
        use_ssl = bool(cfg.get("use_ssl", True))

        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                smtp.login(cfg["user"], cfg["password"])
                smtp.sendmail(cfg["user"], [to_addr], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(cfg["user"], cfg["password"])
                smtp.sendmail(cfg["user"], [to_addr], msg.as_string())

        return True, "OK"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"认证失败（检查授权码/用户名）：{e}"
    except smtplib.SMTPException as e:
        return False, f"SMTP 错误：{e}"
    except Exception as e:
        return False, f"发送失败：{e}"


def test_connection(cfg: dict, timeout: float = 8.0) -> tuple[bool, str]:
    """测试 SMTP 连接（不发送邮件）。"""
    import smtplib
    if not is_configured(cfg):
        return False, "SMTP 未配置完整"

    host = cfg["server"]
    port = int(cfg.get("port", 465))
    use_ssl = bool(cfg.get("use_ssl", True))

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                smtp.login(cfg["user"], cfg["password"])
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(cfg["user"], cfg["password"])
        return True, "连接正常"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"认证失败：{e}"
    except Exception as e:
        return False, f"连接失败：{e}"