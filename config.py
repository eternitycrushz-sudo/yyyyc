# -*- coding: utf-8 -*-
"""
全局配置文件

原理：
1. 所有配置集中管理，方便修改
2. 支持从环境变量读取，方便部署
3. Flask、Worker 都读取这个配置
"""

import os


class Config:
    """基础配置"""
    
    # 数据库配置
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
    DB_NAME = os.getenv('DB_NAME', 'dy_analysis_system')
    
    # RabbitMQ 配置
    MQ_HOST = os.getenv('MQ_HOST', 'localhost')
    MQ_PORT = int(os.getenv('MQ_PORT', 5672))
    MQ_USER = os.getenv('MQ_USER', 'guest')
    MQ_PASSWORD = os.getenv('MQ_PASSWORD', 'guest')
    
    # API Token
    API_TOKEN = os.getenv('API_TOKEN', '45114cedfddd64db6b0c5f0acf929487')
    
    # 智谱 AI 配置
    ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY', '3abf3efec6b745e6a2762da34c7f5a03.1xgrVFKLsa8Df398')
    
    @classmethod
    def get_db_config(cls):
        """获取数据库配置字典"""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'database': cls.DB_NAME
        }
    
    @classmethod
    def get_mq_config(cls):
        """获取 MQ 配置字典"""
        return {
            'host': cls.MQ_HOST,
            'port': cls.MQ_PORT,
            'username': cls.MQ_USER,
            'password': cls.MQ_PASSWORD
        }


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


# 根据环境变量选择配置
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}

def get_config():
    """获取当前配置"""
    env = os.getenv('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
