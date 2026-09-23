#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实仪器连接测试。
用法：
    python tests/test_connection_real.py 192.168.1.122
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.connection import ConnectionManager


def test_connect(ip: str):
    print(f"\n{'=' * 60}")
    print(f"  测试连接: {ip}")
    print(f"{'=' * 60}")

    t0 = time.time()
    conn = ConnectionManager()
    conn.connect(ip=ip)
    print(f"✅ 连接成功，耗时 {time.time() - t0:.2f} 秒")
    print(f"   地址: {conn.address}")

    inst = conn.instrument
    idn = inst.query("*IDN?").strip()
    print(f"   IDN : {idn}")

    # 命令集
    lang = inst.query("*LANG?").strip()
    print(f"   语言: {lang}")

    # 功能切换
    inst.write('SENS:FUNC "VOLT:DC"')
    time.sleep(0.2)
    print(f"   当前功能: {inst.query('SENS:FUNC?').strip()}")

    conn.disconnect()
    print("✅ 断开成功")
    return True


def test_all_modes(ip: str):
    """逐个测试所有测量功能"""
    print(f"\n{'=' * 60}")
    print(f"  测试所有测量模式")
    print(f"{'=' * 60}")

    conn = ConnectionManager()
    conn.connect(ip=ip)
    inst = conn.instrument

    modes = [
        ("DCV",   'SENS:FUNC "VOLT:DC"', "MEAS:VOLT:DC?", "V"),
        ("DCI",   'SENS:FUNC "CURR:DC"', "MEAS:CURR:DC?", "A"),
        ("RES2W", 'SENS:FUNC "RES"',     "MEAS:RES?",     "Ω"),
        ("RES4W", 'SENS:FUNC "FRES"',    "MEAS:FRES?",    "Ω"),
        ("ACV",   'SENS:FUNC "VOLT:AC"', "MEAS:VOLT:AC?", "V"),
        ("ACI",   'SENS:FUNC "CURR:AC"', "MEAS:CURR:AC?", "A"),
        ("CAP",   'SENS:FUNC "CAP"',     "MEAS:CAP?",     "F"),
        ("FREQ",  'SENS:FUNC "FREQ"',    "MEAS:FREQ?",    "Hz"),
        ("PER",   'SENS:FUNC "PER"',     "MEAS:PER?",     "s"),
        ("TEMP",  'SENS:FUNC "TEMP"',    "MEAS:TEMP?",    "°C"),
        ("CONT",  'SENS:FUNC "CONT"',    "MEAS:CONT?",    "Ω"),
        ("DIOD",  'SENS:FUNC "DIOD"',    "MEAS:DIOD?",    "V"),
    ]

    passed = 0
    for name, set_cmd, read_cmd, unit in modes:
        try:
            inst.write(set_cmd)
            time.sleep(0.1)
            # 温度特殊处理
            if name == "TEMP":
                inst.write("SENS:TEMP:TRAN TC")
                inst.write("SENS:TEMP:TC:TYPE K")
                time.sleep(0.2)
            val = inst.query(read_cmd).strip()
            err = inst.query("SYST:ERR?").strip()
            ok = err.startswith("0,") or err.startswith("+0")
            mark = "✅" if ok else "⚠️"
            print(f"  {mark} {name:6s} = {val:>18s} {unit}   ERR: {err}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  ❌ {name:6s} 失败: {e}")

    conn.disconnect()
    print(f"\n通过: {passed}/{len(modes)}")
    return passed == len(modes)


def test_retry(ip: str):
    """连续连接 5 次，验证重试稳定性"""
    print(f"\n{'=' * 60}")
    print(f"  测试连接稳定性（连续 5 次）")
    print(f"{'=' * 60}")

    for i in range(5):
        t0 = time.time()
        conn = ConnectionManager()
        try:
            conn.connect(ip=ip)
            dt = time.time() - t0
            print(f"  第 {i + 1} 次: ✅ {dt:.2f} 秒")
            conn.disconnect()
        except Exception as e:
            print(f"  第 {i + 1} 次: ❌ {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python tests/test_connection_real.py <IP>")
        sys.exit(1)
    ip = sys.argv[1]

    # 依次运行
    test_connect(ip)
    test_retry(ip)
    test_all_modes(ip)