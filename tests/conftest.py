"""pytest fixtures for KeyIn tests"""
import os
import sys
import pytest
import tempfile
import shutil
import sqlite3

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_db(tmp_path):
    """创建临时测试数据库"""
    db_path = str(tmp_path / "test_database.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # 创建核心表
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            status INTEGER DEFAULT 1,
            email TEXT,
            phone TEXT,
            session_token TEXT,
            security_question INTEGER,
            security_answer TEXT,
            last_login TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE,
            description TEXT,
            icon TEXT,
            status INTEGER DEFAULT 1,
            level TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT
        );

        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            parent_id INTEGER DEFAULT 0,
            name TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        );

        CREATE TABLE questions (
            id TEXT PRIMARY KEY,
            stem TEXT NOT NULL,
            options TEXT,
            answer TEXT NOT NULL,
            explanation TEXT,
            qtype TEXT DEFAULT 'single',
            qtype_text TEXT DEFAULT '单选题',
            difficulty TEXT,
            subject_id INTEGER,
            category_id INTEGER,
            is_real_exam INTEGER DEFAULT 0,
            exam_year INTEGER,
            source TEXT DEFAULT 'practice',
            status INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT
        );

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

        CREATE TABLE history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_id TEXT,
            user_answer TEXT,
            correct INTEGER,
            subject_id INTEGER,
            source TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE user_licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject_id INTEGER,
            expires_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE user_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject_id INTEGER,
            can_practice INTEGER DEFAULT 1,
            can_mock INTEGER DEFAULT 1,
            can_daily INTEGER DEFAULT 1,
            can_manage INTEGER DEFAULT 0
        );

        CREATE TABLE invitation_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            subject_id INTEGER,
            days INTEGER DEFAULT 30,
            max_uses INTEGER DEFAULT 1,
            used_count INTEGER DEFAULT 0,
            expires_at TEXT,
            status INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE site_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    yield db_path, conn
    conn.close()


@pytest.fixture
def sample_user(temp_db):
    """创建测试用户"""
    db_path, conn = temp_db
    import hashlib
    from models import hash_password

    password_hash = hash_password("testpassword123")
    conn.execute(
        "INSERT INTO users (username, password_hash, role, status) VALUES (?, ?, ?, ?)",
        ("testuser", password_hash, "user", 1)
    )
    conn.commit()
    return {"id": 1, "username": "testuser", "password": "testpassword123", "role": "user"}


@pytest.fixture
def admin_user(temp_db):
    """创建测试管理员"""
    db_path, conn = temp_db
    from models import hash_password

    password_hash = hash_password("adminpassword123")
    conn.execute(
        "INSERT INTO users (username, password_hash, role, status) VALUES (?, ?, ?, ?)",
        ("admin", password_hash, "admin", 1)
    )
    conn.commit()
    return {"id": 1, "username": "admin", "password": "adminpassword123", "role": "admin"}


@pytest.fixture
def sample_subject(temp_db):
    """创建测试科目"""
    db_path, conn = temp_db
    conn.execute(
        "INSERT INTO subjects (name, code, description, icon, status) VALUES (?, ?, ?, ?, ?)",
        ("测试科目", "TEST001", "测试用科目", "📝", 1)
    )
    conn.commit()
    return {"id": 1, "name": "测试科目", "code": "TEST001"}


@pytest.fixture
def sample_category(temp_db, sample_subject):
    """创建测试分类"""
    db_path, conn = temp_db
    conn.execute(
        "INSERT INTO categories (subject_id, parent_id, name, level, sort_order) VALUES (?, ?, ?, ?, ?)",
        (sample_subject["id"], 0, "第一章", 1, 1)
    )
    conn.commit()
    return {"id": 1, "subject_id": sample_subject["id"], "name": "第一章", "level": 1}


@pytest.fixture
def sample_question(temp_db, sample_subject, sample_category):
    """创建测试题目"""
    db_path, conn = temp_db
    import json
    options = json.dumps({"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"})
    conn.execute(
        "INSERT INTO questions (id, stem, options, answer, explanation, qtype, subject_id, category_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("1.1-01", "测试题目？", options, "A", "这是解析", "single", sample_subject["id"], sample_category["id"], 1)
    )
    conn.commit()
    return {"id": "1.1-01", "stem": "测试题目？", "answer": "A", "subject_id": sample_subject["id"], "category_id": sample_category["id"]}
