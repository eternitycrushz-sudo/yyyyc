# -*- coding: utf-8 -*-
"""
AI 智能助手路由 - 支持数据库查询和聊天记录
"""

from flask import Blueprint, request, jsonify, stream_with_context, Response, g
from backend.config import Config
from backend.utils.decorators import login_required
from backend.models.base import get_db_connection
import json
import re
import uuid
from datetime import datetime

try:
    from zhipuai import ZhipuAI
    ZHIPU_AVAILABLE = True
except ImportError:
    ZHIPU_AVAILABLE = False
    print("警告: zhipuai 未安装，AI 助手功能不可用")

ai_bp = Blueprint('ai', __name__)
CHAT_MODEL = "glm-4-flash"

# 初始化智谱 AI 客户端
if ZHIPU_AVAILABLE:
    client = ZhipuAI(api_key=Config.ZHIPU_API_KEY)


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
}

CATEGORY_THEMES = {
    '食品': ['20018', '20104', '20017', '20120', '38944', '38946'],
    '零食': ['20018', '20104'],
    '居家': ['20115', '20040', '20073', '20015', '20035', '20048', '20070', '20076', '20013', '20069', '20107', '20113'],
    '日用': ['20115', '20040', '20073', '20015', '20035', '20048', '20070', '20076', '20013', '20069', '20107', '20113'],
    '美妆': ['20056', '20029', '20066', '20109'],
    '母婴': ['20068'],
    '服装': ['20005', '20062', '20093'],
    '鞋包': ['20005', '20062', '20093'],
    '饰品': ['20080'],
}


def safe_float(value, default=0.0):
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (TypeError, ValueError):
        text = str(value).strip().lower()
        if not text:
            return default

        multiplier = 10000 if 'w' in text else 1
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        if not numbers:
            return default

        parsed = [float(num) * multiplier for num in numbers]
        if len(parsed) >= 2:
            return sum(parsed[:2]) / 2
        return parsed[0]


def normalize_user_message(user_message):
    return re.sub(r'[\s\u3000]+', '', (user_message or '')).lower()


def extract_theme_cids(user_message):
    matched = []
    for theme, cids in CATEGORY_THEMES.items():
        if theme in user_message:
            matched.extend(cids)

    result = []
    seen = set()
    for cid in matched:
        if cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def parse_label_list(labels_value):
    try:
        labels = json.loads(labels_value) if labels_value else []
        return labels if isinstance(labels, list) else []
    except Exception:
        return []


def infer_goods_category(goods):
    labels = parse_label_list(goods.get('labels'))

    for label in labels:
        if isinstance(label, dict) and str(label.get('id')) == 'category' and label.get('name'):
            return label['name']

    cid = str(goods.get('first_cid') or '')
    if cid:
        return FIRST_CID_CATEGORY_MAP.get(cid, f'类目 {cid}')

    for label in labels:
        if not isinstance(label, dict):
            continue
        name = (label.get('name') or '').strip()
        if not name:
            continue
        if any(keyword in name for keyword in ('佣', '热销', '包邮', '低价', '精选', '不打烊', '爱买')):
            continue
        return name

    return '未知'


def format_ratio_percent(value):
    ratio = safe_float(value)
    if ratio <= 1:
        ratio *= 100
    return f"{ratio:.2f}%"


def extract_label_names(goods):
    labels = parse_label_list(goods.get('labels'))
    names = []
    for label in labels:
        if isinstance(label, dict):
            name = (label.get('name') or '').strip()
            if name:
                names.append(name)
    return names


def get_goods_highlight_labels(goods, limit=3):
    labels = goods.get('label_names') or extract_label_names(goods)
    filtered = []
    for label in labels:
        if label == infer_goods_category(goods):
            continue
        filtered.append(label)
    return filtered[:limit]


def score_label_boost(label_names):
    weight_map = {
        '实时热销': 1.0,
        '定向高佣': 0.9,
        '星客高佣精选': 0.8,
        '粉丝爱买': 0.6,
        '抖in好物': 0.5,
        '历史低价': 0.35,
        '包邮': 0.2
    }
    return sum(weight_map.get(name, 0.0) for name in label_names)


def format_sales_signal(item):
    sales_24 = int(round(safe_float(item.get('sales_24'))))
    sales_signal = int(round(safe_float(item.get('sales_signal'))))
    if sales_24 > 0:
        return f"{sales_24} (24h)"
    if sales_signal > 0:
        return f"约{sales_signal}"
    return "暂无数据"


def estimate_sales_signal(sales_24, total_sales):
    sales_24_value = int(round(safe_float(sales_24)))
    if sales_24_value > 0:
        return sales_24_value

    total_sales_value = int(round(safe_float(total_sales)))
    if total_sales_value <= 0:
        return 0

    return min(max(int(total_sales_value * 0.002), 1), 5000)


def extract_product_id(user_message):
    match = re.search(r'\d{18,20}', user_message or '')
    return match.group() if match else ''


def has_product_id_lookup_intent(user_message):
    return bool(extract_product_id(user_message))


def has_category_commission_intent(user_message):
    normalized = normalize_user_message(user_message)
    category_keywords = ('类目', '分类', '品类', '大类')
    commission_keywords = ('佣金', '收益', '赚钱', '利润', '收入', '回报')
    has_category = any(word in normalized for word in category_keywords)
    has_commission = any(word in normalized for word in commission_keywords)
    return bool(has_category and has_commission)


def has_high_commission_goods_intent(user_message):
    normalized = normalize_user_message(user_message)
    commission_keywords = ('高佣', '高佣金', '佣金高', '佣金潜力', '佣金表现', '佣金')
    goods_keywords = ('商品', '单品', '货盘', '链接', '款')
    action_keywords = ('筛选', '推荐', '识别', '找出', '盘点', '看看', '给出')
    priority_keywords = ('优先级', '优先', '重点', '潜力', '建议', '值得做', '值得推', '值得关注', '先做哪个')
    has_commission = any(word in normalized for word in commission_keywords)
    has_goods = any(word in normalized for word in goods_keywords)
    has_action = any(word in normalized for word in action_keywords)
    has_priority = any(word in normalized for word in priority_keywords)
    return bool(has_commission and (has_goods or has_action or has_priority))


def has_priority_goods_recommendation_intent(user_message):
    normalized = normalize_user_message(user_message)
    if re.search(r'\d{18,20}', normalized):
        return False

    action_keywords = (
        '推荐', '筛选', '盘点', '找出', '看看', '梳理', '给我几款', '给我几个',
        '推什么', '做什么货', '先做什么', '先推什么'
    )
    opportunity_keywords = (
        '值得推', '值得做', '值得关注', '值得跟', '值得上',
        '能打', '能跑', '跑得动', '潜力款', '机会款',
        '重点商品', '重点款', '重点货', '优先商品', '优先看', '优先做',
        '什么好卖', '哪些好卖', '什么能卖', '哪些能卖', '哪些货好做', '有什么货能做'
    )
    goods_keywords = ('商品', '单品', '货', '款', '链接', '品')
    hot_keywords = ('热门', '热销', '爆款', '起量')

    has_action = any(word in normalized for word in action_keywords)
    has_opportunity = any(word in normalized for word in opportunity_keywords)
    has_goods = any(word in normalized for word in goods_keywords)
    has_hot = any(word in normalized for word in hot_keywords)

    return bool((has_action and has_goods) or has_opportunity or (has_hot and has_goods))


