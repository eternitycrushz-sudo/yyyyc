# -*- coding: utf-8 -*-
"""
收藏/关注商品路由
"""

from flask import Blueprint, jsonify, request, g
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required
import logging

logger = logging.getLogger(__name__)

favorites_bp = Blueprint('favorites', __name__)


@favorites_bp.route('/list', methods=['GET'])
@login_required
def get_favorites():
    """获取收藏列表"""
    try:
        user_id = g.current_user['user_id']
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        offset = (page - 1) * page_size

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM user_favorites WHERE user_id = %s", (user_id,))
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT f.id, f.product_id, f.note, f.created_at,
                   g.title, g.cover, g.price, g.cos_fee, g.sales, g.shop_name, g.view_num, g.kol_num
            FROM user_favorites f
            LEFT JOIN goods_list g ON f.product_id = g.product_id
            WHERE f.user_id = %s
            ORDER BY f.created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, page_size, offset))
        items = cursor.fetchall()

        for item in items:
            for key in ['price', 'cos_fee']:
                if item.get(key) is not None:
                    item[key] = float(item[key])

        cursor.close()
        conn.close()

        return jsonify({
            'code': 0,
            'data': {
                'list': items,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取收藏列表失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@favorites_bp.route('/add', methods=['POST'])
@login_required
def add_favorite():
    """添加收藏"""
    try:
        user_id = g.current_user['user_id']
        data = request.json or {}
        product_id = data.get('product_id')
        note = data.get('note', '')

        if not product_id:
            return jsonify({'code': -1, 'msg': '缺少 product_id'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO user_favorites (user_id, product_id, note) VALUES (%s, %s, %s)",
                (user_id, product_id, note)
            )
            conn.commit()
        except Exception as dup:
            if '1062' in str(dup):
                cursor.close()
                conn.close()
                return jsonify({'code': -1, 'msg': '已收藏该商品'})
            raise
        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'msg': '收藏成功'})
    except Exception as e:
        logger.error(f"添加收藏失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@favorites_bp.route('/remove', methods=['POST'])
@login_required
def remove_favorite():
    """取消收藏"""
    try:
        user_id = g.current_user['user_id']
        data = request.json or {}
        product_id = data.get('product_id')

        if not product_id:
            return jsonify({'code': -1, 'msg': '缺少 product_id'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_favorites WHERE user_id = %s AND product_id = %s",
            (user_id, product_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'msg': '已取消收藏'})
    except Exception as e:
        logger.error(f"取消收藏失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@favorites_bp.route('/check', methods=['GET'])
@login_required
def check_favorite():
    """检查是否已收藏"""
    try:
        user_id = g.current_user['user_id']
        product_id = request.args.get('product_id', '')
        if not product_id:
            return jsonify({'code': 0, 'data': {'is_favorited': False}})

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM user_favorites WHERE user_id = %s AND product_id = %s",
            (user_id, product_id)
        )
        is_fav = cursor.fetchone()['cnt'] > 0
        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'data': {'is_favorited': is_fav}})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500
