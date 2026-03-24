# -*- coding: utf-8 -*-
"""
热点预测 & 词云图路由

热点预测算法：
  综合评分 = 销量动量 * 0.3 + 浏览增长 * 0.2 + 达人增长 * 0.2 + 佣金吸引力 * 0.15 + 价格竞争力 * 0.15
  - 销量动量: 近期销量相对值
  - 浏览增长: 浏览量在同类商品中的排名
  - 达人增长: 带货达人数越多，越有可能爆发
  - 佣金吸引力: 佣金比例越高，越吸引达人推广
  - 价格竞争力: 价格越低，越容易转化

词云数据：
  从商品标题中进行中文分词，统计词频
"""

import re
import math
import logging
from collections import Counter
from flask import Blueprint, jsonify, request
from backend.models.base import get_db_connection
from backend.utils.decorators import login_required

logger = logging.getLogger(__name__)

prediction_bp = Blueprint('prediction', __name__)

# ============================================================
# 中文分词工具（优先 jieba，降级到正则分词）
# ============================================================

_segmenter = None


def _get_segmenter():
    """获取分词器，优先 jieba，降级正则"""
    global _segmenter
    if _segmenter is not None:
        return _segmenter

    try:
        import jieba
        # 添加电商领域词汇
        ecommerce_words = [
            '直播', '爆款', '同款', '网红', '明星', '抖音', '小红书',
            '美白', '补水', '保湿', '控油', '防晒', '祛痘', '抗皱',
            '纯棉', '真皮', '不锈钢', '食品级', '国潮', '高颜值',
            '大容量', '便携', '充电', '无线', '智能', '折叠',
            '儿童', '孕妇', '老人', '学生', '男士', '女士',
            '春季', '夏季', '秋季', '冬季', '新款', '限定',
            '买一送一', '半价', '包邮', '正品', '旗舰店',
        ]
        for w in ecommerce_words:
            jieba.add_word(w)

        def jieba_seg(text):
            return list(jieba.cut(text))

        _segmenter = jieba_seg
        logger.info("使用 jieba 分词器")
    except ImportError:
        logger.info("jieba 未安装，使用正则分词")

        def regex_seg(text):
            """基于正则的简单中文分词（2-4字词组 + 英文单词）"""
            words = []
            # 提取中文词组（2-4个汉字）
            chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
            for seg in chinese_chars:
                if len(seg) <= 4:
                    words.append(seg)
                else:
                    # 对长文本做 2-gram、3-gram、4-gram
                    for n in [2, 3, 4]:
                        for i in range(len(seg) - n + 1):
                            words.append(seg[i:i + n])
            # 提取英文单词
            english = re.findall(r'[a-zA-Z]{2,}', text)
            words.extend(english)
            return words

        _segmenter = regex_seg

    return _segmenter


# 停用词
STOP_WORDS = set(
    '的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 '
    '自己 这 他 她 它 们 那 个 下 什么 里 多 还 其 别 把 被 让 给 对 又 但 如果 只 '
    '或者 而 跟 无 可以 用 于 为 与 呢 啊 吧 吗 啦 呀 哦 嗯 哈 嘻 '
    '这个 那个 什么 怎么 为什么 可以 不能 已经 '
    '新款 款式 款 同款 系列 推荐 正品 官方 旗舰 专柜 '  # 电商通用无意义词
    '包邮 现货 特价 促销 热卖 畅销 爆款 '
    'the a an and or is are was were be been it this that of in on for to'.split()
)


def _extract_keywords(titles, top_n=100):
    """从标题列表中提取关键词及其频率"""
    seg = _get_segmenter()
    counter = Counter()

    for title in titles:
        if not title:
            continue
        words = seg(title)
        for w in words:
            w = w.strip()
            # 过滤：长度 >= 2, 非停用词, 非纯数字/符号
            if (len(w) >= 2
                    and w.lower() not in STOP_WORDS
                    and not re.match(r'^[\d\s\.\-\+\*/%&@#!，。、？！：；""''（）【】]+$', w)):
                counter[w] += 1

    return counter.most_common(top_n)


