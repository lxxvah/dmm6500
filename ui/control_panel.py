#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/control_panel.py —— 左侧控制面板（苹果风）
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

from theme import Theme, COLORS
from ui.cards import ToggleSwitch
from libs.analog_gauge_qt import AnalogGauge, GaugeConfig, GAUGE_PRESETS


class SearchButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setFixedWidth(36)

        self._fg = QColor("#363636")
        self._hover_bg = QColor(0, 0, 0, 0)
        self._hover = False

    def set_theme_colors(self, fg_color, hover_bg_color):
        self._fg = QColor(fg_color)
        self._hover_bg = QColor(hover_bg_color)
        self.update()

    def sizeHint(self):
        return QSize(36, 28)

    def minimumSizeHint(self):
        return QSize(36, 28)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        enabled = self.isEnabled()

        if self._hover and enabled:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(self._hover_bg))
            p.drawRoundedRect(0, 0, w, h, 6, 6)

        color = QColor(self._fg)
        if not enabled:
            color.setAlpha(90)

        if self.text():
            p.setPen(QPen(color))
            p.setFont(self.font())
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
            p.end()
            return

        pen = QPen(color, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.22
        ox = cx - r * 0.30
        oy = cy - r * 0.30

        p.drawEllipse(QPointF(ox, oy), r, r)

        k = 0.707
        p.drawLine(
            QPointF(ox + r * k, oy + r * k),
            QPointF(cx + r * 0.85, cy + r * 0.85),
        )
        p.end()


class ControlPanel(QWidget):
    scan_requested = pyqtSignal(str)
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    mode_changed = pyqtSignal(str)
    capture_pause_toggled = pyqtSignal(bool)
    record_toggled = pyqtSignal(bool)
    alarm_config_requested = pyqtSignal()
    html_report_requested = pyqtSignal()
    buffer_download_requested = pyqtSignal()
    clear_requested = pyqtSignal()

    STATUS_MIN_W = 105

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self._connected = False
        self._paused = False
        self._last_status_kind = None

        self._init_ui()
        self._apply_styles()

        self.set_status("未连接", "normal")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ---------- 连接 ----------
        conn_group = self._make_group("连接")
        conn_vbox = QVBoxLayout()
        conn_vbox.setSpacing(4)

        row_ip = QHBoxLayout()
        row_ip.setSpacing(4)
        self.ip_input = QLineEdit("")
        self.ip_input.setPlaceholderText("IP / VISA")
        self.scan_btn = SearchButton()
        self.scan_btn.clicked.connect(
            lambda: self.scan_requested.emit(self.ip_input.text())
        )
        row_ip.addWidget(self.ip_input, 1)
        row_ip.addWidget(self.scan_btn)
        conn_vbox.addLayout(row_ip)

        row_conn = QHBoxLayout()
        row_conn.setSpacing(6)
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.status_label = QLabel("未连接")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumWidth(self.STATUS_MIN_W)
        row_conn.addWidget(self.connect_btn, 1)
        row_conn.addWidget(self.status_label, 2)
        conn_vbox.addLayout(row_conn)

        conn_group.layout().addLayout(conn_vbox)
        layout.addWidget(conn_group)

        # ---------- 功能 ----------
        func_group = self._make_group("功能")
        func_row = QHBoxLayout()
        func_row.setSpacing(6)

        lbl_func = QLabel("功能")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["DCV", "DCI", "RES2W", "RES4W"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        self.autozero_cb = ToggleSwitch("自动调零", accent=COLORS.ACCENT_GREEN)
        self.autozero_cb.setChecked(True)

        func_row.addWidget(lbl_func)
        func_row.addWidget(self.mode_combo, 1)
        func_row.addWidget(self.autozero_cb, 1)
        func_group.layout().addLayout(func_row)
        layout.addWidget(func_group)

        # ---------- 配置 ----------
        cfg_group = self._make_group("配置")
        cfg_vbox = QVBoxLayout()
        cfg_vbox.setSpacing(4)

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        lbl_term = QLabel("端子")
        self.terminal_combo = QComboBox()
        self.terminal_combo.addItems(["FRONT", "REAR"])

        lbl_nplc = QLabel("NPLC")
        self.nplc_combo = QComboBox()
        self.nplc_combo.addItems(["0.01", "0.1", "1", "10", "100"])
        self.nplc_combo.setCurrentText("1")

        row1.addWidget(lbl_term)
        row1.addWidget(self.terminal_combo, 1)
        row1.addWidget(lbl_nplc)
        row1.addWidget(self.nplc_combo, 1)
        cfg_vbox.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.auto_range_cb = ToggleSwitch("自动量程", accent=COLORS.ACCENT_BLUE)
        self.auto_range_cb.setChecked(True)
        self.auto_range_cb.stateChanged.connect(self._on_auto_range_changed)

        self.range_input = QLineEdit("10")
        self.range_input.setEnabled(False)

        row2.addWidget(self.auto_range_cb, 1)
        row2.addWidget(self.range_input, 1)
        cfg_vbox.addLayout(row2)

        cfg_group.layout().addLayout(cfg_vbox)
        layout.addWidget(cfg_group)

        # ---------- 采集 ----------
        cap_group = self._make_group("采集")
        cap_vbox = QVBoxLayout()
        cap_vbox.setSpacing(4)

        row_cap = QHBoxLayout()
        row_cap.setSpacing(4)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_requested.emit)

        row_cap.addWidget(self.pause_btn, 1)
        row_cap.addWidget(self.clear_btn, 1)
        cap_vbox.addLayout(row_cap)

        cap_group.layout().addLayout(cap_vbox)
        layout.addWidget(cap_group)

        # ---------- 数据 ----------
        data_group = self._make_group("数据")
        data_vbox = QVBoxLayout()
        data_vbox.setSpacing(4)

        row_top = QHBoxLayout()
        row_top.setSpacing(4)
        self.alarm_btn = QPushButton("报警设置")
        self.alarm_btn.clicked.connect(self.alarm_config_requested.emit)
        self.html_report_btn = QPushButton("HTML 报告")
        self.html_report_btn.clicked.connect(self.html_report_requested.emit)
        row_top.addWidget(self.alarm_btn, 1)
        row_top.addWidget(self.html_report_btn, 1)
        data_vbox.addLayout(row_top)

        row_ops = QHBoxLayout()
        row_ops.setSpacing(4)
        self.buffer_btn = QPushButton("下载缓存")
        self.buffer_btn.clicked.connect(self.buffer_download_requested.emit)

        self.record_btn = QPushButton("开始记录")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self._on_record_clicked)

        row_ops.addWidget(self.buffer_btn, 1)
        row_ops.addWidget(self.record_btn, 1)
        data_vbox.addLayout(row_ops)

        data_group.layout().addLayout(data_vbox)
        layout.addWidget(data_group)

        # ---------- 机械表容器 ----------
        # ★ 关键：先 gauge_wrap，再 layout.addStretch()——顺序和原代码一致
        #    隐藏时：data_group + (隐藏 widget 不占位) + addStretch() → 100% 等同原 UI
        #    显示时：data_group + 表盘 + addStretch() → 表盘在数据分组下方
        self.gauge_wrap = QWidget(self)
        self.gauge_wrap.setObjectName("gauge_wrap")
        gw_layout = QVBoxLayout(self.gauge_wrap)
        gw_layout.setContentsMargins(0, 8, 0, 6)
        gw_layout.setSpacing(0)

        gw_layout.addStretch(1)

        self.gauge = AnalogGauge(
            self.gauge_wrap,
            width=220, height=220,          # ★ 表盘尺寸
            preset="voltage_v",
            value_position="left",         # ★ below / left / right / center
        )
        gw_layout.addWidget(self.gauge,
                            alignment=Qt.AlignmentFlag.AlignCenter)

        gw_layout.addStretch(1)

        layout.addStretch(1)
        layout.addWidget(self.gauge_wrap)   # ★ 不带 stretch
        layout.addStretch(2)                 # ★ 原封不动保留

        # 默认隐藏
        self.gauge_wrap.setVisible(False)

    def _make_group(self, title):
        g = QGroupBox(title)
        g.setLayout(QVBoxLayout())
        g.layout().setContentsMargins(10, 14, 10, 10)
        g.layout().setSpacing(6)
        return g

    def _apply_styles(self):
        t = self.theme
        self.setStyleSheet(t.app_qss())

        for w in [self.ip_input, self.range_input]:
            w.setStyleSheet(t.input_qss())
        for w in [self.mode_combo, self.terminal_combo, self.nplc_combo]:
            w.setStyleSheet(t.combo_qss())

        self.scan_btn.set_theme_colors(t.fg_mid, t.neutral_hover)

        self.alarm_btn.setStyleSheet(t.button_qss('neutral'))
        self.html_report_btn.setStyleSheet(t.button_qss('neutral'))
        self.buffer_btn.setStyleSheet(t.button_qss('neutral'))
        self.clear_btn.setStyleSheet(t.button_qss('danger'))

        self._update_connect_btn_style()
        self._update_pause_btn_style()
        self._update_record_btn_style()

        for g in self.findChildren(QGroupBox):
            g.setStyleSheet(t.group_box_qss())

        kind = self._last_status_kind if self._last_status_kind is not None else 'normal'
        self.status_label.setStyleSheet(self.theme.status_badge_qss(kind))

        text_color = t.fg if hasattr(t, 'fg') else "#363636"
        bg_off = t.hairline if hasattr(t, 'hairline') else "#d8d8d8"
        self.auto_range_cb.set_theme_colors(text_color, bg_off)
        self.autozero_cb.set_theme_colors(text_color, bg_off)

    def _update_connect_btn_style(self):
        kind = 'danger' if self._connected else 'primary'
        self.connect_btn.setStyleSheet(self.theme.button_qss(kind))

    def _update_pause_btn_style(self):
        kind = 'success' if self._paused else 'warning'
        self.pause_btn.setStyleSheet(self.theme.button_qss(kind))

    def _update_record_btn_style(self):
        kind = 'danger' if self.record_btn.isChecked() else 'primary'
        self.record_btn.setStyleSheet(self.theme.button_qss(kind))

    def _on_connect_clicked(self):
        if not self._connected:
            self._connected = True
            self.connect_btn.setText("断开")
            self._update_connect_btn_style()
            self.connect_requested.emit()
        else:
            self._connected = False
            self.connect_btn.setText("连接")
            self._update_connect_btn_style()
            self.disconnect_requested.emit()

    def _on_auto_range_changed(self, state):
        self.range_input.setEnabled(not self.auto_range_cb.isChecked())

    def _on_mode_changed(self, index):
        self.mode_changed.emit(self.mode_combo.currentText())

    def _on_pause_clicked(self):
        self._paused = not self._paused
        if self._paused:
            self.pause_btn.setText("开始")
        else:
            self.pause_btn.setText("暂停")
        self._update_pause_btn_style()
        self.capture_pause_toggled.emit(self._paused)

    def _on_record_clicked(self):
        checked = self.record_btn.isChecked()
        self._update_record_btn_style()
        self.record_toggled.emit(checked)

    @property
    def current_mode(self) -> str:
        return self.mode_combo.currentText()

    def get_ip(self) -> str:
        return self.ip_input.text().strip()

    def set_ip(self, ip: str):
        self.ip_input.setText(ip)

    def get_config(self) -> dict:
        mode = self.mode_combo.currentText()
        terminal = "FRONT" if self.terminal_combo.currentIndex() == 0 else "REAR"
        try:
            range_val = float(self.range_input.text())
        except ValueError:
            range_val = 10.0
        return {
            "mode": mode,
            "terminal": terminal,
            "nplc": float(self.nplc_combo.currentText()),
            "auto_range": self.auto_range_cb.isChecked(),
            "range_val": range_val,
            "autozero": self.autozero_cb.isChecked(),
        }

    def set_status(self, text: str, kind: str = 'normal'):
        self.status_label.setText(text)

        if self._last_status_kind != kind:
            self._last_status_kind = kind
            self.status_label.setStyleSheet(self.theme.status_badge_qss(kind))

    def set_connected_state(self, connected: bool):
        self._connected = connected
        self.connect_btn.setText("断开" if connected else "连接")
        self._update_connect_btn_style()
        self.set_pause_btn_enabled(connected)
        if not connected:
            self.set_pause_btn_checked(False)

    def set_pause_btn_enabled(self, enabled: bool):
        self.pause_btn.setEnabled(enabled)

    def set_pause_btn_text(self, text: str):
        self.pause_btn.setText(text)

    def set_pause_btn_checked(self, checked: bool):
        self._paused = checked
        self.pause_btn.setText("开始" if checked else "暂停")
        self._update_pause_btn_style()

    def set_record_btn_state(self, checked: bool, text: str = None):
        self.record_btn.setChecked(checked)
        if text:
            self.record_btn.setText(text)
        self._update_record_btn_style()

    def set_scan_btn_enabled(self, enabled: bool):
        self.scan_btn.setEnabled(enabled)

    def set_scan_btn_text(self, text: str):
        self.scan_btn.setText(text)

    def set_mode_list(self, modes):
        self.mode_combo.blockSignals(True)
        current = self.mode_combo.currentText()
        self.mode_combo.clear()
        self.mode_combo.addItems(list(modes))
        if current in modes:
            self.mode_combo.setCurrentText(current)
        self.mode_combo.blockSignals(False)

    def set_mode_silently(self, mode: str):
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentText(mode)
        self.mode_combo.blockSignals(False)

    # ★ 强化显隐：显式触发 layout 重算
    def set_gauge_visible(self, visible: bool) -> None:
        print(f"[面板] set_gauge_visible({visible})", flush=True)
        self.gauge_wrap.setVisible(visible)
        if visible:
            self.gauge_wrap.raise_()
            self.gauge_wrap.updateGeometry()
            self.updateGeometry()
            self.gauge.update()

    def switch_theme(self, theme: Theme):
        self.theme = theme
        self._apply_styles()