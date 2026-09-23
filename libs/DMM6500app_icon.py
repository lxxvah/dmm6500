#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
libs/app_icon.py —— 通用主题图标管理器
==========================================
按主题动态生成应用图标，可绑定到任意 PyQt6 窗口/组件。

特性：
  · 5 个内置主题（light / dark / nord / solarized_light / dracula）
  · 支持注册自定义主题
  · 一个管理器可绑定多个窗口，set_theme 时全部同步刷新
  · 自动缓存（同一主题只渲染一次）
  · 优雅降级：Pillow / PyQt6 缺失时给出清晰错误

依赖：
    pip install Pillow
    pip install PyQt6

用法（推荐：全局单例）：
    from libs.app_icon import set_window_icon

    set_window_icon(window, theme="dark")           # 一次性设置
    # 或
    set_window_icon(window, theme="nord", auto_register=True)

用法（高级：自建实例）：
    from libs.app_icon import AppIconManager

    mgr = AppIconManager()
    mgr.register_theme("custom", {
        "bg": "#000000", "border": "#333", "grid": "#111",
        "wave": "#00ff88", "wave2": "#00aaff", "accent": "#ff3366",
    })
    mgr.attach(window1)
    mgr.attach(window2)
    mgr.set_theme("custom")                         # 两个窗口一起变
