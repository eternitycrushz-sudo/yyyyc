# -*- coding: utf-8 -*-
"""查看所有 raw 表的数据结构"""

import pymysql
import json

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'dy_analysis_system'
}

RAW_TABLES = [
    'analysis_goods_trend_raw',
    'analysis_user_top_raw', 
    'analysis_user_list_raw',
    'analysis_live_trend_raw',
    'analysis_live_list_raw',
    'analysis_live_relation_raw',
    'analysis_video_sales_raw',
    'analysis_video_list_raw',
    'analysis_video_time_raw',
]

conn = pymysql.connect(**DB_CONFIG, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

for table in RAW_TABLES:
    print(f"\n{'='*60}")
    print(f"表: {table}")
    print('='*60)
    
    with conn.cursor() as cursor:
        # 统计
        cursor.execute(f"SELECT COUNT(*) as total, SUM(is_cleaned=0) as uncleaned FROM {table}")
        stats = cursor.fetchone()
        print(f"总数: {stats['total']}, 未清洗: {stats['uncleaned']}")
        
        if stats['total'] == 0:
            print("  (空表)")
            continue
        
        # 查看一条数据结构
        cursor.execute(f"SELECT raw_data FROM {table} LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            data = row['raw_data']
            if isinstance(data, str):
                data = json.loads(data)
            
            print(f"数据类型: {type(data).__name__}")
            
            if isinstance(data, dict):
                print(f"顶层 Keys: {list(data.keys())}")
                # 尝试找到列表数据
                for key in ['result', 'list', 'trend', 'top', 'data']:
                    if key in data and data[key]:
                        items = data[key]
                        if isinstance(items, list) and len(items) > 0:
                            print(f"  {key}[0] 字段: {list(items[0].keys()) if isinstance(items[0], dict) else type(items[0])}")
                        elif isinstance(items, dict):
                            print(f"  {key} 字段: {list(items.keys())}")
                        break
            elif isinstance(data, list):
                print(f"直接是列表，长度: {len(data)}")
                if len(data) > 0:
                    print(f"  [0] 类型: {type(data[0]).__name__}")
                    if isinstance(data[0], dict):
                        print(f"  [0] 字段: {list(data[0].keys())}")

conn.close()
print("\n完成")