def has_assistant_meta_intent(user_message):
    normalized = normalize_user_message(user_message)
    meta_keywords = (
        '你是什么模型', '什么模型', '哪个模型', '用的什么模型',
        '你是谁', '你是干什么的', '你能做什么', '你会什么',
        '怎么用', '怎么提问', '怎么问你', '支持什么', '能帮我做什么',
        '为什么答不了', '为什么没数据', '为什么不能回答', '为什么无法分析',
        '为什么刚才没直接回答', '为什么刚才没答'
    )
    return any(keyword in normalized for keyword in meta_keywords)


def build_assistant_meta_reply(user_message):
    normalized = normalize_user_message(user_message)

    if any(keyword in normalized for keyword in ('什么模型', '哪个模型', '用的什么模型')):
        return (
            f"我是这个系统里的抖音电商数据分析助手。当前后端接入的对话模型是 `{CHAT_MODEL}`。\n\n"
            "在这个页面里，我主要负责基于库内真实商品数据做筛选、对比、优先级建议和单品分析。"
        )

    if any(keyword in normalized for keyword in ('你是谁', '你是干什么的')):
        return (
            "我是这个系统里的抖音电商数据分析助手。\n\n"
            "我的强项是基于当前商品库里的真实数据，帮你筛商品、看类目机会、找高佣候选、做商品优先级判断，以及分析具体商品 ID。"
        )

    if any(keyword in normalized for keyword in ('你能做什么', '你会什么', '支持什么', '能帮我做什么')):
        return (
            "我更擅长这几类问题：\n"
            "- 找当前值得先推的商品\n"
            "- 筛高佣且有动销的候选\n"
            "- 对比不同类目或价格带的机会\n"
            "- 分析某个具体商品 ID 的佣金、销量和店铺特征"
        )

    if any(keyword in normalized for keyword in ('怎么用', '怎么提问', '怎么问你')):
        return (
            "你直接按“范围 + 目标”来问，命中率最高。\n\n"
            "例如：\n"
            "- 家居日用里哪些商品值得先推\n"
            "- 30 到 80 元里有哪些高佣且有动销的商品\n"
            "- 帮我分析 3798803162903740889 的佣金和销量表现\n"
            "- 食品类目里有哪些值得重点关注的商品"
        )

    if any(keyword in normalized for keyword in ('为什么答不了', '为什么没数据', '为什么不能回答', '为什么无法分析', '为什么刚才没直接回答', '为什么刚才没答')):
        return (
            "因为这个页面默认优先基于商品库里的真实数据回答。\n\n"
            "如果你的问题没有命中现有的数据查询路径，或者当前库里确实缺少对应字段，我不应该硬编结果；更合理的做法是告诉你我现在能查什么、以及怎么改问法能继续往下做。"
        )

    return ""


def stream_text_response(text, chunk_size=120):
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


def has_history_memory_intent(user_message):
    normalized = re.sub(r'\s+', '', user_message or '')
    keywords = (
        '我刚问', '我刚才问', '我前面问', '我上一条问', '我上个问题',
        '刚才的问题', '前面的问题', '上一条消息', '上一条问题', '上一个问题',
        '你刚才说', '你刚刚说', '你上条说', '你还记得',
        '回顾一下', '总结一下刚才', '总结下刚才', '总结这段对话',
        '结合前文', '结合上文', '根据刚才',
        '继续', '接着说', '展开说', '换个说法', '重新表述'
    )
    return any(keyword in normalized for keyword in keywords)


def has_precise_history_lookup_intent(user_message):
    normalized = normalize_user_message(user_message)
    previous_user_keywords = (
        '我刚问', '我刚才问', '我前面问', '我上一条问', '我上个问题',
        '刚才的问题', '前面的问题', '上一条问题', '上一个问题'
    )
    previous_assistant_keywords = (
        '你刚才说', '你刚刚说', '你上一条说', '你上条说', '你前面说',
        '你刚才怎么说', '你刚才回答了什么'
    )
    generic_previous_keywords = ('上一条是什么', '上一条消息是什么', '刚才那条是什么')

    return any(keyword in normalized for keyword in previous_user_keywords + previous_assistant_keywords + generic_previous_keywords)


def find_previous_message(history, role=None, skip_current_user=False):
    skipped_current_user = False
    for message in reversed(history or []):
        current_role = message.get('role')
        content = (message.get('content') or '').strip()
        if not content:
            continue
        if skip_current_user and not skipped_current_user and current_role == 'user':
            skipped_current_user = True
            continue
        if role and current_role != role:
            continue
        return message
    return None


def build_precise_history_reply(user_message, history):
    normalized = normalize_user_message(user_message)

    previous_user_keywords = (
        '我刚问', '我刚才问', '我前面问', '我上一条问', '我上个问题',
        '刚才的问题', '前面的问题', '上一条问题', '上一个问题'
    )
    previous_assistant_keywords = (
        '你刚才说', '你刚刚说', '你上一条说', '你上条说', '你前面说',
        '你刚才怎么说', '你刚才回答了什么'
    )

    if any(keyword in normalized for keyword in previous_user_keywords):
        previous_user = find_previous_message(history, role='user', skip_current_user=True)
        if not previous_user:
            return "这轮对话里我还没找到你上一条有效提问。"
        return f"你刚才问的是：{previous_user['content']}"

    if any(keyword in normalized for keyword in previous_assistant_keywords):
        previous_assistant = find_previous_message(history, role='assistant')
        if not previous_assistant:
            return "这轮对话里我还没发出上一条有效回复。"
        content = previous_assistant['content']
        if len(content) > 180:
            content = content[:180].rstrip() + "..."
        return f"我刚才的回复是：{content}"

    if any(keyword in normalized for keyword in ('上一条是什么', '上一条消息是什么', '刚才那条是什么')):
        previous_message = find_previous_message(history, skip_current_user=True)
        if not previous_message:
            return "这轮对话里我还没找到上一条有效消息。"
        speaker = '你' if previous_message.get('role') == 'user' else '我'
        return f"{speaker}上一条说的是：{previous_message['content']}"

    return ""


def build_history_only_system_prompt():
    return """你是抖音电商数据分析助手。

当前这次回答允许你仅基于【当前会话历史】作答，不要求数据库上下文。

回答规则：
1. 只能依据当前会话里已经出现过的内容回答，不能补造未出现过的商品数据、事实或结论。
2. 如果用户在问“我刚问了什么”“上一条是什么”“你刚才说了什么”“继续”“总结一下刚才的对话”等问题，直接根据会话历史回答。
3. 如果当前会话历史不足以支持回答，明确回复“当前对话历史中暂无足够信息支持该回答”。
4. 这类问题优先直接回答，不需要表格；表达简洁、自然、准确即可。
"""


def build_chat_messages(system_content, history, user_message):
    messages = [{"role": "system", "content": system_content}]
    if history:
        messages.extend(history[:-1])
    messages.append({"role": "user", "content": user_message})
    return messages


def build_no_data_reply(user_message):
    if has_category_commission_intent(user_message) or has_high_commission_goods_intent(user_message):
        suggestions = [
            '识别当前佣金表现较强的重点商品',
            '筛选当前高佣金潜力商品并给出优先级建议',
            '从家居日用类目中推荐值得重点关注的商品',
            '提供某个具体商品 ID 的详细分析'
        ]
    elif has_priority_goods_recommendation_intent(user_message):
        suggestions = [
            '梳理当前值得优先关注的重点商品',
            '从家居日用类目中推荐几款当前能打的商品',
            '分析当前热销商品的市场表现与运营亮点',
            '筛选当前高佣金潜力商品并给出优先级建议'
        ]
    elif any(word in user_message for word in ['类目', '分类', '分布']):
        suggestions = [
            '分析当前各类目的商品分布与机会方向',
            '从食品类目中推荐值得重点关注的商品',
            '从家居日用类目中推荐值得重点关注的商品',
            '分析当前热销商品的市场表现与运营亮点'
        ]
    else:
        suggestions = [
            '识别当前佣金表现较强的重点商品',
            '分析当前热销商品的市场表现与运营亮点',
            '分析当前主流价格带的商品分布与竞争情况',
            '提供某个具体商品 ID 的详细分析'
        ]

    lines = [
        "## 我先换个方式帮你",
        "",
        "这句话我先不硬答。",
        "",
        "我现在还不能直接从当前商品库里拿到这句话对应的结果，但不代表这次对话没法继续。",
        "",
        "如果你是在问助手本身，也可以直接问：",
        "- 你是什么模型",
        "- 你能做什么",
        "- 为什么刚才没直接回答",
        "",
        "如果你是想查数据，改成下面这种问法命中率会更高："
    ]
    lines.extend([f"- {item}" for item in suggestions])
    return "\n".join(lines)


