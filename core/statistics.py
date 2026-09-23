#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/statistics.py —— 统计计算模块
=====================================
职责：
  · StreamingStats —— 滑动窗口流式统计，O(1) 更新
  · format_with_unit —— 单位自适应格式化

对外接口：
    stats = StreamingStats()
    stats.update(value)
    stats.max / stats.min / stats.mean / stats.std

    display_str, unit = format_with_unit(value, "V")

性能优化：
  · 均值/方差：O(1) 双累加和
  · max/min：增量维护；只有当被窗口挤出的旧值恰好是当前 max/min 时
            才标脏重扫（其余情况 O(1)）
"""

from __future__ import annotations

import math
from collections import deque
from typing import Deque, Optional


# ============================================
# 流式统计
# ============================================
class StreamingStats:
    """
    滑动窗口统计（O(1) 更新）。

    用法：
        s = StreamingStats(window=100000)
        for v in values:
            s.update(v)
        print(s.mean, s.std, s.min, s.max)
    """

    def __init__(self, window: int = 100000):
        self.window = window
        self._data: Deque[float] = deque(maxlen=window)
        self._sum: float = 0.0
        self._sum_sq: float = 0.0
        self._count: int = 0

        # 缓存（增量维护）
        self._max: Optional[float] = None
        self._min: Optional[float] = None
        self._max_dirty: bool = False
        self._min_dirty: bool = False

    def update(self, value: float) -> None:
        """更新一个值（O(1)）"""
        # 如果窗口已满，先减掉被挤出的旧值
        if len(self._data) == self.window:
            old = self._data[0]
            self._sum -= old
            self._sum_sq -= old * old

            # ✅ 只有被挤出的旧值恰好是当前 max/min，才标脏
            if self._max is not None and old == self._max:
                self._max_dirty = True
            if self._min is not None and old == self._min:
                self._min_dirty = True

        self._data.append(value)
        self._sum += value
        self._sum_sq += value * value
        self._count += 1

        # ✅ 增量更新 max/min
        if self._max is None or value > self._max:
            self._max = value
            self._max_dirty = False
        if self._min is None or value < self._min:
            self._min = value
            self._min_dirty = False

    def reset(self) -> None:
        self._data.clear()
        self._sum = 0.0
        self._sum_sq = 0.0
        self._count = 0
        self._max = None
        self._min = None
        self._max_dirty = False
        self._min_dirty = False

    @property
    def n(self) -> int:
        return len(self._data)

    @property
    def mean(self) -> float:
        n = len(self._data)
        return self._sum / n if n > 0 else 0.0

    @property
    def variance(self) -> float:
        n = len(self._data)
        if n < 2:
            return 0.0
        mean = self._sum / n
        return max(0.0, self._sum_sq / n - mean * mean)

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    @property
    def max(self) -> float:
        if self._max_dirty or self._max is None:
            if not self._data:
                self._max = 0.0
            else:
                self._max = float(max(self._data))
            self._max_dirty = False
        return self._max

    @property
    def min(self) -> float:
        if self._min_dirty or self._min is None:
            if not self._data:
                self._min = 0.0
            else:
                self._min = float(min(self._data))
            self._min_dirty = False
        return self._min


# ============================================
# 单位自适应
# ============================================
def format_with_unit(value, base_unit: str = "V"):
    """
    根据数值大小自动选择前缀单位。

    Args:
        value: 数值
        base_unit: 基础单位（"V" / "A" / "Ω" / "F" / "Hz" / "s" / "°C"）

    Returns:
        (格式化字符串, 单位字符串)

    示例：
        format_with_unit(0.0032, "V")   -> ("3.2", "mV")
        format_with_unit(1500, "Ω")     -> ("1.5", "kΩ")
        format_with_unit(3.1832, "V")   -> ("3.1832", "V")
        format_with_unit(float("nan"), "F")  -> ("---", "F")
    """
    # ---- 1. None 保护 ----
    if value is None:
        return "---", base_unit

    # ---- 2. 类型转换保护 ----
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "---", base_unit

    # ---- 3. NaN / Inf 保护 ----
    if math.isnan(v) or math.isinf(v):
        return "---", base_unit

    abs_val = abs(v)

    # ---- 4. 按基础单位选择前缀表 ----
    if base_unit == "V":
        prefixes = [(1e-6, "µV"), (1e-3, "mV"), (1.0, "V"), (1e3, "kV")]
    elif base_unit == "A":
        prefixes = [(1e-12, "pA"), (1e-9, "nA"), (1e-6, "µA"),
                    (1e-3, "mA"), (1.0, "A")]
    elif base_unit == "Ω":
        prefixes = [(1e-3, "mΩ"), (1.0, "Ω"), (1e3, "kΩ"),
                    (1e6, "MΩ"), (1e9, "GΩ")]
    elif base_unit == "F":
        prefixes = [(1e-12, "pF"), (1e-9, "nF"), (1e-6, "µF"),
                    (1e-3, "mF"), (1.0, "F")]
    elif base_unit == "Hz":
        prefixes = [(1.0, "Hz"), (1e3, "kHz"), (1e6, "MHz"), (1e9, "GHz")]
    elif base_unit == "s":
        prefixes = [(1e-9, "ns"), (1e-6, "µs"), (1e-3, "ms"), (1.0, "s")]
    elif base_unit == "°C":
        return f"{v:.4g}", "°C"
    else:
        return f"{v:.6g}", base_unit

    # ---- 5. 从大到小找第一个匹配的前缀 ----
    for threshold, unit in reversed(prefixes):
        if abs_val >= threshold * 0.999:
            return f"{v / threshold:.6g}", unit

    # ---- 6. 兜底 ----
    return f"{v / prefixes[0][0]:.6g}", prefixes[0][1]