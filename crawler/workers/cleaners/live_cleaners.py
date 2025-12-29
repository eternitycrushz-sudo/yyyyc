# -*- coding: utf-8 -*-
"""
直播分析数据清洗器

包含：
- LiveTrendCleaner: 直播趋势清洗
- LiveListCleaner: 直播列表清洗
- LiveRelationCleaner: 直播关联清洗
"""

from crawler.workers.cleaners.base_cleaner import BaseCleaner


class LiveTrendCleaner(BaseCleaner):
    """直播趋势清洗器"""
    raw_table = 'analysis_live_trend_raw'
    clean_table = 'analysis_live_trend'


class LiveListCleaner(BaseCleaner):
    """直播列表清洗器"""
    raw_table = 'analysis_live_list_raw'
    clean_table = 'analysis_live_list'


class LiveRelationCleaner(BaseCleaner):
    """直播关联清洗器"""
    raw_table = 'analysis_live_relation_raw'
    clean_table = 'analysis_live_relation'
