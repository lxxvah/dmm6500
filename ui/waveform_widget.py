#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
waveform_widget.py —— 通用波形显示模块（苹果风改造）
======================================================
· 苹果风图例卡片 / 游标浮动标签 / 右键菜单
· set_y_label 内部缓存，避免重排
· X 轴滚轮缩放：用户手动缩放后自动停止跟随
· Y 轴 Ctrl+滚轮缩放：标记 user_zoomed，停止自动居中
· 左键拖动平移：同时停止 X 跟随与 Y 自动居中
· 右键菜单「功能介绍」→ 通知上层打开 AboutDialog
· 十字线交点浮动标签：60ms 节流 + 完整避让（边界/曲线/游标）
· 十字线本体与标签都只在鼠标位于绘图区时显示
  （用 QTimer 主动轮询，解决 sigMouseMoved 在离开时不触发的问题）
"""

import csv
import time
import tempfile
import os
import math
from collections import OrderedDict
from typing import List

import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QFileDialog, QMessageBox, QGraphicsItem,
    QMenu, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPoint, QPointF, QSize
from PyQt6.QtGui import (
    QPixmap, QGuiApplication, QFont, QPainterPath, QPainter,
    QColor, QPen, QBrush, QFontMetricsF, QIcon, QCursor
)

import pyqtgraph as pg
import pyqtgraph.exporters


TOGGLE_STYLE = 'chip'


THEMES = {
    'light': {
        'plot_bg': '#ffffff', 'grid': '#d8d8d8', 'grid_alpha': 0.3,
        'axis_text': '#363636', 'legend_bg': (255, 255, 255, 200),
        'crosshair': '#888888',
        'btn_fg': '#080808', 'btn_grid': '#d8d8d8', 'btn_hover': '#ececec',
        'btn_checked_bg': '#080808', 'btn_checked_fg': '#ffffff',
        'combo_bg': '#ffffff', 'combo_fg': '#080808',
        'label_color': '#363636', 'hint_color': '#898989',
        'menu_bg': '#ffffff', 'menu_fg': '#1a1a1a',
        'menu_border': '#d8d8d8', 'menu_hover': '#f0f0f0',
        'menu_sep': '#e8e8e8', 'menu_accent': '#007AFF',
        'toggle_on_bg': '#E5F0FF', 'toggle_on_fg': '#007AFF',
        'toggle_on_border': '#007AFF',
        'legend_bg_css':     'rgba(255, 255, 255, 0.72)',
        'legend_border_css': 'rgba(0, 0, 0, 0.06)',
        'legend_fg':         '#1c1c1e',
    },
    'dark': {
        'plot_bg': '#0a0a0a', 'grid': '#3a3a3a', 'grid_alpha': 0.6,
        'axis_text': '#c0c0c0', 'legend_bg': (26, 26, 26, 200),
        'crosshair': '#c0c0c0',
        'btn_fg': '#f0f0f0', 'btn_grid': '#3a3a3a', 'btn_hover': '#2a2a2a',
        'btn_checked_bg': '#f0f0f0', 'btn_checked_fg': '#1a1a1a',
        'combo_bg': '#252525', 'combo_fg': '#f0f0f0',
        'label_color': '#c0c0c0', 'hint_color': '#898989',
        'menu_bg': '#1a1a1a', 'menu_fg': '#f0f0f0',
        'menu_border': '#3a3a3a', 'menu_hover': '#2a2a2a',
        'menu_sep': '#3a3a3a', 'menu_accent': '#007AFF',
        'toggle_on_bg': '#122A44', 'toggle_on_fg': '#0A84FF',
        'toggle_on_border': '#0A84FF',
        'legend_bg_css':     'rgba(28, 28, 30, 0.72)',
        'legend_border_css': 'rgba(255, 255, 255, 0.08)',
        'legend_fg':         '#f5f5f7',
    },
    'nord': {
        'plot_bg': '#2e3440', 'grid': '#4c566a', 'grid_alpha': 0.5,
        'axis_text': '#d8dee9', 'legend_bg': (46, 52, 64, 220),
        'crosshair': '#d8dee9',
        'btn_fg': '#eceff4', 'btn_grid': '#4c566a', 'btn_hover': '#3b4252',
        'btn_checked_bg': '#eceff4', 'btn_checked_fg': '#2e3440',
        'combo_bg': '#3b4252', 'combo_fg': '#eceff4',
        'label_color': '#d8dee9', 'hint_color': '#7b88a1',
        'menu_bg': '#2e3440', 'menu_fg': '#eceff4',
        'menu_border': '#4c566a', 'menu_hover': '#3b4252',
        'menu_sep': '#4c566a', 'menu_accent': '#007AFF',
        'toggle_on_bg': '#3B5360', 'toggle_on_fg': '#88C0D0',
        'toggle_on_border': '#88C0D0',
        'legend_bg_css':     'rgba(59, 66, 82, 0.75)',
        'legend_border_css': 'rgba(216, 222, 233, 0.10)',
        'legend_fg':         '#eceff4',
    },
    'solarized_light': {
        'plot_bg': '#fdf6e3', 'grid': '#eee8d5', 'grid_alpha': 0.5,
        'axis_text': '#586e75', 'legend_bg': (253, 246, 227, 220),
        'crosshair': '#93a1a1',
        'btn_fg': '#073642', 'btn_grid': '#eee8d5', 'btn_hover': '#eee8d5',
        'btn_checked_bg': '#073642', 'btn_checked_fg': '#fdf6e3',
        'combo_bg': '#fdf6e3', 'combo_fg': '#073642',
        'label_color': '#586e75', 'hint_color': '#93a1a1',
        'menu_bg': '#fdf6e3', 'menu_fg': '#073642',
        'menu_border': '#eee8d5', 'menu_hover': '#eee8d5',
        'menu_sep': '#eee8d5', 'menu_accent': '#007AFF',
        'toggle_on_bg': '#DBE9F4', 'toggle_on_fg': '#268BD2',
        'toggle_on_border': '#268BD2',
        'legend_bg_css':     'rgba(253, 246, 227, 0.78)',
        'legend_border_css': 'rgba(7, 54, 66, 0.08)',
        'legend_fg':         '#073642',
    },
    'dracula': {
        'plot_bg': '#1e1f29', 'grid': '#44475a', 'grid_alpha': 0.5,
        'axis_text': '#f8f8f2', 'legend_bg': (40, 42, 54, 220),
        'crosshair': '#bd93f9',
        'btn_fg': '#f8f8f2', 'btn_grid': '#44475a', 'btn_hover': '#44475a',
        'btn_checked_bg': '#bd93f9', 'btn_checked_fg': '#282a36',
        'combo_bg': '#44475a', 'combo_fg': '#f8f8f2',
        'label_color': '#f8f8f2', 'hint_color': '#6272a4',
        'menu_bg': '#1e1f29', 'menu_fg': '#f8f8f2',
        'menu_border': '#44475a', 'menu_hover': '#44475a',
        'menu_sep': '#44475a', 'menu_accent': '#007AFF',
        'toggle_on_bg': '#3D3255', 'toggle_on_fg': '#BD93F9',
        'toggle_on_border': '#BD93F9',
        'legend_bg_css':     'rgba(40, 42, 54, 0.75)',
        'legend_border_css': 'rgba(248, 248, 242, 0.10)',
        'legend_fg':         '#f8f8f2',
    },
}

CHECK_BLUE = '#007AFF'
CHECK_BOX_BORDER = '#C0C0C0'

DEFAULT_PALETTE = [
    '#7a3dff', '#ff6b00', '#3b89ff', '#00d722',
    '#ed52cb', '#ffae13', '#ee1d36', '#146ef5',
]

LINE_STYLES = {
    '实线': Qt.PenStyle.SolidLine,
    '虚线': Qt.PenStyle.DashLine,
    '点线': Qt.PenStyle.DotLine,
    '点划线': Qt.PenStyle.DashDotLine,
}


def _parse_css_color(css, fallback=(255, 255, 255, 255)) -> QColor:
    css = (css or "").strip()
    if css.startswith("rgba"):
        nums = css[css.find("(") + 1: css.rfind(")")].split(",")
        r, g, b = (int(x.strip()) for x in nums[:3])
        a = float(nums[3].strip())
        return QColor(r, g, b, int(a * 255))
    if css.startswith("rgb"):
        nums = css[css.find("(") + 1: css.rfind(")")].split(",")
        r, g, b = (int(x.strip()) for x in nums[:3])
        return QColor(r, g, b)
    if css.startswith("#"):
        return QColor(css)
    return QColor(*fallback)


def _wheel_delta_y(ev) -> int:
    """
    兼容取出滚轮事件的竖直增量。
      · QGraphicsSceneWheelEvent → 只有 delta()
      · QWheelEvent              → angleDelta().y()
    """
    angle = getattr(ev, "angleDelta", None)
    if callable(angle):
        try:
            return int(angle().y())
        except Exception:
            pass
    try:
        return int(ev.delta())
    except Exception:
        return 0


def make_check_icon(checked: bool, size: int = 16) -> QIcon:
    pix_off = QPixmap(size, size)
    pix_off.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix_off)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(CHECK_BOX_BORDER), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(2, 2, size - 4, size - 4, 3, 3)
    p.end()

    pix_on = QPixmap(size, size)
    pix_on.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix_on)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(CHECK_BLUE)))
    p.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    pen = QPen(QColor("#ffffff"), 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(4.0, 8.5)
    path.lineTo(7.0, 11.0)
    path.lineTo(12.0, 5.0)
    p.drawPath(path)
    p.end()

    icon = QIcon()
    icon.addPixmap(pix_off, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(pix_on, QIcon.Mode.Normal, QIcon.State.On)
    return icon


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strings = []
        for v in values:
            if v < 0:
                strings.append("")
            elif v < 60:
                strings.append(f"{v:.1f}s")
            elif v < 3600:
                m = int(v // 60); s = int(v % 60)
                strings.append(f"{m:02d}:{s:02d}")
            else:
                h = int(v // 3600); m = int((v % 3600) // 60); s = int(v % 60)
                strings.append(f"{h:02d}:{m:02d}:{s:02d}")
        return strings


# ============================================
# 自定义 ViewBox
# ============================================
class CustomViewBox(pg.ViewBox):
    """
    · 滚轮 → 缩放 X 轴；缩放后停止 X 自动跟随
    · Ctrl + 滚轮 → 缩放 Y 轴；标记 user_zoomed，停止 Y 自动居中
    · 左键拖动 → 平移；同时停止 X 自动跟随 + Y 自动居中
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = None

    def wheelEvent(self, ev, axis=None):
        delta = _wheel_delta_y(ev)
        if delta == 0:
            ev.ignore()
            return
        factor = 0.85 if delta > 0 else 1.18
        modifiers = ev.modifiers()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            yr = self.viewRange()[1]
            c = (yr[0] + yr[1]) / 2
            h = (yr[1] - yr[0]) / 2 * factor
            self.setYRange(c - h, c + h, padding=0)
            if self._owner is not None:
                self._owner.y_user_zoomed = True
        else:
            xr = self.viewRange()[0]
            c = (xr[0] + xr[1]) / 2
            h = (xr[1] - xr[0]) / 2 * factor
            self.setXRange(c - h, c + h, padding=0)
            if self._owner is not None:
                self._owner.x_auto_follow = False

        ev.accept()

    def mouseDragEvent(self, ev, axis=None):
        if ev.button() == Qt.MouseButton.LeftButton and self._owner is not None:
            self._owner.x_auto_follow = False
            self._owner.y_user_zoomed = True
        super().mouseDragEvent(ev, axis)


