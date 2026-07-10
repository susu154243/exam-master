"""tests/test_search_licenses.py — 授权搜索分页测试"""
import os
import sys
import pytest
import tempfile
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== P1-7: search_licenses 分页过滤测试 ====================

def test_search_licenses_status_filter_in_sql():
    """
    RED: status 过滤应在 SQL 层完成，保证分页准确。

    当前问题：
        SQL 查询返回 20 条记录后，Python 循环中 continue 跳过不符合 status 的记录。
        导致：
        1. 返回条数可能少于 per_page（如 20 条中只有 10 条 valid）
        2. total 计数是未过滤的总数，分页计算错误

    修复方案：
        将 status 过滤条件移入 SQL WHERE 子句，使用 SQLite 日期函数计算。
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
            CREATE TABLE subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE,
                status INTEGER DEFAULT 1
            );
            CREATE TABLE user_licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER,
                expires_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)

        # 创建测试数据：20 个用户、1 个科目、40 条授权（20 valid + 20 expired）
        for i in range(1, 21):
            conn.execute(
                "INSERT INTO users (id, username, password_hash, status) VALUES (?, ?, ?, ?)",
                (i, f"user{i}", "hash", 1)
            )
        conn.execute(
            "INSERT INTO subjects (id, name, code, status) VALUES (?, ?, ?, ?)",
            (1, "测试科目", "TEST", 1)
        )

        now = datetime.now()
        # 20 条 valid（30 天后过期）
        for i in range(1, 21):
            expires = (now + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                "INSERT INTO user_licenses (user_id, subject_id, expires_at) VALUES (?, ?, ?)",
                (i, 1, expires)
            )
        # 20 条 expired（30 天前过期）
        for i in range(1, 21):
            user_id = i  # 复用 user_id，但实际会有主键冲突，改用新的
            # 为避免冲突，我们创建新的用户
            pass

        # 重新设计：创建 40 个用户，前 20 个 valid，后 20 个 expired
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM user_licenses")

        for i in range(1, 41):
            conn.execute(
                "INSERT INTO users (id, username, password_hash, status) VALUES (?, ?, ?, ?)",
                (i, f"user{i}", "hash", 1)
            )
            if i <= 20:
                # valid: 60 天后过期
                expires = (now + timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                # expired: 30 天前过期
                expires = (now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                "INSERT INTO user_licenses (user_id, subject_id, expires_at) VALUES (?, ?, ?)",
                (i, 1, expires)
            )

        conn.commit()
        conn.close()

        import lib.db as db_module
        original_db_path = db_module.DB_PATH
        db_module.DB_PATH = db_path
        db_module._local.conn = None

        try:
            from models import search_licenses

            # 筛选 valid 状态，每页 10 条
            licenses, total = search_licenses(status='valid', page=1, per_page=10)

            # 修复后：应该返回 10 条 valid 授权
            assert len(licenses) == 10, f"应该返回 10 条，实际返回 {len(licenses)} 条"
            assert total == 20, f"total 应该是 20（valid 总数），实际是 {total}"

            # 所有返回的授权都应该是 valid（未过期且 > 30 天）
            for lic in licenses:
                assert not lic['is_expired'], f"授权 {lic['id']} 应该是 valid"
                assert lic['days_left'] > 30, f"授权 {lic['id']} 应该 > 30 天"

            # 筛选 expired 状态
            licenses, total = search_licenses(status='expired', page=1, per_page=10)
            assert len(licenses) == 10, f"应该返回 10 条 expired"
            assert total == 20, f"total 应该是 20（expired 总数）"

            # 第二页
            licenses, total = search_licenses(status='valid', page=2, per_page=10)
            assert len(licenses) == 10, "第二页应该还有 10 条"

        finally:
            db_module.DB_PATH = original_db_path
            db_module._local.conn = None


def test_search_licenses_expiring_soon_filter():
    """
    RED: expiring_soon 状态应该筛选 0 < days_left <= 30 的授权。
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
            CREATE TABLE subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE,
                status INTEGER DEFAULT 1
            );
            CREATE TABLE user_licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER,
                expires_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)

        now = datetime.now()
        # 创建 3 个用户，分别对应 valid / expiring_soon / expired
        for i, days in [(1, 60), (2, 15), (3, -10)]:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, status) VALUES (?, ?, ?, ?)",
                (i, f"user{i}", "hash", 1)
            )
            expires = (now + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                "INSERT INTO user_licenses (user_id, subject_id, expires_at) VALUES (?, ?, ?)",
                (i, 1, expires)
            )
        conn.execute(
            "INSERT INTO subjects (id, name, code, status) VALUES (?, ?, ?, ?)",
            (1, "测试科目", "TEST", 1)
        )
        conn.commit()
        conn.close()

        import lib.db as db_module
        original_db_path = db_module.DB_PATH
        db_module.DB_PATH = db_path
        db_module._local.conn = None

        try:
            from models import search_licenses

            # expiring_soon 应该只返回 user2（15 天后过期）
            licenses, total = search_licenses(status='expiring_soon', page=1, per_page=10)
            assert len(licenses) == 1, f"应该返回 1 条 expiring_soon，实际 {len(licenses)}"
            assert total == 1
            assert licenses[0]['username'] == 'user2'
            assert 0 < licenses[0]['days_left'] <= 30

        finally:
            db_module.DB_PATH = original_db_path
            db_module._local.conn = None