def fetch_category_commission_stats(user_message):
    matched_cids = extract_theme_cids(user_message)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        where_clauses = ["first_cid IS NOT NULL"]
        params = []
        if matched_cids:
            where_clauses.append(f"first_cid IN ({','.join(['%s'] * len(matched_cids))})")
            params.extend(matched_cids)

        cursor.execute(f"""
            SELECT
                first_cid,
                COUNT(*) AS goods_count,
                AVG(COALESCE(price, 0)) AS avg_price,
                AVG(COALESCE(cos_fee, 0)) AS avg_cos_fee,
                AVG(COALESCE(cos_ratio, 0)) AS avg_cos_ratio,
                SUM(COALESCE(sales_24, 0)) AS total_sales_24,
                SUM(COALESCE(cos_fee, 0) * COALESCE(sales_24, 0)) AS est_commission_24
            FROM goods_list
            WHERE {' AND '.join(where_clauses)}
            GROUP BY first_cid
            ORDER BY est_commission_24 DESC, avg_cos_fee DESC
            LIMIT 8
        """, tuple(params))
        rows = cursor.fetchall()

        stats = []
        for row in rows:
            total_sales_24 = int(round(safe_float(row.get('total_sales_24'))))
            avg_cos_fee = safe_float(row.get('avg_cos_fee'))
            avg_cos_ratio = safe_float(row.get('avg_cos_ratio'))
            est_commission_24 = safe_float(row.get('est_commission_24'))

            if total_sales_24 <= 0 or (avg_cos_fee <= 0 and avg_cos_ratio <= 0 and est_commission_24 <= 0):
                continue

            cid = str(row.get('first_cid') or '')
            stats.append({
                'category_name': FIRST_CID_CATEGORY_MAP.get(cid, f'类目 {cid}' if cid else '其他'),
                'goods_count': int(row.get('goods_count') or 0),
                'avg_price': safe_float(row.get('avg_price')),
                'avg_cos_fee': avg_cos_fee,
                'avg_cos_ratio': avg_cos_ratio,
                'total_sales_24': total_sales_24,
                'est_commission_24': est_commission_24
            })

        return stats
    finally:
        cursor.close()
        conn.close()


def fetch_high_commission_goods(user_message, limit=8):
    matched_cids = extract_theme_cids(user_message)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        where_clauses = [
            "COALESCE(cos_fee, 0) > 0",
            "COALESCE(cos_ratio, 0) > 0",
            "(sales_24 IS NOT NULL OR sales IS NOT NULL)"
        ]
        params = []

        if matched_cids:
            where_clauses.append(f"first_cid IN ({','.join(['%s'] * len(matched_cids))})")
            params.extend(matched_cids)

        cursor.execute(f"""
            SELECT
                product_id,
                title,
                cover,
                shop_name,
                price,
                cos_fee,
                cos_ratio,
                sales,
                sales_24,
                labels,
                first_cid
            FROM goods_list
            WHERE {' AND '.join(where_clauses)}
        """, tuple(params))
        rows = cursor.fetchall()

        candidates = []
        for row in rows:
            sales_24 = int(round(safe_float(row.get('sales_24'))))
            total_sales = int(round(safe_float(row.get('sales'))))
            sales_signal = estimate_sales_signal(sales_24, total_sales)
            cos_fee = safe_float(row.get('cos_fee'))
            cos_ratio = safe_float(row.get('cos_ratio'))

            if sales_signal <= 0 or (cos_fee <= 0 and cos_ratio <= 0):
                continue

            candidates.append({
                'product_id': row.get('product_id'),
                'title': row.get('title') or '',
                'cover': row.get('cover') or '',
                'shop_name': row.get('shop_name') or '暂无数据',
                'category_name': infer_goods_category(row),
                'price': safe_float(row.get('price')),
                'cos_fee': cos_fee,
                'cos_ratio': cos_ratio,
                'sales': total_sales,
                'sales_24': sales_24,
                'sales_signal': sales_signal
            })

        if not candidates:
            return []

        max_fee = max((item['cos_fee'] for item in candidates), default=1.0) or 1.0
        max_ratio = max((item['cos_ratio'] for item in candidates), default=1.0) or 1.0
        max_sales_signal = max((item['sales_signal'] for item in candidates), default=1) or 1

        for item in candidates:
            fee_score = item['cos_fee'] / max_fee
            ratio_score = item['cos_ratio'] / max_ratio
            sales_score = item['sales_signal'] / max_sales_signal
            priority_score = round(fee_score * 45 + ratio_score * 20 + sales_score * 35, 1)

            item['priority_score'] = priority_score

        candidates.sort(
            key=lambda item: (item['priority_score'], item['sales_24'], item['cos_fee'], item['cos_ratio']),
            reverse=True
        )
        selected = candidates[:limit]
        for idx, item in enumerate(selected):
            if idx < 3:
                item['priority_level'] = 'P1'
            elif idx < 6:
                item['priority_level'] = 'P2'
            else:
                item['priority_level'] = 'P3'

        return selected
    finally:
        cursor.close()
        conn.close()


def fetch_priority_goods(user_message, limit=8):
    matched_cids = extract_theme_cids(user_message)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        where_clauses = [
            "(sales_24 IS NOT NULL OR sales IS NOT NULL)",
            "COALESCE(price, 0) > 0"
        ]
        params = []

        if matched_cids:
            where_clauses.append(f"first_cid IN ({','.join(['%s'] * len(matched_cids))})")
            params.extend(matched_cids)

        cursor.execute(f"""
            SELECT
                product_id,
                title,
                cover,
                shop_name,
                price,
                cos_fee,
                cos_ratio,
                sales,
                sales_24,
                labels,
                first_cid
            FROM goods_list
            WHERE {' AND '.join(where_clauses)}
        """, tuple(params))
        rows = cursor.fetchall()

        candidates = []
        for row in rows:
            sales_24 = int(round(safe_float(row.get('sales_24'))))
            total_sales = int(round(safe_float(row.get('sales'))))
            sales_signal = estimate_sales_signal(sales_24, total_sales)
            cos_fee = safe_float(row.get('cos_fee'))
            cos_ratio = safe_float(row.get('cos_ratio'))
            label_names = extract_label_names(row)
            label_boost = score_label_boost(label_names)

            if sales_signal <= 0:
                continue

            candidates.append({
                'product_id': row.get('product_id'),
                'title': row.get('title') or '',
                'cover': row.get('cover') or '',
                'shop_name': row.get('shop_name') or '暂无数据',
                'category_name': infer_goods_category(row),
                'price': safe_float(row.get('price')),
                'cos_fee': cos_fee,
                'cos_ratio': cos_ratio,
                'sales': total_sales,
                'sales_24': sales_24,
                'sales_signal': sales_signal,
                'label_names': label_names,
                'label_boost': label_boost
            })

        if not candidates:
            return []

        max_sales_signal = max((item['sales_signal'] for item in candidates), default=1) or 1
        max_fee = max((item['cos_fee'] for item in candidates), default=1.0) or 1.0
        max_ratio = max((item['cos_ratio'] for item in candidates), default=1.0) or 1.0
        max_label_boost = max((item['label_boost'] for item in candidates), default=1.0) or 1.0

        for item in candidates:
            sales_score = item['sales_signal'] / max_sales_signal
            fee_score = item['cos_fee'] / max_fee if max_fee > 0 else 0
            ratio_score = item['cos_ratio'] / max_ratio if max_ratio > 0 else 0
            label_score = item['label_boost'] / max_label_boost if max_label_boost > 0 else 0
            priority_score = round(sales_score * 50 + fee_score * 20 + ratio_score * 15 + label_score * 15, 1)

            item['priority_score'] = priority_score
            item['highlight_labels'] = get_goods_highlight_labels(item)

        candidates.sort(
            key=lambda item: (item['priority_score'], item['sales_24'], item['cos_fee'], item['cos_ratio']),
            reverse=True
        )
        selected = candidates[:limit]
        for idx, item in enumerate(selected):
            if idx < 3:
                item['priority_level'] = 'P1'
            elif idx < 6:
                item['priority_level'] = 'P2'
            else:
                item['priority_level'] = 'P3'
        return selected
    finally:
        cursor.close()
        conn.close()