# ============================================
# 🍎 苹果风格图例卡片
# ============================================
class AppleLegendCard(QWidget):
    RADIUS = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._text = ""
        self._dot_color = QColor("#7a3dff")
        self._fg = QColor("#1c1c1e")
        self._bg = QColor(255, 255, 255, 180)
        self._border = QColor(0, 0, 0, 15)
        self._font = QFont("PingFang SC", 9)
        self._font.setWeight(QFont.Weight.Medium)

    def set_entry(self, name: str, color: str):
        self._text = str(name)
        self._dot_color = QColor(color)
        self._recalc_size()
        self.update()

    def _recalc_size(self):
        fm = QFontMetricsF(self._font)
        w = int(fm.horizontalAdvance(self._text)) + 46
        h = int(fm.height()) + 14
        self.setFixedSize(max(w, 80), max(h, 28))

    def apply_theme(self, t: dict):
        self._bg     = _parse_css_color(t.get('legend_bg_css'),     (255, 255, 255, 184))
        self._border = _parse_css_color(t.get('legend_border_css'), (0, 0, 0, 15))
        self._fg     = _parse_css_color(t.get('legend_fg'),         (28, 28, 30))
        self.update()

    def paintEvent(self, event):
        if not self._text:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)

        p.setPen(QPen(self._border, 1))
        p.setBrush(QBrush(self._bg))
        p.drawRoundedRect(rect, self.RADIUS, self.RADIUS)

        dot_r = 5
        dot_cx = rect.left() + 14
        dot_cy = rect.center().y()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._dot_color))
        p.drawEllipse(QPointF(dot_cx, dot_cy), dot_r, dot_r)

        p.setPen(QPen(self._fg))
        p.setFont(self._font)
        text_rect = QRectF(
            rect.left() + 14 + dot_r * 2 + 8,
            rect.top(),
            rect.width() - 14 - dot_r * 2 - 8 - 14,
            rect.height()
        )
        p.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._text
        )
        p.end()


