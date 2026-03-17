CREATE TABLE IF NOT EXISTS shop_product (
    -- 主键
    id VARCHAR(32) PRIMARY KEY COMMENT '记录ID',
    product_id VARCHAR(32) NOT NULL COMMENT '商品ID',
    
    -- 基础信息
    platform VARCHAR(20) DEFAULT 'douyin' COMMENT '平台',
    status TINYINT DEFAULT 1 COMMENT '状态',
    title VARCHAR(500) COMMENT '商品标题',
    cover VARCHAR(500) COMMENT '封面图URL',
    url VARCHAR(1000) COMMENT '商品链接',
    
    -- 价格信息
    price DECIMAL(10,2) COMMENT '原价',
    coupon DECIMAL(10,2) DEFAULT 0 COMMENT '优惠券金额',
    coupon_price DECIMAL(10,2) COMMENT '券后价',
    
    -- 佣金信息
    cos_ratio DECIMAL(6,4) COMMENT '佣金比例',
    kol_cos_ratio DECIMAL(6,4) COMMENT 'KOL佣金比例',
    cos_fee DECIMAL(10,2) COMMENT '佣金金额',
    kol_cos_fee DECIMAL(10,2) COMMENT 'KOL佣金金额',
    
    -- 分类信息
    cate_0 INT COMMENT '顶级分类ID',
    first_cid VARCHAR(20) COMMENT '一级类目',
    second_cid INT DEFAULT 0 COMMENT '二级类目',
    third_cid INT DEFAULT 0 COMMENT '三级类目',
    
    -- 补贴信息
    subsidy_status TINYINT DEFAULT 0 COMMENT '补贴状态',
    subsidy_ratio DECIMAL(6,4) DEFAULT 0 COMMENT '补贴比例',
    butie_rate DECIMAL(6,4) DEFAULT 0 COMMENT '补贴费率',
    other_platform TINYINT DEFAULT 0 COMMENT '是否其他平台',
    
    -- 店铺信息
    shop_id VARCHAR(32) COMMENT '店铺ID',
    shop_name VARCHAR(200) COMMENT '店铺名称',
    shop_logo VARCHAR(500) COMMENT '店铺Logo',
    
    -- 活动信息
    activity_id VARCHAR(32) COMMENT '活动ID',
    said VARCHAR(32) COMMENT 'said',
    begin_time DATE COMMENT '活动开始时间',
    end_time DATE COMMENT '活动结束时间',
    
    -- 销售数据
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
    
    -- 其他属性
    combined INT DEFAULT 0 COMMENT '综合评分',
    in_stock TINYINT DEFAULT 1 COMMENT '是否有货',
    sharable TINYINT DEFAULT 1 COMMENT '是否可分享',
    is_redu TINYINT DEFAULT 0 COMMENT '是否热度',
    is_sole TINYINT DEFAULT 0 COMMENT '是否独家',
    is_sample TINYINT DEFAULT 0 COMMENT '是否有样品',
    issue_ratio DECIMAL(10,2) DEFAULT 0 COMMENT '出单率',
    favorite_id INT DEFAULT 0 COMMENT '收藏ID',
    
    -- JSON字段
    imgs JSON COMMENT '图片列表',
    labels JSON COMMENT '标签列表',
    tags JSON COMMENT '标签属性',
    shop_total_score JSON COMMENT '店铺评分',
    
    -- 系统字段
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_valid BOOL DEFAULT 1 COMMENT "是否合法"
    -- 索引
    UNIQUE KEY uk_product_id (product_id),
    INDEX idx_shop_id (shop_id),
    INDEX idx_price (price),
    INDEX idx_view_num (view_num),
    INDEX idx_combined (combined),
    INDEX idx_begin_time (begin_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抖音商品信息表';
