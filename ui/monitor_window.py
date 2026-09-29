#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/monitor_window.py —— DMM6500 监控主窗口
=============================================
状态文本全部 ≤3 字，彻底消除状态栏宽度抖动

【机械表设计】
  · 表盘单位/量程 完全跟随实时值卡片（复用 format_with_unit 的前缀逻辑）
  · 档位用 1/2/5/10 系，滞回 + 冷却防抖
  · 双极：V/A/Ω（±tier）；单极：其余（0~tier）
"""

import time
import csv
from dataclasses import replace
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QDialog,
    QFileDialog,
)
from PyQt6.QtCore import QTimer, Qt

from theme import Theme, COLORS

from ui.control_panel import ControlPanel
from ui.cards import (RealTimeValueCard, StatCard,
                       AlarmConfigDialog, RecordConfirmDialog,
                       BufferProgressDialog)
from ui.waveform_widget import WaveformWidget
from ui.about_dialog import show_about

from core.connection import ScanWorker, ConnectionManager
from core.measurements import MeasurementWorker, get_mode_info, list_modes
from core.statistics import StreamingStats, format_with_unit
from core.recorder import DataRecorder
from core.alarm import AlarmManager
from core.report import ReportBuilder
from core.buffer_downloader import BufferDownloader, BufferDownloadWorker
from core.gauge_range import GaugeRangeController, GaugeRangeDecision

from libs.platform_utils import apply_titlebar_theme

from libs.analog_gauge_qt import (
    AnalogGauge, GaugeConfig, GAUGE_PRESETS,
    ThemeManager as GaugeThemeManager,
    palette_from_theme,
)


def log(msg):
    print(msg, flush=True)


_GAUGE_TITLE = {
    "DCV":   "VOLTAGE",
    "DCI":   "CURRENT",
    "ACV":   "AC VOLTAGE",
    "ACI":   "AC CURRENT",
    "RES2W": "RESISTANCE",
    "RES4W": "RESISTANCE 4W",
    "CAP":   "CAPACITANCE",
    "FREQ":  "FREQUENCY",
    "PER":   "PERIOD",
    "TEMP":  "TEMPERATURE",
    "CONT":  "CONTINUITY",
    "DIOD":  "DIODE",
}


class DMM6500Monitor(QMainWindow):
    def __init__(self, theme: Theme = None):
        super().__init__()
        self.theme = theme if theme else Theme('light')
        self.setWindowTitle("DMM6500 综合监控台")
        self.resize(1400, 850)

        self.worker: MeasurementWorker = None
        self.scan_worker: ScanWorker = None
        self._buffer_worker: BufferDownloadWorker = None

        self.stats = StreamingStats(window=1_000_000)
        self.recorder = DataRecorder(output_dir="./data/recordings",
                                     max_rows_per_file=100_000)

        self.alarm = AlarmManager(log_dir="./data")
        self.alarm.set_callback(self._on_alarm_triggered)

        self.report_builder = ReportBuilder(output_dir="./data/reports")

        self.start_time = time.time()
        self._disconnect_time = None
        self._paused = False
        self.curve_id = None

        # 机械表：更新节流 + 档位控制器
        self._gauge_last_ts = 0.0
        self.gauge_range = GaugeRangeController()

        self._init_ui()

        apply_titlebar_theme(self, self.theme.is_dark)

        self.panel.set_mode_list(list_modes())
        self._apply_mode_to_waveform()
        self._apply_mode_to_gauge(self.panel.current_mode)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.waveform.refresh)
        self.refresh_timer.start(50)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(10)

        self.panel = ControlPanel(self.theme)
        self.panel.scan_requested.connect(self.start_scan)
        self.panel.connect_requested.connect(self.start_measurement)
        self.panel.disconnect_requested.connect(self.stop_measurement)
        self.panel.mode_changed.connect(self.on_mode_changed)
        self.panel.capture_pause_toggled.connect(self.on_pause_toggled)
        self.panel.record_toggled.connect(self.on_record_toggled)
        self.panel.alarm_config_requested.connect(self.open_alarm_dialog)
        self.panel.html_report_requested.connect(self.generate_html_report)
        self.panel.buffer_download_requested.connect(self.download_buffer)
        self.panel.clear_requested.connect(self.clear_waveform)
        main.addWidget(self.panel, stretch=0)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(6)

        self.realtime_card = RealTimeValueCard(self.theme)
        self.card_max = StatCard("MAX", self.theme.stat_max, self.theme)
        self.card_min = StatCard("MIN", self.theme.stat_min, self.theme)
        self.card_avg = StatCard("AVG", self.theme.stat_avg, self.theme)
        self.card_std = StatCard("STD", self.theme.stat_std, self.theme)

        cards_layout.addWidget(self.realtime_card, 3)
        cards_layout.addWidget(self.card_max, 2)
        cards_layout.addWidget(self.card_min, 2)
        cards_layout.addWidget(self.card_avg, 2)
        cards_layout.addWidget(self.card_std, 2)
        right_layout.addLayout(cards_layout)

        self.waveform = WaveformWidget(theme=self.theme.mode)
        self.curve_id = self.waveform.add_curve("曲线1",
                                                 color=COLORS.ACCENT_PURPLE)
        self.waveform.save_data_requested.connect(self.export_full_data)
        self.waveform.about_requested.connect(self.show_about_dialog)
        self.waveform.gauge_toggled.connect(self._on_gauge_toggled)
        right_layout.addWidget(self.waveform, stretch=1)

        main.addWidget(right_panel, stretch=1)

        self.setStyleSheet(self.theme.app_qss())
        self.waveform.reapply_toolbar_style()

    # ============================================
    # 机械表
    # ============================================
    def _apply_mode_to_waveform(self):
        meta = get_mode_info(self.panel.current_mode)
        self.waveform.set_y_label(meta.y_label, meta.unit)

    def _on_gauge_toggled(self, show: bool):
        log(f"[机械表] 右键菜单切换: visible={show}")
        self.panel.set_gauge_visible(show)

    def _apply_mode_to_gauge(self, mode: str):
        """模式切换 → 用默认单位初始化表盘"""
        try:
            base_unit = get_mode_info(mode).unit
            decision = self.gauge_range.get_initial_decision(mode, base_unit)
            cfg = self.panel.gauge.config()
            new_cfg = replace(
                cfg,
                title=_GAUGE_TITLE.get(mode, mode),
                unit=decision.unit,
                min_value=decision.min_value,
                max_value=decision.max_value,
                major_step=decision.major_step,
                minor_step=decision.minor_step,
                decimals=decision.decimals,
                value_position=cfg.value_position,
            )
            self.panel.gauge.set_config(new_cfg)
            self.panel.gauge.set_value(0.0, animate=False)
            log(f"[机械表] 模式 {mode} → "
                f"[{decision.min_value}, {decision.max_value}] "
                f"{decision.unit}")
        except Exception as e:
            log(f"[机械表] 应用模式失败: {e}")

    def _set_gauge_range(self, decision: GaugeRangeDecision) -> bool:
        """同步表盘量程 + 单位；返回 True 表示档位实际变了"""
        cfg = self.panel.gauge.config()
        if (abs(cfg.min_value - decision.min_value) < 1e-12
                and abs(cfg.max_value - decision.max_value) < 1e-12
                and cfg.unit == decision.unit):
            return False
        new_cfg = replace(
            cfg,
            unit=decision.unit,
            min_value=decision.min_value,
            max_value=decision.max_value,
            major_step=decision.major_step,
            minor_step=decision.minor_step,
            decimals=decision.decimals,
        )
        self.panel.gauge.set_config(new_cfg)
        return True

    def _update_gauge(self, value: float):
        """每来一个数据点（10Hz 节流后）调用"""
        try:
            mode = self.panel.current_mode
            base_unit = get_mode_info(mode).unit
            # ★ 关键：3 参数调用
            decision = self.gauge_range.update(mode, value, base_unit)
            changed = self._set_gauge_range(decision)
            # ★ 关键：把原始值换算成"该单位下的显示值"
            disp_value = (value / decision.unit_scale
                          if decision.unit_scale else value)
            self.panel.gauge.set_value(disp_value, animate=not changed)
        except Exception as e:
            log(f"[机械表] 更新失败: {e}")

    def _on_range_updated(self, mode: str, range_val: float):
        """不再跟随仪器档位——保留空实现以兼容信号连接"""
        pass

    # ============================================
    # 模式切换
    # ============================================
    def on_mode_changed(self, mode: str):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "提示", "请先断开连接，再切换测量类型。")
            prev_mode = self.report_builder.get_metadata("mode")
            if prev_mode and prev_mode in list_modes():
                self.panel.set_mode_silently(prev_mode)
            return

        prev_mode = self.report_builder.get_metadata("mode")
        if prev_mode == mode:
            return

        self.report_builder.reset()
        self.alarm.clear_records()
        self.start_time = time.time()
        self._disconnect_time = None
        self._reset_ui_only()
        self._apply_mode_to_waveform()
        self._apply_mode_to_gauge(mode)
        self.panel.set_status("已切换", "info")

    def _reset_ui_only(self):
        self.waveform.clear_data()
        self.stats.reset()
        unit = get_mode_info(self.panel.current_mode).unit
        self.realtime_card.reset(unit)
        self.card_max.update_value("---")
        self.card_min.update_value("---")
        self.card_avg.update_value("---")
        self.card_std.update_value("---")
        try:
            self.panel.gauge.set_value(0.0, animate=False)
        except Exception:
            pass

    # ============================================
    # 功能介绍
    # ============================================
    def show_about_dialog(self):
        try:
            show_about(self, self.theme)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开功能介绍失败：\n{e}")

    # ============================================
    # 扫描
    # ============================================
    def start_scan(self, hint_ip: str = ""):
        if self.scan_worker and self.scan_worker.isRunning():
            return
        self.panel.set_scan_btn_enabled(False)
        self.panel.set_scan_btn_text("...")
        self.panel.set_status("扫描中", "info")

        self.scan_worker = ScanWorker(hint_ip=hint_ip)
        self.scan_worker.scan_finished.connect(self._on_scan_finished)
        self.scan_worker.scan_failed.connect(self._on_scan_failed)
        self.scan_worker.start()

    def _on_scan_finished(self, address: str):
        self.panel.set_scan_btn_enabled(True)
        self.panel.set_scan_btn_text("")
        self.panel.set_ip(address)
        self.panel.set_status("已找到", "success")

    def _on_scan_failed(self, msg: str):
        self.panel.set_scan_btn_enabled(True)
        self.panel.set_scan_btn_text("")
        self.panel.set_status("未找到", "error")
        QMessageBox.warning(self, "扫描失败", msg)

    # ============================================
    # 连接 / 断开
    # ============================================
    def start_measurement(self):
        if self.worker and self.worker.isRunning():
            return

        ip = self.panel.get_ip()
        if not ip:
            QMessageBox.warning(self, "提示",
                                "请先输入 IP 或 VISA 地址，或点击扫描按钮自动识别仪器。")
            self.panel.set_connected_state(False)
            return

        cfg = self.panel.get_config()

        if self._disconnect_time is not None:
            idle = time.time() - self._disconnect_time
            self.start_time += idle
            self._disconnect_time = None

        if not self.report_builder.has_metadata():
            self.start_time = time.time()
            self.report_builder.reset()
            self.alarm.clear_records()
            self._reset_ui_only()

            meta = get_mode_info(cfg["mode"])
            self.report_builder.set_metadata(
                mode=cfg["mode"],
                unit=meta.unit,
                terminal=cfg["terminal"],
                nplc=str(cfg["nplc"]),
                range="AUTO" if cfg["auto_range"] else str(cfg["range_val"]),
                started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            self.report_builder.set_alarm_log(self.alarm.log_file)

        self._apply_mode_to_waveform()
        self._apply_mode_to_gauge(cfg["mode"])

        self._paused = False
        self.panel.set_pause_btn_checked(False)
        self.panel.set_connected_state(True)
        self.panel.set_status("连接中", "info")

        self.worker = MeasurementWorker(ip, cfg)
        self.worker.data_ready.connect(self.update_data)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.connected_info.connect(self._on_connected)
        self.worker.status_update.connect(self._on_status_update)
        self.worker.instrument_error.connect(self._on_instrument_error)
        self.worker.range_updated.connect(self._on_range_updated)
        self.worker.start()

    def stop_measurement(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker = None

        self._disconnect_time = time.time()

        self._paused = False
        self.panel.set_connected_state(False)

        if self.recorder.is_recording:
            self.recorder.stop()
            self.panel.set_record_btn_state(False, "开始记录")

        self.panel.set_status("已断开", "normal")

    def _on_connected(self, address: str):
        self.panel.set_status("已连接", "success")

    def _on_status_update(self, text: str):
        self.panel.set_status(text, "info")

    def _on_instrument_error(self, error_text: str):
        t = time.time() - self.start_time
        self.alarm.add_instrument_error(error_text, elapsed_s=t)

    # ============================================
    # 暂停 / 开始
    # ============================================
    def on_pause_toggled(self, paused: bool):
        self._paused = paused
        self.waveform.pause(paused)
        if paused:
            self.panel.set_status("已暂停", "info")
        else:
            self.panel.set_status("采集中", "info")

    # ============================================
    # 错误处理
    # ============================================
    def handle_error(self, error_msg: str):
        if self.worker:
            try:
                self.worker.stop()
            except Exception:
                pass
            self.worker = None
        if self.recorder.is_recording:
            self.recorder.stop()
            self.panel.set_record_btn_state(False, "开始记录")

        self._paused = False
        self._disconnect_time = time.time()
        self.waveform.pause(False)
        self.panel.set_connected_state(False)
        self.panel.set_status("错误", "error")

        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.setWindowTitle("通信错误")
        dlg.setText("连接或测量失败，点击「Show Details」查看详情：")
        dlg.setDetailedText(error_msg)
        dlg.exec()

    # ============================================
    # 数据更新
    # ============================================
    def update_data(self, raw_str, value):
        t = time.time() - self.start_time
        base_unit = get_mode_info(self.panel.current_mode).unit

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.recorder.is_recording:
            self.recorder.write(ts, t, value, raw_str)

        self.report_builder.add_point(ts, t, value, raw_str)

        if self.curve_id:
            self.alarm.check(self.curve_id, value, elapsed_s=t)

        if self._paused:
            return

        # 实时值卡片（已有）
        s, u = format_with_unit(value, base_unit)
        self.realtime_card.update_value(s, u)

        self.waveform.append_data(self.curve_id, t, value)

        self.stats.update(value)
        for card, v in [
            (self.card_max, self.stats.max),
            (self.card_min, self.stats.min),
            (self.card_avg, self.stats.mean),
            (self.card_std, self.stats.std),
        ]:
            s, u = format_with_unit(v, base_unit)
            card.update_value(s, u)

        # ★ 机械表：10Hz 节流
        if self.panel.gauge_wrap.isVisible():
            now = time.monotonic()
            if now - self._gauge_last_ts >= 0.1:
                self._gauge_last_ts = now
                self._update_gauge(value)

    # ============================================
    # 数据记录
    # ============================================
    def on_record_toggled(self, checked: bool):
        if checked:
            dlg = RecordConfirmDialog(
                self, theme=self.theme,
                record_dir="./data/recordings"
            )
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.panel.set_record_btn_state(False, "开始记录")
                return

            cfg = self.panel.get_config()
            metadata = {
                "mode": cfg["mode"],
                "terminal": cfg["terminal"],
                "nplc": str(cfg["nplc"]),
                "range": "AUTO" if cfg["auto_range"] else str(cfg["range_val"]),
            }
            self.recorder.start(prefix=cfg["mode"], metadata=metadata)
            self.panel.set_record_btn_state(True, "停止记录")
            self.panel.set_status("记录中", "success")
        else:
            self.recorder.stop()
            self.panel.set_record_btn_state(False, "开始记录")
            self.panel.set_status("已停止", "normal")

    # ============================================
    # 报警
    # ============================================
    def open_alarm_dialog(self):
        current_rules = self.alarm.get_rules(self.curve_id) if self.curve_id else []
        initial = [
            {'threshold': r.threshold, 'mode': r.mode, 'enabled': r.enabled}
            for r in current_rules
        ]

        dlg = AlarmConfigDialog(self, initial_rules=initial, theme=self.theme)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        values = dlg.get_values()
        self.alarm.clear_rules_for_curve(self.curve_id)

        n_enabled = 0
        for v in values:
            if v['enabled']:
                self.alarm.add_rule(
                    self.curve_id,
                    threshold=v['threshold'],
                    mode=v['mode'],
                )
                n_enabled += 1

        if n_enabled > 0:
            rules_str = "\n".join(
                f"  • {'高于' if v['mode'] == 'above' else '低于'} {v['threshold']:g}"
                for v in values if v['enabled']
            )
            QMessageBox.information(
                self, "报警已设置",
                f"已启用 {n_enabled} 条报警规则：\n\n{rules_str}"
            )
        else:
            QMessageBox.information(self, "报警已关闭", "所有报警规则已禁用")

    def _on_alarm_triggered(self, triggered_rules, value):
        base_unit = get_mode_info(self.panel.current_mode).unit
        s, u = format_with_unit(value, base_unit)

        lines = []
        for r in triggered_rules:
            label = "高于" if r.mode == "above" else "低于"
            lines.append(f"  • {label} {r.threshold:g}")

        msg = (
            f"数据越界！\n"
            f"当前值: {s} {u}\n\n"
            f"触发规则（{len(triggered_rules)} 条）:\n" + "\n".join(lines)
        )
        QMessageBox.warning(self, "报警", msg)

    # ============================================
    # HTML 报告
    # ============================================
    def generate_html_report(self):
        if not self.report_builder.has_data:
            QMessageBox.information(
                self, "提示",
                "暂无数据，请先连接仪器并采集数据后再生成报告。"
            )
            return

        self.report_builder.set_alarm_records(self.alarm)

        try:
            path = self.report_builder.generate(
                prefix="dmm6500_report",
                auto_open=True,
            )
            n_alarms = len(self.alarm.get_records())
            QMessageBox.information(
                self, "报告已生成",
                f"共 {self.report_builder.count} 个数据点，"
                f"{n_alarms} 条报警记录。\n\n"
                f"文件位置：\n{path}\n\n"
                f"（已自动用浏览器打开）"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "错误",
                f"生成 HTML 报告失败：\n{e}"
            )

    # ============================================
    # 导出完整数据
    # ============================================
    def export_full_data(self):
        data = self.report_builder.get_all_data()
        if not data:
            QMessageBox.information(self, "提示", "暂无数据可保存。")
            return

        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"waveform_{ts_str}.csv"

        path, _ = QFileDialog.getSaveFileName(
            self, "保存数据", default_name,
            "CSV 文件 (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(['Timestamp', 'Elapsed_s', 'Value', 'Raw'])
                for ts, t, v, raw in data:
                    w.writerow([ts, f"{t:.6f}", f"{v:.9g}", raw])

            QMessageBox.information(
                self, "保存成功",
                f"共 {len(data)} 行。\n\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存数据失败：\n{e}")

    # ============================================
    # 下载缓存
    # ============================================
    def download_buffer(self):
        if self._buffer_worker is not None and self._buffer_worker.isRunning():
            QMessageBox.information(self, "提示", "已有下载任务正在进行，请稍候。")
            return

        ip = self.panel.get_ip()
        if not ip:
            QMessageBox.warning(self, "提示", "请先输入 IP 或 VISA 地址。")
            return

        was_running = (self.worker is not None and self.worker.isRunning())
        saved_cfg = None

        if was_running:
            saved_cfg = self.panel.get_config()
            self.panel.set_status("暂停中", "info")
            log("[缓存] 暂停采集，准备独占仪器连接")
            try:
                self.worker.stop()
            except Exception as e:
                log(f"[缓存] 停止 worker 时异常（忽略）: {e}")
            self.worker = None
            time.sleep(1.0)
            log("[缓存] 采集已暂停，VISA 会话已释放")

        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"buffer_{ts_str}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存缓存数据", default_name,
            "CSV 文件 (*.csv)"
        )
        if not path:
            if was_running and saved_cfg is not None:
                self._resume_measurement(ip, saved_cfg)
            return

        dlg = BufferProgressDialog(self, theme=self.theme)
        dlg.set_connecting()

        worker = BufferDownloadWorker(ip, "defbuffer1", path)
        self._buffer_worker = worker

        def on_connected():
            dlg.set_downloading()

        def on_progress(done, total):
            dlg.update_progress(done, total)

        def on_ok(file_path, count):
            try:
                dlg.accept()
            except Exception:
                pass
            self._buffer_worker = None
            self.panel.set_status("已下载", "success")
            QMessageBox.information(
                self, "下载完成",
                f"已下载 {count} 条数据。\n\n文件位置：\n{file_path}"
            )
            if was_running and saved_cfg is not None:
                self._resume_measurement(ip, saved_cfg)

        def on_fail(err):
            try:
                dlg.reject()
            except Exception:
                pass
            self._buffer_worker = None
            if "已取消" in err:
                self.panel.set_status("已取消", "info")
            else:
                self.panel.set_status("失败", "error")
                QMessageBox.critical(self, "错误", f"下载缓存失败：\n{err}")
            if was_running and saved_cfg is not None:
                self._resume_measurement(ip, saved_cfg)

        def on_cancelled():
            worker.cancel()

        worker.connected.connect(on_connected)
        worker.progress.connect(on_progress)
        worker.finished_ok.connect(on_ok)
        worker.failed.connect(on_fail)
        dlg.cancelled.connect(on_cancelled)

        self.panel.set_status("下载中", "info")
        worker.start()
        dlg.exec()

    def _resume_measurement(self, ip: str, cfg: dict):
        if self.worker is not None and self.worker.isRunning():
            return

        log("[缓存] 恢复采集...")
        self.worker = MeasurementWorker(ip, cfg)
        self.worker.data_ready.connect(self.update_data)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.connected_info.connect(self._on_connected)
        self.worker.status_update.connect(self._on_status_update)
        self.worker.instrument_error.connect(self._on_instrument_error)
        self.worker.range_updated.connect(self._on_range_updated)
        self.worker.start()

        self.panel.set_connected_state(True)
        self.panel.set_status("采集中", "success")

    # ============================================
    # 清空
    # ============================================
    def clear_waveform(self):
        self.report_builder.clear_data()
        self.alarm.clear_records()
        self.start_time = time.time()
        self._disconnect_time = None
        self._reset_ui_only()
        self.panel.set_status("已清空", "info")

    # ============================================
    # 主题切换
    # ============================================
    def switch_theme(self, mode: str):
        self.theme = Theme(mode)
        apply_titlebar_theme(self, self.theme.is_dark)
        self.setStyleSheet(self.theme.app_qss())
        self.panel.switch_theme(self.theme)

        self.realtime_card.setStyleSheet(self.theme.realtime_card_qss())
        self.card_max.setStyleSheet(self.theme.stat_card_qss(self.theme.stat_max))
        self.card_min.setStyleSheet(self.theme.stat_card_qss(self.theme.stat_min))
        self.card_avg.setStyleSheet(self.theme.stat_card_qss(self.theme.stat_avg))
        self.card_std.setStyleSheet(self.theme.stat_card_qss(self.theme.stat_std))

        self.waveform.set_theme(mode)
        self.waveform.reapply_toolbar_style()

        try:
            GaugeThemeManager.instance().set_theme(mode)
        except Exception as e:
            print(f"[机械表] 主题切换失败: {e}")

        try:
            from libs.DMM6500app_icon import get_icon_manager
            get_icon_manager().set_theme(mode)
        except Exception as e:
            print(f"[图标] 切换失败: {e}")

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.quit()
            self.scan_worker.wait(1000)
        if self._buffer_worker and self._buffer_worker.isRunning():
            self._buffer_worker.cancel()
            self._buffer_worker.wait(2000)
        if self.recorder.is_recording:
            self.recorder.stop()

        try:
            from libs.DMM6500app_icon import get_icon_manager
            get_icon_manager().detach(self)
        except Exception:
            pass

        event.accept()