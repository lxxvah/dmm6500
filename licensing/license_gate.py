#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing/license_gate.py —— 一行式授权闸门
=================================================
用法：
    from licensing import ensure_licensed
    if not ensure_licensed():
        sys.exit(0)
"""

from __future__ import annotations

import os
import sys


def ensure_licensed(parent=None, app_title: str = None) -> bool:
    """
    检查授权。通过 → True；未通过 → 弹对话框后返回 False。

    Args:
        parent:     父窗口（可选）
        app_title:  应用显示名（覆盖 config.APP_NAME，可选）

    Returns:
        True  —— 已授权 / 试用中 / 用户激活成功
        False —— 未授权且用户未激活
    """
    # 开发者跳过
    if os.environ.get("LICENSE_DEV") == "1":
        print("[licensing] LICENSE_DEV=1，跳过授权校验")
        return True

    try:
        from .config import APP_NAME, APP_ID
        from .client import check_access, LicenseResult
    except Exception as e:
        print(f"[licensing] 初始化失败: {e}")
        return _show_error(
            parent,
            "授权模块加载失败",
            f"{e}\n\n请确认 licensing/ 文件夹完整。"
        )

    # 1) 检查
    try:
        status, info = check_access()
    except Exception as e:
        return _show_error(
            parent, "授权校验失败", f"校验过程出错：\n\n{e}"
        )

    # 2) 通过
    if status == LicenseResult.OK:
        t = info.get("type", "license")
        if t == "license":
            licensee = info.get("licensee", "匿名")
            expire = info.get("expire", "永久")
            print(f"[licensing] ✅ 已授权给 {licensee}（有效期：{expire}）")
        elif t == "trial":
            days = info.get("days_remaining", "?")
            print(f"[licensing] ✅ 试用中（剩余 {days} 天）")
        return True

    # 3) 未通过 → 弹对话框
    try:
        from .dialog import LicenseDialog
        from PyQt6.QtWidgets import QDialog
    except Exception as e:
        return _show_error(
            parent, "授权对话框加载失败", str(e)
        )

    title = app_title or APP_NAME
    dlg = LicenseDialog(status, info, parent=parent)
    dlg.setWindowTitle(f"{title} · 授权")
    ok = dlg.exec() == QDialog.DialogCode.Accepted

    if ok:
        # 再验一遍
        try:
            st2, info2 = check_access()
            if st2 == LicenseResult.OK:
                print(f"[licensing] ✅ 授权成功")
                return True
        except Exception:
            pass

    print("[licensing] ❌ 未通过授权")
    return False


def _show_error(parent, title: str, message: str) -> bool:
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, title, message)
    except Exception:
        print(f"[licensing] {title}: {message}")
    return False