def fetch_product_detail(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                product_id,
                title,
                cover,
                shop_name,
                price,
                cos_fee,
                cos_ratio,
                sales,
                sales_24,
                sales_7day,
                view_num,
                labels,
                first_cid
            FROM goods_list
            WHERE product_id = %s
            LIMIT 1
        """, (product_id,))
        row = cursor.fetchone()
        if not row:
            return None

        sales_24 = int(round(safe_float(row.get('sales_24'))))
        total_sales = int(round(safe_float(row.get('sales'))))
        sales_7day = int(round(safe_float(row.get('sales_7day'))))

        product = {
            'product_id': row.get('product_id'),
            'title': row.get('title') or '',
            'cover': row.get('cover') or '',
            'shop_name': row.get('shop_name') or '暂无数据',
            'category_name': infer_goods_category(row),
            'price': safe_float(row.get('price')),
            'cos_fee': safe_float(row.get('cos_fee')),
            'cos_ratio': safe_float(row.get('cos_ratio')),
            'sales': total_sales,
            'sales_24': sales_24,
            'sales_7day': sales_7day,
            'sales_signal': estimate_sales_signal(sales_24, total_sales),
            'view_num': int(round(safe_float(row.get('view_num')))),
            'label_names': extract_label_names(row),
            'highlight_labels': get_goods_highlight_labels({'labels': row.get('labels'), 'first_cid': row.get('first_cid')})
        }
        return product
    finally:
        cursor.close()
        conn.close()


def build_product_detail_reply(user_message):
    product_id = extract_product_id(user_message)
    if not product_id:
        return ""

    product = fetch_product_detail(product_id)
    if not product:
        return (
            f"我识别到你给的是商品 ID `{product_id}`，但当前库里还没查到这条商品记录。\n\n"
            "你可以继续让我做两件事：\n"
            "- 再提供一个商品 ID，我直接帮你看佣金、销量和类目\n"
            "- 换成类目或目标来问，例如“家居日用里哪些值得先推”"
        )

    highlights = ' / '.join(product.get('highlight_labels') or ['暂无明显标签'])

    if product['cos_ratio'] >= 0.3:
        commission_view = "佣金率偏高，属于高佣候选。"
    elif product['cos_ratio'] >= 0.15:
        commission_view = "佣金率处于中高位，具备一定推广空间。"
    else:
        commission_view = "佣金率不算高，更适合结合动销一起判断。"

    if product['sales_24'] >= 100:
        sales_view = "短期动销比较强，可以优先关注承接效率。"
    elif product['sales_24'] > 0:
        sales_view = "短期有动销，但还不算强势，适合继续观察转化。"
    else:
        sales_view = "24h 动销偏弱，更适合和历史销量、佣金空间一起看。"

    lines = [
        "## 📌 商品详情",
        "",
        f"<img src=\"{product['cover']}\" width=\"72\" style=\"border-radius:8px;\"/>",
        "",
        f"**{product['title']}**",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 商品ID | `{product['product_id']}` |",
        f"| 类目 | {product['category_name']} |",
        f"| 店铺 | {product['shop_name']} |",
        f"| 价格 | ¥{product['price']:.2f} |",
        f"| 单件佣金 | ¥{product['cos_fee']:.2f} |",
        f"| 佣金率 | {format_ratio_percent(product['cos_ratio'])} |",
        f"| 总销量信号 | 约{product['sales']} |",
        f"| 24h销量信号 | {format_sales_signal(product)} |",
        f"| 7天销量信号 | {'约' + str(product['sales_7day']) if product['sales_7day'] > 0 else '暂无数据'} |",
        f"| 浏览量 | {product['view_num'] if product['view_num'] > 0 else '暂无数据'} |",
        f"| 标签亮点 | {highlights} |",
        f"| 操作 | [详情](http://localhost:5001/goods_detail.html?id={product['product_id']}) |",
        "",
        "## 🔍 快速判断",
        "",
        f"- {commission_view}",
        f"- {sales_view}",
        f"- 当前更适合把它当作 **单品复核对象**，继续和同类商品比较价格、佣金和短期动销，再决定是否优先推广。"
    ]
    return "\n".join(lines)


def build_category_commission_reply(user_message):
    stats = fetch_category_commission_stats(user_message)
    if not stats:
        return ""

    top_item = stats[0]
    second_item = stats[1] if len(stats) > 1 else None
    max_ratio_item = max(stats, key=lambda item: item['avg_cos_ratio'])
    revenue_gap = top_item['est_commission_24'] - second_item['est_commission_24'] if second_item else 0

    lines = [
        "## 📊 类目佣金收益总览",
        "",
        "以下结果全部来自当前数据库中的真实商品数据统计，用于评估不同类目的短期佣金产出能力，不包含任何假设或示例数据。",
        "",
        "| 排名 | 类目 | 商品数 | 平均价格 | 平均单件佣金 | 平均佣金率 | 24h 销量 | 预估 24h 佣金收益 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"
    ]

    for idx, item in enumerate(stats, 1):
        lines.append(
            f"| {idx} | {item['category_name']} | {item['goods_count']} | "
            f"¥{item['avg_price']:.2f} | ¥{item['avg_cos_fee']:.2f} | "
            f"{format_ratio_percent(item['avg_cos_ratio'])} | {item['total_sales_24']} | "
            f"¥{item['est_commission_24']:.2f} |"
        )

    lines.extend([
        "",
        "## 🔍 核心洞察",
        "",
        f"- 从预估 24h 佣金收益看，**{top_item['category_name']}** 当前位居第一，预估约 **¥{top_item['est_commission_24']:.2f}**，对应 24h 销量 **{top_item['total_sales_24']}**，说明该类目在当前样本中兼具销量基础与变现能力。"
    ])

    if second_item:
        lines.append(
            f"- 排名第二的是 **{second_item['category_name']}**，预估 24h 佣金收益约 **¥{second_item['est_commission_24']:.2f}**；与第一名相比，当前差额约 **¥{revenue_gap:.2f}**，说明头部类目之间已经出现较明显的收益分层。"
        )

    lines.extend([
        f"- 若从佣金率角度观察，**{max_ratio_item['category_name']}** 的平均佣金率最高，当前均值约 **{format_ratio_percent(max_ratio_item['avg_cos_ratio'])}**。这意味着该类目在单位成交上的收益效率更强，但仍需结合销量规模综合判断实际放量价值。",
        "",
        "## 🚀 经营建议",
        "",
        f"- 如果当前目标是优先提升短期佣金产出，建议优先筛选 **{top_item['category_name']}** 类目中的高销量商品，进一步比较单品佣金、转化稳定性和库存承接能力。",
        f"- 如果更关注利润率而非绝对销量，可以重点跟进 **{max_ratio_item['category_name']}** 类目，优先验证高佣金率商品是否具备持续成交能力，避免只看佣金比例而忽略动销表现。",
        "",
        "## ℹ️ 口径说明",
        "",
        "- `预估 24h 佣金收益 = 平均单件佣金 × 24h 销量`，用于当前数据库内的横向比较。"
    ])

    return "\n".join(lines)


def build_high_commission_goods_reply(user_message):
    goods = fetch_high_commission_goods(user_message, limit=8)
    if not goods:
        return ""

    top_item = goods[0]
    highest_ratio_item = max(goods, key=lambda item: item['cos_ratio'])
    highest_sales_item = max(goods, key=lambda item: item['sales_24'])
    p1_count = sum(1 for item in goods if item['priority_level'] == 'P1')

    lines = [
        "## 🎯 高佣金潜力商品优先级",
        "",
        "以下结果全部来自当前数据库中的真实商品数据，按“单件佣金 + 佣金率 + 动销信号”综合排序，用于回答“先推哪些高佣商品”这类模糊意图。",
        "",
        "| 排名 | 优先级 | 商品 | 类目 | 价格 | 单件佣金 | 佣金率 | 动销信号 | 店铺 | 操作 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |"
    ]

    for idx, item in enumerate(goods, 1):
        title = item['title'].replace('|', ' ')
        lines.append(
            f"| {idx} | {item['priority_level']} ({item['priority_score']:.1f}) | "
            f"<img src=\"{item['cover']}\" width=\"50\" style=\"border-radius:4px;\"/> {title} | "
            f"{item['category_name']} | ¥{item['price']:.2f} | ¥{item['cos_fee']:.2f} | "
            f"{format_ratio_percent(item['cos_ratio'])} | {format_sales_signal(item)} | {item['shop_name']} | "
            f"[详情](http://localhost:5001/goods_detail.html?id={item['product_id']}) |"
        )

    lines.extend([
        "",
        "## 🔍 数据洞察",
        "",
        f"- 当前优先级最高的是 **{top_item['title']}**，综合得分 **{top_item['priority_score']:.1f}**。它兼具 **¥{top_item['cos_fee']:.2f}** 单件佣金和 **{format_sales_signal(top_item)}** 的动销信号，适合优先进入试推名单。",
        f"- 本次候选中共有 **{p1_count}** 个商品进入 `P1`，说明当前库里已经存在一批既有佣金空间、又有短期成交基础的高优先级商品。",
        f"- 如果更关注单位成交收益，**{highest_ratio_item['title']}** 的佣金率最高，当前为 **{format_ratio_percent(highest_ratio_item['cos_ratio'])}**，更适合做利润率导向的补充池。",
        f"- 如果更关注短期起量，**{highest_sales_item['title']}** 的动销信号最高，当前为 **{format_sales_signal(highest_sales_item)}**，说明它的即时承接能力更强。",
        "",
        "## 🚀 经营建议",
        "",
        "- 先用 `P1` 商品做第一轮投放或达人分发，再用 `P2` 作为补位池，不要把高佣但无动销的商品和高动销但低佣的商品混在同一优先级里。",
        "- 对同类目商品，优先比较 `单件佣金` 和 `24h销量` 的组合，而不是只看佣金率；佣金率高但动销弱，短期贡献未必更好。",
        "- 如果用户问题里带有类目词，系统会自动优先收窄到对应类目，避免给出跨类目但不便执行的混合候选清单。",
        "",
        "## ℹ️ 口径说明",
        "",
        "- `优先级得分` 为当前数据库内的相对排序分，用于筛选“值得先看/先推”的候选商品，不代表绝对利润预测。",
        "- `动销信号` 优先展示真实 24h 销量；若 24h 字段缺失或为 0，则回退为基于历史销量的保守折算值。"
    ])

    return "\n".join(lines)


def build_priority_goods_reply(user_message):
    goods = fetch_priority_goods(user_message, limit=8)
    if not goods:
        return ""

    top_item = goods[0]
    top_sales_item = max(goods, key=lambda item: item['sales_24'])
    top_commission_item = max(goods, key=lambda item: item['cos_fee'])
    p1_count = sum(1 for item in goods if item['priority_level'] == 'P1')

    lines = [
        "## 🚀 当前值得优先关注的商品",
        "",
        "以下结果全部来自当前数据库中的真实商品数据，按“24h 动销 + 单件佣金 + 佣金率 + 标签信号”综合排序，用于回答“最近有什么能打的款”“先做什么货”这类口语化意图。",
        "",
        "| 排名 | 优先级 | 商品 | 类目 | 价格 | 单件佣金 | 动销信号 | 标签亮点 | 操作 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |"
    ]

    for idx, item in enumerate(goods, 1):
        title = item['title'].replace('|', ' ')
        highlights = ' / '.join(item.get('highlight_labels') or ['暂无明显标签'])
        lines.append(
            f"| {idx} | {item['priority_level']} ({item['priority_score']:.1f}) | "
            f"<img src=\"{item['cover']}\" width=\"50\" style=\"border-radius:4px;\"/> {title} | "
            f"{item['category_name']} | ¥{item['price']:.2f} | ¥{item['cos_fee']:.2f} | "
            f"{format_sales_signal(item)} | {highlights} | "
            f"[详情](http://localhost:5001/goods_detail.html?id={item['product_id']}) |"
        )

    lines.extend([
        "",
        "## 🔍 数据洞察",
        "",
        f"- 当前综合优先级最高的是 **{top_item['title']}**，得分 **{top_item['priority_score']:.1f}**。它同时具备较强的动销信号和可观的佣金空间，适合作为优先测试对象。",
        f"- 本次候选里共有 **{p1_count}** 个商品进入 `P1`，这些商品更适合作为“先看、先测、先推”的第一梯队。",
        f"- 如果只看短期放量，**{top_sales_item['title']}** 的动销信号最高，当前为 **{format_sales_signal(top_sales_item)}**，更适合承担即时起量任务。",
        f"- 如果更看重单件收益，**{top_commission_item['title']}** 的单件佣金最高，当前为 **¥{top_commission_item['cos_fee']:.2f}**，适合放入利润导向的补充池。",
        "",
        "## 🚀 经营建议",
        "",
        "- 先测试 `P1` 商品的点击和转化，再决定是否扩到 `P2`，不要一上来就把所有候选平均投放。",
        "- 如果用户问题本身没明确提“佣金”，系统会优先按动销和综合经营价值给候选；一旦提到“高佣”“佣金潜力”，则会自动切到高佣优先排序。",
        "- 类目词会自动参与收窄范围，所以像“家居日用有什么能打的货”这类问法，也会优先给出类目内候选而不是全库混排。",
        "",
        "## ℹ️ 口径说明",
        "",
        "- `优先级得分` 为当前数据库内的相对排序分，用于快速筛选“值得先做”的商品，不代表绝对 GMV 或利润承诺。",
        "- `动销信号` 优先展示真实 24h 销量；若 24h 字段缺失或为 0，则回退为基于历史销量的保守折算值。"
    ])

    return "\n".join(lines)


def build_direct_data_reply(user_message):
    if has_product_id_lookup_intent(user_message):
        return build_product_detail_reply(user_message)
    if has_assistant_meta_intent(user_message):
        return build_assistant_meta_reply(user_message)
    if has_high_commission_goods_intent(user_message):
        return build_high_commission_goods_reply(user_message)
    if has_category_commission_intent(user_message):
        return build_category_commission_reply(user_message)
    if has_priority_goods_recommendation_intent(user_message):
        return build_priority_goods_reply(user_message)
    return ""

def get_database_context(user_message, product_id=None):
    """
    根据用户消息从数据库获取相关上下文
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    context = []
    
    # 如果消息中包含 19 位数字，尝试作为 product_id
    if not product_id:
        id_match = re.search(r'\d{18,20}', user_message)
        if id_match:
            product_id = id_match.group()

    try:
        # 1. 如果有商品ID，获取极详细信息
        if product_id:
            cursor.execute("""
                SELECT product_id, title, price, cos_fee, cos_ratio, sales, sales_24, sales_7day, view_num, shop_name, cover, labels, first_cid
                FROM goods_list WHERE product_id = %s
            """, (product_id,))
            goods = cursor.fetchone()
            if goods:
                cat = infer_goods_category(goods)
                
                context.append(f"【当前核心分析商品】\nID: {goods['product_id']}\n标题: {goods['title']}\n数据: 价格¥{goods['price']}, 佣金¥{goods['cos_fee']}({goods['cos_ratio']}%), 总销量{goods['sales']}, 24h销量{goods['sales_24']}\n分类: {cat}\n图片: {goods['cover']}\n")

        # 2. 语义类目/专题分析检测
        matched_cids = extract_theme_cids(user_message)
        
        if matched_cids:
            cursor.execute(f"""
                SELECT product_id, title, cover, price, cos_fee, cos_ratio, sales, sales_24, labels
                FROM goods_list
                WHERE first_cid IN ({','.join(['%s']*len(matched_cids))})
                ORDER BY sales DESC, sales_24 DESC
                LIMIT 5
            """, tuple(matched_cids))
            theme_goods = cursor.fetchall()
            if theme_goods:
                info = f"【数据库中检索到的关联商品】\n"
                for i, g in enumerate(theme_goods, 1):
                    try:
                        lb = json.loads(g['labels']) if g['labels'] else []
                        cn = lb[0]['name'] if lb else "默认"
                    except: cn = "默认"
                    info += f"{i}. [{g['product_id']}] {g['title'][:25]}... | 销量:{g['sales']} | 24h销量:{g['sales_24']} | ¥{g['price']} | 佣金率:{g['cos_ratio']}% | 图片:{g['cover']} | 分类:{cn}\n"
                context.append(info)

        if has_high_commission_goods_intent(user_message):
            candidate_goods = fetch_high_commission_goods(user_message, limit=5)
            if candidate_goods:
                info = "【当前高佣金潜力商品候选】\n"
                for i, g in enumerate(candidate_goods, 1):
                    info += (
                        f"{i}. [{g['product_id']}] {g['title'][:25]}... | 优先级:{g['priority_level']}({g['priority_score']:.1f}) "
                        f"| 单件佣金:¥{g['cos_fee']:.2f} | 佣金率:{format_ratio_percent(g['cos_ratio'])} | 动销信号:{format_sales_signal(g)} "
                        f"| 店铺:{g['shop_name']} | 分类:{g['category_name']} | 图片:{g['cover']}\n"
                    )
                context.append(info)

        if has_priority_goods_recommendation_intent(user_message):
            candidate_goods = fetch_priority_goods(user_message, limit=5)
            if candidate_goods:
                info = "【当前值得优先关注的商品候选】\n"
                for i, g in enumerate(candidate_goods, 1):
                    highlights = '/'.join(g.get('highlight_labels') or ['暂无明显标签'])
                    info += (
                        f"{i}. [{g['product_id']}] {g['title'][:25]}... | 优先级:{g['priority_level']}({g['priority_score']:.1f}) "
                        f"| 动销信号:{format_sales_signal(g)} | 单件佣金:¥{g['cos_fee']:.2f} | 佣金率:{format_ratio_percent(g['cos_ratio'])} "
                        f"| 标签:{highlights} | 分类:{g['category_name']} | 图片:{g['cover']}\n"
                    )
                context.append(info)

        # 3. 趋势分析（如果刚才没触发类目搜索，或者用户明确提了趋势）
        if (any(w in user_message for w in ['趋势', '走势', '推荐', '热门']) or has_priority_goods_recommendation_intent(user_message)) and len(context) < 2:
            cursor.execute("""
                SELECT product_id, title, cover, price, cos_fee, cos_ratio, sales, sales_24, sales_7day, labels
                FROM goods_list
                WHERE sales_24 > 0
                ORDER BY sales_24 DESC LIMIT 5
            """)
            trends = cursor.fetchall()
            if trends:
                info = "【全场销量增长趋势Top5】\n"
                for i, g in enumerate(trends, 1):
                    try:
                        lb = json.loads(g['labels']) if g['labels'] else []
                        cn = lb[0]['name'] if lb else "默认"
                    except: cn = "默认"
                    info += f"{i}. [{g['product_id']}] {g['title'][:25]}... | 24h销量:{g['sales_24']} | 总销量:{g['sales']} | ¥{g['price']} | 分类:{cn} | 图片:{g['cover']}\n"
                context.append(info)

        # 4. 统计信息
        if any(w in user_message for w in ['分类', '分布', '多少']):
            cursor.execute("SELECT first_cid, COUNT(*) as cnt FROM goods_list GROUP BY first_cid")
            rows = cursor.fetchall()
            cat_stats = {FIRST_CID_CATEGORY_MAP.get(str(r['first_cid']), "其他"): r['cnt'] for r in rows}
            if cat_stats:
                info = "【全库商品类目分布】\n" + "\n".join([f"- {k}: {v}个商品" for k, v in sorted(cat_stats.items(), key=lambda x: x[1], reverse=True)])
                context.append(info)

        # 5. 关键词兜底搜索
        if not context or any(w in user_message for w in ['搜', '找']):
            clean_msg = re.sub(r'[趋分推搜找]','', user_message).strip()
            if len(clean_msg) >= 2:
                cursor.execute("SELECT product_id, title, cover, price, cos_fee, cos_ratio, sales, labels FROM goods_list WHERE title LIKE %s ORDER BY sales DESC LIMIT 5", (f'%{clean_msg}%',))
                results = cursor.fetchall()
                if results:
                    info = f"【关键词“{clean_msg}”搜索结果】\n"
                    for i, g in enumerate(results, 1):
                        info += f"{i}. [{g['product_id']}] {g['title'][:25]}... | 销量:{g['sales']} | ¥{g['price']} | 佣金率:{g['cos_ratio']}% | 图片:{g['cover']}\n"
                    context.append(info)

    except Exception as e:
        print(f"DB Context Error: {e}")
    finally:
        cursor.close()
        conn.close()
    
    return "\n".join(context) if context else ""


def save_chat_message(user_id, session_id, role, content):
    """保存聊天消息到数据库"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO chat_history (user_id, session_id, role, content)
            VALUES (%s, %s, %s, %s)
        """, (user_id, session_id, role, content))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"保存聊天记录失败: {e}")


