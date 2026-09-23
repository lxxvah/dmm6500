#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing/config.py —— 本工程的授权配置
============================================
集成到新工程时，只需改这个文件。
"""

from pathlib import Path

# ============================================================
# ① 本工程身份
# ============================================================
APP_ID      = "dmm6500"                     # 内部标识，英文（与作者端一致）
APP_NAME    = "DMM6500 综合监控台"           # 显示名（窗口标题、对话框等）
APP_VERSION = "1.0"                         # 版本号（显示用）
KEY_PREFIX  = "DMM6500-"                    # 密钥前缀（与作者端一致）

# 存储目录名（Windows: %APPDATA%\<KEY>；不建议改）
APP_KEY = "DMM6500Monitor"


# ============================================================
# ② 作者信息与联系方式
# ============================================================
AUTHOR_NAME    = "得鹿梦鱼"
AUTHOR_EMAIL   = "792789598@qq.com"
AUTHOR_EXTRA   = "微信 / QQ：得鹿梦鱼"        # 可留空 ""
AUTHOR_TAGLINE = "「莫道桑榆晚，为霞尚满天」"  # 邮件签名用

# 联系方式行为：
#   "copy"   → 点击复制邮箱到剪贴板（推荐）
#   "mailto" → 打开系统默认邮件客户端
CONTACT_ACTION = "copy"

# 联系方式前的提示语（留空 "" 则不显示）
CONTACT_HINT = "遇到问题请联系"


# ============================================================
# ③ 试用
# ============================================================
TRIAL_DAYS = 1                              # 试用天数


# ============================================================
# ④ 授权卡片（3 个选项）
# ============================================================
# key 不可改（内部识别用），其它字段随便改。
# badge = None 表示不显示徽标；任意字符串则显示在卡片"价格下方右侧"。
PLANS = [
    {
        "key":      "trial",
        "title":    "1 天试用",
        "price":    "¥ 0",
        "subtitle": "立即体验全部功能",
        "badge":    None,
    },
    {
        "key":      "year",
        "title":    "1 年授权",
        "price":    "¥ 0",
        "subtitle": "有效期 365 天",
        "badge":    "⭐ 推荐",
    },
    {
        "key":      "lifetime",
        "title":    "终身购买",
        "price":    "¥ 0",
        "subtitle": "一次买断 · 永久使用",
        "badge":    None,
    },
]


# ============================================================
# ⑤ 按钮文案
# ============================================================
BTN_TRIAL     = "立即试用"      # 试用卡片选中时主按钮
BTN_ACTIVATE  = "激活"          # 授权卡片选中时主按钮
BTN_REQUEST   = "申请正式授权"   # 左下角按钮
BTN_QUIT      = "退出"
BTN_COPY      = "复制"
BTN_BROWSE    = "浏览"
BTN_SEND_MAIL = "用邮件发送"
BTN_COPY_REQ  = "复制申请内容"
BTN_BACK      = "返回"


# ============================================================
# ⑥ 对话框尺寸
# ============================================================
DIALOG_MIN_WIDTH = 620
DIALOG_MAX_WIDTH = 720

CARD_WIDTH  = 176
CARD_HEIGHT = 156

REQUEST_DIALOG_MIN_WIDTH = 560
REQUEST_DIALOG_MAX_WIDTH = 640


# ============================================================
# ⑦ 主要文案（对话框里的其他可改文案）
# ============================================================
SECTION_MACHINE = "机器码"        # 机器码区标题
SECTION_KEY     = "授权密钥"      # 密钥区标题

PLACEHOLDER_KEY = f"粘贴密钥（以 {KEY_PREFIX} 开头），或点击右侧选择 .lic 文件..."

MSG_COPY_OK_TITLE = "已复制"
MSG_COPY_OK_BODY  = "机器码已复制到剪贴板"

MSG_TRIAL_ALREADY_USED = "试用已使用"
MSG_TRIAL_FAILED_TITLE = "无法试用"


# ============================================================
# ⑧ 授权申请（客户端 → 作者）
# ============================================================
REQUEST_EMAIL_SUBJECT = f"[{APP_NAME} 授权申请] {{email}}"

REQUEST_EMAIL_BODY = f"""您好，{AUTHOR_NAME}：

我申请 {APP_NAME} 的正式授权。

客户邮箱：{{email}}
机器码：  {{machine_code}}

请查收，谢谢！
"""

REQUEST_COPY_TEXT = f"""【{APP_NAME} 授权申请】

客户邮箱：{{email}}
机器码：  {{machine_code}}

（请发送给作者获取授权密钥）
"""

REQUEST_HINT = (
    "填写您的邮箱，我们会尽快将授权密钥发送给您。\n"
    "如果邮件客户端打不开，可以复制申请内容，通过微信 / QQ 手动发送。"
)


# ============================================================
# ⑨ RSA 公钥
# ============================================================
# 优先读同目录下的 public_key.pem 文件；
# 找不到时用占位符，运行时会报"授权模块不可用"。
_PUBKEY_FILE = Path(__file__).resolve().parent / "public_key.pem"

if _PUBKEY_FILE.is_file():
    PUBLIC_KEY_PEM = _PUBKEY_FILE.read_bytes()
else:
    PUBLIC_KEY_PEM = (
        b"-----BEGIN PUBLIC KEY-----\n"
        b"PLACEHOLDER_PLEASE_PUT_PUBLIC_KEY_PEM_FILE_NEXT_TO_CONFIG\n"
        b"-----END PUBLIC KEY-----\n"
    )