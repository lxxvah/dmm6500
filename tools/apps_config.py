#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/apps_config.py —— 应用列表配置（作者端专用）
=========================================================
管理"这个签发工具服务于哪些软件"，保存到 exe 同目录的 apps_config.json。

每个应用字段：
    id            内部唯一标识（英文，勿改，用于校验）
    name          应用显示名（中文即可）
    key_prefix    密钥字符串前缀（客户端必须一致）
    contact_email 联系方式（用于邮件正文/申请对话框）
    contact_extra 附加联系方式（如微信号，可留空）

打包后从 exe 同级目录读写；未打包时从本文件目录读写。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional


# ============================================================
# 路径解析（兼容 PyInstaller 打包）
# ============================================================
def _app_dir() -> Path:
    """exe 打包后返回 exe 所在目录；未打包返回本文件目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = _app_dir() / "apps_config.json"


# ============================================================
# 默认配置
# ============================================================
def default_config() -> dict:
    return {
        "current_app": "dmm6500",
        "apps": [
            {
                "id": "dmm6500",
                "name": "DMM6500 综合监控台",
                "key_prefix": "DMM6500-",
                "contact_email": "your@email.com",
                "contact_extra": "微信 / QQ：得鹿梦鱼",
            },
        ],
    }


# ============================================================
# 读 / 写
# ============================================================
def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        cfg = default_config()
        save_config(cfg)
        return cfg

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = default_config()

    # 补齐字段
    if "apps" not in cfg or not isinstance(cfg["apps"], list):
        cfg["apps"] = default_config()["apps"]
    if "current_app" not in cfg:
        cfg["current_app"] = cfg["apps"][0]["id"] if cfg["apps"] else "dmm6500"

    # 保证每个应用都有必需的键
    required = ("id", "name", "key_prefix", "contact_email", "contact_extra")
    for app in cfg["apps"]:
        for k in required:
            app.setdefault(k, "")

    return cfg


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[apps_config] 保存失败: {e}")


# ============================================================
# 便捷访问
# ============================================================
def get_current_app(cfg: dict) -> dict:
    cur_id = cfg.get("current_app", "")
    for app in cfg.get("apps", []):
        if app.get("id") == cur_id:
            return app
    apps = cfg.get("apps", [])
    return apps[0] if apps else default_config()["apps"][0]


def set_current_app(cfg: dict, app_id: str) -> None:
    cfg["current_app"] = app_id
    save_config(cfg)


def list_app_names(cfg: dict) -> list:
    return [a.get("name", a.get("id", "未命名")) for a in cfg.get("apps", [])]


def find_by_name(cfg: dict, name: str) -> Optional[dict]:
    for app in cfg.get("apps", []):
        if app.get("name") == name:
            return app
    return None