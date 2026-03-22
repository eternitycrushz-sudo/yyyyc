# -*- coding: utf-8 -*-
"""
清理 RabbitMQ 队列消息

使用方式：
    python clean_queues.py          # 交互式清理
    python clean_queues.py --force  # 强制清理（不询问）
"""

import sys
import os
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.mq.rabbitmq import RabbitMQClient
from config import Config

# MQ配置
MQ_CONFIG = Config.get_mq_config()

# 队列列表
QUEUES = ['list_q', 'detail_q', 'analysis_q']


def show_status(queues):
    """显示队列状态"""
    print("\n" + "=" * 60)
    print("RabbitMQ 队列状态")
    print("=" * 60)
    
    total_count = 0
    
    try:
        mq = RabbitMQClient(**MQ_CONFIG)
        
        for queue_name in queues:
            try:
                channel = mq._get_channel()
                method = channel.queue_declare(queue=queue_name, passive=True)
                count = method.method.message_count
                total_count += count
                print(f"{queue_name:20s}: {count:6d} 条消息")
            except Exception as e:
                print(f"{queue_name:20s}:      0 条消息")
        
        mq.close()
        
    except Exception as e:
        print(f"获取队列状态失败: {e}")
        return 0
    
    print("-" * 60)
    print(f"{'总计':20s}: {total_count:6d} 条消息")
    print("=" * 60)
    
    return total_count


def clean_queues(queues):
    """清理队列"""
    try:
        mq = RabbitMQClient(**MQ_CONFIG)
        
        for queue_name in queues:
            try:
                channel = mq._get_channel()
                channel.queue_purge(queue=queue_name)
                print(f"✓ 已清理队列: {queue_name}")
            except Exception as e:
                print(f"✗ 清理队列失败 {queue_name}: {e}")
        
        mq.close()
        
    except Exception as e:
        print(f"清理失败: {e}")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description='清理 RabbitMQ 队列消息')
    parser.add_argument('--force', action='store_true', help='强制清理，不询问确认')
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("RabbitMQ 队列清理工具")
    print("=" * 60)
    
    print("\n开始清理队列...")
    
    # 显示清理前状态
    print("\n清理前状态：")
    before_count = show_status(QUEUES)
    
    if before_count == 0:
        print("\n所有队列都是空的，无需清理。")
        return
    
    # 确认清理
    if not args.force:
        confirm = input(f"\n确定要清理 {len(QUEUES)} 个队列中的 {before_count} 条消息吗？(yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("\n已取消清理操作。")
            return
    
    # 执行清理
    print("\n正在清理...")
    if clean_queues(QUEUES):
        print("\n清理后状态：")
        show_status(QUEUES)
        print("\n✓ 清理完成！")
    else:
        print("\n✗ 清理失败！")


if __name__ == '__main__':
    main()
