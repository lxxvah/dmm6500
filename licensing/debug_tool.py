#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing/debug_tool.py —— 授权调试工具（开发/排查用）
==============================================================
用法：
    python licensing/debug_tool.py              # 交互式菜单
    python licensing/debug_tool.py status       # 查看当前状态
    python licensing/debug_tool.py clear-all    # 清除所有记录
    python licensing/debug_tool.py clear-trial  # 只清试用
    python licensing/debug_tool.py clear-lic    # 只清授权
    python licensing/debug_tool.py machine      # 打印本机机器码
    python licensing/debug_tool.py paths        # 打印所有存储位置
"""

import sys
from pathlib import Path

# 允许直接 python licensing/debug_tool.py
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _import_client():
    from licensing import client as c
    from licensing.config import APP_ID, APP_NAME, KEY_PREFIX
    from licensing.fingerprint import get_machine_code
    return c, APP_ID, APP_NAME, KEY_PREFIX, get_machine_code


# ============================================================
# 注册表辅助
# ============================================================
def _reg_module():
    if sys.platform != "win32":
        return None
    try:
        import winreg
        return winreg
    except ImportError:
        return None


# ============================================================
# 状态
# ============================================================
def show_status():
    c, app_id, app_name, prefix, machine = _import_client()

    print()
    print("=" * 60)
    print(f"  应用:     {app_name}  ({app_id})")
    print(f"  密钥前缀: {prefix}")
    print(f"  机器码:   {machine()}")
    print("=" * 60)

    # License
    print()
    print("【正式授权】")
    lic_path = c.find_license_file()
    if lic_path:
        print(f"  文件位置: {lic_path}")
    else:
        print("  文件位置: （未找到）")

    st, info = c.check_license()
    print(f"  状态:     {st}")
    if info.get("reason"):
        print(f"  说明:     {info['reason']}")
    if st == c.LicenseResult.OK:
        for k in ("licensee", "edition", "expire", "issued_at", "app"):
            if k in info:
                print(f"    {k}: {info[k]}")

    # Trial
    print()
    print("【试用】")
    trial_first = c._read_trial_first_ts()
    if trial_first:
        import datetime
        ts = datetime.datetime.fromtimestamp(trial_first)
        print(f"  起始时间: {ts:%Y-%m-%d %H:%M:%S}")
    else:
        print("  起始时间: （无记录）")

    tst, days = c.check_trial()
    print(f"  状态:     {tst}")
    print(f"  剩余:     {days} 天")

    # 综合
    print()
    print("【综合判断 check_access()】")
    status, info = c.check_access()
    print(f"  状态:     {status}")
    if status == c.LicenseResult.OK:
        print(f"  类型:     {info.get('type')}")
        if info.get("type") == "trial":
            print(f"  剩余:     {info.get('days_remaining')} 天")
        else:
            print(f"  授权对象: {info.get('licensee')}")
            print(f"  有效期:   {info.get('expire')}")
    else:
        print(f"  原因:     {info.get('reason', '')}")

    print()


def show_paths():
    c, app_id, app_name, prefix, machine = _import_client()

    print()
    print("=" * 60)
    print("  授权文件候选位置（按查找顺序）")
    print("=" * 60)
    for p in c._candidate_license_paths():
        mark = "✓" if p.is_file() else " "
        print(f"  [{mark}] {p}")

    print()
    print("=" * 60)
    print("  试用文件候选位置（按查找顺序）")
    print("=" * 60)
    for p in c._candidate_trial_paths():
        mark = "✓" if p.is_file() else " "
        print(f"  [{mark}] {p}")

    print()
    print("=" * 60)
    print("  注册表位置")
    print("=" * 60)
    print(f"  HKCU\\Software\\{app_id}\\Trial")
    reg = _reg_module()
    if reg is not None:
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER,
                             rf"Software\{app_id}\Trial") as k:
                ts, _ = reg.QueryValueEx(k, "first_ts")
                print(f"  当前值 first_ts = {ts}")
        except FileNotFoundError:
            print("  （无记录）")
        except Exception as e:
            print(f"  读取失败: {e}")
    else:
        print("  （非 Windows 平台，跳过）")

    print()


# ============================================================
# 清除
# ============================================================
def clear_license() -> int:
    c, _, _, _, _ = _import_client()
    n = 0
    for p in c._candidate_license_paths():
        try:
            if p.is_file():
                p.unlink()
                print(f"  [删] {p}")
                n += 1
        except Exception as e:
            print(f"  [失败] {p}: {e}")
    return n


def clear_trial() -> int:
    c, app_id, _, _, _ = _import_client()
    n = 0

    # 1) 文件
    for p in c._candidate_trial_paths():
        try:
            if p.is_file():
                p.unlink()
                print(f"  [删] {p}")
                n += 1
        except Exception as e:
            print(f"  [失败] {p}: {e}")

    # 2) 注册表
    reg = _reg_module()
    if reg is not None:
        try:
            reg.DeleteKey(reg.HKEY_CURRENT_USER,
                          rf"Software\{app_id}\Trial")
            print(f"  [删] HKCU\\Software\\{app_id}\\Trial")
            n += 1
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"  [失败] 注册表: {e}")

    return n


def clear_all():
    print()
    print(">>> 清除正式授权")
    n1 = clear_license()

    print()
    print(">>> 清除试用记录")
    n2 = clear_trial()

    print()
    if n1 + n2 == 0:
        print("✅ 没有需要清除的记录（已经是干净状态）")
    else:
        print(f"✅ 已清除 {n1 + n2} 条记录")
    print()


# ============================================================
# 交互式菜单
# ============================================================
def interactive_menu():
    while True:
        print()
        print("=" * 60)
        print("  授权调试工具")
        print("=" * 60)
        print("  1. 查看当前状态")
        print("  2. 查看所有存储位置")
        print("  3. 清除所有记录（授权 + 试用）")
        print("  4. 只清试用记录")
        print("  5. 只清授权文件")
        print("  6. 打印本机机器码")
        print("  0. 退出")
        print("=" * 60)

        try:
            choice = input("请输入选项: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "1":
            show_status()
        elif choice == "2":
            show_paths()
        elif choice == "3":
            clear_all()
        elif choice == "4":
            print()
            print(">>> 清除试用记录")
            n = clear_trial()
            print(f"✅ 已清除 {n} 条记录" if n else "（无记录）")
            print()
        elif choice == "5":
            print()
            print(">>> 清除正式授权")
            n = clear_license()
            print(f"✅ 已清除 {n} 个文件" if n else "（无文件）")
            print()
        elif choice == "6":
            _, _, _, _, machine = _import_client()
            print()
            print(f"本机机器码: {machine()}")
            print()
        elif choice in ("0", "q", "quit", "exit"):
            print("再见")
            return
        else:
            print("无效选项")


# ============================================================
# 入口
# ============================================================
def main():
    args = sys.argv[1:]

    if not args:
        interactive_menu()
        return

    cmd = args[0].lower()

    if cmd == "status":
        show_status()
    elif cmd == "paths":
        show_paths()
    elif cmd in ("clear", "clear-all"):
        clear_all()
    elif cmd in ("clear-trial", "cleartrial"):
        print()
        print(">>> 清除试用记录")
        n = clear_trial()
        print(f"✅ 已清除 {n} 条记录" if n else "（无记录）")
        print()
    elif cmd in ("clear-lic", "clear-license", "clearlicense"):
        print()
        print(">>> 清除正式授权")
        n = clear_license()
        print(f"✅ 已清除 {n} 个文件" if n else "（无文件）")
        print()
    elif cmd in ("machine", "machine-code"):
        _, _, _, _, machine = _import_client()
        print(machine())
    elif cmd in ("-h", "--help", "help"):
        print(__doc__)
    else:
        print(f"未知命令: {cmd}")
        print("运行 `python licensing/debug_tool.py help` 查看用法")
        sys.exit(1)


if __name__ == "__main__":
    main()