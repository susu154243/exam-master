"""tests/test_mock_exam.py — 模拟考试权限和数量限制测试"""
import os
import sys
import pytest
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== P1-8: 模拟考试权限和数量限制测试 ====================

def test_start_mock_exam_requires_subject_license():
    """
    RED: 模拟考试路由应该有 @_check_subject_license 装饰器。

    当前问题：
        @app.route('/subjects/<int:subject_id>/mock/start', methods=['POST'])
        @login_required
        def start_mock_exam(subject_id):

        缺少权限检查，任何登录用户可对任意科目发起模拟考试。

    修复方案：
        添加 @_check_subject_license 装饰器。
    """
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找 start_mock_exam 函数的装饰器
    pattern = r"(@[^\n]+\n)+def start_mock_exam"
    match = re.search(pattern, content)

    assert match is not None, "start_mock_exam 函数应该存在"

    decorators = match.group(0)

    # 应该有权限检查装饰器
    assert '@_check_subject_license' in decorators, \
        "start_mock_exam 应该有 @_check_subject_license 装饰器"


def test_mock_exam_limits_question_count():
    """
    RED: 模拟考试应该限制题目数量上限。

    当前问题：
        question_count = request.form.get('question_count', 20, type=int)
        # 无上限检查

    修复方案：
        限制 question_count 上限（如 min(count, 100)）。
    """
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找 start_mock_exam 函数体
    pattern = r"def start_mock_exam\(subject_id\):.*?(?=\n@app\.route|\ndef |\Z)"
    match = re.search(pattern, content, re.DOTALL)

    assert match is not None, "start_mock_exam 函数应该存在"

    func_body = match.group(0)

    # 检查是否有数量限制逻辑
    has_limit = (
        'min(' in func_body or
        'max_count' in func_body or
        'limit' in func_body.lower() or
        'question_count >' in func_body or
        'question_count >=' in func_body
    )

    assert has_limit, \
        "start_mock_exam 应该限制 question_count 上限"
