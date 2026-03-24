# -*- coding: utf-8 -*-
"""查询原始数据结构"""

import pymysql
import json

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'dy_analysis_system'
}

conn = pymysql.connect(**DB_CONFIG, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

with conn.cursor() as cursor:
    # 查询 analysis_user_list_raw 的一条数据
    cursor.execute("SELECT raw_data FROM analysis_user_list_raw LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        data = json.loads(row['raw_data']) if isinstance(row['raw_data'], str) else row['raw_data']
        print("=== analysis_user_list_raw 数据结构 ===")
        print(f"类型: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
            
            # 打印 result 中的第一条
            if 'result' in data and data['result']:
                print("\n=== result[0] 字段 ===")
                first_item = data['result'][0]
                print(json.dumps(first_item, ensure_ascii=False, indent=2))
    else:
        print("没有数据")

conn.close()
