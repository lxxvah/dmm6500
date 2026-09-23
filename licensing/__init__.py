#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing —— 通用授权模块（客户端）
=========================================
对外只暴露一个函数：ensure_licensed()
"""

from .config import APP_ID, APP_NAME
from .license_gate import ensure_licensed

__all__ = ["ensure_licensed", "APP_ID", "APP_NAME"]