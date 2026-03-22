-- ============================================
-- 商品分析系统数据库表结构 V2
-- 
-- 改进：
-- 1. 原始数据表加 _raw 后缀
-- 2. 添加 task_id 关联
-- 3. 添加 is_cleaned 标记
-- 4. 任务管理表
-- ============================================

-- ============================================
-- 任务管理表
-- ============================================

-- 主任务表
CREATE TABLE IF NOT EXISTS `crawler_task` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '任务ID',
    `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型: list/detail/analysis',
    `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/running/completed/failed/cancelled',
    `params` JSON COMMENT '任务参数',
    `result` JSON COMMENT '执行结果',
    `error_msg` TEXT COMMENT '错误信息',
    `progress` INT DEFAULT 0 COMMENT '进度 0-100',
    `total_steps` INT DEFAULT 0 COMMENT '总步骤数',
    `completed_steps` INT DEFAULT 0 COMMENT '已完成步骤',
    `created_by` VARCHAR(50) COMMENT '创建人',
    `started_at` TIMESTAMP NULL COMMENT '开始时间',
    `completed_at` TIMESTAMP NULL COMMENT '完成时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_task_type` (`task_type`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬虫任务表';

-- 任务步骤明细表
CREATE TABLE IF NOT EXISTS `crawler_task_detail` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '主任务ID',
    `step_name` VARCHAR(100) NOT NULL COMMENT '步骤名称',
    `step_type` VARCHAR(50) COMMENT '步骤类型',
    `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    `params` JSON COMMENT '步骤参数',
    `result` JSON COMMENT '执行结果',
    `error_msg` TEXT COMMENT '错误信息',
    `retry_count` INT DEFAULT 0 COMMENT '重试次数',
    `started_at` TIMESTAMP NULL,
    `completed_at` TIMESTAMP NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务步骤明细表';

-- ============================================
-- 达人分析原始数据表
-- ============================================

-- 商品趋势原始数据
CREATE TABLE IF NOT EXISTS `analysis_goods_trend_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗: 0否 1是',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品趋势原始数据';

-- 达人TOP原始数据
CREATE TABLE IF NOT EXISTS `analysis_user_top_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='达人TOP原始数据';

-- 达人列表原始数据
CREATE TABLE IF NOT EXISTS `analysis_user_list_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_page_no` (`page_no`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='达人列表原始数据';

-- ============================================
-- 直播分析原始数据表
-- ============================================

-- 直播趋势原始数据
CREATE TABLE IF NOT EXISTS `analysis_live_trend_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播趋势原始数据';

-- 直播列表原始数据
CREATE TABLE IF NOT EXISTS `analysis_live_list_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_page_no` (`page_no`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播列表原始数据';

-- 直播关联原始数据
CREATE TABLE IF NOT EXISTS `analysis_live_relation_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播关联原始数据';

-- ============================================
-- 视频分析原始数据表
-- ============================================

-- 视频销售原始数据
CREATE TABLE IF NOT EXISTS `analysis_video_sales_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频销售原始数据';

-- 视频列表原始数据
CREATE TABLE IF NOT EXISTS `analysis_video_list_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_page_no` (`page_no`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频列表原始数据';

-- 视频时间原始数据
CREATE TABLE IF NOT EXISTS `analysis_video_time_raw` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    `start_time` BIGINT COMMENT '查询开始时间(毫秒)',
    `end_time` BIGINT COMMENT '查询结束时间(毫秒)',
    `page_no` INT DEFAULT 1 COMMENT '页码',
    `raw_data` JSON COMMENT '原始响应数据',
    `data_count` INT DEFAULT 0 COMMENT '数据条数',
    `is_cleaned` TINYINT DEFAULT 0 COMMENT '是否已清洗',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_is_cleaned` (`is_cleaned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频时间原始数据';
