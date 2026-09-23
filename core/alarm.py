#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/alarm.py —— 触发/报警模块
=================================
✅ 双轨记录：磁盘文件（历史）+ 内存列表（当前会话）
✅ 支持两类记录：
   · 规则触发报警（ALARM #N）
   · 仪器错误（ERROR）—— 由 MeasurementWorker 上报

内存限制：
  · _records 使用 deque(maxlen=MAX_MEMORY_RECORDS)
  · 超过 10000 条后自动丢弃最老的（磁盘日志仍完整）
"""

from __future__ import annotations

import os
import math
import time
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional


# ✅ 内存中最多保留的报警条数（磁盘日志无限制）
MAX_MEMORY_RECORDS = 10_000


@dataclass
class AlarmRule:
    id: int
    curve_id: str
    threshold: float
    mode: str = "above"
    enabled: bool = True
    active: bool = False
    trigger_count: int = 0
    last_trigger_time: Optional[float] = None


@dataclass
class AlarmRecord:
    """内存记录（含报告时间轴上的 elapsed_s）"""
    timestamp: str
    elapsed_s: Optional[float]
    text: str
    rule_id: int          # -1 表示仪器错误
    count: int
    value: float
    threshold: float
    mode: str
    kind: str = "rule"    # "rule" | "instrument"


class AlarmManager:
    def __init__(self, log_dir: str = "./data", sound_enabled: bool = True):
        self.rules: List[AlarmRule] = []
        self._next_id = 1
        self._callback: Optional[Callable] = None

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "alarm_log.txt"
        self.sound_enabled = sound_enabled
        self._lock = threading.Lock()

        # ✅ 用 deque 限制内存条数
        self._records: deque = deque(maxlen=MAX_MEMORY_RECORDS)

    # ---------- 回调 ----------
    def set_callback(self, cb: Optional[Callable]) -> None:
        self._callback = cb

    # ---------- 规则管理 ----------
    def add_rule(self, curve_id: str, threshold: float, mode: str = "above") -> int:
        if mode not in ("above", "below"):
            raise ValueError("mode 必须是 'above' 或 'below'")
        with self._lock:
            rid = self._next_id
            self._next_id += 1
            self.rules.append(AlarmRule(
                id=rid, curve_id=curve_id,
                threshold=float(threshold), mode=mode,
            ))
            return rid

    def remove_rule(self, rule_id: int) -> None:
        with self._lock:
            self.rules = [r for r in self.rules if r.id != rule_id]

    def clear_rules_for_curve(self, curve_id: str) -> None:
        with self._lock:
            self.rules = [r for r in self.rules if r.curve_id != curve_id]

    def clear_rules(self) -> None:
        with self._lock:
            self.rules.clear()

    def get_rules(self, curve_id: Optional[str] = None) -> List[AlarmRule]:
        with self._lock:
            if curve_id is None:
                return list(self.rules)
            return [r for r in self.rules if r.curve_id == curve_id]

    def set_rule_enabled(self, rule_id: int, enabled: bool) -> None:
        with self._lock:
            for r in self.rules:
                if r.id == rule_id:
                    r.enabled = enabled
                    break

    # ---------- 核心检查 ----------
    def check(self, curve_id: str, value: float,
              elapsed_s: Optional[float] = None) -> bool:
        # 拦截 None / NaN / Inf，避免静默失效
        if value is None:
            return False
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False
        if math.isnan(v) or math.isinf(v):
            return False

        triggered_rules: List[AlarmRule] = []

        with self._lock:
            for rule in self.rules:
                if rule.curve_id != curve_id or not rule.enabled:
                    continue

                is_triggered = False
                if rule.mode == "above" and v > rule.threshold:
                    is_triggered = True
                elif rule.mode == "below" and v < rule.threshold:
                    is_triggered = True

                if is_triggered and not rule.active:
                    rule.active = True
                    rule.trigger_count += 1
                    rule.last_trigger_time = time.time()
                    triggered_rules.append(rule)
                elif not is_triggered:
                    rule.active = False

        if not triggered_rules:
            return False

        for r in triggered_rules:
            self._record_alarm(r.id, curve_id, v, r.threshold,
                               r.mode, r.trigger_count, elapsed_s)

        if self.sound_enabled:
            self._beep()

        if self._callback is not None:
            try:
                self._callback(triggered_rules, v)
            except Exception as e:
                print(f"[报警] 回调执行失败: {e}")

        return True

    # ---------- 仪器错误记录 ----------
    def add_instrument_error(self, error_text: str,
                             elapsed_s: Optional[float] = None) -> None:
        try:
            ts_abs = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if elapsed_s is not None:
                t_disp = self._format_elapsed(elapsed_s)
                text = (f"[{ts_abs}] [{t_disp}] ({elapsed_s:.3f}s) "
                        f"ERROR | {error_text}")
            else:
                text = f"[{ts_abs}] ERROR | {error_text}"

            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(text + '\n')
            except Exception as e:
                print(f"[报警] 写文件失败: {e}")

            with self._lock:
                self._records.append(AlarmRecord(
                    timestamp=ts_abs,
                    elapsed_s=elapsed_s,
                    text=text,
                    rule_id=-1,
                    count=0,
                    value=0.0,
                    threshold=0.0,
                    mode="error",
                    kind="instrument",
                ))
        except Exception as e:
            print(f"[报警] 记录仪器错误失败: {e}")

    # ---------- 内存 API ----------
    def get_records(self) -> List[AlarmRecord]:
        with self._lock:
            return list(self._records)

    def get_records_text(self) -> List[str]:
        with self._lock:
            return [r.text for r in self._records]

    def clear_records(self) -> None:
        with self._lock:
            self._records.clear()

    # ---------- 静态：读磁盘 ----------
    @staticmethod
    def read_all_records_from_file(log_file) -> List[str]:
        try:
            p = Path(log_file) if not isinstance(log_file, Path) else log_file
            if not p.is_file():
                return []
            with open(p, "r", encoding="utf-8") as f:
                return [ln.strip() for ln in f if ln.strip()]
        except Exception:
            return []

    # ---------- 辅助 ----------
    def _record_alarm(self, rule_id: int, curve_id: str, value: float,
                      threshold: float, mode: str, count: int,
                      elapsed_s: Optional[float]) -> None:
        try:
            ts_abs = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if elapsed_s is not None:
                t_disp = self._format_elapsed(elapsed_s)
                text = (f"[{ts_abs}] [{t_disp}] ({elapsed_s:.3f}s) "
                        f"ALARM #{count} | curve={curve_id} | "
                        f"value={value:.6g} | threshold={threshold:.6g} | mode={mode}")
            else:
                text = (f"[{ts_abs}] ALARM #{count} | curve={curve_id} | "
                        f"value={value:.6g} | threshold={threshold:.6g} | mode={mode}")

            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(text + '\n')
            except Exception as e:
                print(f"[报警] 写文件失败: {e}")

            with self._lock:
                self._records.append(AlarmRecord(
                    timestamp=ts_abs,
                    elapsed_s=elapsed_s,
                    text=text,
                    rule_id=rule_id,
                    count=count,
                    value=value,
                    threshold=threshold,
                    mode=mode,
                    kind="rule",
                ))
        except Exception as e:
            print(f"[报警] 记录失败: {e}")

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        if seconds is None or seconds < 0:
            return "00:00"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _beep(self) -> None:
        try:
            if os.name == 'nt':
                import winsound
                winsound.Beep(1000, 200)
            else:
                print('\a')
        except Exception:
            pass