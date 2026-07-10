"""tests/test_csrf.py — CSRF保护测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_csrf_protection_enabled():
    """
    RED: 应用应该启用CSRF保护。

    当前问题：
        所有POST路由都没有CSRF token验证，存在跨站请求伪造风险。

    修复方案：
        1. 安装flask-wtf
        2. 在app.py中初始化CSRFProtect
        3. 在所有模板表单中添加{{ csrf_token() }}
    """
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否导入并初始化了CSRFProtect
    has_csrf_import = 'from flask_wtf.csrf import CSRFProtect' in content or 'CSRFProtect' in content
    has_csrf_init = 'csrf = CSRFProtect(app)' in content or 'csrf.init_app(app)' in content

    assert has_csrf_import and has_csrf_init, \
        "app.py应该导入并初始化CSRFProtect"


def test_csrf_token_in_login_form():
    """
    RED: 登录表单应该包含CSRF token。

    修复方案：
        在templates/login.html的<form>标签内添加{{ csrf_token() }}
    """
    template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'login.html')

    if not os.path.exists(template_path):
        pytest.skip("login.html不存在")

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否有CSRF token
    has_csrf = '{{ csrf_token() }}' in content or '{% csrf_token %}' in content or 'csrf_token()' in content

    assert has_csrf, "login.html应该包含CSRF token"
