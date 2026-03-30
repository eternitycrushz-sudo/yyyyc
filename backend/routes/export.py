# -*- coding: utf-8 -*-
"""
数据导出路由 - 支持 CSV 和 JSON 格式导出
"""

from flask import Blueprint, request, jsonify, Response
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required, permission_required
import csv
import io
import json
import logging
from datetime import datetime
from crawler.workers.cleaners.utils import parse_range, parse_number

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__)


def _build_goods_query(args):
    """构建商品查询SQL和参数（复用时间过滤逻辑）"""
    where_parts = []
    params = []

    # 时间过滤
    start_date = args.get('start_date', '')
    end_date = args.get('end_date', '')
    if start_date:
        where_parts.append("DATE(created_at) >= %s")
        params.append(start_date)
    if end_date:
        where_parts.append("DATE(created_at) <= %s")
        params.append(end_date)

    # 分类过滤
    category = args.get('category', '')
    if category:
        where_parts.append("JSON_CONTAINS(labels, JSON_OBJECT('id', 'category', 'name', %s))")
        params.append(category)

    # 关键词搜索
    keyword = args.get('keyword', '')
    if keyword:
        where_parts.append("(product_id = %s OR title LIKE %s)")
        params.extend([keyword, f'%{keyword}%'])

    where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

    # 排序
    allowed_sort = {'created_at', 'price', 'cos_fee', 'view_num'}
    sort_by = args.get('sort_by', 'created_at')
    if sort_by not in allowed_sort:
        sort_by = 'created_at'
    order = 'ASC' if args.get('order', 'desc').upper() == 'ASC' else 'DESC'
    order_clause = f" ORDER BY {sort_by} {order}"

    return where_clause, params, order_clause


def _clean_range_value(value):
    """将范围字符串（如 '750-1000'、'2.5w-5w'）转为中间值，无法解析返回原值"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    min_val, max_val = parse_range(value)
    if min_val is not None and max_val is not None:
        return (min_val + max_val) / 2
    num = parse_number(value)
    return num if num is not None else value


@export_bp.route('/goods/csv', methods=['GET'])
@login_required
@permission_required('data:export')
def export_goods_csv():
    """
    导出商品数据为 CSV

    参数：
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        category: 分类筛选
        keyword: 关键词搜索
        limit: 最大导出条数，默认1000
    """
    try:
        limit = min(int(request.args.get('limit', 1000)), 10000)
        where_clause, params, order_clause = _build_goods_query(request.args)

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = f"""
        SELECT product_id, title, price, coupon_price, cos_fee, cos_ratio,
               shop_name, view_num, order_num, sales, sales_24, sales_7day,
               kol_num, platform, created_at, updated_at
        FROM goods_list
        {where_clause}
        {order_clause}
        LIMIT %s
        """
        params.append(limit)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # 生成 CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # 表头
        headers = ['商品ID', '标题', '价格', '券后价', '佣金', '佣金比例',
                    '店铺', '浏览量', '订单数', '总销量', '24h销量', '7日销量',
                    '达人数', '平台', '创建时间', '更新时间']
        writer.writerow(headers)

        # 数据行（对范围字符串字段做数据清洗，转为数值中间值）
        range_fields = ('order_num', 'sales', 'sales_24', 'sales_7day', 'kol_num')
        for row in rows:
            writer.writerow([
                row['product_id'], row['title'],
                row['price'], row['coupon_price'],
                row['cos_fee'], row['cos_ratio'],
                row['shop_name'], row['view_num'],
                _clean_range_value(row['order_num']),
                _clean_range_value(row['sales']),
                _clean_range_value(row['sales_24']),
                _clean_range_value(row['sales_7day']),
                _clean_range_value(row['kol_num']),
                row['platform'],
                str(row['created_at']), str(row['updated_at'])
            ])

        csv_data = output.getvalue()
        output.close()

        # 添加 BOM 头以支持 Excel 中文显示
        bom = '\ufeff'
        filename = f"goods_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return Response(
            bom + csv_data,
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )

    except Exception as e:
        logger.error(f"导出CSV失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500


@export_bp.route('/goods/json', methods=['GET'])
@login_required
@permission_required('data:export')
def export_goods_json():
    """
    导出商品数据为 JSON

    参数同 CSV 导出
    """
    try:
        limit = min(int(request.args.get('limit', 1000)), 10000)
        where_clause, params, order_clause = _build_goods_query(request.args)

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = f"""
        SELECT product_id, title, price, coupon_price, cos_fee, cos_ratio,
               shop_name, view_num, order_num, sales, sales_24, sales_7day,
               kol_num, platform, created_at, updated_at
        FROM goods_list
        {where_clause}
        {order_clause}
        LIMIT %s
        """
        params.append(limit)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # 序列化日期字段，并对范围字符串字段做数据清洗
        for row in rows:
            for key in ['created_at', 'updated_at']:
                if row[key]:
                    row[key] = str(row[key])
            for key in ['price', 'coupon_price', 'cos_fee', 'cos_ratio']:
                if row[key] is not None:
                    row[key] = float(row[key])
            for key in ['order_num', 'sales', 'sales_24', 'sales_7day', 'kol_num']:
                row[key] = _clean_range_value(row[key])

        filename = f"goods_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_data = json.dumps(rows, ensure_ascii=False, indent=2)

        return Response(
            json_data,
            mimetype='application/json; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'application/json; charset=utf-8'
            }
        )

    except Exception as e:
        logger.error(f"导出JSON失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500


@export_bp.route('/analysis/csv/<product_id>', methods=['GET'])
@login_required
@permission_required('data:export')
def export_analysis_csv(product_id):
    """
    导出单个商品的分析数据为 CSV

    参数：
        type: 数据类型 trend/kol/video/live，默认 trend
    """
    try:
        data_type = request.args.get('type', 'trend')

        conn = get_db_connection()
        cursor = conn.cursor()

        if data_type == 'trend':
            cursor.execute("""
                SELECT date, sales_count, sales_amount, video_count, live_count, user_count
                FROM analysis_goods_trend
                WHERE goods_id = %s ORDER BY date ASC
            """, (product_id,))
            headers = ['日期', '销量', '销售额', '视频数', '直播数', '达人数']
        elif data_type == 'video':
            cursor.execute("""
                SELECT date, video_count, play_count, sales_count, like_count, comment_count
                FROM analysis_video_sales
                WHERE goods_id = %s ORDER BY date ASC
            """, (product_id,))
            headers = ['日期', '视频数', '播放量', '销量', '点赞数', '评论数']
        elif data_type == 'live':
            cursor.execute("""
                SELECT date, live_count, sales_count, sales_amount, viewer_count
                FROM analysis_live_trend
                WHERE goods_id = %s ORDER BY date ASC
            """, (product_id,))
            headers = ['日期', '直播数', '销量', '销售额', '观看人数']
        elif data_type == 'kol':
            cursor.execute("""
                SELECT nickname, sales_count, follower_count
                FROM analysis_user_top
                WHERE goods_id = %s ORDER BY `rank` ASC
            """, (product_id,))
            headers = ['达人', '销量', '粉丝数']
        else:
            return jsonify({'success': False, 'message': '不支持的数据类型'}), 400

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return jsonify({'success': False, 'message': '暂无数据'}), 404

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        for row in rows:
            writer.writerow([str(v) if v is not None else '' for v in row.values()])

        csv_data = output.getvalue()
        output.close()

        filename = f"{product_id}_{data_type}_{datetime.now().strftime('%Y%m%d')}.csv"

        return Response(
            '\ufeff' + csv_data,
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )

    except Exception as e:
        logger.error(f"导出分析CSV失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
