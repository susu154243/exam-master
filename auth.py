#!/usr/bin/env python3
"""
权限中间件：装饰器用于保护路由。
"""
from functools import wraps
from flask import session, redirect, url_for, flash, abort, request
from models import get_user_by_id, get_user_subjects


def login_required(f):
    """需要登录"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """需要管理员权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        user = get_user_by_id(session['user_id'])
        if not user or user['role'] != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def subject_required(f):
    """需要科目访问权限（从 URL 参数或路径中获取 subject_id）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        
        user = get_user_by_id(session['user_id'])
        if not user:
            abort(403)
        
        # 管理员直接放行
        if user['role'] == 'admin':
            return f(*args, **kwargs)
        
        # 获取 subject_id（从参数或 kwargs）
        subject_id = kwargs.get('subject_id')
        if not subject_id:
            subject_id = request.args.get('subject_id')
        
        if not subject_id:
            abort(400)
        
        # 检查权限
        subjects = get_user_subjects(user['id'])
        allowed_ids = [s['id'] for s in subjects]
        if int(subject_id) not in allowed_ids:
            flash('您没有访问该科目的权限', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """获取当前登录用户"""
    if 'user_id' not in session:
        return None
    return get_user_by_id(session['user_id'])
