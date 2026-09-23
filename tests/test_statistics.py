#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计模块测试"""
import math
from core.statistics import StreamingStats, format_with_unit


def test_streaming_basic():
    s = StreamingStats(window=100)
    for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
        s.update(v)
    assert s.n == 5
    assert abs(s.mean - 3.0) < 1e-9
    assert abs(s.max - 5.0) < 1e-9
    assert abs(s.min - 1.0) < 1e-9
    assert abs(s.std - math.sqrt(2.0)) < 1e-9
    print("✅ test_streaming_basic")


def test_streaming_window():
    """滑动窗口：窗口满了要挤掉旧值"""
    s = StreamingStats(window=3)
    for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
        s.update(v)
    assert s.n == 3
    assert abs(s.mean - 4.0) < 1e-9
    assert abs(s.max - 5.0) < 1e-9
    assert abs(s.min - 3.0) < 1e-9
    print("✅ test_streaming_window")


def test_reset():
    s = StreamingStats(window=10)
    for v in range(10):
        s.update(v)
    s.reset()
    assert s.n == 0
    assert s.mean == 0.0
    assert s.max == 0.0
    assert s.min == 0.0
    print("✅ test_reset")


def test_format_with_unit():
    """
    单位自适应测试。

    ✅ 修正：0.0005 s 期望改为 "µs"（500 µs）。
       SI 前缀规则：数值必须落在 [1, 1000) 才用该前缀对应的单位。
       · 0.0005 s = 500 µs = 0.5 ms
       · 0.0005 >= 1e-3 (ms 阈值)？ 否 → 不是 ms
       · 0.0005 >= 1e-6 (µs 阈值)？ 是 → 500 µs
    """
    cases = [
        # ---- 电压 ----
        (0.0032, "V", "mV"),         # 3.2 mV
        (3.1832, "V", "V"),          # 3.1832 V（在 [1, 1000)）
        (1500, "V", "kV"),           # 1.5 kV
        (0.000_000_5, "V", "µV"),    # 0.5 µV

        # ---- 电流 ----
        (0.000_001, "A", "µA"),      # 1 µA
        (0.000_000_001, "A", "nA"),  # 1 nA
        (0.5, "A", "mA"),            # 500 mA

        # ---- 电阻 ----
        (1500, "Ω", "kΩ"),           # 1.5 kΩ
        (2_500_000, "Ω", "MΩ"),      # 2.5 MΩ

        # ---- 频率 ----
        (1234, "Hz", "kHz"),         # 1.234 kHz
        (50, "Hz", "Hz"),            # 50 Hz

        # ---- 电容 ----
        (0.000_000_001, "F", "nF"),  # 1 nF
        (0.000_123, "F", "µF"),      # 123 µF

        # ---- 周期 ----
        (0.5, "s", "ms"),            # 500 ms
        (2.5, "s", "s"),             # 2.5 s
        # ✅ 修正：0.0005 s = 500 µs（不是 0.5 ms）
        (0.0005, "s", "µs"),         # 500 µs
    ]
    for val, unit, expected_unit in cases:
        _, got_unit = format_with_unit(val, unit)
        assert got_unit == expected_unit, \
            f"{val} {unit} -> {got_unit} (期望 {expected_unit})"
    print("✅ test_format_with_unit")


if __name__ == "__main__":
    test_streaming_basic()
    test_streaming_window()
    test_reset()
    test_format_with_unit()
    print("\n📊 statistics.py 全部通过")