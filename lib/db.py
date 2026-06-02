#!/usr/bin/env python3
"""
数据库连接管理：线程级连接缓存 + 一次性表初始化。
供 models.py / app.py / admin.py 共用。
"""
import sqlite3
import os
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database.db')
DB_PATH = os.path.normpath(DB_PATH)

_local = threading.local()


def get_db():
    """获取数据库连接（线程级缓存，避免重复 connect + PRAGMA）"""
    conn = getattr(_local, 'conn', None)
    if conn is None:
        conn = _new_connection()
        _local.conn = conn
    else:
        # 检查连接是否仍然有效（SQLite 连接在 fork 后会失效）
        try:
            conn.execute("SELECT 1")
        except sqlite3.ProgrammingError:
            # 连接已失效，创建新连接
            conn = _new_connection()
            _local.conn = conn
    return conn


def _new_connection():
    """创建新的数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def close_db(exception=None):
    """关闭当前线程的数据库连接"""
    conn = getattr(_local, 'conn', None)
    if conn is not None:
        try:
            conn.close()
        finally:
            _local.conn = None


def reset_db():
    """强制清除线程连接缓存，不关闭连接（仅设 _local.conn = None）。
    用于 Gunicorn master 初始化后、fork worker 前调用，
    确保 fork 后 worker 创建新连接而非继承 master 的旧连接。
    """
    _local.conn = None


# ==================== 一次性表初始化（启动时调用） ====================

def init_tables():
    """确保所有必要的表和列已创建。应在 Flask 启动时调用一次。"""
    conn = get_db()
    cur = conn.cursor()

    # practice_sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            queue TEXT,
            answered TEXT,
            retry_count TEXT,
            stubborn TEXT,
            total_attempts INTEGER DEFAULT 0,
            answered_correct_first INTEGER DEFAULT 0,
            answered_wrong INTEGER DEFAULT 0,
            initial_count INTEGER DEFAULT 0,
            current_qid TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # exam_records
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            total INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # notifications
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            question_id TEXT,
            is_read INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 检查 question_comments.read_by_admin_at 列
    try:
        cur.execute("ALTER TABLE question_comments ADD COLUMN read_by_admin_at DATETIME")
    except Exception:
        pass

    # 检查 question_notes.read_by_admin_at 列
    try:
        cur.execute("ALTER TABLE question_notes ADD COLUMN read_by_admin_at DATETIME")
    except Exception:
        pass

    conn.commit()


# 兼容旧版 models.py 的导入别名
_init_tables = init_tables
