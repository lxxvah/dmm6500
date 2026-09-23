#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
licensing/client.py —— 授权校验核心
=========================================
· RSA 签名校验
· app 字段绑定（只认本工程）
· 机器码绑定
· 有效期检查
· 1 天试用（多位置冗余 + 时间回退检测）
"""

from __future__ import annotations

import base64
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

try:
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import hashes, serialization
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

from .config import (
    APP_ID, KEY_PREFIX, TRIAL_DAYS, PUBLIC_KEY_PEM,
)
from .fingerprint import get_machine_code


LICENSE_FILENAME = "license.lic"
TRIAL_FILENAME = "trial.dat"


# ============================================================
# 状态常量
# ============================================================
class LicenseResult:
    OK             = "ok"
    NOT_FOUND      = "not_found"
    INVALID_FORMAT = "invalid_format"
    BAD_SIGNATURE  = "bad_signature"
    WRONG_APP      = "wrong_app"
    WRONG_MACHINE  = "wrong_machine"
    EXPIRED        = "expired"
    TIME_TAMPERED  = "time_tampered"
    NO_CRYPTO      = "no_crypto"


class TrialStatus:
    NOT_STARTED = "not_started"
    ACTIVE      = "active"
    EXPIRED     = "expired"
    TAMPERED    = "tampered"


# ============================================================
# 存储路径
# ============================================================
def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(sys.argv[0]).resolve().parent


def _candidate_license_paths() -> list:
    home = Path.home()
    paths: list = []
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
        paths.append(appdata / APP_ID / LICENSE_FILENAME)
    else:
        paths.append(home / f".{APP_ID.lower()}" / LICENSE_FILENAME)
    paths.append(_app_dir() / LICENSE_FILENAME)
    return paths


def _candidate_trial_paths() -> list:
    home = Path.home()
    paths: list = []
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
        localappdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        paths.append(appdata / APP_ID / TRIAL_FILENAME)
        paths.append(localappdata / APP_ID / TRIAL_FILENAME)
    else:
        paths.append(home / f".{APP_ID.lower()}" / TRIAL_FILENAME)
        paths.append(Path("/tmp") / f".{APP_ID.lower()}_{TRIAL_FILENAME}")
    return paths


def _reg_key():
    if sys.platform != "win32":
        return None
    try:
        import winreg
        return winreg
    except ImportError:
        return None


# ============================================================
# 签名校验
# ============================================================
def _load_public_key():
    if not HAS_CRYPTO:
        return None
    try:
        return serialization.load_pem_public_key(PUBLIC_KEY_PEM)
    except Exception:
        return None


def _verify_signature(payload: dict, signature_b64: str) -> bool:
    pub = _load_public_key()
    if pub is None:
        return False
    try:
        sig = base64.b64decode(signature_b64)
        data = json.dumps(payload, ensure_ascii=False,
                          sort_keys=True).encode("utf-8")
        pub.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


# ============================================================
# License：查找 / 校验 / 安装
# ============================================================
def find_license_file() -> Optional[Path]:
    for p in _candidate_license_paths():
        if p.is_file():
            return p
    return None


def _validate_license_payload(lic: dict) -> Tuple[str, dict]:
    payload = lic.get("payload")
    signature = lic.get("signature")

    if not isinstance(payload, dict) or not isinstance(signature, str):
        return LicenseResult.INVALID_FORMAT, {"reason": "文件结构异常"}

    if not _verify_signature(payload, signature):
        return LicenseResult.BAD_SIGNATURE, {"reason": "签名无效或已被篡改"}

    # ✅ app 绑定校验：只认本工程的密钥
    lic_app = payload.get("app", "")
    if lic_app != APP_ID:
        return LicenseResult.WRONG_APP, {
            "reason": f"密钥不适用于本软件（授权给 {lic_app or '未知'}）",
            "lic_app": lic_app,
            "expected_app": APP_ID,
        }

    my_code = get_machine_code()
    if payload.get("machine_code") != my_code:
        return LicenseResult.WRONG_MACHINE, {
            "reason": "授权文件不适用于本机",
            "my_machine_code": my_code,
            "lic_machine_code": payload.get("machine_code"),
        }

    # 时间回退检测
    issued_at = payload.get("issued_at")
    if issued_at:
        try:
            issued_dt = datetime.strptime(issued_at, "%Y-%m-%d %H:%M:%S")
            today = datetime.now().replace(hour=0, minute=0, second=0,
                                           microsecond=0)
            if today < issued_dt.replace(hour=0, minute=0, second=0,
                                         microsecond=0):
                return LicenseResult.TIME_TAMPERED, {
                    "reason": "检测到系统时间早于授权签发日，可能被回退"
                }
        except Exception:
            pass

    # 有效期
    expire = payload.get("expire")
    if expire and str(expire).lower() not in ("never", "permanent", "永久"):
        try:
            exp_dt = datetime.strptime(str(expire), "%Y-%m-%d")
            if datetime.now() > exp_dt.replace(hour=23, minute=59, second=59):
                return LicenseResult.EXPIRED, {
                    "reason": f"授权已于 {expire} 过期",
                    "expire": expire,
                }
        except Exception:
            return LicenseResult.INVALID_FORMAT, {
                "reason": f"有效期格式错误: {expire}"
            }

    return LicenseResult.OK, payload


def check_license() -> Tuple[str, dict]:
    if not HAS_CRYPTO:
        return LicenseResult.NO_CRYPTO, {
            "reason": "缺少 cryptography 库，请运行 pip install cryptography"
        }

    path = find_license_file()
    if path is None:
        return LicenseResult.NOT_FOUND, {"reason": "未找到授权文件"}

    try:
        with open(path, "r", encoding="utf-8") as f:
            lic = json.load(f)
    except Exception as e:
        return LicenseResult.INVALID_FORMAT, {"reason": f"读取失败: {e}"}

    return _validate_license_payload(lic)


def _write_license_file(lic: dict, path: Path) -> Tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(lic, f, ensure_ascii=False, indent=2)
        return True, str(path)
    except Exception as e:
        return False, f"写入失败: {e}"


def install_license(src_path: str) -> Tuple[bool, str]:
    src = Path(src_path)
    if not src.is_file():
        return False, "文件不存在"
    try:
        with open(src, "r", encoding="utf-8") as f:
            lic = json.load(f)
    except Exception as e:
        return False, f"文件格式错误: {e}"

    st, info = _validate_license_payload(lic)
    if st != LicenseResult.OK:
        return False, info.get("reason", "授权无效")

    dst = _candidate_license_paths()[0]
    return _write_license_file(lic, dst)


def install_license_string(s: str) -> Tuple[bool, str]:
    """从粘贴的字符串安装授权。前缀按 config.KEY_PREFIX。"""
    raw = "".join((s or "").split())
    if raw.startswith(KEY_PREFIX):
        raw = raw[len(KEY_PREFIX):]
    if not raw:
        return False, "密钥为空"

    try:
        decoded = base64.b64decode(raw)
        lic = json.loads(decoded)
    except Exception as e:
        return False, f"密钥格式错误: {e}"

    st, info = _validate_license_payload(lic)
    if st != LicenseResult.OK:
        return False, info.get("reason", "授权无效")

    dst = _candidate_license_paths()[0]
    return _write_license_file(lic, dst)


# ============================================================
# 试用管理
# ============================================================
def _read_trial_first_ts() -> Optional[float]:
    candidates: list = []

    for p in _candidate_trial_paths():
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                ts = float(data.get("first_ts", 0))
                last = float(data.get("last_ts", 0))
                if ts > 0:
                    candidates.append(ts)
                if last > 0 and last > ts:
                    candidates.append(last)
        except Exception:
            pass

    reg = _reg_key()
    if reg is not None:
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER,
                             rf"Software\{APP_ID}\Trial") as k:
                ts, _ = reg.QueryValueEx(k, "first_ts")
                if float(ts) > 0:
                    candidates.append(float(ts))
        except Exception:
            pass

    return min(candidates) if candidates else None


def _write_trial_record(first_ts: float) -> None:
    payload = json.dumps({
        "first_ts": first_ts,
        "last_ts": first_ts,
        "app": APP_ID,
    })

    for p in _candidate_trial_paths():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(payload, encoding="utf-8")
        except Exception:
            pass

    reg = _reg_key()
    if reg is not None:
        try:
            with reg.CreateKey(reg.HKEY_CURRENT_USER,
                               rf"Software\{APP_ID}\Trial") as k:
                reg.SetValueEx(k, "first_ts", 0, reg.REG_SZ, str(first_ts))
        except Exception:
            pass


def _touch_trial_last_ts(ts: float) -> None:
    for p in _candidate_trial_paths():
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                prev = float(data.get("last_ts", 0))
                if ts > prev:
                    data["last_ts"] = ts
                    p.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass


def check_trial() -> Tuple[str, int]:
    first = _read_trial_first_ts()
    if first is None:
        return TrialStatus.NOT_STARTED, TRIAL_DAYS

    now = datetime.now().timestamp()

    for p in _candidate_trial_paths():
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                last = float(data.get("last_ts", 0))
                if last > 0 and now < last - 3600:
                    return TrialStatus.TAMPERED, 0
        except Exception:
            pass

    _touch_trial_last_ts(now)

    elapsed_days = (now - first) / 86400.0
    remaining = TRIAL_DAYS - elapsed_days

    if remaining <= 0:
        return TrialStatus.EXPIRED, 0
    return TrialStatus.ACTIVE, max(1, math.ceil(remaining))


def start_trial() -> Tuple[bool, str]:
    first = _read_trial_first_ts()
    if first is not None:
        return False, "试用已使用过，无法再次开启"

    ts = datetime.now().timestamp()
    _write_trial_record(ts)
    return True, "试用已开启"


# ============================================================
# 综合入口
# ============================================================
def check_access() -> Tuple[str, dict]:
    """统一判断：有正式授权 or 试用有效 → OK。"""
    st, info = check_license()
    if st == LicenseResult.OK:
        return LicenseResult.OK, {**info, "type": "license"}

    trial_st, days = check_trial()
    if trial_st == TrialStatus.ACTIVE:
        return LicenseResult.OK, {
            "type": "trial",
            "days_remaining": days,
        }

    info = dict(info) if isinstance(info, dict) else {}
    info["trial_status"] = trial_st
    info["trial_days"] = days
    return st, info


def machine_code() -> str:
    return get_machine_code()