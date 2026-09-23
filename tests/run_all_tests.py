#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键跑所有无硬件测试"""
import sys
import traceback
from pathlib import Path

# 把项目根目录加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run(module_name, module):
    print(f"\n{'=' * 60}")
    print(f"  {module_name}")
    print(f"{'=' * 60}")
    try:
        # 找到模块里的 test_* 函数依次运行
        tests = [n for n in dir(module) if n.startswith("test_")]
        for tname in sorted(tests):
            getattr(module, tname)()
        return True
    except Exception as e:
        print(f"\n❌ {module_name} 失败: {e}")
        traceback.print_exc()
        return False


def main():
    import tests.test_statistics as m1
    import tests.test_recorder as m2
    import tests.test_alarm as m3
    import tests.test_report as m4
    import tests.test_measurements as m5

    modules = [
        ("statistics.py",  m1),
        ("recorder.py",    m2),
        ("alarm.py",       m3),
        ("report.py",      m4),
        ("measurements.py", m5),
    ]
    results = [run(name, mod) for name, mod in modules]

    print(f"\n{'=' * 60}")
    passed = sum(results)
    total = len(results)
    print(f"  结果: {passed}/{total} 模块通过")
    print(f"{'=' * 60}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())