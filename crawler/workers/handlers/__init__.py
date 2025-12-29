# -*- coding: utf-8 -*-
"""
接口处理器模块

每个分析接口有独立的 Handler，负责：
1. 爬取数据（支持分页自动翻页）
2. 保存原始数据到 *_raw 表
3. 返回数据供后续清洗

Handler 基类定义了通用逻辑，子类只需实现：
- api_path: 接口路径
- table_name: 原始数据表名
- is_paged: 是否分页接口
- parse_response(): 解析响应（可选）
"""

from crawler.workers.handlers.base_handler import BaseApiHandler
from crawler.workers.handlers.kol_handlers import (
    GoodsTrendHandler,
    GoodsUserTopHandler,
    GoodsUserListHandler
)
from crawler.workers.handlers.live_handlers import (
    GoodsLiveTrendHandler,
    GoodsLiveListHandler,
    GoodsLiveRelationHandler
)
from crawler.workers.handlers.video_handlers import (
    GoodsVideoSalesHandler,
    GoodsVideoListHandler,
    GoodsVideoTimeHandler
)

# 所有 Handler 映射
ALL_HANDLERS = {
    # 达人分析
    'goodsTrend': GoodsTrendHandler,
    'goodsUserTop': GoodsUserTopHandler,
    'goodsUserList': GoodsUserListHandler,
    # 直播分析
    'goodsLiveSalesTrend': GoodsLiveTrendHandler,
    'goodsLiveList': GoodsLiveListHandler,
    'goodsLiveRelation': GoodsLiveRelationHandler,
    # 视频分析
    'goodsVideosales': GoodsVideoSalesHandler,
    'goodsVideoList': GoodsVideoListHandler,
    'goodsVideoTime': GoodsVideoTimeHandler,
}

__all__ = [
    'BaseApiHandler',
    'ALL_HANDLERS',
    'GoodsTrendHandler',
    'GoodsUserTopHandler',
    'GoodsUserListHandler',
    'GoodsLiveTrendHandler',
    'GoodsLiveListHandler',
    'GoodsLiveRelationHandler',
    'GoodsVideoSalesHandler',
    'GoodsVideoListHandler',
    'GoodsVideoTimeHandler',
]
