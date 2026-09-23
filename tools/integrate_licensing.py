#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/integrate_licensing.py —— 授权模块自动化集成工具（作者端）
======================================================================
把 licensing/ 模块一键部署到目标工程：
  · 拷贝 licensing/*.py（排除 __pycache__）
  · 拷贝 public_key.pem
  · 自动改写目标工程的 licensing/config.py
  · 可选：自动在 main.py 里插入授权校验代码

用法（交互式）：
    python tools/integrate_licensing.py

用法（命令行）：
    python tools/integrate_licensing.py ^
        --target D:\\Python\\my_new_tool ^
        --app-id my_new_tool ^
        --app-name "我的新工具" ^
        --key-prefix MYTOOL- ^
        --app-key MyNewToolMonitor ^
        --author-email 792789598@qq.com ^
        --author-extra "微信 / QQ：得鹿梦鱼" ^
        --trial-days 1

可选参数：
    --no-main      不修改 main.py（只拷贝 + 改 config）
    --force        目标已存在 licensing/ 时直接覆盖（默认询问）
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


# ============================================================
# 路径
# ============================================================
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent                  # dmm6500/
SOURCE_LICENSING = PROJECT_ROOT / "licensing"
SOURCE_PUBKEY = HERE / "public_key.pem"

# 要拷贝的文件
COPY_FILES = [
    "__init__.py",
    "config.py",
    "client.py",
    "dialog.py",
    "request_dialog.py",
    "fingerprint.py",
    "license_gate.py",
    "icon.py",
    "debug_tool.py",
]


# ============================================================
# 工具函数
# ============================================================
def cprint(msg: str, kind: str = "info"):
    prefix = {
        "info":    "  ",
        "ok":      "✅ ",
        "warn":    "⚠️  ",
        "err":     "❌ ",
        "step":    "\n▶ ",
        "sub":     "   · ",
    }.get(kind, "  ")
    print(prefix + msg)


def validate_app_id(s: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", s))


def validate_key_prefix(s: str) -> bool:
    return s.endswith("-") and len(s) >= 3


def prompt(question: str, default: str = "", required: bool = False) -> str:
    while True:
        hint = f" [{default}]" if default else ""
        raw = input(f"{question}{hint}: ").strip()
        val = raw or default
        if not val and required:
            cprint("此项不能为空，请重新输入", "warn")
            continue
        return val


def prompt_yesno(question: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    raw = input(f"{question} {hint}: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


# ============================================================
# 步骤 1：确认源文件
# ============================================================
def check_source() -> bool:
    cprint("检查源文件", "step")

    if not SOURCE_LICENSING.is_dir():
        cprint(f"找不到源模块目录：{SOURCE_LICENSING}", "err")
        return False

    missing = []
    for f in COPY_FILES:
        if not (SOURCE_LICENSING / f).is_file():
            missing.append(f)

    if missing:
        cprint(f"licensing 目录缺少文件：{', '.join(missing)}", "err")
        return False

    if not SOURCE_PUBKEY.is_file():
        cprint(f"找不到公钥：{SOURCE_PUBKEY}", "err")
        cprint("请先运行：python tools/generate_keys.py", "sub")
        return False

    cprint(f"源目录：{SOURCE_LICENSING}", "sub")
    cprint(f"公钥：  {SOURCE_PUBKEY}", "sub")
    cprint("源文件完整", "ok")
    return True


# ============================================================
# 步骤 2：采集目标信息
# ============================================================
def collect_args(args) -> dict:
    cprint("收集集成参数", "step")

    # 目标目录
    target = args.target
    if not target:
        target = prompt("目标工程根目录（如 D:\\Python\\my_new_tool）",
                        required=True)
    target_path = Path(target).expanduser().resolve()
    if not target_path.is_dir():
        cprint(f"目标目录不存在：{target_path}", "err")
        sys.exit(1)
    cprint(f"目标：{target_path}", "sub")

    # APP_ID
    app_id = args.app_id or prompt(
        "APP_ID（英文标识，与作者端 apps_config.json 一致）",
        default=target_path.name,
        required=True,
    )
    if not validate_app_id(app_id):
        cprint(f"APP_ID 格式不正确（须字母开头 + 字母数字下划线）：{app_id}", "err")
        sys.exit(1)

    # APP_NAME
    app_name = args.app_name or prompt("APP_NAME（中文显示名）",
                                        default=app_id)

    # KEY_PREFIX
    key_prefix = args.key_prefix or prompt(
        "KEY_PREFIX（密钥前缀，末尾带 -）",
        default=app_id.upper().replace("_", "")[:12] + "-",
    )
    if not validate_key_prefix(key_prefix):
        cprint(f"KEY_PREFIX 须以 - 结尾，例如 MYTOOL-：{key_prefix}", "err")
        sys.exit(1)

    # APP_KEY
    app_key = args.app_key or prompt(
        "APP_KEY（Windows 存储目录名）",
        default=app_id.replace("_", "").title() + "Monitor",
    )

    # 作者信息
    author_email = args.author_email or prompt(
        "作者邮箱", default="792789598@qq.com"
    )
    author_extra = args.author_extra or prompt(
        "附加联系方式（可留空）", default="微信 / QQ：得鹿梦鱼"
    )
    trial_days = args.trial_days or prompt(
        "试用天数", default="1"
    )

    return {
        "target":       target_path,
        "app_id":       app_id,
        "app_name":     app_name,
        "key_prefix":   key_prefix,
        "app_key":      app_key,
        "author_email": author_email,
        "author_extra": author_extra,
        "trial_days":   trial_days,
    }


# ============================================================
# 步骤 3：拷贝文件
# ============================================================
def copy_files(cfg: dict, force: bool) -> bool:
    cprint("拷贝模块文件", "step")

    target_lic = cfg["target"] / "licensing"

    if target_lic.exists():
        if not force:
            cprint(f"目标已存在：{target_lic}", "warn")
            if not prompt_yesno("是否覆盖？", default=False):
                cprint("已取消", "warn")
                return False
        cprint(f"删除旧的：{target_lic}", "sub")
        shutil.rmtree(target_lic)

    target_lic.mkdir(parents=True)
    cprint(f"新建目录：{target_lic}", "sub")

    # 拷贝 .py 文件
    count = 0
    for f in COPY_FILES:
        src = SOURCE_LICENSING / f
        if not src.is_file():
            cprint(f"跳过（不存在）：{f}", "warn")
            continue
        dst = target_lic / f
        shutil.copy2(src, dst)
        cprint(f"{f}", "sub")
        count += 1

    # 拷贝 public_key.pem
    dst_pubkey = target_lic / "public_key.pem"
    shutil.copy2(SOURCE_PUBKEY, dst_pubkey)
    cprint("public_key.pem", "sub")
    count += 1

    cprint(f"共拷贝 {count} 个文件", "ok")
    return True


# ============================================================
# 步骤 4：改写目标 config.py
# ============================================================
def _replace_var(text: str, var: str, new_value: str) -> tuple[str, bool]:
    """
    把 `VAR = ...` 替换为 `VAR = <new_value>`。

    Returns:
        (新文本, 是否找到并替换)
    """
    pattern = re.compile(
        rf"^({re.escape(var)}\s*=\s*).*$",
        re.MULTILINE,
    )
    if not pattern.search(text):
        return text, False

    # 用 lambda 而不是 rf'\1{new_value}'，避免 new_value 里的数字
    # 被误当作 \1 后面的组引用（例如 TRIAL_DAYS 的值 "1" → \11）
    new_text = pattern.sub(
        lambda m: m.group(1) + new_value,
        text,
        count=1,
    )
    return new_text, True


def rewrite_config(cfg: dict) -> bool:
    cprint("改写 config.py", "step")

    cfg_path = cfg["target"] / "licensing" / "config.py"
    if not cfg_path.is_file():
        cprint(f"未找到：{cfg_path}", "err")
        return False

    text = cfg_path.read_text(encoding="utf-8")

    replacements = {
        "APP_ID":       f'"{cfg["app_id"]}"',
        "APP_NAME":     f'"{cfg["app_name"]}"',
        "KEY_PREFIX":   f'"{cfg["key_prefix"]}"',
        "APP_KEY":      f'"{cfg["app_key"]}"',
        "AUTHOR_EMAIL": f'"{cfg["author_email"]}"',
        "AUTHOR_EXTRA": f'"{cfg["author_extra"]}"',
        "TRIAL_DAYS":   cfg["trial_days"],
    }

    for var, val in replacements.items():
        text, ok = _replace_var(text, var, val)
        if ok:
            cprint(f"{var} = {val}", "sub")
        else:
            cprint(f"{var} 未找到（跳过）", "warn")

    cfg_path.write_text(text, encoding="utf-8")
    cprint("config.py 已更新", "ok")
    return True


# ============================================================
# 步骤 5：可选修改 main.py
# ============================================================
MAIN_MARKER_IMPORT = "# ===== licensing ====="
MAIN_MARKER_CHECK = "# ===== licensing_check ====="


def patch_main(cfg: dict) -> bool:
    cprint("尝试改写 main.py", "step")

    main_path = cfg["target"] / "main.py"
    if not main_path.is_file():
        cprint("目标没有 main.py，跳过", "warn")
        return False

    text = main_path.read_text(encoding="utf-8")

    if MAIN_MARKER_CHECK in text:
        cprint("main.py 已包含授权校验，跳过", "warn")
        return True

    m = re.search(
        r"^(\s*)(\w+)\s*=\s*QApplication\s*\(\s*sys\.argv\s*\)\s*$",
        text,
        re.MULTILINE,
    )
    if not m:
        cprint("没找到 `app = QApplication(sys.argv)`，无法自动插入", "warn")
        cprint("请手动在 QApplication 之后添加：", "info")
        print()
        print("    from licensing import ensure_licensed")
        print("    if not ensure_licensed():")
        print("        sys.exit(0)")
        print()
        return False

    indent = m.group(1)
    insert_pos = m.end()

    snippet = (
        f"\n\n{indent}{MAIN_MARKER_IMPORT}\n"
        f"{indent}from licensing import ensure_licensed\n"
        f"{indent}if not ensure_licensed():\n"
        f"{indent}    sys.exit(0)\n"
        f"{indent}{MAIN_MARKER_CHECK}"
    )

    new_text = text[:insert_pos] + snippet + text[insert_pos:]

    # 备份
    backup = main_path.with_suffix(".py.bak")
    backup.write_text(text, encoding="utf-8")
    cprint(f"备份原文件：{backup.name}", "sub")

    main_path.write_text(new_text, encoding="utf-8")
    cprint("main.py 已插入授权校验", "ok")
    return True


# ============================================================
# 步骤 6：验证
# ============================================================
def verify(cfg: dict) -> bool:
    cprint("验证集成结果", "step")

    target_lic = cfg["target"] / "licensing"

    required = ["__init__.py", "config.py", "client.py",
                "dialog.py", "request_dialog.py", "fingerprint.py",
                "license_gate.py", "icon.py", "public_key.pem"]
    missing = [f for f in required if not (target_lic / f).is_file()]
    if missing:
        cprint(f"缺少文件：{missing}", "err")
        return False
    cprint(f"文件齐全（{len(required)} 个）", "ok")

    cfg_text = (target_lic / "config.py").read_text(encoding="utf-8")
    ok = True
    for var, expected in [
        ("APP_ID", cfg["app_id"]),
        ("APP_NAME", cfg["app_name"]),
        ("KEY_PREFIX", cfg["key_prefix"]),
        ("APP_KEY", cfg["app_key"]),
    ]:
        m = re.search(rf'^{var}\s*=\s*"([^"]*)"', cfg_text, re.MULTILINE)
        got = m.group(1) if m else ""
        if got == expected:
            cprint(f"{var} = {got}", "sub")
        else:
            cprint(f"{var} 不符：期望 {expected}，实际 {got}", "err")
            ok = False

    if not ok:
        return False

    cprint("配置正确", "ok")
    return True


# ============================================================
# 步骤 7：打印后续提示
# ============================================================
def print_next_steps(cfg: dict, main_patched: bool):
    target = cfg["target"]

    print()
    print("=" * 66)
    print("  🎉 集成完成")
    print("=" * 66)
    print()

    if not main_patched:
        print("【还需手动做 1 件事】")
        print()
        print("  打开 main.py，在 QApplication 创建之后加上：")
        print()
        print("      from licensing import ensure_licensed")
        print("      if not ensure_licensed():")
        print("          sys.exit(0)")
        print()
    else:
        print("【main.py 已自动插入授权校验】")
        print()

    print("【作者端需要做的事】")
    print()
    print("  1. 打开 tools/apps_config.json")
    print("  2. 加入一条应用记录：")
    print()
    print("     {")
    print(f'         "id": "{cfg["app_id"]}",')
    print(f'         "name": "{cfg["app_name"]}",')
    print(f'         "key_prefix": "{cfg["key_prefix"]}",')
    print(f'         "contact_email": "{cfg["author_email"]}",')
    print(f'         "contact_extra": "{cfg["author_extra"]}"')
    print("     }")
    print()
    print("  3. 打开 python tools/keygen_gui.py")
    print(f"  4. 点「刷新」→ 下拉里就能看到「{cfg['app_name']}」")
    print()

    print("【验证步骤】")
    print()
    print(f"  cd {target}")
    print(f'  python -c "from licensing.fingerprint import get_machine_code; print(get_machine_code())"')
    print("  python main.py")
    print()
    print("  首次启动应弹出授权对话框。")
    print()
    print("=" * 66)
    print()


# ============================================================
# 入口
# ============================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="licensing 模块自动化集成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--target", type=str, default=None,
                        help="目标工程根目录")
    parser.add_argument("--app-id", type=str, default=None,
                        help="应用 ID（英文）")
    parser.add_argument("--app-name", type=str, default=None,
                        help="应用显示名")
    parser.add_argument("--key-prefix", type=str, default=None,
                        help="密钥前缀，末尾带 -")
    parser.add_argument("--app-key", type=str, default=None,
                        help="存储目录名")
    parser.add_argument("--author-email", type=str, default=None,
                        help="作者邮箱")
    parser.add_argument("--author-extra", type=str, default=None,
                        help="附加联系方式")
    parser.add_argument("--trial-days", type=str, default=None,
                        help="试用天数")
    parser.add_argument("--no-main", action="store_true",
                        help="不修改 main.py")
    parser.add_argument("--force", action="store_true",
                        help="目标存在时直接覆盖")
    return parser.parse_args()


def main():
    print()
    print("=" * 66)
    print("  licensing 模块自动化集成工具")
    print("=" * 66)

    args = parse_args()

    # 步骤 1
    if not check_source():
        sys.exit(1)

    # 步骤 2
    cfg = collect_args(args)

    # 步骤 3
    if not copy_files(cfg, force=args.force):
        sys.exit(1)

    # 步骤 4
    if not rewrite_config(cfg):
        sys.exit(1)

    # 步骤 5（可选）
    main_patched = False
    if not args.no_main:
        main_patched = patch_main(cfg)

    # 步骤 6
    if not verify(cfg):
        cprint("验证失败，请检查上面的输出", "err")
        sys.exit(1)

    # 步骤 7
    print_next_steps(cfg, main_patched)


if __name__ == "__main__":
    main()