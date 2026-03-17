# -*- coding: utf-8 -*-
"""
Workers 模块

这个模块包含所有的消息队列消费者（Worker）

架构说明：
┌─────────┐    ┌──────────┐    ┌───────────────┐
│ list_q  │ -> │ detail_q │ -> │  analysis_q   │
└─────────┘    └──────────┘    └───────────────┘
     │              │                  │
     v              v                  v
 ListWorker   DetailWorker      AnalysisWorker
 (商品列表)    (商品详情)        (9个分析接口)

队列名称常量：
- QUEUE_LIST: 商品列表队列
- QUEUE_DETAIL: 商品详情队列  
- QUEUE_ANALYSIS: 数据分析队列
"""

# 队列名称常量
QUEUE_LIST = 'list_q'
QUEUE_DETAIL = 'detail_q'
QUEUE_ANALYSIS = 'analysis_q'

# 导出 Worker 类
from crawler.workers.list_worker import ListWorker
from crawler.workers.detail_worker import DetailWorker
from crawler.workers.analysis_worker import AnalysisWorker

__all__ = [
    'QUEUE_LIST',
    'QUEUE_DETAIL', 
    'QUEUE_ANALYSIS',
    'ListWorker',
    'DetailWorker',
    'AnalysisWorker'
]
