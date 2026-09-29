#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/gauge_range.py —— 机械表自动量程控制器
=================================================
和实时值卡片（format_with_unit）保持一致：
  · 单位前缀（µV / mV / V / kV）自动切换
  · 档位用 1/2/5/10 系（不是 10 系固定表）
  · 窗口最大值决定量级，带滞回 + 冷却防抖
  · 双极：V / A / Ω（±tier）；单极：F / Hz / s / °C（0~tier）

对外接口：
    ctrl = GaugeRangeController()
    d = ctrl.get_initial_decision("DCV", "V")
    d = ctrl.update("DCV", 0.000872971, "V")
    ctrl.reset("DCV")
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple


# ============================================================
# 单位前缀表（与 core/statistics.format_with_unit 保持一致）
# ============================================================
_PREFIXES: Dict[str, list] = {
    "V":  [(1e-6, "µV"), (1e-3, "mV"), (1.0, "V"),  (1e3, "kV")],
    "A":  [(1e-12, "pA"), (1e-9, "nA"), (1e-6, "µA"),
           (1e-3, "mA"), (1.0, "A")],
    "Ω":  [(1e-3, "mΩ"), (1.0, "Ω"), (1e3, "kΩ"),
           (1e6, "MΩ"), (1e9, "GΩ")],
    "F":  [(1e-12, "pF"), (1e-9, "nF"), (1e-6, "µF"),
           (1e-3, "mF"), (1.0, "F")],
    "Hz": [(1.0, "Hz"), (1e3, "kHz"), (1e6, "MHz"), (1e9, "GHz")],
    "s":  [(1e-9, "ns"), (1e-6, "µs"), (1e-3, "ms"), (1.0, "s")],
    "°C": [(1.0, "°C")],
}

# 双极模式：表盘显示 ±tier
_BIPOLAR_UNITS = {"V", "A", "Ω"}

# 无数据时的默认档位（在该基础单位下）
_DEFAULT_TIER = {
    "V": 1.0,
    "A": 1e-3,
    "Ω": 1000.0,
    "F": 1e-6,
    "Hz": 1000.0,
    "s": 1.0,
    "°C": 100.0,
}


# ============================================================
# 决策结果
# ============================================================
@dataclass
class GaugeRangeDecision:
    min_value: float          # 表盘左端（该单位下的显示值）
    max_value: float          # 表盘右端（该单位下的显示值）
    major_step: float
    minor_step: float
    decimals: int             # 刻度数字的小数位数（值不受此限制）
    unit: str = ""            # 显示单位："µV" / "mV" / "V" ...
    unit_scale: float = 1.0   # 显示值 = 原始值 / unit_scale


