#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing/dialog.py —— 苹果风授权对话框（通用 / 自包含）
==============================================================
· 3 个授权卡片，徽标在"价格下一行右侧"
· 所有文案 / 尺寸从 config.py 读取
· 机器码一键复制、密钥粘贴/文件导入
· 「申请正式授权」按钮 → 申请对话框
· 激活后不弹确认框，直接进入
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QGuiApplication, QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QFrame,
)

from .config import (
    APP_NAME, KEY_PREFIX, PLANS,
    AUTHOR_NAME, AUTHOR_EMAIL, AUTHOR_EXTRA,
    CONTACT_ACTION, CONTACT_HINT,
    BTN_TRIAL, BTN_ACTIVATE, BTN_REQUEST, BTN_QUIT,
    BTN_COPY, BTN_BROWSE,
    DIALOG_MIN_WIDTH, DIALOG_MAX_WIDTH,
    CARD_WIDTH, CARD_HEIGHT,
    SECTION_MACHINE, SECTION_KEY,
    PLACEHOLDER_KEY,
    MSG_COPY_OK_TITLE, MSG_COPY_OK_BODY,
    MSG_TRIAL_ALREADY_USED, MSG_TRIAL_FAILED_TITLE,
)
from .client import (
    LicenseResult, TrialStatus,
    check_license, check_trial,
    install_license, install_license_string,
    machine_code, start_trial,
)
from .icon_licensing import make_license_icon


# ---------- 配色（苹果浅色，固定，不常改） ----------
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
}


STATUS_TITLES = {
    LicenseResult.NOT_FOUND:      "选择您的授权类型",
    LicenseResult.INVALID_FORMAT: "授权文件格式异常",
    LicenseResult.BAD_SIGNATURE:  "授权文件无效",
    LicenseResult.WRONG_APP:      "密钥不适用于本软件",
    LicenseResult.WRONG_MACHINE:  "授权文件与本机不匹配",
    LicenseResult.EXPIRED:        "授权已过期",
    LicenseResult.TIME_TAMPERED:  "系统时间异常",
    LicenseResult.NO_CRYPTO:      "缺少依赖库",
}


