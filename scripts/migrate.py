#!/usr/bin/env python3
"""
数据库迁移脚本：从旧版单表结构迁移到新版多表权限结构。
"""
import sqlite3
import json
import os
import secrets

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def run_migrations():
    conn = get_conn()
    cursor = conn.cursor()

    print("开始数据库迁移...")

    # =========================================
    # 1. 创建新表
    # =========================================

    # 科目表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        description TEXT DEFAULT '',
        icon TEXT DEFAULT '📚',
        status INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("✅ 创建 subjects 表")

    # 分类表（三级）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        parent_id INTEGER DEFAULT 0,
        name TEXT NOT NULL,
        level INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER DEFAULT 0
    )
    """)
    print("✅ 创建 categories 表")

    # 用户权限表（先不创建外键，避免依赖问题）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        can_practice INTEGER DEFAULT 1,
        can_mock INTEGER DEFAULT 1,
        can_daily INTEGER DEFAULT 1,
        can_manage INTEGER DEFAULT 0
    )
    """)
    print("✅ 创建 user_subjects 表")

    # 扩展 users 表
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
    except sqlite3.OperationalError:
        pass
    print("✅ 扩展 users 表")

    # 改造 questions 表（先不添加外键约束）
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN subject_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN category_id INTEGER REFERENCES categories(id)")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN explanation TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN is_real_exam INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN exam_year INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN source TEXT DEFAULT 'practice'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN status INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN qtype_text TEXT DEFAULT '单选题'")
    except sqlite3.OperationalError:
        pass
    print("✅ 扩展 questions 表")

    # 扩展 history 表
    try:
        cursor.execute("ALTER TABLE history ADD COLUMN subject_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    print("✅ 扩展 history 表")

    # 扩展 favorites 表
    try:
        cursor.execute("ALTER TABLE favorites ADD COLUMN subject_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    print("✅ 扩展 favorites 表")

    # =========================================
    # 2. 插入测试数据
    # =========================================

    # 插入科目
    cursor.execute("""
    INSERT OR IGNORE INTO subjects (id, name, code, description, icon, status)
    VALUES (1, '软考高项', 'ruankao_gaoxiang', '信息系统项目管理师', '📚', 1)
    """)
    print("✅ 插入科目：软考高项")

    # 插入分类树
    categories = [
        # 一级分类
        (2, 1, 0, '综合知识', 1, 1),
        (3, 1, 0, '案例分析', 1, 2),
        # 二级分类 - 综合知识
        (4, 1, 2, '信息化与信息系统', 2, 1),
        (5, 1, 2, '项目管理基础', 2, 2),
        (6, 1, 2, '法律法规与标准', 2, 3),
        # 三级分类 - 信息化与信息系统
        (7, 1, 4, '信息技术基础', 3, 1),
        (8, 1, 4, '信息系统工程', 3, 2),
        (9, 1, 4, '信息安全', 3, 3),
        # 三级分类 - 项目管理基础
        (10, 1, 5, '项目整体管理', 3, 1),
        (11, 1, 5, '项目范围管理', 3, 2),
        (12, 1, 5, '项目进度管理', 3, 3),
        # 三级分类 - 法律法规与标准
        (13, 1, 6, '合同法', 3, 1),
        (14, 1, 6, '招投标法', 3, 2),
        # 二级分类 - 案例分析
        (15, 1, 3, '进度管理', 2, 1),
        (16, 1, 3, '成本管理', 2, 2),
        (17, 1, 3, '质量管理', 2, 3),
        # 三级分类 - 进度管理
        (18, 1, 15, '网络图计算', 3, 1),
        (19, 1, 15, '关键路径', 3, 2),
        # 三级分类 - 成本管理
        (20, 1, 16, '挣值分析', 3, 1),
        (21, 1, 16, '成本估算', 3, 2),
        # 三级分类 - 质量管理
        (22, 1, 17, '质量保证', 3, 1),
        (23, 1, 17, '质量控制', 3, 2),
    ]
    for cat in categories:
        cursor.execute("""
        INSERT OR IGNORE INTO categories (id, subject_id, parent_id, name, level, sort_order)
        VALUES (?, ?, ?, ?, ?, ?)
        """, cat)
    print(f"✅ 插入 {len(categories)} 个分类")

    # =========================================
    # 3. 筛选 30 道题并更新标签
    # =========================================
    print("\n筛选 30 道测试题...")
    
    # 先获取所有题目
    cursor.execute("SELECT id FROM questions ORDER BY id")
    all_ids = [row['id'] for row in cursor.fetchall()]
    
    # 均匀采样 30 题
    import random
    random.seed(42)  # 固定种子，确保可重复
    if len(all_ids) > 30:
        selected_ids = sorted(random.sample(all_ids, 30))
    else:
        selected_ids = all_ids
    
    print(f"选中题目: {selected_ids}")

    # 分类分配（均匀分配到不同三级分类）
    leaf_categories = [7, 8, 9, 10, 11, 12, 13, 14, 18, 19, 20, 21, 22, 23]
    sources = ['practice', 'practice', 'practice', 'exam', 'mock', 'daily']
    
    for i, qid in enumerate(selected_ids):
        cat_id = leaf_categories[i % len(leaf_categories)]
        source = sources[i % len(sources)]
        
        # 判断题型
        cursor.execute("SELECT qtype FROM questions WHERE id = ?", (qid,))
        row = cursor.fetchone()
        qtype_text = row['qtype'] if row else '单选题'
        qtype_code = 'multiple' if '多选' in qtype_text else 'single'
        
        # 判断是否真题
        is_real = 1 if source == 'exam' else 0
        exam_year = 2024 if is_real else None
        
        cursor.execute("""
        UPDATE questions SET
            subject_id = 1,
            category_id = ?,
            source = ?,
            qtype_text = ?,
            is_real_exam = ?,
            exam_year = ?,
            status = 1
        WHERE id = ?
        """, (cat_id, source, qtype_code, is_real, exam_year, qid))

    # 禁用未选中的题目
    placeholders = ','.join(['?' for _ in selected_ids])
    cursor.execute(f"""
    UPDATE questions SET status = 0
    WHERE id NOT IN ({placeholders})
    """, selected_ids)
    
    print(f"✅ 启用 {len(selected_ids)} 道题，禁用 {len(all_ids) - len(selected_ids)} 道题")

    # =========================================
    # 4. 创建默认管理员账号
    # =========================================
    import hashlib
    
    admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    cursor.execute("""
    INSERT OR IGNORE INTO users (username, password_hash, role, status)
    VALUES ('admin', ?, 'admin', 1)
    """, (admin_hash,))
    
    # 创建测试用户 A（有软考权限）
    user_a_hash = hashlib.sha256('userA123'.encode()).hexdigest()
    cursor.execute("""
    INSERT OR IGNORE INTO users (username, password_hash, role, status)
    VALUES ('userA', ?, 'user', 1)
    """, (user_a_hash,))
    
    # 创建测试用户 B（无权限）
    user_b_hash = hashlib.sha256('userB123'.encode()).hexdigest()
    cursor.execute("""
    INSERT OR IGNORE INTO users (username, password_hash, role, status)
    VALUES ('userB', ?, 'user', 1)
    """, (user_b_hash,))
    
    # 分配权限
    cursor.execute("SELECT id FROM users WHERE username = 'userA'")
    user_a = cursor.fetchone()
    if user_a:
        cursor.execute("""
        INSERT OR IGNORE INTO user_subjects (user_id, subject_id, can_practice, can_mock, can_daily, can_manage)
        VALUES (?, 1, 1, 1, 1, 0)
        """, (user_a['id'],))
    
    print("✅ 创建管理员 (admin/admin123)")
    print("✅ 创建测试用户A (userA/userA123) — 有软考权限")
    print("✅ 创建测试用户B (userB/userB123) — 无权限")

    # =========================================
    # 5. 清理旧数据
    # =========================================
    cursor.execute("DELETE FROM history WHERE subject_id IS NULL")
    cursor.execute("DELETE FROM favorites WHERE subject_id IS NULL")
    print("✅ 清理旧数据")

    conn.commit()
    conn.close()
    print("\n🎉 数据库迁移完成！")

if __name__ == '__main__':
    run_migrations()
