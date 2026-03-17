-- ============================================
-- 清洗后数据表结构
-- 
-- 原理：
-- 1. 每个 *_raw 表对应一个清洗后的表
-- 2. 范围字段（如 range_last_price）拆分为 _min/_max 两列
-- 3. 数字字段使用 DECIMAL/BIGINT 存储
-- 4. 保留 raw_id 关联原始数据
-- ============================================

-- ============================================
-- 达人分析相关表
-- ============================================

-- 商品趋势（清洗后）
CREATE TABLE IF NOT EXISTS `analysis_goods_trend` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `date` VARCHAR(32) COMMENT '日期',
    `sales_count` BIGINT COMMENT '销量',
    `sales_amount` DECIMAL(20,2) COMMENT '销售额',
    `video_count` INT COMMENT '视频数',
    `live_count` INT COMMENT '直播数',
    `user_count` INT COMMENT '达人数',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品趋势（清洗后）';


-- 达人TOP排行（清洗后）
CREATE TABLE IF NOT EXISTS `analysis_user_top` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `user_id` VARCHAR(64) COMMENT '达人ID',
    `nickname` VARCHAR(255) COMMENT '达人昵称',
    `avatar` VARCHAR(512) COMMENT '头像URL',
    `rank` INT COMMENT '排名',
    `sales_count` BIGINT COMMENT '销量',
    `sales_amount` DECIMAL(20,2) COMMENT '销售额',
    `follower_count` BIGINT COMMENT '粉丝数',
    `video_count` INT COMMENT '视频数',
    `live_count` INT COMMENT '直播数',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_rank` (`rank`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='达人TOP排行（清洗后）';


-- 达人列表（清洗后）
-- 特点：范围字段已拆分为 _min/_max
CREATE TABLE IF NOT EXISTS `analysis_user_list` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `user_id` VARCHAR(64) COMMENT '达人ID',
    `nickname` VARCHAR(255) COMMENT '达人昵称',
    `avatar` VARCHAR(512) COMMENT '头像URL',
    `sec_uid` VARCHAR(128) COMMENT '达人sec_uid',
    
    `follower_count` BIGINT COMMENT '粉丝数',
    `video_count` INT COMMENT '视频数',
    `live_count` INT COMMENT '直播数',
    `sales_count` BIGINT COMMENT '销量',
    `sales_amount` DECIMAL(20,2) COMMENT '销售额',
    `avg_price` DECIMAL(10,2) COMMENT '平均价格',
    `commission_rate` DECIMAL(5,4) COMMENT '佣金率',
    
    -- 范围字段（已拆分）
    `range_last_price_min` DECIMAL(20,2) COMMENT '近期价格最小值',
    `range_last_price_max` DECIMAL(20,2) COMMENT '近期价格最大值',
    `range_last_sales_min` BIGINT COMMENT '近期销量最小值',
    `range_last_sales_max` BIGINT COMMENT '近期销量最大值',
    `range_follower_min` BIGINT COMMENT '粉丝范围最小值',
    `range_follower_max` BIGINT COMMENT '粉丝范围最大值',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_follower_count` (`follower_count`),
    INDEX `idx_sales_amount` (`sales_amount`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='达人列表（清洗后）';


-- ============================================
-- 直播分析相关表
-- ============================================

-- 直播趋势（清洗后）
CREATE TABLE IF NOT EXISTS `analysis_live_trend` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `date` VARCHAR(32) COMMENT '日期',
    `live_count` INT COMMENT '直播场次',
    `sales_count` BIGINT COMMENT '销量',
    `sales_amount` DECIMAL(20,2) COMMENT '销售额',
    `viewer_count` BIGINT COMMENT '观看人数',
    `avg_duration` INT COMMENT '平均时长(秒)',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播趋势（清洗后）';


-- 直播列表（清洗后）
CREATE TABLE IF NOT EXISTS `analysis_live_list` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `room_id` VARCHAR(64) COMMENT '直播间ID',
    `title` VARCHAR(512) COMMENT '直播标题',
    `cover` VARCHAR(512) COMMENT '封面图URL',
    `start_time` VARCHAR(32) COMMENT '开始时间',
    `end_time` VARCHAR(32) COMMENT '结束时间',
    
    `user_id` VARCHAR(64) COMMENT '主播ID',
    `nickname` VARCHAR(255) COMMENT '主播昵称',
    `avatar` VARCHAR(512) COMMENT '主播头像',
    
    `duration` INT COMMENT '时长(秒)',
    `viewer_count` BIGINT COMMENT '观看人数',
    `sales_count` BIGINT COMMENT '销量',
    `sales_amount` DECIMAL(20,2) COMMENT '销售额',
    `avg_price` DECIMAL(10,2) COMMENT '平均价格',
    `follower_count` BIGINT COMMENT '主播粉丝数',
    
    `range_sales_min` BIGINT COMMENT '销量范围最小值',
    `range_sales_max` BIGINT COMMENT '销量范围最大值',
    `range_amount_min` DECIMAL(20,2) COMMENT '销售额范围最小值',
    `range_amount_max` DECIMAL(20,2) COMMENT '销售额范围最大值',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_room_id` (`room_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_sales_amount` (`sales_amount`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播列表（清洗后）';


-- 直播关联（清洗后）
CREATE TABLE IF NOT EXISTS `analysis_live_relation` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `relation_type` VARCHAR(64) COMMENT '关联类型',
    `related_id` VARCHAR(64) COMMENT '关联ID',
    `related_name` VARCHAR(255) COMMENT '关联名称',
    `count` INT COMMENT '数量',
    `ratio` DECIMAL(5,4) COMMENT '占比',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_relation_type` (`relation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播关联（清洗后）';


-- ============================================
-- 视频分析相关表
-- ============================================

-- 视频销售（清洗后）
CREATE TABLE IF NOT EXISTS `analysis_video_sales` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `date` VARCHAR(32) COMMENT '日期',
    `video_count` INT COMMENT '视频数',
    `sales_count` BIGINT COMMENT '销量',
    `sales_amount` DECIMAL(20,2) COMMENT '销售额',
    `play_count` BIGINT COMMENT '播放量',
    `like_count` BIGINT COMMENT '点赞数',
    `comment_count` BIGINT COMMENT '评论数',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频销售（清洗后）';


-- 视频列表（清洗后）
CREATE TABLE IF NOT EXISTS `analysis_video_list` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `aweme_id` VARCHAR(64) COMMENT '视频ID',
    `title` VARCHAR(512) COMMENT '视频标题',
    `cover` VARCHAR(512) COMMENT '封面图URL',
    `publish_time` VARCHAR(32) COMMENT '发布时间',
    
    `user_id` VARCHAR(64) COMMENT '作者ID',
    `nickname` VARCHAR(255) COMMENT '作者昵称',
    `avatar` VARCHAR(512) COMMENT '作者头像',
    
    `duration` INT COMMENT '时长(秒)',
    `play_count` BIGINT COMMENT '播放量',
    `like_count` BIGINT COMMENT '点赞数',
    `comment_count` BIGINT COMMENT '评论数',
    `share_count` BIGINT COMMENT '分享数',
    `sales_count` BIGINT COMMENT '销量',
    `sales_amount` DECIMAL(20,2) COMMENT '销售额',
    `follower_count` BIGINT COMMENT '作者粉丝数',
    
    `range_sales_min` BIGINT COMMENT '销量范围最小值',
    `range_sales_max` BIGINT COMMENT '销量范围最大值',
    `range_amount_min` DECIMAL(20,2) COMMENT '销售额范围最小值',
    `range_amount_max` DECIMAL(20,2) COMMENT '销售额范围最大值',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_aweme_id` (`aweme_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_sales_amount` (`sales_amount`),
    INDEX `idx_play_count` (`play_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频列表（清洗后）';


-- 视频时间分布（清洗后）
CREATE TABLE IF NOT EXISTS `analysis_video_time` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `raw_id` BIGINT COMMENT '原始数据ID',
    `task_id` VARCHAR(64) COMMENT '任务ID',
    `goods_id` VARCHAR(64) NOT NULL COMMENT '商品ID',
    
    `hour` TINYINT COMMENT '小时(0-23)',
    `weekday` TINYINT COMMENT '星期几(0-6)',
    `video_count` INT COMMENT '视频数',
    `sales_count` BIGINT COMMENT '销量',
    `sales_amount` DECIMAL(20,2) COMMENT '销售额',
    `avg_play` BIGINT COMMENT '平均播放量',
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_goods_id` (`goods_id`),
    INDEX `idx_hour` (`hour`),
    INDEX `idx_weekday` (`weekday`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频时间分布（清洗后）';
