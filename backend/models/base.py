# -*- coding: utf-8 -*-
"""
数据库基础操作
"""
import hashlib

import pymysql

from backend.config import Config


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )


def init_tables():
    """初始化系统表结构"""
    sqls = [
        """
        CREATE TABLE IF NOT EXISTS `sys_user` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
            `password` VARCHAR(255) NOT NULL COMMENT '密码(加密)',
            `nickname` VARCHAR(50) COMMENT '昵称',
            `email` VARCHAR(100) COMMENT '邮箱',
            `phone` VARCHAR(20) COMMENT '手机号',
            `avatar` VARCHAR(255) COMMENT '头像URL',
            `status` TINYINT DEFAULT 1 COMMENT '状态 1启用 0禁用',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_username` (`username`),
            INDEX `idx_status` (`status`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `sys_role` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `code` VARCHAR(50) NOT NULL UNIQUE COMMENT '角色编码',
            `name` VARCHAR(50) NOT NULL COMMENT '角色名称',
            `description` VARCHAR(200) COMMENT '描述',
            `status` TINYINT DEFAULT 1 COMMENT '状态 1启用 0禁用',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_code` (`code`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `sys_permission` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `code` VARCHAR(100) NOT NULL UNIQUE COMMENT '权限编码，如 crawler:start',
            `name` VARCHAR(50) NOT NULL COMMENT '权限名称',
            `type` VARCHAR(20) DEFAULT 'api' COMMENT '类型: menu/button/api',
            `description` VARCHAR(200) COMMENT '描述',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_code` (`code`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `sys_user_role` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `user_id` INT NOT NULL,
            `role_id` INT NOT NULL,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
            INDEX `idx_user_id` (`user_id`),
            INDEX `idx_role_id` (`role_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `sys_role_permission` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `role_id` INT NOT NULL,
            `permission_id` INT NOT NULL,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY `uk_role_permission` (`role_id`, `permission_id`),
            INDEX `idx_role_id` (`role_id`),
            INDEX `idx_permission_id` (`permission_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `sys_operation_log` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `user_id` INT COMMENT '用户ID',
            `username` VARCHAR(50) COMMENT '用户名',
            `action` VARCHAR(100) COMMENT '操作动作',
            `module` VARCHAR(100) COMMENT '操作模块',
            `detail` TEXT COMMENT '操作详情',
            `ip` VARCHAR(50) COMMENT 'IP地址',
            `status` TINYINT DEFAULT 1 COMMENT '状态：1成功 0失败',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_user_id` (`user_id`),
            INDEX `idx_action` (`action`),
            INDEX `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `ai_chat_session` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `user_id` INT NOT NULL,
            `session_id` VARCHAR(64) NOT NULL,
            `title` VARCHAR(100) NULL,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY `uk_user_session` (`user_id`, `session_id`),
            INDEX `idx_user_id` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI会话表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `ai_chat_message` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `session_id` VARCHAR(64) NOT NULL,
            `role` VARCHAR(20) NOT NULL,
            `content` TEXT NOT NULL,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_session_id` (`session_id`),
            INDEX `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI会话消息表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `crawler_task_log` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `task_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '任务ID',
            `task_type` VARCHAR(50) COMMENT '任务类型: list/detail/analysis',
            `params` TEXT COMMENT '任务参数(JSON)',
            `user_id` INT COMMENT '发起人ID',
            `username` VARCHAR(50) COMMENT '发起人用户名',
            `status` VARCHAR(20) DEFAULT 'sent' COMMENT '状态: sent/running/completed/failed/dead_letter',
            `result` VARCHAR(500) DEFAULT '' COMMENT '执行结果摘要',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_task_id` (`task_id`),
            INDEX `idx_status` (`status`),
            INDEX `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬虫任务日志表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `sys_password_reset_request` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `username` VARCHAR(50) NOT NULL COMMENT '申请重置的用户名',
            `reason` VARCHAR(500) DEFAULT '' COMMENT '申请原因',
            `status` TINYINT DEFAULT 0 COMMENT '0=待处理 1=已通过 2=已拒绝',
            `temporary_password` VARCHAR(100) DEFAULT '' COMMENT '管理员设置的临时密码',
            `handler_id` INT NULL COMMENT '处理管理员ID',
            `handler_username` VARCHAR(50) NULL COMMENT '处理管理员用户名',
            `handled_at` TIMESTAMP NULL COMMENT '处理时间',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_status` (`status`),
            INDEX `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='密码重置申请表';
        """,
        """
        CREATE TABLE IF NOT EXISTS `sys_notification` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `user_id` INT NULL COMMENT '目标用户ID',
            `type` VARCHAR(20) DEFAULT 'info' COMMENT '通知类型',
            `title` VARCHAR(200) NOT NULL COMMENT '通知标题',
            `content` TEXT COMMENT '通知内容',
            `source` VARCHAR(50) DEFAULT '' COMMENT '来源',
            `is_read` TINYINT DEFAULT 0 COMMENT '0未读 1已读',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_user_id` (`user_id`),
            INDEX `idx_is_read` (`is_read`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统通知表';
        """,
    ]

    alter_sqls = [
        "ALTER TABLE `sys_user` ADD COLUMN `force_pwd_change` TINYINT DEFAULT 0 COMMENT '是否强制修改密码: 1=是 0=否'",
        "ALTER TABLE `sys_password_reset_request` ADD COLUMN `temporary_password` VARCHAR(100) DEFAULT '' COMMENT '管理员设置的临时密码'",
    ]

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for sql in sqls:
                cursor.execute(sql)
            for sql in alter_sqls:
                try:
                    cursor.execute(sql)
                except Exception:
                    pass
        conn.commit()
        print("RBAC 表初始化完成")
    finally:
        conn.close()


