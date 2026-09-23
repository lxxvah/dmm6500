#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/about_dialog.py —— 苹果风格使用说明对话框
==============================================
入口：右键菜单 → 功能介绍
Tab：概览 / 鼠标 / 键盘 / 测量模式 / 功能 / 授权
顶部：状态徽标（⭐已激活 / 🕐试用中 / ⚠️未激活 等）
"""

import sys
import math

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QTextBrowser, QPushButton, QWidget,
    QFrame,
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath
)

from theme import Theme
from libs.platform_utils import apply_titlebar_theme


# ---------- 辅助：rgba 字符串 ----------
def _hex_to_rgb(hex_str: str):
    h = hex_str.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


# ============================================================
# 内容 HTML 生成（按主题注入颜色）
# ============================================================
def _h2(text, fg):
    return (f'<h2 style="color:{fg}; margin-top:0; margin-bottom:8px; '
            f'font-size:16px; font-weight:600;">{text}</h2>')


def _h3(text, fg):
    return (f'<h3 style="color:{fg}; margin-top:14px; margin-bottom:6px; '
            f'font-size:13px; font-weight:600;">{text}</h3>')


def _p(text, mid):
    return (f'<p style="color:{mid}; line-height:1.7; '
            f'margin:4px 0; font-size:13px;">{text}</p>')


def _ul(items, fg, mid):
    li = "".join(
        f'<li style="margin:4px 0; color:{mid}; line-height:1.6;">{it}</li>'
        for it in items
    )
    return f'<ul style="margin:6px 0 6px 0; padding-left:20px;">{li}</ul>'


def _kv(k, v, k_color, v_color):
    return (f'<li style="margin:5px 0; line-height:1.65; color:{v_color};">'
            f'<b style="color:{k_color};">{k}</b> &nbsp;&mdash;&nbsp; {v}</li>')


def build_overview_html(t: Theme) -> str:
    fg  = t.fg
    mid = t.fg_mid

    try:
        from libs.license_config import AUTHOR_NAME, AUTHOR_TAGLINE
        author_line = f"作者：{AUTHOR_NAME} &nbsp;&middot;&nbsp; <i>{AUTHOR_TAGLINE}</i>"
    except Exception:
        author_line = ""

    return (
        f'<div style="font-family:\'Microsoft YaHei UI\', Inter, sans-serif;">'
        + _h2("关于本软件", fg)
        + _p(
            f'一款基于 <b>PyQt6 + PyVISA</b> 的 Keithley/Tektronix '
            f'<b>DMM6500</b> 数字万用表上位机监控软件。',
            mid
        )
        + (_p(author_line, mid) if author_line else "")
        + _h3("核心特性", fg)
        + _ul([
            '<b>实时波形</b> &mdash; 高刷新率绘制，自动降采样，10 万+ 数据点无卡顿',
            '<b>多阈值报警</b> &mdash; 同一曲线可挂多条独立规则，各自去重',
            '<b>数据记录</b> &mdash; CSV 自动分卷，每 10 万行切分',
            '<b>HTML 报告</b> &mdash; 单文件交互式报告，内嵌 ECharts 波形',
            '<b>缓存下载</b> &mdash; 从仪器内部缓冲区下载历史数据',
            '<b>5 套主题</b> &mdash; light / dark / nord / solarized_light / dracula',
        ], fg, mid)
        + _h3("系统要求", fg)
        + _ul([
            'Python 3.9+',
            'PyQt6 &middot; pyqtgraph &middot; pyvisa &middot; numpy',
            'Windows / macOS / Linux',
        ], fg, mid)
        + '</div>'
    )


def build_mouse_html(t: Theme) -> str:
    fg   = t.fg
    mid  = t.fg_mid
    pri  = t.primary

    items = [
        _kv("滚轮 上下",   "缩放 X 轴（时间轴）", pri, mid),
        _kv("Ctrl + 滚轮", "缩放 Y 轴（读数轴）", pri, mid),
        _kv("左键拖动",    "平移视图", pri, mid),
        _kv("中键拖动",    "沿单轴缩放", pri, mid),
        _kv("右键拖动",    "矩形框缩放", pri, mid),
        _kv("右键单击",    "弹出功能菜单（显示全部 / 功能介绍 / 9 项开关）", pri, mid),
        _kv("拖动游标",    "移动两根垂直游标线，标签自动避让", pri, mid),
    ]
    list_html = f'<ul style="margin:8px 0; padding-left:20px;">{"".join(items)}</ul>'

    tool_items = [
        _kv("chip 按钮", "开关对应功能（游标/网格/十字线/Y轴居中）", pri, mid),
        _kv("下拉菜单",  "选择 X 轴时间窗口", pri, mid),
        _kv("保存数据",  "发信号给主窗口，导出完整 CSV", pri, mid),
        _kv("复制截图",  "抓取整个主窗口 → 剪贴板", pri, mid),
    ]
    tool_html = f'<ul style="margin:8px 0; padding-left:20px;">{"".join(tool_items)}</ul>'

    return (
        f'<div style="font-family:\'Microsoft YaHei UI\', Inter, sans-serif;">'
        + _h2("鼠标操作", fg)
        + _h3("波形绘图区", fg)
        + list_html
        + _h3("工具栏", fg)
        + tool_html
        + '</div>'
    )


def build_keyboard_html(t: Theme) -> str:
    fg  = t.fg
    mid = t.fg_mid
    pri = t.primary

    items = [
        _kv("Ctrl + T", "循环切换 5 个主题", pri, mid),
    ]
    list_html = f'<ul style="margin:8px 0; padding-left:20px;">{"".join(items)}</ul>'

    return (
        f'<div style="font-family:\'Microsoft YaHei UI\', Inter, sans-serif;">'
        + _h2("键盘快捷键", fg)
        + list_html
        + _h3("说明", fg)
        + _p(
            "DMM6500 综合监控台目前只有 Ctrl+T 一个全局快捷键。"
            "其他操作通过工具栏按钮和右键菜单完成。",
            mid
        )
        + '</div>'
    )


def build_modes_html(t: Theme) -> str:
    fg  = t.fg
    mid = t.fg_mid
    pri = t.primary

    def section(title, rows):
        items = "".join(_kv(k, v, pri, mid) for k, v in rows)
        return _h3(title, fg) + f'<ul style="margin:6px 0; padding-left:20px;">{items}</ul>'

    return (
        f'<div style="font-family:\'Microsoft YaHei UI\', Inter, sans-serif;">'
        + _h2("测量模式", fg)
        + _p("DMM6500 支持 12 种测量功能，可在左侧「功能」下拉框中切换。", mid)
        + section("DC 直流", [
            ("DCV",   "直流电压"),
            ("DCI",   "直流电流"),
            ("RES2W", "2 线电阻"),
            ("RES4W", "4 线电阻"),
        ])
        + section("AC 交流", [
            ("ACV", "交流电压"),
            ("ACI", "交流电流"),
            ("CAP", "电容"),
        ])
        + section("频率 / 周期", [
            ("FREQ", "频率"),
            ("PER",  "周期"),
        ])
        + section("其他", [
            ("TEMP", "温度（默认 K 型热电偶）"),
            ("CONT", "通断"),
            ("DIOD", "二极管"),
        ])
        + '</div>'
    )


def build_features_html(t: Theme) -> str:
    fg  = t.fg
    mid = t.fg_mid
    pri = t.primary

    def kv_list(items):
        rows = "".join(_kv(k, v, pri, mid) for k, v in items)
        return f'<ul style="margin:6px 0; padding-left:20px;">{rows}</ul>'

    return (
        f'<div style="font-family:\'Microsoft YaHei UI\', Inter, sans-serif;">'
        + _h2("功能说明", fg)
        + _h3("左侧面板", fg)
        + kv_list([
            ("连接", "输入 IP，扫描 / 连接 / 断开"),
            ("功能", "选择测量模式，自动调零开关"),
            ("配置", "端子 / NPLC / 自动量程"),
            ("采集", "暂停 / 清空"),
            ("数据", "报警设置 / HTML 报告 / 下载缓存 / 开始记录"),
        ])
        + _h3("波形工具栏", fg)
        + kv_list([
            ("波形暂停", "冻结绘制（数据仍写入 recorder / report / alarm）"),
            ("波形复位", "Y 轴回到 [-1, 1]，恢复自动居中"),
            ("窗口",     "选择 X 轴时间窗口"),
            ("游标 / 网格 / 十字线", "显示开关"),
            ("Y轴居中",  "Y 轴自动跟随数据"),
            ("保存图形", "PNG / JPG / SVG"),
            ("保存数据", "导出完整数据 CSV"),
            ("复制截图", "整个窗口截图到剪贴板"),
        ])
        + _h3("数据生命周期", fg)
        + _p(
            "数据会持续累积到报告缓冲区（上限 100 万点）。"
            "切换测量模式会清空报告缓冲区；断开 / 重连不会清空。",
            mid
        )
        + _h3("右键菜单", fg)
        + kv_list([
            ("显示全部", "一次性显示 / 隐藏全部工具栏按钮"),
            ("功能介绍", "打开本对话框，查看软件完整操作说明"),
        ])
        + '</div>'
    )


# ============================================================
# 授权 Tab 内容
# ============================================================
def _edition_display(edition: str) -> str:
    m = {
        "standard":   "标准版",
        "pro":        "专业版",
        "enterprise": "企业版",
        "trial":      "试用版",
    }
    return m.get((edition or "").lower(), edition or "-")


def _info_row(label: str, value: str, t: Theme) -> str:
    return (
        f'<tr>'
        f'<td style="color:{t.fg_mute}; font-size:12px; '
        f'padding:6px 16px 6px 0; white-space:nowrap; '
        f'vertical-align:top; width:100px;">{label}</td>'
        f'<td style="color:{t.fg}; font-size:13px; padding:6px 0; '
        f'font-family:Consolas,\'Courier New\',monospace; '
        f'word-break:break-all;">{value}</td>'
        f'</tr>'
    )


def build_license_html(t: Theme, status, info: dict, my_code: str) -> str:
    """根据授权状态生成 HTML。"""
    fg      = t.fg
    fg_mid  = t.fg_mid
    fg_mute = t.fg_mute

    from licensing.client import LicenseResult, TrialStatus

    # ---------- 状态标题 ----------
    if status == LicenseResult.OK:
        t_type = info.get("type")

        if t_type == "license":
            header = (
                f'<div style="margin-bottom:14px;">'
                f'<span style="color:{t.success}; font-size:20px; '
                f'font-weight:600;">⭐ 已激活</span>'
                f'</div>'
            )
            rows = ""
            rows += _info_row("授权对象", info.get("licensee", "匿名"), t)
            rows += _info_row("版本", _edition_display(info.get("edition")), t)
            expire = info.get("expire", "永久")
            if str(expire).lower() in ("never", "permanent", "永久"):
                expire_disp = "永久"
            else:
                expire_disp = str(expire)
            rows += _info_row("有效期", expire_disp, t)
            if info.get("issued_at"):
                rows += _info_row("签发时间", info["issued_at"], t)
            rows += _info_row("机器码", my_code, t)

            footer = (
                f'<p style="color:{fg_mute}; font-size:12px; '
                f'margin-top:16px; line-height:1.7;">'
                f'如需更换授权或升级版本，请点击下方按钮。</p>'
            )

        elif t_type == "trial":
            days = info.get("days_remaining", 0)
            header = (
                f'<div style="margin-bottom:14px;">'
                f'<span style="color:{t.primary}; font-size:20px; '
                f'font-weight:600;">🕐 试用中</span>'
                f'<span style="color:{t.fg_mid}; font-size:13px; '
                f'margin-left:12px;">剩余 {days} 天</span>'
                f'</div>'
            )
            rows = _info_row("机器码", my_code, t)
            footer = (
                f'<p style="color:{fg_mute}; font-size:12px; '
                f'margin-top:16px; line-height:1.7;">'
                f'试用期结束后需激活才能继续使用。'
                f'点击下方按钮购买或申请正式授权。</p>'
            )
        else:
            header = (
                f'<div style="margin-bottom:14px;">'
                f'<span style="color:{t.fg_mute}; font-size:20px; '
                f'font-weight:600;">未激活</span>'
                f'</div>'
            )
            rows = _info_row("机器码", my_code, t)
            footer = ""
    else:
        # 未通过
        trial_status = info.get("trial_status")

        if status == LicenseResult.EXPIRED or trial_status == TrialStatus.EXPIRED:
            header = (
                f'<div style="margin-bottom:14px;">'
                f'<span style="color:{t.danger}; font-size:20px; '
                f'font-weight:600;">❌ 授权已过期</span>'
                f'</div>'
            )
        elif (status == LicenseResult.TIME_TAMPERED
              or trial_status == TrialStatus.TAMPERED):
            header = (
                f'<div style="margin-bottom:14px;">'
                f'<span style="color:{t.warning}; font-size:20px; '
                f'font-weight:600;">⚠️ 系统时间异常</span>'
                f'</div>'
            )
        else:
            header = (
                f'<div style="margin-bottom:14px;">'
                f'<span style="color:{t.danger}; font-size:20px; '
                f'font-weight:600;">⚠️ 未激活</span>'
                f'</div>'
            )

        rows = ""
        if info.get("reason"):
            rows += _info_row("原因", info["reason"], t)
        rows += _info_row("机器码", my_code, t)

        footer = (
            f'<p style="color:{fg_mute}; font-size:12px; '
            f'margin-top:16px; line-height:1.7;">'
            f'将机器码发送给作者，获取授权密钥后点击下方按钮激活。</p>'
        )

    return (
        f'<div style="font-family:\'Microsoft YaHei UI\', Inter, sans-serif; '
        f'padding:16px 18px;">'
        + header
        + f'<table style="border-collapse:collapse;">{rows}</table>'
        + footer
        + '</div>'
    )


# ============================================================
# 自绘应用图标
# ============================================================
def _make_app_icon(theme: Theme, size: int = 64) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(theme.primary)))
    p.drawRoundedRect(2, 2, size - 4, size - 4, 14, 14)

    pen = QPen(QColor("#ffffff"), 3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    path = QPainterPath()
    n = 32
    x0, x1 = 12, size - 12
    cy = size / 2
    amp = size * 0.22
    for i in range(n):
        t = i / (n - 1)
        x = x0 + (x1 - x0) * t
        y = cy + math.sin(t * math.pi * 3.0) * amp
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    p.drawPath(path)
    p.end()

    return pix


# ============================================================
# 主对话框
# ============================================================
class AboutDialog(QDialog):
    """苹果风使用说明对话框（含授权 Tab）"""

    def __init__(self, parent=None, theme: Theme = None):
        super().__init__(parent)
        self.theme = theme if theme else Theme('light')

        self.setWindowTitle("关于 DMM6500 综合监控台")
        self.setModal(True)
        self.setMinimumSize(780, 640)
        self.setMaximumSize(920, 820)

        # 授权状态缓存
        self._lic_status = None
        self._lic_info = {}
        self._lic_code = ""

        self._init_ui()
        self._apply_theme()
        self._refresh_license_status()

    # ---------- 标题栏跟随主题 ----------
    def showEvent(self, event):
        super().showEvent(event)
        apply_titlebar_theme(self, self.theme.is_dark)

    # ---------- UI ----------
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 20)
        layout.setSpacing(16)

        # 顶部：图标 + 标题 + 副标题 + 状态徽标
        header = QHBoxLayout()
        header.setSpacing(18)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setPixmap(_make_app_icon(self.theme, 64))
        header.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignTop)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title_box.setContentsMargins(0, 4, 0, 0)

        # 标题行：标题 + 徽标
        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        self.title_label = QLabel("DMM6500 综合监控台")
        self.title_label.setObjectName("about_title")
        title_row.addWidget(self.title_label)

        self.status_badge = QLabel()
        self.status_badge.setObjectName("status_badge")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.addWidget(self.status_badge)

        title_row.addStretch()
        title_box.addLayout(title_row)

        # 副标题
        self.subtitle_label = QLabel("Version 1.0   ·   PyQt6 + PyVISA")
        self.subtitle_label.setObjectName("about_subtitle")
        title_box.addWidget(self.subtitle_label)

        # 作者
        try:
            from libs.license_config import AUTHOR_NAME, AUTHOR_TAGLINE
            author_text = f"作者：{AUTHOR_NAME}   ·   {AUTHOR_TAGLINE}"
        except Exception:
            author_text = "作者：得鹿梦鱼   ·   「莫道桑榆晚，为霞尚满天」"

        self.author_label = QLabel(author_text)
        self.author_label.setObjectName("about_author")
        title_box.addWidget(self.author_label)

        title_box.addStretch()
        header.addLayout(title_box, 1)

        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("about_tabs")
        self.tabs.setDocumentMode(True)

        self.tab_overview = self._make_browser()
        self.tab_mouse    = self._make_browser()
        self.tab_keyboard = self._make_browser()
        self.tab_modes    = self._make_browser()
        self.tab_features = self._make_browser()
        self.tab_license  = self._make_license_tab()

        self.tabs.addTab(self.tab_overview, "概览")
        self.tabs.addTab(self.tab_mouse,    "鼠标")
        self.tabs.addTab(self.tab_keyboard, "键盘")
        self.tabs.addTab(self.tab_modes,    "测量模式")
        self.tabs.addTab(self.tab_features, "功能")
        self.tabs.addTab(self.tab_license,  "授权")

        layout.addWidget(self.tabs, 1)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setDefault(True)
        self.ok_btn.setMinimumWidth(96)
        self.ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.ok_btn)
        layout.addLayout(btn_row)

    def _make_browser(self) -> QTextBrowser:
        b = QTextBrowser()
        b.setOpenExternalLinks(False)
        b.setFrameShape(QFrame.Shape.NoFrame)
        # ✅ 禁用右键菜单
        b.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        return b

    def _make_license_tab(self) -> QWidget:
        """授权 Tab：上面 QTextBrowser 显示信息，下面放按钮。"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_license_browser = QTextBrowser()
        self.tab_license_browser.setOpenExternalLinks(False)
        self.tab_license_browser.setFrameShape(QFrame.Shape.NoFrame)
        # ✅ 禁用右键菜单
        self.tab_license_browser.setContextMenuPolicy(
            Qt.ContextMenuPolicy.NoContextMenu
        )
        layout.addWidget(self.tab_license_browser, 1)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(18, 6, 18, 14)
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.license_primary_btn = QPushButton("立即激活")
        self.license_primary_btn.setMinimumWidth(120)
        self.license_primary_btn.clicked.connect(self._on_activate_clicked)
        btn_row.addWidget(self.license_primary_btn)

        self.license_copy_btn = QPushButton("复制机器码")
        self.license_copy_btn.setMinimumWidth(120)
        self.license_copy_btn.clicked.connect(self._on_copy_machine)
        btn_row.addWidget(self.license_copy_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return page

    # ---------- 授权状态刷新 ----------
    def _refresh_license_status(self):
        """读取授权状态 → 更新徽标 + Tab 内容 + 主按钮文案。"""
        try:
            from licensing.client import (
                check_access, LicenseResult, TrialStatus, machine_code,
            )
            self._lic_status, self._lic_info = check_access()
            self._lic_code = machine_code()
        except Exception as e:
            print(f"[About] 授权模块读取失败: {e}")
            self._lic_status = None
            self._lic_info = {"reason": f"授权模块不可用: {e}"}
            self._lic_code = "-"

        self._update_status_badge()
        self._update_license_tab()
        self._update_primary_button()

    def _update_status_badge(self):
        """更新顶部徽标文本与配色。"""
        from licensing.client import LicenseResult, TrialStatus

        t = self.theme
        text = ""
        kind = "normal"

        if self._lic_status is None:
            text, kind = "授权模块异常", "error"
        elif self._lic_status == LicenseResult.OK:
            t_type = self._lic_info.get("type")
            if t_type == "license":
                expire = self._lic_info.get("expire", "永久")
                if str(expire).lower() in ("never", "permanent", "永久"):
                    text, kind = "⭐ 已激活", "success"
                else:
                    text, kind = f"⭐ 已激活 · 至 {expire}", "success"
            elif t_type == "trial":
                days = self._lic_info.get("days_remaining", 0)
                text, kind = f"🕐 试用中 · 剩 {days} 天", "info"
        else:
            trial_status = self._lic_info.get("trial_status")
            if (self._lic_status == LicenseResult.EXPIRED
                    or trial_status == TrialStatus.EXPIRED):
                text, kind = "❌ 已过期", "error"
            elif (self._lic_status == LicenseResult.TIME_TAMPERED
                  or trial_status == TrialStatus.TAMPERED):
                text, kind = "⚠️ 时间异常", "warning"
            else:
                text, kind = "⚠️ 未激活", "error"

        # 配色
        if kind == "success":
            bg, fg = _rgba(t.success, 0.14), t.success
        elif kind == "info":
            bg, fg = _rgba(t.primary, 0.14), t.primary
        elif kind == "warning":
            bg, fg = _rgba(t.warning, 0.14), t.warning
        elif kind == "error":
            bg, fg = _rgba(t.danger, 0.14), t.danger
        else:
            bg, fg = _rgba(t.fg_mute, 0.10), t.fg_mute

        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(f"""
            QLabel#status_badge {{
                color: {fg};
                background-color: {bg};
                border-radius: 10px;
                padding: 3px 12px;
                font-size: 11px;
                font-weight: 600;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}
        """)

    def _update_license_tab(self):
        """重绘授权 Tab 内容。"""
        html = build_license_html(
            self.theme,
            self._lic_status,
            self._lic_info or {},
            self._lic_code or "-",
        )
        self.tab_license_browser.setHtml(html)

    def _update_primary_button(self):
        """主按钮文案随状态变化。"""
        from licensing.client import LicenseResult, TrialStatus

        if self._lic_status == LicenseResult.OK:
            t_type = self._lic_info.get("type")
            if t_type == "license":
                self.license_primary_btn.setText("更换授权")
            elif t_type == "trial":
                self.license_primary_btn.setText("立即购买")
        else:
            self.license_primary_btn.setText("立即激活")

    # ---------- 授权按钮事件 ----------
    def _on_activate_clicked(self):
        """打开授权对话框。关闭后刷新本 Tab。"""
        try:
            from licensing.dialog import LicenseDialog
            from licensing.client import LicenseResult
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误",
                                 f"无法加载授权对话框：\n{e}")
            return

        # 打开一个"全新的授权选择"界面
        dlg = LicenseDialog(
            status=LicenseResult.NOT_FOUND,
            info={},
            parent=self,
        )

        result = dlg.exec()

        from PyQt6.QtWidgets import QDialog
        # 无论用户是否激活成功，都刷新一下状态
        self._refresh_license_status()

        if result == QDialog.DialogCode.Accepted:
            # 用户激活成功 → 立即刷新（刷新已在上面做）
            pass

    def _on_copy_machine(self):
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtGui import QGuiApplication
        if not self._lic_code or self._lic_code == "-":
            QMessageBox.warning(self, "提示", "机器码不可用")
            return
        QGuiApplication.clipboard().setText(self._lic_code)
        QMessageBox.information(
            self, "已复制",
            f"机器码已复制到剪贴板：\n\n{self._lic_code}"
        )

    # ---------- 主题 ----------
    def _apply_theme(self):
        t = self.theme

        self.icon_label.setPixmap(_make_app_icon(t, 64))

        self.tab_overview.setHtml(build_overview_html(t))
        self.tab_mouse.setHtml(build_mouse_html(t))
        self.tab_keyboard.setHtml(build_keyboard_html(t))
        self.tab_modes.setHtml(build_modes_html(t))
        self.tab_features.setHtml(build_features_html(t))
        # 授权 Tab 由 _refresh_license_status 渲染

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg};
                color: {t.fg};
            }}
            QLabel#about_title {{
                color: {t.fg};
                font-size: 22px;
                font-weight: 600;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
                letter-spacing: -0.3px;
            }}
            QLabel#about_subtitle {{
                color: {t.fg_mute};
                font-size: 12px;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}
            QLabel#about_author {{
                color: {t.primary};
                font-size: 12px;
                font-weight: 500;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}

            QTabWidget#about_tabs::pane {{
                background-color: {t.bg_deep if t.is_dark else '#ffffff'};
                border: 1px solid {t.hairline};
                border-radius: 10px;
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {t.fg_mute};
                padding: 8px 18px;
                margin-right: 4px;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}
            QTabBar::tab:hover {{
                color: {t.fg};
                background-color: {t.hairline if not t.is_dark else 'rgba(255,255,255,0.06)'};
            }}
            QTabBar::tab:selected {{
                color: {t.primary};
                font-weight: 600;
            }}

            QTextBrowser {{
                background-color: transparent;
                border: none;
                padding: 14px 18px;
                color: {t.fg_mid};
                font-size: 13px;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}
            QTextBrowser::viewport {{
                background-color: transparent;
            }}

            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {t.hairline};
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        # 按钮样式（跟随主题）
        self.ok_btn.setStyleSheet(t.button_qss('primary'))
        self.license_primary_btn.setStyleSheet(t.button_qss('primary'))
        self.license_copy_btn.setStyleSheet(t.button_qss('neutral'))

        # 徽标样式由 _update_status_badge 设置
        self._update_status_badge()


# ============================================================
# 一行式入口
# ============================================================
def show_about(parent=None, theme: Theme = None) -> None:
    dlg = AboutDialog(parent, theme)
    dlg.exec()