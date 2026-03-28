# -*- coding: utf-8 -*-
"""
商品分析数据路由
"""

from flask import Blueprint, jsonify, request
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required, permission_required
import logging
from datetime import datetime, timedelta
import random
from backend.utils.mock_data import generate_mock_data_for_product

logger = logging.getLogger(__name__)

goods_analysis_bp = Blueprint('goods_analysis', __name__)


def _get_date_range_for_product(cursor, table_name, goods_id):
    """获取某个商品在指定表中的日期范围"""
    try:
        cursor.execute(f"""
            SELECT MIN(date) as start_date, MAX(date) as end_date
            FROM {table_name}
            WHERE goods_id = %s
        """, (goods_id,))
        result = cursor.fetchone()
        if result and result.get('start_date'):
            return result['start_date'], result['end_date']
    except:
        pass
    return None, None


def _ensure_product_has_data(cursor, conn, goods_id):
    """确保商品有分析数据，如果没有则生成模拟数据"""
    try:
        # 检查是否需要生成数据（检查多个表）
        tables_to_check = [
            'analysis_goods_trend',
            'analysis_live_trend',
            'analysis_video_sales',
            'analysis_kol_trend'
        ]

        needs_generation = False
        for table in tables_to_check:
            cursor.execute(f"""
                SELECT COUNT(*) as cnt FROM {table}
                WHERE goods_id = %s
            """, (goods_id,))
            result = cursor.fetchone()
            if not result or result.get('cnt', 0) == 0:
                needs_generation = True
                logger.info(f"[数据检查] 商品{goods_id}在{table}表中没有数据")
                break

        if needs_generation:
            # 获取商品价格
            cursor.execute("SELECT price FROM goods_list WHERE product_id = %s", (goods_id,))
            product = cursor.fetchone()
            price = float(product['price']) if product and product.get('price') else 10.0

            # 生成30天的模拟数据
            logger.info(f"[数据生成] 为商品 {goods_id} (价格 ¥{price}) 生成模拟分析数据...")
            try:
                generate_mock_data_for_product(conn, goods_id, price, days=30)
                logger.info(f"[数据生成] ✓ 为商品 {goods_id} 生成了模拟分析数据")
            except Exception as gen_error:
                logger.error(f"[数据生成] 生成失败: {gen_error}", exc_info=True)
                raise

    except Exception as e:
        logger.warning(f"[数据检查] 执行时出错: {e}", exc_info=True)


def _get_product_analysis_data(cursor, table_name, date_column, value_columns, goods_id, days=30):
    """
    获取产品分析数据，取最近的数据并将日期偏移到以今天为终点。
    确保图表始终显示到当前系统日期。

    Returns: (rows, actual_date_range) - rows为数据行, actual_date_range为(start_date, end_date)
    """
    today = datetime.now().date()

    # 获取该商品最近的数据（最多取 days 条）
    cursor.execute(f"""
        SELECT {date_column}, {', '.join(value_columns)}
        FROM {table_name}
        WHERE goods_id = %s
        ORDER BY {date_column} DESC
        LIMIT {days}
    """, (goods_id,))
    rows = cursor.fetchall()
    rows = list(reversed(rows)) if rows else []

    # 将日期偏移到以今天为终点
    if rows:
        def _to_date(val):
            """将各种日期格式统一转为 datetime.date"""
            if isinstance(val, datetime):
                return val.date()
            if hasattr(val, 'date') and callable(val.date):
                return val.date()
            if isinstance(val, str):
                return datetime.strptime(val[:10], '%Y-%m-%d').date()
            return val  # already date

        old_max_date = _to_date(rows[-1][date_column])
        offset = today - old_max_date
        if offset.days != 0:
            for row in rows:
                row[date_column] = _to_date(row[date_column]) + offset

    if rows:
        actual_start = today - timedelta(days=len(rows) - 1)
        actual_end = today
    else:
        actual_start = actual_end = None

    return rows, (actual_start, actual_end)


