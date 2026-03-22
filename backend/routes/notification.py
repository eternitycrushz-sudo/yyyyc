# -*- coding: utf-8 -*-
"""
通知/预警路由
"""

from flask import Blueprint, jsonify, request, g
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required
import logging

logger = logging.getLogger(__name__)

notification_bp = Blueprint('notification', __name__)


def create_notification(title, content='', ntype='info', source='', user_id=None):
    """创建通知（工具函数）"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO sys_notification (user_id, type, title, content, source) VALUES (%s, %s, %s, %s, %s)",
                (user_id, ntype, title, content, source)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"创建通知失败: {e}")


@notification_bp.route('/list', methods=['GET'])
@login_required
def get_notifications():
    """获取通知列表"""
    try:
        user_id = g.current_user['user_id']
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        unread_only = request.args.get('unread_only', '') == '1'
        offset = (page - 1) * page_size

        conn = get_db_connection()
        cursor = conn.cursor()

        where = "WHERE (user_id = %s OR user_id IS NULL)"
        params = [user_id]
        if unread_only:
            where += " AND is_read = 0"

        cursor.execute(f"SELECT COUNT(*) as total FROM sys_notification {where}", params)
        total = cursor.fetchone()['total']

        cursor.execute(
            f"SELECT * FROM sys_notification {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        items = cursor.fetchall()

        # 未读数
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM sys_notification WHERE (user_id = %s OR user_id IS NULL) AND is_read = 0",
            (user_id,)
        )
        unread_count = cursor.fetchone()['cnt']

        cursor.close()
        conn.close()

        return jsonify({
            'code': 0,
            'data': {
                'list': items,
                'total': total,
                'unread_count': unread_count,
                'page': page,
                'page_size': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取通知失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@notification_bp.route('/read', methods=['POST'])
@login_required
def mark_read():
    """标记已读"""
    try:
        data = request.json or {}
        nid = data.get('id')
        mark_all = data.get('all', False)
        user_id = g.current_user['user_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        if mark_all:
            cursor.execute(
                "UPDATE sys_notification SET is_read = 1 WHERE (user_id = %s OR user_id IS NULL) AND is_read = 0",
                (user_id,)
            )
        elif nid:
            cursor.execute("UPDATE sys_notification SET is_read = 1 WHERE id = %s", (nid,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'msg': '操作成功'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500


@notification_bp.route('/unread_count', methods=['GET'])
@login_required
def get_unread_count():
    """获取未读通知数"""
    try:
        user_id = g.current_user['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM sys_notification WHERE (user_id = %s OR user_id IS NULL) AND is_read = 0",
            (user_id,)
        )
        cnt = cursor.fetchone()['cnt']
        cursor.close()
        conn.close()
        return jsonify({'code': 0, 'data': {'count': cnt}})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500
