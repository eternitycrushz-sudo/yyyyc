# -*- coding: utf-8 -*-
"""
Task 任务管理器

原理讲解：
1. 每个爬虫任务都有一个 task_id，贯穿整个流程
2. task 表记录任务状态：pending → running → completed/failed
3. 支持事务回滚：异常时标记失败，可以重试
4. 子任务追踪：一个主任务可以有多个子任务（如爬取多个接口）

表结构：
- crawler_task: 主任务表
- crawler_task_detail: 子任务/步骤表
"""

import pymysql
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from contextlib import contextmanager

from logger import get_logger

log = get_logger("TaskManager")


class TaskStatus(Enum):
    """任务状态"""
    PENDING = 'pending'      # 等待执行
    RUNNING = 'running'      # 执行中
    COMPLETED = 'completed'  # 完成
    FAILED = 'failed'        # 失败
    CANCELLED = 'cancelled'  # 取消


class TaskManager:
    """
    任务管理器
    
    使用方式：
        tm = TaskManager(db_config)
        
        # 创建任务
        task_id = tm.create_task('list_crawler', {'start_page': 1, 'end_page': 10})
        
        # 更新状态
        tm.update_status(task_id, TaskStatus.RUNNING)
        
        # 记录子任务
        tm.add_detail(task_id, 'fetch_page_1', 'completed', {'count': 10})
        
        # 完成或失败
        tm.complete_task(task_id, result={'total': 100})
        tm.fail_task(task_id, error='连接超时')
    """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self._ensure_tables()
    
    def _get_conn(self):
        """获取数据库连接"""
        return pymysql.connect(
            **self.db_config,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        使用方式：
            with tm.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
                # 自动提交或回滚
        """
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error(f"事务回滚: {e}")
            raise
        finally:
            conn.close()
    
    def _ensure_tables(self):
        """确保任务表存在"""
        sqls = [
            # 主任务表
            """
            CREATE TABLE IF NOT EXISTS `crawler_task` (
                `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                `task_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '任务ID',
                `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型: list/detail/analysis',
                `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
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
            """,
            
            # 子任务/步骤表
            """
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
            """
        ]
        
        try:
            conn = self._get_conn()
            with conn.cursor() as cursor:
                for sql in sqls:
                    cursor.execute(sql)
            conn.commit()
            conn.close()
            log.debug("任务表检查完成")
        except Exception as e:
            log.error(f"创建任务表失败: {e}")
    
    def create_task(self, task_id: str, task_type: str, 
                    params: Dict = None, created_by: str = None,
                    total_steps: int = 0) -> str:
        """
        创建任务
        
        Args:
            task_id: 任务ID（外部传入，保证唯一）
            task_type: 任务类型
            params: 任务参数
            created_by: 创建人
            total_steps: 总步骤数
            
        Returns:
            task_id
        """
        import json
        
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO crawler_task 
                    (task_id, task_type, status, params, created_by, total_steps)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        status = VALUES(status),
                        params = VALUES(params),
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    task_id, task_type, TaskStatus.PENDING.value,
                    json.dumps(params or {}, ensure_ascii=False),
                    created_by, total_steps
                ))
            conn.commit()
            log.info(f"任务创建成功: {task_id}")
            return task_id
        finally:
            conn.close()
    
    def update_status(self, task_id: str, status: TaskStatus, 
                      progress: int = None, error_msg: str = None):
        """更新任务状态"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                updates = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
                values = [status.value]
                
                if status == TaskStatus.RUNNING:
                    updates.append("started_at = CURRENT_TIMESTAMP")
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    updates.append("completed_at = CURRENT_TIMESTAMP")
                
                if progress is not None:
                    updates.append("progress = %s")
                    values.append(progress)
                
                if error_msg:
                    updates.append("error_msg = %s")
                    values.append(error_msg)
                
                values.append(task_id)
                
                cursor.execute(f"""
                    UPDATE crawler_task SET {', '.join(updates)}
                    WHERE task_id = %s
                """, values)
            conn.commit()
        finally:
            conn.close()
    
    def update_progress(self, task_id: str, completed_steps: int, 
                        total_steps: int = None):
        """更新进度"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                if total_steps:
                    progress = int(completed_steps / total_steps * 100)
                    cursor.execute("""
                        UPDATE crawler_task 
                        SET completed_steps = %s, total_steps = %s, progress = %s
                        WHERE task_id = %s
                    """, (completed_steps, total_steps, progress, task_id))
                else:
                    cursor.execute("""
                        UPDATE crawler_task 
                        SET completed_steps = %s,
                            progress = CASE WHEN total_steps > 0 
                                THEN ROUND(completed_steps / total_steps * 100) 
                                ELSE 0 END
                        WHERE task_id = %s
                    """, (completed_steps, task_id))
            conn.commit()
        finally:
            conn.close()
    
    def add_detail(self, task_id: str, step_name: str, 
                   status: str = 'pending', params: Dict = None,
                   result: Dict = None, error_msg: str = None) -> int:
        """添加子任务/步骤"""
        import json
        
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO crawler_task_detail 
                    (task_id, step_name, status, params, result, error_msg,
                     started_at, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s,
                            CASE WHEN %s IN ('running', 'completed', 'failed') 
                                 THEN CURRENT_TIMESTAMP ELSE NULL END,
                            CASE WHEN %s IN ('completed', 'failed') 
                                 THEN CURRENT_TIMESTAMP ELSE NULL END)
                """, (
                    task_id, step_name, status,
                    json.dumps(params or {}, ensure_ascii=False) if params else None,
                    json.dumps(result or {}, ensure_ascii=False) if result else None,
                    error_msg, status, status
                ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def complete_task(self, task_id: str, result: Dict = None):
        """完成任务"""
        import json
        
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE crawler_task 
                    SET status = %s, progress = 100, result = %s,
                        completed_at = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                """, (
                    TaskStatus.COMPLETED.value,
                    json.dumps(result or {}, ensure_ascii=False),
                    task_id
                ))
            conn.commit()
            log.info(f"任务完成: {task_id}")
        finally:
            conn.close()
    
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        self.update_status(task_id, TaskStatus.FAILED, error_msg=error)
        log.error(f"任务失败: {task_id} - {error}")
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM crawler_task WHERE task_id = %s",
                    (task_id,)
                )
                return cursor.fetchone()
        finally:
            conn.close()
    
    def get_task_details(self, task_id: str) -> List[Dict]:
        """获取任务步骤明细"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM crawler_task_detail WHERE task_id = %s ORDER BY id",
                    (task_id,)
                )
                return cursor.fetchall()
        finally:
            conn.close()
