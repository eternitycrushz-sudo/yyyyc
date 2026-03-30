# -*- coding: utf-8 -*-
"""
系统设置路由 - 用户管理、角色管理
"""

from flask import Blueprint, jsonify, request, g
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required, permission_required
from backend.routes.oplog import log_operation
import hashlib
import logging

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)


# ===================== 用户管理 =====================

@settings_bp.route('/users', methods=['GET'])
@login_required
@permission_required('user:list')
def list_users():
    """获取用户列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        offset = (page - 1) * page_size

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM sys_user")
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT u.id, u.username, u.nickname, u.email, u.phone, u.status, u.created_at,
                   GROUP_CONCAT(r.name) as role_names,
                   GROUP_CONCAT(r.code) as role_codes
            FROM sys_user u
            LEFT JOIN sys_user_role ur ON u.id = ur.user_id
            LEFT JOIN sys_role r ON ur.role_id = r.id
            GROUP BY u.id
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, (page_size, offset))
        users = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'code': 0,
            'data': {
                'list': users,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@settings_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@permission_required('user:update')
def update_user(user_id):
    """更新用户信息（包括角色）"""
    try:
        admin_id = g.current_user['user_id']
        admin_username = g.current_user['username']

        # 防止管理员修改自己的角色
        if user_id == admin_id:
            return jsonify({'code': -1, 'msg': '不能修改自己的角色'}), 400

        data = request.json or {}
        nickname = data.get('nickname')
        email = data.get('email')
        phone = data.get('phone')
        status = data.get('status')
        role_code = data.get('role_code')  # 'operator' 或 'viewer'

        conn = get_db_connection()
        cursor = conn.cursor()

        updates = []
        params = []
        changes = []

        if nickname is not None:
            updates.append("nickname = %s")
            params.append(nickname)
            changes.append(f"昵称: {nickname}")
        if email is not None:
            updates.append("email = %s")
            params.append(email)
            changes.append(f"邮箱: {email}")
        if phone is not None:
            updates.append("phone = %s")
            params.append(phone)
            changes.append(f"电话: {phone}")
        if status is not None:
            updates.append("status = %s")
            params.append(status)
            changes.append(f"状态: {status}")

        if updates:
            params.append(user_id)
            cursor.execute(f"UPDATE sys_user SET {', '.join(updates)} WHERE id = %s", params)

        # 更新角色 - 只允许修改为 'operator' 或 'viewer'
        if role_code and role_code in ['operator', 'viewer']:
            cursor.execute("SELECT id, name FROM sys_role WHERE code = %s", (role_code,))
            role = cursor.fetchone()
            if role:
                cursor.execute("DELETE FROM sys_user_role WHERE user_id = %s", (user_id,))
                cursor.execute("INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)", (user_id, role['id']))
                changes.append(f"角色: {role['name']}")

        if changes:
            # 记录操作日志
            cursor.execute("""
                INSERT INTO sys_operation_log (user_id, username, action, module, detail, ip, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (admin_id, admin_username, '修改用户信息', 'user_management',
                  f"修改用户ID {user_id}: {', '.join(changes)}", request.remote_addr, 1))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'msg': '更新成功'})
    except Exception as e:
        logger.error(f"更新用户失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@settings_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
@login_required
@permission_required('user:update')
def reset_password(user_id):
    """重置用户密码"""
    try:
        data = request.json or {}
        new_password = data.get('password', '123456')
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sys_user SET password = %s WHERE id = %s", (password_hash, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'msg': f'密码已重置为 {new_password}'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500


@settings_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@permission_required('user:delete')
def delete_user(user_id):
    """删除用户"""
    try:
        if user_id == g.current_user['user_id']:
            return jsonify({'code': -1, 'msg': '不能删除自己'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 先查询被删除用户的用户名
        cursor.execute("SELECT username FROM sys_user WHERE id = %s", (user_id,))
        target_user = cursor.fetchone()
        target_username = target_user['username'] if target_user else f'ID:{user_id}'

        cursor.execute("DELETE FROM sys_user_role WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM sys_user WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # 记录操作日志
        log_operation('删除用户', '用户管理', f"删除用户 {target_username} (ID:{user_id})")

        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ===================== 角色管理 =====================

@settings_bp.route('/roles', methods=['GET'])
@login_required
@permission_required('user:list')
def list_roles():
    """获取角色列表（含权限）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.id, r.code, r.name, r.description, r.status,
                   GROUP_CONCAT(p.code) as permissions
            FROM sys_role r
            LEFT JOIN sys_role_permission rp ON r.id = rp.role_id
            LEFT JOIN sys_permission p ON rp.permission_id = p.id
            GROUP BY r.id
            ORDER BY r.id ASC
        """)
        roles = cursor.fetchall()

        cursor.execute("SELECT * FROM sys_permission ORDER BY id")
        permissions = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'code': 0,
            'data': {
                'roles': roles,
                'permissions': permissions
            }
        })
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500


@settings_bp.route('/roles/<int:role_id>/permissions', methods=['PUT'])
@login_required
@permission_required('user:update')
def update_role_permissions(role_id):
    """更新角色权限"""
    try:
        data = request.json or {}
        permission_codes = data.get('permissions', [])

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM sys_role_permission WHERE role_id = %s", (role_id,))

            if permission_codes:
                placeholders = ','.join(['%s'] * len(permission_codes))
                cursor.execute(f"SELECT id, code FROM sys_permission WHERE code IN ({placeholders})", permission_codes)
                perms = cursor.fetchall()
                for p in perms:
                    cursor.execute("INSERT INTO sys_role_permission (role_id, permission_id) VALUES (%s, %s)", (role_id, p['id']))

            conn.commit()
            cursor.close()
        finally:
            conn.close()

        return jsonify({'code': 0, 'msg': '权限更新成功'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': f'权限更新失败: {str(e)}'}), 500


# ===================== 个人信息管理 =====================

@settings_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取当前用户的个人信息"""
    try:
        user_id = g.current_user['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.id, u.username, u.nickname, u.email, u.phone, u.avatar, u.status, u.created_at,
                   GROUP_CONCAT(r.name) as role_names
            FROM sys_user u
            LEFT JOIN sys_user_role ur ON u.id = ur.user_id
            LEFT JOIN sys_role r ON ur.role_id = r.id
            WHERE u.id = %s
            GROUP BY u.id
        """, (user_id,))

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return jsonify({'code': -1, 'msg': '用户不存在'}), 404

        return jsonify({'code': 0, 'data': user})
    except Exception as e:
        logger.error(f"获取个人信息失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@settings_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新当前用户的个人信息"""
    try:
        user_id = g.current_user['user_id']
        data = request.json or {}

        username = data.get('username')
        nickname = data.get('nickname')
        email = data.get('email')
        phone = data.get('phone')
        avatar = data.get('avatar')

        conn = get_db_connection()
        cursor = conn.cursor()

        updates = []
        params = []
        log_parts = []  # 用于记录操作日志的字段=值

        # 如果修改用户名，检查是否已存在
        if username is not None and username.strip():
            cursor.execute("SELECT id FROM sys_user WHERE username = %s AND id != %s", (username, user_id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'code': -1, 'msg': '用户名已存在'}), 400
            updates.append("username = %s")
            params.append(username.strip())
            log_parts.append(f"username={username.strip()}")

        if nickname is not None:
            updates.append("nickname = %s")
            params.append(nickname)
            log_parts.append(f"nickname={nickname}")
        if email is not None:
            updates.append("email = %s")
            params.append(email)
            log_parts.append(f"email={email}")
        if phone is not None:
            updates.append("phone = %s")
            params.append(phone)
            log_parts.append(f"phone={phone}")
        if avatar is not None:
            updates.append("avatar = %s")
            params.append(avatar)
            log_parts.append("avatar=<已更新>")

        if updates:
            params.append(user_id)
            sql = f"UPDATE sys_user SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)

            # 记录操作日志
            cursor.execute("""
                INSERT INTO sys_operation_log (user_id, username, action, module, detail, ip, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, g.current_user['username'], '修改个人信息', 'profile',
                  f"修改了: {', '.join(log_parts)}", request.remote_addr, 1))

            conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'msg': '个人信息更新成功'})
    except Exception as e:
        logger.error(f"更新个人信息失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@settings_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """修改当前用户的密码"""
    try:
        user_id = g.current_user['user_id']
        data = request.json or {}

        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        if not old_password or not new_password or not confirm_password:
            return jsonify({'code': -1, 'msg': '缺少必要参数'}), 400

        if new_password != confirm_password:
            return jsonify({'code': -1, 'msg': '两次输入的密码不一致'}), 400

        if old_password == new_password:
            return jsonify({'code': -1, 'msg': '新密码不能与原密码相同'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 验证旧密码
        old_password_hash = hashlib.sha256(old_password.encode()).hexdigest()
        cursor.execute("SELECT password FROM sys_user WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user or user['password'] != old_password_hash:
            cursor.close()
            conn.close()
            return jsonify({'code': -1, 'msg': '原密码错误'}), 400

        # 更新新密码
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute("UPDATE sys_user SET password = %s WHERE id = %s", (new_password_hash, user_id))

        # 记录操作日志
        cursor.execute("""
            INSERT INTO sys_operation_log (user_id, username, action, module, detail, ip, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, g.current_user['username'], '修改密码', 'profile', '用户修改了自己的密码', request.remote_addr, 1))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'msg': '密码修改成功'})
    except Exception as e:
        logger.error(f"修改密码失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ===================== 操作日志管理 =====================

@settings_bp.route('/operation_logs', methods=['GET'])
@login_required
@permission_required('user:list')
def get_operation_logs():
    """获取操作日志"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        offset = (page - 1) * page_size

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM sys_operation_log")
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT id, user_id, username, action, module, detail, ip, status, created_at
            FROM sys_operation_log
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (page_size, offset))

        logs = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'code': 0,
            'data': {
                'list': logs,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取操作日志失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500
