#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/connection.py —— 连接管理模块
"""

from __future__ import annotations

import time
import traceback
from typing import Optional, List

import pyvisa
from PyQt6.QtCore import QThread, pyqtSignal

from libs.DMM6500 import DMM6500


def log(msg):
    print(msg, flush=True)


class ScanWorker(QThread):
    scan_finished = pyqtSignal(str)
    scan_failed = pyqtSignal(str)

    def __init__(self, hint_ip: str = ""):
        super().__init__()
        self.hint_ip = hint_ip.strip()

    def _try_connect(self, resource: str, rm) -> Optional[str]:
        """
        ✅ 修复 #5：TCPIP 返回纯 IP；USB/GPIB 返回完整 VISA 地址。
                    两种形式都由上层统一送入输入框，连接时按是否含 '::' 分流。
        """
        try:
            log(f"[扫描] 尝试: {resource}")
            inst = rm.open_resource(resource, open_timeout=1500)
            inst.timeout = 3000
            idn = inst.query("*IDN?").strip()
            log(f"[扫描]   响应: {idn}")
            inst.close()
            if "DMM6500" in idn:
                if "TCPIP" in resource:
                    # 返回纯 IP
                    parts = resource.split("::")
                    if len(parts) >= 2:
                        return parts[1]
                # USB / GPIB 等：返回完整 VISA 地址
                return resource
        except Exception as e:
            log(f"[扫描]   失败: {e}")
        return None

    def run(self):
        try:
            rm = pyvisa.ResourceManager()

            for resource in rm.list_resources():
                if (resource.startswith("TCPIP")
                        or "6500" in resource
                        or "0x05E6" in resource.upper()):
                    ip = self._try_connect(resource, rm)
                    if ip:
                        self.scan_finished.emit(ip)
                        return

            try:
                for resource in rm.list_resources("TCPIP?*INSTR"):
                    ip = self._try_connect(resource, rm)
                    if ip:
                        self.scan_finished.emit(ip)
                        return
            except Exception:
                pass

            candidates: List[str] = []
            if self.hint_ip:
                candidates.append(self.hint_ip)
            for ip in ["192.168.1.122", "192.168.1.100",
                       "192.168.1.1", "169.254.20.99"]:
                if ip not in candidates:
                    candidates.append(ip)

            log(f"[扫描] 将主动尝试: {candidates}")
            for ip in candidates:
                resource = f"TCPIP0::{ip}::inst0::INSTR"
                result = self._try_connect(resource, rm)
                if result:
                    self.scan_finished.emit(result)
                    return

            self.scan_failed.emit(
                "未找到 DMM6500。\n"
                "请确认仪器已开机、网线已连接，或直接手动输入 IP。"
            )

        except Exception as e:
            err = f"扫描异常: {str(e)}\n{traceback.format_exc()}"
            log(err)
            self.scan_failed.emit(str(e))


class ConnectionManager:
    def __init__(self):
        self._dmm: Optional[DMM6500] = None
        self._inst = None
        self._address: Optional[str] = None

    @property
    def instrument(self):
        if self._inst is None:
            raise ConnectionError("尚未连接仪器")
        return self._inst

    @property
    def address(self) -> Optional[str]:
        return self._address

    @property
    def is_connected(self) -> bool:
        return self._inst is not None

    @property
    def dmm(self) -> Optional[DMM6500]:
        return self._dmm

    def connect(self, ip: str = "", address: str = "") -> None:
        if self._inst is not None:
            self.disconnect()

        max_outer_retries = 2
        last_error = None

        for attempt in range(1, max_outer_retries + 1):
            try:
                if address:
                    log(f"[连接] 使用 VISA 地址: {address} (尝试 {attempt}/{max_outer_retries})")
                    self._dmm = DMM6500(auto_connect=False, address=address)
                    self._dmm.connect(address=address)
                elif ip:
                    log(f"[连接] 使用 IP: {ip} (尝试 {attempt}/{max_outer_retries})")
                    self._dmm = DMM6500(auto_connect=False, ip_address=ip)
                    self._dmm.connect(ip_address=ip)
                else:
                    log("[连接] 自动识别模式")
                    self._dmm = DMM6500(auto_connect=False)
                    self._dmm.connect()

                self._inst = self._dmm.instrument
                self._address = self._dmm.address

                self._ensure_scpi_mode()

                log(f"[连接] ✅ 已连接: {self._address}")
                return

            except Exception as e:
                last_error = e
                log(f"[连接] 第 {attempt} 次尝试失败: {e}")

                if self._dmm is not None:
                    try:
                        self._dmm.disconnect()
                    except Exception as de:
                        log(f"[连接] 清理时出错（忽略）: {de}")
                self._inst = None
                self._dmm = None
                self._address = None

                if attempt < max_outer_retries:
                    log("[连接] 等待 2 秒后重试...")
                    time.sleep(2.0)

        raise ConnectionError(f"连接失败（已重试 {max_outer_retries} 次）: {last_error}")

    def disconnect(self) -> None:
        if self._dmm is not None:
            try:
                self._dmm.disconnect()
            except Exception as e:
                log(f"[连接] 断开时异常（可忽略）: {e}")
        self._dmm = None
        self._inst = None
        self._address = None
        log("[连接] 已断开")

    # ✅ 修复 #6：查询失败时不再静默放过；用 *IDN? 二次探测，
    #            探测也失败 → 抛异常，避免后续所有 SCPI 命令莫名报错
    def _ensure_scpi_mode(self) -> None:
        try:
            lang = self._inst.query("*LANG?").strip()
            log(f"[命令集] 当前语言: {lang}")
        except Exception as e:
            log(f"[命令集] *LANG? 查询失败: {e}")
            try:
                self._inst.query("*IDN?").strip()
                log("[命令集] 探测成功，假定为 SCPI 模式继续")
                return
            except Exception as probe_err:
                raise ConnectionError(
                    f"仪器通信异常，无法确认命令集: {probe_err}"
                )

        lang_clean = lang.strip('"').strip("'").upper()
        if "SCPI" in lang_clean:
            log("[命令集] ✅ 已经是 SCPI 模式")
            return

        log(f"[命令集] ⚠️ 检测到 {lang_clean}，发送 *LANG SCPI")
        try:
            self._inst.write("*LANG SCPI")
            time.sleep(0.5)
        except Exception as e:
            log(f"[命令集] 切换失败: {e}")

        raise ConnectionError(
            "命令集不是 SCPI 模式，已发送切换指令。\n"
            "请手动断电重启 DMM6500，然后重新连接。"
        )


_default_conn: Optional[ConnectionManager] = None


def get_connection() -> ConnectionManager:
    global _default_conn
    if _default_conn is None:
        _default_conn = ConnectionManager()
    return _default_conn