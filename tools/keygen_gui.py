#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/keygen_gui.py —— 软件授权签发工具（苹果风 / 通用 / 作者专用）
========================================================================
支持多应用切换，每个应用独立：
  · 显示名
  · 密钥前缀
  · 联系方式

所有应用的签发共用同一私钥（与 exe 同级的 private_key.pem），
通过 payload 里的 "app" 字段区分，客户端会自动校验。

依赖：
    pip install PyQt6 cryptography

使用（开发模式）：
    1. 首次：python tools/generate_keys.py 生成 private_key.pem
    2. python tools/keygen_gui.py
    3. 应用列表在 tools/apps_config.json 中维护

使用（打包后）：
    1. Keygen.exe 同目录放 private_key.pem
    2. 双击 Keygen.exe
    3. 同目录自动生成/读取 apps_config.json
"""

import base64
import json
import os
import re
import smtplib
import subprocess
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from pathlib import Path

from PyQt6.QtCore import Qt, QDate, QRectF, QPointF
from PyQt6.QtGui import (
    QFont, QGuiApplication, QIcon, QPixmap, QPainter, QPen, QBrush,
    QColor, QLinearGradient,
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QDateEdit, QDialog, QSpinBox, QCheckBox,
    QFrame, QScrollArea,
)

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    print("缺少 cryptography 库，请运行：pip install cryptography")
    sys.exit(1)


# ======================================================================
# 路径 & 常量（兼容 PyInstaller 打包）
# ======================================================================
def _app_dir() -> Path:
    """exe 打包后返回 exe 所在目录；未打包返回本文件目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


HERE = _app_dir()
PRIVATE_KEY_PATH = HERE / "private_key.pem"
SMTP_CONFIG_PATH = HERE / "smtp_config.json"

# KEY_PREFIX 默认值（打包后无法从项目读取，回退到默认）
KEY_PREFIX = "DMM6500-"

# 开发模式下可尝试从项目读 KEY_PREFIX
if not getattr(sys, "frozen", False):
    try:
        PROJECT_ROOT = HERE.parent
        sys.path.insert(0, str(PROJECT_ROOT))
        from libs.license_config import KEY_PREFIX as _KP
        KEY_PREFIX = _KP
    except Exception:
        pass

# 应用配置模块（同目录；打包时被 PyInstaller 嵌入）
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(HERE))

try:
    from apps_config import (
        load_config as load_apps_config,
        save_config as save_apps_config,
        get_current_app,
        set_current_app,
        list_app_names,
        find_by_name,
        CONFIG_PATH as APPS_CONFIG_IMPORTED_PATH,
    )
except Exception as e:
    print(f"[警告] 无法加载 apps_config 模块：{e}")
    sys.exit(1)


# ======================================================================
# 苹果风配色
# ======================================================================
class C:
    PRIMARY       = "#007AFF"
    PRIMARY_HOVER = "#0066D6"
    PRIMARY_DOWN  = "#0055B3"
    PRIMARY_DIS   = "#B8B8BD"

    INK           = "#1D1D1F"
    INK_MID       = "#48484A"
    INK_MUTE      = "#86868B"

    BG            = "#F5F5F7"
    CARD          = "#FFFFFF"
    INPUT         = "#F5F5F7"
    INPUT_FOCUS   = "#FFFFFF"
    CODE_BG       = "#FAFAFA"

    HAIRLINE      = "#E5E5E7"
    HAIRLINE_SOFT = "#F0F0F2"

    SUCCESS       = "#34C759"
    DANGER        = "#FF3B30"
    WARNING       = "#FF9500"

    SECONDARY_BG  = "#E8E8ED"
    SECONDARY_FG  = "#1D1D1F"


