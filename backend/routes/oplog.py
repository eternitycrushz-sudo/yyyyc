# -*- coding: utf-8 -*-
"""
操作日志路由 + 日志记录工具
"""

from flask import Blueprint, jsonify, request, g
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required, permission_required
import logging
import json

logger = logging.getLogger(__name__)

oplog_bp = Blueprint('oplog', __name__)


def log_operation(action, module, detail='', status=1, user_id=None, username=None):
    """记录操作日志（工具函数，供其他模块调用）"""
    try:
        if user_id is None and hasattr(g, 'current_user'):
            user_id = g.current_user.get('user_id')
            username = g.current_user.get('username')
        ip = request.remote_addr if request else ''
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO sys_operation_log (user_id, username, action, module, detail, ip, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (user_id, username, action, module, detail, ip, status)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"记录操作日志失败: {e}")


@oplog_bp.route('/list', methods=['GET'])
@login_required
@permission_required('user:list')
def get_logs():
    """获取操作日志列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        action = request.args.get('action', '')
        module = request.args.get('module', '')
        username = request.args.get('username', '')
        offset = (page - 1) * page_size

        where_parts = []
        params = []
        if action:
            where_parts.append("action = %s")
            params.append(action)
        if module:
            where_parts.append("module = %s")
            params.append(module)
        if username:
            where_parts.append("username LIKE %s")
            params.append(f'%{username}%')
        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as total FROM sys_operation_log {where_clause}", params)
        total = cursor.fetchone()['total']

        cursor.execute(
            f"SELECT * FROM sys_operation_log {where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
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
