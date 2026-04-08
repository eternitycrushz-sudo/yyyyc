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
            'force_pwd_change': bool(user.get('force_pwd_change', 0)),
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
    提交密码重置申请（无需登录）

    请求：
    {
        "username": "test",
        "reason": "忘记密码了"
    }
    """
    data = request.json or {}
    username = data.get('username', '').strip()
    reason = data.get('reason', '').strip()

    if not username:
        return jsonify({
            'success': False,
            'message': '请输入用户名'
        }), 400

    # 查找用户是否存在
    user = UserModel.find_by_username(username)
    if not user:
        return jsonify({
            'success': False,
            'message': '该用户名不存在'
        }), 404

    # 检查是否已有待处理的申请
    try:
        from backend.models.base import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM sys_password_reset_request WHERE username = %s AND status = 0",
                (username,)
            )
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': '您已提交过重置申请，请等待管理员处理'
                }), 400

            # 插入申请
            cursor.execute(
                "INSERT INTO sys_password_reset_request (username, reason) VALUES (%s, %s)",
                (username, reason)
            )
        conn.commit()
        conn.close()

        try:
            log_operation('提交密码重置申请', '认证', f"用户 {username} 提交了密码重置申请")
        except:
            pass

        return jsonify({
            'success': True,
            'message': '申请已提交，请等待管理员处理'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'提交失败: {str(e)}'
        }), 500
 
 
@auth_bp.route('/reset-request-status', methods=['GET'])
def get_reset_request_status():
    """查询用户最近一次密码重置申请状态"""
    username = request.args.get('username', '').strip()

    if not username:
        return jsonify({
            'success': False,
            'message': '请输入用户名'
        }), 400

    try:
        user = UserModel.find_by_username(username)
        if not user:
            return jsonify({
                'success': False,
                'message': '该用户名不存在'
            }), 404

        from backend.models.base import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, reason, status, temporary_password, handler_username, handled_at, created_at
                FROM sys_password_reset_request
                WHERE username = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (username,)
            )
            latest = cursor.fetchone()
        conn.close()

        if not latest:
            return jsonify({
                'success': True,
                'data': {
                    'status': -1,
                    'message': '暂无重置申请记录'
                }
            })

        data = {
            'status': latest['status'],
            'message': '',
            'created_at': latest.get('created_at'),
            'handled_at': latest.get('handled_at'),
            'handler_username': latest.get('handler_username'),
        }
        if latest['status'] == 0:
            data['message'] = '申请正在处理中，请稍后再查询'
        elif latest['status'] == 1:
            data['message'] = '申请已通过'
            data['temporary_password'] = latest.get('temporary_password') or '123456'
        else:
            data['message'] = '申请已被拒绝，请联系管理员'

        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查询失败: {str(e)}'
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


@auth_bp.route('/force-change-password', methods=['POST'])
@login_required
def force_change_password():
    """
    强制修改密码（用户被管理员重置密码后，必须修改密码才能进入系统）

    请求：
    {
        "new_password": "newpass123",
        "confirm_password": "newpass123"
    }
    """
    data = request.json or {}
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'message': '新密码长度至少6位'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400

    user_id = g.current_user['user_id']
    try:
        from backend.models.base import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE sys_user SET password = %s, force_pwd_change = 0 WHERE id = %s",
                (UserModel.hash_password(new_password), user_id)
            )
        conn.commit()
        conn.close()

        try:
            log_operation('强制修改密码', '认证', '用户完成强制密码修改',
                          user_id=user_id, username=g.current_user.get('username', ''))
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
