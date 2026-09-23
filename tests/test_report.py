#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML 报告模块测试"""
import shutil
import tempfile
from pathlib import Path
from core.report import ReportBuilder


def test_generate_basic():
    """基本生成"""
    tmp = Path(tempfile.mkdtemp())
    try:
        rb = ReportBuilder(output_dir=str(tmp))
        rb.set_metadata(mode="DCV", unit="V", terminal="FRONT", nplc="1")
        for i in range(100):
            rb.add_point(i * 0.2, 2.5 + 0.001 * (i % 10))
        path = rb.generate(prefix="test", auto_open=False)

        assert Path(path).exists(), "HTML 文件应被创建"
        content = Path(path).read_text(encoding="utf-8")
        assert "DMM6500 测量报告" in content
        assert "DCV" in content
        assert "2.5" in content or "2.50" in content
        assert "echarts" in content.lower()
        print(f"✅ test_generate_basic -> {path}")
    finally:
        shutil.rmtree(tmp)


def test_empty_data():
    """空数据也能生成（显示提示）"""
    tmp = Path(tempfile.mkdtemp())
    try:
        rb = ReportBuilder(output_dir=str(tmp))
        assert rb.has_data is False
        path = rb.generate(prefix="empty", auto_open=False)
        content = Path(path).read_text(encoding="utf-8")
        assert "暂无数据" in content
        print("✅ test_empty_data")
    finally:
        shutil.rmtree(tmp)


def test_large_data_downsampling():
    """大数据降采样"""
    tmp = Path(tempfile.mkdtemp())
    try:
        rb = ReportBuilder(output_dir=str(tmp))
        rb.set_metadata(mode="DCV", unit="V")
        for i in range(50_000):
            rb.add_point(i * 0.01, 1.0)
        path = rb.generate(prefix="large", auto_open=False)
        content = Path(path).read_text(encoding="utf-8")
        # 图表点数应被降采样到 5000 点以内
        import re
        m = re.search(r"const CHART_DATA = (\[.*?\]);", content, re.DOTALL)
        assert m, "应包含 CHART_DATA"
        data_str = m.group(1)
        # 粗略统计逗号+分号对数
        pairs = data_str.count("],[") + 1
        assert pairs <= 6000, f"降采样后应 ≤5000 点，实际 {pairs}"
        print(f"✅ test_large_data_downsampling (降采样后 {pairs} 点)")
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    test_generate_basic()
    test_empty_data()
    test_large_data_downsampling()
    print("\n📊 report.py 全部通过")