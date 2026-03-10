# -*- coding: utf-8 -*-
"""
商品数据路由
"""

from flask import Blueprint, jsonify, request
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required, permission_required
import logging

logger = logging.getLogger(__name__)

goods_bp = Blueprint('goods', __name__)


def parse_chinese_number(value):
    """
    解析中文数字格式
    例如: '2.5w' -> 25000, '1000+' -> 1000, '2.5w-5w' -> 25000
    """
    if value is None:
        return 0
    
    # 如果已经是数字，直接返回
    if isinstance(value, (int, float)):
        return value
    
    # 转换为字符串
    value = str(value).strip()
    
    # 空字符串返回0
    if not value:
        return 0
    
    try:
        # 处理范围格式 (取第一个值): '2.5w-5w' -> '2.5w'
        if '-' in value:
            value = value.split('-')[0].strip()
        
        # 处理加号: '1000+' -> '1000'
        value = value.replace('+', '')
        
        # 处理万: '2.5w' -> 25000
        if 'w' in value.lower() or '万' in value:
            value = value.replace('w', '').replace('W', '').replace('万', '')
            return int(float(value) * 10000)
        
        # 处理千: '2.5k' -> 2500
        if 'k' in value.lower() or '千' in value:
            value = value.replace('k', '').replace('K', '').replace('千', '')
            return int(float(value) * 1000)
        
        # 直接转换为数字
        return int(float(value))
    except:
        return 0


@goods_bp.route('/search', methods=['GET'])
@login_required
def search_goods():
    """
    搜索商品
    
    参数：
        q: 搜索关键词（商品ID或商品名称）
        page: 页码，默认1
        page_size: 每页数量，默认20
    """
    try:
        # 获取参数
        query = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        if not query:
            return jsonify({
                'code': -1,
                'msg': '搜索关键词不能为空'
            }), 400
        
        # 验证参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 查询数据
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建搜索条件
        # 支持商品ID精确匹配或商品名称模糊匹配
        where_clause = """
            WHERE product_id = %s 
            OR goods_id = %s 
            OR title LIKE %s
        """
        search_params = [query, query, f'%{query}%']
        
        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM goods_list {where_clause}"
        cursor.execute(count_query, search_params)
        total = cursor.fetchone()['total']
        
        # 查询数据
        query_sql = f"""
        SELECT 
            id, goods_id, product_id, platform, status,
            title, cover, url,
            price, coupon, coupon_price,
            cos_ratio, kol_cos_ratio, cos_fee, kol_cos_fee,
            shop_id, shop_name, shop_logo,
            view_num, order_num, combined, sales_24, kol_num, sales, sales_7day,
            activity_id, labels, tags,
            created_at, updated_at
        FROM goods_list
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        
        search_params.extend([page_size, offset])
        cursor.execute(query_sql, search_params)
        goods_list = cursor.fetchall()
        
        # 转换数值字段
        for goods in goods_list:
            try:
                # 转换价格相关字段
                if 'price' in goods:
                    goods['price'] = float(goods['price']) if goods['price'] else 0
                if 'coupon' in goods:
                    goods['coupon'] = float(goods['coupon']) if goods['coupon'] else 0
                if 'coupon_price' in goods:
                    goods['coupon_price'] = float(goods['coupon_price']) if goods['coupon_price'] else 0
                
                # 转换佣金相关字段
                if 'cos_ratio' in goods:
                    goods['cos_ratio'] = float(goods['cos_ratio']) if goods['cos_ratio'] else 0
                if 'kol_cos_ratio' in goods:
                    goods['kol_cos_ratio'] = float(goods['kol_cos_ratio']) if goods['kol_cos_ratio'] else 0
                if 'cos_fee' in goods:
                    goods['cos_fee'] = float(goods['cos_fee']) if goods['cos_fee'] else 0
                if 'kol_cos_fee' in goods:
                    goods['kol_cos_fee'] = float(goods['kol_cos_fee']) if goods['kol_cos_fee'] else 0
                
                # 转换统计相关字段
                if 'view_num' in goods:
                    goods['view_num'] = parse_chinese_number(goods['view_num'])
                if 'order_num' in goods:
                    goods['order_num'] = parse_chinese_number(goods['order_num'])
                if 'combined' in goods:
                    goods['combined'] = parse_chinese_number(goods['combined'])
                if 'sales_24' in goods:
                    goods['sales_24'] = parse_chinese_number(goods['sales_24'])
                if 'kol_num' in goods:
                    goods['kol_num'] = parse_chinese_number(goods['kol_num'])
                if 'sales' in goods:
                    goods['sales'] = parse_chinese_number(goods['sales'])
                if 'sales_7day' in goods:
                    goods['sales_7day'] = parse_chinese_number(goods['sales_7day'])
            except Exception as e:
                logger.error(f"转换商品数据失败 (product_id={goods.get('product_id')}): {e}")
                continue
        
        cursor.close()
        conn.close()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'list': goods_list,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'query': query
            }
        })
        
    except Exception as e:
        logger.error(f"搜索商品失败: {e}", exc_info=True)
        return jsonify({
            'code': -1,
            'msg': f'搜索商品失败: {str(e)}'
        }), 500


@goods_bp.route('/list', methods=['GET'])
@login_required
def get_goods_list():
    """
    获取商品列表
    
    参数：
        page: 页码，默认1
        page_size: 每页数量，默认20
        sort_by: 排序字段，默认created_at
        order: 排序方向，asc/desc，默认desc
        category: 分类筛选，可选
    """
    try:
        # 获取参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc').upper()
        category = request.args.get('category', '')  # 分类筛选
        
        # 验证参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        if order not in ['ASC', 'DESC']:
            order = 'DESC'
        
        # 允许的排序字段
        allowed_sort_fields = ['created_at', 'price', 'cos_fee', 'view_num', 'sales']
        if sort_by not in allowed_sort_fields:
            sort_by = 'created_at'
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 查询数据
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建WHERE子句
        where_clause = ""
        query_params = []
        
        if category:
            where_clause = "WHERE labels LIKE %s"
            query_params.append(f'%{category}%')
        
        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM goods_list {where_clause}"
        cursor.execute(count_query, query_params)
        total = cursor.fetchone()['total']
        
        # 查询数据
        query = f"""
        SELECT 
            id, goods_id, product_id, platform, status,
            title, cover, url,
            price, coupon, coupon_price,
            cos_ratio, kol_cos_ratio, cos_fee, kol_cos_fee,
            shop_id, shop_name, shop_logo,
            view_num, order_num, combined, sales_24, kol_num, sales, sales_7day,
            activity_id, labels, tags,
            created_at, updated_at
        FROM goods_list
        {where_clause}
        ORDER BY {sort_by} {order}
        LIMIT %s OFFSET %s
        """
        
        query_params.extend([page_size, offset])
        cursor.execute(query, query_params)
        goods_list = cursor.fetchall()
        
        # 转换数值字段
        for goods in goods_list:
            try:
                # 转换价格相关字段
                if 'price' in goods:
                    goods['price'] = float(goods['price']) if goods['price'] else 0
                if 'coupon' in goods:
                    goods['coupon'] = float(goods['coupon']) if goods['coupon'] else 0
                if 'coupon_price' in goods:
                    goods['coupon_price'] = float(goods['coupon_price']) if goods['coupon_price'] else 0
                
                # 转换佣金相关字段
                if 'cos_ratio' in goods:
                    goods['cos_ratio'] = float(goods['cos_ratio']) if goods['cos_ratio'] else 0
                if 'kol_cos_ratio' in goods:
                    goods['kol_cos_ratio'] = float(goods['kol_cos_ratio']) if goods['kol_cos_ratio'] else 0
                if 'cos_fee' in goods:
                    goods['cos_fee'] = float(goods['cos_fee']) if goods['cos_fee'] else 0
                if 'kol_cos_fee' in goods:
                    goods['kol_cos_fee'] = float(goods['kol_cos_fee']) if goods['kol_cos_fee'] else 0
                
                # 转换统计相关字段 (使用中文数字解析)
                if 'view_num' in goods:
                    goods['view_num'] = parse_chinese_number(goods['view_num'])
                if 'order_num' in goods:
                    goods['order_num'] = parse_chinese_number(goods['order_num'])
                if 'combined' in goods:
                    goods['combined'] = parse_chinese_number(goods['combined'])
                if 'sales_24' in goods:
                    goods['sales_24'] = parse_chinese_number(goods['sales_24'])
                if 'kol_num' in goods:
                    goods['kol_num'] = parse_chinese_number(goods['kol_num'])
                if 'sales' in goods:
                    goods['sales'] = parse_chinese_number(goods['sales'])
                if 'sales_7day' in goods:
                    goods['sales_7day'] = parse_chinese_number(goods['sales_7day'])
            except Exception as e:
                logger.error(f"转换商品数据失败 (product_id={goods.get('product_id')}): {e}")
                # 继续处理其他商品，不中断
                continue
        
        cursor.close()
        conn.close()
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'list': goods_list,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
        })
        
    except Exception as e:
        logger.error(f"获取商品列表失败: {e}", exc_info=True)
        return jsonify({
            'code': -1,
            'msg': f'获取商品列表失败: {str(e)}'
        }), 500


@goods_bp.route('/stats', methods=['GET'])
@login_required
def get_goods_stats():
    """获取商品统计数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 商品总数
        cursor.execute("SELECT COUNT(*) as total FROM goods_list")
        total_goods = cursor.fetchone()['total']
        
        # 今日新增
        cursor.execute("""
            SELECT COUNT(*) as today_count 
            FROM goods_list 
            WHERE DATE(created_at) = CURDATE()
        """)
        today_count = cursor.fetchone()['today_count']
        
        # 平均价格
        cursor.execute("SELECT AVG(price) as avg_price FROM goods_list WHERE price > 0")
        avg_price = cursor.fetchone()['avg_price'] or 0
        
        # 平均佣金
        cursor.execute("SELECT AVG(cos_fee) as avg_commission FROM goods_list WHERE cos_fee > 0")
        avg_commission = cursor.fetchone()['avg_commission'] or 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'total_goods': total_goods,
                'today_count': today_count,
                'avg_price': round(avg_price, 2),
                'avg_commission': round(avg_commission, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"获取商品统计失败: {e}", exc_info=True)
        return jsonify({
            'code': -1,
            'msg': f'获取商品统计失败: {str(e)}'
        }), 500


@goods_bp.route('/detail/<product_id>', methods=['GET'])
@login_required
def get_goods_detail(product_id):
    """获取商品详情"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM goods_list WHERE product_id = %s
        """, (product_id,))
        
        goods = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not goods:
            return jsonify({
                'code': -1,
                'msg': '商品不存在'
            }), 404
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': goods
        })
        
    except Exception as e:
        logger.error(f"获取商品详情失败: {e}", exc_info=True)
        return jsonify({
            'code': -1,
            'msg': f'获取商品详情失败: {str(e)}'
        }), 500
