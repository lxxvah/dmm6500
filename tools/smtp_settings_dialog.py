#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/smtp_settings_dialog.py —— SMTP 配置窗口
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QMessageBox, QSpinBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from tools.smtp_config import (
    load_config, save_config, PRESETS, test_connection,
)


class SmtpSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SMTP 邮件设置")
        self.setModal(True)
        self.setMinimumWidth(480)

        self.cfg = load_config()
        self._init_ui()
        self._load_into_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        # 预设
        row0 = QHBoxLayout()
        row0.addWidget(QLabel("预设："))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self._on_preset)
        row0.addWidget(self.preset_combo, 1)
        layout.addLayout(row0)

        # 服务器
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("SMTP 服务器："))
        self.server_edit = QLineEdit()
        row1.addWidget(self.server_edit, 1)
        layout.addLayout(row1)

        # 端口 + SSL
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("端口："))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(465)
        self.port_spin.setFixedWidth(90)
        row2.addWidget(self.port_spin)

        self.ssl_cb = QCheckBox("使用 SSL")
        self.ssl_cb.setChecked(True)
        row2.addWidget(self.ssl_cb)
        row2.addStretch()
        layout.addLayout(row2)

        # 用户名
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("邮箱账号："))
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("例：xxx@qq.com")
        row3.addWidget(self.user_edit, 1)
        layout.addLayout(row3)

        # 密码
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("授权码："))
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setPlaceholderText(
            "QQ / 163 邮箱使用「授权码」，不是登录密码"
        )
        row4.addWidget(self.pwd_edit, 1)

        self.show_pwd_cb = QCheckBox("显示")
        self.show_pwd_cb.toggled.connect(
            lambda on: self.pwd_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on
                else QLineEdit.EchoMode.Password
            )
        )
        row4.addWidget(self.show_pwd_cb)
        layout.addLayout(row4)

        # 发件人显示名
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("发件人名称："))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("收件人看到的发件人名字")
        row5.addWidget(self.name_edit, 1)
        layout.addLayout(row5)

        # 帮助
        help_text = QLabel(
            '<span style="color:#898989; font-size: 11px;">'
            'QQ 邮箱授权码获取：设置 → 账户 → POP3/SMTP服务 → 开启 → 生成授权码<br>'
            '163 邮箱类似；Gmail 需用「应用专用密码」'
            '</span>'
        )
        help_text.setTextFormat(Qt.TextFormat.RichText)
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        layout.addSpacing(6)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self._on_test)
        btn_row.addWidget(self.test_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        layout.addLayout(btn_row)

    # ---------- 载入 / 保存 ----------
    def _load_into_ui(self):
        self.server_edit.setText(self.cfg.get("server", ""))
        self.port_spin.setValue(int(self.cfg.get("port", 465)))
        self.ssl_cb.setChecked(bool(self.cfg.get("use_ssl", True)))
        self.user_edit.setText(self.cfg.get("user", ""))
        self.pwd_edit.setText(self.cfg.get("password", ""))
        self.name_edit.setText(self.cfg.get("sender_name", ""))

        # 自动匹配预设
        for name, preset in PRESETS.items():
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
            "password":    self.pwd_edit.text(),       # 授权码不要 strip
            "sender_name": self.name_edit.text().strip(),
        }

    # ---------- 事件 ----------
    def _on_preset(self, name: str):
        preset = PRESETS.get(name)
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
        self.repaint()

        try:
            ok, msg = test_connection(cfg)
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
            QMessageBox.warning(
                self, "提示",
                "服务器、账号、授权码都必须填写。"
            )
            return
        save_config(cfg)
        QMessageBox.information(self, "已保存", "SMTP 配置已保存")
        self.accept()