def _parse_num(value):
    """将中文数字字符串转为数值"""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace('+', '').replace(',', '')
    if not s:
        return 0
    try:
        if '-' in s:
            s = s.split('-')[0].strip()
        multiplier = 1
        if s.endswith('w') or s.endswith('W') or s.endswith('万'):
            s = s.rstrip('wW万')
            multiplier = 10000
        elif s.endswith('k') or s.endswith('K') or s.endswith('千'):
            s = s.rstrip('kK千')
            multiplier = 1000
        elif s.endswith('亿'):
            s = s.rstrip('亿')
            multiplier = 100000000
        return float(s) * multiplier
    except (ValueError, TypeError):
        return 0


# ============================================================
# 热点预测 API
# ============================================================

@prediction_bp.route('/hot', methods=['GET'])
@login_required
def predict_hot():
    """
    热点预测 - 预测可能成为爆款的商品

    参数：
        limit: 返回数量，默认20
        category: 分类筛选，可选

    算法：
        综合评分 = 销量动量*0.3 + 浏览热度*0.2 + 达人热度*0.2 + 佣金吸引力*0.15 + 价格竞争力*0.15
    """
    try:
        limit = min(int(request.args.get('limit', 20)), 50)
        category = request.args.get('category', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取商品数据
        where_clause = ""
        params = []
        if category:
            # 从labels JSON字段中过滤分类
            where_clause = "WHERE JSON_SEARCH(labels, 'one', %s) IS NOT NULL"
            params.append(category)

        cursor.execute(f"""
            SELECT product_id, title, cover, price, coupon_price,
                   cos_fee, cos_ratio, shop_name, shop_id,
                   view_num, order_num, sales, sales_24, sales_7day,
                   kol_num, combined, labels, created_at
            FROM goods_list
            {where_clause}
            ORDER BY created_at DESC
            LIMIT 500
        """, params)

        products = cursor.fetchall()

        if not products:
            cursor.close()
            conn.close()
            return jsonify({'code': 0, 'data': []})

        # 统计全局数据用于归一化
        all_sales = [_parse_num(p['sales']) for p in products]
        all_views = [_parse_num(p['view_num']) for p in products]
        all_kol = [_parse_num(p['kol_num']) for p in products]
        all_prices = [float(p['price'] or 0) for p in products]
        all_cos_ratio = [float(p['cos_ratio'] or 0) for p in products]

        max_sales = max(all_sales) if all_sales else 1
        max_views = max(all_views) if all_views else 1
        max_kol = max(all_kol) if all_kol else 1
        max_price = max(all_prices) if all_prices else 1
        max_cos = max(all_cos_ratio) if all_cos_ratio else 1

        # 尝试获取有趋势数据的商品进行更精确的预测
        trend_data = {}
        try:
            cursor.execute("""
                SELECT goods_id,
                       SUM(sales_count) as total_sales,
                       COUNT(*) as data_days,
                       MAX(sales_count) as peak_sales,
                       AVG(sales_count) as avg_sales
                FROM analysis_goods_trend
                GROUP BY goods_id
            """)
            for row in cursor.fetchall():
                trend_data[row['goods_id']] = row
        except Exception:
            pass  # 表可能不存在

        cursor.close()
        conn.close()

        # 计算评分
        scored = []
        for p in products:
            sales_val = _parse_num(p['sales'])
            views_val = _parse_num(p['view_num'])
            kol_val = _parse_num(p['kol_num'])
            price_val = float(p['price'] or 0)
            cos_ratio_val = float(p['cos_ratio'] or 0)
            sales_24_val = _parse_num(p['sales_24'])

            # 归一化到 0~1
            sales_score = sales_val / max_sales if max_sales > 0 else 0
            view_score = views_val / max_views if max_views > 0 else 0
            kol_score = kol_val / max_kol if max_kol > 0 else 0
            cos_score = cos_ratio_val / max_cos if max_cos > 0 else 0
            # 价格竞争力：越便宜越高分（反向归一化）
            price_score = 1 - (price_val / max_price) if max_price > 0 else 0

            # 趋势加成（如果有趋势数据）
            trend_bonus = 0
            pid = p.get('product_id') or p.get('goods_id')
            if pid and pid in trend_data:
                td = trend_data[pid]
                if td['avg_sales'] and td['avg_sales'] > 0:
                    # 峰值/均值 越高说明爆发力越强
                    burst_ratio = float(td['peak_sales'] or 0) / float(td['avg_sales'])
                    trend_bonus = min(burst_ratio / 10, 0.3)  # 最多加 0.3

            # 24h 销量加成
            momentum_bonus = 0
            if sales_24_val > 0 and sales_val > 0:
                daily_ratio = sales_24_val / sales_val
                momentum_bonus = min(daily_ratio * 5, 0.2)  # 最多加 0.2

            # 综合评分（基础权重 0.3+0.2+0.2+0.15+0.15=1.0）
            base_score = (
                sales_score * 0.3
                + view_score * 0.2
                + kol_score * 0.2
                + cos_score * 0.15
                + price_score * 0.15
            )
            total_score = min((base_score + trend_bonus + momentum_bonus) * 100, 100)

            # 预测等级
            if total_score >= 70:
                level = '极热'
                level_color = '#ef4444'
            elif total_score >= 50:
                level = '大热'
                level_color = '#f97316'
            elif total_score >= 35:
                level = '潜力'
                level_color = '#eab308'
            elif total_score >= 20:
                level = '观望'
                level_color = '#22c55e'
            else:
                level = '平稳'
                level_color = '#6b7280'

            scored.append({
                'product_id': p['product_id'],
                'title': p['title'],
                'cover': p['cover'],
                'price': float(p['price'] or 0),
                'cos_fee': float(p['cos_fee'] or 0),
                'shop_name': p['shop_name'],
                'sales': sales_val,
                'views': views_val,
                'kol_count': kol_val,
                'sales_24': sales_24_val,
                'score': round(total_score, 1),
                'level': level,
                'level_color': level_color,
                'factors': {
                    'sales_momentum': round(sales_score * 100, 1),
                    'view_heat': round(view_score * 100, 1),
                    'kol_heat': round(kol_score * 100, 1),
                    'commission_appeal': round(cos_score * 100, 1),
                    'price_competitiveness': round(price_score * 100, 1),
                }
            })

        # 按评分排序
        scored.sort(key=lambda x: x['score'], reverse=True)

        # 统计各等级数量
        level_counts = Counter(p['level'] for p in scored)

        return jsonify({
            'code': 0,
            'data': {
                'products': scored[:limit],
                'total': len(scored),
                'level_distribution': [
                    {'name': '极热', 'value': level_counts.get('极热', 0), 'color': '#ef4444'},
                    {'name': '大热', 'value': level_counts.get('大热', 0), 'color': '#f97316'},
                    {'name': '潜力', 'value': level_counts.get('潜力', 0), 'color': '#eab308'},
                    {'name': '观望', 'value': level_counts.get('观望', 0), 'color': '#22c55e'},
                    {'name': '平稳', 'value': level_counts.get('平稳', 0), 'color': '#6b7280'},
                ]
            }
        })

    except Exception as e:
        logger.error(f"热点预测失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ============================================================
# 词云图 API
# ============================================================

@prediction_bp.route('/wordcloud', methods=['GET'])
@login_required
def get_wordcloud():
    """
    获取词云数据（商品标题关键词频率）

    参数：
        limit: 关键词数量，默认80
        source: 数据源 titles(标题) / shops(店铺)，默认 titles
        category: 分类筛选，可选
    """
    try:
        word_limit = min(int(request.args.get('limit', 80)), 200)
        source = request.args.get('source', 'titles')
        category = request.args.get('category', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        where_clause = ""
        params = []
        if category:
            # 从labels JSON字段中过滤分类
            where_clause = "WHERE JSON_SEARCH(labels, 'one', %s) IS NOT NULL"
            params.append(category)

        if source == 'shops':
            cursor.execute(f"""
                SELECT shop_name FROM goods_list
                {where_clause}
            """, params)
            texts = [row['shop_name'] for row in cursor.fetchall() if row['shop_name']]
        else:
            cursor.execute(f"""
                SELECT title FROM goods_list
                {where_clause}
                LIMIT 2000
            """, params)
            texts = [row['title'] for row in cursor.fetchall() if row['title']]

        cursor.close()
        conn.close()

        if not texts:
            return jsonify({'code': 0, 'data': []})

        keywords = _extract_keywords(texts, top_n=word_limit)

        # 转为 echarts-wordcloud 格式
        result = [{'name': word, 'value': count} for word, count in keywords]

        return jsonify({'code': 0, 'data': result})

    except Exception as e:
        logger.error(f"获取词云数据失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ============================================================
# 单品趋势预测 API
# ============================================================

@prediction_bp.route('/forecast/<product_id>', methods=['GET'])
@login_required
def forecast_product(product_id):
    """
    单品趋势预测 - 简单线性回归预测未来7天走势

    参数：
        days: 预测天数，默认7
    """
    try:
        forecast_days = min(int(request.args.get('days', 7)), 14)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, sales_count, sales_amount, video_count, live_count, user_count
            FROM analysis_goods_trend
            WHERE goods_id = %s
            ORDER BY date ASC
        """, (product_id,))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows or len(rows) < 3:
            return jsonify({'code': -1, 'msg': '历史数据不足，无法预测（至少需要3天数据）'}), 404

        # 提取历史数据
        dates = [str(r['date']) for r in rows]
        sales = [int(r['sales_count'] or 0) for r in rows]

        # 简单线性回归预测
        n = len(sales)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(sales) / n

        numerator = sum((x[i] - x_mean) * (sales[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
            intercept = y_mean
        else:
            slope = numerator / denominator
            intercept = y_mean - slope * x_mean

        # 生成预测数据
        forecast_dates = []
        forecast_values = []
        from datetime import datetime, timedelta

        last_date = datetime.strptime(dates[-1], '%Y-%m-%d')
        for i in range(1, forecast_days + 1):
            future_date = last_date + timedelta(days=i)
            forecast_dates.append(future_date.strftime('%Y-%m-%d'))
            predicted = max(0, slope * (n + i - 1) + intercept)
            # 添加一些随机波动让预测更自然
            import random
            noise = random.uniform(0.9, 1.1)
            forecast_values.append(round(predicted * noise))

        # 计算趋势判断
        if slope > 0:
            trend = 'up'
            trend_text = '上升趋势'
        elif slope < 0:
            trend = 'down'
            trend_text = '下降趋势'
        else:
            trend = 'stable'
            trend_text = '平稳'

        # 计算增长率
        if sales[0] > 0:
            growth_rate = ((sales[-1] - sales[0]) / sales[0]) * 100
        else:
            growth_rate = 0

        return jsonify({
            'code': 0,
            'data': {
                'history': {
                    'dates': dates,
                    'sales': sales,
                },
                'forecast': {
                    'dates': forecast_dates,
                    'sales': forecast_values,
                },
                'trend': trend,
                'trend_text': trend_text,
                'growth_rate': round(growth_rate, 1),
                'avg_daily_sales': round(y_mean, 1),
                'slope': round(slope, 2),
            }
        })

    except Exception as e:
        logger.error(f"趋势预测失败: {e}", exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)}), 500
