#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测量功能注册表测试（无硬件）"""
from core.measurements import MODE_REGISTRY, get_mode_info, list_modes


def test_all_modes_registered():
    """所有 12 种功能都应注册"""
    expected = ["DCV", "DCI", "RES2W", "RES4W",
                "ACV", "ACI", "CAP", "FREQ", "PER",
                "TEMP", "CONT", "DIOD"]
    for mode in expected:
        assert mode in MODE_REGISTRY, f"缺少功能: {mode}"
    print(f"✅ test_all_modes_registered ({len(MODE_REGISTRY)} 种)")


def test_mode_info_fields():
    """每个 ModeInfo 的字段完整性"""
    for name, info in MODE_REGISTRY.items():
        assert info.func, f"{name}: func 为空"
        assert info.node, f"{name}: node 为空"
        assert info.meas.startswith("MEAS:"), f"{name}: meas 命令格式错"
        assert info.unit, f"{name}: unit 为空"
        assert info.y_label, f"{name}: y_label 为空"
        assert info.category in ("DC", "AC", "FREQ", "TEMP", "CONT"), \
            f"{name}: category 未知 {info.category}"
    print("✅ test_mode_info_fields")


def test_category_attributes():
    """AC 类不带 NPLC / AZERO"""
    for name in ["ACV", "ACI", "CAP"]:
        info = get_mode_info(name)
        assert info.supports_nplc is False, f"{name} 不应支持 NPLC"
        assert info.supports_autozero is False, f"{name} 不应支持 AZERO"
    # DC 类应支持
    for name in ["DCV", "DCI", "RES2W", "RES4W"]:
        info = get_mode_info(name)
        assert info.supports_nplc is True
        assert info.supports_autozero is True
    print("✅ test_category_attributes")


def test_get_invalid():
    """未知功能应抛异常"""
    try:
        get_mode_info("XXX")
        assert False, "未知功能应抛 ValueError"
    except ValueError:
        pass
    print("✅ test_get_invalid")


def test_extra_cmds():
    """TEMP 有额外命令"""
    info = get_mode_info("TEMP")
    assert len(info.extra_cmds) > 0, "TEMP 应有 extra_cmds"
    assert any("TEMP" in cmd.upper() for cmd in info.extra_cmds)
    print("✅ test_extra_cmds")


if __name__ == "__main__":
    test_all_modes_registered()
    test_mode_info_fields()
    test_category_attributes()
    test_get_invalid()
    test_extra_cmds()
    print("\n📊 measurements.py 全部通过")