# ============================================
# 🍎 游标/十字线浮动标签（毛玻璃 + 左侧彩色竖条）
# ============================================
class CursorBadge(pg.GraphicsObject):
    def __init__(self, bg_color="#ed52cb", fg_color="#ffffff", accent_color=None):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

        color = accent_color if accent_color is not None else bg_color
        self.accent = QColor(color)

        self._card_bg     = QColor(255, 255, 255, 220)
        self._card_border = QColor(0, 0, 0, 15)
        self._fg          = QColor("#1c1c1e")

        self.text = ""
        self.lines: List[str] = []

        self._font = QFont("Consolas", 9)
        self._padding_h = 12
        self._padding_v = 5
        self._line_spacing = 2
        self._radius = 10
        self._accent_w = 3
        self._accent_gap = 10

        self._bounds = QRectF(0, 0, 0, 0)
        self._path = QPainterPath()
        self._accent_path = QPainterPath()

    def set_accent(self, color):
        """单独更新左侧彩色竖条颜色（十字线跟随主题时需要）"""
        self.accent = QColor(color)
        self.update()

    def apply_theme(self, t: dict):
        self._card_bg = _parse_css_color(t.get('legend_bg_css'), (255, 255, 255, 184))
        self._card_bg.setAlpha(min(255, int(self._card_bg.alpha() * 1.15)))
        self._card_border = _parse_css_color(t.get('legend_border_css'), (0, 0, 0, 15))
        self._fg = _parse_css_color(t.get('legend_fg'), (28, 28, 30))
        self.update()

    def setLines(self, lines: List[str]):
        if lines == self.lines:
            return
        self.prepareGeometryChange()
        self.lines = list(lines)
        self.text = "\n".join(lines)
        self._recalc_geometry()
        self.update()

    def setText(self, text: str):
        lines = text.split("\n") if text else []
        self.setLines(lines)

    def _recalc_geometry(self):
        if not self.lines:
            self._bounds = QRectF(0, 0, 0, 0)
            self._path = QPainterPath()
            self._accent_path = QPainterPath()
            return

        fm = QFontMetricsF(self._font)
        line_h = fm.height()
        n = len(self.lines)
        max_w = max(fm.horizontalAdvance(s) for s in self.lines)

        w = (self._padding_h + self._accent_w + self._accent_gap
             + max_w + self._padding_h)
        h = n * line_h + (n - 1) * self._line_spacing + 2 * self._padding_v

        self._bounds = QRectF(-w / 2, -h, w, h)
        self._path = QPainterPath()
        self._path.addRoundedRect(self._bounds, self._radius, self._radius)

        acc_x = self._bounds.x() + self._padding_h
        acc_y0 = self._bounds.y() + self._padding_v + 1
        acc_y1 = self._bounds.bottom() - self._padding_v - 1
        acc_h = max(acc_y1 - acc_y0, 4)
        r = self._accent_w / 2
        self._accent_path = QPainterPath()
        self._accent_path.addRoundedRect(
            QRectF(acc_x, acc_y0, self._accent_w, acc_h), r, r
        )

    def size_px(self):
        if not self.lines:
            return (0, 0)
        fm = QFontMetricsF(self._font)
        line_h = fm.height()
        n = len(self.lines)
        max_w = max(fm.horizontalAdvance(s) for s in self.lines)
        w = (self._padding_h + self._accent_w + self._accent_gap
             + max_w + self._padding_h)
        h = n * line_h + (n - 1) * self._line_spacing + 2 * self._padding_v
        return w, h

    def boundingRect(self):
        if self._path.isEmpty() or not self.lines:
            return QRectF(0, 0, 0, 0)
        return self._bounds

    def paint(self, painter, option, widget=None):
        if not self.lines:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(self._card_border, 1))
        painter.setBrush(QBrush(self._card_bg))
        painter.drawPath(self._path)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.accent))
        painter.drawPath(self._accent_path)

        painter.setPen(QPen(self._fg))
        painter.setFont(self._font)

        fm = QFontMetricsF(self._font)
        line_h = fm.height()

        x_left = (self._bounds.x() + self._padding_h
                  + self._accent_w + self._accent_gap)
        y_top = self._bounds.y() + self._padding_v
        text_w = (self._bounds.width() - self._padding_h * 2
                  - self._accent_w - self._accent_gap)

        for i, line in enumerate(self.lines):
            y_line = y_top + i * (line_h + self._line_spacing)
            rect = QRectF(x_left, y_line, text_w, line_h)
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                line
            )


class CurveInfo:
    def __init__(self, curve_id, name, color, width, style):
        self.curve_id = curve_id; self.name = name
        self.color = color; self.width = width; self.style = style
        self.x_data = []; self.y_data = []
        self.plot_item = None; self.visible = True
        self.alarm_threshold = None; self.alarm_mode = None
        self.alarm_active = False
        self._x_np = None; self._y_np = None

    def append(self, x, y):
        self.x_data.append(x); self.y_data.append(y)

    def get_np(self):
        if self._x_np is None or len(self._x_np) != len(self.x_data):
            self._x_np = np.asarray(self.x_data, dtype=np.float64)
            self._y_np = np.asarray(self.y_data, dtype=np.float64)
        return self._x_np, self._y_np

    def clear(self):
        self.x_data.clear(); self.y_data.clear()
        self._x_np = None; self._y_np = None


