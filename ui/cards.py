#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/cards.py —— 卡片与小组件集合（苹果风）
"""

from PyQt6.QtWidgets import (
    QFrame, QLabel, QHBoxLayout, QVBoxLayout, QCheckBox,
    QSizePolicy, QDialog, QFormLayout,
    QDoubleSpinBox, QComboBox, QDialogButtonBox,
    QScrollArea, QWidget, QPushButton, QMessageBox,
    QAbstractSpinBox, QProgressBar,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

from theme import Theme, COLORS
from libs.platform_utils import apply_titlebar_theme


CARD_HEIGHT = 60


class ToggleSwitch(QCheckBox):
    def __init__(self, text="", parent=None, accent="#00d722"):
        super().__init__(text, parent)
        self._accent = QColor(accent)
        self._bg_off = QColor("#d8d8d8")
        self._knob = QColor("#ffffff")
        self._text_color = QColor("#363636")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(22)

    def set_theme_colors(self, text_color, bg_off):
        self._text_color = QColor(text_color)
        self._bg_off = QColor(bg_off)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = 30, 16
        x, y = 0, (self.height() - h) // 2

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._accent if self.isChecked() else self._bg_off))
        p.drawRoundedRect(x, y, w, h, h // 2, h // 2)

        knob = h - 4
        kx = x + (w - knob - 2) if self.isChecked() else x + 2
        p.setBrush(QBrush(self._knob))
        p.drawEllipse(kx, y + 2, knob, knob)

        if self.text():
            p.setPen(QPen(self._text_color))
            p.drawText(w + 6, 0, self.width() - w - 6, self.height(),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       self.text())
        p.end()

    def sizeHint(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self.text()) if self.text() else 0
        return QSize(30 + 6 + text_w + 4, 22)


# ============================================
# 🍎 实时值卡片
# ============================================
class RealTimeValueCard(QFrame):
    def __init__(self, theme: Theme):
        super().__init__()
        self.theme = theme
        self.setStyleSheet(theme.realtime_card_qss())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(CARD_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(6)

        self.value_label = QLabel("---")
        self.value_label.setObjectName("rt_value")
        self.value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.unit_label = QLabel("V")
        self.unit_label.setObjectName("rt_unit")
        self.unit_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addStretch()
        layout.addWidget(self.value_label)
        layout.addWidget(self.unit_label)
        layout.addStretch()

    def update_value(self, raw_str, unit="V"):
        self.value_label.setText(raw_str)
        self.unit_label.setText(unit)

    def reset(self, unit="V"):
        self.value_label.setText("---")
        self.unit_label.setText(unit)


# ============================================
# 🍎 统计卡片
# ============================================
class StatCard(QFrame):
    def __init__(self, title, color, theme: Theme, text_color=None):
        super().__init__()
        self.theme = theme
        self.setStyleSheet(theme.stat_card_qss(color, text_color))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(CARD_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(2)

        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("st_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_label = QLabel("---")
        self.value_label.setObjectName("st_value")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumWidth(60)

        layout.addStretch(1)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addStretch(1)

    def update_value(self, raw_str, unit=""):
        self.value_label.setText(f"{raw_str} {unit}" if unit else raw_str)


# ============================================
# 报警配置对话框
# ============================================
class AlarmConfigDialog(QDialog):
    COL_ENABLE_W    = 50
    COL_THRESHOLD_W = 130
    COL_MODE_W      = 90
    COL_DELETE_W    = 44
    COL_SPACING     = 8
    INNER_MARGIN    = 6
    DIALOG_W_MIN    = 400
    DIALOG_W_MAX    = 440
    ROW_HEIGHT      = 30

    def __init__(self, parent=None, initial_rules=None, theme=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("报警设置")
        self.setMinimumWidth(self.DIALOG_W_MIN)
        self.setMaximumWidth(self.DIALOG_W_MAX)

        self._row_widgets = []

        self._init_ui()
        self._apply_theme()

        if initial_rules:
            for r in initial_rules:
                self._add_row(
                    threshold=r.get('threshold', 5.0),
                    mode=r.get('mode', 'above'),
                    enabled=r.get('enabled', True),
                )
        else:
            self._add_row(5.0, 'above', False)

    def showEvent(self, event):
        super().showEvent(event)
        if self.theme is not None:
            apply_titlebar_theme(self, self.theme.is_dark)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.title_label = QLabel("配置报警阈值（可添加多条，独立生效）")
        self.title_label.setObjectName("alarm_title")
        layout.addWidget(self.title_label)

        body = QWidget()
        body.setObjectName("alarm_body")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(4)
        body_layout.addWidget(self._make_header())

        self.divider = QFrame()
        self.divider.setObjectName("alarm_divider")
        self.divider.setFixedHeight(1)
        body_layout.addWidget(self.divider)

        self.rules_container = QWidget()
        self.rules_container.setObjectName("alarm_rules_container")
        self.rules_container.setStyleSheet("background-color: transparent;")
        self.rules_layout = QVBoxLayout(self.rules_container)
        self.rules_layout.setContentsMargins(self.INNER_MARGIN, 4,
                                             self.INNER_MARGIN, 4)
        self.rules_layout.setSpacing(4)
        self.rules_layout.addStretch()

        body_layout.addWidget(self.rules_container)
        layout.addWidget(body)

        self.hint_label = QLabel("触发时会：弹窗提示 + 声音 + 写入 alarm_log.txt")
        self.hint_label.setObjectName("alarm_hint")
        layout.addWidget(self.hint_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.add_btn = QPushButton("+ 添加阈值")
        self.add_btn.clicked.connect(lambda: self._add_row(5.0, 'above', True))
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.add_btn, 1)
        btn_row.addWidget(self.ok_btn, 1)
        btn_row.addWidget(self.cancel_btn, 1)
        layout.addLayout(btn_row)

    def _make_header(self):
        header_widget = QWidget()
        header_widget.setObjectName("alarm_header_row")
        h = QHBoxLayout(header_widget)
        h.setContentsMargins(self.INNER_MARGIN, 4, self.INNER_MARGIN, 4)
        h.setSpacing(self.COL_SPACING)
        columns = [
            ("启用", self.COL_ENABLE_W),
            ("阈值", self.COL_THRESHOLD_W),
            ("条件", self.COL_MODE_W),
            ("删除", self.COL_DELETE_W),
        ]
        for text, width in columns:
            lbl = QLabel(text)
            lbl.setObjectName("alarm_header_label")
            lbl.setFixedWidth(width)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.addWidget(lbl)
        return header_widget

    def _apply_theme(self):
        if self.theme is None:
            return
        t = self.theme

        self.setStyleSheet(f"""
            QDialog {{ background-color: {t.bg}; color: {t.fg}; }}
            QWidget#alarm_body, QWidget#alarm_rules_container,
            QWidget#alarm_header_row {{ background-color: transparent; }}
            QLabel {{ color: {t.fg_mid};
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif; }}
            QLabel#alarm_title {{ color: {t.fg}; font-size: 13px; font-weight: 600; }}
            QLabel#alarm_header_label {{ color: {t.fg_mute}; font-size: 11px; font-weight: 600; }}
            QLabel#alarm_hint {{ color: {t.fg_mute}; font-size: 10px; }}
            QFrame#alarm_divider {{ background-color: {t.hairline}; border: none; }}
            QDoubleSpinBox {{
                background-color: {t.input_bg}; color: {t.input_fg};
                border: 1px solid {t.hairline}; border-radius: 6px;
                padding: 2px 8px; font-size: 12px;
            }}
            QDoubleSpinBox:focus {{ border-color: {t.primary}; }}
            QComboBox {{
                background-color: {t.input_bg}; color: {t.input_fg};
                border: 1px solid {t.hairline}; border-radius: 6px;
                padding: 2px 8px; font-size: 12px;
            }}
            QComboBox:focus {{ border-color: {t.primary}; }}
            QComboBox::drop-down {{ border: none; width: 14px; }}
            QComboBox QAbstractItemView {{
                background-color: {t.bg}; color: {t.fg};
                border: 1px solid {t.hairline};
                border-radius: 8px;
                outline: none;
                padding: 0;
            }}
            QComboBox QAbstractItemView::item {{
                height: 26px;
                padding: 0 12px;
                border: none;
                border-radius: 0;
                color: {t.fg};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {t.primary};
                color: #ffffff;
            }}
            QCheckBox {{ color: {t.fg}; }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border: 1px solid {t.hairline}; border-radius: 4px;
                background-color: {t.input_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {t.primary}; border-color: {t.primary};
            }}
        """)

        self.divider.setStyleSheet(
            f"background-color: {t.hairline}; border: none;"
        )

        self.add_btn.setStyleSheet(t.button_qss('neutral'))
        self.ok_btn.setStyleSheet(t.button_qss('primary'))
        self.cancel_btn.setStyleSheet(t.button_qss('neutral'))

        for r in self._row_widgets:
            self._update_remove_btn_style(r)

    def _update_remove_btn_style(self, row):
        btn = row.get('remove_btn')
        if btn is None or self.theme is None:
            return
        t = self.theme
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.fg_mute};
                border: 1px solid {t.hairline};
                border-radius: 6px;
                font-size: 12px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {t.hairline};
                color: {t.danger};
                border-color: {t.danger};
            }}
        """)

    def _add_row(self, threshold=5.0, mode='above', enabled=True):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(self.INNER_MARGIN, 0, self.INNER_MARGIN, 0)
        row_layout.setSpacing(self.COL_SPACING)

        enable_box = QWidget()
        enable_box.setFixedWidth(self.COL_ENABLE_W)
        enable_box.setFixedHeight(self.ROW_HEIGHT)
        enable_box.setStyleSheet("background-color: transparent;")
        eb = QHBoxLayout(enable_box)
        eb.setContentsMargins(0, 0, 0, 0)
        eb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        enable_cb = QCheckBox()
        enable_cb.setChecked(enabled)
        enable_cb.setFixedSize(18, 18)
        enable_cb.setStyleSheet(
            "QCheckBox { padding: 0; margin: 0; }"
            "QCheckBox::indicator { width: 16px; height: 16px; }"
        )
        eb.addWidget(enable_cb)

        threshold_spin = QDoubleSpinBox()
        threshold_spin.setRange(-1e9, 1e9)
        threshold_spin.setDecimals(4)
        threshold_spin.setValue(threshold)
        threshold_spin.setSingleStep(0.1)
        threshold_spin.setFixedWidth(self.COL_THRESHOLD_W)
        threshold_spin.setFixedHeight(self.ROW_HEIGHT)
        threshold_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        threshold_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        mode_combo = QComboBox()
        mode_combo.addItems(["高于", "低于"])
        mode_combo.setCurrentIndex(0 if mode == 'above' else 1)
        mode_combo.setFixedWidth(self.COL_MODE_W)
        mode_combo.setFixedHeight(self.ROW_HEIGHT)
        mode_combo.setEditable(True)
        mode_combo.lineEdit().setReadOnly(True)
        mode_combo.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_combo.lineEdit().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        mode_combo.lineEdit().setStyleSheet(
            "QLineEdit { background: transparent; border: none; }"
        )
        mode_combo.view().setStyleSheet(
            "QListView::item { padding: 4px 8px; text-align: center; }"
        )

        remove_btn = QPushButton("✕")
        remove_btn.setFixedWidth(self.COL_DELETE_W)
        remove_btn.setFixedHeight(self.ROW_HEIGHT)
        remove_btn.clicked.connect(lambda: self._remove_row(row_widget))

        row_layout.addWidget(enable_box, 0)
        row_layout.addWidget(threshold_spin, 0)
        row_layout.addWidget(mode_combo, 0)
        row_layout.addWidget(remove_btn, 0)

        self.rules_layout.insertWidget(self.rules_layout.count() - 1, row_widget)

        row_info = {
            'widget': row_widget,
            'enable_cb': enable_cb,
            'threshold_spin': threshold_spin,
            'mode_combo': mode_combo,
            'remove_btn': remove_btn,
        }
        self._row_widgets.append(row_info)
        self._update_remove_btn_style(row_info)

    def _remove_row(self, row_widget):
        if len(self._row_widgets) <= 1:
            QMessageBox.information(self, "提示", "至少保留一条规则")
            return
        for i, r in enumerate(self._row_widgets):
            if r['widget'] is row_widget:
                self._row_widgets.pop(i)
                break
        row_widget.setParent(None)
        row_widget.deleteLater()

    def get_values(self):
        result = []
        for r in self._row_widgets:
            result.append({
                'threshold': r['threshold_spin'].value(),
                'mode': 'above' if r['mode_combo'].currentIndex() == 0 else 'below',
                'enabled': r['enable_cb'].isChecked(),
            })
        return result