def init_default_data():
    """初始化默认角色、权限和管理员账号"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM sys_role")
            if cursor.fetchone()['cnt'] > 0:
                print("默认数据已存在，跳过初始化")
                return

            roles = [
                ('admin', '管理员', '系统管理员，拥有所有权限'),
                ('operator', '操作员', '可以执行爬虫任务'),
                ('viewer', '观察者', '只能查看数据'),
            ]
            cursor.executemany(
                "INSERT INTO sys_role (code, name, description) VALUES (%s, %s, %s)",
                roles,
            )

            permissions = [
                ('user:list', '用户列表', 'api', '查看用户列表'),
                ('user:create', '创建用户', 'api', '创建新用户'),
                ('user:update', '更新用户', 'api', '更新用户信息'),
                ('user:delete', '删除用户', 'api', '删除用户'),
                ('crawler:start', '启动爬虫', 'api', '启动爬虫任务'),
                ('crawler:stop', '停止爬虫', 'api', '停止爬虫任务'),
                ('crawler:view', '查看爬虫', 'api', '查看爬虫状态'),
                ('crawler:clean', '数据清洗', 'api', '执行数据清洗'),
                ('data:view', '查看数据', 'api', '查看分析数据'),
                ('data:export', '导出数据', 'api', '导出分析数据'),
            ]
            cursor.executemany(
                "INSERT INTO sys_permission (code, name, type, description) VALUES (%s, %s, %s, %s)",
                permissions,
            )

            cursor.execute("SELECT id, code FROM sys_role")
            role_map = {row['code']: row['id'] for row in cursor.fetchall()}

            cursor.execute("SELECT id, code FROM sys_permission")
            perm_map = {row['code']: row['id'] for row in cursor.fetchall()}

            for perm_id in perm_map.values():
                cursor.execute(
                    "INSERT INTO sys_role_permission (role_id, permission_id) VALUES (%s, %s)",
                    (role_map['admin'], perm_id),
                )

            for perm_code in ['crawler:start', 'crawler:stop', 'crawler:view', 'crawler:clean', 'data:view', 'data:export']:
                cursor.execute(
                    "INSERT INTO sys_role_permission (role_id, permission_id) VALUES (%s, %s)",
                    (role_map['operator'], perm_map[perm_code]),
                )

            for perm_code in ['crawler:view', 'data:view']:
                cursor.execute(
                    "INSERT INTO sys_role_permission (role_id, permission_id) VALUES (%s, %s)",
                    (role_map['viewer'], perm_map[perm_code]),
                )

            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO sys_user (username, password, nickname) VALUES (%s, %s, %s)",
                ('admin', password_hash, '系统管理员'),
            )
            admin_user_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)",
                (admin_user_id, role_map['admin']),
            )

        conn.commit()
        print("默认数据初始化完成")
        print("默认管理员账号: admin / admin123")
    finally:
        conn.close()
