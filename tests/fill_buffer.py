#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fill_buffer.py —— 灌数据到 defbuffer1

策略：
  1. 显式设置 TRAC:FEED:CONTrol NEXT，确保读数自动写入缓冲区
  2. 循环 READ? 每次采 1 点
  3. 实时报告缓冲区大小
"""
import pyvisa
import time

IP = "192.168.1.122"
TARGET = 1000         # 目标点数（想多灌改这个数字）
                     #   200 → 约 6 秒
                     #   500 → 约 15 秒
                     #   1000 → 约 30 秒


def query(inst, cmd, default=""):
    """安全查询（命令不支持时返回 default）"""
    try:
        return inst.query(cmd).strip()
    except Exception as e:
        print(f"  [查询失败] {cmd} -> {e}")
        return default


def main():
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(f"TCPIP0::{IP}::inst0::INSTR")
    inst.timeout = 20000
    inst.read_termination = '\n'
    inst.write_termination = '\n'

    print(f"已连接: {query(inst, '*IDN?')}")

    # 复位
    inst.write('*RST')
    time.sleep(1.5)

    # 清错误队列
    while True:
        e = query(inst, 'SYST:ERR?')
        if e.startswith('0,') or e.startswith('+0') or not e:
            break

    # ---- 诊断 ----
    print("\n== 缓冲区诊断 ==")
    print(f"  TRAC:ACT?  defbuffer1 -> {query(inst, 'TRAC:ACT? \"defbuffer1\"')}")
    print(f"  TRAC:POIN? defbuffer1 -> {query(inst, 'TRAC:POIN? \"defbuffer1\"')}")

    # ---- 配置测量 ----
    inst.write('SENS:FUNC "VOLT:DC"')
    inst.write('SENS:VOLT:DC:NPLC 0.01')
    inst.write('SENS:VOLT:DC:RANG:AUTO ON')
    time.sleep(0.3)

    # ---- 清空 + 设置缓冲区容量 ----
    inst.write('TRAC:CLE "defbuffer1"')
    time.sleep(0.3)
    inst.write(f'TRAC:POIN {TARGET}, "defbuffer1"')
    time.sleep(0.3)

    # ---- 关键：让读数自动写入缓冲区 ----
    print("\n== 尝试设置 TRAC:FEED:CONTrol ==")
    # 尝试多种语法（不同固件可能不同）
    attempts = [
        'TRAC:FEED:CONT NEXT, "defbuffer1"',
        'TRAC:FEED:CONT NEXT',
        'TRAC:FEED:CONT ALW, "defbuffer1"',
        'TRAC:FEED:CONT ALWays, "defbuffer1"',
    ]
    feed_ok = False
    for cmd in attempts:
        try:
            inst.write(cmd)
            time.sleep(0.1)
            # 检查错误
            e = query(inst, 'SYST:ERR?')
            if e.startswith('0,') or e.startswith('+0'):
                print(f"  ✅ 成功: {cmd}")
                feed_ok = True
                break
            else:
                print(f"  ❌ 失败: {cmd} -> {e}")
                # 清错误
                while True:
                    e = query(inst, 'SYST:ERR?')
                    if e.startswith('0,') or e.startswith('+0') or not e:
                        break
        except Exception as ex:
            print(f"  ❌ 异常: {cmd} -> {ex}")

    if not feed_ok:
        print("  ⚠️ 未能显式设置 feed，尝试直接用 READ? 循环")

    # ---- 循环采集 ----
    print(f"\n== 开始采集 {TARGET} 点 ==")
    t0 = time.time()
    n_before = 0
    try:
        n_before = int(float(query(inst, 'TRAC:ACT? "defbuffer1"', "0")))
    except Exception:
        pass
    print(f"  起始缓冲: {n_before}")

    for i in range(TARGET):
        try:
            val = query(inst, 'READ?')
        except Exception as e:
            print(f"  READ? 失败 @{i+1}: {e}")
            break
        if (i + 1) % 25 == 0 or (i + 1) == TARGET:
            try:
                n = int(float(query(inst, 'TRAC:ACT? "defbuffer1"', "0")))
            except Exception:
                n = -1
            elapsed = time.time() - t0
            print(f"  {i+1}/{TARGET}  缓冲={n}  ({elapsed:.1f}s)  val={val}")
        time.sleep(0.02)

    # ---- 结果 ----
    time.sleep(0.3)
    n_final = int(float(query(inst, 'TRAC:ACT? "defbuffer1"', "0")))
    err = query(inst, 'SYST:ERR?')

    print(f"\n== 结果 ==")
    print(f"  起始缓冲: {n_before}")
    print(f"  最终缓冲: {n_final}")
    print(f"  新增:     {n_final - n_before}")
    print(f"  仪器错误: {err}")

    if n_final > n_before + 10:
        print(f"✅ 成功！defbuffer1 里有 {n_final} 条数据")
    else:
        print(f"❌ 失败：缓冲区没有增长")

    inst.close()


if __name__ == "__main__":
    main()