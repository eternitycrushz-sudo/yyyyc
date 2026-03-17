# -*- coding: utf-8 -*-
"""
数据清洗器基类

原理：
1. 从 *_raw 表读取 is_cleaned=0 的数据
2. 解析 raw_data JSON
3. 根据字段类型自动清洗（智能识别范围字段、数字字段）
4. 动态创建清洗后的表（根据实际数据结构）
5. 写入清洗后的表
6. 更新 is_cleaned=1

改进点：
- 自动识别 range_xxx 字段并拆分为 _min/_max
- 自动识别数字字符串并转换
- 动态建表，不需要预定义表结构
"""

import json
import pymysql
from abc import ABC
from typing import Dict, List, Any, Optional

from logger import get_logger
from crawler.workers.cleaners.utils import parse_number, parse_range


class BaseCleaner(ABC):
    """
    清洗器基类
    
    子类只需定义：
    - raw_table: 原始数据表名
    - clean_table: 清洗后表名
    
    可选定义：
    - field_config: 字段清洗配置（不定义则自动识别）
    - range_fields: 需要拆分的范围字段列表
    - number_fields: 需要转数字的字段列表
    """
    
    raw_table: str = None
    clean_table: str = None
    
    # 字段配置（可选，不配置则自动识别）
    field_config: Dict[str, str] = {}
    
    # 范围字段（以 range_ 开头的字段会自动识别）
    range_fields: List[str] = []
    
    # 数字字段（自动识别纯数字字符串）
    number_fields: List[str] = []
    
    # 跳过的字段
    skip_fields: List[str] = ['show_type', 'hidden_data', 'params_data', 'show_original_data']
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.log = get_logger(self.__class__.__name__)
        self._table_created = False
    
    def _get_conn(self):
        return pymysql.connect(
            **self.db_config,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def _ensure_table(self, sample_data: Dict):
        """
        根据样本数据动态创建表
        
        原理：
        1. 分析样本数据的字段
        2. 根据字段类型生成 CREATE TABLE 语句
        3. 范围字段生成 _min/_max 两列
        """
        if self._table_created:
            return
        
        # 先检查表是否存在，如果存在则跳过（不删除，保留数据）
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                cursor.execute(f"SHOW TABLES LIKE '{self.clean_table}'")
                if cursor.fetchone():
                    self._table_created = True
                    self.log.info(f"表 {self.clean_table} 已存在，跳过创建")
                    conn.close()
                    return
            conn.close()
        except Exception as e:
            self.log.warning(f"检查表存在性失败: {e}")
        
        # 构建列定义
        columns = [
            "`id` BIGINT AUTO_INCREMENT PRIMARY KEY",
            "`raw_id` BIGINT COMMENT '原始数据ID'",
            "`task_id` VARCHAR(64) COMMENT '任务ID'",
            "`goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID'",
        ]
        
        # 根据样本数据添加列
        for field, value in sample_data.items():
            if field in self.skip_fields:
                continue
            if field in ['raw_id', 'task_id', 'goods_id']:
                continue
            
            # 范围字段：拆分为 _min/_max
            if field.startswith('range_') or field in self.range_fields:
                columns.append(f"`{field}_min` DECIMAL(20,2) COMMENT '{field}最小值'")
                columns.append(f"`{field}_max` DECIMAL(20,2) COMMENT '{field}最大值'")
            # URL 字段
            elif 'avatar' in field or 'url' in field or 'cover' in field or field.endswith('_larger'):
                columns.append(f"`{field}` VARCHAR(512) COMMENT '{field}'")
            # ID 字段
            elif field.endswith('_id') or field == 'unique_id' or field == 'sec_uid':
                columns.append(f"`{field}` VARCHAR(64) COMMENT '{field}'")
            # 数字字段（检查是否是数字字符串）
            elif self._is_number_field(field, value):
                columns.append(f"`{field}` DECIMAL(20,2) COMMENT '{field}'")
            # 其他字符串
            else:
                columns.append(f"`{field}` VARCHAR(255) COMMENT '{field}'")
        
        columns.append("`created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        # 添加索引
        indexes = [
            "INDEX `idx_task_id` (`task_id`)",
            "INDEX `idx_goods_id` (`goods_id`)",
            "INDEX `idx_raw_id` (`raw_id`)",
        ]
        
        sql = f"""
        CREATE TABLE IF NOT EXISTS `{self.clean_table}` (
            {', '.join(columns)},
            {', '.join(indexes)}
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{self.clean_table}';
        """
        
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                cursor.execute(sql)
            conn.commit()
            conn.close()
            self._table_created = True
            self.log.info(f"创建表 {self.clean_table} 成功")
        except Exception as e:
            self.log.error(f"创建表失败: {e}")
            # 表可能已存在，继续执行
            self._table_created = True
    
    def _is_number_field(self, field: str, value: Any) -> bool:
        """判断是否是数字字段"""
        if field in self.number_fields:
            return True
        if field.endswith('_count') or field.endswith('_price') or field.endswith('_grow'):
            return True
        if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
            return True
        return False
    
    def clean_item(self, item: Dict) -> Dict:
        """
        清洗单条数据
        
        自动识别：
        1. range_xxx 字段 → 拆分为 xxx_min, xxx_max
        2. 数字字符串 → 转为数字
        3. 其他 → 保持原样
        """
        result = {}
        
        for field, value in item.items():
            if field in self.skip_fields:
                continue
            
            # 范围字段：拆分
            if field.startswith('range_') or field in self.range_fields:
                min_val, max_val = parse_range(value)
                result[f'{field}_min'] = min_val
                result[f'{field}_max'] = max_val
            # 数字字段：转换
            elif self._is_number_field(field, value):
                result[field] = parse_number(value)
            # 其他：保持原样
            else:
                result[field] = value
        
        return result
    
    def process(self, task_id: str = None, batch_size: int = 100) -> Dict:
        """
        执行清洗
        
        Args:
            task_id: 只清洗指定任务的数据，None 表示清洗所有未清洗的
            batch_size: 每批处理数量
            
        Returns:
            {'success': True, 'processed': 100, 'failed': 0}
        """
        self.log.info(f"开始清洗 {self.raw_table} → {self.clean_table}")
        
        conn = self._get_conn()
        processed = 0
        failed = 0
        
        try:
            while True:
                # 读取未清洗的数据
                with conn.cursor() as cursor:
                    if task_id:
                        cursor.execute(f"""
                            SELECT id, task_id, goods_id, raw_data 
                            FROM {self.raw_table}
                            WHERE is_cleaned = 0 AND task_id = %s
                            LIMIT %s
                        """, (task_id, batch_size))
                    else:
                        cursor.execute(f"""
                            SELECT id, task_id, goods_id, raw_data 
                            FROM {self.raw_table}
                            WHERE is_cleaned = 0
                            LIMIT %s
                        """, (batch_size,))
                    
                    rows = cursor.fetchall()
                
                if not rows:
                    break
                
                # 处理每条数据
                for row in rows:
                    try:
                        raw_id = row['id']
                        goods_id = row['goods_id']
                        task_id_val = row['task_id']
                        
                        # 解析 JSON
                        raw_data = row['raw_data']
                        if isinstance(raw_data, str):
                            raw_data = json.loads(raw_data)
                        
                        # 提取列表数据（兼容不同数据结构）
                        # 情况1: [...] 直接是列表
                        # 情况2: {'result': [...]} 
                        # 情况3: {'list': [...]}
                        # 情况4: {'trend': [...]}
                        # 情况5: {'live_list': [...], 'user_list': [...], ...} 多个列表
                        if isinstance(raw_data, list):
                            items = raw_data
                        elif isinstance(raw_data, dict):
                            # 尝试常见的 key
                            items = None
                            for key in ['result', 'list', 'trend', 'top', 'data']:
                                if key in raw_data and raw_data[key]:
                                    items = raw_data[key]
                                    break
                            
                            # 如果没找到，检查是否有多个 *_list 的 key（如 user_top）
                            if items is None:
                                items = []
                                for key, value in raw_data.items():
                                    if key.endswith('_list') and isinstance(value, list):
                                        # 给每条数据加上来源标记
                                        for item in value:
                                            if isinstance(item, dict):
                                                item['_source_list'] = key
                                                items.append(item)
                            
                            # 如果还是空，整个 raw_data 可能就是一条记录
                            if not items and raw_data:
                                # 排除分页信息等元数据
                                meta_keys = {'page_no', 'page_size', 'total_page', 'total_record', 
                                           'hidden_data', 'params_data', 'show_original_data', 'orders'}
                                if not all(k in meta_keys for k in raw_data.keys()):
                                    items = [raw_data]
                            
                            if items is None:
                                items = []
                            elif isinstance(items, dict):
                                items = [items]
                            elif not isinstance(items, list):
                                items = []
                        else:
                            items = []
                        
                        if not items:
                            # 没有数据，直接标记已清洗
                            with conn.cursor() as cursor:
                                cursor.execute(f"""
                                    UPDATE {self.raw_table} SET is_cleaned = 1 WHERE id = %s
                                """, (raw_id,))
                            processed += 1
                            continue
                        
                        # 确保表存在（用第一条数据作为样本）
                        if not self._table_created:
                            self._ensure_table(items[0])
                        
                        # 清洗并保存
                        for item in items:
                            cleaned = self.clean_item(item)
                            cleaned['goods_id'] = goods_id
                            cleaned['task_id'] = task_id_val
                            cleaned['raw_id'] = raw_id
                            
                            self._save_cleaned(conn, cleaned)
                        
                        # 标记已清洗
                        with conn.cursor() as cursor:
                            cursor.execute(f"""
                                UPDATE {self.raw_table} SET is_cleaned = 1 WHERE id = %s
                            """, (raw_id,))
                        
                        processed += 1
                        
                    except Exception as e:
                        self.log.error(f"清洗失败 id={row['id']}: {e}")
                        failed += 1
                
                conn.commit()
                self.log.info(f"已处理 {processed} 条，失败 {failed} 条")
        
        finally:
            conn.close()
        
        self.log.info(f"清洗完成: 成功 {processed}, 失败 {failed}")
        return {'success': True, 'processed': processed, 'failed': failed}
    
    def _save_cleaned(self, conn, data: Dict):
        """
        保存清洗后的数据
        
        策略：遇到不存在的列时自动添加
        """
        fields = list(data.keys())
        placeholders = ', '.join(['%s'] * len(fields))
        columns = ', '.join([f'`{f}`' for f in fields])
        
        sql = f"INSERT IGNORE INTO {self.clean_table} ({columns}) VALUES ({placeholders})"
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, list(data.values()))
        except Exception as e:
            error_msg = str(e)
            # 如果是列不存在的错误，自动添加列
            if "Unknown column" in error_msg:
                self._add_missing_columns(conn, data)
                # 重试插入
                with conn.cursor() as cursor:
                    cursor.execute(sql, list(data.values()))
            else:
                raise
    
    def _add_missing_columns(self, conn, data: Dict):
        """动态添加缺失的列"""
        # 获取表中已有的列
        with conn.cursor() as cursor:
            cursor.execute(f"DESCRIBE {self.clean_table}")
            existing_columns = {row['Field'] for row in cursor.fetchall()}
        
        # 添加缺失的列
        for field, value in data.items():
            if field not in existing_columns:
                col_type = self._get_column_type(field, value)
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(f"ALTER TABLE {self.clean_table} ADD COLUMN `{field}` {col_type}")
                    conn.commit()
                    self.log.info(f"添加列 {field} ({col_type})")
                except Exception as e:
                    # 可能是并发添加，忽略
                    if "Duplicate column" not in str(e):
                        self.log.warning(f"添加列 {field} 失败: {e}")
    
    def _get_column_type(self, field: str, value: Any) -> str:
        """根据字段名和值推断列类型"""
        # 范围字段的 min/max
        if field.endswith('_min') or field.endswith('_max'):
            return "DECIMAL(20,2)"
        # URL 字段
        if 'avatar' in field or 'url' in field or 'cover' in field or field.endswith('_larger'):
            return "VARCHAR(512)"
        # ID 字段
        if field.endswith('_id') or field == 'unique_id' or field == 'sec_uid':
            return "VARCHAR(64)"
        # 数字字段
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit()):
            return "DECIMAL(20,2)"
        if field.endswith('_count') or field.endswith('_price') or field.endswith('_grow') or field.endswith('_level'):
            return "DECIMAL(20,2)"
        # 默认字符串
        return "VARCHAR(255)"
