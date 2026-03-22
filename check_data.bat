@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 检查数据库数据
echo ========================================
echo.

.env\Scripts\python.exe -c "import pymysql; conn = pymysql.connect(host='localhost', user='root', password='123456', database='dy_analysis_system', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) as count FROM goods_list'); result = cursor.fetchone(); print('商品总数:', result['count']); cursor.execute('SELECT product_id, title, price, cos_fee FROM goods_list LIMIT 3'); print('\n最新3个商品:'); import json; for row in cursor.fetchall(): print(json.dumps(row, ensure_ascii=False)); cursor.close(); conn.close()"

echo.
pause