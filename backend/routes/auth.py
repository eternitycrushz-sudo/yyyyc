# -*- coding: utf-8 -*-
"""
认证路由：登录、注册、获取用户信息
"""

from flask import Blueprint, request, jsonify, g
from backend.models.user import UserModel
from backend.models.role import RoleModel
from backend.utils.jwt_util import create_token
from backend.utils.decorators import login_required
from backend.routes.oplog import log_operation

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    
    请求：
    {
        "username": "admin",
        "password": "admin123"
    }
    
    响应：
    {
        "success": true,
        "data": {
            "token": "xxx",
            "user": {...}
        }
    }
    """
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'message': '用户名和密码不能为空'
        }), 400
    
    # 查找用户
    user = UserModel.find_by_username(username)
    if not user:
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        }), 401
    
    # 验证密码
    if not UserModel.verify_password(password, user['password']):
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        }), 401
    
    # 检查状态
    if user['status'] != 1:
        return jsonify({
            'success': False,
            'message': '账号已被禁用'
        }), 403
    
    # 获取角色
    roles = UserModel.get_user_roles(user['id'])
    role_codes = [r['code'] for r in roles]
    
    # 生成 Token
    token = create_token(user['id'], user['username'], role_codes)
    
    # 获取权限
    permissions = UserModel.get_user_permissions(user['id'])
    
    # 记录登录日志
    try:
        log_operation('登录', '认证', f"用户 {username} 登录成功", user_id=user['id'], username=username)
    except:
        pass

    return jsonify({
        'success': True,
        'message': '登录成功',
        'data': {
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'nickname': user['nickname'],
                'avatar': user['avatar'],
                'roles': roles,
                'permissions': [p['code'] for p in permissions]
            }
        }
    })


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册

    请求：
    {
        "username": "test",
        "password": "123456",
        "nickname": "测试用户",
        "role": "viewer"  # 可选: 'viewer' 或 'operator'，默认为 'viewer'
    }
    """
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    nickname = data.get('nickname', '')
    role = data.get('role', 'observer').lower()  # 默认为观察员

    if not username or not password:
        return jsonify({
            'success': False,
            'message': '用户名和密码不能为空'
        }), 400

    if len(password) < 6:
        return jsonify({
            'success': False,
            'message': '密码长度至少6位'
        }), 400

    # 验证角色
    if role not in ['observer', 'operator']:
        return jsonify({
            'success': False,
            'message': '无效的角色，只能选择 observer 或 operator'
        }), 400

    # 检查用户名是否存在
    if UserModel.find_by_username(username):
        return jsonify({
            'success': False,
            'message': '用户名已存在'
        }), 400

    try:
        # 创建用户
        user_id = UserModel.create(username, password, nickname)

        # 分配选中的角色
        selected_role = RoleModel.find_by_code(role)
        if selected_role:
            UserModel.assign_role(user_id, selected_role['id'])
        else:
            # 如果找不到角色，默认分配 observer
            observer_role = RoleModel.find_by_code('observer')
            if observer_role:
                UserModel.assign_role(user_id, observer_role['id'])

        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': {'user_id': user_id}
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'注册失败: {str(e)}'
        }), 500


@auth_bp.route('/info', methods=['GET'])
@login_required
def get_user_info():
    """
    获取当前登录用户信息
    """
    user_id = g.current_user['user_id']
    user = UserModel.find_by_id(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': '用户不存在'
        }), 404
    
    roles = UserModel.get_user_roles(user_id)
    permissions = UserModel.get_user_permissions(user_id)
    
    return jsonify({
        'success': True,
        'data': {
            'id': user['id'],
            'username': user['username'],
            'nickname': user['nickname'],
            'email': user['email'],
            'phone': user['phone'],
            'avatar': user['avatar'],
            'roles': roles,
            'permissions': [p['code'] for p in permissions]
        }
    })


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    重置密码

    请求：
    {
        "username": "test",
        "new_password": "newpass123"
    }
    """
    data = request.json or {}
    username = data.get('username', '').strip()
    new_password = data.get('new_password', '')

    if not username or not new_password:
        return jsonify({
            'success': False,
            'message': '用户名和新密码不能为空'
        }), 400

    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'message': '新密码长度至少6位'
        }), 400

    # 查找用户
    user = UserModel.find_by_username(username)
    if not user:
        return jsonify({
            'success': False,
            'message': '该用户名不存在'
        }), 404

    # 更新密码
    try:
        from backend.models.base import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE sys_user SET password = %s WHERE username = %s",
                (UserModel.hash_password(new_password), username)
            )
        conn.commit()
        conn.close()

        try:
            log_operation('重置密码', '认证', f"用户 {username} 重置了密码")
        except:
            pass

        return jsonify({
            'success': True,
            'message': '密码重置成功，请使用新密码登录'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'密码重置失败: {str(e)}'
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """
    修改自己的密码（需登录）

    请求：
    {
        "old_password": "123456",
        "new_password": "newpass123"
    }
    """
    data = request.json or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'success': False, 'message': '旧密码和新密码不能为空'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '新密码长度至少6位'}), 400

    # 检查新旧密码是否相同
    if old_password == new_password:
        return jsonify({'success': False, 'message': '新密码不能与原密码相同'}), 400

    user_id = g.current_user['user_id']
    user = UserModel.find_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    if UserModel.hash_password(old_password) != user['password']:
        return jsonify({'success': False, 'message': '旧密码不正确'}), 400

    try:
        from backend.models.base import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE sys_user SET password = %s WHERE id = %s",
                (UserModel.hash_password(new_password), user_id)
            )
        conn.commit()
        conn.close()

        # 记录操作日志
        try:
            log_operation('修改密码', '认证', f"用户修改了自己的密码", user_id=user_id, username=g.current_user.get('username', ''))
        except:
            pass

        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'修改失败: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    退出登录
    
    JWT 是无状态的，服务端不需要做什么
    前端删除本地存储的 token 即可
    """
    return jsonify({
        'success': True,
        'message': '退出成功'
    })
