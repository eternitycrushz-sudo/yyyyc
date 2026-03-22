#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试 API 和数据库
"""

import requests
import pymysql
import json

# ================== 配置 ==================
BASE_URL = 'http://localhost:5001/api'
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Dy@analysis2024',
    'database': 'dy_analysis_system',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# ================== 测试函数 ==================

def test_login():
    """测试登录"""
    print("\n=== 测试登录 ===")
    res = requests.post(f'{BASE_URL}/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    data = res.json()
    print(f"状态码: {res.status_code}")
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")

    if data.get('code') == 0 and data.get('data', {}).get('token'):
        return data['data']['token']
    return None


def test_get_product_list(token):
    """测试获取商品列表"""
    print("\n=== 测试获取商品列表 ===")
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(f'{BASE_URL}/goods/list?page=1&page_size=1', headers=headers)
    data = res.json()
    print(f"状态码: {res.status_code}")

    if data.get('code') == 0 and data.get('data', {}).get('list'):
        product = data['data']['list'][0]
        print(f"找到商品: {product['title']}")
        print(f"商品ID: {product['product_id']}")
        print(f"价格: {product['price']}")
        return product['product_id']
    else:
        print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    return None


def test_api_endpoints(token, product_id):
    """测试各个分析 API"""
    print(f"\n=== 测试分析 API (商品ID: {product_id}) ===")

    endpoints = {
        '趋势数据': f'/goods/analysis/trend/{product_id}',
        '直播数据': f'/goods/analysis/live/{product_id}',
        '视频数据': f'/goods/analysis/video/{product_id}',
        '达人数据': f'/goods/analysis/kol/{product_id}',
    }

    headers = {'Authorization': f'Bearer {token}'}

    for name, endpoint in endpoints.items():
        print(f"\n{name}: {endpoint}")
        try:
            res = requests.get(f'{BASE_URL}{endpoint}', headers=headers, timeout=5)
            data = res.json()
            print(f"  状态码: {res.status_code}")
            print(f"  返回代码: {data.get('code')}")
            print(f"  消息: {data.get('msg')}")

            if data.get('code') == 0 and data.get('data'):
                print(f"  数据点数: {len(data['data'].get('dates', []))}")
            else:
                print(f"  错误详情: {data.get('msg', '未知错误')}")
        except Exception as e:
            print(f"  异常: {e}")


def test_database(product_id):
    """测试数据库中的数据"""
    print(f"\n=== 测试数据库数据 (商品ID: {product_id}) ===")

    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 检查各个表
        tables = {
            'analysis_goods_trend': '商品趋势',
            'analysis_live_trend': '直播趋势',
            'analysis_video_sales': '视频数据',
            'analysis_kol_trend': '达人数据',
        }

        for table, name in tables.items():
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE goods_id = %s", (product_id,))
            result = cursor.fetchone()
            count = result['cnt'] if result else 0
            status = '✓' if count > 0 else '✗'
            print(f"{status} {name} ({table}): {count} 条记录")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"数据库连接失败: {e}")


# ================== 主程序 ==================

if __name__ == '__main__':
    print("=" * 50)
    print("API 和数据库测试工具")
    print("=" * 50)

    # 1. 测试登录
    token = test_login()
    if not token:
        print("\n登录失败!")
        exit(1)

    print(f"\n✓ 登录成功，Token: {token[:20]}...")

    # 2. 获取示例商品
    product_id = test_get_product_list(token)
    if not product_id:
        print("\n获取商品失败!")
        exit(1)

    # 3. 测试 API
    test_api_endpoints(token, product_id)

    # 4. 测试数据库
    test_database(product_id)

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