# ============================================================
# 控制器
# ============================================================
class GaugeRangeController:
    """
    自动量程控制器——和实时值卡片一致。

    滞回参数（可直接改类属性）：
        WINDOW_SIZE = 20     采样窗口大小
        UP_RATIO    = 0.90   升档阈值
        DOWN_RATIO  = 0.40   降档阈值
        COOLDOWN_S  = 1.0    切档冷却时间
    """

    WINDOW_SIZE = 20
    UP_RATIO = 0.90
    DOWN_RATIO = 0.40
    COOLDOWN_S = 1.0

    def __init__(self):
        self._recent: Dict[str, Deque[float]] = {}
        self._cur_unit: Dict[str, str] = {}
        self._cur_scale: Dict[str, float] = {}
        self._cur_tier: Dict[str, float] = {}
        self._last_switch: Dict[str, float] = {}

    # --------------------------------------------------------
    # 外部 API
    # --------------------------------------------------------
    def reset(self, mode: Optional[str] = None) -> None:
        if mode is None:
            self._recent.clear()
            self._cur_unit.clear()
            self._cur_scale.clear()
            self._cur_tier.clear()
            self._last_switch.clear()
            return
        self._recent.pop(mode, None)
        self._cur_unit.pop(mode, None)
        self._cur_scale.pop(mode, None)
        self._cur_tier.pop(mode, None)
        self._last_switch.pop(mode, None)

    def on_instrument_range(self, mode: str, range_val: float) -> None:
        """保留以便兼容旧信号连接（当前设计不用）"""
        pass

    def get_initial_decision(self, mode: str,
                             base_unit: str) -> GaugeRangeDecision:
        self.reset(mode)
        return self._build(mode, base_unit, vmax=0.0, force_reset=True)

    def update(self, mode: str, value: float,
               base_unit: str) -> GaugeRangeDecision:
        buf = self._recent.setdefault(mode, deque(maxlen=self.WINDOW_SIZE))
        try:
            buf.append(abs(float(value)))
        except (TypeError, ValueError):
            pass
        vmax = max(buf) if buf else 0.0
        return self._build(mode, base_unit, vmax)

    # --------------------------------------------------------
    # 核心决策
    # --------------------------------------------------------
    def _build(self, mode: str, base_unit: str,
               vmax: float, force_reset: bool = False) -> GaugeRangeDecision:

        # ---- 1. 定单位 ----
        if vmax <= 0:
            unit_str, scale = self._default_unit(base_unit)
        else:
            unit_str, scale = self._pick_unit(vmax, base_unit)
        vmax_disp = vmax / scale if scale > 0 else 0.0

        # ---- 2. 定档位 ----
        if vmax_disp <= 0:
            ideal_tier = _DEFAULT_TIER.get(base_unit, 1.0)
            ideal_tier = ideal_tier / scale if scale > 0 else 1.0
        else:
            ideal_tier = self._nice_tier(vmax_disp)

        # ---- 3. 滞回 ----
        cur_tier = self._cur_tier.get(mode)
        cur_scale = self._cur_scale.get(mode)
        now = time.monotonic()

        if force_reset or cur_tier is None:
            new_tier, new_scale = ideal_tier, scale

        elif abs(scale - (cur_scale or 0)) > 1e-20 * max(1.0, abs(scale)):
            new_tier, new_scale = ideal_tier, scale

        elif ideal_tier > cur_tier:
            if vmax_disp > cur_tier * self.UP_RATIO:
                new_tier, new_scale = ideal_tier, scale
            else:
                new_tier, new_scale = cur_tier, cur_scale

        elif ideal_tier < cur_tier:
            if (now - self._last_switch.get(mode, 0) >= self.COOLDOWN_S
                    and vmax_disp < cur_tier * self.DOWN_RATIO):
                new_tier, new_scale = ideal_tier, scale
            else:
                new_tier, new_scale = cur_tier, cur_scale
        else:
            new_tier, new_scale = cur_tier, cur_scale

        # ---- 4. 记录 + 日志 ----
        changed = (
            cur_tier is None
            or abs(new_tier - cur_tier) > 1e-20
            or abs(new_scale - (cur_scale or 0)) > 1e-20 * max(1.0, abs(new_scale))
        )
        if changed:
            self._last_switch[mode] = now
            new_unit_disp = self._unit_for_scale(base_unit, new_scale)
            print(f"[档位] {mode} → {new_unit_disp} ±{new_tier:g} "
                  f"(vmax={vmax:.6g})", flush=True)

        self._cur_unit[mode] = self._unit_for_scale(base_unit, new_scale)
        self._cur_scale[mode] = new_scale
        self._cur_tier[mode] = new_tier

        # ---- 5. 双极 / 单极 ----
        bipolar = base_unit in _BIPOLAR_UNITS
        if bipolar:
            vmin, vmax_val = -new_tier, new_tier
        else:
            vmin, vmax_val = 0.0, new_tier

        span = vmax_val - vmin
        major = span / 10.0
        minor = major / 5.0
        decimals = self._decimals_for(span)
        unit_disp = self._unit_for_scale(base_unit, new_scale)

        return GaugeRangeDecision(
            min_value=vmin,
            max_value=vmax_val,
            major_step=major,
            minor_step=minor,
            decimals=decimals,
            unit=unit_disp,
            unit_scale=new_scale,
        )

    # --------------------------------------------------------
    # 工具方法
    # --------------------------------------------------------
    @staticmethod
    def _pick_unit(v_abs: float, base_unit: str) -> Tuple[str, float]:
        prefixes = _PREFIXES.get(base_unit)
        if not prefixes:
            return base_unit, 1.0
        for threshold, unit_str in reversed(prefixes):
            if v_abs >= threshold * 0.999:
                return unit_str, threshold
        return prefixes[0][1], prefixes[0][0]

    @staticmethod
    def _unit_for_scale(base_unit: str, scale: float) -> str:
        prefixes = _PREFIXES.get(base_unit)
        if not prefixes:
            return base_unit
        for threshold, unit_str in prefixes:
            if abs(threshold - scale) < 1e-20 * max(1.0, abs(scale)):
                return unit_str
        return base_unit

    @staticmethod
    def _default_unit(base_unit: str) -> Tuple[str, float]:
        prefixes = _PREFIXES.get(base_unit)
        if not prefixes:
            return base_unit, 1.0
        for threshold, unit_str in prefixes:
            if abs(threshold - 1.0) < 1e-20:
                return unit_str, 1.0
        return prefixes[0][1], prefixes[0][0]

    @staticmethod
    def _nice_tier(v: float) -> float:
        """1/2/5/10 系"""
        if v <= 0:
            return 1.0
        exp = math.floor(math.log10(v))
        base = 10.0 ** exp
        mant = v / base
        if mant <= 1.001:
            return base
        if mant <= 2.001:
            return 2.0 * base
        if mant <= 5.001:
            return 5.0 * base
        return 10.0 * base

    @staticmethod
    def _decimals_for(span: float) -> int:
        """
        刻度数字的小数位数——按量级自适应，避免刻度重叠。
        值本身的显示精度由 analog_gauge_qt 的 _format_value_display
        单独处理（6 位有效数字），与此无关。
        """
        if span <= 0:
            return 1
        vmax = span / 2.0
        if vmax <= 0:
            return 1
        if vmax >= 100:    return 0     # 100  / 80
        if vmax >= 10:     return 1     # 10.0 / 8.0
        if vmax >= 1:      return 2     # 5.00 / 4.00
        if vmax >= 0.1:    return 3     # 0.500
        if vmax >= 0.01:   return 4     # 0.0500
        if vmax >= 0.001:  return 5     # 0.00500
        return 6