def get_chat_history(user_id, session_id, limit=10):
    """获取聊天历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, created_at
            FROM chat_history
            WHERE user_id = %s AND session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, session_id, limit))
        
        messages = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 反转顺序（从旧到新）
        return [{'role': m['role'], 'content': m['content']} for m in reversed(messages)]
    except Exception as e:
        print(f"获取聊天历史失败: {e}")
        return []


def create_or_get_session(user_id, session_id=None, title=None):
    """创建或获取会话"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 检查会话是否存在
        cursor.execute("""
            SELECT session_id, title FROM chat_sessions
            WHERE session_id = %s AND user_id = %s
        """, (session_id, user_id))
        
        existing = cursor.fetchone()
        if not existing:
            # 创建新会话，使用传入的标题
            display_title = (title[:20] + '...') if title and len(title) > 20 else (title or '新对话')
            cursor.execute("""
                INSERT INTO chat_sessions (session_id, user_id, title)
                VALUES (%s, %s, %s)
            """, (session_id, user_id, display_title))
            conn.commit()
        else:
            # 取出原有标题：由于 PyMySQL DictCursor 返回字典
            existing_title = existing.get('title') if isinstance(existing, dict) else existing[1]
            if (existing_title == '新对话' or not existing_title) and title and title != '新对话':
                # 如果是初始化的新对话标题，用真正的第一句提问更新它
                display_title = (title[:20] + '...') if len(title) > 20 else title
                cursor.execute("""
                    UPDATE chat_sessions 
                    SET title = %s 
                    WHERE session_id = %s AND user_id = %s
                """, (display_title, session_id, user_id))
                conn.commit()
        
        cursor.close()
        conn.close()
        return session_id
    except Exception as e:
        print(f"创建会话失败: {e}")
        return session_id or str(uuid.uuid4())


