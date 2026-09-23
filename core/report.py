#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/report.py —— HTML 报告生成模块
======================================
✅ 报警记录：双 Tab（当前告警 / 历史告警）
✅ 数据预览：分页表格（前端 JS 分页，全数据可翻页）
✅ ECharts 内嵌（优先读 libs/echarts.min.js，离线可用）
✅ get_all_data()：供外部导出完整数据

修复：
  · 采样点数卡片不再带单位
  · 历史报警日志只读最近 N 条（防日志膨胀拖慢报告生成）
  · 报告文件名加序号（防同秒生成覆盖）
  · _load_current_alarms 提前判断内存报警是否启用（避免白扫）
"""

from __future__ import annotations

import html as _html
import json
import webbrowser
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np


MAX_POINTS = 1_000_000       # 内存保留上限
MAX_CHART_POINTS = 5_000     # 图表显示上限
MAX_PREVIEW_ROWS = 200       # 分页：默认每页行数
MAX_EMBED_ROWS = 50_000      # 嵌入 HTML 的最大行数（超过则截断）
MAX_HISTORY_ALARMS = 1_000   # ✅ 历史报警日志最多读取条数


_ECHARTS_PLACEHOLDER = "<!--__ECHARTS_INLINE__-->"


_HTML_TEMPLATE = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DMM6500 测量报告</title>
{_ECHARTS_PLACEHOLDER}
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                 "Microsoft YaHei UI", "PingFang SC", sans-serif;
    background: #f5f5f7; color: #1a1a1a; margin: 0; padding: 24px;
    line-height: 1.5; -webkit-font-smoothing: antialiased;
  }}
  .container {{ max-width: 1280px; margin: 0 auto; }}
  header {{ margin-bottom: 24px; }}
  h1 {{ font-size: 24px; margin: 0 0 8px; font-weight: 600; letter-spacing: -0.3px; }}
  h2 {{ font-size: 15px; margin: 0 0 14px; font-weight: 600;
       color: #363636; letter-spacing: 0.2px; }}
  .sub {{ color: #898989; font-size: 13px; margin: 0; }}
  .card {{ background: #fff; border-radius: 10px; padding: 20px 22px;
          margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
  .card-grid {{ display: grid;
               grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
               gap: 12px; margin-bottom: 16px; }}
  .stat-card {{ background: #fff; border-radius: 10px; padding: 16px 18px;
               box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
  .stat-card .label {{ font-size: 10px; color: #898989; text-transform: uppercase;
                      letter-spacing: 0.6px; margin-bottom: 6px;
                      font-weight: 600; text-align: center; }}
  .stat-card .value {{ font-size: 20px; font-weight: 600; color: #080808;
                      font-variant-numeric: tabular-nums; text-align: center; }}
  .stat-card .unit {{ font-size: 13px; color: #898989; margin-left: 4px;
                     font-weight: 500; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: center; padding: 8px 10px;
           border-bottom: 1px solid #ececec;
           font-variant-numeric: tabular-nums; }}
  th {{ color: #898989; font-weight: 600; font-size: 10px;
       text-transform: uppercase; letter-spacing: 0.6px; }}
  td.mono {{ font-family: Consolas, "Courier New", monospace; font-size: 12px; }}

  /* Tab */
  .tabs {{ display: flex; gap: 4px; border-bottom: 1px solid #ececec;
          margin-bottom: 14px; }}
  .tab-btn {{ padding: 8px 16px; border: none; background: transparent;
             cursor: pointer; font-size: 13px; color: #898989;
             border-bottom: 2px solid transparent; font-weight: 500;
             font-family: inherit; }}
  .tab-btn:hover {{ color: #363636; }}
  .tab-btn.active {{ color: #080808; border-bottom-color: #7a3dff;
                    font-weight: 600; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  .alarm-list {{ list-style: none; padding: 0; margin: 0;
                max-height: 400px; overflow-y: auto;
                border: 1px solid #f0f0f0; border-radius: 6px; }}
  .alarm-list li {{ padding: 8px 12px; border-bottom: 1px solid #f5f5f5;
                   font-size: 12px; color: #363636;
                   font-variant-numeric: tabular-nums;
                   font-family: Consolas, "Courier New", monospace;
                   text-align: left; }}
  .alarm-list li:last-child {{ border-bottom: none; }}
  .alarm-list li:before {{ content: "⚠ "; color: #ee1d36; font-weight: 700;
                          font-family: sans-serif; }}
  .empty {{ color: #898989; font-size: 13px; padding: 20px 0;
           text-align: center; font-style: italic; }}
  .meta-table {{ width: 100%; font-size: 13px; }}
  .meta-table th {{ width: 130px; color: #898989; font-weight: 500;
                   text-transform: none; letter-spacing: 0; padding: 6px 0;
                   border: none; font-size: 13px; text-align: left; }}
  .meta-table td {{ padding: 6px 0; border: none; text-align: left; }}
  footer {{ text-align: center; color: #ababab; font-size: 11px;
           margin-top: 32px; padding: 16px 0; }}
  .preview-note {{ color: #898989; font-size: 11px; margin: 0 0 10px;
                  text-align: center; }}
  .alarm-note {{ color: #898989; font-size: 11px; margin: 8px 0 10px;
                text-align: center; }}

  /* 分页控件 */
  .preview-controls {{
    display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
    padding: 10px 12px; background: #fafafa;
    border: 1px solid #f0f0f0; border-radius: 6px;
    margin-bottom: 10px; font-size: 12px; color: #363636;
  }}
  .pg-btn {{
    padding: 4px 10px; font-size: 12px;
    border: 1px solid #d8d8d8; background: #ffffff;
    border-radius: 4px; cursor: pointer; color: #363636;
    font-family: inherit;
  }}
  .pg-btn:hover {{ background: #f0f0f0; border-color: #b8b8b8; }}
  .pg-btn:active {{ background: #e8e8e8; }}
  .pg-input {{
    width: 56px; padding: 3px 6px; text-align: center;
    border: 1px solid #d8d8d8; border-radius: 4px; font-size: 12px;
    font-family: inherit;
  }}
  .pg-select {{
    padding: 3px 6px; border: 1px solid #d8d8d8; border-radius: 4px;
    font-size: 12px; background: #ffffff; color: #363636;
    font-family: inherit;
  }}
  .pg-info-right {{ margin-left: auto; color: #898989; }}
  .pg-sep {{ color: #d8d8d8; }}

  .preview-table-wrap {{
    max-height: 600px; overflow-y: auto;
    border: 1px solid #f0f0f0; border-radius: 6px;
  }}
  .preview-table-wrap table thead th {{
    position: sticky; top: 0; background: #fafafa; z-index: 1;
  }}
</style>
</head>
<body>
<div class="container">

  <header>
    <h1>DMM6500 测量报告</h1>
    <p class="sub">生成时间：__GENERATED_AT__ &nbsp;·&nbsp; 采样点数：__TOTAL_COUNT__ &nbsp;·&nbsp; 采集时长：__DURATION__</p>
  </header>

  <section class="card">
    <h2>测量参数</h2>
    <table class="meta-table">
      __META_ROWS__
    </table>
  </section>

  <section class="card-grid">
    __STATS_CARDS__
  </section>

  <section class="card">
    <h2>波形</h2>
    <div id="chart" style="width:100%;height:520px;__CHART_DISPLAY__"></div>
    __CHART_EMPTY__
  </section>

  <section class="card">
    <h2>报警记录</h2>
    <div class="tabs">
      <button class="tab-btn active" onclick="showTab('current', this)">
        当前告警（__ALARM_CURRENT_COUNT__）
      </button>
      <button class="tab-btn" onclick="showTab('history', this)">
        历史告警（__ALARM_HISTORY_COUNT__）
      </button>
    </div>
    <div id="tab-current" class="tab-panel active">
      <p class="alarm-note">报告时间段（__DATA_RANGE__）内的报警</p>
      __ALARM_CURRENT_HTML__
    </div>
    <div id="tab-history" class="tab-panel">
      <p class="alarm-note">来自 ./data/alarm_log.txt 的最近 __ALARM_HISTORY_LIMIT__ 条</p>
      __ALARM_HISTORY_HTML__
    </div>
  </section>

  <section class="card">
    <h2>数据预览（共 __PREVIEW_TOTAL__ 行，可翻页）</h2>
    <p class="preview-note">
      <b>Timestamp</b> 绝对时间戳 ·
      <b>Elapsed_s</b> 相对开始秒数 ·
      <b>Value</b> 数值 ·
      <b>Raw</b> 仪器原始返回值
      __TRUNCATED_NOTE__
    </p>
    __PREVIEW_CONTROLS__
    <div class="preview-table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width:60px;">#</th>
            <th style="width:180px;">Timestamp</th>
            <th style="width:110px;">Elapsed_s</th>
            <th style="width:150px;">Value</th>
            <th>Raw</th>
          </tr>
        </thead>
        <tbody id="pgBody"></tbody>
      </table>
    </div>
  </section>
  <footer>
    由 DMM6500 综合监控台生成 · Powered by ECharts<br>
    <span style="display:inline-block; margin-top:6px; color:#898989;">
      作者：得鹿梦鱼 &nbsp;·&nbsp; <i>「莫道桑榆晚，为霞尚满天」</i>
    </span>
  </footer>
</div>

<script>
const CHART_DATA = __CHART_JSON__;
const UNIT = __UNIT_JSON__;

(function () {{
  const el = document.getElementById('chart');
  if (!el || CHART_DATA.length === 0) return;
  if (typeof echarts === 'undefined') {{
    el.innerHTML = '<div class="empty">ECharts 库未加载，请检查 libs/echarts.min.js</div>';
    return;
  }}
  const chart = echarts.init(el);
  const option = {{
    grid: {{ left: 70, right: 30, top: 30, bottom: 70 }},
    tooltip: {{
      trigger: 'axis',
      valueFormatter: function (v) {{
        if (Array.isArray(v)) v = v[1];
        return (typeof v === 'number' ? v.toFixed(6) : v) + ' ' + UNIT;
      }}
    }},
    xAxis: {{
      type: 'value',
      name: '时间',
      nameLocation: 'middle',
      nameGap: 32,
      axisLabel: {{
        formatter: function (val) {{
          if (val < 60) return val.toFixed(1) + 's';
          if (val < 3600) {{
            const m = Math.floor(val / 60);
            const s = Math.floor(val % 60);
            return m + ':' + String(s).padStart(2, '0');
          }}
          const h = Math.floor(val / 3600);
          const m = Math.floor((val % 3600) / 60);
          const s = Math.floor(val % 60);
          return h + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
        }}
      }}
    }},
    yAxis: {{ type: 'value', name: '读数 (' + UNIT + ')', scale: true }},
    dataZoom: [
      {{ type: 'inside', start: 0, end: 100 }},
      {{ type: 'slider', start: 0, end: 100, height: 22, bottom: 12 }}
    ],
    series: [{{
      type: 'line',
      showSymbol: false,
      sampling: 'lttb',
      lineStyle: {{ width: 1.5, color: '#7a3dff' }},
      areaStyle: {{
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          {{ offset: 0, color: 'rgba(122,61,255,0.18)' }},
          {{ offset: 1, color: 'rgba(122,61,255,0.02)' }}
        ])
      }},
      data: CHART_DATA,
      large: true,
      largeThreshold: 2000
    }}]
  }};
  chart.setOption(option);
  window.addEventListener('resize', () => chart.resize());
}})();

function showTab(name, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}}

// 数据预览分页
const PREVIEW_ROWS = __PREVIEW_ROWS_JSON__;
let pgCurrent = 1;
let pgSize = __PREVIEW_PAGE_SIZE__;

function pgEscape(s) {{
  return String(s).replace(/[&<>"']/g, c => ({{
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }}[c]));
}}

function pgTotalPages() {{
  return Math.max(1, Math.ceil(PREVIEW_ROWS.length / pgSize));
}}

function pgRender() {{
  const total = PREVIEW_ROWS.length;
  if (total === 0) {{
    document.getElementById('pgBody').innerHTML =
      '<tr><td colspan="5" class="empty">暂无数据。</td></tr>';
    document.getElementById('pgInfo').textContent = '无数据';
    return;
  }}
  const totalPages = pgTotalPages();
  if (pgCurrent > totalPages) pgCurrent = totalPages;
  if (pgCurrent < 1) pgCurrent = 1;

  const start = (pgCurrent - 1) * pgSize;
  const end = Math.min(start + pgSize, total);

  let html = '';
  for (let i = start; i < end; i++) {{
    const row = PREVIEW_ROWS[i];
    html += '<tr>'
      + '<td>' + (i + 1) + '</td>'
      + '<td class="mono">' + pgEscape(row[0]) + '</td>'
      + '<td class="mono">' + pgEscape(row[1]) + '</td>'
      + '<td class="mono">' + pgEscape(row[2]) + '</td>'
      + '<td class="mono">' + pgEscape(row[3]) + '</td>'
      + '</tr>';
  }}
  document.getElementById('pgBody').innerHTML = html;
  document.getElementById('pgInput').value = pgCurrent;
  document.getElementById('pgTotal').textContent = totalPages;
  document.getElementById('pgInfo').textContent =
    '显示 ' + (start + 1) + ' ~ ' + end + ' 条，共 ' + total + ' 条';
}}

function pgFirst() {{ pgCurrent = 1; pgRender(); }}
function pgPrev()  {{ pgCurrent -= 1; pgRender(); }}
function pgNext()  {{ pgCurrent += 1; pgRender(); }}
function pgLast()  {{ pgCurrent = pgTotalPages(); pgRender(); }}
function pgJump()  {{
  const v = parseInt(document.getElementById('pgInput').value) || 1;
  pgCurrent = v;
  pgRender();
}}
function pgSizeChange() {{
  pgSize = parseInt(document.getElementById('pgSize').value) || 200;
  pgCurrent = 1;
  pgRender();
}}

if (PREVIEW_ROWS.length > 0) pgRender();
</script>
</body>
</html>
"""


