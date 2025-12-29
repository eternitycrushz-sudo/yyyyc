# -*- coding: utf-8 -*-
"""
视频分析数据清洗器

包含：
- VideoSalesCleaner: 视频销售清洗
- VideoListCleaner: 视频列表清洗
- VideoTimeCleaner: 视频时间分布清洗
"""

from crawler.workers.cleaners.base_cleaner import BaseCleaner


class VideoSalesCleaner(BaseCleaner):
    """视频销售清洗器"""
    raw_table = 'analysis_video_sales_raw'
    clean_table = 'analysis_video_sales'


class VideoListCleaner(BaseCleaner):
    """视频列表清洗器"""
    raw_table = 'analysis_video_list_raw'
    clean_table = 'analysis_video_list'


class VideoTimeCleaner(BaseCleaner):
    """视频时间分布清洗器"""
    raw_table = 'analysis_video_time_raw'
    clean_table = 'analysis_video_time'
