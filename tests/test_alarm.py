#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报警模块测试"""
import shutil
import tempfile
from pathlib import Path
from core.alarm import AlarmManager


def test_above_trigger():
    """高于阈值触发"""
    tmp = Path(tempfile.mkdtemp())
    try:
        am = AlarmManager(log_dir=str(tmp), sound_enabled=False)
        triggered = []
        am.add_rule("c1", threshold=5.0, mode="above",
                    on_trigger=lambda v: triggered.append(v))

        assert am.check("c1", 4.0) is False   # 未越界
        assert am.check("c1", 6.0) is True    # 越界 → 触发
        assert am.check("c1", 7.0) is False   # 持续越界 → 不重复触发
        assert am.check("c1", 4.0) is False   # 恢复
        assert am.check("c1", 6.5) is True    # 再次越界 → 再次触发
        assert len(triggered) == 2
        print("✅ test_above_trigger")
    finally:
        shutil.rmtree(tmp)


def test_below_trigger():
    """低于阈值触发"""
    tmp = Path(tempfile.mkdtemp())
    try:
        am = AlarmManager(log_dir=str(tmp), sound_enabled=False)
        am.add_rule("c1", threshold=0.0, mode="below")
        assert am.check("c1", 0.5) is False
        assert am.check("c1", -0.1) is True
        assert am.check("c1", -0.5) is False   # 持续 → 不重复
        print("✅ test_below_trigger")
    finally:
        shutil.rmtree(tmp)


def test_disable_enable():
    """禁用后不触发"""
    tmp = Path(tempfile.mkdtemp())
    try:
        am = AlarmManager(log_dir=str(tmp), sound_enabled=False)
        am.add_rule("c1", threshold=5.0, mode="above")
        am.set_enabled("c1", False)
        assert am.check("c1", 10.0) is False
        am.set_enabled("c1", True)
        assert am.check("c1", 10.0) is True
        print("✅ test_disable_enable")
    finally:
        shutil.rmtree(tmp)


def test_log_file():
    """验证日志文件被写入"""
    tmp = Path(tempfile.mkdtemp())
    try:
        am = AlarmManager(log_dir=str(tmp), sound_enabled=False)
        am.add_rule("c1", threshold=5.0, mode="above")
        am.check("c1", 6.0)
        log_file = tmp / "alarm_log.txt"
        assert log_file.exists(), "日志文件应被创建"
        content = log_file.read_text(encoding="utf-8")
        assert "ALARM #1" in content
        assert "curve=c1" in content
        print("✅ test_log_file")
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    test_above_trigger()
    test_below_trigger()
    test_disable_enable()
    test_log_file()
    print("\n📊 alarm.py 全部通过")