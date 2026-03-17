# -*- coding: utf-8 -*-
"""
仪表盘路由 - 综合数据统计和图表接口
"""

from flask import Blueprint, jsonify, request
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/overview', methods=['GET'])
@login_required
def get_overview():
    """
    仪表盘概览数据

    返回：商品总数、今日新增、平均价格、平均佣金、总销量、总达人数
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 商品总数
        cursor.execute("SELECT COUNT(*) as total FROM goods_list")
        total_goods = cursor.fetchone()['total']

        # 今日新增
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM goods_list
            WHERE DATE(created_at) = CURDATE()
        """)
        today_count = cursor.fetchone()['cnt']

        # 昨日新增（用于计算增长率）
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM goods_list
            WHERE DATE(created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
        """)
        yesterday_count = cursor.fetchone()['cnt']

        # 平均价格
        cursor.execute("SELECT AVG(price) as val FROM goods_list WHERE price > 0")
        avg_price = cursor.fetchone()['val'] or 0

        # 平均佣金
        cursor.execute("SELECT AVG(cos_fee) as val FROM goods_list WHERE cos_fee > 0")
        avg_commission = cursor.fetchone()['val'] or 0

        # 店铺总数
        cursor.execute("SELECT COUNT(DISTINCT shop_id) as cnt FROM goods_list WHERE shop_id IS NOT NULL")
        total_shops = cursor.fetchone()['cnt']

        cursor.close()
        conn.close()

        return jsonify({
            'code': 0,
            'data': {
                'total_goods': total_goods,
                'today_count': today_count,
                'yesterday_count': yesterday_count,
                'avg_price': round(float(avg_price), 2),
                'avg_commission': round(float(avg_commission), 2),
                'total_shops': total_shops,
            }
        })

    except Exception as e:
        logger.error(f"获取概览数据失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@dashboard_bp.route('/price_distribution', methods=['GET'])
@login_required
def get_price_distribution():
    """
    价格分布统计

    返回各价格区间的商品数量
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                SUM(price < 10) as 'under_10',
                SUM(price >= 10 AND price < 50) as 'p10_50',
                SUM(price >= 50 AND price < 100) as 'p50_100',
                SUM(price >= 100 AND price < 200) as 'p100_200',
                SUM(price >= 200 AND price < 500) as 'p200_500',
                SUM(price >= 500) as 'over_500'
            FROM goods_list WHERE price > 0
        """)
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        data = [
            {'name': '10元以下', 'value': int(row['under_10'] or 0)},
            {'name': '10-50元', 'value': int(row['p10_50'] or 0)},
            {'name': '50-100元', 'value': int(row['p50_100'] or 0)},
            {'name': '100-200元', 'value': int(row['p100_200'] or 0)},
            {'name': '200-500元', 'value': int(row['p200_500'] or 0)},
            {'name': '500元以上', 'value': int(row['over_500'] or 0)},
        ]

        return jsonify({'code': 0, 'data': data})

    except Exception as e:
        logger.error(f"获取价格分布失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@dashboard_bp.route('/daily_trend', methods=['GET'])
@login_required
def get_daily_trend():
    """
    每日新增商品趋势（最近30天）

    参数：
        days: 天数，默认30
    """
    try:
        days = min(int(request.args.get('days', 30)), 90)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM goods_list
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """, (days,))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        dates = [str(r['date']) for r in rows]
        counts = [r['count'] for r in rows]

        return jsonify({
            'code': 0,
            'data': {
                'dates': dates,
                'counts': counts
            }
        })

    except Exception as e:
        logger.error(f"获取每日趋势失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@dashboard_bp.route('/top_shops', methods=['GET'])
@login_required
def get_top_shops():
    """
    商品数量 TOP 店铺

    参数：
        limit: 数量，默认10
    """
    try:
        limit = min(int(request.args.get('limit', 10)), 50)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT shop_name, shop_id, COUNT(*) as goods_count,
                   ROUND(AVG(price), 2) as avg_price
            FROM goods_list
            WHERE shop_name IS NOT NULL AND shop_name != ''
            GROUP BY shop_id, shop_name
            ORDER BY goods_count DESC
            LIMIT %s
        """, (limit,))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        for row in rows:
            if row['avg_price'] is not None:
                row['avg_price'] = float(row['avg_price'])

        return jsonify({'code': 0, 'data': rows})

    except Exception as e:
        logger.error(f"获取TOP店铺失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@dashboard_bp.route('/commission_ranking', methods=['GET'])
@login_required
def get_commission_ranking():
    """
    佣金排行榜

    参数：
        limit: 数量，默认10
    """
    try:
        limit = min(int(request.args.get('limit', 10)), 50)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT product_id, title, price, cos_fee, cos_ratio, shop_name
            FROM goods_list
            WHERE cos_fee > 0
            ORDER BY cos_fee DESC
            LIMIT %s
        """, (limit,))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        for row in rows:
            for key in ['price', 'cos_fee', 'cos_ratio']:
                if row[key] is not None:
                    row[key] = float(row[key])

        return jsonify({'code': 0, 'data': rows})

    except Exception as e:
        logger.error(f"获取佣金排行失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


@dashboard_bp.route('/category_stats', methods=['GET'])
@login_required
def get_category_stats():
    """
    分类统计（基于 labels 字段的粗略统计）
    """
    try:
        categories = ['饰品配件', '家居日用', '食品饮料', '服饰鞋包',
                       '美妆个护', '数码家电', '母婴用品', '运动户外']

        conn = get_db_connection()
        cursor = conn.cursor()

        result = []
        for cat in categories:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM goods_list WHERE category_name = %s",
                (cat,)
            )
            count = cursor.fetchone()['cnt']
            if count > 0:
                result.append({'name': cat, 'value': count})

        cursor.close()
        conn.close()

        return jsonify({'code': 0, 'data': result})

    except Exception as e:
        logger.error(f"获取分类统计失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500
