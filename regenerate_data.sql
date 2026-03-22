-- 清理旧数据并重新生成
-- 这个脚本会清空分析表，迫使后端自动生成新数据

USE dy_analysis_system;

-- 1. 备份原有数据（可选）
-- 创建备份表的语句已注释，如需要可取消注释

-- 2. 清空分析表（这样后端会自动重新生成）
TRUNCATE TABLE analysis_goods_trend;
TRUNCATE TABLE analysis_live_trend;
TRUNCATE TABLE analysis_video_sales;
TRUNCATE TABLE analysis_kol_trend;
TRUNCATE TABLE analysis_live_relation;
TRUNCATE TABLE analysis_video_relation;
TRUNCATE TABLE analysis_kol_relation;

-- 3. 验证清空成功
SELECT '=' AS message;
SELECT 'Analysis tables cleared successfully' AS message;
SELECT '=' AS message;

-- 显示清空后的记录数
SELECT 'Goods Trend' as table_name, COUNT(*) as count FROM analysis_goods_trend
UNION ALL
SELECT 'Live Trend', COUNT(*) FROM analysis_live_trend
UNION ALL
SELECT 'Video Sales', COUNT(*) FROM analysis_video_sales
UNION ALL
SELECT 'KOL Trend', COUNT(*) FROM analysis_kol_trend;
