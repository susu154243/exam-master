"""tests/test_auth.py — auth.py 权限中间件测试"""
import os
import sys
import pytest
import tempfile
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== P1-6: admin_required 单设备校验测试 ====================

def test_admin_required_verifies_session_token():
    """
    RED: admin_required 装饰器应该验证 session_token，确保单设备登录策略。

    当前问题：
        def admin_required(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    return redirect(url_for('admin.login'))
                user = get_user_by_id(session['user_id'])
                if not user or user['role'] != 'admin':
                    abort(403)
                return f(*args, **kwargs)
            return decorated_function

        缺少 verify_session_token 调用，管理员在其他设备登录后旧会话仍然有效。

    修复方案：
        添加 session_token 验证，与 login_required 保持一致。
    """
    auth_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'auth.py')
    with open(auth_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找 admin_required 函数
    import re
    pattern = r"def admin_required\(f\):.*?return decorated_function"
    match = re.search(pattern, content, re.DOTALL)

    assert match is not None, "admin_required 函数应该存在"

    func_body = match.group(0)

    # 检查函数中是否调用了 verify_session_token
    assert 'verify_session_token' in func_body, \
        "admin_required 应该调用 verify_session_token 进行单设备校验"


def test_admin_required_clears_session_on_token_mismatch():
    """
    RED: 当 session_token 不匹配时，admin_required 应该清除 session 并重定向到登录页。

    当前问题：
        admin_required 没有验证 session_token，所以即使 token 不匹配也不会清除 session。

    修复方案：
        验证失败时调用 session.clear() 并重定向。
    """
    auth_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'auth.py')
    with open(auth_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找 admin_required 函数
    import re
    pattern = r"def admin_required\(f\):.*?return decorated_function"
    match = re.search(pattern, content, re.DOTALL)

    assert match is not None, "admin_required 函数应该存在"

    func_body = match.group(0)

    # 检查函数中是否有 session.clear() 调用（验证失败时清除 session）
    assert 'session.clear()' in func_body, \
        "admin_required 在 token 验证失败时应该调用 session.clear()"
