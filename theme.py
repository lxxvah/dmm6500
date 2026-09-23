#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theme.py —— 多主题配色模块（苹果风格）
===========================================
· 5 主题 × 5 语义色（按钮）
· 5 主题 × 4 统计色（卡片）
· GroupBox：卡片内部左上角标题（顶部与右侧卡片齐平）
"""

from __future__ import annotations
from typing import Dict


class COLORS:
    PRIMARY       = "#080808"
    ON_PRIMARY    = "#ffffff"
    INK           = "#080808"
    INK_STRONG    = "#222222"
    BODY          = "#363636"
    BODY_MID      = "#5a5a5a"
    MUTE          = "#898989"
    MUTE_SOFT     = "#ababab"
    HAIRLINE      = "#d8d8d8"
    CANVAS        = "#ffffff"

    ACCENT_PURPLE = "#7a3dff"
    ACCENT_PINK   = "#ed52cb"
    ACCENT_BLUE   = "#3b89ff"
    ACCENT_BLUE_DEEP = "#006acc"
    ACCENT_BLUE_INFO = "#146ef5"
    ACCENT_ORANGE = "#ff6b00"
    ACCENT_GREEN  = "#00d722"
    ACCENT_YELLOW = "#ffae13"
    ACCENT_RED    = "#ee1d36"

    DARK_BG        = "#1a1a1a"
    DARK_BG_DEEP   = "#0a0a0a"
    DARK_INK       = "#f0f0f0"
    DARK_BODY      = "#c0c0c0"
    DARK_HAIRLINE  = "#3a3a3a"
    DARK_CARD_BG   = "#2a2a2a"


FONTS = type("FONTS", (), {
    "FAMILY": "Microsoft YaHei UI, Inter, system-ui, sans-serif",
    "MONO": "Consolas, 'Courier New', monospace",
    "SIZE_DISPLAY": "22px",
    "SIZE_TITLE": "11px",
    "SIZE_VALUE": "18px",
    "SIZE_BODY": "11px",
    "SIZE_CAPTION": "10px",
    "WEIGHT_BOLD": 600,
    "WEIGHT_MEDIUM": 500,
    "WEIGHT_NORMAL": 400,
})

SPACING = type("SPACING", (), {"XS": 2, "SM": 4, "MD": 6, "LG": 8, "XL": 12, "XXL": 16})
RADIUS = type("RADIUS", (), {"NONE": 0, "XS": 2, "SM": 4, "MD": 6, "LG": 8, "FULL": 9999})


THEME_CYCLE = ['light', 'dark', 'nord', 'solarized_light', 'dracula']
DARK_THEMES = {'dark', 'nord', 'dracula'}


SEMANTIC_COLORS: Dict[str, Dict[str, str]] = {
    'light': {
        'primary':        "#007AFF", 'primary_hover': "#0066D6",
        'danger':         "#FF3B30", 'danger_hover':  "#D93025",
        'warning':        "#FF9500", 'warning_hover': "#D97F00",
        'success':        "#34C759", 'success_hover': "#2AA84A",
        'neutral_bg':     "#E5E5EA", 'neutral_hover': "#D1D1D6",
        'neutral_press':  "#C7C7CC", 'neutral_fg':    "#363636",
    },
    'dark': {
        'primary':        "#0A84FF", 'primary_hover': "#409CFF",
        'danger':         "#FF453A", 'danger_hover':  "#FF6961",
        'warning':        "#FF9F0A", 'warning_hover': "#FFB340",
        'success':        "#30D158", 'success_hover': "#5FDD7F",
        'neutral_bg':     "#3A3A3C", 'neutral_hover': "#48484A",
        'neutral_press':  "#2C2C2E", 'neutral_fg':    "#F0F0F0",
    },
    'nord': {
        'primary':        "#5E81AC", 'primary_hover': "#81A1C1",
        'danger':         "#BF616A", 'danger_hover':  "#D08770",
        'warning':        "#D08770", 'warning_hover': "#E39B86",
        'success':        "#A3BE8C", 'success_hover': "#B8D0A4",
        'neutral_bg':     "#3B4252", 'neutral_hover': "#434C5E",
        'neutral_press':  "#2E3440", 'neutral_fg':    "#D8DEE9",
    },
    'solarized_light': {
        'primary':        "#268BD2", 'primary_hover': "#1E6FA8",
        'danger':         "#DC322F", 'danger_hover':  "#B52623",
        'warning':        "#CB4B16", 'warning_hover': "#A63D12",
        'success':        "#859900", 'success_hover': "#6B7A00",
        'neutral_bg':     "#EEE8D5", 'neutral_hover': "#E4DCCA",
        'neutral_press':  "#D9D0BC", 'neutral_fg':    "#073642",
    },
    'dracula': {
        'primary':        "#BD93F9", 'primary_hover': "#CAA8FA",
        'danger':         "#FF5555", 'danger_hover':  "#FF7979",
        'warning':        "#FFB86C", 'warning_hover': "#FFCB8E",
        'success':        "#50FA7B", 'success_hover': "#7CFB9A",
        'neutral_bg':     "#44475A", 'neutral_hover': "#525566",
        'neutral_press':  "#383B4D", 'neutral_fg':    "#F8F8F2",
    },
}


STATS_COLORS: Dict[str, Dict[str, str]] = {
    'light': {
        'max': "#FF3B30", 'min': "#007AFF",
        'avg': "#34C759", 'std': "#AF52DE",
    },
    'dark': {
        'max': "#FF453A", 'min': "#0A84FF",
        'avg': "#30D158", 'std': "#BF5AF2",
    },
    'nord': {
        'max': "#BF616A", 'min': "#5E81AC",
        'avg': "#A3BE8C", 'std': "#B48EAD",
    },
    'solarized_light': {
        'max': "#DC322F", 'min': "#268BD2",
        'avg': "#859900", 'std': "#6C71C4",
    },
    'dracula': {
        'max': "#FF5555", 'min': "#8BE9FD",
        'avg': "#50FA7B", 'std': "#BD93F9",
    },
}


REALTIME_CARD_BG: Dict[str, str] = {
    'light':            "#1C1C1E",
    'dark':             "#0A0A0A",
    'nord':             "#1F2430",
    'solarized_light':  "#073642",
    'dracula':          "#1E1F29",
}


def _hex_to_rgb(hex_str: str):
    h = hex_str.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgba_css(hex_color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


class Theme:
    def __init__(self, mode: str = 'light'):
        if mode not in SEMANTIC_COLORS:
            mode = 'light'
        self.mode = mode
        self.is_dark = (mode in DARK_THEMES)
        self._build_palette()

    def _build_palette(self):
        if self.is_dark:
            self.bg            = "#1a1a1a"
            self.bg_deep       = "#0a0a0a"
            self.card_bg       = "#2a2a2a"
            self.fg            = "#f0f0f0"
            self.fg_mid        = "#c0c0c0"
            self.fg_mute       = "#898989"
            self.hairline      = "#3a3a3a"
            self.input_bg      = "#252525"
            self.input_fg      = "#f0f0f0"
            self.plot_bg       = "#0a0a0a"
            self.plot_grid     = "#3a3a3a"
            self.plot_text     = "#c0c0c0"
            self.group_title_bg = "#1a1a1a"
        else:
            self.bg            = "#ffffff"
            self.bg_deep       = "#ffffff"
            self.card_bg       = "#ffffff"
            self.fg            = "#080808"
            self.fg_mid        = "#363636"
            self.fg_mute       = "#898989"
            self.hairline      = "#d8d8d8"
            self.input_bg      = "#ffffff"
            self.input_fg      = "#080808"
            self.plot_bg       = "#ffffff"
            self.plot_grid     = "#d8d8d8"
            self.plot_text     = "#363636"
            self.group_title_bg = "#ffffff"

        if self.mode == 'nord':
            self.bg            = "#2e3440"
            self.bg_deep       = "#272c36"
            self.card_bg       = "#3b4252"
            self.fg            = "#eceff4"
            self.fg_mid        = "#d8dee9"
            self.fg_mute       = "#7b88a1"
            self.hairline      = "#4c566a"
            self.input_bg      = "#3b4252"
            self.input_fg      = "#eceff4"
            self.plot_bg       = "#2e3440"
            self.plot_grid     = "#4c566a"
            self.plot_text     = "#d8dee9"
            self.group_title_bg = "#2e3440"
        elif self.mode == 'solarized_light':
            self.bg            = "#fdf6e3"
            self.bg_deep       = "#eee8d5"
            self.card_bg       = "#fdf6e3"
            self.fg            = "#073642"
            self.fg_mid        = "#586e75"
            self.fg_mute       = "#93a1a1"
            self.hairline      = "#eee8d5"
            self.input_bg      = "#fdf6e3"
            self.input_fg      = "#073642"
            self.plot_bg       = "#fdf6e3"
            self.plot_grid     = "#eee8d5"
            self.plot_text     = "#657b83"
            self.group_title_bg = "#fdf6e3"
        elif self.mode == 'dracula':
            self.bg            = "#282a36"
            self.bg_deep       = "#1e1f29"
            self.card_bg       = "#44475a"
            self.fg            = "#f8f8f2"
            self.fg_mid        = "#bd93f9"
            self.fg_mute       = "#6272a4"
            self.hairline      = "#44475a"
            self.input_bg      = "#44475a"
            self.input_fg      = "#f8f8f2"
            self.plot_bg       = "#1e1f29"
            self.plot_grid     = "#44475a"
            self.plot_text     = "#f8f8f2"
            self.group_title_bg = "#282a36"

        sc = SEMANTIC_COLORS[self.mode]
        for k, v in sc.items():
            setattr(self, k, v)

        stats = STATS_COLORS[self.mode]
        self.stat_max = stats['max']
        self.stat_min = stats['min']
        self.stat_avg = stats['avg']
        self.stat_std = stats['std']

        self.realtime_card_bg = REALTIME_CARD_BG[self.mode]

    def toggle(self) -> "Theme":
        idx = THEME_CYCLE.index(self.mode) if self.mode in THEME_CYCLE else 0
        self.mode = THEME_CYCLE[(idx + 1) % len(THEME_CYCLE)]
        self.is_dark = (self.mode in DARK_THEMES)
        self._build_palette()
        return self

    def next_mode(self) -> str:
        idx = THEME_CYCLE.index(self.mode) if self.mode in THEME_CYCLE else 0
        return THEME_CYCLE[(idx + 1) % len(THEME_CYCLE)]

    # ------------------------------------------------
    # 全局样式
    # ------------------------------------------------
    def app_qss(self) -> str:
        return f"""
            QMainWindow, QWidget {{
                background-color: {self.bg};
                color: {self.fg};
                font-family: {FONTS.FAMILY};
                font-size: {FONTS.SIZE_BODY};
            }}
            QLabel {{
                color: {self.fg_mid};
                font-family: {FONTS.FAMILY};
            }}
            QToolTip {{
                background-color: {self.fg};
                color: {self.bg};
                border: none;
                padding: 4px 8px;
                border-radius: {RADIUS.SM}px;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {self.hairline};
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """

    def group_box_qss(self) -> str:
        if self.is_dark:
            card_bg     = "rgba(255, 255, 255, 0.035)"
            card_border = "rgba(255, 255, 255, 0.06)"
        else:
            card_bg     = "rgba(0, 0, 0, 0.025)"
            card_border = "rgba(0, 0, 0, 0.05)"
        return f"""
            QGroupBox {{
                font-size: {FONTS.SIZE_CAPTION};
                font-weight: {FONTS.WEIGHT_BOLD};
                color: {self.fg};
                border: 1px solid {card_border};
                border-radius: 12px;
                margin-top: 0;
                padding: 22px {SPACING.MD}px {SPACING.MD}px {SPACING.MD}px;
                background-color: {card_bg};
            }}
            QGroupBox::title {{
                subcontrol-origin: padding;
                subcontrol-position: top left;
                left: 12px;
                top: 4px;
                padding: 0 4px;
                color: {self.fg_mid};
                background-color: transparent;
            }}
        """

    def input_qss(self) -> str:
        return f"""
            QLineEdit {{
                background-color: {self.input_bg};
                color: {self.input_fg};
                border: 1px solid {self.hairline};
                border-radius: {RADIUS.SM}px;
                padding: {SPACING.SM}px {SPACING.MD}px;
                font-size: {FONTS.SIZE_BODY};
            }}
            QLineEdit:focus {{ border: 1px solid {self.fg}; }}
            QLineEdit:disabled {{
                background-color: {self.bg_deep};
                color: {self.fg_mute};
            }}
        """

    def combo_qss(self) -> str:
        if self.is_dark:
            dropdown_bg     = "rgba(40, 40, 42, 0.94)"
            dropdown_border = "rgba(255, 255, 255, 0.10)"
        else:
            dropdown_bg     = "rgba(255, 255, 255, 0.94)"
            dropdown_border = "rgba(0, 0, 0, 0.08)"

        return f"""
            QComboBox {{
                background-color: {self.input_bg};
                color: {self.input_fg};
                border: 1px solid {self.hairline};
                border-radius: {RADIUS.SM}px;
                padding: {SPACING.SM}px {SPACING.MD}px;
                font-size: {FONTS.SIZE_BODY};
            }}
            QComboBox:focus {{ border: 1px solid {self.fg}; }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox::down-arrow {{ image: none; }}

            QComboBox QAbstractItemView {{
                background-color: {dropdown_bg};
                color: {self.fg};
                border: 1px solid {dropdown_border};
                border-radius: 10px;
                outline: none;
                padding: 0;
            }}
            QComboBox QAbstractItemView::item {{
                height: 28px;
                padding: 0 14px;
                border: none;
                border-radius: 0;
                color: {self.fg};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {self.neutral_hover};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {self.primary};
                color: #ffffff;
            }}
        """

    def button_qss(self, kind: str = 'neutral') -> str:
        kind = (kind or 'neutral').lower()
        if kind not in ('primary', 'danger', 'warning', 'success', 'neutral'):
            kind = 'neutral'

        if kind == 'neutral':
            return f"""
                QPushButton {{
                    background-color: {self.neutral_bg};
                    color: {self.neutral_fg};
                    border: none;
                    border-radius: {RADIUS.SM}px;
                    padding: {SPACING.MD}px {SPACING.LG}px;
                    font-size: {FONTS.SIZE_BODY};
                    font-weight: {FONTS.WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{ background-color: {self.neutral_hover}; }}
                QPushButton:pressed {{ background-color: {self.neutral_press}; }}
                QPushButton:disabled {{
                    background-color: {self.hairline};
                    color: {self.fg_mute};
                }}
            """

        color_map = {
            'primary': (self.primary, self.primary_hover),
            'danger':  (self.danger,  self.danger_hover),
            'warning': (self.warning, self.warning_hover),
            'success': (self.success, self.success_hover),
        }
        base, hover = color_map[kind]

        return f"""
            QPushButton {{
                background-color: {base};
                color: #ffffff;
                border: none;
                border-radius: {RADIUS.SM}px;
                padding: {SPACING.MD}px {SPACING.LG}px;
                font-size: {FONTS.SIZE_BODY};
                font-weight: {FONTS.WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {hover}; }}
            QPushButton:disabled {{
                background-color: {COLORS.MUTE_SOFT};
                color: {COLORS.CANVAS};
            }}
        """

    def checkbox_qss(self) -> str:
        return f"""
            QCheckBox {{
                font-size: {FONTS.SIZE_CAPTION};
                color: {self.fg_mid};
                spacing: {SPACING.SM}px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {self.hairline};
                border-radius: {RADIUS.XS}px;
                background-color: {self.input_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.fg};
                border-color: {self.fg};
            }}
        """

    def realtime_card_qss(self, bg=None) -> str:
        primary = self.primary
        if self.is_dark:
            bg_css     = _rgba_css(primary, 0.18)
            border_css = _rgba_css(primary, 0.32)
        else:
            bg_css     = _rgba_css(primary, 0.06)
            border_css = _rgba_css(primary, 0.16)

        return f"""
            QFrame {{
                background-color: {bg_css};
                border: 1px solid {border_css};
                border-radius: 12px;
            }}
            QFrame QLabel#rt_value {{
                color: {self.fg};
                background: transparent;
                border: none;
                font-family: {FONTS.FAMILY};
                font-size: 32px;
                font-weight: 600;
                letter-spacing: -0.5px;
            }}
            QFrame QLabel#rt_unit {{
                color: {self.fg_mute};
                background: transparent;
                border: none;
                font-family: {FONTS.FAMILY};
                font-size: 14px;
                font-weight: 500;
            }}
        """

    # ✅ 修复 #3：形参 text_color 不再被无条件覆盖
    def stat_card_qss(self, color, text_color=None) -> str:
        if text_color is None:
            text_color = self.fg

        if self.is_dark:
            bg_css     = _rgba_css(color, 0.20)
            border_css = _rgba_css(color, 0.34)
        else:
            bg_css     = _rgba_css(color, 0.10)
            border_css = _rgba_css(color, 0.22)

        return f"""
            QFrame {{
                background-color: {bg_css};
                border: 1px solid {border_css};
                border-radius: 12px;
            }}
            QFrame QLabel#st_title {{
                color: {color};
                background: transparent;
                border: none;
                font-family: {FONTS.FAMILY};
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.8px;
            }}
            QFrame QLabel#st_value {{
                color: {text_color};
                background: transparent;
                border: none;
                font-family: {FONTS.FAMILY};
                font-size: 18px;
                font-weight: 600;
                letter-spacing: -0.3px;
            }}
        """

    def status_qss(self, kind='normal') -> str:
        colors = {
            'normal':  self.fg_mute,
            'success': self.success,
            'error':   self.danger,
            'info':    self.primary,
        }
        return f"""
            color: {colors.get(kind, self.fg_mute)};
            font-size: {FONTS.SIZE_CAPTION};
            font-weight: {FONTS.WEIGHT_MEDIUM};
        """

    def status_badge_qss(self, kind='normal') -> str:
        if self.is_dark:
            neutral_bg = "rgba(255, 255, 255, 0.06)"
        else:
            neutral_bg = "rgba(0, 0, 0, 0.04)"

        color_map = {
            'normal':  (self.fg_mute,  neutral_bg),
            'success': (self.success,  _rgba_css(self.success, 0.14)),
            'error':   (self.danger,   _rgba_css(self.danger,  0.14)),
            'info':    (self.primary,  _rgba_css(self.primary, 0.14)),
        }
        fg, bg = color_map.get(kind, color_map['normal'])

        return f"""
            QLabel {{
                color: {fg};
                background-color: {bg};
                border-radius: 9px;
                padding: 3px 10px;
                font-size: {FONTS.SIZE_CAPTION};
                font-weight: {FONTS.WEIGHT_MEDIUM};
            }}
        """

    @staticmethod
    def _darken(hex_color, factor=0.85):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = max(0, int(r * factor))
        g = max(0, int(g * factor))
        b = max(0, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"


_default_theme = Theme('light')


def get_theme():
    return _default_theme


def set_theme(mode):
    global _default_theme
    _default_theme = Theme(mode)
    return _default_theme


def list_themes():
    return list(THEME_CYCLE)