# ============================================================
# 授权卡片
# ============================================================
class PlanCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, plan_key, title, price, subtitle,
                 badge: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("plan_card")
        self.plan_key = plan_key
        self._selected = False
        self._hover = False
        self._disabled = False

        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(0)

        # ---------- 标题 ----------
        self.title_label = QLabel(title)
        self.title_label.setObjectName("plan_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        layout.addSpacing(8)

        # ---------- 价格（居中） ----------
        self.price_label = QLabel(price)
        self.price_label.setObjectName("plan_price")
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.price_label)

        layout.addSpacing(4)

        # ---------- 徽标（独立一行，右对齐；即使没有也占位，保证三卡片高度一致） ----------
        self.badge_label = None
        if badge:
            self.badge_label = QLabel(badge)
            self.badge_label.setObjectName("plan_badge")
            self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            badge_row = QHBoxLayout()
            badge_row.setContentsMargins(0, 0, 0, 0)
            badge_row.setSpacing(0)
            badge_row.addStretch()
            badge_row.addWidget(self.badge_label)
            badge_row.addSpacing(2)
            layout.addLayout(badge_row)
        else:
            # 占位行
            placeholder = QLabel(" ")
            placeholder.setFixedHeight(18)
            layout.addWidget(placeholder)

        layout.addStretch()

        # ---------- 副标题 ----------
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("plan_subtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        self._apply_style()

    def set_selected(self, selected: bool):
        if self._disabled:
            return
        self._selected = selected
        self._apply_style()

    def set_disabled(self, disabled: bool, subtitle_override: str = None):
        self._disabled = disabled
        if subtitle_override is not None:
            self.subtitle_label.setText(subtitle_override)
        if disabled:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
            self._selected = False
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def is_disabled(self) -> bool:
        return self._disabled

    def enterEvent(self, event):
        if not self._disabled:
            self._hover = True
            self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._apply_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._disabled:
            self.clicked.emit(self.plan_key)
        super().mousePressEvent(event)

    def _apply_style(self):
        c = _COL

        if self._disabled:
            border, bg, bw = c["hairline"], "transparent", 1
            title_color = price_color = sub_color = c["fg_mute"]
        elif self._selected:
            border, bg, bw = c["primary"], self._tint(c["primary"], 0.06), 2
            title_color = c["fg"]
            price_color = c["primary"]
            sub_color = c["fg_mid"]
        elif self._hover:
            border, bg, bw = c["hairline"], c["neutral_hover"], 1
            title_color = price_color = c["fg"]
            sub_color = c["fg_mid"]
        else:
            border, bg, bw = c["hairline"], "transparent", 1
            title_color = price_color = c["fg"]
            sub_color = c["fg_mute"]

        badge_bg = self._tint(c["primary"], 0.14)
        badge_fg = c["primary"]
        if self._disabled:
            badge_bg = c["hairline"]
            badge_fg = c["fg_mute"]

        self.setStyleSheet(f"""
            QFrame#plan_card {{
                background-color: {bg};
                border: {bw}px solid {border};
                border-radius: 12px;
            }}
            QFrame#plan_card QLabel {{
                background: transparent;
                border: none;
            }}
            QLabel#plan_title {{
                color: {title_color};
                font-size: 14px;
                font-weight: 600;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QLabel#plan_price {{
                color: {price_color};
                font-size: 28px;
                font-weight: 700;
                letter-spacing: -0.5px;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QLabel#plan_subtitle {{
                color: {sub_color};
                font-size: 11px;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QLabel#plan_badge {{
                color: {badge_fg};
                background-color: {badge_bg};
                border: none;
                border-radius: 8px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 600;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
        """)

    @staticmethod
    def _tint(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"


# ============================================================
# 支持粘贴清理的输入框
# ============================================================
class PasteCleanLineEdit(QLineEdit):
    def insertFromMimeData(self, source):
        text = source.text() if source else ""
        self.insert("".join(text.split()))


# ============================================================
# 主对话框
# ============================================================
class LicenseDialog(QDialog):
    def __init__(self, status: str, info: dict, parent=None):
        super().__init__(parent)
        self.status = status
        self.info = info

        self.setWindowTitle(f"{APP_NAME} · 授权")
        self.setModal(True)
        self.setMinimumWidth(DIALOG_MIN_WIDTH)
        self.setMaximumWidth(DIALOG_MAX_WIDTH)
        self.setWindowIcon(make_license_icon())
        self.setStyleSheet(self._qss())

        self.plan_keys = [p["key"] for p in PLANS]
        self.default_plan = self.plan_keys[0]
        self.selected_plan = self.default_plan
        self._cards: dict = {}

        self._init_ui()
        self._refresh_trial_state()
        self._on_plan_selected(self.selected_plan)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        title_text = STATUS_TITLES.get(self.status, "选择您的授权类型")
        if self.status != LicenseResult.NOT_FOUND:
            reason = self.info.get("reason", "")
            if reason and self.info.get("trial_status") not in (
                TrialStatus.ACTIVE, TrialStatus.NOT_STARTED
            ):
                title_text = STATUS_TITLES.get(self.status, "软件授权")

        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("lic_title")
        layout.addWidget(self.title_label)

        reason = self.info.get("reason", "")
        if reason and self.status != LicenseResult.NOT_FOUND:
            self.reason_label = QLabel(reason)
            self.reason_label.setObjectName("lic_reason")
            self.reason_label.setWordWrap(True)
            layout.addWidget(self.reason_label)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        cards_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for plan in PLANS:
            card = PlanCard(
                plan_key=plan["key"],
                title=plan["title"],
                price=plan["price"],
                subtitle=plan["subtitle"],
                badge=plan.get("badge"),
            )
            card.clicked.connect(self._on_plan_selected)
            cards_row.addWidget(card)
            self._cards[plan["key"]] = card

        layout.addLayout(cards_row)

        divider = QFrame()
        divider.setObjectName("lic_divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        layout.addWidget(self._section_label(SECTION_MACHINE))

        mc_row = QHBoxLayout()
        mc_row.setSpacing(6)
        self.machine_edit = QLineEdit(machine_code())
        self.machine_edit.setReadOnly(True)
        self.machine_edit.setObjectName("lic_machine")
        self.machine_edit.setFont(QFont("Consolas", 11))
        self.machine_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mc_row.addWidget(self.machine_edit, 1)

        self.copy_btn = QPushButton(BTN_COPY)
        self.copy_btn.setFixedWidth(72)
        self.copy_btn.clicked.connect(self._on_copy_machine)
        mc_row.addWidget(self.copy_btn)
        layout.addLayout(mc_row)

        self.key_label = self._section_label(SECTION_KEY)
        layout.addWidget(self.key_label)

        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        self.key_edit = PasteCleanLineEdit()
        self.key_edit.setPlaceholderText(PLACEHOLDER_KEY)
        self.key_edit.setObjectName("lic_key")
        self.key_edit.setMinimumHeight(34)
        key_row.addWidget(self.key_edit, 1)

        self.browse_btn = QPushButton(BTN_BROWSE)
        self.browse_btn.setFixedWidth(72)
        self.browse_btn.clicked.connect(self._on_browse)
        key_row.addWidget(self.browse_btn)
        layout.addLayout(key_row)

        self.contact_label = QLabel()
        self.contact_label.setObjectName("lic_contact")
        self.contact_label.setTextFormat(Qt.TextFormat.RichText)
        self.contact_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.contact_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.contact_label.mousePressEvent = self._on_contact_clicked
        self._refresh_contact_text()
        layout.addWidget(self.contact_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.request_btn = QPushButton(BTN_REQUEST)
        self.request_btn.setMinimumWidth(120)
        self.request_btn.clicked.connect(self._on_request_license)
        btn_row.addWidget(self.request_btn)

        btn_row.addStretch()

        self.quit_btn = QPushButton(BTN_QUIT)
        self.quit_btn.setMinimumWidth(92)
        self.quit_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.quit_btn)

        self.activate_btn = QPushButton(BTN_TRIAL)
        self.activate_btn.setObjectName("primary")
        self.activate_btn.setMinimumWidth(120)
        self.activate_btn.setDefault(True)
        self.activate_btn.clicked.connect(self._on_activate)
        btn_row.addWidget(self.activate_btn)

        layout.addLayout(btn_row)

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("lic_section")
        return lbl

    def _refresh_trial_state(self):
        try:
            st, _ = check_trial()
        except Exception:
            st = TrialStatus.NOT_STARTED

        if st in (TrialStatus.EXPIRED, TrialStatus.TAMPERED):
            trial_card = self._cards.get("trial")
            if trial_card is not None:
                trial_card.set_disabled(True, MSG_TRIAL_ALREADY_USED)
            if self.selected_plan == "trial":
                self.selected_plan = (
                    self.plan_keys[1] if len(self.plan_keys) > 1
                    else self.plan_keys[0]
                )

    def _on_plan_selected(self, plan_key: str):
        if plan_key not in self._cards:
            return
        if self._cards[plan_key].is_disabled():
            return

        self.selected_plan = plan_key

        for k, c in self._cards.items():
            c.set_selected(k == plan_key)

        is_trial = (plan_key == "trial")
        self.key_edit.setEnabled(not is_trial)
        self.browse_btn.setEnabled(not is_trial)
        self.key_label.setEnabled(not is_trial)
        self.activate_btn.setText(BTN_TRIAL if is_trial else BTN_ACTIVATE)

    def _on_copy_machine(self):
        QGuiApplication.clipboard().setText(self.machine_edit.text())
        QMessageBox.information(self, MSG_COPY_OK_TITLE, MSG_COPY_OK_BODY)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择授权文件", "",
            "授权文件 (*.lic *.json);;所有文件 (*)"
        )
        if path:
            self.key_edit.setText(path)
            self._do_activate_from_file(path)

    def _on_activate(self):
        if self.selected_plan == "trial":
            self._do_start_trial()
        else:
            self._do_activate_from_key()

    def _do_start_trial(self):
        ok, msg = start_trial()
        if not ok:
            QMessageBox.warning(self, MSG_TRIAL_FAILED_TITLE, msg)
            self._refresh_trial_state()
            return
        self.accept()

    def _do_activate_from_key(self):
        s = self.key_edit.text().strip()
        if not s:
            QMessageBox.warning(self, "提示",
                                "请先粘贴密钥，或点击「浏览」选择授权文件")
            return
        if Path(s).is_file():
            self._do_activate_from_file(s)
            return

        ok, msg = install_license_string(s)
        if not ok:
            QMessageBox.critical(self, "激活失败", msg)
            return
        self._after_success()

    def _do_activate_from_file(self, path: str):
        ok, msg = install_license(path)
        if not ok:
            QMessageBox.critical(self, "激活失败", msg)
            return
        self._after_success()

    def _after_success(self):
        st, info = check_license()
        if st != LicenseResult.OK:
            QMessageBox.critical(self, "激活失败",
                                 info.get("reason", "授权校验未通过"))
            return
        # 不弹确认框，直接进入
        self.accept()

    def _on_request_license(self):
        from .request_dialog import LicenseRequestDialog
        dlg = LicenseRequestDialog(
            machine_code=self.machine_edit.text(),
            parent=self,
        )
        dlg.exec()

    def _refresh_contact_text(self):
        c = _COL
        parts = []
        if CONTACT_HINT:
            parts.append(
                f'<span style="color:{c["fg_mute"]}; font-size:11px;">'
                f'{CONTACT_HINT}&nbsp;&nbsp;</span>'
            )
        parts.append(
            f'<span style="color:{c["primary"]}; font-size:11px; '
            f'font-weight:500;">{AUTHOR_EMAIL}</span>'
        )
        if AUTHOR_EXTRA:
            parts.append(
                f'<span style="color:{c["fg_mute"]}; font-size:11px;">'
                f'&nbsp;&nbsp;·&nbsp;&nbsp;{AUTHOR_EXTRA}</span>'
            )
        self.contact_label.setText("".join(parts))

    def _on_contact_clicked(self, event):
        if CONTACT_ACTION == "copy":
            QGuiApplication.clipboard().setText(AUTHOR_EMAIL)
            QMessageBox.information(
                self, MSG_COPY_OK_TITLE,
                f"联系邮箱已复制到剪贴板：\n{AUTHOR_EMAIL}"
            )
        else:
            QDesktopServices.openUrl(QUrl(f"mailto:{AUTHOR_EMAIL}"))

    def _qss(self) -> str:
        c = _COL
        return f"""
            QDialog {{
                background-color: {c["bg"]};
                color: {c["fg"]};
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QLabel#lic_title {{
                color: {c["fg"]};
                font-size: 20px; font-weight: 600;
                letter-spacing: -0.3px;
            }}
            QLabel#lic_reason {{
                color: {c["danger"]};
                font-size: 13px;
            }}
            QLabel#lic_section {{
                color: {c["fg_mid"]};
                font-size: 12px; font-weight: 600;
            }}
            QFrame#lic_divider {{
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
            QLineEdit#lic_machine {{
                letter-spacing: 1px;
                font-size: 13px;
            }}
            QLineEdit#lic_key {{
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
            }}
            QLineEdit#lic_key:disabled {{
                background-color: #F5F5F7;
                color: {c["fg_mute"]};
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


# ============================================================
# 一行式入口
# ============================================================
def run_license_check(parent=None) -> bool:
    from .client import check_access
    status, info = check_access()
    if status == LicenseResult.OK:
        return True

    dlg = LicenseDialog(status, info, parent=parent)
    return dlg.exec() == QDialog.DialogCode.Accepted