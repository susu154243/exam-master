"""tests/test_app.py — app.py 路由测试"""
import os
import sys
import pytest
import tempfile
import sqlite3
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== P0-5: 历年真题权限校验测试 ====================

def test_exam_by_year_requires_subject_permission():
    """
    RED: 无权限用户访问历年真题应返回 403，当前代码仅检查登录状态。

    当前问题：
        @app.route('/subjects/<int:subject_id>/exams/<int:year>')
        @login_required  # 只检查登录，不检查科目权限
        def exam_by_year(subject_id, year):

    修复方案：
        添加 @_check_subject_license 装饰器检查授权有效性
    """
    # 这个测试需要 Flask 测试客户端，我们先验证当前代码确实缺少权限检查
    # 通过代码审查确认：exam_by_year 只有 @login_required，没有权限检查

    # 读取 app.py 中 exam_by_year 函数的装饰器
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找 exam_by_year 函数定义前的装饰器
    import re
    pattern = r"(@[^\n]+\n)+def exam_by_year"
    match = re.search(pattern, content)

    assert match is not None, "exam_by_year 函数应该存在"

    decorators = match.group(0)

    # 当前代码只有 @login_required，没有 @_check_subject_license
    # 这个断言会在修复前失败（因为缺少权限检查装饰器）
    assert '@_check_subject_license' in decorators or '@_check_subject_permission' in decorators, \
        "exam_by_year 应该有权限检查装饰器（@_check_subject_license 或 @_check_subject_permission）"


def test_submit_exam_requires_subject_license():
    """
    RED: 考试提交路由也应该检查授权，当前代码缺少检查。
    """
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    import re
    pattern = r"(@[^\n]+\n)+def submit_exam"
    match = re.search(pattern, content)

    assert match is not None, "submit_exam 函数应该存在"

    decorators = match.group(0)

    # 提交考试也应该检查授权
    assert '@_check_subject_license' in decorators, \
        "submit_exam 应该有 @_check_subject_license 装饰器"
