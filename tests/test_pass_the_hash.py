"""tests/test_pass_the_hash.py — pass-the-hash 漏洞验证测试"""
import os
import sys
import pytest
import tempfile
import sqlite3
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== P0-3: pass-the-hash 验证 ====================

def test_legacy_sha256_is_not_vulnerable_to_pass_the_hash():
    """
    验证当前代码不受 pass-the-hash 攻击影响。

    分析：
        elif len(pw_hash) == 64:
            match = pw_hash == hashlib.sha256(password.encode()).hexdigest()

        如果攻击者用哈希值作为密码：
        - pw_hash = "abc123..." (存储的哈希)
        - password = "abc123..." (攻击者输入)
        - hashlib.sha256("abc123...".encode()).hexdigest() = "xyz789..." (新的哈希)
        - "abc123..." != "xyz789..." → match = False → 登录失败

    结论：当前代码已经安全，因为密码会被再次哈希，哈希值不等于原密码。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        conn.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                status INTEGER DEFAULT 1
            );
        """)

        # 创建使用旧版 sha256 的用户
        original_password = "mysecretpassword123"
        hash_value = hashlib.sha256(original_password.encode()).hexdigest()
        assert len(hash_value) == 64, "sha256 哈希应该是 64 位"

        conn.execute(
            "INSERT INTO users (id, username, password_hash, status) VALUES (?, ?, ?, ?)",
            (1, "testuser", hash_value, 1)
        )
        conn.commit()
        conn.close()

        import lib.db as db_module
        original_db_path = db_module.DB_PATH
        db_module.DB_PATH = db_path
        db_module._local.conn = None

        try:
            from models import authenticate_user

            # 用原始密码登录应该成功
            result = authenticate_user("testuser", original_password)
            assert result is not None, "用原始密码登录应该成功"
            assert result['id'] == 1

            # 用哈希值当密码登录应该失败（pass-the-hash 攻击被阻止）
            result = authenticate_user("testuser", hash_value)
            assert result is None, "用哈希值作为密码登录应该失败"

        finally:
            db_module.DB_PATH = original_db_path
            db_module._local.conn = None
