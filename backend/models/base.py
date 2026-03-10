# -*- coding: utf-8 -*-
"""
数据库基础操作
"""
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
        cursorclass=pymysql.cursors.DictCursor
    )


def init_tables():
    """
    初始化 RBAC 相关表
    
    表结构：
    - sys_user: 用户表
    - sys_role: 角色表
    - sys_permission: 权限表
    - sys_user_role: 用户-角色关联表
    - sys_role_permission: 角色-权限关联表
    """
    
    sqls = [
        # 用户表
        """
        CREATE TABLE IF NOT EXISTS `sys_user` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
            `password` VARCHAR(255) NOT NULL COMMENT '密码(加密)',
            `nickname` VARCHAR(50) COMMENT '昵称',
            `email` VARCHAR(100) COMMENT '邮箱',
            `phone` VARCHAR(20) COMMENT '手机号',
            `avatar` VARCHAR(255) COMMENT '头像URL',
            `status` TINYINT DEFAULT 1 COMMENT '状态: 1启用 0禁用',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_username` (`username`),
            INDEX `idx_status` (`status`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
        """,
        
        # 角色表
        """
        CREATE TABLE IF NOT EXISTS `sys_role` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `code` VARCHAR(50) NOT NULL UNIQUE COMMENT '角色编码',
            `name` VARCHAR(50) NOT NULL COMMENT '角色名称',
            `description` VARCHAR(200) COMMENT '描述',
            `status` TINYINT DEFAULT 1 COMMENT '状态: 1启用 0禁用',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_code` (`code`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';
        """,
        
        # 权限表
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
        
        # 用户-角色关联表
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
        
        # 角色-权限关联表
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
        
        # AI 会话表
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
        
        # AI 消息表
        """
        CREATE TABLE IF NOT EXISTS `ai_chat_message` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `session_id` INT NOT NULL,
            `role` VARCHAR(20) NOT NULL,
            `content` TEXT NOT NULL,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_session_id` (`session_id`),
            INDEX `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI会话消息表';
        """,
    ]
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for sql in sqls:
                cursor.execute(sql)
        conn.commit()
        print("RBAC 表初始化完成")
    finally:
        conn.close()


def init_default_data():
    """
    初始化默认数据：角色、权限、管理员账号
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查是否已有数据
            cursor.execute("SELECT COUNT(*) as cnt FROM sys_role")
            if cursor.fetchone()['cnt'] > 0:
                print("默认数据已存在，跳过初始化")
                return
            
            # 插入默认角色
            roles = [
                ('admin', '管理员', '系统管理员，拥有所有权限'),
                ('operator', '操作员', '可以执行爬虫任务'),
                ('viewer', '观察者', '只能查看数据')
            ]
            cursor.executemany(
                "INSERT INTO sys_role (code, name, description) VALUES (%s, %s, %s)",
                roles
            )
            
            # 插入默认权限
            permissions = [
                ('user:list', '用户列表', 'api', '查看用户列表'),
                ('user:create', '创建用户', 'api', '创建新用户'),
                ('user:update', '更新用户', 'api', '更新用户信息'),
                ('user:delete', '删除用户', 'api', '删除用户'),
                ('crawler:start', '启动爬虫', 'api', '启动爬虫任务'),
                ('crawler:stop', '停止爬虫', 'api', '停止爬虫任务'),
                ('crawler:view', '查看爬虫', 'api', '查看爬虫状态'),
                ('data:view', '查看数据', 'api', '查看分析数据'),
                ('data:export', '导出数据', 'api', '导出分析数据'),
            ]
            cursor.executemany(
                "INSERT INTO sys_permission (code, name, type, description) VALUES (%s, %s, %s, %s)",
                permissions
            )
            
            # 获取角色和权限ID
            cursor.execute("SELECT id, code FROM sys_role")
            role_map = {r['code']: r['id'] for r in cursor.fetchall()}
            
            cursor.execute("SELECT id, code FROM sys_permission")
            perm_map = {p['code']: p['id'] for p in cursor.fetchall()}
            
            # 分配权限给角色
            # admin 拥有所有权限
            for perm_id in perm_map.values():
                cursor.execute(
                    "INSERT INTO sys_role_permission (role_id, permission_id) VALUES (%s, %s)",
                    (role_map['admin'], perm_id)
                )
            
            # operator 拥有爬虫和数据查看权限
            operator_perms = ['crawler:start', 'crawler:stop', 'crawler:view', 'data:view']
            for perm_code in operator_perms:
                cursor.execute(
                    "INSERT INTO sys_role_permission (role_id, permission_id) VALUES (%s, %s)",
                    (role_map['operator'], perm_map[perm_code])
                )
            
            # viewer 只有查看权限
            viewer_perms = ['crawler:view', 'data:view']
            for perm_code in viewer_perms:
                cursor.execute(
                    "INSERT INTO sys_role_permission (role_id, permission_id) VALUES (%s, %s)",
                    (role_map['viewer'], perm_map[perm_code])
                )
            
            # 创建默认管理员账号 admin/admin123
            import hashlib
            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO sys_user (username, password, nickname) VALUES (%s, %s, %s)",
                ('admin', password_hash, '系统管理员')
            )
            admin_user_id = cursor.lastrowid
            
            # 给 admin 用户分配 admin 角色
            cursor.execute(
                "INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)",
                (admin_user_id, role_map['admin'])
            )
            
        conn.commit()
        print("默认数据初始化完成")
        print("默认管理员账号: admin / admin123")
        
    finally:
        conn.close()



