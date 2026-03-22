# -*- coding: utf-8 -*-
"""
商品对比分析路由
"""

from flask import Blueprint, jsonify, request
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required
import logging

logger = logging.getLogger(__name__)

compare_bp = Blueprint('compare', __name__)


@compare_bp.route('/goods', methods=['POST'])
@login_required
def compare_goods():
    """
    对比多个商品

    请求：
    {
        "product_ids": ["id1", "id2", "id3"]
    }
    """
    try:
        data = request.json or {}
        product_ids = data.get('product_ids', [])

        if len(product_ids) < 2:
            return jsonify({'code': -1, 'msg': '至少选择2个商品进行对比'}), 400
        if len(product_ids) > 6:
            return jsonify({'code': -1, 'msg': '最多支持6个商品同时对比'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        placeholders = ','.join(['%s'] * len(product_ids))
        cursor.execute(f"""
            SELECT product_id, title, cover, price, cos_fee, cos_ratio,
                   kol_cos_fee, kol_cos_ratio, kol_num, view_num, order_num,
                   sales, sales_7day, sales_24, shop_name, labels
            FROM goods_list
            WHERE product_id IN ({placeholders})
        """, product_ids)

        goods = cursor.fetchall()

        # 获取趋势数据
        for item in goods:
            for key in ['price', 'cos_fee', 'cos_ratio', 'kol_cos_fee', 'kol_cos_ratio']:
                if item.get(key) is not None:
                    item[key] = float(item[key])
            # Convert string number fields
            for key in ['view_num', 'order_num', 'kol_num', 'sales', 'sales_7day', 'sales_24']:
                val = item.get(key)
                if val is not None:
                    try:
                        val_str = str(val).replace('+', '').strip()
                        if val_str.lower().endswith('w'):
                            item[key] = int(float(val_str[:-1]) * 10000)
                        else:
                            item[key] = int(float(val_str))
                    except:
                        item[key] = 0

            cursor.execute("""
                SELECT date, sales_count, sales_amount, video_count, live_count, user_count
                FROM analysis_goods_trend
                WHERE goods_id = %s
                ORDER BY date ASC
                LIMIT 30
            """, (item['product_id'],))
            item['trend'] = cursor.fetchall()
            for t in item['trend']:
                if t.get('sales_amount'):
                    t['sales_amount'] = float(t['sales_amount'])

        cursor.close()
        conn.close()

        # 计算对比维度的最大/最小值
        if goods:
            dimensions = ['price', 'cos_fee', 'kol_num', 'view_num', 'sales']
            stats = {}
            for dim in dimensions:
                values = [g.get(dim, 0) or 0 for g in goods]
                stats[dim] = {
                    'max': max(values),
                    'min': min(values),
                    'avg': round(sum(values) / len(values), 2)
                }
        else:
            stats = {}

        return jsonify({
            'code': 0,
            'data': {
                'goods': goods,
                'stats': stats
            }
        })

    except Exception as e:
        logger.error(f"商品对比失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500
