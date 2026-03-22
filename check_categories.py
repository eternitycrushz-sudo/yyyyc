#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的实际分类值
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.base import get_db_connection

try:
    conn = get_db_connection()
    cursor = conn.cursor()

    print("=" * 60)
    print("数据库中的实际分类分布")
    print("=" * 60)

    # 1. 检查category_name字段的唯一值
    cursor.execute("""
        SELECT DISTINCT category_name, COUNT(*) as count
        FROM goods_list
        WHERE category_name IS NOT NULL AND category_name != ''
        GROUP BY category_name
        ORDER BY count DESC
    """)

    categories = cursor.fetchall()
    print("\n【category_name字段的值】\n")
    for cat in categories:
        print(f"  {cat['category_name']:20s} : {cat['count']:4d} 个商品")

    # 2. 检查是否有食品相关的商品
    print("\n【零食/食品相关商品】\n")
    cursor.execute("""
        SELECT title, category_name, price, sales
        FROM goods_list
        WHERE category_name LIKE '%食%' OR category_name LIKE '%饮%' OR title LIKE '%零食%' OR title LIKE '%食品%'
        ORDER BY sales DESC
        LIMIT 5
    """)

    foods = cursor.fetchall()
    if foods:
        for food in foods:
            print(f"  {food['title'][:40]:40s} | 分类:{food['category_name']:15s} | 销量:{food['sales']}")
    else:
        print("  未找到食品相关商品")

    # 3. 检查特定分类的商品数量
    print("\n【特定分类查询测试】\n")
    test_categories = ['食品饮料', '美妆个护', '服饰鞋包', '家居日用']
    for cat in test_categories:
        cursor.execute("SELECT COUNT(*) as cnt FROM goods_list WHERE category_name = %s", (cat,))
        result = cursor.fetchone()
        count = result['cnt'] if result else 0
        print(f"  category_name='{cat:15s}' : {count:4d} 个商品")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()