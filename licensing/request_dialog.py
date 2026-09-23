#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing/request_dialog.py —— 客户申请正式授权（自包含 / 苹果风）
======================================================================
· 填写邮箱 → 生成申请内容（含机器码）
· 邮件发送（mailto） 或 复制内容 → 微信 / QQ 手动发送
· 不依赖外部 theme 模块
"""

import re

from PyQt6.QtCore import Qt, QSettings, QUrl
from PyQt6.QtGui import QGuiApplication, QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QFrame, QTextEdit,
)

from .config import (
    APP_ID, APP_NAME,
    AUTHOR_NAME, AUTHOR_EMAIL, AUTHOR_EXTRA,
    REQUEST_EMAIL_SUBJECT, REQUEST_EMAIL_BODY,
    REQUEST_COPY_TEXT, REQUEST_HINT,
)


# ---------- 配色（与 dialog.py 保持一致） ----------
_COL = {
    "bg":            "#FFFFFF",
    "fg":            "#1D1D1F",
    "fg_mid":        "#48484A",
    "fg_mute":       "#86868B",
    "primary":       "#007AFF",
    "primary_hover": "#0066D6",
    "hairline":      "#E5E5E7",
    "input_bg":      "#F5F5F7",
    "input_focus":   "#FFFFFF",
    "danger":        "#FF3B30",
    "secondary_bg":  "#E8E8ED",
    "secondary_fg":  "#1D1D1F",
    "neutral_hover": "#DCDCE1",
    "code_bg":       "#FAFAFA",
}


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LicenseRequestDialog(QDialog):
    """
    客户填写邮箱，生成授权申请。
    """

    def __init__(self, machine_code: str, parent=None):
        super().__init__(parent)
        self.machine_code = machine_code

        self.setWindowTitle(f"{APP_NAME} · 申请授权")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMaximumWidth(640)
        self.setStyleSheet(self._qss())

        self._init_ui()
        self._restore_email()

    # ---------- UI ----------
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        # 标题
        title = QLabel("申请正式授权")
        title.setObjectName("req_title")
        layout.addWidget(title)

        # 提示
        hint = QLabel(REQUEST_HINT)
        hint.setObjectName("req_hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 邮箱
        lbl_email = QLabel("您的邮箱")
        lbl_email.setObjectName("req_section")
        layout.addWidget(lbl_email)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("例：user@example.com")
        self.email_edit.setMinimumHeight(34)
        self.email_edit.setObjectName("req_email")
        self.email_edit.textChanged.connect(self._refresh_preview)
        layout.addWidget(self.email_edit)

        # 分隔
        divider = QFrame()
        divider.setObjectName("req_divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # 机器码
        lbl_mc = QLabel("机器码")
        lbl_mc.setObjectName("req_section")
        layout.addWidget(lbl_mc)

        mc_row = QHBoxLayout()
        mc_row.setSpacing(6)
        self.machine_edit = QLineEdit(self.machine_code)
        self.machine_edit.setReadOnly(True)
        self.machine_edit.setObjectName("req_machine")
        self.machine_edit.setFont(QFont("Consolas", 11))
        self.machine_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mc_row.addWidget(self.machine_edit, 1)

        self.copy_mc_btn = QPushButton("复制")
        self.copy_mc_btn.setFixedWidth(72)
        self.copy_mc_btn.clicked.connect(self._on_copy_machine)
        mc_row.addWidget(self.copy_mc_btn)
        layout.addLayout(mc_row)

        # 预览
        lbl_preview = QLabel("申请内容预览")
        lbl_preview.setObjectName("req_section")
        layout.addWidget(lbl_preview)

        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setFont(QFont("Microsoft YaHei UI", 10))
        self.preview_edit.setMaximumHeight(150)
        self.preview_edit.setObjectName("req_preview")
        layout.addWidget(self.preview_edit)

        # 联系方式
        parts = [
            f'<span style="color:{_COL["fg_mute"]}; font-size:11px;">'
            f'作者邮箱：</span>'
        ]
        parts.append(
            f'<span style="color:{_COL["primary"]}; font-size:11px; '
            f'font-weight:500;">{AUTHOR_EMAIL}</span>'
        )
        if AUTHOR_EXTRA:
            parts.append(
                f'<span style="color:{_COL["fg_mute"]}; font-size:11px;">'
                f'&nbsp;&nbsp;·&nbsp;&nbsp;{AUTHOR_EXTRA}</span>'
            )

        contact = QLabel("".join(parts))
        contact.setTextFormat(Qt.TextFormat.RichText)
        contact.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(contact)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self.cancel_btn = QPushButton("返回")
        self.cancel_btn.setMinimumWidth(90)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.copy_btn = QPushButton("复制申请内容")
        self.copy_btn.setMinimumWidth(120)
        self.copy_btn.clicked.connect(self._on_copy_request)
        btn_row.addWidget(self.copy_btn)

        self.send_btn = QPushButton("用邮件发送")
        self.send_btn.setObjectName("primary")
        self.send_btn.setMinimumWidth(120)
        self.send_btn.setDefault(True)
        self.send_btn.clicked.connect(self._on_send_email)
        btn_row.addWidget(self.send_btn)

        layout.addLayout(btn_row)

        self._refresh_preview()

    # ---------- 状态 ----------
    def _valid_email(self) -> bool:
        return bool(_EMAIL_RE.match(self.email_edit.text().strip()))

    def _get_email(self) -> str:
        return self.email_edit.text().strip()

    def _refresh_preview(self):
        email = self._get_email() or "（请先填写邮箱）"
        text = REQUEST_COPY_TEXT.format(
            email=email,
            machine_code=self.machine_code,
        )
        self.preview_edit.setPlainText(text)

    def _save_email(self):
        try:
            s = QSettings("LicenseStudio", APP_ID)
            s.setValue("last_email", self._get_email())
        except Exception:
            pass

    def _restore_email(self):
        try:
            s = QSettings("LicenseStudio", APP_ID)
            last = s.value("last_email", "", type=str)
            if last:
                self.email_edit.setText(last)
        except Exception:
            pass

    # ---------- 事件 ----------
    def _on_copy_machine(self):
        QGuiApplication.clipboard().setText(self.machine_code)
        QMessageBox.information(self, "已复制", "机器码已复制到剪贴板")

    def _on_copy_request(self):
        email = self._get_email()
        if not email:
            QMessageBox.warning(self, "提示", "请先填写邮箱")
            self.email_edit.setFocus()
            return
        if not self._valid_email():
            QMessageBox.warning(self, "邮箱格式错误",
                                "请检查邮箱格式是否正确，例如：user@example.com")
            self.email_edit.setFocus()
            return

        text = REQUEST_COPY_TEXT.format(
            email=email,
            machine_code=self.machine_code,
        )
        QGuiApplication.clipboard().setText(text)
        self._save_email()

        QMessageBox.information(
            self, "已复制",
            "申请内容已复制到剪贴板。\n\n"
            f"请打开微信 / QQ，把内容发送给作者：\n{AUTHOR_EMAIL}"
        )
        self.accept()

    def _on_send_email(self):
        email = self._get_email()
        if not email:
            QMessageBox.warning(self, "提示", "请先填写邮箱")
            self.email_edit.setFocus()
            return
        if not self._valid_email():
            QMessageBox.warning(self, "邮箱格式错误",
                                "请检查邮箱格式是否正确，例如：user@example.com")
            self.email_edit.setFocus()
            return

        subject = REQUEST_EMAIL_SUBJECT.format(email=email)
        body = REQUEST_EMAIL_BODY.format(
            email=email,
            machine_code=self.machine_code,
        )

        # 同时复制一份，防止用户没配邮件客户端
        QGuiApplication.clipboard().setText(
            REQUEST_COPY_TEXT.format(
                email=email, machine_code=self.machine_code
            )
        )
        self._save_email()

        try:
            from urllib.parse import quote
            url = (
                f"mailto:{AUTHOR_EMAIL}"
                f"?subject={quote(subject)}"
                f"&body={quote(body)}"
            )
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            QMessageBox.warning(
                self, "无法打开邮件客户端",
                f"错误：{e}\n\n"
                "申请内容已复制到剪贴板，可手动通过微信 / QQ 发送。"
            )
            return

        QMessageBox.information(
            self, "已打开邮件客户端",
            "已为您打开系统邮件客户端，请在邮件窗口中点击「发送」。\n\n"
            "如果没有打开，申请内容也已复制到剪贴板，可手动发送。"
        )
        self.accept()

    # ---------- QSS ----------
    def _qss(self) -> str:
        c = _COL
        return f"""
            QDialog {{
                background-color: {c["bg"]};
                color: {c["fg"]};
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QLabel#req_title {{
                color: {c["fg"]};
                font-size: 18px; font-weight: 600;
            }}
            QLabel#req_hint {{
                color: {c["fg_mid"]};
                font-size: 12px; line-height: 1.7;
            }}
            QLabel#req_section {{
                color: {c["fg_mid"]};
                font-size: 12px; font-weight: 600;
            }}
            QFrame#req_divider {{
                background-color: {c["hairline"]};
                border: none;
            }}
            QLineEdit {{
                background-color: {c["input_bg"]};
                color: {c["fg"]};
                border: 1px solid {c["hairline"]};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                background-color: {c["input_focus"]};
                border: 1px solid {c["primary"]};
            }}
            QLineEdit#req_machine {{
                letter-spacing: 1px;
                font-size: 13px;
            }}
            QTextEdit#req_preview {{
                background-color: {c["code_bg"]};
                color: {c["fg_mid"]};
                border: 1px solid {c["hairline"]};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                line-height: 1.6;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QPushButton {{
                background-color: {c["secondary_bg"]};
                color: {c["secondary_fg"]};
                border: none;
                border-radius: 8px;
                padding: 7px 16px;
                font-size: 13px; font-weight: 500;
                min-height: 18px;
            }}
            QPushButton:hover {{ background-color: {c["neutral_hover"]}; }}
            QPushButton:pressed {{ background-color: #CFCFD5; }}
            QPushButton#primary {{
                background-color: {c["primary"]};
                color: white;
            }}
            QPushButton#primary:hover {{ background-color: {c["primary_hover"]}; }}
        """