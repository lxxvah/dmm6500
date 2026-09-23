#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/recorder.py —— 数据记录模块
"""

from __future__ import annotations

import csv
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, TextIO


class DataRecorder:
    def __init__(self,
                 output_dir: str = "./data/recordings",
                 max_rows_per_file: int = 100_000):
        self.output_dir = Path(output_dir)
        self.max_rows_per_file = max_rows_per_file

        self._file: Optional[TextIO] = None
        self._writer = None
        self._filename: Optional[str] = None
        self._row_count = 0
        self._file_index = 0
        self._prefix = "dmm6500"
        self._metadata: Dict[str, str] = {}
        self._lock = threading.Lock()
        self.paused = False

        self.total_rows = 0
        self.total_files = 0

    @property
    def is_recording(self) -> bool:
        return self._file is not None

    @property
    def current_file(self) -> Optional[str]:
        return self._filename

    def start(self, prefix: str = "dmm6500",
              metadata: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._close_locked()
            self._prefix = prefix
            self._metadata = metadata or {}
            self._file_index = 0
            self.total_rows = 0
            self.total_files = 0
            self._open_new_file_locked()
            print(f"[记录] 已开始，文件: {self._filename}")

    def stop(self) -> None:
        with self._lock:
            self._close_locked()
            print(f"[记录] 已停止，共写入 {self.total_rows} 行，"
                  f"{self.total_files} 个文件")

    def pause(self) -> None:
        self.paused = True
        print("[记录] 已暂停")

    def resume(self) -> None:
        self.paused = False
        print("[记录] 已恢复")

    def write(self, timestamp: str, elapsed_s: float,
              value: float, raw_str: str = "") -> None:
        if self.paused or self._file is None:
            return

        with self._lock:
            if self._file is None:
                return

            if self._row_count >= self.max_rows_per_file:
                self._close_locked()
                self._open_new_file_locked()

            try:
                self._writer.writerow([
                    timestamp,
                    f"{elapsed_s:.6f}",
                    repr(float(value)),
                    raw_str,
                ])
                self._row_count += 1
                self.total_rows += 1
            except Exception as e:
                print(f"[记录] 写入失败: {e}")

    def _open_new_file_locked(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._file_index += 1
        name = f"{self._prefix}_{ts}_{self._file_index:03d}.csv"
        self._filename = str(self.output_dir / name)

        self._file = open(self._filename, 'w', newline='', encoding='utf-8')
        self._writer = csv.writer(self._file)

        self._writer.writerow(['# DMM6500 Data Recording'])
        self._writer.writerow([f'# Started: {datetime.now().isoformat()}'])
        for k, v in self._metadata.items():
            self._writer.writerow([f'# {k}: {v}'])
        self._writer.writerow(['#'])

        self._writer.writerow(['Timestamp', 'Elapsed_s', 'Value', 'Raw'])
        self._file.flush()
        self._row_count = 0
        self.total_files += 1

    def _close_locked(self) -> None:
        if self._file is not None:
            try:
                self._file.flush()
                self._file.close()
            except Exception:
                pass
            self._file = None
            self._writer = None
            self._filename = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()