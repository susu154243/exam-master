"""tests/test_password_reset.py — 密码重置流程测试"""
import os
import sys
import pytest
import tempfile
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== P0-2: 密码重置 token 提前消费测试 ====================

def test_verify_reset_token_exists_without_consuming():
    """
    RED: 应该存在一个只验证不消费 token 的函数。

    当前问题：
        reset_password_page() 在 GET 和 POST 时都调用 verify_and_consume_reset_token()
        GET 时 token 被消费（删除），POST 时 token 已不存在 → 密码永远无法重置

    修复方案：
        1. 新增 verify_reset_token() 函数（只验证不消费）
        2. GET 时用 verify_reset_token() 验证 token 有效性
        3. POST 时才用 verify_and_consume_reset_token() 消费 token
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
            CREATE TABLE password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.execute("INSERT INTO users (id, username, password_hash, status) VALUES (?, ?, ?, ?)",
                     (1, "testuser", "hash", 1))

        # 创建一个有效的 token
        import secrets
        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
            (1, token, expires)
        )
        conn.commit()
        conn.close()

        import lib.db as db_module
        original_db_path = db_module.DB_PATH
        db_module.DB_PATH = db_path

        try:
            from models import verify_reset_token

            # 第一次验证：应该成功，且不消费 token
            result1 = verify_reset_token(token)
            assert result1 == 1, "verify_reset_token 应该返回 user_id"

            # 第二次验证：token 应该仍然有效（未被消费）
            result2 = verify_reset_token(token)
            assert result2 == 1, "verify_reset_token 不应消费 token，第二次调用仍应返回 user_id"

        finally:
            db_module.DB_PATH = original_db_path


def test_reset_password_page_uses_verify_not_consume_on_get():
    """
    RED: app.py 的 reset_password_page 在 GET 请求时不应消费 token。

    当前代码：
        user_id = verify_and_consume_reset_token(token)  # 第 362 行，GET/POST 都执行

    修复后：
        if request.method == 'GET':
            user_id = verify_reset_token(token)  # 只验证
        elif request.method == 'POST':
            user_id = verify_and_consume_reset_token(token)  # 验证并消费
    """
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找 reset_password_page 函数
    import re
    pattern = r"def reset_password_page.*?(?=\n@app\.route|\ndef |\Z)"
    match = re.search(pattern, content, re.DOTALL)
    assert match is not None, "reset_password_page 函数应该存在"

    func_body = match.group(0)

    # 检查函数中是否区分了 GET/POST 的 token 验证方式
    # 修复后应该有 verify_reset_token 的调用（用于 GET）
    assert 'verify_reset_token' in func_body, \
        "reset_password_page 应该使用 verify_reset_token（只验证不消费）处理 GET 请求"
