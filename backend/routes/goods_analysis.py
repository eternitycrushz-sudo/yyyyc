# -*- coding: utf-8 -*-
"""
商品分析数据路由
"""

from flask import Blueprint, jsonify, request
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required
import logging
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

goods_analysis_bp = Blueprint('goods_analysis', __name__)


@goods_analysis_bp.route('/trend/<product_id>', methods=['GET'])
@login_required
def get_goods_trend(product_id):
    """获取商品趋势数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 从数据库查询趋势数据
        cursor.execute("""
            SELECT date, sales_count, sales_amount, video_count, live_count, user_count
            FROM analysis_goods_trend
            WHERE goods_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
            ORDER BY date ASC
        """, (product_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not rows:
            return jsonify({'code': -1, 'msg': '暂无趋势数据'}), 404
        
        # 格式化数据
        dates = []
        sales_data = []
        amount_data = []
        video_count_data = []
        live_count_data = []
        user_count_data = []
        
        for row in rows:
            dates.append(str(row['date'])[5:])  # 只保留月-日
            sales_data.append(int(row['sales_count']) if row['sales_count'] else 0)
            amount_data.append(float(row['sales_amount']) if row['sales_amount'] else 0)
            video_count_data.append(int(row['video_count']) if row['video_count'] else 0)
            live_count_data.append(int(row['live_count']) if row['live_count'] else 0)
            user_count_data.append(int(row['user_count']) if row['user_count'] else 0)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'dates': dates,
                'sales': sales_data,
                'amount': amount_data,
                'video_count': video_count_data,
                'live_count': live_count_data,
                'user_count': user_count_data
            }
        })
        
    except Exception as e:
        logger.error(f"获取商品趋势失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': f'获取趋势数据失败: {str(e)}'}), 500


@goods_analysis_bp.route('/kol/<product_id>', methods=['GET'])
@login_required
def get_goods_kol(product_id):
    """获取商品达人数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 从趋势数据中获取每日达人数
        cursor.execute("""
            SELECT date, user_count, video_count
            FROM analysis_goods_trend
            WHERE goods_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
            ORDER BY date ASC
        """, (product_id,))
        
        trend_rows = cursor.fetchall()
        
        # 获取TOP达人数据
        cursor.execute("""
            SELECT nickname, sales_count, follower_count
            FROM analysis_user_top
            WHERE goods_id = %s
            ORDER BY `rank` ASC
            LIMIT 10
        """, (product_id,))
        
        top_rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not trend_rows:
            return jsonify({'code': -1, 'msg': '暂无达人数据'}), 404
        
        # 格式化趋势数据
        dates = []
        daily_kol_data = []
        new_kol_data = []
        
        for row in trend_rows:
            dates.append(str(row['date'])[5:])
            daily_kol_data.append(int(row['video_count']) if row['video_count'] else 0)
            new_kol_data.append(int(row['user_count']) if row['user_count'] else 0)
        
        # 格式化TOP达人数据
        top_names = []
        top_sales = []
        top_followers = []
        
        for row in top_rows:
            top_names.append(row['nickname'] if row['nickname'] else '达人')
            top_sales.append(int(row['sales_count']) if row['sales_count'] else 0)
            top_followers.append(int(row['follower_count']) if row['follower_count'] else 0)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'dates': dates,
                'daily_kol': daily_kol_data,
                'new_kol': new_kol_data,
                'top_names': top_names,
                'top_sales': top_sales,
                'top_followers': top_followers
            }
        })
        
    except Exception as e:
        logger.error(f"获取达人数据失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': f'获取达人数据失败: {str(e)}'}), 500


@goods_analysis_bp.route('/video/<product_id>', methods=['GET'])
@login_required
def get_goods_video(product_id):
    """获取商品视频数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 从数据库查询视频数据
        cursor.execute("""
            SELECT date, video_count, play_count, sales_count, like_count, comment_count
            FROM analysis_video_sales
            WHERE goods_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
            ORDER BY date ASC
        """, (product_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not rows:
            return jsonify({'code': -1, 'msg': '暂无视频数据'}), 404
        
        # 格式化数据
        dates = []
        video_count_data = []
        video_views_data = []
        video_sales_data = []
        like_data = []
        comment_data = []
        
        for row in rows:
            dates.append(str(row['date'])[5:])
            video_count_data.append(int(row['video_count']) if row['video_count'] else 0)
            video_views_data.append(int(row['play_count']) if row['play_count'] else 0)
            video_sales_data.append(int(row['sales_count']) if row['sales_count'] else 0)
            like_data.append(int(row['like_count']) if row['like_count'] else 0)
            comment_data.append(int(row['comment_count']) if row['comment_count'] else 0)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'dates': dates,
                'video_count': video_count_data,
                'video_views': video_views_data,
                'video_sales': video_sales_data,
                'like_count': like_data,
                'comment_count': comment_data
            }
        })
        
    except Exception as e:
        logger.error(f"获取视频数据失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': f'获取视频数据失败: {str(e)}'}), 500


@goods_analysis_bp.route('/live/<product_id>', methods=['GET'])
@login_required
def get_goods_live(product_id):
    """获取商品直播数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 从数据库查询直播数据
        cursor.execute("""
            SELECT date, live_count, sales_count, sales_amount, viewer_count
            FROM analysis_live_trend
            WHERE goods_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
            ORDER BY date ASC
        """, (product_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not rows:
            return jsonify({'code': -1, 'msg': '暂无直播数据'}), 404
        
        # 格式化数据
        dates = []
        live_count_data = []
        live_sales_data = []
        live_amount_data = []
        live_viewer_data = []
        
        for row in rows:
            dates.append(str(row['date'])[5:])
            live_count_data.append(int(row['live_count']) if row['live_count'] else 0)
            live_sales_data.append(int(row['sales_count']) if row['sales_count'] else 0)
            live_amount_data.append(float(row['sales_amount']) if row['sales_amount'] else 0)
            live_viewer_data.append(int(row['viewer_count']) if row['viewer_count'] else 0)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'dates': dates,
                'live_count': live_count_data,
                'live_sales': live_sales_data,
                'live_amount': live_amount_data,
                'live_viewer': live_viewer_data
            }
        })
        
    except Exception as e:
        logger.error(f"获取直播数据失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': f'获取直播数据失败: {str(e)}'}), 500
