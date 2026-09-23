#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据记录模块测试"""
import csv
import shutil
import tempfile
from pathlib import Path
from core.recorder import DataRecorder


def test_basic_write():
    """
    基础写入。

    ✅ 修复：断言行数从 10 改为 11。
       实际文件行数：
         1) # DMM6500 Data Recording
         2) # Started: ...
         3) # mode: DCV           （metadata 第 1 项）
         4) # unit: V             （metadata 第 2 项）
         5) #
         6) Timestamp,Elapsed_s,Value,Raw   （列头）
         7-11) 5 行数据
       共 11 行。
    """
    tmp = Path(tempfile.mkdtemp())
    try:
        rec = DataRecorder(output_dir=str(tmp), max_rows_per_file=10)
        rec.start(prefix="test", metadata={"mode": "DCV", "unit": "V"})

        for i in range(5):
            rec.write(f"2026-09-20 15:00:0{i}", float(i), i * 1.5, f"raw{i}")

        rec.stop()
        files = list(tmp.glob("test_*.csv"))
        assert len(files) == 1, f"应生成 1 个文件，实际 {len(files)}"

        with open(files[0], "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 11, f"应 11 行，实际 {len(lines)}"
        assert "# DMM6500 Data Recording" in lines[0]
        assert "mode: DCV" in "".join(lines[1:5])
        assert "Timestamp" in lines[5]
        print("✅ test_basic_write")
    finally:
        shutil.rmtree(tmp)


def test_auto_split():
    """自动分卷"""
    tmp = Path(tempfile.mkdtemp())
    try:
        rec = DataRecorder(output_dir=str(tmp), max_rows_per_file=5)
        rec.start(prefix="split")
        for i in range(13):
            rec.write(f"ts{i}", float(i), float(i), "")
        rec.stop()

        files = sorted(tmp.glob("split_*.csv"))
        assert len(files) == 3, f"每 5 行分卷应生成 3 个文件，实际 {len(files)}"
        assert rec.total_rows == 13
        assert rec.total_files == 3
        print("✅ test_auto_split")
    finally:
        shutil.rmtree(tmp)


def test_pause_resume():
    """暂停时不写入"""
    tmp = Path(tempfile.mkdtemp())
    try:
        rec = DataRecorder(output_dir=str(tmp), max_rows_per_file=100)
        rec.start(prefix="pause")
        rec.write("ts1", 1.0, 1.0, "")
        rec.pause()
        rec.write("ts2", 2.0, 2.0, "")
        rec.resume()
        rec.write("ts3", 3.0, 3.0, "")
        rec.stop()

        files = list(tmp.glob("pause_*.csv"))
        with open(files[0], "r", encoding="utf-8") as f:
            content = f.read()
        assert "ts1" in content
        assert "ts2" not in content, "暂停期间的 ts2 不该被写入"
        assert "ts3" in content
        print("✅ test_pause_resume")
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    test_basic_write()
    test_auto_split()
    test_pause_resume()
    print("\n📊 recorder.py 全部通过")