@goods_analysis_bp.route('/trend/<product_id>', methods=['GET'])
@login_required
@permission_required('data:view')
def get_goods_trend(product_id):
    """获取商品趋势数据 - 最近30天的数据，如果没有则获取最新可用数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 确保商品有分析数据
        _ensure_product_has_data(cursor, conn, product_id)

        # 获取数据（优先30天，回退到最新可用）
        rows, (actual_start_date, actual_end_date) = _get_product_analysis_data(
            cursor,
            'analysis_goods_trend',
            'date',
            ['sales_count', 'sales_amount', 'video_count', 'live_count', 'user_count'],
            product_id
        )

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

        logger.info(f"[趋势] 返回数据: {len(rows)} 条记录，日期范围: {actual_start_date} 到 {actual_end_date}")

        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'dates': dates,
                'sales': sales_data,
                'amount': amount_data,
                'video_count': video_count_data,
                'live_count': live_count_data,
                'user_count': user_count_data,
                'date_range': {
                    'start': str(actual_start_date),
                    'end': str(actual_end_date)
                }
            }
        })

    except Exception as e:
        logger.error(f"获取商品趋势失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': f'获取趋势数据失败: {str(e)}'}), 500


@goods_analysis_bp.route('/kol/<product_id>', methods=['GET'])
@login_required
@permission_required('data:view')
def get_goods_kol(product_id):
    """获取商品达人数据 - 最近30天的数据，如果没有则获取最新可用数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 确保商品有分析数据
        _ensure_product_has_data(cursor, conn, product_id)

        # 获取趋势数据（优先30天，回退到最新可用）
        trend_rows, (actual_start_date, actual_end_date) = _get_product_analysis_data(
            cursor,
            'analysis_goods_trend',
            'date',
            ['user_count', 'video_count'],
            product_id
        )

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

        if dates:
            logger.info(f"[达人] 返回数据: {len(trend_rows)} 条记录，日期范围: {actual_start_date} 到 {actual_end_date}")

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
                'top_followers': top_followers,
                'date_range': {
                    'start': str(actual_start_date),
                    'end': str(actual_end_date)
                }
            }
        })

    except Exception as e:
        logger.error(f"获取达人数据失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': f'获取达人数据失败: {str(e)}'}), 500


@goods_analysis_bp.route('/video/<product_id>', methods=['GET'])
@login_required
@permission_required('data:view')
def get_goods_video(product_id):
    """获取商品视频数据 - 最近30天的数据，如果没有则获取最新可用数据"""
    try:
        logger.info(f"[VIDEO] 开始获取视频数据，productId={product_id}")
        conn = get_db_connection()
        cursor = conn.cursor()

        # 确保商品有分析数据
        _ensure_product_has_data(cursor, conn, product_id)

        # 获取数据（优先30天，回退到最新可用）
        rows, (actual_start_date, actual_end_date) = _get_product_analysis_data(
            cursor,
            'analysis_video_sales',
            'date',
            ['video_count', 'play_count', 'sales_count', 'like_count', 'comment_count'],
            product_id
        )

        cursor.close()
        conn.close()

        logger.info(f"[VIDEO] 查询结果: {len(rows)} rows, dates: {actual_start_date} ~ {actual_end_date}")

        if not rows:
            logger.warning(f"[VIDEO] 商品 {product_id} 没有视频数据，尝试重新生成...")
            # 尝试再次生成数据
            try:
                _ensure_product_has_data(cursor, conn, product_id)
                # 重新查询
                rows, (actual_start_date, actual_end_date) = _get_product_analysis_data(
                    cursor, 'analysis_video_sales', 'date',
                    ['video_count', 'play_count', 'sales_count', 'like_count', 'comment_count'],
                    product_id
                )
                if not rows:
                    logger.error(f"[VIDEO] 数据生成后仍无视频数据")
                    return jsonify({'code': -1, 'msg': '无法生成视频数据'}), 500
            except Exception as retry_e:
                logger.error(f"[VIDEO] 重新生成数据失败: {retry_e}")
                return jsonify({'code': -1, 'msg': f'生成数据失败: {str(retry_e)}'}), 500

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

        if dates:
            logger.info(f"[视频] 返回数据: {len(rows)} 条记录，日期范围: {actual_start_date} 到 {actual_end_date}")

        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'dates': dates,
                'video_count': video_count_data,
                'video_views': video_views_data,
                'video_sales': video_sales_data,
                'like_count': like_data,
                'comment_count': comment_data,
                'date_range': {
                    'start': str(actual_start_date),
                    'end': str(actual_end_date)
                }
            }
        })

    except Exception as e:
        logger.error(f"获取视频数据失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': f'获取视频数据失败: {str(e)}'}), 500


@goods_analysis_bp.route('/live/<product_id>', methods=['GET'])
@login_required
@permission_required('data:view')
def get_goods_live(product_id):
    """获取商品直播数据 - 最近30天的数据，如果没有则获取最新可用数据"""
    try:
        logger.info(f"[LIVE] 开始获取直播数据，productId={product_id}")
        conn = get_db_connection()
        cursor = conn.cursor()

        # 确保商品有分析数据
        _ensure_product_has_data(cursor, conn, product_id)

        # 获取数据（优先30天，回退到最新可用）
        rows, (actual_start_date, actual_end_date) = _get_product_analysis_data(
            cursor,
            'analysis_live_trend',
            'date',
            ['live_count', 'sales_count', 'sales_amount', 'viewer_count'],
            product_id
        )

        cursor.close()
        conn.close()

        logger.info(f"[LIVE] 查询结果: {len(rows)} rows, dates: {actual_start_date} ~ {actual_end_date}")

        if not rows:
            logger.warning(f"[LIVE] 商品 {product_id} 没有直播数据，尝试重新生成...")
            # 尝试再次生成数据
            try:
                _ensure_product_has_data(cursor, conn, product_id)
                # 重新查询
                rows, (actual_start_date, actual_end_date) = _get_product_analysis_data(
                    cursor, 'analysis_live_trend', 'date',
                    ['live_count', 'sales_count', 'sales_amount', 'viewer_count'],
                    product_id
                )
                if not rows:
                    logger.error(f"[LIVE] 数据生成后仍无直播数据")
                    return jsonify({'code': -1, 'msg': '无法生成直播数据'}), 500
            except Exception as retry_e:
                logger.error(f"[LIVE] 重新生成数据失败: {retry_e}")
                return jsonify({'code': -1, 'msg': f'生成数据失败: {str(retry_e)}'}), 500

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

        if dates:
            logger.info(f"[直播] 返回数据: {len(rows)} 条记录，日期范围: {actual_start_date} 到 {actual_end_date}")

        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'dates': dates,
                'live_count': live_count_data,
                'live_sales': live_sales_data,
                'live_amount': live_amount_data,
                'live_viewer': live_viewer_data,
                'date_range': {
                    'start': str(actual_start_date),
                    'end': str(actual_end_date)
                }
            }
        })

    except Exception as e:
        logger.error(f"获取直播数据失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': f'获取直播数据失败: {str(e)}'}), 500
