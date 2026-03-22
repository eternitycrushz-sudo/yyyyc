# -*- coding: utf-8 -*-
"""
为商品生成模拟分析数据

根据商品价格生成不同量级的数据，让每个商品的图表都不一样。
高价商品销量低但客单价高，低价商品销量高但客单价低。
"""

import random
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
import pymysql


# 达人昵称池
KOL_NAMES = [
    '小美说好物', '大牛测评', '阿花带货', '老王推荐', '小李种草',
    '甜甜爱分享', '帅哥评测', '美妆达人Luna', '吃货小胖', '家居好物馆',
    '穿搭日记', '数码极客', '美食猎人', '母婴好物', '健身达人Max',
    '护肤博主CC', '零食测评官', '居家好物控', '潮流先锋', '生活小妙招',
    '好物推荐官', '省钱小能手', '品质生活家', '时尚买手', '种草小分队',
    '真实测评', '宝妈好物', '男士好物馆', '厨房达人', '清洁好物推荐',
]


def _seed_from_id(goods_id: str) -> int:
    """用 goods_id 生成稳定的随机种子，确保同一商品每次生成相同数据"""
    return int(hashlib.md5(goods_id.encode()).hexdigest()[:8], 16)


def _get_product_profile(price: float, seed: int):
    """根据价格决定商品的数据量级"""
    rng = random.Random(seed)

    if price <= 5:
        # 低价爆品：销量极高
        base_sales = rng.randint(50000, 500000)
        video_base = rng.randint(15, 80)
        live_base = rng.randint(10, 50)
        kol_base = rng.randint(30, 150)
    elif price <= 20:
        # 中低价：销量高
        base_sales = rng.randint(10000, 200000)
        video_base = rng.randint(8, 50)
        live_base = rng.randint(5, 30)
        kol_base = rng.randint(15, 80)
    elif price <= 50:
        # 中价：中等销量
        base_sales = rng.randint(2000, 50000)
        video_base = rng.randint(3, 25)
        live_base = rng.randint(2, 15)
        kol_base = rng.randint(5, 40)
    else:
        # 高价：销量较低但金额高
        base_sales = rng.randint(500, 10000)
        video_base = rng.randint(1, 15)
        live_base = rng.randint(1, 8)
        kol_base = rng.randint(3, 20)

    return {
        'base_sales': base_sales,
        'price': price,
        'video_base': video_base,
        'live_base': live_base,
        'kol_base': kol_base,
        'trend_type': rng.choice(['rising', 'stable', 'peak_mid', 'wave']),
    }


def _trend_multiplier(day_idx: int, total_days: int, trend_type: str, rng: random.Random):
    """根据趋势类型生成每日波动系数"""
    progress = day_idx / max(total_days - 1, 1)
    noise = rng.uniform(0.6, 1.4)

    if trend_type == 'rising':
        base = 0.3 + 0.7 * progress
    elif trend_type == 'stable':
        base = 0.8 + 0.2 * rng.random()
    elif trend_type == 'peak_mid':
        # 中间高，两头低
        base = 0.4 + 0.6 * (1 - abs(progress - 0.5) * 2)
    else:  # wave
        import math
        base = 0.5 + 0.5 * math.sin(progress * math.pi * 2 + rng.uniform(0, math.pi))

    return max(0.1, base * noise)


