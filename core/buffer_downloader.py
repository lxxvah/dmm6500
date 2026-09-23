#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/buffer_downloader.py —— 仪器缓冲区下载模块
==================================================
职责：
  · 从 DMM6500 内部读数缓冲区（defbuffer1 / defbuffer2）下载数据
  · 分块下载（避免一次性读太多超时）
  · 支持导出为 CSV
  · BufferDownloadWorker —— QThread 封装（后台下载 + 进度 + 取消）

信号（Worker）：
    connected          —— 仪器连接成功（用于进度对话框切换阶段）
    progress(done, total)   —— 下载进度
    finished_ok(path, count) —— 成功完成
    failed(error_message)   —— 失败或取消
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Callable, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal


def log(msg):
    print(msg, flush=True)


class BufferDownloader:
    """DMM6500 内部缓冲区下载器（同步版）"""

    DEFAULT_CHUNK = 10_000
    SUPPORTED_BUFFERS = ("defbuffer1", "defbuffer2")

    def __init__(self, connection):
        self.conn = connection

    def get_buffer_size(self, buffer_name: str = "defbuffer1") -> int:
        inst = self.conn.instrument
        try:
            rsp = inst.query(f"TRACe:ACTual? '{buffer_name}'").strip()
            return int(float(rsp))
        except Exception:
            pass
        try:
            rsp = inst.query(f"TRACe:ACTual? {buffer_name}").strip()
            return int(float(rsp))
        except Exception as e:
            log(f"[缓存] 查询 {buffer_name} 大小失败: {e}")
            return 0

    def get_buffer_capacity(self, buffer_name: str = "defbuffer1") -> int:
        inst = self.conn.instrument
        try:
            rsp = inst.query(f"TRACe:POINts? '{buffer_name}'").strip()
            return int(float(rsp))
        except Exception:
            try:
                rsp = inst.query(f"TRACe:POINts? {buffer_name}").strip()
                return int(float(rsp))
            except Exception:
                return 0

    def download(self,
                 buffer_name: str = "defbuffer1",
                 chunk_size: int = DEFAULT_CHUNK,
                 progress_callback: Optional[Callable[[int, int], None]] = None
                 ) -> List[float]:
        inst = self.conn.instrument
        n = self.get_buffer_size(buffer_name)
        if n <= 0:
            log(f"[缓存] {buffer_name} 为空")
            return []

        log(f"[缓存] 开始下载 {buffer_name}，共 {n} 点")
        values: List[float] = []
        start = 1
        chunk_size = max(1, int(chunk_size))

        while start <= n:
            stop = min(start + chunk_size - 1, n)
            try:
                chunk = inst.query_ascii_values(
                    f"TRACe:DATA? {start},{stop},'{buffer_name}'",
                    container=list
                )
            except Exception:
                chunk = inst.query_ascii_values(
                    f"TRACe:DATA? {start},{stop},{buffer_name}",
                    container=list
                )
            values.extend(float(v) for v in chunk)
            log(f"[缓存]   已下载 {len(values)}/{n}")
            if progress_callback is not None:
                try:
                    progress_callback(len(values), n)
                except Exception:
                    pass
            start = stop + 1

        log(f"[缓存] ✅ 下载完成，共 {len(values)} 点")
        return values

    @staticmethod
    def save_to_csv(values: List[float], path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['Index', 'Value'])
            for i, v in enumerate(values, 1):
                w.writerow([i, f"{v:.9g}"])
        log(f"[缓存] 已保存到 {p}")

    def clear_buffer(self, buffer_name: str = "defbuffer1") -> None:
        inst = self.conn.instrument
        try:
            inst.write(f"TRACe:CLEar '{buffer_name}'")
        except Exception:
            try:
                inst.write(f"TRACe:CLEar {buffer_name}")
            except Exception as e:
                log(f"[缓存] 清空失败: {e}")


class BufferDownloadWorker(QThread):
    """
    后台下载 DMM6500 内部缓冲区的 QThread。

    信号：
        connected                     —— 仪器连接成功（连接/下载阶段切换）
        progress(downloaded, total)   —— 下载进度
        finished_ok(file_path, count) —— 成功完成
        failed(error_message)         —— 失败或取消
    """
    connected = pyqtSignal()
    progress = pyqtSignal(int, int)
    finished_ok = pyqtSignal(str, int)
    failed = pyqtSignal(str)

    def __init__(self,
                 ip: str,
                 buffer_name: str = "defbuffer1",
                 output_path: str = "",
                 chunk_size: int = 10000):
        super().__init__()
        # ip 字段复用：可能是纯 IP，也可能是完整 VISA 地址
        self.ip = ip
        self.buffer_name = buffer_name
        self.output_path = output_path
        self.chunk_size = max(1, chunk_size)
        self._cancelled = False
        self._conn = None

    def cancel(self) -> None:
        self._cancelled = True

    def run(self):
        from core.connection import ConnectionManager

        try:
            # ---- 1. 连接仪器 ----
            self._conn = ConnectionManager()
            addr = self.ip or ""
            # ✅ 修复 #5：区分 IP / VISA 地址
            if "::" in addr:
                log(f"[缓存] 使用 VISA 地址连接: {addr}")
                self._conn.connect(address=addr)
            else:
                log(f"[缓存] 使用 IP 连接: {addr}")
                self._conn.connect(ip=addr)

            inst = self._conn.instrument
            self.connected.emit()

            # ---- 2. 查询缓冲区大小 ----
            try:
                rsp = inst.query(f"TRACe:ACTual? '{self.buffer_name}'").strip()
                n = int(float(rsp))
            except Exception:
                rsp = inst.query(f"TRACe:ACTual? {self.buffer_name}").strip()
                n = int(float(rsp))

            if n <= 0:
                self.failed.emit(f"{self.buffer_name} 缓冲区为空")
                return

            log(f"[缓存] 开始下载 {self.buffer_name}，共 {n} 点")

            # ---- 3. 分块下载 ----
            values: List[float] = []
            start = 1
            while start <= n:
                if self._cancelled:
                    self.failed.emit("已取消")
                    return

                stop = min(start + self.chunk_size - 1, n)
                try:
                    chunk = inst.query_ascii_values(
                        f"TRACe:DATA? {start},{stop},'{self.buffer_name}'",
                        container=list
                    )
                except Exception:
                    chunk = inst.query_ascii_values(
                        f"TRACe:DATA? {start},{stop},{self.buffer_name}",
                        container=list
                    )

                values.extend(float(v) for v in chunk)
                self.progress.emit(len(values), n)
                # ✅ 修复 #1（你已删除）：原先的 time.sleep(0.1) 已移除
                start = stop + 1

            # ---- 4. 保存 ----
            if self._cancelled:
                self.failed.emit("已取消")
                return

            p = Path(self.output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(['Index', 'Value'])
                for i, v in enumerate(values, 1):
                    w.writerow([i, f"{v:.9g}"])

            log(f"[缓存] ✅ 已保存到 {p}")
            self.finished_ok.emit(str(p), len(values))

        except Exception as e:
            log(f"[缓存] ❌ 失败: {e}")
            self.failed.emit(str(e))
        finally:
            if self._conn is not None:
                try:
                    self._conn.disconnect()
                except Exception:
                    pass
                self._conn = None