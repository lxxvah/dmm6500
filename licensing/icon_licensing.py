#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing/icon.py —— 苹果风应用图标（QPainter 代码绘制）
==============================================================
· 无外部图片文件，纯代码绘制
· 圆角方形 + 苹果蓝渐变 + 白色钥匙
· 支持多尺寸（16~256），HiDPI 下清晰
"""

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QPen, QBrush, QColor, QLinearGradient,
)


def _draw_key_glyph(p: QPainter, scale: float):
    """在 256×256 逻辑坐标系里绘制钥匙。"""
    # 圆角方形底 + 苹果蓝渐变
    grad = QLinearGradient(0, 0, 0, 256 * scale)
    grad.setColorAt(0.0, QColor("#5AA9FF"))
    grad.setColorAt(0.55, QColor("#0A84FF"))
    grad.setColorAt(1.0, QColor("#0066D6"))

    bg_rect = QRectF(16 * scale, 16 * scale, 224 * scale, 224 * scale)
    radius = 56 * scale

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(bg_rect, radius, radius)

    # 顶部高光（内嵌渐变，让图标更立体）
    hl = QLinearGradient(0, 0, 0, 128 * scale)
    hl.setColorAt(0.0, QColor(255, 255, 255, 70))
    hl.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(QBrush(hl))
    p.drawRoundedRect(
        QRectF(16 * scale, 16 * scale, 224 * scale, 112 * scale),
        radius, radius,
    )

    # 白色钥匙
    pen = QPen(QColor("#FFFFFF"), 14 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    # 钥匙头（圆环）
    head_cx = 92 * scale
    head_cy = 128 * scale
    head_r = 30 * scale
    p.drawEllipse(QPointF(head_cx, head_cy), head_r, head_r)

    # 手柄
    shaft_start = head_cx + head_r - 4 * scale
    shaft_end = 208 * scale
    p.drawLine(QPointF(shaft_start, head_cy), QPointF(shaft_end, head_cy))

    # 齿 1
    p.drawLine(QPointF(170 * scale, head_cy),
               QPointF(170 * scale, head_cy + 26 * scale))

    # 齿 2
    p.drawLine(QPointF(194 * scale, head_cy),
               QPointF(194 * scale, head_cy + 18 * scale))


def make_license_icon() -> QIcon:
    """生成多尺寸苹果风钥匙图标。"""
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