# -*- coding: utf-8 -*-
"""
达人分析数据清洗器

包含：
- GoodsTrendCleaner: 商品趋势清洗
- UserTopCleaner: 达人TOP清洗
- UserListCleaner: 达人列表清洗

原理：
继承 BaseCleaner，只需定义 raw_table 和 clean_table
BaseCleaner 会自动：
1. 根据实际数据动态创建表
2. 自动识别 range_xxx 字段并拆分
3. 自动识别数字字段并转换
"""

from crawler.workers.cleaners.base_cleaner import BaseCleaner


class GoodsTrendCleaner(BaseCleaner):
    """商品趋势清洗器"""
    raw_table = 'analysis_goods_trend_raw'
    clean_table = 'analysis_goods_trend'


class UserTopCleaner(BaseCleaner):
    """达人TOP排行清洗器"""
    raw_table = 'analysis_user_top_raw'
    clean_table = 'analysis_user_top'


class UserListCleaner(BaseCleaner):
    """
    达人列表清洗器
    
    原始字段示例：
    - user_id: '3959803806747258'
    - nickname: '德佑衣物清洁用品直播间'
    - follower_count: '15150' → 转数字
    - range_last_price: '50w-75w' → 拆分为 _min/_max
    - range_last_sales: '7.5w-10w' → 拆分为 _min/_max
    """
    raw_table = 'analysis_user_list_raw'
    clean_table = 'analysis_user_list'