"""

from __future__ import annotations

import math
import threading
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

# ---------- 依赖检测 ----------
try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None
    ImageDraw = None

try:
    from PyQt6.QtGui import QIcon, QPixmap
    from PyQt6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False
    QIcon = None
    QPixmap = None
    QApplication = None


# 兼容 Pillow 9+ 的重采样常量
if HAS_PIL:
    try:
        _LANCZOS = Image.Resampling.LANCZOS
    except AttributeError:
        _LANCZOS = Image.LANCZOS
else:
    _LANCZOS = None


# ============================================================
# 主类
# ============================================================
class AppIconManager:
    """
    主题图标管理器。

    线程安全：缓存访问用锁保护。
    注意：to_qicon() 必须在 Qt 主线程调用（QPixmap 要求）。
    """

    # ---- ✅ 内置 5 主题配色 ----
    BUILTIN_PALETTES: Dict[str, Dict[str, str]] = {
        "light": {
            "bg":      "#ffffff",
            "border":  "#d8d8d8",
            "grid":    "#e8e8e8",
            "wave":    "#7a3dff",   # 主波形（紫）
            "wave2":   "#3b89ff",   # 次波形（蓝）
            "accent":  "#ee1d36",   # 末端点（红）
        },
        "dark": {
            "bg":      "#1e1e1e",
            "border":  "#3a3a3a",
            "grid":    "#2a2a2a",
            "wave":    "#9d6fff",
            "wave2":   "#4da3ff",
            "accent":  "#ff4757",
        },
        "nord": {
            "bg":      "#2e3440",
            "border":  "#4c566a",
            "grid":    "#3b4252",
            "wave":    "#88c0d0",   # 冰蓝
            "wave2":   "#81a1c1",
            "accent":  "#bf616a",
        },
        "solarized_light": {
            "bg":      "#fdf6e3",
            "border":  "#eee8d5",
            "grid":    "#f0e8d4",
            "wave":    "#268bd2",
            "wave2":   "#2aa198",
            "accent":  "#dc322f",
        },
        "dracula": {
            "bg":      "#282a36",
            "border":  "#44475a",
            "grid":    "#313442",
            "wave":    "#bd93f9",
            "wave2":   "#8be9fd",
            "accent":  "#ff79c6",
        },
    }

    DEFAULT_THEME = "light"
    DEFAULT_SIZES: Tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)

    # ============================================================
    # 初始化
    # ============================================================
    def __init__(self,
                 icon_size: int = 256,
                 palettes: Optional[Dict[str, Dict[str, str]]] = None,
                 supersample: int = 4):
        """
        Args:
            icon_size:    底图尺寸（越大越清晰，建议 256）
            palettes:     自定义主题字典 {name: {bg,border,grid,wave,wave2,accent}}
                          会与内置主题合并（同名覆盖）
            supersample:  超采样倍数（抗锯齿用，4 倍效果良好）
        """
        if not HAS_PIL:
            raise ImportError(
                "AppIconManager 需要 Pillow 库。\n"
                "请运行：pip install Pillow"
            )

        self.icon_size = icon_size
        self.supersample = max(1, int(supersample))

        # 主题表：内置 + 用户自定义
        self._palettes: Dict[str, Dict[str, str]] = {
            k: dict(v) for k, v in self.BUILTIN_PALETTES.items()
        }
        if palettes:
            for name, pal in palettes.items():
                self._palettes[name] = dict(pal)

        # 缓存
        self._pil_cache: Dict[str, Any] = {}       # name -> PIL Image
        self._qicon_cache: Dict[str, Any] = {}     # name -> QIcon
        self._lock = threading.Lock()

        # 已绑定的窗口
        self._targets: List[Any] = []
        self._current_theme: str = self.DEFAULT_THEME

    # ============================================================
    # 主题管理
    # ============================================================
    def register_theme(self, name: str, palette: Dict[str, str]) -> None:
        """
        注册或覆盖一个主题。

        Args:
            name:    主题名（唯一）
            palette: 配色字典，必须包含 6 个 key：
                     bg, border, grid, wave, wave2, accent
        """
        required = {"bg", "border", "grid", "wave", "wave2", "accent"}
        missing = required - set(palette.keys())
        if missing:
            raise ValueError(
                f"主题 '{name}' 缺少字段: {missing}\n"
                f"必须提供: {required}"
            )
        with self._lock:
            self._palettes[name] = dict(palette)
            # 使缓存失效
            self._pil_cache.pop(name, None)
            self._qicon_cache.pop(name, None)

    def list_themes(self) -> List[str]:
        """返回所有已注册的主题名"""
        return list(self._palettes.keys())

    def has_theme(self, name: str) -> bool:
        return name in self._palettes

    # ============================================================
    # 渲染
    # ============================================================
    def render(self, theme_name: str):
        """
        渲染指定主题的 PIL Image（RGBA）。

        Returns:
            PIL.Image.Image
        """
        if theme_name not in self._palettes:
            raise KeyError(f"未注册的主题: '{theme_name}'")

        with self._lock:
            if theme_name in self._pil_cache:
                return self._pil_cache[theme_name]

        img = self._render_pil(theme_name)

        with self._lock:
            self._pil_cache[theme_name] = img

        return img

    def _render_pil(self, theme_name: str):
        """实际渲染逻辑"""
        cfg = self._palettes[theme_name]
        size = self.icon_size
        ss = self.supersample
        W = size * ss
        scale = W / 256.0

        def S(v: float) -> int:
            return int(round(v * scale))

        # ---------- 画布 ----------
        img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # ---------- 圆角方形外壳 ----------
        margin = S(12)
        radius = S(56)
        draw.rounded_rectangle(
            [margin, margin, W - margin, W - margin],
            radius=radius,
            fill=cfg["bg"],
            outline=cfg["border"],
            width=max(1, S(3)),
        )

        # ---------- 内嵌显示区（微妙的明暗层次） ----------
        im = S(34)
        ir = S(34)
        bg_rgb = self._hex_to_rgb(cfg["bg"])
        brightness = (bg_rgb[0] * 299 + bg_rgb[1] * 587 + bg_rgb[2] * 114) / 1000

        overlay = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        if brightness > 128:
            od.rounded_rectangle([im, im, W - im, W - im], radius=ir,
                                 fill=(0, 0, 0, 12))
        else:
            od.rounded_rectangle([im, im, W - im, W - im], radius=ir,
                                 fill=(255, 255, 255, 14))
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

        # ---------- 网格 ----------
        grid_rgb = self._hex_to_rgb(cfg["grid"])
        grid_color = grid_rgb + (90,)
        gw = max(1, S(1))
        grid_pad = S(16)
        for i in range(1, 4):
            y = im + (W - 2 * im) * i // 4
            draw.line([(im + grid_pad, y), (W - im - grid_pad, y)],
                      fill=grid_color, width=gw)
        for i in range(1, 4):
            x = im + (W - 2 * im) * i // 4
            draw.line([(x, im + grid_pad), (x, W - im - grid_pad)],
                      fill=grid_color, width=gw)

        # ---------- 主波形 ----------
        wave_left = im + S(20)
        wave_right = W - im - S(20)
        wave_cy = W // 2
        wave_amp = S(52)
        n = 80
        main_pts = []
        for i in range(n):
            t = i / (n - 1)
            x = wave_left + (wave_right - wave_left) * t
            y = wave_cy + (
                math.sin(t * 2 * math.pi * 1.8) * wave_amp * 0.70 +
                math.sin(t * 2 * math.pi * 3.6 + 0.8) * wave_amp * 0.25
            )
            main_pts.append((int(x), int(y)))

        main_w = max(2, S(11))
        draw.line(main_pts, fill=cfg["wave"], width=main_w, joint="curve")

        # ---------- 次波形 ----------
        secondary_cy = W // 2 + S(30)
        secondary_amp = S(30)
        sec_pts = []
        for i in range(n):
            t = i / (n - 1)
            x = wave_left + (wave_right - wave_left) * t
            y = secondary_cy + (
                math.sin(t * 2 * math.pi * 2.2 + 1.3) * secondary_amp * 0.60 +
                math.sin(t * 2 * math.pi * 4.4) * secondary_amp * 0.20
            )
            sec_pts.append((int(x), int(y)))

        sec_w = max(2, S(6))
        draw.line(sec_pts, fill=cfg["wave2"], width=sec_w, joint="curve")

        # ---------- 末端读数点 + 光晕 ----------
        dot_cx = int(main_pts[-1][0])
        dot_cy = int(main_pts[-1][1])
        dot_r = S(11)
        accent_rgb = self._hex_to_rgb(cfg["accent"])

        halo = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        for r_off, alpha in ((S(14), 22), (S(7), 55)):
            r = dot_r + r_off
            hd.ellipse([dot_cx - r, dot_cy - r, dot_cx + r, dot_cy + r],
                       fill=accent_rgb + (alpha,))
        img = Image.alpha_composite(img, halo)
        draw = ImageDraw.Draw(img)

        draw.ellipse([dot_cx - dot_r, dot_cy - dot_r,
                      dot_cx + dot_r, dot_cy + dot_r],
                     fill=cfg["accent"])

        # ---------- 缩放回目标尺寸 ----------
        if ss > 1:
            img = img.resize((size, size), _LANCZOS)

        return img

    # ============================================================
    # Qt 导出
    # ============================================================
    def to_qicon(self, theme_name: str):
        """
        生成多尺寸 QIcon（供 setWindowIcon 使用）。

        注意：必须在 QApplication 创建后调用。
        """
        if not HAS_QT:
            raise ImportError("PyQt6 未安装")

        if QApplication.instance() is None:
            raise RuntimeError(
                "需要先创建 QApplication 才能生成 QIcon"
            )

        with self._lock:
            if theme_name in self._qicon_cache:
                return self._qicon_cache[theme_name]

        base = self.render(theme_name)

        icon = QIcon()
        for sz in self.DEFAULT_SIZES:
            img_sz = base if sz == self.icon_size else base.resize(
                (sz, sz), _LANCZOS
            )
            buf = BytesIO()
            img_sz.save(buf, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue(), "PNG")
            icon.addPixmap(pixmap)

        with self._lock:
            self._qicon_cache[theme_name] = icon

        return icon

    def to_qpixmap(self, theme_name: str, size: int = 64):
        """生成单尺寸 QPixmap"""
        if not HAS_QT:
            raise ImportError("PyQt6 未安装")
        if QApplication.instance() is None:
            raise RuntimeError("需要先创建 QApplication 才能生成 QPixmap")

        img = self.render(theme_name).resize((size, size), _LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue(), "PNG")
        return pixmap

    def save_png(self, theme_name: str, path: str,
                 size: Optional[int] = None) -> None:
        """导出 PNG 文件（用于打包/网页/favicon）"""
        img = self.render(theme_name)
        if size is not None and size != self.icon_size:
            img = img.resize((size, size), _LANCZOS)
        img.save(path, format="PNG")

    # ============================================================
    # 窗口绑定
    # ============================================================
    def attach(self, window: Any) -> None:
        """
        绑定 Qt 窗口/组件。attach 后，set_theme() 会自动刷新其图标。

        可多次调用，绑定多个窗口。
        """
        if window is None or window in self._targets:
            return
        self._targets.append(window)
        # 立即应用当前主题
        try:
            window.setWindowIcon(self.to_qicon(self._current_theme))
        except Exception as e:
            print(f"[图标] 绑定窗口失败: {e}")

    def detach(self, window: Any) -> None:
        """解绑"""
        if window in self._targets:
            self._targets.remove(window)

    def detach_all(self) -> None:
        """解绑全部"""
        self._targets.clear()

    def set_theme(self, theme_name: str) -> None:
        """
        切换主题：重新生成图标并应用到所有已绑定的窗口。

        主题不存在时静默忽略（不抛异常，避免切换失败）。
        """
        if theme_name not in self._palettes:
            print(f"[图标] 未知主题: '{theme_name}'，忽略")
            return

        self._current_theme = theme_name

        try:
            icon = self.to_qicon(theme_name)
        except Exception as e:
            print(f"[图标] 生成 QIcon 失败: {e}")
            return

        for w in list(self._targets):
            try:
                w.setWindowIcon(icon)
            except Exception as e:
                print(f"[图标] 应用失败: {e}")

    def current_theme(self) -> str:
        return self._current_theme

    # ============================================================
    # 应用级图标（影响所有窗口的默认图标）
    # ============================================================
    def set_application_icon(self, theme_name: str) -> None:
        """设置 QApplication 级别的默认图标（影响任务栏/所有窗口）"""
        if not HAS_QT:
            return
        app = QApplication.instance()
        if app is None:
            return
        try:
            app.setWindowIcon(self.to_qicon(theme_name))
        except Exception as e:
            print(f"[图标] 应用级图标设置失败: {e}")

    # ============================================================
    # 缓存管理
    # ============================================================
    def clear_cache(self) -> None:
        """清空 PIL 和 QIcon 缓存（主题配色改动后调用）"""
        with self._lock:
            self._pil_cache.clear()
            self._qicon_cache.clear()

    # ============================================================
    # 内部工具
    # ============================================================
    @staticmethod
    def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
        h = hex_str.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ============================================================
# 全局单例（模块级快捷函数）
# ============================================================
_default_manager: Optional[AppIconManager] = None
_default_lock = threading.Lock()


def get_icon_manager() -> AppIconManager:
    """获取全局单例（懒加载）"""
    global _default_manager
    if _default_manager is None:
        with _default_lock:
            if _default_manager is None:
                _default_manager = AppIconManager()
    return _default_manager


def set_window_icon(window: Any, theme: str = "light") -> AppIconManager:
    """
    一行代码：给窗口绑定主题图标管理器。

    返回 AppIconManager 实例，方便后续切换主题：
        mgr = set_window_icon(window, "light")
        mgr.set_theme("dark")    # 图标会跟着变
    """
    mgr = get_icon_manager()
    mgr.attach(window)
    mgr.set_theme(theme)
    return mgr


def set_application_icon(theme: str = "light") -> None:
    """一行代码：给 QApplication 设置默认图标"""
    get_icon_manager().set_application_icon(theme)