def build_system_prompt(db_context, product_id=None):
    """构建统一的系统提示词，确保 AI 仅基于真实数据输出专业 Markdown"""
    prompt = f"""你是抖音电商数据分析助手，只能基于【数据库上下文】中的真实数据回答，输出风格要像正式的商业分析简报：专业、克制、信息密度高、适合直接给运营负责人或老板查看。

## 铁律
1. 只允许使用上下文中已经出现过的商品、类目、ID、图片和数值。
2. 没有提供的字段必须明确写“暂无数据”，不要估算、补全、类比或脑补。
3. 严禁出现“假设”“示例”“商品1/商品2”“类目A/类目B”等占位内容。
4. 如果上下文不足以支持用户问题，不要生硬拒绝；先明确当前库里缺少哪些关键信息，再给出 2-4 个可继续执行的查询建议或改写问法。
5. 如果用户问的是助手本身的信息，例如“你是什么模型”“你能做什么”“为什么刚才没答”，不要套用数据库分析口径，直接简洁说明。
6. 开头不要寒暄，不要复述用户问题，直接给结论或表格。
7. 用词要专业客观，避免“卖爆了”“很火”“冲一波”这类口语化表达。

## 输出结构
1. 优先按以下结构输出，使用二级标题：
   - `## 📌 核心结论`
   - 商品表或统计表
   - `## 🔍 数据洞察`
   - `## 🚀 经营建议`
   - `## ⚠️ 风险提示`（仅当上下文确实支持相关判断时输出）
2. emoji 可以适度使用，但仅限标题或极少量强调位置，全文最多 4 个，不要堆叠。
3. 非表格正文要比普通问答更完整，不要只写一句“洞察：……”，也不要空话套话。

## 输出要求
1. 如果上下文是具体商品列表，先写 2-3 句结论摘要，再输出 Markdown 商品表，列为：排名、商品主图、商品名称、分类、价格、佣金(率)、24h销量、操作。
2. 商品主图使用：`<img src="URL" width="50" style="border-radius:4px;"/>`。
3. 商品操作链接使用：`[详情](http://localhost:5001/goods_detail.html?id=[product_id])`。
4. 如果上下文是商品列表，表格后必须输出 `## 🔍 数据洞察`，写 3-4 条；每条 1-2 句，并尽量引用真实的价格带、类目、标签、销量、佣金或店铺特征。
5. `## 🚀 经营建议` 输出 2-3 条，每条 1-2 句，必须能够回扣到上下文中的真实数据，不要泛泛而谈。
6. 如果上下文是类目、分布或汇总统计，不要强行套用商品表；改为先写 2-3 句摘要，再输出统计结果与 3-4 条洞察、2-3 条建议。
7. 如果字段缺失，明确写“暂无数据”，不要补全。
8. 不要输出超过上下文中实际存在的数据行数。
9. 全文语气保持专业，避免过度营销感；可以稍微增加篇幅，但每段都要有信息量。

## 数据库上下文
{db_context}
"""
    return prompt


