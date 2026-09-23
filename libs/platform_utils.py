#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
libs/platform_utils.py —— 跨平台小工具集
==============================================
提供：
  · set_windows_titlebar_dark(hwnd, dark) —— 底层：设置指定窗口的标题栏深浅
  · apply_titlebar_theme(window, is_dark) —— 高层：把窗口标题栏按主题设置（幂等）

设计说明：
  · 非 Windows 平台全部静默返回 False，不影响调用方
  · apply_titlebar_theme 内部维护 window._titlebar_dark_state 缓存，
    避免在 showEvent / switch_theme 等入口反复调用系统 API
  · 主题真正变化（light↔dark）时缓存自动失效并重新应用
  · 想强制重新应用时，传 force=True
"""

from __future__ import annotations

import sys
from typing import Any


__all__ = ["set_windows_titlebar_dark", "apply_titlebar_theme"]


# Windows DWMWA_USE_IMMERSIVE_DARK_MODE 属性号
#   20 是 Win10 20H1+ 的新值
#   19 是 Win10 1903 ~ 1909 的旧值
_DWMWA_USE_IMMERSIVE_DARK_MODE_NEW = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19


def set_windows_titlebar_dark(hwnd: int, dark: bool) -> None:
    """设置 Windows 窗口标题栏的深浅模式。

    Args:
        hwnd: 窗口句柄（int(window.winId())）
        dark: True = 深色标题栏；False = 浅色

    非 Windows 平台或调用失败时静默返回。
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        value = ctypes.c_int(1 if dark else 0)
        for attr in (_DWMWA_USE_IMMERSIVE_DARK_MODE_NEW,
                     _DWMWA_USE_IMMERSIVE_DARK_MODE_OLD):
            try:
                res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(int(hwnd)),
                    attr,
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                )
                if res == 0:
                    return
            except Exception:
                continue
    except Exception:
        pass


def apply_titlebar_theme(window: Any, is_dark: bool, *,
                         force: bool = False) -> bool:
    """把窗口的标题栏主题设置为浅色/深色（幂等）。

    内部用 window._titlebar_dark_state 缓存上次已应用的状态，
    只有状态变化（或 force=True）才会真正调用系统 API。

    Args:
        window:  任意 QWidget / QDialog / QMainWindow
        is_dark: True 表示深色标题栏
        force:   跳过缓存，强制重新应用

    Returns:
        True  —— 本次真正调用了系统 API
        False —— 平台不支持 / 状态未变 / 调用失败
    """
    if sys.platform != "win32":
        return False

    prev = getattr(window, "_titlebar_dark_state", None)
    if not force and prev == is_dark:
        return False

    try:
        hwnd = int(window.winId())
    except Exception:
        return False

    set_windows_titlebar_dark(hwnd, is_dark)

    # 无论系统 API 是否成功都记录状态，避免反复失败重试
    try:
        window._titlebar_dark_state = is_dark
    except Exception:
        pass
    return True