class ReportBuilder:
    """采集数据 → 生成单文件交互式 HTML 报告"""

    def __init__(self, output_dir: str = "./data/reports",
                 max_points: int = MAX_POINTS):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._max_points = max_points
        # 每个点是 (timestamp, elapsed_s, value, raw_str)
        self._data: deque = deque(maxlen=max_points)
        self._metadata: dict = {}
        self._alarm_log_path: Optional[Path] = None

        # 内存报警记录
        self._alarm_records: List = []
        self._use_memory_alarms: bool = False

        self._project_root = Path(__file__).resolve().parent.parent
        self._echarts_path = self._project_root / "libs" / "echarts.min.js"

    # ------------------------------------------------------------
    # 数据收集
    # ------------------------------------------------------------
    @property
    def has_data(self) -> bool:
        return len(self._data) > 0

    @property
    def count(self) -> int:
        return len(self._data)

    def has_metadata(self) -> bool:
        return bool(self._metadata)

    def get_metadata(self, key: str, default=None):
        return self._metadata.get(key, default)

    def reset(self) -> None:
        self._data.clear()
        self._metadata.clear()
        self._alarm_records.clear()
        self._use_memory_alarms = False

    def clear_data(self) -> None:
        self._data.clear()

    def set_metadata(self, **kwargs) -> None:
        self._metadata.update(kwargs)

    # ------------------------------------------------------------
    # 报警数据源
    # ------------------------------------------------------------
    def set_alarm_records(self, records) -> None:
        if records is None:
            self._alarm_records = []
        elif hasattr(records, "get_records"):
            self._alarm_records = list(records.get_records())
        else:
            self._alarm_records = list(records)
        self._use_memory_alarms = True

    def set_alarm_log(self, path) -> None:
        self._alarm_log_path = Path(path) if path else None

    def add_point(self, timestamp: str, elapsed_s: float,
                  value: float, raw_str: str = "") -> None:
        try:
            self._data.append((
                str(timestamp),
                float(elapsed_s),
                float(value),
                str(raw_str),
            ))
        except (TypeError, ValueError):
            pass

    def get_all_data(self) -> list:
        """返回全部数据点的快照（供外部导出）。"""
        return list(self._data)

    # ------------------------------------------------------------
    # ECharts 内嵌
    # ------------------------------------------------------------
    def _build_echarts_tag(self) -> str:
        if self._echarts_path.is_file():
            try:
                js = self._echarts_path.read_text(encoding="utf-8")
                return f"<script>{js}</script>"
            except Exception as e:
                print(f"[报告] 读取 echarts.min.js 失败: {e}")

        print(f"[报告] 未找到 {self._echarts_path}，使用 CDN（需要联网）")
        return ('<script src="https://cdn.jsdelivr.net/npm/'
                'echarts@5/dist/echarts.min.js"></script>')

    # ------------------------------------------------------------
    # 生成
    # ------------------------------------------------------------
    def generate(self, prefix: str = "dmm6500_report",
                 auto_open: bool = True) -> str:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        unit = self._metadata.get("unit", "")

        stats = self._compute_stats()
        chart_data = self._build_chart_data()

        current_alarms = self._load_current_alarms()
        history_alarms = self._load_history_alarms()

        total_rows = len(self._data)
        embed_rows = list(self._data)[:MAX_EMBED_ROWS]
        truncated = total_rows > MAX_EMBED_ROWS
        preview_json = self._build_preview_json(embed_rows)

        duration_str = "—"
        data_range_str = "—"
        if len(self._data) >= 2:
            t0 = self._data[0][1]
            t1 = self._data[-1][1]
            duration_str = self._format_duration(t1 - t0)
            data_range_str = f"{t0:.2f}s ~ {t1:.2f}s"

        html = _HTML_TEMPLATE
        html = html.replace(_ECHARTS_PLACEHOLDER, self._build_echarts_tag())

        html = html.replace("__GENERATED_AT__", generated_at)
        html = html.replace("__TOTAL_COUNT__", f"{total_rows:,}")
        html = html.replace("__DURATION__", duration_str)
        html = html.replace("__DATA_RANGE__", data_range_str)

        html = html.replace("__META_ROWS__", self._render_meta_rows())
        html = html.replace("__STATS_CARDS__",
                            self._render_stats_cards(stats, unit))

        chart_json = json.dumps(chart_data, ensure_ascii=False,
                                allow_nan=False, separators=(",", ":")) \
            if chart_data else "[]"
        html = html.replace("__CHART_JSON__", chart_json)
        html = html.replace("__UNIT_JSON__", json.dumps(unit, ensure_ascii=False))
        if chart_data:
            html = html.replace("__CHART_DISPLAY__", "")
            html = html.replace("__CHART_EMPTY__", "")
        else:
            html = html.replace("__CHART_DISPLAY__", "display:none;")
            html = html.replace(
                "__CHART_EMPTY__",
                '<div class="empty">暂无数据，请先采集后生成报告。</div>'
            )

        html = html.replace("__ALARM_CURRENT_COUNT__", str(len(current_alarms)))
        html = html.replace("__ALARM_HISTORY_COUNT__", str(len(history_alarms)))
        html = html.replace("__ALARM_HISTORY_LIMIT__", str(MAX_HISTORY_ALARMS))
        html = html.replace("__ALARM_CURRENT_HTML__",
                            self._render_alarm_list(current_alarms,
                                                    "本次报告时间段内无报警记录。"))
        html = html.replace("__ALARM_HISTORY_HTML__",
                            self._render_alarm_list(history_alarms,
                                                    "历史报警日志为空。"))

        html = html.replace("__PREVIEW_TOTAL__", f"{total_rows:,}")
        if truncated:
            note = (f'<br><span style="color: #ee1d36;">'
                    f'⚠️ 数据量过大（共 {total_rows:,} 行），'
                    f'仅嵌入前 {MAX_EMBED_ROWS:,} 行用于预览</span>')
        else:
            note = ""
        html = html.replace("__TRUNCATED_NOTE__", note)

        html = html.replace("__PREVIEW_CONTROLS__", self._render_preview_controls())
        html = html.replace("__PREVIEW_ROWS_JSON__", preview_json)
        html = html.replace("__PREVIEW_PAGE_SIZE__", str(MAX_PREVIEW_ROWS))

        # ✅ 文件名加序号，防同秒覆盖
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}.html"
        filepath = self.output_dir / filename

        if filepath.exists():
            idx = 1
            while True:
                filename = f"{prefix}_{ts}_{idx:03d}.html"
                filepath = self.output_dir / filename
                if not filepath.exists():
                    break
                idx += 1

        filepath.write_text(html, encoding="utf-8")

        if auto_open:
            try:
                webbrowser.open(filepath.absolute().as_uri())
            except Exception:
                pass

        return str(filepath)

    # ------------------------------------------------------------
    # 内部渲染
    # ------------------------------------------------------------
    def _compute_stats(self) -> dict:
        if not self._data:
            return {}
        ys = np.array([v for _, _, v, _ in self._data], dtype=np.float64)
        ys = ys[np.isfinite(ys)]
        if ys.size == 0:
            return {}
        return {
            "count": int(ys.size),
            "max": float(np.max(ys)),
            "min": float(np.min(ys)),
            "mean": float(np.mean(ys)),
            "std": float(np.std(ys)),
            "range": float(np.max(ys) - np.min(ys)),
        }

    def _build_chart_data(self):
        if not self._data:
            return []
        xs = [d[1] for d in self._data]
        ys = [d[2] for d in self._data]
        n = len(xs)
        if n > MAX_CHART_POINTS:
            step = max(1, n // MAX_CHART_POINTS)
            xs_ds = xs[::step]
            ys_ds = ys[::step]
            if xs_ds and xs_ds[-1] != xs[-1]:
                xs_ds.append(xs[-1])
                ys_ds.append(ys[-1])
        else:
            xs_ds, ys_ds = xs, ys
        return [[round(float(x), 6), round(float(y), 9)]
                for x, y in zip(xs_ds, ys_ds)]

    def _build_preview_json(self, rows) -> str:
        arr = []
        for ts, t, v, raw in rows:
            arr.append([
                str(ts),
                f"{t:.6f}",
                f"{v:.9g}",
                str(raw),
            ])
        return json.dumps(arr, ensure_ascii=False,
                          allow_nan=False, separators=(",", ":"))

    def _render_preview_controls(self) -> str:
        return """
        <div class="preview-controls">
          <button class="pg-btn" onclick="pgFirst()" title="首页">⏮ 首页</button>
          <button class="pg-btn" onclick="pgPrev()" title="上一页">◀ 上一页</button>
          <span>
            第
            <input id="pgInput" class="pg-input" type="number" min="1" value="1"
                   onchange="pgJump()" onkeydown="if(event.key==='Enter')pgJump()">
            / <span id="pgTotal">1</span> 页
          </span>
          <button class="pg-btn" onclick="pgNext()" title="下一页">下一页 ▶</button>
          <button class="pg-btn" onclick="pgLast()" title="末页">末页 ⏭</button>
          <span class="pg-sep">|</span>
          <label>每页
            <select id="pgSize" class="pg-select" onchange="pgSizeChange()">
              <option value="100">100</option>
              <option value="200" selected>200</option>
              <option value="500">500</option>
              <option value="1000">1000</option>
            </select>
            条
          </label>
          <span id="pgInfo" class="pg-info-right"></span>
        </div>
        """

    # ✅ 提前判断内存报警是否启用（避免白扫 100 万点）
    def _load_current_alarms(self) -> List[str]:
        if not self._use_memory_alarms:
            return []
        if not self._data:
            return []

        # 单次遍历取时间范围（原实现新建一个 100 万元素列表再 min/max）
        t_min = None
        t_max = None
        for d in self._data:
            t = d[1]
            if t_min is None or t < t_min:
                t_min = t
            if t_max is None or t > t_max:
                t_max = t
        if t_min is None or t_max is None:
            return []
        t_min -= 0.5
        t_max += 0.5

        result = []
        for r in self._alarm_records:
            elapsed = getattr(r, "elapsed_s", None)
            text = getattr(r, "text", str(r))
            if elapsed is None:
                continue
            if t_min <= elapsed <= t_max:
                result.append(text)
        return result

    # ✅ 只读最近 N 条（防日志膨胀）
    def _load_history_alarms(self) -> List[str]:
        if self._alarm_log_path is None or not self._alarm_log_path.is_file():
            return []
        try:
            with open(self._alarm_log_path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            # 只保留最近 MAX_HISTORY_ALARMS 条
            if len(lines) > MAX_HISTORY_ALARMS:
                lines = lines[-MAX_HISTORY_ALARMS:]
            return lines
        except Exception:
            return []

    def _render_alarm_list(self, alarms: list, empty_text: str) -> str:
        if not alarms:
            return f'<div class="empty">{_html.escape(empty_text)}</div>'
        items = "".join(f'<li>{_html.escape(str(a))}</li>' for a in alarms)
        return f'<ul class="alarm-list">{items}</ul>'

    def _render_meta_rows(self) -> str:
        if not self._metadata:
            return '<tr><td colspan="2" class="empty">无元数据</td></tr>'
        order = ["mode", "unit", "terminal", "nplc", "range", "started_at"]
        keys = [k for k in order if k in self._metadata]
        keys += [k for k in self._metadata if k not in keys]
        rows = []
        for k in keys:
            v = self._metadata[k]
            rows.append(
                f'<tr><th>{_html.escape(str(k))}</th>'
                f'<td>{_html.escape(str(v))}</td></tr>'
            )
        return "".join(rows)

    # ✅ 采样点数卡片不带单位
    def _render_stats_cards(self, stats: dict, unit: str) -> str:
        if not stats:
            return '<div class="stat-card"><div class="label">状态</div>' \
                   '<div class="value">无数据</div></div>'
        unit_html = f'<span class="unit">{_html.escape(unit)}</span>' if unit else ""

        def card(label, val, with_unit: bool = True):
            suffix = unit_html if with_unit else ""
            return (f'<div class="stat-card">'
                    f'<div class="label">{label}</div>'
                    f'<div class="value">{val}{suffix}</div>'
                    f'</div>')

        return "".join([
            card("采样点数", f"{stats['count']:,}", with_unit=False),
            card("最大值", f"{stats['max']:.6g}"),
            card("最小值", f"{stats['min']:.6g}"),
            card("平均值", f"{stats['mean']:.6g}"),
            card("标准差", f"{stats['std']:.6g}"),
            card("峰峰值", f"{stats['range']:.6g}"),
        ])

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.2f} 秒"
        if seconds < 3600:
            m = int(seconds // 60)
            s = seconds % 60
            return f"{m} 分 {s:.1f} 秒"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h} 时 {m} 分 {s} 秒"