@ai_bp.route('/chat/stream', methods=['POST'])
@login_required
def chat_stream():
    """
    AI 助手流式对话接口
    """
    if not ZHIPU_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'AI 助手功能未启用，请安装 zhipuai: pip install zhipuai'
        }), 503

    data = request.json or {}
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', '')
    product_id = data.get('product_id', '')
    user_id = g.current_user.get('user_id', 1)
    
    if not user_message:
        return jsonify({
            'success': False,
            'message': '消息不能为空'
        }), 400
    
    def generate_stream():
        try:
            # 创建或获取会话
            session_id_final = create_or_get_session(user_id, session_id, title=user_message)
            
            # 保存用户消息
            save_chat_message(user_id, session_id_final, 'user', user_message)

            # 获取历史对话
            history = get_chat_history(user_id, session_id_final, limit=10)

            precise_history_reply = build_precise_history_reply(user_message, history)
            if precise_history_reply:
                save_chat_message(user_id, session_id_final, 'assistant', precise_history_reply)
                yield from stream_text_response(precise_history_reply)
                return

            # 优先走真实数据直出逻辑，避免模型编造类目对比结果
            direct_reply = build_direct_data_reply(user_message)
            if direct_reply:
                save_chat_message(user_id, session_id_final, 'assistant', direct_reply)
                yield from stream_text_response(direct_reply)
                return
            
            # 获取数据库上下文
            db_context = get_database_context(user_message, product_id)

            # 对话记忆类问题允许直接基于历史走 LLM
            if not db_context:
                if has_history_memory_intent(user_message):
                    system_content = build_history_only_system_prompt()
                    messages = build_chat_messages(system_content, history, user_message)

                    response = client.chat.completions.create(
                        model=CHAT_MODEL,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=1200,
                        stream=True
                    )

                    full_reply = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_reply += content
                            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

                    save_chat_message(user_id, session_id_final, 'assistant', full_reply)
                    yield "data: [DONE]\n\n"
                    return

                # 没有真实数据时直接返回，不调用模型生成假设内容
                full_reply = build_no_data_reply(user_message)
                save_chat_message(user_id, session_id_final, 'assistant', full_reply)
                yield from stream_text_response(full_reply)
                return

            # 构建消息列表
            system_content = build_system_prompt(db_context, product_id)
            messages = build_chat_messages(system_content, history, user_message)
            
            # 调用智谱 AI 流式接口
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=2200,
                stream=True  # 启用流式输出
            )
            
            full_reply = ""
            
            # 流式返回数据
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_reply += content
                    
                    # 发送流式数据
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            
            # 保存完整的AI回复
            save_chat_message(user_id, session_id_final, 'assistant', full_reply)
            
            # 发送结束标志
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"[AI Stream] 错误: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        generate_stream(),
        mimetype='text/plain',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    )

