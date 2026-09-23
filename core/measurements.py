#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/measurements.py —— 测量功能模块
=======================================
状态文本 ≤3 字
"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass
from typing import Optional, List, Tuple

from PyQt6.QtCore import QThread, pyqtSignal

from core.connection import ConnectionManager


def log(msg):
    print(msg, flush=True)


@dataclass
class ModeInfo:
    func: str
    node: str
    meas: str
    unit: str
    y_label: str
    category: str = "DC"
    supports_nplc: bool = True
    supports_autozero: bool = True
    supports_range: bool = True
    extra_cmds: Tuple[str, ...] = ()


MODE_REGISTRY = {
    "DCV":   ModeInfo(func="VOLT:DC", node="VOLT:DC", meas="MEAS:VOLT:DC?", unit="V",  y_label="电压", category="DC"),
    "DCI":   ModeInfo(func="CURR:DC", node="CURR:DC", meas="MEAS:CURR:DC?", unit="A",  y_label="电流", category="DC"),
    "RES2W": ModeInfo(func="RES",     node="RES",     meas="MEAS:RES?",     unit="Ω",  y_label="电阻(2线)", category="DC"),
    "RES4W": ModeInfo(func="FRES",    node="FRES",    meas="MEAS:FRES?",    unit="Ω",  y_label="电阻(4线)", category="DC"),
    "ACV":   ModeInfo(func="VOLT:AC", node="VOLT:AC", meas="MEAS:VOLT:AC?", unit="V",  y_label="交流电压", category="AC",
                      supports_nplc=False, supports_autozero=False),
    "ACI":   ModeInfo(func="CURR:AC", node="CURR:AC", meas="MEAS:CURR:AC?", unit="A",  y_label="交流电流", category="AC",
                      supports_nplc=False, supports_autozero=False),
    "CAP":   ModeInfo(func="CAP",     node="CAP",     meas="MEAS:CAP?",     unit="F",  y_label="电容",     category="AC",
                      supports_nplc=False, supports_autozero=False),
    "FREQ":  ModeInfo(func="FREQ",    node="FREQ",    meas="MEAS:FREQ?",    unit="Hz", y_label="频率", category="FREQ",
                      supports_nplc=False, supports_autozero=False, supports_range=False),
    "PER":   ModeInfo(func="PER",     node="PER",     meas="MEAS:PER?",     unit="s",  y_label="周期", category="FREQ",
                      supports_nplc=False, supports_autozero=False, supports_range=False),
    "TEMP":  ModeInfo(func="TEMP",    node="TEMP",    meas="MEAS:TEMP?",    unit="°C", y_label="温度", category="TEMP",
                      supports_nplc=False, supports_autozero=False, supports_range=False,
                      extra_cmds=("SENS:TEMP:TRAN TC", "SENS:TEMP:TC:TYPE K")),
    "CONT":  ModeInfo(func="CONT",    node="CONT",    meas="MEAS:CONTinuity?", unit="Ω",  y_label="通断", category="CONT",
                      supports_nplc=False, supports_autozero=False, supports_range=False),
    "DIOD":  ModeInfo(func="DIOD",    node="DIOD",    meas="MEAS:DIODe?",      unit="V",  y_label="二极管", category="DC",
                      supports_range=False),
}


def get_mode_info(mode: str) -> ModeInfo:
    if mode not in MODE_REGISTRY:
        raise ValueError(f"未知测量功能: {mode}")
    return MODE_REGISTRY[mode]


def list_modes() -> List[str]:
    return list(MODE_REGISTRY.keys())


