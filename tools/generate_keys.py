#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/generate_keys.py —— 一次性生成 RSA 密钥对（带自检）
==============================================================
运行：
    python tools/generate_keys.py

生成：
    tools/private_key.pem   ⚠️ 私钥，绝不外传、绝不进 git
    tools/public_key.pem    公钥，把内容粘贴到 libs/license_client.py
"""

from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization


def validate_pem(path: Path, is_private: bool) -> bool:
    """读回文件，验证 PEM 是否有效。"""
    print()
    print("-" * 62)
    print(f"自检: {path.name}")
    print("-" * 62)

    if not path.is_file():
        print(f"❌ 文件不存在")
        return False

    data = path.read_bytes()
    print(f"文件大小: {len(data)} 字节")

    if len(data) < 100:
        print(f"❌ 文件太小，内容异常")
        return False

    text = data.decode("utf-8", errors="replace")
    first_line = text.splitlines()[0] if text.splitlines() else ""
    last_line = text.splitlines()[-1] if text.splitlines() else ""

    print(f"首行: {first_line!r}")
    print(f"末行: {last_line!r}")

    if not first_line.startswith("-----BEGIN"):
        print("❌ 缺少 BEGIN 头")
        return False
    if not last_line.startswith("-----END"):
        print("❌ 缺少 END 尾")
        return False

    try:
        if is_private:
            serialization.load_pem_private_key(data, password=None)
        else:
            serialization.load_pem_public_key(data)
        print("✅ PEM 校验通过")
        return True
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return False


def main():
    here = Path(__file__).resolve().parent
    priv_path = here / "private_key.pem"
    pub_path = here / "public_key.pem"

    if priv_path.exists():
        print(f"⚠️  {priv_path} 已存在。")
        print("   覆盖会作废所有已签发的授权！")
        ans = input("   继续？[y/N] ").strip().lower()
        if ans != "y":
            print("已取消")
            return

    # 清掉旧文件，避免残留导致困惑
    for p in (priv_path, pub_path):
        if p.exists():
            try:
                p.unlink()
            except Exception as e:
                print(f"⚠️ 无法删除 {p}: {e}")

    print("正在生成 RSA-2048 密钥对...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # 关键：用 write_bytes，避免编码 / BOM / 换行符问题
    priv_path.write_bytes(priv_pem)
    pub_path.write_bytes(pub_pem)

    # 立即自检
    priv_ok = validate_pem(priv_path, is_private=True)
    pub_ok = validate_pem(pub_path, is_private=False)

    print()
    if not (priv_ok and pub_ok):
        print("=" * 62)
        print("❌ 生成的文件未能通过自检！")
        print("   请把上面输出完整贴出来，方便排查。")
        print("=" * 62)
        return

    print("=" * 62)
    print("✅ 密钥对已生成且自检通过")
    print("=" * 62)
    print(f"私钥：{priv_path}  ⚠️ 务必保密，不要提交 git")
    print(f"公钥：{pub_path}")
    print()
    print("=" * 62)
    print("请把下面整段公钥内容，粘贴到 libs/license_config.py 的")
    print("PUBLIC_KEY_PEM 变量里（替换掉占位符）：")
    print("=" * 62)
    print()
    print(pub_pem.decode("utf-8"))
    print("=" * 62)
    print()


if __name__ == "__main__":
    main()