@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """
    AI 助手对话接口（支持数据库查询）
    """
    if not ZHIPU_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'AI 助手功能未启用，请安装 zhipuai: pip install zhipuai'
        }), 503
    
    data = request.json or {}
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', '')
    product_id = data.get('product_id', '')  # 新增：商品ID参数
    user_id = g.current_user.get('user_id', 1)
    
    # 添加调试日志
    print(f"[AI Chat] 用户ID: {user_id}, 消息: {user_message[:50]}..., 商品ID: {product_id}")
    print(f"[AI Chat] 当前用户信息: {g.current_user}")
    
    if not user_message:
        return jsonify({
            'success': False,
            'message': '消息不能为空'
        }), 400

    user_id = g.current_user['user_id']

    try:
        # 创建或获取会话
        session_id = create_or_get_session(user_id, session_id, title=user_message)
        
        # 保存用户消息
        save_chat_message(user_id, session_id, 'user', user_message)

        # 获取历史对话
        history = get_chat_history(user_id, session_id, limit=10)

        precise_history_reply = build_precise_history_reply(user_message, history)
        if precise_history_reply:
            save_chat_message(user_id, session_id, 'assistant', precise_history_reply)
            return jsonify({
                'success': True,
                'data': {
                    'reply': precise_history_reply,
                    'session_id': session_id
                }
            })

        # 优先走真实数据直出逻辑，避免模型编造类目对比结果
        direct_reply = build_direct_data_reply(user_message)
        if direct_reply:
            save_chat_message(user_id, session_id, 'assistant', direct_reply)
            return jsonify({
                'success': True,
                'data': {
                    'reply': direct_reply,
                    'session_id': session_id
                }
            })
        
        # 获取数据库上下文（传入商品ID）
        db_context = get_database_context(user_message, product_id)
        print(f"[AI Chat] 数据库上下文长度: {len(db_context) if db_context else 0}")

        if not db_context:
            if has_history_memory_intent(user_message):
                system_content = build_history_only_system_prompt()
                messages = build_chat_messages(system_content, history, user_message)

                response = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1200
                )

                reply = response.choices[0].message.content
                save_chat_message(user_id, session_id, 'assistant', reply)
                return jsonify({
                    'success': True,
                    'data': {
                        'reply': reply,
                        'session_id': session_id,
                        'usage': {
                            'prompt_tokens': response.usage.prompt_tokens,
                            'completion_tokens': response.usage.completion_tokens,
                            'total_tokens': response.usage.total_tokens
                        }
                    }
                })

            reply = build_no_data_reply(user_message)
            save_chat_message(user_id, session_id, 'assistant', reply)
            return jsonify({
                'success': True,
                'data': {
                    'reply': reply,
                    'session_id': session_id
                }
            })
        
        print(f"[AI Chat] 历史对话数量: {len(history)}")
        
        # 构建消息列表
        system_content = build_system_prompt(db_context, product_id)
        messages = build_chat_messages(system_content, history, user_message)
        
        print(f"[AI Chat] 发送给AI的消息数量: {len(messages)}")
        
        # 调用智谱 AI
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=2200
        )

        reply = response.choices[0].message.content
        print(f"[AI Chat] AI回复长度: {len(reply)}")
        
        # 保存AI回复
        save_chat_message(user_id, session_id, 'assistant', reply)
        
        return jsonify({
            'success': True,
            'data': {
                'reply': reply,
                'session_id': session_id,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        })

    except Exception as e:
        print(f"[AI Chat] 错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'AI 调用失败: {str(e)}'
        }), 500


@ai_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """获取用户的聊天历史"""
    session_id = request.args.get('session_id', '')
    user_id = g.current_user.get('user_id', 1)
    
    if not session_id:
        return jsonify({
            'success': False,
            'message': '缺少session_id'
        }), 400
    
    try:
        history = get_chat_history(user_id, session_id, limit=50)
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取历史失败: {str(e)}'
        }), 500


@ai_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """获取用户的所有会话"""
    user_id = g.current_user.get('user_id', 1)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, title, created_at, updated_at
            FROM chat_sessions
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT 20
        """, (user_id,))
        
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取会话列表失败: {str(e)}'
        }), 500


@ai_bp.route('/session/messages', methods=['GET'])
@login_required
def get_session_messages():
    """获取会话历史消息"""
    session_id = (request.args.get('session_id') or '').strip() or 'default'
    limit = int(request.args.get('limit', 50))
    user_id = g.current_user['user_id']

    history = get_chat_history(user_id, session_id, limit=limit)
    return jsonify({
        'success': True,
        'data': history
    })


@ai_bp.route('/session/delete', methods=['POST'])
@login_required
def delete_session():
    """删除会话及其消息"""
    data = request.json or {}
    session_id = (data.get('session_id') or '').strip()
    user_id = g.current_user['user_id']

    if not session_id:
        return jsonify({'code': -1, 'msg': '缺少 session_id'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM chat_history WHERE user_id = %s AND session_id = %s",
            (user_id, session_id)
        )
        cursor.execute(
            "DELETE FROM chat_sessions WHERE user_id = %s AND session_id = %s",
            (user_id, session_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)}), 500


@ai_bp.route('/session/create', methods=['POST'])
@login_required
def create_session():
    """显式创建新会话，立即返回会话信息"""
    data = request.json or {}
    session_id = data.get('session_id', '') or str(uuid.uuid4())
    title = data.get('title', '新对话')
    user_id = g.current_user.get('user_id', 1)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查是否已存在
        cursor.execute("SELECT session_id FROM chat_sessions WHERE session_id = %s AND user_id = %s",
                       (session_id, user_id))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO chat_sessions (session_id, user_id, title)
                VALUES (%s, %s, %s)
            """, (session_id, user_id, title))
            conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'session_id': session_id,
                'title': title,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@ai_bp.route('/suggestions', methods=['GET'])
@login_required
def get_suggestions():
    """获取基于数据库数据的快捷问题建议"""
    suggestions = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 查询销量最高的商品名称
        cursor.execute("""
            SELECT title FROM goods_list
            WHERE sales > 0
            ORDER BY sales DESC
            LIMIT 1
        """)
        top_goods = cursor.fetchone()
        if top_goods:
            short_name = top_goods['title'][:15]
            suggestions.append(f"分析“{short_name}”的市场表现与运营亮点")
        else:
            suggestions.append("分析当前热销商品的市场表现与运营亮点")

        # 查询高佣金商品
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM goods_list WHERE cos_fee > 5
        """)
        high_comm = cursor.fetchone()
        if high_comm and high_comm['cnt'] > 0:
            suggestions.append("筛选当前高佣金潜力商品并给出优先级建议")
        else:
            suggestions.append("识别当前佣金表现较强的重点商品")

        # 查询分类
        cursor.execute("SELECT first_cid FROM goods_list WHERE first_cid IS NOT NULL LIMIT 1")
        row = cursor.fetchone()
        if row:
            cid = str(row['first_cid'])
            cat_name = FIRST_CID_CATEGORY_MAP.get(cid, "主营")
            suggestions.append(f"从{cat_name}类目中推荐值得重点关注的商品")
        else:
            suggestions.append("分析当前各类目的商品分布与机会方向")

        # 查询价格区间
        cursor.execute("""
            SELECT MIN(price) as min_p, MAX(price) as max_p, AVG(price) as avg_p
            FROM goods_list WHERE price > 0
        """)
        price_stats = cursor.fetchone()
        if price_stats and price_stats['avg_p']:
            suggestions.append("分析当前主流价格带的商品分布与竞争情况")

        # 通用建议
        suggestions.append("对比不同类目的佣金效率与经营价值")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"获取建议失败: {e}")
        # 降级到默认建议
        suggestions = [
            "分析当前热销商品的市场表现与运营亮点",
            "识别当前佣金表现较强的重点商品",
            "分析近期商品销量趋势与变化特征",
            "分析当前各类目的商品分布与机会方向",
            "分析当前主流价格带的商品分布与竞争情况",
            "梳理当前值得重点关注的热门商品"
        ]

    return jsonify({
        'success': True,
        'data': suggestions[:6]
    })
