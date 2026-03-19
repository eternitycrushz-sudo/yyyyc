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
    """更新用户信息"""
    try:
        data = request.json or {}
        nickname = data.get('nickname')
        email = data.get('email')
        phone = data.get('phone')
        status = data.get('status')
        role_code = data.get('role_code')

        conn = get_db_connection()
        cursor = conn.cursor()

        updates = []
        params = []
        if nickname is not None:
            updates.append("nickname = %s")
            params.append(nickname)
        if email is not None:
            updates.append("email = %s")
            params.append(email)
        if phone is not None:
            updates.append("phone = %s")
            params.append(phone)
        if status is not None:
            updates.append("status = %s")
            params.append(status)

        if updates:
            params.append(user_id)
            cursor.execute(f"UPDATE sys_user SET {', '.join(updates)} WHERE id = %s", params)

        # 更新角色
        if role_code:
            cursor.execute("SELECT id FROM sys_role WHERE code = %s", (role_code,))
            role = cursor.fetchone()
            if role:
                cursor.execute("DELETE FROM sys_user_role WHERE user_id = %s", (user_id,))
                cursor.execute("INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)", (user_id, role['id']))

        conn.commit()
        cursor.close()
        conn.close()

        log_operation('更新', '用户管理', f'更新用户ID={user_id}')
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
        log_operation('重置密码', '用户管理', f'重置用户ID={user_id} 密码失败', status=0)
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
        cursor.execute("DELETE FROM sys_user_role WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM sys_user WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()

        log_operation('删除', '用户管理', f'删除用户ID={user_id}')
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        log_operation('删除', '用户管理', f'删除用户ID={user_id} 失败', status=0)
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
