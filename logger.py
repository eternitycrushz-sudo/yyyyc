# -*- coding: utf-8 -*-
"""
全局日志处理模块
支持控制台彩色输出、文件记录、日志轮转
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


class WinSafeRotatingFileHandler(RotatingFileHandler):
    """Windows 多进程安全的日志轮转处理器。

    Windows 不允许重命名被其他进程占用的文件，多个 Worker 进程同时
    轮转日志时会抛出 PermissionError [WinError 32]。
    此类在轮转失败时静默跳过，待下次触发时再尝试。
    """

    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            pass  # 另一进程正在占用，跳过本次轮转

    def emit(self, record):
        try:
            super().emit(record)
        except PermissionError:
            pass  # 写入冲突时静默跳过

# Windows 控制台颜色支持
if sys.platform == 'win32':
    os.system('')  # 启用 ANSI 转义码支持


class ColorFormatter(logging.Formatter):
    """带颜色的日志格式化器 - Level、类名、消息、线程名着色"""
    
    # ANSI 颜色码
    LEVEL_COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35;1m' # 紫色加粗
    }
    CYAN = '\033[36m'    # 青色 - 用于类名/模块名
    BLUE = '\033[34m'    # 蓝色 - 用于线程名
    RESET = '\033[0m'
    
    def format(self, record):
        # 保存原始值
        orig_levelname = record.levelname
        orig_name = record.name
        orig_module = record.module
        orig_funcName = record.funcName
        orig_msg = record.msg
        orig_threadName = record.threadName
        
        level_color = self.LEVEL_COLORS.get(record.levelname, '')
        
        # Level 着色
        record.levelname = f"{level_color}{record.levelname}{self.RESET}"
        
        # 模块/类名着色（青色）
        record.name = f"{self.CYAN}{record.name}{self.RESET}"
        record.module = f"{self.CYAN}{record.module}{self.RESET}"
        record.funcName = f"{self.CYAN}{record.funcName}{self.RESET}"
        
        # 线程名着色（蓝色）
        record.threadName = f"{self.BLUE}{record.threadName}{self.RESET}"
        
        # 消息内容着色（和Level同色）
        record.msg = f"{level_color}{record.msg}{self.RESET}"
        
        # 格式化
        result = super().format(record)
        
        # 恢复原始值
        record.levelname = orig_levelname
        record.name = orig_name
        record.module = orig_module
        record.funcName = orig_funcName
        record.msg = orig_msg
        record.threadName = orig_threadName
        return result


class LoggerManager:
    """日志管理器"""
    
    _loggers = {}
    _initialized = False
    _log_dir = "logs"
    _log_level = logging.DEBUG
    _console_level = logging.INFO
    _file_level = logging.DEBUG
    
    @classmethod
    def init(cls, log_dir="logs", log_level=logging.DEBUG, 
             console_level=logging.INFO, file_level=logging.DEBUG):
        """
        初始化日志配置
        
        Args:
            log_dir: 日志文件目录
            log_level: 全局日志级别
            console_level: 控制台输出级别
            file_level: 文件记录级别
        """
        cls._log_dir = log_dir
        cls._log_level = log_level
        cls._console_level = console_level
        cls._file_level = file_level
        cls._initialized = True
        
        # 创建日志目录
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    @classmethod
    def get_logger(cls, name=None, log_file=None):
        """
        获取日志记录器
        
        Args:
            name: 日志记录器名称，默认使用调用模块名
            log_file: 日志文件名，默认使用 name.log
            
        Returns:
            logging.Logger: 日志记录器实例
        """
        if not cls._initialized:
            cls.init()
        
        if name is None:
            name = "app"
        
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(cls._log_level)
        logger.handlers = []  # 清除已有处理器
        
        # 日志格式 - 包含线程名
        log_fmt = '%(asctime)s.%(msecs)03d [%(levelname)-8s] [%(threadName)s] %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s'
        date_fmt = '%Y-%m-%d %H:%M:%S'
        
        # 文件用普通格式
        file_formatter = logging.Formatter(fmt=log_fmt, datefmt=date_fmt)
        
        # 控制台用彩色格式
        color_formatter = ColorFormatter(fmt=log_fmt, datefmt=date_fmt)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls._console_level)
        console_handler.setFormatter(color_formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器 - 按大小轮转
        if log_file is None:
            log_file = f"{name}.log"
        
        log_path = os.path.join(cls._log_dir, log_file)
        file_handler = WinSafeRotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(cls._file_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 错误日志单独记录
        error_log_path = os.path.join(cls._log_dir, f"{name}_error.log")
        error_handler = WinSafeRotatingFileHandler(
            error_log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
        
        cls._loggers[name] = logger
        return logger


# 便捷函数
def get_logger(name=None, log_file=None):
    """获取日志记录器的便捷函数"""
    return LoggerManager.get_logger(name, log_file)


def init_logger(log_dir="logs", log_level=logging.DEBUG,
                console_level=logging.INFO, file_level=logging.DEBUG):
    """初始化日志配置的便捷函数"""
    LoggerManager.init(log_dir, log_level, console_level, file_level)


# 默认日志实例
logger = get_logger("crawler")


if __name__ == "__main__":
    # 测试示例
    init_logger(log_dir="logs")
    
    test_logger = get_logger("test")
    test_logger.debug("这是 DEBUG 信息")
    test_logger.info("这是 INFO 信息")
    test_logger.warning("这是 WARNING 信息")
    test_logger.error("这是 ERROR 信息")
    test_logger.critical("这是 CRITICAL 信息")
    
    print("\n日志测试完成，请查看 logs 目录")