class MeasurementWorker(QThread):
    data_ready       = pyqtSignal(str, float)
    error_occurred   = pyqtSignal(str)
    connected_info   = pyqtSignal(str)
    status_update    = pyqtSignal(str)
    instrument_error = pyqtSignal(str)

    def __init__(self, ip_address: str, config: dict, interval_ms: int = 200):
        super().__init__()
        # ip_address 字段复用：既可能是 "192.168.x.x"，也可能是
        # "USB0::0x05E6::0x6500::xxxx::INSTR" 之类的 VISA 地址
        self.ip_address = ip_address
        self.config = config
        self.interval_ms = interval_ms
        self.running = False
        self.conn: Optional[ConnectionManager] = None

    # ✅ 修复 #5：自动区分 IP / VISA 地址
    def _connect(self):
        self.conn = ConnectionManager()
        addr = self.ip_address or ""
        if "::" in addr:
            log(f"[后台] 使用 VISA 地址连接: {addr}")
            self.conn.connect(address=addr)
        else:
            log(f"[后台] 使用 IP 连接: {addr}")
            self.conn.connect(ip=addr)
        self.connected_info.emit(str(self.conn.address))
        return self.conn.instrument

    def _safe_write(self, inst, cmd: str):
        try:
            inst.write(cmd)
        except Exception as e:
            log(f"[配置] 命令失败（忽略）: {cmd} -> {e}")

    def _check_instrument_error(self, inst):
        try:
            err = inst.query("SYST:ERR?").strip()
            if err and not (err.startswith("+0") or err.startswith("0,")):
                log(f"[仪器错误] {err}")
                self.instrument_error.emit(err)
        except Exception:
            pass

    def _apply_config(self, inst):
        cfg = self.config
        info = get_mode_info(cfg["mode"])
        log(f"[配置] 开始配置: mode={cfg['mode']}, func={info.func}, cat={info.category}")

        self._safe_write(inst, '*RST')
        time.sleep(0.5)
        self._safe_write(inst, 'TRIG:SOUR IMM')
        self._safe_write(inst, 'TRIG:COUN 1')
        self._safe_write(inst, f'SENS:FUNC "{info.func}"')
        time.sleep(0.2)

        term = "FRON" if cfg["terminal"] == "FRONT" else "REAR"
        self._safe_write(inst, f'ROUT:TERM {term}')

        if info.category in ("DC", "DIOD"):
            if info.supports_range:
                if cfg["auto_range"]:
                    self._safe_write(inst, f'SENS:{info.node}:RANG:AUTO ON')
                else:
                    self._safe_write(inst, f'SENS:{info.node}:RANG:AUTO OFF')
                    self._safe_write(inst, f'SENS:{info.node}:RANG {cfg["range_val"]}')
            if info.supports_nplc:
                self._safe_write(inst, f'SENS:{info.node}:NPLC {cfg["nplc"]}')
            if info.supports_autozero:
                self._safe_write(inst, f'SENS:AZER {"ON" if cfg["autozero"] else "OFF"}')
        elif info.category == "AC":
            if cfg["auto_range"]:
                self._safe_write(inst, f'SENS:{info.node}:RANG:AUTO ON')
            else:
                self._safe_write(inst, f'SENS:{info.node}:RANG:AUTO OFF')
                self._safe_write(inst, f'SENS:{info.node}:RANG {cfg["range_val"]}')
        elif info.category == "FREQ":
            if not cfg["auto_range"]:
                try:
                    self._safe_write(inst, f'SENS:FREQ:THR:VOLT:RANG {float(cfg["range_val"])}')
                except Exception:
                    pass

        for cmd in info.extra_cmds:
            self._safe_write(inst, cmd)

        log(f"[配置] ✅ {cfg['mode']} 配置完成")

    def run(self):
        self.running = True
        try:
            self.status_update.emit("连接中")
            log("[后台] 正在连接仪器...")
            inst = self._connect()
            log("[后台] ✅ 连接成功")

            self.status_update.emit("配置中")
            self._apply_config(inst)

            try:
                while True:
                    e = inst.query("SYST:ERR?").strip()
                    if e.startswith("+0") or e.startswith("0,"):
                        break
            except Exception:
                pass

            info = get_mode_info(self.config["mode"])
            self.status_update.emit("测量中")
            log(f"[后台] 开始读取 ({self.config['mode']})...")

            count = 0
            error_count = 0
            while self.running:
                try:
                    val_str = inst.query(info.meas).strip()
                    value = float(val_str)
                    self.data_ready.emit(val_str, value)
                    count += 1
                    if count % 10 == 0:
                        log(f"[后台] 已读取 {count} 个，最新: {val_str}")
                        self._check_instrument_error(inst)
                except Exception as e:
                    error_count += 1
                    log(f"[读取错误 #{error_count}] {e}")
                    self._check_instrument_error(inst)
                    if error_count > 20:
                        raise RuntimeError("读取错误次数过多，停止测量")
                time.sleep(self.interval_ms / 1000.0)

        except Exception as e:
            err_full = f"连接或测量失败: {str(e)}\n\n{traceback.format_exc()}"
            log(err_full)
            self.error_occurred.emit(err_full)
        finally:
            if self.conn:
                try:
                    self.conn.disconnect()
                except Exception:
                    pass

    def stop(self):
        self.running = False
        self.wait(2000)