# ======================================================================
# 苹果风钥匙图标
# ======================================================================
def _draw_key_glyph(p: QPainter, scale: float):
    grad = QLinearGradient(0, 0, 0, 256 * scale)
    grad.setColorAt(0.0, QColor("#5AA9FF"))
    grad.setColorAt(0.55, QColor("#0A84FF"))
    grad.setColorAt(1.0, QColor("#0066D6"))

    bg_rect = QRectF(16 * scale, 16 * scale, 224 * scale, 224 * scale)
    radius = 54 * scale

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(bg_rect, radius, radius)

    hl = QLinearGradient(0, 0, 0, 128 * scale)
    hl.setColorAt(0.0, QColor(255, 255, 255, 60))
    hl.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(QBrush(hl))
    p.drawRoundedRect(
        QRectF(16 * scale, 16 * scale, 224 * scale, 112 * scale),
        radius, radius,
    )

    pen = QPen(QColor("#FFFFFF"), 13 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    head_cx = 92 * scale
    head_cy = 128 * scale
    head_r = 32 * scale
    p.drawEllipse(QPointF(head_cx, head_cy), head_r, head_r)

    shaft_start_x = head_cx + head_r - 4 * scale
    shaft_end_x = 210 * scale
    p.drawLine(QPointF(shaft_start_x, head_cy),
               QPointF(shaft_end_x, head_cy))

    p.drawLine(QPointF(170 * scale, head_cy),
               QPointF(170 * scale, head_cy + 26 * scale))
    p.drawLine(QPointF(194 * scale, head_cy),
               QPointF(194 * scale, head_cy + 18 * scale))


def make_key_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(s, s)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        _draw_key_glyph(p, s / 256.0)
        p.end()
        icon.addPixmap(pm)
    return icon


# ======================================================================
# QSS
# ======================================================================
GLOBAL_QSS = f"""
QWidget {{
    font-family: "Microsoft YaHei UI", "PingFang SC", "Inter", system-ui, sans-serif;
    color: {C.INK};
}}

QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QFrame#card {{
    background-color: {C.CARD};
    border: 1px solid {C.HAIRLINE};
    border-radius: 14px;
}}

QFrame#app_bar {{
    background-color: {C.CARD};
    border: 1px solid {C.HAIRLINE};
    border-radius: 12px;
}}

QLabel#card_title {{
    color: {C.INK};
    font-size: 14px;
    font-weight: 600;
    background: transparent;
}}

QLabel#field_label {{
    color: {C.INK_MID};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}}

QLabel#hint {{
    color: {C.INK_MUTE};
    font-size: 11px;
    background: transparent;
}}

QLabel#status_ok {{
    color: {C.SUCCESS};
    font-size: 11px;
    background: transparent;
}}

QLabel#status_err {{
    color: {C.DANGER};
    font-size: 11px;
    background: transparent;
}}

QLineEdit {{
    background-color: {C.INPUT};
    color: {C.INK};
    border: 1px solid {C.HAIRLINE};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {C.PRIMARY};
    selection-color: white;
}}
QLineEdit:focus {{
    background-color: {C.INPUT_FOCUS};
    border: 1px solid {C.PRIMARY};
}}
QLineEdit:read-only {{
    color: {C.INK_MID};
}}
QLineEdit#mono {{
    font-family: Consolas, "Courier New", monospace;
}}

QComboBox {{
    background-color: {C.INPUT};
    color: {C.INK};
    border: 1px solid {C.HAIRLINE};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    min-height: 18px;
}}
QComboBox:focus {{
    background-color: {C.INPUT_FOCUS};
    border: 1px solid {C.PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 8px; height: 8px;
    border-left: 1.5px solid {C.INK_MUTE};
    border-bottom: 1.5px solid {C.INK_MUTE};
    margin-right: 8px;
    margin-top: -2px;
    transform: rotate(-45deg);
}}
QComboBox QAbstractItemView {{
    background-color: {C.CARD};
    color: {C.INK};
    border: 1px solid {C.HAIRLINE};
    border-radius: 10px;
    outline: none;
    padding: 4px;
    selection-background-color: {C.PRIMARY};
    selection-color: white;
}}
QComboBox QAbstractItemView::item {{
    min-height: 22px;
    padding: 2px 8px;
    border-radius: 6px;
    color: {C.INK};
    background: transparent;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {C.PRIMARY};
    color: #FFFFFF;
}}

QDateEdit {{
    background-color: {C.INPUT};
    color: {C.INK};
    border: 1px solid {C.HAIRLINE};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
}}
QDateEdit:focus {{
    background-color: {C.INPUT_FOCUS};
    border: 1px solid {C.PRIMARY};
}}
QDateEdit::drop-down {{
    border: none;
    width: 22px;
}}

QSpinBox {{
    background-color: {C.INPUT};
    color: {C.INK};
    border: 1px solid {C.HAIRLINE};
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 13px;
}}
QSpinBox:focus {{
    background-color: {C.INPUT_FOCUS};
    border: 1px solid {C.PRIMARY};
}}

QCheckBox {{
    color: {C.INK_MID};
    font-size: 12px;
    spacing: 6px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {C.HAIRLINE};
    border-radius: 4px;
    background-color: {C.INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {C.PRIMARY};
    border-color: {C.PRIMARY};
    image: none;
}}

QPushButton {{
    background-color: {C.SECONDARY_BG};
    color: {C.SECONDARY_FG};
    border: none;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: #DCDCE1;
}}
QPushButton:pressed {{
    background-color: #CFCFD5;
}}
QPushButton:disabled {{
    background-color: {C.HAIRLINE_SOFT};
    color: {C.INK_MUTE};
}}

QPushButton#primary {{
    background-color: {C.PRIMARY};
    color: white;
}}
QPushButton#primary:hover {{
    background-color: {C.PRIMARY_HOVER};
}}
QPushButton#primary:pressed {{
    background-color: {C.PRIMARY_DOWN};
}}
QPushButton#primary:disabled {{
    background-color: {C.PRIMARY_DIS};
    color: white;
}}

QPushButton#ghost {{
    background-color: transparent;
    color: {C.PRIMARY};
    border: 1px solid transparent;
}}
QPushButton#ghost:hover {{
    background-color: rgba(0, 122, 255, 0.08);
}}

QTextEdit {{
    background-color: {C.CODE_BG};
    color: {C.INK};
    border: 1px solid {C.HAIRLINE};
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
    selection-background-color: {C.PRIMARY};
    selection-color: white;
}}
QTextEdit:focus {{
    border: 1px solid {C.PRIMARY};
}}
QTextEdit#key_output {{
    font-family: Consolas, "Courier New", monospace;
    font-size: 11px;
    color: {C.INK_MID};
}}
QTextEdit#email_body {{
    font-family: "Microsoft YaHei UI", "PingFang SC", system-ui, sans-serif;
    font-size: 12px;
    line-height: 1.55;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C.HAIRLINE};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: #C8C8CD;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
}}
"""


# ======================================================================
# SMTP 配置
# ======================================================================
SMTP_PRESETS = {
    "QQ 邮箱":   {"server": "smtp.qq.com",       "port": 465, "use_ssl": True},
    "163 邮箱":  {"server": "smtp.163.com",      "port": 465, "use_ssl": True},
    "126 邮箱":  {"server": "smtp.126.com",      "port": 465, "use_ssl": True},
    "Gmail":    {"server": "smtp.gmail.com",    "port": 465, "use_ssl": True},
    "Outlook":  {"server": "smtp.office365.com","port": 587, "use_ssl": False},
    "自定义":    {"server": "",                  "port": 465, "use_ssl": True},
}


def load_smtp_config() -> dict:
    cfg = {
        "server": "", "port": 465, "use_ssl": True,
        "user": "", "password": "", "sender_name": "得鹿梦鱼",
    }
    if SMTP_CONFIG_PATH.is_file():
        try:
            with open(SMTP_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def save_smtp_config(cfg: dict) -> None:
    try:
        SMTP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SMTP_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[SMTP] 保存失败: {e}")


def smtp_is_configured(cfg: dict) -> bool:
    return bool(cfg.get("server") and cfg.get("user") and cfg.get("password"))


def send_email_smtp(cfg: dict, to_addr: str, subject: str,
                    body: str, timeout: float = 15.0) -> tuple:
    if not smtp_is_configured(cfg):
        return False, "SMTP 未配置完整"

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


def test_smtp_connection(cfg: dict, timeout: float = 8.0) -> tuple:
    if not smtp_is_configured(cfg):
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


# ======================================================================
# 通用小组件
# ======================================================================
class Card(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(18, 16, 18, 16)
        self._outer.setSpacing(10)

        if title:
            lbl = QLabel(title)
            lbl.setObjectName("card_title")
            self._outer.addWidget(lbl)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self._outer.addLayout(self.body)

    def add_layout(self, layout):
        self.body.addLayout(layout)

    def add_widget(self, widget):
        self.body.addWidget(widget)


def field_row(label_text: str, widget: QWidget,
              label_w: int = 80) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label_text)
    lbl.setObjectName("field_label")
    lbl.setFixedWidth(label_w)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return row


# ======================================================================
# SMTP 设置对话框
# ======================================================================
class SmtpSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SMTP 邮件设置")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setStyleSheet(GLOBAL_QSS)
        self.setWindowIcon(make_key_icon())

        self.cfg = load_smtp_config()
        self._init_ui()
        self._load_into_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.setAutoFillBackground(True)
        self.setStyleSheet(
            GLOBAL_QSS +
            f"QDialog {{ background-color: {C.BG}; }}"
        )

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(22, 20, 22, 18)
        cl.setSpacing(14)

        title = QLabel("SMTP 邮件设置")
        title.setStyleSheet(
            f"color: {C.INK}; font-size: 18px; font-weight: 600;"
        )
        cl.addWidget(title)

        card1 = Card()
        row0 = QHBoxLayout()
        row0.setSpacing(10)
        lbl0 = QLabel("预设")
        lbl0.setObjectName("field_label")
        lbl0.setFixedWidth(80)
        lbl0.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(SMTP_PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self._on_preset)
        row0.addWidget(lbl0)
        row0.addWidget(self.preset_combo, 1)
        card1.add_layout(row0)

        self.server_edit = QLineEdit()
        self.server_edit.setPlaceholderText("smtp.qq.com")
        card1.add_layout(field_row("服务器", self.server_edit))

        row_port = QHBoxLayout()
        row_port.setSpacing(10)
        lblp = QLabel("端口")
        lblp.setObjectName("field_label")
        lblp.setFixedWidth(80)
        lblp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row_port.addWidget(lblp)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(465)
        self.port_spin.setFixedWidth(110)
        row_port.addWidget(self.port_spin)
        self.ssl_cb = QCheckBox("使用 SSL")
        self.ssl_cb.setChecked(True)
        row_port.addWidget(self.ssl_cb)
        row_port.addStretch()
        card1.add_layout(row_port)

        cl.addWidget(card1)

        card2 = Card()
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("例：xxx@qq.com")
        card2.add_layout(field_row("邮箱账号", self.user_edit))

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(10)
        lbl_pwd = QLabel("授权码")
        lbl_pwd.setObjectName("field_label")
        lbl_pwd.setFixedWidth(80)
        lbl_pwd.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pwd_row.addWidget(lbl_pwd)
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setPlaceholderText("QQ/163 邮箱用授权码，不是登录密码")
        pwd_row.addWidget(self.pwd_edit, 1)
        self.show_pwd_cb = QCheckBox("显示")
        self.show_pwd_cb.toggled.connect(
            lambda on: self.pwd_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on
                else QLineEdit.EchoMode.Password
            )
        )
        pwd_row.addWidget(self.show_pwd_cb)
        card2.add_layout(pwd_row)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("收件人看到的发件人名字")
        card2.add_layout(field_row("发件人", self.name_edit))
        cl.addWidget(card2)

        help_label = QLabel(
            "QQ 邮箱：设置 → 账户 → 开启 IMAP/SMTP → 生成授权码<br>"
            "163 邮箱：设置 → POP3/SMTP/IMAP → 开启 → 获取授权码<br>"
            "Gmail：需在 Google 账号里生成「应用专用密码」"
        )
        help_label.setObjectName("hint")
        help_label.setTextFormat(Qt.TextFormat.RichText)
        help_label.setWordWrap(True)
        cl.addWidget(help_label)

        cl.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self._on_test)
        btn_row.addWidget(self.test_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("primary")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        cl.addLayout(btn_row)
        outer.addWidget(content)

    def _load_into_ui(self):
        self.server_edit.setText(self.cfg.get("server", ""))
        self.port_spin.setValue(int(self.cfg.get("port", 465)))
        self.ssl_cb.setChecked(bool(self.cfg.get("use_ssl", True)))
        self.user_edit.setText(self.cfg.get("user", ""))
        self.pwd_edit.setText(self.cfg.get("password", ""))
        self.name_edit.setText(self.cfg.get("sender_name", ""))

        for name, preset in SMTP_PRESETS.items():
            if preset["server"] == self.cfg.get("server"):
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentText(name)
                self.preset_combo.blockSignals(False)
                break
        else:
            self.preset_combo.setCurrentText("自定义")

    def _collect(self) -> dict:
        return {
            "server":      self.server_edit.text().strip(),
            "port":        int(self.port_spin.value()),
            "use_ssl":     bool(self.ssl_cb.isChecked()),
            "user":        self.user_edit.text().strip(),
            "password":    self.pwd_edit.text(),
            "sender_name": self.name_edit.text().strip(),
        }

    def _on_preset(self, name: str):
        preset = SMTP_PRESETS.get(name)
        if not preset:
            return
        if preset["server"]:
            self.server_edit.setText(preset["server"])
        self.port_spin.setValue(preset["port"])
        self.ssl_cb.setChecked(preset["use_ssl"])

    def _on_test(self):
        cfg = self._collect()
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        QApplication.processEvents()

        try:
            ok, msg = test_smtp_connection(cfg)
        except Exception as e:
            ok, msg = False, str(e)

        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")

        if ok:
            QMessageBox.information(self, "连接成功",
                                    f"SMTP 连接正常！\n\n{msg}")
        else:
            QMessageBox.critical(self, "连接失败", msg)

    def _on_save(self):
        cfg = self._collect()
        if not cfg["server"] or not cfg["user"] or not cfg["password"]:
            QMessageBox.warning(self, "提示",
                                "服务器、账号、授权码都必须填写。")
            return
        save_smtp_config(cfg)
        self.accept()


# ======================================================================
# 主窗口
# ======================================================================
class KeygenWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("软件授权签发工具")
        self.resize(840, 960)
        self.setMinimumSize(720, 680)
        self.setStyleSheet(GLOBAL_QSS)
        self.setWindowIcon(make_key_icon())

        self._private_key = None
        self._smtp_cfg = load_smtp_config()
        self._apps_cfg = load_apps_config()
        self._current_app = get_current_app(self._apps_cfg)

        self._last_lic: dict | None = None
        self._last_key_string: str = ""
        self._last_default_name: str = ""

        self._load_private_key()
        self._init_ui()
        self._refresh_smtp_status()

    def _load_private_key(self):
        if not PRIVATE_KEY_PATH.is_file():
            QMessageBox.critical(
                None, "缺少私钥",
                f"未找到：\n{PRIVATE_KEY_PATH}\n\n"
                "请把 private_key.pem 放到 exe 同目录，或运行：\n"
                "    python tools/generate_keys.py"
            )
            sys.exit(1)
        try:
            self._private_key = serialization.load_pem_private_key(
                PRIVATE_KEY_PATH.read_bytes(), password=None
            )
        except Exception as e:
            QMessageBox.critical(None, "私钥加载失败", str(e))
            sys.exit(1)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        root.addWidget(scroll)

        inner = QWidget()
        scroll.setWidget(inner)

        v = QVBoxLayout(inner)
        v.setContentsMargins(22, 22, 22, 22)
        v.setSpacing(14)

        # 页头
        header = QHBoxLayout()
        header.setSpacing(12)

        logo = QLabel("🔑")
        logo.setStyleSheet("font-size: 30px;")
        header.addWidget(logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        t1 = QLabel("软件授权签发工具")
        t1.setStyleSheet(
            f"color: {C.INK}; font-size: 20px; font-weight: 600;"
        )
        t2 = QLabel("作者专用 · 得鹿梦鱼")
        t2.setObjectName("hint")
        title_box.addWidget(t1)
        title_box.addWidget(t2)
        header.addLayout(title_box)
        header.addStretch()
        v.addLayout(header)

        v.addSpacing(4)

        # 应用选择器
        app_bar = QFrame()
        app_bar.setObjectName("app_bar")
        ab = QHBoxLayout(app_bar)
        ab.setContentsMargins(16, 12, 16, 12)
        ab.setSpacing(10)

        ab_lbl = QLabel("当前应用")
        ab_lbl.setObjectName("field_label")
        ab_lbl.setFixedWidth(80)
        ab_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ab.addWidget(ab_lbl)

        self.app_combo = QComboBox()
        self.app_combo.addItems(list_app_names(self._apps_cfg))
        for i, app in enumerate(self._apps_cfg.get("apps", [])):
            if app.get("id") == self._apps_cfg.get("current_app"):
                self.app_combo.setCurrentIndex(i)
                break
        self.app_combo.currentIndexChanged.connect(self._on_app_changed)
        ab.addWidget(self.app_combo, 1)

        self.edit_apps_btn = QPushButton("编辑应用列表")
        self.edit_apps_btn.setFixedWidth(120)
        self.edit_apps_btn.clicked.connect(self._on_edit_apps)
        ab.addWidget(self.edit_apps_btn)

        self.reload_apps_btn = QPushButton("刷新")
        self.reload_apps_btn.setFixedWidth(60)
        self.reload_apps_btn.clicked.connect(self._on_reload_apps)
        ab.addWidget(self.reload_apps_btn)

        v.addWidget(app_bar)

        self.app_info_label = QLabel()
        self.app_info_label.setObjectName("hint")
        self.app_info_label.setWordWrap(True)
        v.addWidget(self.app_info_label)

        v.addSpacing(4)

        # ① 客户机器码
        card1 = Card("①  客户机器码")
        self.machine_edit = QLineEdit()
        self.machine_edit.setObjectName("mono")
        self.machine_edit.setPlaceholderText("例：A3F5-9B21-C8E4-7D02")
        self.machine_edit.setMinimumHeight(36)

        paste_btn = QPushButton("粘贴")
        paste_btn.setFixedWidth(70)
        paste_btn.clicked.connect(self._on_paste_machine)

        mc_row = QHBoxLayout()
        mc_row.setSpacing(8)
        mc_row.addWidget(self.machine_edit, 1)
        mc_row.addWidget(paste_btn)
        card1.add_layout(mc_row)

        hint1 = QLabel(
            "客户首次启动软件会看到这串码。"
            "也可让客户运行： python main.py --show-license"
        )
        hint1.setObjectName("hint")
        hint1.setWordWrap(True)
        card1.add_widget(hint1)

        v.addWidget(card1)

        # ② 授权信息
        card2 = Card("②  授权信息")

        self.licensee_edit = QLineEdit()
        self.licensee_edit.setPlaceholderText("客户名 / 公司名（可留空）")
        card2.add_layout(field_row("授权对象", self.licensee_edit))

        self.edition_combo = QComboBox()
        self.edition_combo.addItem("标准版", "standard")
        self.edition_combo.addItem("专业版", "pro")
        self.edition_combo.setCurrentIndex(0)
        card2.add_layout(field_row("版本", self.edition_combo))

        period_row = QHBoxLayout()
        period_row.setSpacing(10)
        lbl_p = QLabel("有效期")
        lbl_p.setObjectName("field_label")
        lbl_p.setFixedWidth(80)
        lbl_p.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        period_row.addWidget(lbl_p)

        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "永久", "1 天", "1 个月", "3 个月", "6 个月",
            "1 年", "2 年", "3 年", "自定义日期",
        ])
        self.period_combo.setCurrentText("1 年")
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        period_row.addWidget(self.period_combo, 2)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate().addYears(1))
        self.date_edit.setEnabled(False)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setFixedWidth(140)
        period_row.addWidget(self.date_edit, 1)

        card2.add_layout(period_row)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("可选，仅存档用")
        card2.add_layout(field_row("备注", self.note_edit))

        v.addWidget(card2)

        # ③ 生成结果
        card3 = Card("③  生成结果")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.gen_btn = QPushButton("生成授权")
        self.gen_btn.setObjectName("primary")
        self.gen_btn.setMinimumHeight(34)
        self.gen_btn.setMinimumWidth(130)
        self.gen_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(self.gen_btn)

        self.copy_key_btn = QPushButton("复制密钥")
        self.copy_key_btn.setEnabled(False)
        self.copy_key_btn.clicked.connect(self._on_copy_key)
        btn_row.addWidget(self.copy_key_btn)

        self.save_lic_btn = QPushButton("保存为 .lic")
        self.save_lic_btn.setEnabled(False)
        self.save_lic_btn.clicked.connect(self._on_save_lic)
        btn_row.addWidget(self.save_lic_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setObjectName("ghost")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self.clear_btn)

        btn_row.addStretch()
        card3.add_layout(btn_row)

        self.key_edit = QTextEdit()
        self.key_edit.setObjectName("key_output")
        self.key_edit.setReadOnly(True)
        self.key_edit.setMinimumHeight(90)
        self.key_edit.setMaximumHeight(130)
        self.key_edit.setPlaceholderText("生成的密钥字符串会出现在这里...")
        card3.add_widget(self.key_edit)

        v.addWidget(card3)

        # ④ 发送邮件
        card4 = Card("④  发送授权邮件")

        email_row = QHBoxLayout()
        email_row.setSpacing(8)
        lbl_e = QLabel("客户邮箱")
        lbl_e.setObjectName("field_label")
        lbl_e.setFixedWidth(80)
        lbl_e.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        email_row.addWidget(lbl_e)
        self.to_email_edit = QLineEdit()
        self.to_email_edit.setObjectName("mono")
        self.to_email_edit.setPlaceholderText("客户在申请时填写的邮箱")
        email_row.addWidget(self.to_email_edit, 1)

        self.smtp_settings_btn = QPushButton("SMTP 设置")
        self.smtp_settings_btn.clicked.connect(self._on_open_smtp_settings)
        email_row.addWidget(self.smtp_settings_btn)

        card4.add_layout(email_row)

        self.smtp_status_label = QLabel()
        self.smtp_status_label.setObjectName("hint")
        card4.add_widget(self.smtp_status_label)

        self.email_subject_edit = QLineEdit()
        self.email_subject_edit.setText("授权密钥")
        card4.add_layout(field_row("主题", self.email_subject_edit))

        body_lbl = QLabel("正文")
        body_lbl.setObjectName("field_label")
        card4.add_widget(body_lbl)

        self.email_body_edit = QTextEdit()
        self.email_body_edit.setObjectName("email_body")
        self.email_body_edit.setMinimumHeight(220)
        self.email_body_edit.setPlaceholderText(
            "点击上方「生成授权」后，正文会自动填充..."
        )
        card4.add_widget(self.email_body_edit)

        send_row = QHBoxLayout()
        send_row.setSpacing(8)
        send_row.addStretch()

        self.preview_btn = QPushButton("预览")
        self.preview_btn.clicked.connect(self._on_preview_email)
        send_row.addWidget(self.preview_btn)

        self.send_email_btn = QPushButton("📧  发送邮件给客户")
        self.send_email_btn.setObjectName("primary")
        self.send_email_btn.setMinimumHeight(34)
        self.send_email_btn.setMinimumWidth(180)
        self.send_email_btn.setEnabled(False)
        self.send_email_btn.clicked.connect(self._on_send_email)
        send_row.addWidget(self.send_email_btn)

        card4.add_layout(send_row)

        v.addWidget(card4)

        v.addStretch()

        self._refresh_app_info()

    def _refresh_app_info(self):
        app = self._current_app
        name = app.get("name", "未命名")
        prefix = app.get("key_prefix", "")
        email = app.get("contact_email", "")
        extra = app.get("contact_extra", "")

        parts = [f"应用：{name}", f"密钥前缀：{prefix}"]
        if email:
            parts.append(f"联系邮箱：{email}")
        if extra:
            parts.append(extra)

        self.app_info_label.setText("　·　".join(parts))

    def _on_app_changed(self, idx: int):
        apps = self._apps_cfg.get("apps", [])
        if idx < 0 or idx >= len(apps):
            return

        new_app = apps[idx]
        if new_app.get("id") == self._current_app.get("id"):
            return

        self._current_app = new_app
        set_current_app(self._apps_cfg, new_app["id"])

        self._last_lic = None
        self._last_key_string = ""
        self._last_default_name = ""
        self.key_edit.clear()
        self.copy_key_btn.setEnabled(False)
        self.save_lic_btn.setEnabled(False)
        self.send_email_btn.setEnabled(False)
        self.email_body_edit.clear()

        self._refresh_app_info()

    def _on_edit_apps(self):
        path = APPS_CONFIG_IMPORTED_PATH
        if not path.is_file():
            load_apps_config()

        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            QMessageBox.information(
                self, "编辑应用列表",
                f"请手动打开以下文件进行编辑：\n\n{path}\n\n"
                f"（自动打开失败：{e}）"
            )

    def _on_reload_apps(self):
        self._apps_cfg = load_apps_config()
        self._current_app = get_current_app(self._apps_cfg)

        self.app_combo.blockSignals(True)
        self.app_combo.clear()
        self.app_combo.addItems(list_app_names(self._apps_cfg))
        for i, app in enumerate(self._apps_cfg.get("apps", [])):
            if app.get("id") == self._apps_cfg.get("current_app"):
                self.app_combo.setCurrentIndex(i)
                break
        self.app_combo.blockSignals(False)

        self._refresh_app_info()
        QMessageBox.information(self, "已刷新", "应用列表已重新加载")

    def _refresh_smtp_status(self):
        self._smtp_cfg = load_smtp_config()
        if smtp_is_configured(self._smtp_cfg):
            user = self._smtp_cfg.get("user", "")
            server = self._smtp_cfg.get("server", "")
            self.smtp_status_label.setText(f"✅ 已配置：{user} @ {server}")
            self.smtp_status_label.setObjectName("status_ok")
        else:
            self.smtp_status_label.setText(
                "⚠️ SMTP 未配置，请点击右侧「SMTP 设置」"
            )
            self.smtp_status_label.setObjectName("status_err")

        self.smtp_status_label.style().unpolish(self.smtp_status_label)
        self.smtp_status_label.style().polish(self.smtp_status_label)

    def _on_paste_machine(self):
        text = QGuiApplication.clipboard().text().strip()
        if text:
            self.machine_edit.setText(text)

    def _on_period_changed(self, idx):
        self.date_edit.setEnabled(
            self.period_combo.currentText() == "自定义日期"
        )

    def _normalize_machine_code(self, s: str) -> str:
        return "".join(s.split()).upper()

    def _compute_expire(self) -> str:
        txt = self.period_combo.currentText()
        today = datetime.now().date()
        if txt == "永久":
            return "never"
        if txt == "1 天":
            return str(today + timedelta(days=1))
        if txt == "1 个月":
            return str(today + timedelta(days=30))
        if txt == "3 个月":
            return str(today + timedelta(days=90))
        if txt == "6 个月":
            return str(today + timedelta(days=180))
        if txt == "1 年":
            return str(today + timedelta(days=365))
        if txt == "2 年":
            return str(today + timedelta(days=730))
        if txt == "3 年":
            return str(today + timedelta(days=1095))
        return self.date_edit.date().toString("yyyy-MM-dd")

    def _on_clear(self):
        self.machine_edit.clear()
        self.licensee_edit.clear()
        self.edition_combo.setCurrentIndex(0)
        self.period_combo.setCurrentText("1 年")
        self.date_edit.setDate(QDate.currentDate().addYears(1))
        self.note_edit.clear()
        self.key_edit.clear()
        self.to_email_edit.clear()
        self.email_subject_edit.setText("授权密钥")
        self.email_body_edit.clear()
        self._last_lic = None
        self._last_key_string = ""
        self._last_default_name = ""
        self.copy_key_btn.setEnabled(False)
        self.save_lic_btn.setEnabled(False)
        self.send_email_btn.setEnabled(False)

    def _on_generate(self):
        machine = self._normalize_machine_code(self.machine_edit.text())
        if not machine:
            QMessageBox.warning(self, "提示", "请填写客户机器码")
            self.machine_edit.setFocus()
            return

        if len(machine) != 19 or machine.count("-") != 3:
            ans = QMessageBox.question(
                self, "格式提醒",
                f"机器码格式似乎不太对：\n\n{machine}\n\n"
                "正常短码形如：A3F5-9B21-C8E4-7D02（19 字符）\n\n"
                "仍然要生成吗？"
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        payload = {
            "app": self._current_app.get("id", "default"),
            "machine_code": machine,
            "licensee": self.licensee_edit.text().strip() or "匿名",
            "edition": self.edition_combo.currentData() or "standard",
            "expire": self._compute_expire(),
            "issued_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "author": "得鹿梦鱼",
        }
        note = self.note_edit.text().strip()
        if note:
            payload["note"] = note

        try:
            data = json.dumps(payload, ensure_ascii=False,
                              sort_keys=True).encode("utf-8")
            signature = self._private_key.sign(
                data, padding.PKCS1v15(), hashes.SHA256()
            )
            lic = {
                "payload": payload,
                "signature": base64.b64encode(signature).decode("ascii"),
            }
        except Exception as e:
            QMessageBox.critical(self, "签名失败", str(e))
            return

        raw = json.dumps(lic, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
        key_prefix = self._current_app.get("key_prefix", "APP-")
        key_string = key_prefix + base64.b64encode(raw).decode("ascii")

        self._last_lic = lic
        self._last_key_string = key_string
        self._last_default_name = (
            f"license_{machine[:9].replace('-', '')}_"
            f"{datetime.now():%Y%m%d}.lic"
        )

        self.key_edit.setPlainText(key_string)
        self.copy_key_btn.setEnabled(True)
        self.save_lic_btn.setEnabled(True)
        self.send_email_btn.setEnabled(True)

        self._fill_email_template(payload, key_string)

    def _fill_email_template(self, payload: dict, key_string: str):
        name = payload.get("licensee", "客户")
        if name == "匿名":
            name = "您好"

        app_name = self._current_app.get("name", "本软件")
        author_extra = self._current_app.get("contact_extra", "") or "得鹿梦鱼"

        edition_map = {
            "standard":   "标准版",
            "pro":        "专业版",
            "enterprise": "企业版",
            "trial":      "试用版",
        }
        edition = edition_map.get(
            payload.get("edition", "standard"),
            payload.get("edition", "标准版")
        )

        expire = payload.get("expire", "永久")
        expire_disp = "永久" if expire == "never" else expire

        body = f"""{name}：

感谢您支持 {app_name}，您的授权密钥如下。

【授权信息】
  授权对象：{name}
  版本：    {edition}
  有效期：  {expire_disp}

【激活步骤】
  1. 启动软件，在授权对话框中选择对应的授权类型
  2. 将下方密钥完整复制，粘贴到「授权密钥」输入框
  3. 点击「激活」按钮，即可完成授权

【密钥（请完整复制）】
{key_string}

如有任何问题，回复本邮件即可。

{author_extra}
"""
        self.email_body_edit.setPlainText(body)

    def _on_copy_key(self):
        if not self._last_key_string:
            return
        QGuiApplication.clipboard().setText(self._last_key_string)
        QMessageBox.information(
            self, "已复制",
            f"密钥字符串已复制到剪贴板（{len(self._last_key_string)} 字符）。"
        )

    def _on_save_lic(self):
        if not self._last_lic:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存授权文件", self._last_default_name,
            "授权文件 (*.lic)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._last_lic, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", f"授权文件已保存：\n\n{path}")

    def _on_open_smtp_settings(self):
        dlg = SmtpSettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_smtp_status()

    def _on_preview_email(self):
        to_addr = self.to_email_edit.text().strip()
        subject = self.email_subject_edit.text().strip()
        body = self.email_body_edit.toPlainText()

        QMessageBox.information(
            self, "邮件预览",
            f"收件人：{to_addr or '（未填写）'}\n"
            f"主题：  {subject}\n\n"
            f"正文：\n{body[:600]}"
            + ("\n\n...(已省略)" if len(body) > 600 else "")
        )

    def _on_send_email(self):
        if not self._last_lic:
            QMessageBox.warning(self, "提示", "请先生成授权密钥")
            return

        to_addr = self.to_email_edit.text().strip()
        if not to_addr:
            QMessageBox.warning(self, "提示", "请填写客户邮箱")
            self.to_email_edit.setFocus()
            return

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to_addr):
            QMessageBox.warning(self, "邮箱格式错误",
                                "客户邮箱格式不正确，请检查")
            return

        if not smtp_is_configured(self._smtp_cfg):
            QMessageBox.warning(
                self, "SMTP 未配置",
                "请先点击「SMTP 设置」填写邮件服务器信息。"
            )
            return

        subject = self.email_subject_edit.text().strip() or "授权密钥"
        body = self.email_body_edit.toPlainText()
        if not body.strip():
            QMessageBox.warning(self, "提示", "邮件正文不能为空")
            return

        ans = QMessageBox.question(
            self, "确认发送",
            f"确定要发送授权邮件吗？\n\n"
            f"收件人：{to_addr}\n"
            f"主题：  {subject}"
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        self.send_email_btn.setEnabled(False)
        self.send_email_btn.setText("发送中...")
        QApplication.processEvents()

        try:
            ok, msg = send_email_smtp(self._smtp_cfg, to_addr, subject, body)
        except Exception as e:
            ok, msg = False, str(e)

        self.send_email_btn.setEnabled(True)
        self.send_email_btn.setText("📧  发送邮件给客户")

        if ok:
            QMessageBox.information(
                self, "发送成功",
                f"授权邮件已发送至：\n{to_addr}"
            )
        else:
            QMessageBox.critical(
                self, "发送失败",
                f"错误：{msg}\n\n"
                "请检查 SMTP 设置，或直接复制密钥手动发送。"
            )


# ======================================================================
# 入口
# ======================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("License Studio")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setWindowIcon(make_key_icon())

    w = KeygenWindow()
    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()