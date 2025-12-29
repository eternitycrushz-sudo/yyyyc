# -*- coding: utf-8 -*-
"""
数据库回调模块 - 用于爬虫数据入库
支持首次全量更新，后续增量更新（INSERT ON DUPLICATE KEY UPDATE）
"""

import json
import pymysql
from typing import Dict, Any
from logger import get_logger

log = get_logger("DBCallback")


class DBCallback:
    """数据库回调处理器"""
    
    def __init__(self, host: str = 'localhost', port: int = 3306,
                 user: str = 'root', password: str = '', database: str = 'dy_shop'):
        self.db_config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4'
        }
        self._conn = None
        self._ensure_table()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def _get_conn(self):
        """获取数据库连接"""
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(**self.db_config)
        return self._conn
    
    def _ensure_table(self):
        """确保表存在"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS shop_product (
            id VARCHAR(32) PRIMARY KEY COMMENT '记录ID',
            product_id VARCHAR(32) NOT NULL COMMENT '商品ID',
            platform VARCHAR(20) DEFAULT 'douyin' COMMENT '平台',
            status TINYINT DEFAULT 1 COMMENT '状态',
            title VARCHAR(500) COMMENT '商品标题',
            cover VARCHAR(500) COMMENT '封面图URL',
            url VARCHAR(1000) COMMENT '商品链接',
            price DECIMAL(10,2) COMMENT '原价',
            coupon DECIMAL(10,2) DEFAULT 0 COMMENT '优惠券金额',
            coupon_price DECIMAL(10,2) COMMENT '券后价',
            cos_ratio DECIMAL(6,4) COMMENT '佣金比例',
            kol_cos_ratio DECIMAL(6,4) COMMENT 'KOL佣金比例',
            cos_fee DECIMAL(10,2) COMMENT '佣金金额',
            kol_cos_fee DECIMAL(10,2) COMMENT 'KOL佣金金额',
            cate_0 INT COMMENT '顶级分类ID',
            first_cid VARCHAR(20) COMMENT '一级类目',
            second_cid INT DEFAULT 0 COMMENT '二级类目',
            third_cid INT DEFAULT 0 COMMENT '三级类目',
            subsidy_status TINYINT DEFAULT 0 COMMENT '补贴状态',
            subsidy_ratio DECIMAL(6,4) DEFAULT 0 COMMENT '补贴比例',
            butie_rate DECIMAL(6,4) DEFAULT 0 COMMENT '补贴费率',
            other_platform TINYINT DEFAULT 0 COMMENT '是否其他平台',
            shop_id VARCHAR(32) COMMENT '店铺ID',
            shop_name VARCHAR(200) COMMENT '店铺名称',
            shop_logo VARCHAR(500) COMMENT '店铺Logo',
            activity_id VARCHAR(32) COMMENT '活动ID',
            said VARCHAR(32) COMMENT 'said',
            begin_time DATE COMMENT '活动开始时间',
            end_time DATE COMMENT '活动结束时间',
            view_num BIGINT DEFAULT 0 COMMENT '浏览量',
            order_num VARCHAR(50) COMMENT '订单数范围',
            order_count INT DEFAULT 0 COMMENT '订单数',
            sales VARCHAR(50) COMMENT '总销量范围',
            sales_24 VARCHAR(50) COMMENT '24小时销量',
            sales_7day VARCHAR(50) COMMENT '7天销量',
            kol_num VARCHAR(50) COMMENT '带货达人数范围',
            kol_weekday INT DEFAULT 0 COMMENT '周带货达人数',
            pay_amount DECIMAL(12,2) DEFAULT 0 COMMENT '支付金额',
            service_fee DECIMAL(10,2) DEFAULT 0 COMMENT '服务费',
            combined INT DEFAULT 0 COMMENT '综合评分',
            in_stock TINYINT DEFAULT 1 COMMENT '是否有货',
            sharable TINYINT DEFAULT 1 COMMENT '是否可分享',
            is_redu TINYINT DEFAULT 0 COMMENT '是否热度',
            is_sole TINYINT DEFAULT 0 COMMENT '是否独家',
            is_sample TINYINT DEFAULT 0 COMMENT '是否有样品',
            issue_ratio DECIMAL(10,2) DEFAULT 0 COMMENT '出单率',
            favorite_id INT DEFAULT 0 COMMENT '收藏ID',
            imgs JSON COMMENT '图片列表',
            labels JSON COMMENT '标签列表',
            tags JSON COMMENT '标签属性',
            shop_total_score JSON COMMENT '店铺评分',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            UNIQUE KEY uk_product_id (product_id),
            INDEX idx_shop_id (shop_id),
            INDEX idx_price (price),
            INDEX idx_view_num (view_num)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抖音商品信息表';
        """
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                cursor.execute(create_sql)
            conn.commit()
            log.info("数据表检查完成")
        except Exception as e:
            log.error(f"创建表失败: {e}")
    
    def _convert_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """转换单条数据，处理特殊字段"""
        data = item.copy()
        data['in_stock'] = 1 if item.get('in_stock') else 0
        data['other_platform'] = 1 if item.get('other_platform') else 0
        
        for field in ['imgs', 'labels', 'tags', 'shop_total_score']:
            if field in data and data[field] is not None:
                data[field] = json.dumps(data[field], ensure_ascii=False)
        
        return data
    
    def save_page(self, page: int, page_data: Dict[str, Any]):
        """保存单页数据 - INSERT ON DUPLICATE KEY UPDATE 实现增量更新"""
        if 'data' not in page_data or not page_data['data']:
            log.warning(f"第{page}页数据为空，跳过")
            return
        
        items = page_data['data']
        fields = [
            'id', 'product_id', 'platform', 'status', 'title', 'cover', 'url',
            'price', 'coupon', 'coupon_price', 'cos_ratio', 'kol_cos_ratio',
            'cos_fee', 'kol_cos_fee', 'cate_0', 'first_cid', 'second_cid', 'third_cid',
            'subsidy_status', 'subsidy_ratio', 'butie_rate', 'other_platform',
            'shop_id', 'shop_name', 'shop_logo', 'activity_id', 'said',
            'begin_time', 'end_time', 'view_num', 'order_num', 'order_count',
            'sales', 'sales_24', 'sales_7day', 'kol_num', 'kol_weekday',
            'pay_amount', 'service_fee', 'combined', 'in_stock', 'sharable',
            'is_redu', 'is_sole', 'is_sample', 'issue_ratio', 'favorite_id',
            'imgs', 'labels', 'tags', 'shop_total_score'
        ]
        
        update_fields = [f for f in fields if f != 'id']
        placeholders = ', '.join(['%s'] * len(fields))
        update_clause = ', '.join([f"{f}=VALUES({f})" for f in update_fields])
        
        sql = f"""
            INSERT INTO shop_product ({', '.join(fields)})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
        """
        
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                for item in items:
                    data = self._convert_item(item)
                    values = [data.get(f) for f in fields]
                    cursor.execute(sql, values)
            conn.commit()
            log.info(f"第{page}页数据保存成功，共{len(items)}条")
        except Exception as e:
            log.error(f"第{page}页数据保存失败: {e}")
            conn.rollback()
    
    def close(self):
        """关闭连接"""
        if self._conn and self._conn.open:
            self._conn.close()
            log.info("数据库连接已关闭")