# ============================================
# 开始记录确认对话框
# ============================================
class RecordConfirmDialog(QDialog):
    def __init__(self, parent=None, theme: Theme = None,
                 record_dir: str = "./data/recordings"):
        super().__init__(parent)
        self.theme = theme
        self.record_dir = record_dir

        self.setWindowTitle("开始记录")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setMaximumWidth(500)

        self._init_ui()
        self._apply_theme()

    def showEvent(self, event):
        super().showEvent(event)
        if self.theme is not None:
            apply_titlebar_theme(self, self.theme.is_dark)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        self.title_label = QLabel("开始记录数据")
        self.title_label.setObjectName("rec_title")
        layout.addWidget(self.title_label)

        self.content_label = QLabel(
            "将从当前时刻开始，持续把每个测量数据追加写入 CSV 文件。\n\n"
            f"·  保存位置：{self.record_dir}/\n"
            "·  每 10 万行自动分卷\n"
            "·  采集期间可暂停 / 继续"
        )
        self.content_label.setObjectName("rec_content")
        self.content_label.setWordWrap(True)
        layout.addWidget(self.content_label)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("开始记录")
        self.ok_btn.setDefault(True)
        self.ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.ok_btn)

        layout.addLayout(btn_row)

    def _apply_theme(self):
        if self.theme is None:
            return
        t = self.theme

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg};
                color: {t.fg};
            }}
            QLabel#rec_title {{
                color: {t.fg};
                font-size: 16px;
                font-weight: 600;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}
            QLabel#rec_content {{
                color: {t.fg_mid};
                font-size: 13px;
                line-height: 1.7;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}
        """)

        self.cancel_btn.setStyleSheet(t.button_qss('neutral'))
        self.ok_btn.setStyleSheet(t.button_qss('primary'))


# ============================================================
# 下载缓存进度对话框
# ============================================================
class BufferProgressDialog(QDialog):
    cancelled = pyqtSignal()

    def __init__(self, parent=None, theme: Theme = None):
        super().__init__(parent)
        self.theme = theme

        self.setWindowTitle("下载缓存")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setMaximumWidth(560)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._init_ui()
        self._apply_theme()

    def showEvent(self, event):
        super().showEvent(event)
        if self.theme is not None:
            apply_titlebar_theme(self, self.theme.is_dark)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(12)

        self.stage_label = QLabel("正在连接仪器...")
        self.stage_label.setObjectName("buf_stage")
        layout.addWidget(self.stage_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("buf_bar")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.count_label = QLabel("")
        self.count_label.setObjectName("buf_count")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.count_label)

        layout.addSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

    def _on_cancel(self):
        self.cancelled.emit()
        self.reject()

    def set_connecting(self):
        self.stage_label.setText("正在连接仪器...")
        self.progress_bar.setRange(0, 0)
        self.count_label.setText("")

    def set_downloading(self):
        self.stage_label.setText("正在下载...")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.count_label.setText("")

    def update_progress(self, done: int, total: int):
        if total <= 0:
            return
        pct = int(done / total * 100)
        self.progress_bar.setValue(pct)
        self.count_label.setText(f"{done:,} / {total:,}")

    def set_total_hint(self, total: int):
        if total > 0:
            self.count_label.setText(f"0 / {total:,}")

    def _apply_theme(self):
        if self.theme is None:
            return
        t = self.theme

        if t.is_dark:
            bar_bg = "rgba(255, 255, 255, 0.08)"
        else:
            bar_bg = "rgba(0, 0, 0, 0.06)"

        text_color = t.fg
        chunk_color = t.primary

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg};
                color: {t.fg};
            }}
            QLabel#buf_stage {{
                color: {t.fg};
                font-size: 15px;
                font-weight: 600;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}
            QLabel#buf_count {{
                color: {t.fg_mute};
                font-size: 11px;
                font-weight: 400;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
                margin-top: 4px;
            }}
            QProgressBar#buf_bar {{
                background-color: {bar_bg};
                color: {text_color};
                border: none;
                border-radius: 11px;
                text-align: center;
                height: 22px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
            }}
            QProgressBar#buf_bar::chunk {{
                background-color: {chunk_color};
                border-radius: 11px;
            }}
        """)

        self.cancel_btn.setStyleSheet(t.button_qss('neutral'))