-- ============================================
-- 商品分析系统数据库表结构
-- 包含：商品详情表 + 9个分析数据表
-- ============================================

-- 商品详情表
CREATE TABLE IF NOT EXISTS `product_detail` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `product_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `title` VARCHAR(500) COMMENT '商品标题',
    `cover` VARCHAR(500) COMMENT '封面图',
    `price` DECIMAL(10,2) COMMENT '价格',
    `commission_rate` DECIMAL(5,2) COMMENT '佣金率',
    `shop_name` VARCHAR(200) COMMENT '店铺名称',
    `shop_id` VARCHAR(64) COMMENT '店铺ID',
    `category_name` VARCHAR(100) COMMENT '分类名称',
    `sell_num` BIGINT COMMENT '销量',
    `platform` VARCHAR(20) COMMENT '平台',
    `raw_data` JSON COMMENT '原始数据（完整JSON）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_product_id` (`product_id`),
    INDEX `idx_shop_id` (`shop_id`),
    INDEX `idx_category` (`category_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品详情表';

-- ============================================
-- 达人分析相关表
-- ============================================

-- 商品趋势分析
CREATE TABLE IF NOT EXISTS `analysis_goods_trend` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品趋势分析';

-- 达人TOP排行
CREATE TABLE IF NOT EXISTS `analysis_user_top` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='达人TOP排行';

-- 达人列表
CREATE TABLE IF NOT EXISTS `analysis_user_list` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='达人列表';

-- ============================================
-- 直播分析相关表
-- ============================================

-- 直播销售趋势
CREATE TABLE IF NOT EXISTS `analysis_live_trend` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播销售趋势';

-- 直播列表
CREATE TABLE IF NOT EXISTS `analysis_live_list` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播列表';

-- 直播关联分析
CREATE TABLE IF NOT EXISTS `analysis_live_relation` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播关联分析';

-- ============================================
-- 视频分析相关表
-- ============================================

-- 视频销售分析
CREATE TABLE IF NOT EXISTS `analysis_video_sales` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频销售分析';

-- 视频列表
CREATE TABLE IF NOT EXISTS `analysis_video_list` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频列表';

-- 视频时间分析
CREATE TABLE IF NOT EXISTS `analysis_video_time` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `raw_data` JSON COMMENT '原始数据',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_time_range` (`start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频时间分析';
