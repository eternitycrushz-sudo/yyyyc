# -*- coding: utf-8 -*-
"""
数据报告生成路由
"""

from flask import Blueprint, jsonify, request, make_response
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required, permission_required
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

report_bp = Blueprint('report', __name__)


@report_bp.route('/generate', methods=['GET'])
@login_required
@permission_required('data:export')
def generate_report():
    """
    生成数据分析报告（HTML格式）

    参数：
        start_date: 开始日期
        end_date: 结束日期
        format: html (默认) / json
    """
    try:
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        fmt = request.args.get('format', 'html')

        conn = get_db_connection()
        cursor = conn.cursor()

        # 总览
        where_parts = []
        params = []
        if start_date:
            where_parts.append("DATE(created_at) >= %s")
            params.append(start_date)
        if end_date:
            where_parts.append("DATE(created_at) <= %s")
            params.append(end_date)
        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

        cursor.execute(f"SELECT COUNT(*) as total FROM goods_list {where_clause}", params)
        total = cursor.fetchone()['total']

        cursor.execute(f"SELECT AVG(price) as v FROM goods_list {where_clause + ' AND ' if where_clause else ' WHERE '} price > 0", params)
        avg_price = round(float(cursor.fetchone()['v'] or 0), 2)

        cursor.execute(f"SELECT AVG(cos_fee) as v FROM goods_list {where_clause + ' AND ' if where_clause else ' WHERE '} cos_fee > 0", params)
        avg_commission = round(float(cursor.fetchone()['v'] or 0), 2)

        cursor.execute(f"SELECT COUNT(DISTINCT shop_id) as v FROM goods_list {where_clause}", params)
        total_shops = cursor.fetchone()['v']

        # Top 10 商品（按销量）
        cursor.execute(f"""
            SELECT title, product_id, price, sales, cos_fee, kol_num, view_num, shop_name
            FROM goods_list {where_clause}
            ORDER BY sales DESC LIMIT 10
        """, params)
        top_goods = cursor.fetchall()
        for g in top_goods:
            for k in ['price', 'cos_fee']:
                if g.get(k): g[k] = float(g[k])

        # 价格分布
        cursor.execute(f"""
            SELECT
                SUM(price < 10) as u10,
                SUM(price >= 10 AND price < 50) as p10_50,
                SUM(price >= 50 AND price < 100) as p50_100,
                SUM(price >= 100) as over100
            FROM goods_list {where_clause + ' AND ' if where_clause else ' WHERE '} price > 0
        """, params)
        price_dist = cursor.fetchone()

        # Top 店铺
        cursor.execute(f"""
            SELECT shop_name, COUNT(*) as cnt, ROUND(AVG(price),2) as avg_p
            FROM goods_list {where_clause + ' AND ' if where_clause else ' WHERE '} shop_name IS NOT NULL AND shop_name != ''
            GROUP BY shop_name ORDER BY cnt DESC LIMIT 10
        """, params)
        top_shops = cursor.fetchall()
        for s in top_shops:
            if s.get('avg_p'): s['avg_p'] = float(s['avg_p'])

        cursor.close()
        conn.close()

        report_data = {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_range': f"{start_date or '全部'} ~ {end_date or '全部'}",
            'overview': {
                'total_goods': total,
                'avg_price': avg_price,
                'avg_commission': avg_commission,
                'total_shops': total_shops,
            },
            'top_goods': top_goods,
            'price_distribution': {
                '10元以下': int(price_dist['u10'] or 0),
                '10-50元': int(price_dist['p10_50'] or 0),
                '50-100元': int(price_dist['p50_100'] or 0),
                '100元以上': int(price_dist['over100'] or 0),
            },
            'top_shops': top_shops,
        }

        if fmt == 'json':
            return jsonify({'code': 0, 'data': report_data})

        # 生成 HTML 报告
        html = _build_html_report(report_data)
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        return response

    except Exception as e:
        logger.error(f"生成报告失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


def _build_html_report(data):
    top_rows = ''
    for i, g in enumerate(data['top_goods'], 1):
        top_rows += f"""<tr>
            <td>{i}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{g['title']}</td>
            <td>{g['shop_name'] or '-'}</td>
            <td>&yen;{g['price']}</td>
            <td>{g['sales'] or 0}</td>
            <td>&yen;{g['cos_fee']}</td>
            <td>{g['kol_num'] or 0}</td>
        </tr>"""

    shop_rows = ''
    for s in data['top_shops']:
        shop_rows += f"<tr><td>{s['shop_name']}</td><td>{s['cnt']}</td><td>&yen;{s['avg_p']}</td></tr>"

    price_items = ''
    for k, v in data['price_distribution'].items():
        price_items += f"<li>{k}: <strong>{v}</strong> 件</li>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>数据分析报告 - {data['date_range']}</title>
<style>
body {{ font-family: -apple-system, 'Noto Sans SC', sans-serif; max-width: 900px; margin: 0 auto; padding: 40px 20px; color: #333; background: #f8f9fa; }}
h1 {{ color: #0d7377; border-bottom: 3px solid #13c8ec; padding-bottom: 10px; }}
h2 {{ color: #1a3035; margin-top: 30px; }}
.card {{ background: white; border-radius: 12px; padding: 20px; margin: 16px 0; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
.stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
.stat-item {{ text-align: center; }}
.stat-item .val {{ font-size: 28px; font-weight: bold; color: #0d7377; }}
.stat-item .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 14px; }}
th {{ background: #f0f8f8; color: #1a3035; }}
tr:hover {{ background: #f8fffe; }}
.footer {{ text-align: center; color: #aaa; margin-top: 40px; font-size: 13px; }}
</style></head><body>
<h1>抖音电商数据分析报告</h1>
<p style="color:#888">报告时间: {data['generated_at']} | 数据范围: {data['date_range']}</p>

<h2>数据概览</h2>
<div class="card">
<div class="stats">
    <div class="stat-item"><div class="val">{data['overview']['total_goods']}</div><div class="label">商品总数</div></div>
    <div class="stat-item"><div class="val">&yen;{data['overview']['avg_price']}</div><div class="label">平均价格</div></div>
    <div class="stat-item"><div class="val">&yen;{data['overview']['avg_commission']}</div><div class="label">平均佣金</div></div>
    <div class="stat-item"><div class="val">{data['overview']['total_shops']}</div><div class="label">店铺总数</div></div>
</div></div>

<h2>价格分布</h2>
<div class="card"><ul>{price_items}</ul></div>

<h2>Top 10 热销商品</h2>
<div class="card"><table>
<thead><tr><th>#</th><th>商品名称</th><th>店铺</th><th>价格</th><th>销量</th><th>佣金</th><th>达人数</th></tr></thead>
<tbody>{top_rows}</tbody>
</table></div>

<h2>Top 店铺</h2>
<div class="card"><table>
<thead><tr><th>店铺名称</th><th>商品数</th><th>均价</th></tr></thead>
<tbody>{shop_rows}</tbody>
</table></div>

<div class="footer">Douyin E-commerce Analysis System | Auto-generated Report</div>
</body></html>"""
