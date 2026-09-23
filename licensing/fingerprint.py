#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing/fingerprint.py —— 硬件指纹采集
=============================================
跨平台采集 CPU / 主板 / 磁盘序列号，生成稳定机器码。

优化点：
  · 模块级缓存：进程内只计算一次，后续调用 0ms
  · Windows 平台合并为一次 PowerShell 调用（3 倍提速）
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
import uuid
from typing import List, Optional


# ============================================================
# 缓存（进程内只算一次）
# ============================================================
_full_code_cache: Optional[str] = None


# ============================================================
# 内部工具
# ============================================================
def _run(cmd: List[str], timeout: float = 6.0) -> str:
    kwargs = {
        "text": True,
        "timeout": timeout,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        # CREATE_NO_WINDOW：避免弹黑框
        kwargs["creationflags"] = 0x08000000
    try:
        return subprocess.check_output(cmd, **kwargs).strip()
    except Exception:
        return ""


# ============================================================
# Windows：一次 PowerShell 拿全部信息
# ============================================================
def _win_components() -> List[str]:
    """一次 PowerShell 调用拿到 CPU / 主板 / 磁盘序列号。"""
    ps_script = (
        "$cpu = (Get-CimInstance Win32_Processor).ProcessorId; "
        "$uuid = (Get-CimInstance Win32_ComputerSystemProduct).UUID; "
        "$vol = (Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\").VolumeSerialNumber; "
        'Write-Output "$cpu|$uuid|$vol"'
    )

    out = _run([
        "powershell", "-NoProfile", "-Command", ps_script
    ], timeout=10.0)

    parts: List[str] = []
    if out:
        # 取第一行，按 | 拆分
        line = out.splitlines()[0].strip() if out.splitlines() else ""
        fields = line.split("|")
        if len(fields) >= 1 and fields[0].strip():
            parts.append("cpu:" + fields[0].strip())
        if len(fields) >= 2 and fields[1].strip():
            parts.append("mb:" + fields[1].strip())
        if len(fields) >= 3 and fields[2].strip():
            parts.append("vol:" + fields[2].strip())

    return parts


# ============================================================
# Linux / macOS
# ============================================================
def _linux_components() -> List[str]:
    parts: List[str] = []
    for path, tag in [
        ("/etc/machine-id", "mid"),
        ("/sys/class/dmi/id/product_uuid", "uuid"),
    ]:
        try:
            with open(path) as f:
                parts.append(f"{tag}:" + f.read().strip())
        except Exception:
            pass
    return parts


def _mac_components() -> List[str]:
    parts: List[str] = []
    out = _run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
    for line in out.splitlines():
        if "IOPlatformUUID" in line:
            try:
                parts.append("uuid:" + line.split('"')[-2])
            except Exception:
                pass
            break
    return parts


# ============================================================
# 核心计算（不缓存，只被 get_machine_code 调用一次）
# ============================================================
def _compute_full_code() -> str:
    """计算完整 SHA256 hex 机器码。"""
    if sys.platform == "win32":
        parts = _win_components()
    elif sys.platform == "darwin":
        parts = _mac_components()
    else:
        parts = _linux_components()

    # MAC 地址
    try:
        mac = uuid.getnode()
        if mac and mac != 0:
            parts.append(f"mac:{mac:012x}")
    except Exception:
        pass

    if not parts:
        parts.append("fallback:" + platform.node())

    raw = "|".join(sorted(parts)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


# ============================================================
# 对外 API
# ============================================================
def get_machine_code(short: bool = True) -> str:
    """
    返回本机机器码。

    优化：结果在进程内缓存，第一次约 1~2 秒，之后 0ms。

    Args:
        short: True → 19 字符短码（A3F5-9B21-C8E4-7D02）
               False → 完整 SHA256 hex

    Returns:
        机器码字符串
    """
    global _full_code_cache
    if _full_code_cache is None:
        _full_code_cache = _compute_full_code()

    if short:
        return "-".join(_full_code_cache[i:i + 4] for i in range(0, 16, 4))
    return _full_code_cache


def clear_cache() -> None:
    """清空缓存（仅调试用）。"""
    global _full_code_cache
    _full_code_cache = None