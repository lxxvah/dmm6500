#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file DMM6500.py
#   @brief Keysight-style wrapper for Keithley/Tektronix DMM6500 using pure SCPI.

from __future__ import annotations

import struct
import time
import statistics as stats
from typing import Optional, Tuple, List, Literal

import pyvisa
from colorama import init, Fore, Style

try:
    from loading import loading
except Exception:
    class loading:
        def delay_with_loading_indicator(self, seconds: float) -> None:
            time.sleep(seconds)

_ERROR_STYLE   = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_DELAY         = 0.1


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


class DMM6500:
    """Simple SCPI wrapper for Keithley/Tektronix DMM6500."""

    # ============================================================
    # Init / Connect / Disconnect
    # ============================================================
    def __init__(self, auto_connect: bool = True, address: Optional[str] = None,
                 ip_address: Optional[str] = None, debug: bool = False):
        init(autoreset=True)
        self.rm = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.loading = loading()
        self.status = "Not Connected"
        self._idn: Optional[str] = None
        self._address_hint = address
        self._ip_address = ip_address
        self.debug = debug

        if auto_connect:
            self.connect(address=self._address_hint, ip_address=self._ip_address)

    def connect(self, address: Optional[str] = None, ip_address: Optional[str] = None,
                max_retries: int = 3):
        """
        ✅ 修复 #2：首次连接超时
          · open_timeout=10000（10 秒预算，覆盖冷启动开销）
          · 3 次自动重试（间隔 1 秒）
          · VXI-11 (INSTR) 失败后自动尝试 RAW socket (5025)
        """
        ip = ip_address or self._ip_address

        # ============================================================
        # 1) IP 直连（带重试 + 双协议备选）
        # ============================================================
        if ip and not address and not self._address_hint:
            candidates = [
                f"TCPIP0::{ip}::inst0::INSTR",   # VXI-11
                f"TCPIP0::{ip}::5025::SOCKET",   # RAW socket
            ]
            last_error = None

            for attempt in range(1, max_retries + 1):
                for tcpip_address in candidates:
                    inst = None
                    try:
                        print(_SUCCESS_STYLE +
                              f"[连接] 尝试 {attempt}/{max_retries}: {tcpip_address}")

                        # ✅ 关键：显式 open_timeout
                        inst = self.rm.open_resource(tcpip_address, open_timeout=10000)
                        inst.read_termination = '\n'
                        inst.write_termination = '\n'
                        inst.timeout = 20000

                        idn = inst.query("*IDN?").strip()
                        if "DMM6500" in idn:
                            self.instrument = inst
                            self.address = tcpip_address
                            self._idn = idn
                            self.status = "Connected"
                            print(_SUCCESS_STYLE +
                                  f"Connected to DMM6500 via Ethernet at {ip} [{self._idn}]")
                            return
                        else:
                            print(_ERROR_STYLE +
                                  f"Device at '{ip}' is not a DMM6500 (IDN='{idn}').")
                            inst.close()
                            inst = None
                    except Exception as e:
                        last_error = e
                        print(f"[连接] {tcpip_address} 失败: {e}")
                        if inst is not None:
                            try:
                                inst.close()
                            except Exception:
                                pass
                            inst = None

                if attempt < max_retries:
                    print("[连接] 等待 1 秒后重试...")
                    time.sleep(1.0)

            raise ConnectionError(_ERROR_STYLE +
                f"Failed to connect to DMM6500 at IP '{ip}' after {max_retries} retries. "
                f"Last error: {last_error}")

        # ============================================================
        # 2) 显式 VISA 地址
        # ============================================================
        explicit = address or self._address_hint
        if explicit:
            try:
                inst = self.rm.open_resource(explicit, open_timeout=10000)
                inst.read_termination = '\n'
                inst.write_termination = '\n'
                inst.timeout = 20000
                idn = inst.query("*IDN?").strip()
                if "DMM6500" in idn:
                    self.instrument = inst
                    self.address = explicit
                else:
                    inst.close()
                    raise ConnectionError(_ERROR_STYLE +
                        f"Resource '{explicit}' is not a DMM6500 (IDN='{idn}').")
            except Exception as e:
                raise ConnectionError(_ERROR_STYLE +
                    f"Failed to open explicit address '{explicit}': {e}")

        # ============================================================
        # 3) 自动扫描 VISA 资源
        # ============================================================
        if self.instrument is None:
            resources = self.rm.list_resources()
            if self.debug:
                print(f"\n[DEBUG] Found {len(resources)} VISA resources:")
                for r in resources:
                    print(f"[DEBUG]   - {r}")
                print()

            for resource in resources:
                if resource.startswith("TCPIP") or "6500" in resource:
                    if self.debug:
                        print(f"[DEBUG] Trying resource: {resource}")
                    try:
                        inst = self.rm.open_resource(resource, open_timeout=10000)
                        inst.read_termination = '\n'
                        inst.write_termination = '\n'
                        inst.timeout = 20000
                        idn = inst.query("*IDN?").strip()
                        if "DMM6500" in idn:
                            self.instrument = inst
                            self.address = resource
                            break
                        inst.close()
                    except Exception:
                        continue

        if self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Keithley DMM6500 not found.")

        try:
            self.instrument.write("*CLS")
        except Exception:
            pass
        try:
            self._idn = self.instrument.query("*IDN?").strip()
        except Exception:
            self._idn = "Keithley DMM6500"

        self.status = "Connected"
        print(_SUCCESS_STYLE + f"Connected to DMM6500 at {self.address} [{self._idn}]")

    def disconnect(self):
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                print(f"\rDisconnected from DMM6500 at {self.address}")
        self.status = "Not Connected"
        self.instrument = None
        self.address = None

    # ============================================================
    # Helpers / SCPI utilities
    # ============================================================
    def _chk(self):
        if self.status != "Connected" or self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected to DMM6500.")

    def get_current_function(self) -> str:
        self._chk()
        self.instrument.write("SENSe:FUNCtion?")
        return _strip_quotes(self.instrument.read())

    def _ensure_function(self, fn: str) -> None:
        """
        ✅ 修复 #7：用精确匹配（==）而非子串匹配（in），避免误判
        """
        cur = self.get_current_function().upper().strip()
        if fn.upper() != cur:
            self.instrument.write(f"SENSe:FUNCtion '{fn}'")
            self.loading.delay_with_loading_indicator(_DELAY)

    def _read_float_query(self, q: str) -> float:
        self._chk()
        return float(self.instrument.query(q))

    # ============================================================
    # Core configuration helpers
    # ============================================================
    def set_terminals(self, where: str = "FRONt") -> None:
        self._chk()
        w = where.strip().upper()
        if w.startswith("FRON"):
            self.instrument.write("ROUTe:TERMinals FRONt")
        elif w == "REAR":
            self.instrument.write("ROUTe:TERMinals REAR")
        else:
            raise ValueError("Terminals must be 'FRONt' or 'REAR'.")

    def disable_autorange(self, function: Optional[str] = None) -> None:
        self._chk()
        fn = (function or self.get_current_function()).upper()
        if "VOLT" in fn:
            node = "VOLT:DC"
        elif "CURR" in fn:
            node = "CURR:DC"
        elif "FRES" in fn:
            node = "FRES"
        else:
            node = "RES"
        self.instrument.write(f"SENSe:{node}:RANGe:AUTO OFF")
        print(f"\rAutorange disabled for {node}.")

    def set_nplc(self, nplc: float, function: Optional[str] = None) -> None:
        self._chk()
        fn = (function or self.get_current_function()).upper()
        if "VOLT" in fn:
            node = "VOLT:DC"
        elif "CURR" in fn:
            node = "CURR:DC"
        elif "FRES" in fn:
            node = "FRES"
        else:
            node = "RES"
        self.instrument.write(f"SENSe:{node}:NPLC {float(nplc)}")

    def set_autozero(self, state: str = "OFF") -> None:
        self._chk()
        st = state.strip().upper()
        if st not in ("ON", "OFF"):
            raise ValueError("Autozero must be 'ON' or 'OFF'.")
        self.instrument.write(f"SENSe:AZERo {st}")

    def configure(self, measurement_type: str, range_val: float, resolution_val: float) -> None:
        self._chk()
        mt = measurement_type.strip().upper()
        if mt in ("VOLTAGE:DC", "VOLT:DC"):
            self.instrument.write(f"CONFigure:VOLTage:DC {range_val},{resolution_val}")
            self.instrument.write("SENSe:FUNCtion 'VOLT:DC'")
        elif mt in ("CURRENT:DC", "CURR:DC"):
            self.instrument.write(f"CONFigure:CURRent:DC {range_val},{resolution_val}")
            self.instrument.write("SENSe:FUNCtion 'CURR:DC'")
        elif mt in ("FRESISTANCE", "FRES"):
            self.instrument.write(f"CONFigure:FRESistance {range_val},{resolution_val}")
            self.instrument.write("SENSe:FUNCtion 'FRES'")
        elif mt in ("RESISTANCE", "RES"):
            self.instrument.write(f"CONFigure:RESistance {range_val},{resolution_val}")
            self.instrument.write("SENSe:FUNCtion 'RES'")
        else:
            raise ValueError(_ERROR_STYLE + f"Unsupported measurement_type: {measurement_type}")
        print(f"\rConfigured {mt} Range={range_val}, Resolution={resolution_val}")

    # ============================================================
    # One-shot DC measurements
    # ============================================================
    def measure_voltage(self) -> float:
        self._ensure_function("VOLT:DC")
        return self._read_float_query("MEASure:VOLTage:DC?")

    def measure_current(self) -> float:
        self._ensure_function("CURR:DC")
        return self._read_float_query("MEASure:CURRent:DC?")

    def measure_resistance(self, four_wire: bool = False) -> float:
        if four_wire:
            self._ensure_function("FRES")
            return self._read_float_query("MEASure:FRESistance?")
        else:
            self._ensure_function("RES")
            return self._read_float_query("MEASure:RESistance?")

    # ============================================================
    # AC measurements
    # ============================================================
    def measure_voltage_ac(self) -> float:
        """AC voltage via MEASure:VOLTage:AC?"""
        self._ensure_function("VOLT:AC")
        return self._read_float_query("MEASure:VOLTage:AC?")

    def measure_current_ac(self) -> float:
        """AC current via MEASure:CURRent:AC?"""
        self._ensure_function("CURR:AC")
        return self._read_float_query("MEASure:CURRent:AC?")

    # ============================================================
    # Capacitance
    # ============================================================
    def measure_capacitance(self) -> float:
        """Capacitance via MEASure:CAPacitance?"""
        self._ensure_function("CAP")
        return self._read_float_query("MEASure:CAPacitance?")

    # ============================================================
    # Frequency / Period
    # ============================================================
    def measure_frequency(self) -> float:
        """Frequency via MEASure:FREQuency?"""
        self._ensure_function("FREQ")
        return self._read_float_query("MEASure:FREQuency?")

    def measure_period(self) -> float:
        """Period via MEASure:PERiod?"""
        self._ensure_function("PER")
        return self._read_float_query("MEASure:PERiod?")

    # ============================================================
    # Temperature
    # ============================================================
    def measure_temperature(self, transducer: str = "TC", tc_type: str = "K") -> float:
        """
        测量温度。
        transducer: "TC" (热电偶) | "FRTD" (4线RTD) | "THER" (热敏电阻)
        tc_type:    仅当 transducer="TC" 时有效，如 "K", "J", "T", "E" ...
        """
        self._chk()
        tr = transducer.strip().upper()
        try:
            if tr == "TC":
                self.instrument.write("SENSe:TEMPerature:TRANsducer TC")
                self.instrument.write(f"SENSe:TEMPerature:TCouple:TYPE {tc_type}")
            elif tr == "FRTD":
                self.instrument.write("SENSe:TEMPerature:TRANsducer FRTD")
            elif tr == "THER":
                self.instrument.write("SENSe:TEMPerature:TRANsducer THER")
            else:
                raise ValueError(f"未知温度传感器类型: {transducer}")
        except Exception as e:
            raise ConnectionError(f"配置温度传感器失败: {e}")

        self.instrument.write("SENSe:FUNCtion 'TEMP'")
        return self._read_float_query("MEASure:TEMPerature?")

    # ============================================================
    # Continuity / Diode
    # ============================================================
    def measure_continuity(self) -> float:
        """
        ✅ 修复 #8：使用完整 SCPI 拼写，兼容性更好
        返回电阻（Ω）。若超量程会返回很大的值（如 9.9E37）。
        """
        self._ensure_function("CONT")
        return self._read_float_query("MEASure:CONTinuity?")

    def measure_diode(self) -> float:
        """
        ✅ 修复 #8：使用完整 SCPI 拼写
        返回正向压降（V）。
        """
        self._ensure_function("DIOD")
        return self._read_float_query("MEASure:DIODe?")

    # ============================================================
    # High-level dispatcher
    # ============================================================
    def get(self, item: str):
        k = item.strip().lower()
        if   k == "voltage":         return self.measure_voltage()
        elif k == "current":         return self.measure_current()
        elif k == "resistance":      return self.measure_resistance(False)
        elif k == "voltage_ac":      return self.measure_voltage_ac()
        elif k == "current_ac":      return self.measure_current_ac()
        elif k == "capacitance":     return self.measure_capacitance()
        elif k == "frequency":       return self.measure_frequency()
        elif k == "temperature":     return self.measure_temperature()
        elif k == "statistics":      return self.calculate_statistics()
        else:
            raise ValueError(_ERROR_STYLE + f"Invalid item: {item} request to DMM6500")

    # ============================================================
    # Host-side statistics
    # ============================================================
    def calculate_statistics(self, n: int = 100,
                             measurement_type: Optional[str] = None,
                             delay_s: float = 0.0) -> Tuple[float, float, float, float]:
        self._chk()

        def oneshot() -> float:
            if measurement_type is None:
                fn = self.get_current_function().upper()
                if   "VOLT" in fn: return self.measure_voltage()
                elif "CURR" in fn: return self.measure_current()
                elif "FRES" in fn: return self.measure_resistance(True)
                else:              return self.measure_resistance(False)
            mt = measurement_type.strip().upper()
            if   mt in ("VOLTAGE:DC", "VOLT:DC"): return self.measure_voltage()
            if   mt in ("CURRENT:DC", "CURR:DC"): return self.measure_current()
            if   mt in ("FRESISTANCE", "FRES"):   return self.measure_resistance(True)
            if   mt in ("RESISTANCE", "RES"):     return self.measure_resistance(False)
            raise ValueError(_ERROR_STYLE + f"Unsupported measurement_type: {measurement_type}")

        vals: List[float] = []
        for _ in range(max(1, int(n))):
            vals.append(oneshot())
            if delay_s > 0:
                time.sleep(delay_s)

        mean = stats.fmean(vals)
        stdev = stats.pstdev(vals) if len(vals) > 1 else 0.0
        vmin = min(vals)
        vmax = max(vals)
        return mean, stdev, vmin, vmax

    # ============================================================
    # Buffer trace fetching
    # ============================================================
    def fetch_trace(self, buffer: str = "defbuffer1", chunk: int = 50000,
                    debug: bool = True, step: bool = True):
        self._chk()
        inst = self.instrument

        import datetime
        def _now():
            return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

        def _pause(where: str):
            if not step:
                return
            try:
                input(f"[{_now()}] {where}  —  press Enter to continue...")
            except Exception:
                pass

        def _log(msg: str):
            if debug:
                print(f"[{_now()}] {msg}")

        def _query(cmd: str) -> str:
            _log(f"QUERY: {cmd}")
            rsp = inst.query(cmd).strip()
            _log(f"  -> '{rsp}'")
            _pause(f"Query: {cmd}")
            return rsp

        def _query_ascii(cmd: str):
            _log(f"QUERY_ASCII: {cmd}")
            vals = inst.query_ascii_values(cmd, container=list)
            _log(f"  -> {len(vals)} numbers")
            _pause(f"Query ASCII: {cmd}")
            return vals

        try:
            n = int(_query(f"TRACe:ACTual? '{buffer}'"))
        except Exception:
            n = int(_query(f"TRACe:ACTual? {buffer}"))

        _log(f"BUFFER COUNT: {n}")
        if n <= 0:
            return [], None

        values: List[float] = []
        start = 1
        chunk = max(1, int(chunk))
        while start <= n:
            stop = min(start + chunk - 1, n)
            try:
                raw = _query_ascii(f"TRACe:DATA? {start},{stop},'{buffer}'")
            except Exception:
                raw = _query_ascii(f"TRACe:DATA? {start},{stop},{buffer}")
            values.extend(float(v) for v in raw)
            start = stop + 1
        return values, None