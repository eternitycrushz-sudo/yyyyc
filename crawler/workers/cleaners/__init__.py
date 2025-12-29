# -*- coding: utf-8 -*-
"""
数据清洗模块

原理讲解：
1. 每个 Handler 对应一个 Cleaner
2. Cleaner 从 *_raw 表读取 is_cleaned=0 的数据
3. 根据 field_config 配置清洗数据：
   - number: 转数字（支持 23w, 1.5万 等）
   - range: 拆分范围（如 "50w-75w" → min/max）
   - percent: 转百分比
   - keep: 保持原样
4. 写入清洗后的表
5. 更新 is_cleaned=1

使用方法：
    from crawler.workers.cleaners import ALL_CLEANERS
    
    # 清洗所有数据
    for name, cleaner_class in ALL_CLEANERS.items():
        cleaner = cleaner_class(db_config)
        cleaner.process()
    
    # 清洗指定任务
    cleaner = UserListCleaner(db_config)
    cleaner.process(task_id='xxx')
"""

from crawler.workers.cleaners.base_cleaner import BaseCleaner
from crawler.workers.cleaners.utils import (
    parse_number,
    parse_range,
    parse_percent,
    clean_dict
)
from crawler.workers.cleaners.kol_cleaners import (
    GoodsTrendCleaner,
    UserTopCleaner,
    UserListCleaner
)
from crawler.workers.cleaners.live_cleaners import (
    LiveTrendCleaner,
    LiveListCleaner,
    LiveRelationCleaner
)
from crawler.workers.cleaners.video_cleaners import (
    VideoSalesCleaner,
    VideoListCleaner,
    VideoTimeCleaner
)

# 所有清洗器映射（与 Handler 名称对应）
ALL_CLEANERS = {
    # 达人分析
    'goodsTrend': GoodsTrendCleaner,
    'goodsUserTop': UserTopCleaner,
    'goodsUserList': UserListCleaner,
    # 直播分析
    'goodsLiveSalesTrend': LiveTrendCleaner,
    'goodsLiveList': LiveListCleaner,
    'goodsLiveRelation': LiveRelationCleaner,
    # 视频分析
    'goodsVideosales': VideoSalesCleaner,
    'goodsVideoList': VideoListCleaner,
    'goodsVideoTime': VideoTimeCleaner,
}

__all__ = [
    'BaseCleaner',
    'ALL_CLEANERS',
    'parse_number',
    'parse_range',
    'parse_percent',
    'clean_dict',
    'GoodsTrendCleaner',
    'UserTopCleaner',
    'UserListCleaner',
    'LiveTrendCleaner',
    'LiveListCleaner',
    'LiveRelationCleaner',
    'VideoSalesCleaner',
    'VideoListCleaner',
    'VideoTimeCleaner',
]
