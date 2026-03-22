# -*- coding: utf-8 -*-
"""查看原始数据的实际字段结构"""

import pymysql
import json

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Dy@analysis2024',
    'database': 'dy_analysis_system'
}

conn = pymysql.connect(**DB_CONFIG, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

with conn.cursor() as cursor:
    # 查询 analysis_user_list_raw 的一条数据
    cursor.execute("SELECT id, raw_data FROM analysis_user_list_raw LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        print(f"=== Raw ID: {row['id']} ===")
        data = row['raw_data']
        if isinstance(data, str):
            data = json.loads(data)
        
        print(f"\n顶层 Keys: {list(data.keys())}")
        
        # 打印 result 中的第一条
        if 'result' in data and data['result']:
            first_item = data['result'][0]
            print(f"\n=== result[0] 的所有字段 ({len(first_item)} 个) ===")
            for key, value in first_item.items():
                print(f"  {key}: {value!r} ({type(value).__name__})")
        else:
            print("\n没有 result 数据")
            print(f"完整数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    else:
        print("没有数据")

conn.close()