def generate_mock_data_for_product(conn, product_id: str, price: float, days: int = 30):
    """
    为单个商品生成所有分析数据

    Args:
        conn: 数据库连接
        product_id: 商品的 product_id (长ID)
        price: 商品价格
        days: 生成多少天的数据
    """
    seed = _seed_from_id(product_id)
    rng = random.Random(seed)
    profile = _get_product_profile(max(price, 1), seed)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days - 1)

    cursor = conn.cursor()

    # ========== 1. 商品趋势 (analysis_goods_trend) ==========
    trend_rows = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        mult = _trend_multiplier(i, days, profile['trend_type'], rng)

        sales_count = int(profile['base_sales'] * mult)
        sales_amount = round(sales_count * price * rng.uniform(0.85, 1.15), 2)
        video_count = max(1, int(profile['video_base'] * mult * rng.uniform(0.5, 1.5)))
        live_count = max(0, int(profile['live_base'] * mult * rng.uniform(0.3, 1.7)))
        user_count = max(1, int(profile['kol_base'] * mult * rng.uniform(0.4, 1.6)))

        trend_rows.append((
            product_id, str(date), sales_count, sales_amount,
            video_count, live_count, user_count
        ))

    cursor.executemany("""
        INSERT IGNORE INTO analysis_goods_trend
        (goods_id, date, sales_count, sales_amount, video_count, live_count, user_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, trend_rows)

    # ========== 2. 达人 TOP (analysis_user_top) ==========
    top_count = rng.randint(5, 10)
    shuffled_names = list(KOL_NAMES)
    rng.shuffle(shuffled_names)

    top_rows = []
    remaining_sales = profile['base_sales'] * days
    for rank in range(1, top_count + 1):
        share = rng.uniform(0.08, 0.25) if rank <= 3 else rng.uniform(0.02, 0.08)
        kol_sales = int(remaining_sales * share)
        kol_amount = round(kol_sales * price * rng.uniform(0.9, 1.1), 2)
        followers = rng.randint(5000, 5000000)
        videos = rng.randint(1, 30)
        lives = rng.randint(0, 15)
        user_id = hashlib.md5(f"{product_id}_{rank}".encode()).hexdigest()[:16]

        top_rows.append((
            product_id, user_id, shuffled_names[rank - 1], rank,
            kol_sales, kol_amount, followers, videos, lives
        ))

    cursor.executemany("""
        INSERT IGNORE INTO analysis_user_top
        (goods_id, user_id, nickname, `rank`, sales_count, sales_amount, follower_count, video_count, live_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, top_rows)

    # ========== 3. 视频销售趋势 (analysis_video_sales) ==========
    video_rows = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        mult = _trend_multiplier(i, days, profile['trend_type'], rng)

        video_count = max(1, int(profile['video_base'] * mult * rng.uniform(0.5, 1.5)))
        v_sales = int(profile['base_sales'] * 0.6 * mult)  # 视频贡献约60%销量
        v_amount = round(v_sales * price * rng.uniform(0.85, 1.15), 2)
        play_count = v_sales * rng.randint(8, 30)
        like_count = int(play_count * rng.uniform(0.02, 0.08))
        comment_count = int(like_count * rng.uniform(0.05, 0.2))

        video_rows.append((
            product_id, str(date), video_count, v_sales, v_amount,
            play_count, like_count, comment_count
        ))

    cursor.executemany("""
        INSERT IGNORE INTO analysis_video_sales
        (goods_id, date, video_count, sales_count, sales_amount, play_count, like_count, comment_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, video_rows)

    # ========== 4. 直播趋势 (analysis_live_trend) ==========
    live_rows = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        mult = _trend_multiplier(i, days, profile['trend_type'], rng)

        live_count = max(0, int(profile['live_base'] * mult * rng.uniform(0.3, 1.7)))
        if live_count == 0:
            live_rows.append((product_id, str(date), 0, 0, 0, 0, 0))
            continue

        l_sales = int(profile['base_sales'] * 0.4 * mult)  # 直播贡献约40%
        l_amount = round(l_sales * price * rng.uniform(0.85, 1.15), 2)
        viewer_count = l_sales * rng.randint(3, 15)
        avg_duration = rng.randint(30, 240)  # 分钟

        live_rows.append((
            product_id, str(date), live_count, l_sales, l_amount,
            viewer_count, avg_duration
        ))

    cursor.executemany("""
        INSERT IGNORE INTO analysis_live_trend
        (goods_id, date, live_count, sales_count, sales_amount, viewer_count, avg_duration)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, live_rows)

    conn.commit()


def generate_all_mock_data(db_config: dict, days: int = 30, force: bool = False):
    """
    为所有缺少分析数据的商品生成模拟数据

    Args:
        db_config: 数据库连接配置
        days: 生成多少天
        force: True=覆盖已有数据, False=只补充缺失的
    """
    conn = pymysql.connect(
        **db_config, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    # 获取所有商品
    cursor.execute("SELECT product_id, price FROM goods_list")
    products = cursor.fetchall()

    # 获取已有趋势数据的商品
    if not force:
        cursor.execute("SELECT DISTINCT goods_id FROM analysis_goods_trend")
        existing = {r['goods_id'] for r in cursor.fetchall()}
    else:
        existing = set()

    generated = 0
    for p in products:
        pid = p['product_id']
        if pid in existing:
            continue

        price = float(p['price']) if p['price'] else 10.0
        try:
            generate_mock_data_for_product(conn, pid, price, days)
            generated += 1
        except Exception as e:
            print(f"Failed for {pid}: {e}")
            conn.rollback()

    cursor.close()
    conn.close()
    return {'total': len(products), 'generated': generated, 'skipped': len(existing)}


if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'Dy@analysis2024',
        'database': 'dy_analysis_system'
    }
    result = generate_all_mock_data(db_config)
    print(f"Done: {result}")
