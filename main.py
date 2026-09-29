#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py —— 程序入口
=====================
职责：
  · 创建 QApplication
  · 授权校验（licensing 模块）
  · 创建主窗口 DMM6500Monitor
  · 全局快捷键 Ctrl+T 循环切换主题
  · 图标由 libs/DMM6500app_icon.py 管理（跟随主题）
  · 机械表色板桥接（libs/analog_gauge_qt.py 跟随主题）

命令行参数：
  --dark              使用深色主题启动
  --theme <name>      指定启动主题
  --show-license      打印本机机器码后退出
"""

import sys
import argparse

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

from theme import Theme, THEME_CYCLE
from ui.monitor_window import DMM6500Monitor

# 图标模块（Pillow 缺失时优雅降级）
try:
    from libs.DMM6500app_icon import get_icon_manager
    HAS_APP_ICON = True
except Exception as _e:
    print(f"[图标] 模块加载失败: {_e}")
    get_icon_manager = None
    HAS_APP_ICON = False

# 机械表色板桥接（失败时优雅降级，不影响主功能）
try:
    from libs.analog_gauge_qt import (
        ThemeManager as GaugeThemeManager,
        palette_from_theme,
    )
    HAS_GAUGE = True
except Exception as _e:
    print(f"[机械表] 模块加载失败: {_e}")
    GaugeThemeManager = None
    palette_from_theme = None
    HAS_GAUGE = False


def parse_args():
    parser = argparse.ArgumentParser(description="DMM6500 监控台")
    parser.add_argument("--dark", action="store_true",
                        help="使用深色主题启动")
    parser.add_argument("--theme", type=str, default=None,
                        choices=THEME_CYCLE,
                        help="指定启动主题")
    parser.add_argument("--show-license", action="store_true",
                        help="打印本机机器码后退出")
    return parser.parse_args()


def main():
    args = parse_args()

    # --show-license：仅打印机器码
    if args.show_license:
        try:
            from licensing.fingerprint import get_machine_code
            print("=" * 50)
            print("本机机器码：")
            print("  " + get_machine_code())
            print("=" * 50)
        except Exception as e:
            print(f"获取机器码失败: {e}")
        return

    app = QApplication(sys.argv)
    app.setApplicationName("DMM6500 Monitor")
    app.setFont(QFont("Microsoft YaHei UI", 10))

    # 初始主题
    if args.theme:
        initial_mode = args.theme
    elif args.dark:
        initial_mode = 'dark'
    else:
        initial_mode = 'light'

    # 应用级图标：libs/DMM6500app_icon.py（按主题生成）
    if HAS_APP_ICON:
        try:
            mgr = get_icon_manager()
            mgr.set_theme(initial_mode)
            mgr.set_application_icon(initial_mode)
        except Exception as e:
            print(f"[图标] 应用级图标设置失败: {e}")

    # 机械表：注册主题色板桥接（全局一次）
    if HAS_GAUGE:
        try:
            GaugeThemeManager.instance().set_palette_provider(
                lambda name: palette_from_theme(Theme(name))
            )
            GaugeThemeManager.instance().set_theme(initial_mode)
        except Exception as e:
            print(f"[机械表] 色板桥接注册失败: {e}")

    # 授权校验
    from licensing import ensure_licensed
    if not ensure_licensed():
        sys.exit(0)

    # 创建主窗口
    theme = Theme(initial_mode)
    window = DMM6500Monitor(theme=theme)

    # 把窗口绑定到图标管理器（switch_theme 时自动刷新）
    if HAS_APP_ICON:
        try:
            mgr = get_icon_manager()
            mgr.attach(window)
        except Exception as e:
            print(f"[图标] 窗口图标绑定失败: {e}")

    window.show()

    # Ctrl+T 循环切换主题
    def _cycle_theme():
        next_mode = window.theme.next_mode()
        window.switch_theme(next_mode)
        print(f"[主题] 切换到: {next_mode}")

    shortcut = QShortcut(QKeySequence("Ctrl+T"), window)
    shortcut.activated.connect(_cycle_theme)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()