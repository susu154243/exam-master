"""tests/test_models.py — models.py 测试"""
import os
import sys
import sqlite3
import pytest
import tempfile

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== P0-1: SQL 注入测试 ====================

def test_get_retention_curve_handles_special_characters_safely():
    """
    RED: source 参数包含单引号时，当前代码因 f-string 拼接导致 SQL 语法错误崩溃。
    GREEN: 修复后使用参数化查询，单引号作为普通字符处理，不崩溃。

    当前失败原因：
        h_src = f"AND h.source = '{source}'"
        当 source = "it's" 时，生成 SQL: AND h.source = 'it's'
        多余的 ' 导致 SQL 语法错误 → OperationalError

    修复后：
        h_src = "AND h.source = ?" if source else ""
        参数化查询将 'it's' 作为字面值处理，不破坏 SQL 结构。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        # 创建必要的表
        conn.executescript("""
            CREATE TABLE review_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id TEXT,
                subject_id INTEGER,
                ease_factor REAL DEFAULT 2.5,
                interval INTEGER DEFAULT 0,
                repetitions INTEGER DEFAULT 0,
                next_review TEXT,
                last_review TEXT,
                last_quality INTEGER,
                stability REAL DEFAULT 1.0,
                difficulty REAL DEFAULT 5.0,
                desired_retention REAL DEFAULT 0.9,
                card_state TEXT DEFAULT 'learning',
                learning_step INTEGER DEFAULT 2,
                consecutive_easy INTEGER DEFAULT 0
            );
            CREATE TABLE questions (
                id TEXT PRIMARY KEY,
                stem TEXT,
                options TEXT,
                answer TEXT,
                explanation TEXT,
                qtype TEXT,
                qtype_text TEXT,
                difficulty TEXT,
                subject_id INTEGER,
                category_id INTEGER,
                is_real_exam INTEGER,
                exam_year INTEGER,
                source TEXT,
                status INTEGER,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id TEXT,
                user_answer TEXT,
                correct INTEGER,
                subject_id INTEGER,
                source TEXT,
                timestamp TEXT
            );
        """)
        conn.commit()
        conn.close()

        # 临时替换 get_db 使用测试数据库
        import lib.db as db_module
        original_db_path = db_module.DB_PATH
        db_module.DB_PATH = db_path

        try:
            from models import get_retention_curve

            # 包含单引号的 source —— 当前代码会因此崩溃（OperationalError）
            # 修复后应该正常返回空列表
            result = get_retention_curve(user_id=1, subject_id=1, source="it's")

            # 应该返回空列表（没有数据），而不是崩溃
            assert isinstance(result, list)
            assert len(result) == 0

        finally:
            db_module.DB_PATH = original_db_path


def test_get_retention_curve_sql_injection_returns_no_data():
    """
    RED: SQL 注入 payload 导致查询结构被破坏，当前代码抛出 OperationalError。
    GREEN: 修复后使用参数化查询，注入 payload 作为普通字符串处理，返回空列表。

    当前失败原因：
        payload = "' UNION SELECT sql,2,3 FROM sqlite_master--"
        f-string 拼接后：AND h.source = '' UNION SELECT sql,2,3 FROM sqlite_master--'
        -- 注释掉了后续的 WHERE/GROUP BY 子句，导致 HAVING total >= 1 中 total 未定义
        → OperationalError: no such column: total

    修复后：
        参数化查询将整个 payload 作为 source 的字面值匹配
        没有 source 等于该 payload 的数据 → 返回空列表
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        conn.executescript("""
            CREATE TABLE review_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id TEXT,
                subject_id INTEGER,
                ease_factor REAL DEFAULT 2.5,
                interval INTEGER DEFAULT 0,
                repetitions INTEGER DEFAULT 0,
                next_review TEXT,
                last_review TEXT,
                last_quality INTEGER,
                stability REAL DEFAULT 1.0,
                difficulty REAL DEFAULT 5.0,
                desired_retention REAL DEFAULT 0.9,
                card_state TEXT DEFAULT 'learning',
                learning_step INTEGER DEFAULT 2,
                consecutive_easy INTEGER DEFAULT 0
            );
            CREATE TABLE questions (
                id TEXT PRIMARY KEY,
                stem TEXT,
                options TEXT,
                answer TEXT,
                explanation TEXT,
                qtype TEXT,
                qtype_text TEXT,
                difficulty TEXT,
                subject_id INTEGER,
                category_id INTEGER,
                is_real_exam INTEGER,
                exam_year INTEGER,
                source TEXT,
                status INTEGER,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id TEXT,
                user_answer TEXT,
                correct INTEGER,
                subject_id INTEGER,
                source TEXT,
                timestamp TEXT
            );
        """)
        conn.commit()
        conn.close()

        import lib.db as db_module
        original_db_path = db_module.DB_PATH
        db_module.DB_PATH = db_path

        try:
            from models import get_retention_curve

            # 经典 SQL 注入 payload
            malicious_source = "' UNION SELECT sql,2,3 FROM sqlite_master--"

            # 修复后：参数化查询将整个字符串作为 source 值匹配
            # 没有数据的 source 等于该 payload → 返回空列表
            result = get_retention_curve(user_id=1, subject_id=1, source=malicious_source)

            assert isinstance(result, list)
            assert len(result) == 0

            # 关键断言：结果中不应包含任何 sqlite_master 的内容
            for row in result:
                for val in row.values():
                    assert 'CREATE TABLE' not in str(val).upper()

        finally:
            db_module.DB_PATH = original_db_path


def test_get_retention_curve_normal_source():
    """
    正常 source 参数应该不崩溃，返回有效列表。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        conn.executescript("""
            CREATE TABLE review_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id TEXT,
                subject_id INTEGER,
                ease_factor REAL DEFAULT 2.5,
                interval INTEGER DEFAULT 0,
                repetitions INTEGER DEFAULT 0,
                next_review TEXT,
                last_review TEXT,
                last_quality INTEGER,
                stability REAL DEFAULT 1.0,
                difficulty REAL DEFAULT 5.0,
                desired_retention REAL DEFAULT 0.9,
                card_state TEXT DEFAULT 'learning',
                learning_step INTEGER DEFAULT 2,
                consecutive_easy INTEGER DEFAULT 0
            );
            CREATE TABLE questions (
                id TEXT PRIMARY KEY,
                stem TEXT,
                options TEXT,
                answer TEXT,
                explanation TEXT,
                qtype TEXT,
                qtype_text TEXT,
                difficulty TEXT,
                subject_id INTEGER,
                category_id INTEGER,
                is_real_exam INTEGER,
                exam_year INTEGER,
                source TEXT,
                status INTEGER,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id TEXT,
                user_answer TEXT,
                correct INTEGER,
                subject_id INTEGER,
                source TEXT,
                timestamp TEXT
            );
        """)
        conn.commit()
        conn.close()

        import lib.db as db_module
        original_db_path = db_module.DB_PATH
        db_module.DB_PATH = db_path
        db_module._local.conn = None

        try:
            from models import get_retention_curve

            # 正常 source 应该返回空列表（无数据时不崩溃）
            result = get_retention_curve(user_id=1, subject_id=1, source="practice")
            assert isinstance(result, list), "应该返回列表"

            # None source 也应该正常
            result = get_retention_curve(user_id=1, subject_id=1, source=None)
            assert isinstance(result, list), "source=None 应该返回列表"

        finally:
            db_module.DB_PATH = original_db_path
            db_module._local.conn = None
