#!/usr/bin/env python3
"""
迁移脚本：为 review_schedule 表添加 lapses 字段

lapses 字段用于追踪用户答错次数（quality <= 1），帮助分析学习难点。
"""

import sqlite3
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import DB_PATH


def migrate():
    """执行迁移"""
    db_path = DB_PATH
    print(f"数据库路径: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 检查 lapses 字段是否已存在
    cur.execute("PRAGMA table_info(review_schedule)")
    columns = [row[1] for row in cur.fetchall()]

    if 'lapses' in columns:
        print("✓ lapses 字段已存在，无需迁移")
        conn.close()
        return

    print("→ 添加 lapses 字段...")

    try:
        # 添加 lapses 字段，默认值为 0
        cur.execute("""
            ALTER TABLE review_schedule
            ADD COLUMN lapses INTEGER DEFAULT 0
        """)

        conn.commit()
        print("✓ lapses 字段添加成功")

        # 统计信息
        cur.execute("SELECT COUNT(*) FROM review_schedule")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM review_schedule WHERE lapses = 0")
        zero_count = cur.fetchone()[0]

        print(f"  - 总记录数: {total}")
        print(f"  - lapses=0 的记录: {zero_count}")
        print(f"  - 新字段已初始化: {total} 条记录")

    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

    print("\n✓ 迁移完成")


if __name__ == '__main__':
    migrate()
