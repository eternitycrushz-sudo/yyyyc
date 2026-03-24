# -*- coding: utf-8 -*-
"""
商品对比分析路由
"""

from flask import Blueprint, jsonify, request
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required
import logging
from backend.routes.goods_analysis import _ensure_product_has_data

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
            SELECT product_id, goods_id, title, cover, price, cos_fee, cos_ratio,
                   kol_cos_fee, kol_cos_ratio, kol_num, view_num, order_num,
                   sales, sales_7day, sales_24, shop_name, labels
            FROM goods_list
            WHERE product_id IN ({placeholders})
        """, product_ids)

        goods = cursor.fetchall()

        # 确保所有商品都有分析数据（会自动生成缺失的数据）
        for item in goods:
            _ensure_product_has_data(cursor, conn, item['product_id'])

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
                        # 处理范围值 "10w-25w" → 取前半部分
                        if '-' in val_str and val_str[0].isdigit():
                            val_str = val_str.split('-')[0]

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
            """, (item['goods_id'],))
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