class ToolbarChip(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setObjectName("toolbar_chip")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class ToolbarSwitch(QPushButton):
    SW_W = 32; SW_H = 16; GAP = 8; PAD_L = 4; PAD_R = 4

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._base_text = text
        self.setCheckable(True)
        self.setObjectName("toolbar_switch")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)

        self._text_color = QColor("#363636")
        self._text_color_on = QColor("#007AFF")
        self._switch_on_bg = QColor("#007AFF")
        self._switch_off_bg = QColor("#C0C0C0")
        self._knob_color = QColor("#ffffff")
        self._hover_bg = QColor(0, 0, 0, 0)
        self._hover = False
        self.setMouseTracking(True)

    def set_theme_colors(self, theme_dict):
        self._text_color = QColor(theme_dict['btn_fg'])
        self._text_color_on = QColor(theme_dict['toggle_on_fg'])
        self._switch_on_bg = QColor(theme_dict['toggle_on_fg'])
        self._switch_off_bg = QColor(theme_dict['btn_grid'])
        self._knob_color = QColor("#ffffff")
        self._hover_bg = QColor(theme_dict['btn_hover'])
        self.update()

    def sizeHint(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._base_text)
        w = self.PAD_L + text_w + self.GAP + self.SW_W + self.PAD_R
        return QSize(w, 26)

    def minimumSizeHint(self):
        return self.sizeHint()

    def enterEvent(self, e):
        self._hover = True; self.update(); super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False; self.update(); super().leaveEvent(e)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self._hover:
            bg = QColor(self._hover_bg); bg.setAlpha(120)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg))
            painter.drawRoundedRect(0, 0, w, h, 5, 5)

        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._base_text)
        text_color = self._text_color_on if self.isChecked() else self._text_color
        painter.setPen(QPen(text_color))
        painter.drawText(
            self.PAD_L, 0, text_w + 4, h,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._base_text
        )

        sw_x = self.PAD_L + text_w + self.GAP
        sw_y = (h - self.SW_H) // 2
        track_color = self._switch_on_bg if self.isChecked() else self._switch_off_bg
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(sw_x, sw_y, self.SW_W, self.SW_H,
                                self.SW_H // 2, self.SW_H // 2)

        knob_size = self.SW_H - 4
        if self.isChecked():
            knob_x = sw_x + (self.SW_W - knob_size - 2)
        else:
            knob_x = sw_x + 2
        painter.setBrush(QBrush(self._knob_color))
        painter.drawEllipse(knob_x, sw_y + 2, knob_size, knob_size)


def ToolbarToggle(text: str, parent=None):
    if TOGGLE_STYLE == 'switch':
        return ToolbarSwitch(text, parent)
    return ToolbarChip(text, parent)


class WaveformWidget(QWidget):
    cursor_moved = pyqtSignal(float, float)
    alarm_triggered = pyqtSignal(str, float)
    save_data_requested = pyqtSignal()
    about_requested = pyqtSignal()

    MENU_CONFIG = [
        ("reset",      "复位",           True),
        ("window",     "窗口",           True),
        ("cursor",     "游标",           True),
        ("grid",       "网格",           False),
        ("crosshair",  "十字线",         False),
        ("save_img",   "保存图形",       False),
        ("save_data",  "保存数据",       False),
        ("y_center",   "Y轴自动居中",    True),
        ("copy",       "复制截图",       False),
    ]

    # 十字线浮动标签的节流间隔（秒）
    _CH_THROTTLE_S = 0.06
    # 鼠标离场检测的轮询间隔（毫秒）
    _LEAVE_CHECK_MS = 80

    def __init__(self, parent=None, theme='light'):
        super().__init__(parent)
        self.curves = OrderedDict()
        self._curve_counter = 0
        self.paused = False
        self.x_window = 300.0
        self.x_auto_follow = True
        self.y_auto_center = True
        self.y_user_zoomed = False
        self.theme = theme if theme in THEMES else 'light'

        self._y_label_cache = (None, None)

        self._menu_visible = {key: default for key, _, default in self.MENU_CONFIG}
        self._show_all_state = False

        self._func_state = {
            'cursor': False,
            'grid': True,
            'crosshair': False,
            'y_center': True,
        }

        # ✅ 十字线相关状态
        self._ch_last_ts = 0.0
        self._ch_last_pos = None
        self._cursor_rects_cache = []
        self._mouse_in_plot = False

        self._init_ui()
        self._init_plot()
        self._init_crosshair()
        self._init_cursors()

        # 十字线标签节流定时器（单次触发）
        self._ch_timer = QTimer(self)
        self._ch_timer.setSingleShot(True)
        self._ch_timer.timeout.connect(self._flush_crosshair_badge)

        # ✅ 鼠标离场检测定时器：sigMouseMoved 在鼠标离开场景后不再触发，
        #    必须靠轮询 QCursor.pos() 才能检测到"离开绘图区"
        self._leave_timer = QTimer(self)
        self._leave_timer.setInterval(self._LEAVE_CHECK_MS)
        self._leave_timer.timeout.connect(self._check_mouse_in_plot)
        self._leave_timer.start()

        self.set_theme(self.theme)

        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.plot_widget.customContextMenuRequested.connect(
            self._show_context_menu
        )

        self.plot_widget.setXRange(0, 300, padding=0)
        self.plot_widget.setYRange(-1, 1, padding=0)

        self._apply_menu_visibility()
        self._apply_func_state()

    def _init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(4, 4, 4, 4)
        main.setSpacing(4)

        self.toolbar_container = QWidget()
        self.toolbar_container.setObjectName("waveform_toolbar")

        toolbar = QHBoxLayout(self.toolbar_container)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)

        self.pause_btn = QPushButton("波形暂停")
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.pause_btn.setObjectName("toolbar_btn")
        toolbar.addWidget(self.pause_btn)

        self.reset_btn = QPushButton("波形复位")
        self.reset_btn.clicked.connect(self.reset_view)
        self.reset_btn.setObjectName("toolbar_btn")
        toolbar.addWidget(self.reset_btn)

        self.window_label = QLabel("窗口:")
        self.window_label.setObjectName("toolbar_label")
        toolbar.addWidget(self.window_label)

        self.window_combo = QComboBox()
        self.window_combo.addItems(
            ["5 秒", "10 秒", "30 秒", "1 分钟", "5 分钟", "10 分钟", "全部"]
        )
        self.window_combo.setCurrentText("5 分钟")
        self.window_combo.currentTextChanged.connect(self._on_window_changed)
        self.window_combo.setObjectName("toolbar_combo")
        toolbar.addWidget(self.window_combo)

        self.cursor_btn = ToolbarToggle("游标")
        self.cursor_btn.toggled.connect(self._on_func_cursor_toggled)
        toolbar.addWidget(self.cursor_btn)

        self.grid_btn = ToolbarToggle("网格")
        self.grid_btn.setChecked(True)
        self.grid_btn.toggled.connect(self._on_func_grid_toggled)
        toolbar.addWidget(self.grid_btn)

        self.crosshair_btn = ToolbarToggle("十字线")
        self.crosshair_btn.toggled.connect(self._on_func_crosshair_toggled)
        toolbar.addWidget(self.crosshair_btn)

        self.y_center_btn = ToolbarToggle("Y轴居中")
        self.y_center_btn.setChecked(True)
        self.y_center_btn.toggled.connect(self._on_func_y_center_toggled)
        toolbar.addWidget(self.y_center_btn)

        toolbar.addStretch()

        self.save_img_btn = QPushButton("保存图形")
        self.save_img_btn.clicked.connect(lambda: self.save_image())
        self.save_img_btn.setObjectName("toolbar_btn")
        toolbar.addWidget(self.save_img_btn)

        self.save_data_btn = QPushButton("保存数据")
        self.save_data_btn.clicked.connect(self.save_data_requested.emit)
        self.save_data_btn.setObjectName("toolbar_btn")
        toolbar.addWidget(self.save_data_btn)

        self.copy_btn = QPushButton("复制截图")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setObjectName("toolbar_btn")
        toolbar.addWidget(self.copy_btn)

        main.addWidget(self.toolbar_container)

    def _init_plot(self):
        pg.setConfigOptions(antialias=True)

        time_axis = TimeAxisItem(orientation='bottom')
        y_axis = pg.AxisItem(orientation='left')

        viewbox = CustomViewBox()
        viewbox._owner = self

        self.plot_widget = pg.PlotWidget(
            viewBox=viewbox,
            axisItems={'bottom': time_axis, 'left': y_axis}
        )
        self.plot_widget.setBackground('#ffffff')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', '读数', color='#363636', size='11px')
        self.plot_widget.setLabel('bottom', '时间', color='#363636', size='11px')
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.getPlotItem().vb.setMouseMode(pg.ViewBox.PanMode)
        self.plot_widget.enableAutoRange(axis='y', enable=False)
        self.plot_widget.enableAutoRange(axis='x', enable=False)

        self.legend_card = AppleLegendCard(self.plot_widget)
        self.legend_card.move(60, 14)
        self.legend_card.hide()
        self.legend_card.raise_()

        self.layout().addWidget(self.plot_widget, stretch=1)

    def _init_crosshair(self):
        self.vline = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen('#888888', width=1, style=Qt.PenStyle.DashLine)
        )
        self.hline = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen('#888888', width=1, style=Qt.PenStyle.DashLine)
        )
        self.vline.setVisible(False)
        self.hline.setVisible(False)
        self.plot_widget.addItem(self.vline, ignoreBounds=True)
        self.plot_widget.addItem(self.hline, ignoreBounds=True)
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _init_cursors(self):
        self.cursor1 = pg.InfiniteLine(
            angle=90, movable=True, pen=pg.mkPen('#ed52cb', width=2)
        )
        self.cursor2 = pg.InfiniteLine(
            angle=90, movable=True, pen=pg.mkPen('#3b89ff', width=2)
        )
        self.cursor1.setValue(0); self.cursor2.setValue(60)
        self.cursor1.setVisible(False); self.cursor2.setVisible(False)
        self.plot_widget.addItem(self.cursor1, ignoreBounds=True)
        self.plot_widget.addItem(self.cursor2, ignoreBounds=True)

        self.badge1 = CursorBadge(bg_color="#ed52cb")
        self.badge2 = CursorBadge(bg_color="#3b89ff")
        self.badge1.setZValue(100); self.badge2.setZValue(100)
        self.badge1.setVisible(False); self.badge2.setVisible(False)
        self.plot_widget.addItem(self.badge1, ignoreBounds=True)
        self.plot_widget.addItem(self.badge2, ignoreBounds=True)

        self.cursor1.sigPositionChanged.connect(self._update_cursor_labels)
        self.cursor2.sigPositionChanged.connect(self._update_cursor_labels)

        self.crosshair_badge = CursorBadge(bg_color="#888888")
        self.crosshair_badge.setZValue(90)
        self.crosshair_badge.setVisible(False)
        self.plot_widget.addItem(self.crosshair_badge, ignoreBounds=True)

    def _apply_menu_visibility(self):
        mv = self._menu_visible
        self.pause_btn.setVisible(True)
        self.reset_btn.setVisible(mv['reset'])
        self.save_img_btn.setVisible(mv['save_img'])
        self.save_data_btn.setVisible(mv['save_data'])
        self.copy_btn.setVisible(mv['copy'])

        self.window_label.setVisible(mv['window'])
        self.window_combo.setVisible(mv['window'])
        self.cursor_btn.setVisible(mv['cursor'])
        self.grid_btn.setVisible(mv['grid'])
        self.crosshair_btn.setVisible(mv['crosshair'])
        self.y_center_btn.setVisible(mv['y_center'])

    def _apply_func_state(self):
        fs = self._func_state

        self.cursor1.setVisible(fs['cursor'])
        self.cursor2.setVisible(fs['cursor'])
        self.badge1.setVisible(fs['cursor'])
        self.badge2.setVisible(fs['cursor'])
        if fs['cursor']:
            xr = self.plot_widget.viewRange()[0]
            self.cursor1.setValue(xr[0] + (xr[1] - xr[0]) * 0.33)
            self.cursor2.setValue(xr[0] + (xr[1] - xr[0]) * 0.66)
            self._update_cursor_labels()
        else:
            self.badge1.setText("")
            self.badge2.setText("")
            self._cursor_rects_cache = []

        t = THEMES.get(self.theme, THEMES['light'])
        alpha = t['grid_alpha'] if fs['grid'] else 0.0
        self.plot_widget.showGrid(x=fs['grid'], y=fs['grid'], alpha=alpha)

        # 十字线本体：功能开 且 鼠标在绘图区内
        show_ch = fs['crosshair'] and self._mouse_in_plot
        self.vline.setVisible(show_ch)
        self.hline.setVisible(show_ch)
        if not show_ch:
            self.crosshair_badge.setVisible(False)

        self.y_auto_center = fs['y_center']
        if fs['y_center']:
            self.y_user_zoomed = False

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(self._context_menu_qss())

        all_checked = all(self._menu_visible.values())
        act_show_all = menu.addAction("显示全部")
        act_show_all.setCheckable(True)
        act_show_all.setChecked(all_checked)
        act_show_all.setIcon(make_check_icon(all_checked))
        act_show_all.triggered.connect(self._action_show_all_toggle)

        act_about = menu.addAction("功能介绍")
        act_about.triggered.connect(lambda: self.about_requested.emit())

        menu.addSeparator()

        self._menu_actions = {}
        for key, label, _ in self.MENU_CONFIG:
            act = menu.addAction(label)
            act.setCheckable(True)
            checked = self._menu_visible[key]
            act.setChecked(checked)
            act.setIcon(make_check_icon(checked))
            act.triggered.connect(
                lambda chk, k=key: self._action_toggle_menu(k, chk)
            )
            self._menu_actions[key] = act

        global_pos = self.plot_widget.mapToGlobal(pos)
        menu.exec(global_pos)

    def _action_show_all_toggle(self, checked: bool):
        for key, _, _ in self.MENU_CONFIG:
            self._menu_visible[key] = checked
        self._apply_menu_visibility()

    def _action_toggle_menu(self, key: str, checked: bool):
        self._menu_visible[key] = checked
        self._apply_menu_visibility()

    def _context_menu_qss(self) -> str:
        t = THEMES.get(self.theme, THEMES['light'])

        if self.theme in ('dark', 'nord', 'dracula'):
            menu_bg     = "rgba(28, 28, 30, 0.88)"
            menu_border = "rgba(255, 255, 255, 0.10)"
        else:
            menu_bg     = "rgba(255, 255, 255, 0.90)"
            menu_border = "rgba(0, 0, 0, 0.06)"

        fg = t['menu_fg']
        sep = t['menu_sep']
        accent = t['menu_accent']

        return f"""
            QMenu {{
                background-color: {menu_bg};
                color: {fg};
                border: 1px solid {menu_border};
                border-radius: 10px;
                padding: 6px 6px;
                font-family: 'Microsoft YaHei UI', 'Inter', system-ui, sans-serif;
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 7px 24px 7px 36px;
                border-radius: 8px;
                margin: 1px 2px;
                min-width: 160px;
            }}
            QMenu::item:selected {{
                background-color: {accent};
                color: #ffffff;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {sep};
                margin: 6px 12px;
            }}
            QMenu::indicator {{
                width: 0px;
                height: 0px;
                margin: 0px;
            }}
            QMenu::icon {{
                margin-left: 10px;
                width: 16px;
                height: 16px;
            }}
        """

    def _on_func_cursor_toggled(self, checked: bool):
        self._func_state['cursor'] = checked
        self.cursor1.setVisible(checked)
        self.cursor2.setVisible(checked)
        self.badge1.setVisible(checked)
        self.badge2.setVisible(checked)
        if checked:
            xr = self.plot_widget.viewRange()[0]
            self.cursor1.setValue(xr[0] + (xr[1] - xr[0]) * 0.33)
            self.cursor2.setValue(xr[0] + (xr[1] - xr[0]) * 0.66)
            self._update_cursor_labels()
        else:
            self.badge1.setText("")
            self.badge2.setText("")
            self._cursor_rects_cache = []

    def _on_func_grid_toggled(self, checked: bool):
        self._func_state['grid'] = checked
        t = THEMES.get(self.theme, THEMES['light'])
        alpha = t['grid_alpha'] if checked else 0.0
        self.plot_widget.showGrid(x=checked, y=checked, alpha=alpha)

    def _on_func_crosshair_toggled(self, checked: bool):
        self._func_state['crosshair'] = checked

        if checked:
            # ✅ 立即主动检测一次（用户刚打开开关时的位置）
            self._check_mouse_in_plot()
        else:
            self.vline.setVisible(False)
            self.hline.setVisible(False)
            self.crosshair_badge.setVisible(False)
            self._mouse_in_plot = False

    def _on_func_y_center_toggled(self, checked: bool):
        self._func_state['y_center'] = checked
        self.y_auto_center = checked
        if checked:
            self.y_user_zoomed = False

    def add_curve(self, name, color=None, width=2, style='实线'):
        self._curve_counter += 1
        curve_id = f"c{self._curve_counter}"
        if color is None:
            color = DEFAULT_PALETTE[(self._curve_counter - 1) % len(DEFAULT_PALETTE)]
        info = CurveInfo(curve_id, name, color, width, style)
        pen = pg.mkPen(color=color, width=width,
                       style=LINE_STYLES.get(style, Qt.PenStyle.SolidLine))
        info.plot_item = self.plot_widget.plot([], [], pen=pen, name=name)
        self.curves[curve_id] = info

        if hasattr(self, 'legend_card'):
            self.legend_card.set_entry(name, color)
            self.legend_card.show()
            self.legend_card.raise_()

        return curve_id

    def remove_curve(self, curve_id):
        if curve_id not in self.curves: return
        info = self.curves[curve_id]
        try: self.plot_widget.removeItem(info.plot_item)
        except Exception: pass
        del self.curves[curve_id]

    def append_data(self, curve_id, x, y):
        if self.paused or curve_id not in self.curves: return
        info = self.curves[curve_id]
        info.append(float(x), float(y))

    def append_batch(self, curve_id, xs, ys):
        if self.paused or curve_id not in self.curves: return
        info = self.curves[curve_id]
        for x, y in zip(xs, ys):
            info.append(float(x), float(y))

    def refresh(self):
        if self.paused: return

        for info in self.curves.values():
            if not info.visible or len(info.x_data) == 0: continue
            xs, ys = info.get_np()
            n = len(xs)
            if n > 20000:
                step = n // 10000
                xs_draw = xs[::step]; ys_draw = ys[::step]
                if (n - 1) % step != 0:
                    xs_draw = np.append(xs_draw, xs[-1])
                    ys_draw = np.append(ys_draw, ys[-1])
                info.plot_item.setData(xs_draw, ys_draw)
            else:
                info.plot_item.setData(xs, ys)

        if self.x_auto_follow and self.x_window > 0:
            last_x = 0.0
            for info in self.curves.values():
                if info.visible and len(info.x_data) > 0:
                    x = info.x_data[-1]
                    if x > last_x: last_x = x
            x_right = max(last_x, self.x_window)
            x_left = max(0.0, x_right - self.x_window)
            self.plot_widget.setXRange(x_left, x_right, padding=0)

        if self.y_auto_center and not self.y_user_zoomed:
            self._auto_center_y()

        if self._func_state['cursor']:
            self._update_cursor_labels()

    def _auto_center_y(self):
        xr = self.plot_widget.viewRange()[0]
        x_min, x_max = xr[0], xr[1]

        y_min, y_max = None, None
        for info in self.curves.values():
            if not info.visible or len(info.y_data) == 0: continue
            xs, ys = info.get_np()
            if len(xs) == 0: continue
            i0 = np.searchsorted(xs, x_min, side='left')
            i1 = np.searchsorted(xs, x_max, side='right')
            if i1 <= i0:
                w_min = float(np.min(ys)); w_max = float(np.max(ys))
            else:
                window_ys = ys[i0:i1]
                w_min = float(np.min(window_ys)); w_max = float(np.max(window_ys))
            if y_min is None or w_min < y_min: y_min = w_min
            if y_max is None or w_max > y_max: y_max = w_max

        if y_min is None or y_max is None: return

        y_range = y_max - y_min
        y_center = (y_min + y_max) / 2

        yr = self.plot_widget.viewRange()[1]
        cur_lo, cur_hi = yr[0], yr[1]

        outside = (y_min > cur_hi) or (y_max < cur_lo)
        if outside:
            half = max(y_range / 2 * 1.15, 0.5)
            nice_half = math.ceil(half / 0.5) * 0.5
            self.plot_widget.setYRange(y_center - nice_half,
                                        y_center + nice_half, padding=0)
            return

        if y_range < 0.5: return

        half = y_range / 2 * 1.15
        nice_half = math.ceil(half / 0.5) * 0.5
        self.plot_widget.setYRange(y_center - nice_half,
                                    y_center + nice_half, padding=0)

    def clear_data(self, curve_id=None):
        if curve_id is None:
            for info in self.curves.values():
                info.clear(); info.plot_item.setData([], [])
        elif curve_id in self.curves:
            info = self.curves[curve_id]
            info.clear(); info.plot_item.setData([], [])

    def set_y_label(self, text='读数', unit=''):
        if not hasattr(self, '_y_label_cache'):
            self._y_label_cache = (None, None)

        if self._y_label_cache == (text, unit):
            return

        self._y_label_cache = (text, unit)
        self.plot_widget.setLabel('left', text, units=unit,
                                  color='#363636', size='11px')

    def set_x_window(self, seconds):
        self.x_window = seconds
        self.x_auto_follow = (seconds > 0)

    def pause(self, paused=True):
        self.paused = paused
        self.pause_btn.setChecked(paused)
        self.pause_btn.setText("波形继续" if paused else "波形暂停")

    def reset_view(self):
        self.y_auto_center = True
        self.y_user_zoomed = False
        self._func_state['y_center'] = True
        self.y_center_btn.setChecked(True)
        self.x_auto_follow = True
        self.plot_widget.setYRange(-1, 1, padding=0)
        self.refresh()

    def set_curve_visibility(self, curve_id, visible):
        if curve_id in self.curves:
            info = self.curves[curve_id]
            info.visible = visible
            info.plot_item.setVisible(visible)

    def set_curve_color(self, curve_id, color):
        if curve_id in self.curves:
            info = self.curves[curve_id]
            info.color = color
            pen = pg.mkPen(color=color, width=info.width,
                           style=LINE_STYLES.get(info.style, Qt.PenStyle.SolidLine))
            info.plot_item.setPen(pen)

    def set_curve_style(self, curve_id, width=None, style=None):
        if curve_id in self.curves:
            info = self.curves[curve_id]
            if width is not None: info.width = width
            if style is not None: info.style = style
            pen = pg.mkPen(color=info.color, width=info.width,
                           style=LINE_STYLES.get(info.style, Qt.PenStyle.SolidLine))
            info.plot_item.setPen(pen)

    def set_alarm(self, curve_id, threshold, mode='above'):
        if curve_id in self.curves:
            info = self.curves[curve_id]
            info.alarm_threshold = threshold
            info.alarm_mode = mode

    def set_theme(self, theme):
        if theme not in THEMES:
            theme = 'light'
        self.theme = theme
        self._apply_plot_theme(theme)
        self._apply_toolbar_theme(theme)

    def _apply_plot_theme(self, theme):
        t = THEMES.get(theme, THEMES['light'])

        self.plot_widget.setBackground(t['plot_bg'])
        for axis_name in ('left', 'bottom'):
            ax = self.plot_widget.getAxis(axis_name)
            ax.setPen(t['grid'])
            ax.setTextPen(t['axis_text'])

        alpha = t['grid_alpha'] if self._func_state['grid'] else 0.0
        self.plot_widget.showGrid(x=self._func_state['grid'],
                                   y=self._func_state['grid'],
                                   alpha=alpha)

        if hasattr(self, 'legend_card'):
            self.legend_card.apply_theme(t)

        if hasattr(self, 'badge1'):
            self.badge1.apply_theme(t)
        if hasattr(self, 'badge2'):
            self.badge2.apply_theme(t)

        if hasattr(self, 'crosshair_badge'):
            self.crosshair_badge.apply_theme(t)
            self.crosshair_badge.set_accent(t['crosshair'])

        self.vline.setPen(pg.mkPen(t['crosshair'], width=1,
                                    style=Qt.PenStyle.DashLine))
        self.hline.setPen(pg.mkPen(t['crosshair'], width=1,
                                    style=Qt.PenStyle.DashLine))

        if (self._func_state.get('crosshair')
                and self._mouse_in_plot
                and self._ch_last_pos is not None):
            self._flush_crosshair_badge()

    def _apply_toolbar_theme(self, theme):
        t = THEMES.get(theme, THEMES['light'])

        if TOGGLE_STYLE == 'switch':
            for btn in [self.cursor_btn, self.grid_btn,
                        self.crosshair_btn, self.y_center_btn]:
                if isinstance(btn, ToolbarSwitch):
                    btn.set_theme_colors(t)

        self.toolbar_container.setStyleSheet(f"""
            #waveform_toolbar QPushButton#toolbar_btn {{
                background-color: transparent;
                color: {t['btn_fg']};
                border: 1px solid {t['btn_grid']};
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 500;
            }}
            #waveform_toolbar QPushButton#toolbar_btn:hover {{
                background-color: {t['btn_hover']};
            }}
            #waveform_toolbar QPushButton#toolbar_btn:checked {{
                background-color: {t['btn_checked_bg']};
                color: {t['btn_checked_fg']};
                border-color: {t['btn_checked_bg']};
            }}

            #waveform_toolbar QPushButton#toolbar_chip {{
                background-color: transparent;
                color: {t['hint_color']};
                border: none;
                border-radius: 12px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 500;
            }}
            #waveform_toolbar QPushButton#toolbar_chip:hover {{
                background-color: {t['btn_hover']};
            }}
            #waveform_toolbar QPushButton#toolbar_chip:checked {{
                background-color: {t['toggle_on_bg']};
                color: {t['toggle_on_fg']};
                font-weight: 600;
            }}

            #waveform_toolbar QPushButton#toolbar_switch {{
                background-color: transparent;
                border: none;
                padding: 0;
            }}

            #waveform_toolbar QComboBox#toolbar_combo {{
                background-color: {t['combo_bg']};
                color: {t['combo_fg']};
                border: 1px solid {t['btn_grid']};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
            }}
            #waveform_toolbar QComboBox#toolbar_combo::drop-down {{ border: none; }}
            #waveform_toolbar QComboBox#toolbar_combo::down-arrow {{ image: none; }}
            #waveform_toolbar QComboBox#toolbar_combo QAbstractItemView {{
                background-color: {t['combo_bg']};
                color: {t['combo_fg']};
                border: 1px solid {t['btn_grid']};
                border-radius: 10px;
                outline: none;
                padding: 0;
            }}
            #waveform_toolbar QComboBox#toolbar_combo QAbstractItemView::item {{
                height: 26px;
                padding: 0 12px;
                border: none;
                border-radius: 0;
                color: {t['combo_fg']};
            }}
            #waveform_toolbar QComboBox#toolbar_combo QAbstractItemView::item:hover {{
                background-color: {t['btn_hover']};
            }}
            #waveform_toolbar QComboBox#toolbar_combo QAbstractItemView::item:selected {{
                background-color: {t['menu_accent']};
                color: #ffffff;
            }}

            #waveform_toolbar QLabel#toolbar_label {{
                font-size: 11px; color: {t['label_color']};
            }}
            #waveform_toolbar QLabel#hint_label {{
                font-size: 10px; color: {t['hint_color']};
            }}
        """)

    def reapply_toolbar_style(self):
        self._apply_toolbar_theme(self.theme)

    # ---------- 鼠标移动 ----------
    def _on_mouse_moved(self, pos):
        # 鼠标在场景内触发；离开时不会触发，离开检测交给 _leave_timer
        if not self._func_state['crosshair']:
            return

        try:
            inside = self.plot_widget.sceneBoundingRect().contains(pos)
        except Exception:
            return
        if not inside:
            return

        mp = self.plot_widget.getPlotItem().vb.mapSceneToView(pos)

        # 若之前状态是"离开"，直接在这里翻转为"进入"，避免等到下一次定时器
        if not self._mouse_in_plot:
            self._mouse_in_plot = True
            self.vline.setVisible(True)
            self.hline.setVisible(True)

        self.vline.setPos(mp.x())
        self.hline.setPos(mp.y())
        self.cursor_moved.emit(mp.x(), mp.y())
        self._schedule_crosshair_badge(mp.x(), mp.y())

    # ---------- 鼠标离场轮询 ----------
    def _check_mouse_in_plot(self):
        """
        sigMouseMoved 只在鼠标位于场景内触发；鼠标离开后收不到任何通知，
        因此需要主动轮询 QCursor.pos()，判断其是否还在 ViewBox 内。
        """
        if not self._func_state['crosshair']:
            # 功能关着时只需保证状态位不残留
            if self._mouse_in_plot:
                self._mouse_in_plot = False
            return

        try:
            global_pos = QCursor.pos()
            local_pos = self.plot_widget.mapFromGlobal(global_pos)
            scene_pos = self.plot_widget.mapToScene(local_pos)
            vb_rect = self.plot_widget.getPlotItem().vb.sceneBoundingRect()
            inside = vb_rect.contains(QPointF(scene_pos))
        except Exception:
            inside = False

        if inside == self._mouse_in_plot:
            return

        self._mouse_in_plot = inside

        if inside:
            # 顺手用当前鼠标位置刷新一次 _ch_last_pos，让 badge 立刻到位
            try:
                view_pos = self.plot_widget.getPlotItem().vb.mapSceneToView(
                    QPointF(scene_pos)
                )
                self._ch_last_pos = (view_pos.x(), view_pos.y())
            except Exception:
                pass

            self.vline.setVisible(True)
            self.hline.setVisible(True)

            if self._ch_last_pos is not None:
                x, y = self._ch_last_pos
                self.vline.setPos(x)
                self.hline.setPos(y)
                self._flush_crosshair_badge()
        else:
            self.vline.setVisible(False)
            self.hline.setVisible(False)
            self.crosshair_badge.setVisible(False)

    # ---------- 十字线浮动标签（节流 + 完整避让） ----------
    def _schedule_crosshair_badge(self, x: float, y: float):
        """节流入口：每 60ms 至多重排一次；鼠标停下后必刷新一次。"""
        self._ch_last_pos = (x, y)
        now = time.monotonic()
        elapsed = now - self._ch_last_ts
        if elapsed >= self._CH_THROTTLE_S:
            self._ch_last_ts = now
            self._flush_crosshair_badge()
        elif not self._ch_timer.isActive():
            remaining_ms = int((self._CH_THROTTLE_S - elapsed) * 1000) + 1
            self._ch_timer.start(remaining_ms)

    def _flush_crosshair_badge(self):
        if not self._func_state['crosshair']:
            return
        if not self._mouse_in_plot:
            return
        if self._ch_last_pos is None:
            return

        self._ch_last_ts = time.monotonic()

        x, y = self._ch_last_pos

        xr = self.plot_widget.viewRange()[0]
        yr = self.plot_widget.viewRange()[1]
        x_rng = xr[1] - xr[0] if xr[1] > xr[0] else 1.0
        y_rng = yr[1] - yr[0] if yr[1] > yr[0] else 1.0

        vb = self.plot_widget.getPlotItem().vb
        rect_px = vb.sceneBoundingRect()
        view_w_px = max(rect_px.width(), 1)
        view_h_px = max(rect_px.height(), 1)

        lines = [f"X = {x:.4f}s", f"Y = {y:.6g}"]
        self.crosshair_badge.setLines(lines)

        w_px, h_px = self.crosshair_badge.size_px()
        w = w_px / view_w_px * x_rng
        h = h_px / view_h_px * y_rng

        occupied = list(self._cursor_rects_cache)

        self._auto_place(
            self.crosshair_badge, x, y, w, h,
            xr, yr, None, None,
            prefer='above', occupied=occupied
        )
        self.crosshair_badge.setVisible(True)

    def _interp_y_at(self, xs, ys, x):
        if len(xs) == 0: return None
        if x <= xs[0]: return float(ys[0])
        if x >= xs[-1]: return float(ys[-1])
        i = int(np.searchsorted(xs, x))
        x0, x1 = xs[i - 1], xs[i]
        y0, y1 = ys[i - 1], ys[i]
        if x1 == x0: return float(y0)
        return float(y0 + (y1 - y0) * (x - x0) / (x1 - x0))

    def _curve_crosses_rect(self, xs, ys, rect):
        if xs is None or len(xs) == 0: return False
        x1, y1, x2, y2 = rect
        i0 = np.searchsorted(xs, x1, side='left')
        i1 = np.searchsorted(xs, x2, side='right')
        if i1 <= i0: return False
        seg = ys[i0:i1]
        return bool(np.any((seg >= y1) & (seg <= y2)))

    def _update_cursor_labels(self):
        if not self._func_state['cursor']:
            return

        xr = self.plot_widget.viewRange()[0]
        yr = self.plot_widget.viewRange()[1]
        x_rng = xr[1] - xr[0] if xr[1] > xr[0] else 1.0
        y_rng = yr[1] - yr[0] if yr[1] > yr[0] else 1.0

        vb = self.plot_widget.getPlotItem().vb
        rect_px = vb.sceneBoundingRect()
        view_w_px = max(rect_px.width(), 1)
        view_h_px = max(rect_px.height(), 1)

        xs_ref, ys_ref = None, None
        for info in self.curves.values():
            if info.visible and len(info.x_data) > 0:
                xs_ref, ys_ref = info.get_np()
                break

        x1 = self.cursor1.value()
        x2 = self.cursor2.value()
        y1 = self._interp_y_at(xs_ref, ys_ref, x1) if xs_ref is not None else None
        y2 = self._interp_y_at(xs_ref, ys_ref, x2) if xs_ref is not None else None

        lines1: List[str] = []
        if y1 is not None:
            lines1.append(f"X1 = {x1:.4f}s")
            lines1.append(f"Y1 = {y1:.6g}")
        else:
            lines1.append(f"X1 = {x1:.4f}s")

        lines2: List[str] = []
        if y2 is not None and y1 is not None:
            lines2.append(f"X2 = {x2:.4f}s")
            lines2.append(f"Y2 = {y2:.6g}")
            lines2.append(f"ΔX = {x2 - x1:.4f}s")
            lines2.append(f"ΔY = {y2 - y1:.6g}")
        elif y2 is not None:
            lines2.append(f"X2 = {x2:.4f}s")
            lines2.append(f"Y2 = {y2:.6g}")
        else:
            lines2.append(f"X2 = {x2:.4f}s")

        self.badge1.setLines(lines1)
        self.badge2.setLines(lines2)

        w1_px, h1_px = self.badge1.size_px()
        w2_px, h2_px = self.badge2.size_px()

        w1 = w1_px / view_w_px * x_rng
        h1 = h1_px / view_h_px * y_rng
        w2 = w2_px / view_w_px * x_rng
        h2 = h2_px / view_h_px * y_rng

        rect1 = self._auto_place(
            self.badge1, x1, y1, w1, h1,
            xr, yr, xs_ref, ys_ref,
            prefer='above', occupied=[]
        )
        rect2 = self._auto_place(
            self.badge2, x2, y2, w2, h2,
            xr, yr, xs_ref, ys_ref,
            prefer='below', occupied=[rect1]
        )

        if self._rects_overlap(rect1, rect2):
            rect1 = self._auto_place(
                self.badge1, x1, y1, w1, h1,
                xr, yr, xs_ref, ys_ref,
                prefer='above', occupied=[rect2]
            )

        if self._rects_overlap(rect1, rect2):
            rect2 = self._auto_place(
                self.badge2, x2, y2, w2, h2,
                xr, yr, xs_ref, ys_ref,
                prefer='below', occupied=[rect1]
            )

        self._cursor_rects_cache = [rect1, rect2]

    @staticmethod
    def _rects_overlap(r1, r2) -> bool:
        if r1 is None or r2 is None:
            return False
        return not (r1[2] <= r2[0] or r2[2] <= r1[0] or
                    r1[3] <= r2[1] or r2[3] <= r1[1])

    def _any_curve_crosses_rect(self, rect) -> bool:
        for info in self.curves.values():
            if not info.visible or len(info.x_data) == 0:
                continue
            xs, ys = info.get_np()
            if self._curve_crosses_rect(xs, ys, rect):
                return True
        return False

    def _auto_place(self, badge, x, y, w, h, xr, yr,
                    xs_ref, ys_ref, prefer, occupied):
        if y is None:
            y = (yr[0] + yr[1]) / 2

        gap_v = h * 0.5
        gap_h = w * 0.10

        above_list = [
            (0,       gap_v),
            (gap_h,   gap_v),
            (-gap_h,  gap_v),
            (0,       h + gap_v * 2),
            (gap_h,   h + gap_v * 2),
            (-gap_h,  h + gap_v * 2),
            (0,       -h - gap_v),
            (gap_h,   -h - gap_v),
            (-gap_h,  -h - gap_v),
            (0,       -h * 2 - gap_v * 2),
            (gap_h,   -h * 2 - gap_v * 2),
            (-gap_h,  -h * 2 - gap_v * 2),
            (w * 0.6,  gap_v),
            (-w * 0.6, gap_v),
            (w * 0.6, -h - gap_v),
            (-w * 0.6, -h - gap_v),
        ]
        below_list = [
            (0,       -h - gap_v),
            (gap_h,   -h - gap_v),
            (-gap_h,  -h - gap_v),
            (0,       -h * 2 - gap_v * 2),
            (gap_h,   -h * 2 - gap_v * 2),
            (-gap_h,  -h * 2 - gap_v * 2),
            (0,       gap_v),
            (gap_h,   gap_v),
            (-gap_h,  gap_v),
            (0,       h + gap_v * 2),
            (gap_h,   h + gap_v * 2),
            (-gap_h,  h + gap_v * 2),
            (w * 0.6,  -h - gap_v),
            (-w * 0.6, -h - gap_v),
            (w * 0.6,  gap_v),
            (-w * 0.6, gap_v),
        ]
        candidates = above_list if prefer == 'above' else below_list

        best = None
        best_score = -1

        for dx, dy in candidates:
            px = x + dx
            py = y + dy

            px = max(xr[0] + w / 2, min(xr[1] - w / 2, px))
            py = max(yr[0] + h, min(yr[1], py))

            rect = (px - w / 2, py - h, px + w / 2, py)

            in_bounds = (rect[0] >= xr[0] - 1e-9 and rect[2] <= xr[1] + 1e-9
                         and rect[1] >= yr[0] - 1e-9 and rect[3] <= yr[1] + 1e-9)

            overlaps = False
            for o in occupied:
                if self._rects_overlap(rect, o):
                    overlaps = True
                    break

            crosses = self._any_curve_crosses_rect(rect)

            score = 0
            if in_bounds:
                score += 100
            if not overlaps:
                score += 500
            if not crosses:
                score += 300

            if score > best_score:
                best_score = score
                best = (px, py, rect)
                if in_bounds and not overlaps and not crosses:
                    break

        if best is None:
            px = max(xr[0] + w / 2, min(xr[1] - w / 2, x))
            py = max(yr[0] + h, min(yr[1], y + gap_v))
            best = (px, py, (px - w / 2, py - h, px + w / 2, py))

        px, py, rect = best
        badge.setPos(px, py)
        return rect

    def _on_pause_clicked(self):
        self.pause(self.pause_btn.isChecked())

    def _on_window_changed(self, text):
        mapping = {
            "5 秒": 5, "10 秒": 10, "30 秒": 30,
            "1 分钟": 60, "5 分钟": 300, "10 分钟": 600, "全部": 0,
        }
        self.set_x_window(mapping.get(text, 300))

    def save_image(self, path=None):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, "保存图形", "waveform.png",
                "PNG 图像 (*.png);;JPEG 图像 (*.jpg);;SVG 矢量图 (*.svg)"
            )
            if not path: return
        try:
            if path.lower().endswith('.svg'):
                exporter = pg.exporters.SVGExporter(self.plot_widget.plotItem)
            else:
                exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
            exporter.export(path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存图形失败: {e}")

    def copy_to_clipboard(self):
        try:
            top_window = self.window()
            if top_window is None:
                top_window = self
            pixmap = top_window.grab()
            QGuiApplication.clipboard().setPixmap(pixmap)
            QMessageBox.information(
                self, "已复制",
                "整个窗口截图已复制到剪贴板。\n\n"
                "可在 Word / PPT / 微信 / QQ 等\n"
                "用 Ctrl+V 粘贴。"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"复制失败: {e}")

    def save_data(self, path=None, curve_id=None):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, "保存数据", "waveform.csv", "CSV 文件 (*.csv)"
            )
            if not path: return

        if curve_id is not None:
            curves_to_save = {curve_id: self.curves[curve_id]} if curve_id in self.curves else {}
        else:
            curves_to_save = self.curves

        if not curves_to_save:
            QMessageBox.information(self, "提示", "没有数据可保存。")
            return

        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(['Time (s)'] + [info.name for info in curves_to_save.values()])
                curve_list = list(curves_to_save.values())
                max_len = max(len(c.x_data) for c in curve_list)
                for i in range(max_len):
                    row = [f"{curve_list[0].x_data[i]:.9f}" if i < len(curve_list[0].x_data) else ""]
                    for c in curve_list:
                        row.append(repr(c.y_data[i]) if i < len(c.y_data) else "")
                    w.writerow(row)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存数据失败: {e}")