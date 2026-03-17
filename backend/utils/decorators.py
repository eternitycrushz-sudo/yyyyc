# -*- coding: utf-8 -*-
"""
装饰器

原理：
装饰器是 Python 的语法糖，用于在不修改函数代码的情况下增加功能。
这里用来实现：
1. @login_required - 需要登录才能访问
2. @permission_required('xxx') - 需要特定权限才能访问
"""

from functools import wraps
from flask import request, jsonify, g
from backend.utils.jwt_util import verify_token, get_token_from_header
from backend.models.user import UserModel


def login_required(f):
    """
    登录验证装饰器
    
    使用方式：
        @app.route('/api/xxx')
        @login_required
        def xxx():
            # g.current_user 可以获取当前用户信息
            pass
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header(request.headers)
        # 也支持从 URL 参数获取 token（用于 window.open 下载等场景）
        if not token:
            token = request.args.get('token')

        if not token:
            return jsonify({
                'success': False,
                'code': 401,
                'message': '未登录，请先登录'
            }), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'code': 401,
                'message': 'Token 无效或已过期'
            }), 401
        
        # 将用户信息存到 g 对象，方便后续使用
        g.current_user = {
            'user_id': payload['user_id'],
            'username': payload['username'],
            'roles': payload.get('roles', [])
        }
        
        return f(*args, **kwargs)
    
    return decorated


def permission_required(permission_code: str):
    """
    权限验证装饰器
    
    使用方式：
        @app.route('/api/xxx')
        @login_required
        @permission_required('crawler:start')
        def xxx():
            pass
    
    Args:
        permission_code: 权限编码，如 'crawler:start'
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 先检查是否登录
            if not hasattr(g, 'current_user'):
                return jsonify({
                    'success': False,
                    'code': 401,
                    'message': '未登录'
                }), 401
            
            user_id = g.current_user['user_id']
            
            # 检查权限
            if not UserModel.has_permission(user_id, permission_code):
                return jsonify({
                    'success': False,
                    'code': 403,
                    'message': f'无权限: {permission_code}'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator
