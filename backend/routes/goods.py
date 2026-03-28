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

# first_cid -> 分类名称映射
FIRST_CID_CATEGORY_MAP = {
    '20115': '家居日用', '20018': '食品饮料', '20104': '食品饮料',
    '20040': '家居日用', '20068': '母婴用品', '20056': '美妆个护',
    '20073': '家居日用', '20005': '服饰鞋包', '20015': '家居日用',
    '20017': '食品饮料', '20035': '家居日用', '20048': '家居日用',
    '20080': '饰品配件', '20070': '家居日用', '20076': '家居日用',
    '20013': '家居日用', '20029': '美妆个护', '20062': '服饰鞋包',
    '20066': '美妆个护', '20069': '家居日用', '20072': '家居日用',
    '20090': '家居日用', '20093': '服饰鞋包', '20094': '家居日用',
    '20107': '家居日用', '20109': '美妆个护', '20113': '家居日用',
    '20120': '食品饮料', '38944': '食品饮料', '38946': '食品饮料',
    # 补充缺失的分类映射
    '20085': '美妆个护', '20007': '数码家电', '20012': '食品饮料',
    '20074': '家居日用', '20044': '数码家电', '20009': '运动户外',
    '20059': '家居日用', '20065': '数码家电', '20027': '服饰鞋包',
    '20099': '美妆个护', '20000': '数码家电', '20083': '家居日用',
    '20011': '服饰鞋包', '38945': '食品饮料', '20010': '服饰鞋包',
    '20071': '家居日用', '20006': '服饰鞋包', '20032': '家居日用',
    '20004': '家居日用', '20063': '家居日用',
}

# 默认分类（当 first_cid 无法匹配时，根据关键词推断）
KEYWORD_CATEGORY_MAP = {
    '数码家电': ['手机', '电脑', '耳机', '充电', '数码', '家电', '风扇', '加湿', '电器', '油烟机', '灶', '净水', '净饮', '洗碗机', '冰箱', '空调', '洗衣机', '电视'],
    '食品饮料': ['零食', '饮料', '麦片', '燕麦', '食品', '饼干', '糖果', '酱料', '茶叶', '咖啡', '牛奶', '酸奶', '肉', '鱼', '虾', '水果', '蔬菜', '调料', '食用油', '面条', '大米', '粥', '汤料', '蜂蜜', '坚果', '白酒', '红酒', '啤酒'],
    '家居日用': ['清洁', '洗衣', '垃圾袋', '收纳', '厨房', '家居', '毛巾', '纸巾', '牙刷', '拖把', '刷子', '贴', '灯', '花', '植物', '工具', '胶带'],
    '美妆个护': ['面膜', '口红', '眉笔', '洗面', '护肤', '化妆', '美妆', '香水', '防晒', '乳液', '精华', '卸妆', '皂', '维生素', '身体', '沐浴'],
    '服饰鞋包': ['裤', '衣', '鞋', '袜', '帽', '围巾', '手套', '包', '裙', '外套', '内衣', '睡衣'],
    '母婴用品': ['儿童', '宝宝', '婴', '奶瓶', '尿', '玩具', '童装', '孕'],
    '饰品配件': ['项链', '手链', '耳环', '戒指', '发夹', '发卡', '手表', '饰品', '配饰'],
    '运动户外': ['运动', '健身', '瑜伽', '跑步', '户外', '露营', '钓鱼', '球'],
}


def guess_category_by_title(title):
    """根据商品标题关键词推断分类"""
    if not title:
        return '家居日用'
    for cat, keywords in KEYWORD_CATEGORY_MAP.items():
        for kw in keywords:
            if kw in title:
                return cat
    return '家居日用'


def get_category_for_product(first_cid, title=''):
    """获取商品分类名称"""
    cid_str = str(first_cid) if first_cid else ''
    if cid_str in FIRST_CID_CATEGORY_MAP:
        return FIRST_CID_CATEGORY_MAP[cid_str]
    return guess_category_by_title(title)


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


@goods_bp.route('/categories', methods=['GET'])
@login_required
@permission_required('data:view')
def get_categories():
    """获取商品分类列表及数量"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取所有商品的labels字段（无LIMIT限制）
        cursor.execute("""
            SELECT labels
            FROM goods_list
            WHERE labels IS NOT NULL AND JSON_CONTAINS(labels, JSON_OBJECT('id', 'category'))
        """)

        # 手动解析并统计分类（确保不重复）
        category_counts = {}
        import json

        for row in cursor.fetchall():
            try:
                if row['labels']:
                    labels = json.loads(row['labels']) if isinstance(row['labels'], str) else row['labels']
                    for label in labels:
                        if isinstance(label, dict) and label.get('id') == 'category':
                            cat_name = label.get('name')
                            if cat_name:
                                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
                            break
            except:
                pass

        # 按数量排序，去除重复
        categories = [
            {'name': name, 'count': count}
            for name, count in sorted(set((name, category_counts[name]) for name in category_counts.keys()),
                                     key=lambda x: x[1], reverse=True)
        ]

        cursor.close()
        conn.close()
        return jsonify({'code': 0, 'data': categories})
    except Exception as e:
        logger.error(f"获取分类失败: {e}")
        return jsonify({'code': -1, 'message': str(e)})


@goods_bp.route('/search', methods=['GET'])
@login_required
@permission_required('data:view')
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
        # 支持商品ID、店铺ID精确匹配或商品名称模糊匹配
        where_clause = """
            WHERE product_id = %s
            OR goods_id = %s
            OR shop_id = %s
            OR title LIKE %s
        """
        search_params = [query, query, query, f'%{query}%']
        
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
@permission_required('data:view')
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
        
        # 时间过滤
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

        # 构建WHERE子句
        where_parts = []
        query_params = []

        if category:
            # 使用JSON_CONTAINS从labels字段中过滤分类
            where_parts.append("JSON_CONTAINS(labels, JSON_OBJECT('id', 'category', 'name', %s))")
            query_params.append(category)

        if start_date:
            where_parts.append("DATE(created_at) >= %s")
            query_params.append(start_date)

        if end_date:
            where_parts.append("DATE(created_at) <= %s")
            query_params.append(end_date)

        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        
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
@permission_required('data:view')
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
                'avg_price': float(round(avg_price, 2)),
                'avg_commission': float(round(avg_commission, 2))
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
@permission_required('data:view')
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
