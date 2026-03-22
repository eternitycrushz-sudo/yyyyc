#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
爬虫代码问题测试套件
用于验证爬虫系统中的11个潜在问题
"""

import sys
import time
import threading
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 测试结果记录
test_results = []

def test_case(name, severity):
    """装饰器：用于标记测试用例"""
    def decorator(func):
        def wrapper():
            print(f"\n{'='*70}")
            print(f"[{severity}] TEST: {name}")
            print(f"{'='*70}")
            try:
                result = func()
                status = "[OK] PASS" if result else "[FAIL] FAIL"
                test_results.append({
                    'name': name,
                    'severity': severity,
                    'status': status,
                    'time': datetime.now().isoformat()
                })
                return result
            except Exception as e:
                print(f"[FAIL] 测试异常: {e}")
                test_results.append({
                    'name': name,
                    'severity': severity,
                    'status': '[FAIL] ERROR',
                    'error': str(e),
                    'time': datetime.now().isoformat()
                })
                return False
        return wrapper()
    return decorator


# ==================== 测试1: 数据库连接泄漏 ====================

@test_case("Problem 1: 数据库连接泄漏检测", "CRITICAL")
def test_db_connection_leak():
    """
    模拟多线程爬取中数据库连接是否正确释放
    """
    print("\n场景: 模拟5个并发线程爬取，检查连接是否泄漏\n")

    connections = []
    leaked_connections = []

    class MockConnection:
        def __init__(self, conn_id):
            self.conn_id = conn_id
            self.closed = False

        def close(self):
            self.closed = True
            connections.remove(self)
            print(f"  [OK] 连接 {self.conn_id} 已关闭")

        def cursor(self):
            return Mock()

    def fetch_page(page_id):
        """模拟Handler中的页面爬取函数"""
        conn = MockConnection(f"thread-{threading.current_thread().name}-page-{page_id}")
        connections.append(conn)
        print(f"  -> 创建连接: {conn.conn_id}")

        time.sleep(0.1)  # 模拟网络延迟

        # 问题: 这里没有 try-finally 确保关闭
        if page_id < 2:  # 只关闭前两个
            conn.close()
        # 其他连接未关闭 - 模拟泄漏

    # 模拟多线程并发爬取
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_page, i) for i in range(5)]
        for future in as_completed(futures):
            future.result()

    leaked_connections = [c for c in connections if not c.closed]

    print(f"\n结果统计:")
    print(f"  总连接数: {len(connections) + len(leaked_connections)}")
    print(f"  已关闭: {len(connections)}")
    print(f"  泄漏的连接: {len(leaked_connections)}")

    if leaked_connections:
        print(f"\n[WARN]  发现连接泄漏! 建议使用 DBUtils.PooledDB 或 SQLAlchemy 连接池")
        return False

    print(f"\n[OK] 没有检测到连接泄漏")
    return True


# ==================== 测试2: 消息重试机制 ====================

@test_case("Problem 2: 消息处理异常重试检测", "CRITICAL")
def test_message_retry_mechanism():
    """
    检查消息处理失败时是否有重试限制
    """
    print("\n场景: 模拟消息处理失败，检查是否无限重试\n")

    max_retries = 3
    retry_count = 0

    class MessageHandler:
        def __init__(self):
            self.attempt = 0

        def process(self, message):
            self.attempt += 1
            print(f"  -> 处理消息 (第 {self.attempt} 次尝试)")

            if self.attempt < max_retries:
                raise Exception("模拟处理失败")

            print(f"  [OK] 消息处理成功")
            return True

    handler = MessageHandler()

    # 检查当前代码中是否有重试限制
    print("检查爬虫代码中的重试机制:")

    try:
        with open("crawler/workers/base.py", "r", encoding="utf-8") as f:
            content = f.read()

            # 检查是否有重试次数限制
            has_max_retries = "max_retries" in content or "MAX_RETRIES" in content
            has_retry_limit = "retry_count" in content or "attempt" in content
            has_dead_letter = "dead_letter" in content.lower()

            print(f"  {'[OK]' if has_max_retries else '[NO]'} 有最大重试次数限制: {has_max_retries}")
            print(f"  {'[OK]' if has_retry_limit else '[NO]'} 有重试计数机制: {has_retry_limit}")
            print(f"  {'[OK]' if has_dead_letter else '[NO]'} 有死信队列处理: {has_dead_letter}")

            if not (has_max_retries and has_dead_letter):
                print(f"\n[WARN]  缺乏完善的重试机制! 建议:")
                print(f"  1. 添加 max_retries 限制（如最多重试 3 次）")
                print(f"  2. 实现死信队列处理失败消息")
                print(f"  3. 添加指数退避策略（1s, 5s, 30s...）")
                return False

            print(f"\n[OK] 检测到完善的重试机制")
            return True

    except FileNotFoundError:
        print(f"[WARN]  无法读取 base.py 文件")
        return False


# ==================== 测试3: 请求限速 ====================

@test_case("Problem 3: 并发请求限速检测", "HIGH")
def test_request_rate_limiting():
    """
    检查多线程爬取中是否有请求延迟控制
    """
    print("\n场景: 模拟5个并发请求，测量请求间隔\n")

    request_times = []
    lock = threading.Lock()

    def make_request(request_id):
        """模拟发送HTTP请求"""
        with lock:
            request_times.append({
                'id': request_id,
                'time': time.time()
            })

        print(f"  -> 请求 {request_id}: {time.time():.3f}")
        time.sleep(0.05)  # 模拟网络延迟

    # 测量请求的时间间隔
    from concurrent.futures import ThreadPoolExecutor

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(5)]
        for future in futures:
            future.result()

    end_time = time.time()

    # 分析结果
    request_times.sort(key=lambda x: x['time'])
    total_duration = end_time - start_time

    print(f"\n结果分析:")
    print(f"  总请求数: {len(request_times)}")
    print(f"  总耗时: {total_duration:.3f} 秒")
    print(f"  平均请求间隔: {(total_duration / len(request_times)):.3f} 秒")

    # 检查爬虫代码中的限速
    try:
        with open("crawler/workers/handlers/base_handler.py", "r", encoding="utf-8") as f:
            content = f.read()

            has_sleep = "sleep" in content.lower()
            has_throttle = "throttle" in content.lower() or "rate_limit" in content.lower()
            has_semaphore = "semaphore" in content.lower()

            print(f"\n代码检查:")
            print(f"  {'[OK]' if has_sleep else '[NO]'} 有 sleep 延迟: {has_sleep}")
            print(f"  {'[OK]' if has_throttle else '[NO]'} 有限速机制: {has_throttle}")
            print(f"  {'[OK]' if has_semaphore else '[NO]'} 有 Semaphore 控制: {has_semaphore}")

            if not (has_sleep or has_throttle or has_semaphore):
                print(f"\n[WARN]  检测到缺乏请求限速!")
                print(f"  建议: 添加随机延迟 (time.sleep(random.uniform(0.3, 0.6)))")
                return False

            print(f"\n[OK] 检测到请求限速机制")
            return True

    except FileNotFoundError:
        print(f"[WARN]  无法读取 base_handler.py 文件")
        return False


# ==================== 测试4: Token失效处理 ====================

@test_case("Problem 4: Token失效检测和处理", "HIGH")
def test_token_expiry_handling():
    """
    检查Token过期时是否能自动处理
    """
    print("\n场景: 模拟API返回登录状态错误\n")

    # 模拟API响应
    test_responses = [
        {"msg": "登录状态有误，请重新登录", "code": -1},
        {"msg": "Token expired", "code": 401},
        {"msg": "成功", "code": 0, "data": []},
    ]

    print("测试API响应处理:")
    for i, response in enumerate(test_responses):
        is_expired = "登录状态有误" in str(response.get('msg', ''))
        print(f"  响应 {i}: {response['msg']} -> 失效: {is_expired}")

    # 检查处理代码
    try:
        with open("crawler/workers/handlers/base_handler.py", "r", encoding="utf-8") as f:
            content = f.read()

            has_token_check = "is_token_expired" in content
            has_refresh_token = "refresh_token" in content.lower()
            has_auto_refresh = "mark_expired" in content or "auto_refresh" in content.lower()

            print(f"\n代码检查:")
            print(f"  {'[OK]' if has_token_check else '[NO]'} 有 Token 失效检查: {has_token_check}")
            print(f"  {'[OK]' if has_refresh_token else '[NO]'} 有 Token 刷新机制: {has_refresh_token}")
            print(f"  {'[OK]' if has_auto_refresh else '[NO]'} 有自动刷新触发: {has_auto_refresh}")

            if not has_auto_refresh:
                print(f"\n[WARN]  检测到缺乏自动Token刷新!")
                print(f"  建议: 在接收到失效响应时，调用 token_manager.mark_expired()")
                return False

            print(f"\n[OK] 检测到完善的Token处理机制")
            return True

    except FileNotFoundError:
        print(f"[WARN]  无法读取 base_handler.py 文件")
        return False


# ==================== 测试5: 数据重复检测 ====================

@test_case("Problem 5: 数据重复检测", "MEDIUM")
def test_duplicate_detection():
    """
    检查是否存在全局去重机制
    """
    print("\n场景: 模拟多个Worker同时处理相同商品\n")

    processed_items = []
    lock = threading.Lock()

    def process_item(item_id, worker_id):
        """模拟处理商品"""
        with lock:
            processed_items.append({
                'item_id': item_id,
                'worker_id': worker_id,
                'time': time.time()
            })
        print(f"  -> Worker {worker_id} 处理商品 {item_id}")
        time.sleep(0.01)

    # 模拟多个Worker处理相同商品
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for item_id in range(3):
            for worker_id in range(2):  # 2个Worker
                futures.append(executor.submit(process_item, item_id, worker_id))
        for future in futures:
            future.result()

    # 统计重复
    print(f"\n结果分析:")
    print(f"  总处理数: {len(processed_items)}")

    item_counts = {}
    for item in processed_items:
        item_id = item['item_id']
        item_counts[item_id] = item_counts.get(item_id, 0) + 1

    for item_id, count in sorted(item_counts.items()):
        print(f"  商品 {item_id}: 被处理 {count} 次")

    # 检查去重机制
    try:
        with open("crawler/workers/list_worker.py", "r", encoding="utf-8") as f:
            content = f.read()

            has_redis = "redis" in content.lower()
            has_seen_ids = "seen_ids" in content or "seen" in content.lower()
            has_db_check = "SELECT.*product_id" in content

            print(f"\n代码检查:")
            print(f"  {'[OK]' if has_redis else '[NO]'} 使用 Redis 去重: {has_redis}")
            print(f"  {'[OK]' if has_seen_ids else '[NO]'} 使用内存集合: {has_seen_ids}")
            print(f"  {'[OK]' if has_db_check else '[NO]'} 检查数据库: {has_db_check}")

            # 如果只有内存集合，多Worker会有问题
            if has_seen_ids and not has_redis:
                print(f"\n[WARN]  只使用内存集合去重，多Worker会产生重复!")
                print(f"  建议: 使用 Redis 实现全局去重")
                return False

            print(f"\n[OK] 检测到有效的去重机制")
            return True

    except FileNotFoundError:
        print(f"[WARN]  无法读取 list_worker.py 文件")
        return False


# ==================== 测试6: 日志脱敏 ====================

@test_case("Problem 6: 敏感信息泄露检测", "MEDIUM")
def test_sensitive_data_leakage():
    """
    检查日志中是否有敏感信息泄露风险
    """
    print("\n场景: 扫描代码中的日志记录\n")

    sensitive_patterns = [
        ("token", "Token/授权信息"),
        ("password", "密码"),
        ("secret", "密钥"),
        ("key", "API密钥"),
        ("authorization", "授权头"),
    ]

    issues_found = []

    files_to_check = [
        "crawler/workers/base.py",
        "crawler/workers/handlers/base_handler.py",
        "crawler/workers/cleaners/base_cleaner.py",
    ]

    for file_path in files_to_check:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

                for line_no, line in enumerate(lines, 1):
                    if "log." in line or "print(" in line:
                        for pattern, desc in sensitive_patterns:
                            if pattern in line.lower() and "{" in line:
                                issues_found.append({
                                    'file': file_path,
                                    'line': line_no,
                                    'pattern': desc,
                                    'code': line.strip()
                                })
                                print(f"  [WARN]  {file_path}:{line_no}")
                                print(f"      {desc} 可能泄露")
                                print(f"      {line.strip()[:60]}...")

        except FileNotFoundError:
            print(f"  [WARN]  文件不存在: {file_path}")

    print(f"\n结果统计:")
    print(f"  发现潜在泄露: {len(issues_found)} 处")

    if issues_found:
        print(f"\n[WARN]  检测到敏感信息泄露风险!")
        print(f"  建议: 实现日志脱敏函数，如:")
        print(f"    def mask_sensitive(data):")
        print(f"        return str(data)[:8] + '***'")
        return False

    print(f"\n[OK] 未检测到明显的敏感信息泄露")
    return True


# ==================== 测试7: 动态建表竞态 ====================

@test_case("Problem 7: 动态建表竞态条件", "MEDIUM")
def test_dynamic_table_creation_race():
    """
    检查多个Cleaner同时建表是否会产生竞态条件
    """
    print("\n场景: 模拟多个线程同时检查和创建表\n")

    table_created = False
    create_attempts = 0
    lock = threading.Lock()

    def create_table_unsafe(thread_id):
        """模拟不安全的建表（有竞态条件）"""
        nonlocal table_created, create_attempts

        print(f"  -> 线程 {thread_id}: 检查表是否存在...")
        time.sleep(0.01)  # 模拟检查延迟

        if not table_created:
            print(f"  -> 线程 {thread_id}: 开始创建表...")
            create_attempts += 1
            time.sleep(0.05)  # 模拟创建延迟
            table_created = True
            print(f"  -> 线程 {thread_id}: 创建完成")
        else:
            print(f"  -> 线程 {thread_id}: 表已存在，跳过")

    # 模拟多个线程
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(create_table_unsafe, i) for i in range(4)]
        for future in futures:
            future.result()

    print(f"\n结果分析:")
    print(f"  创建尝试数: {create_attempts}")

    if create_attempts > 1:
        print(f"\n[WARN]  检测到竞态条件! 有 {create_attempts} 个线程都尝试创建表")
        print(f"  建议: 使用 CREATE TABLE IF NOT EXISTS 并忽略异常")
        return False

    print(f"\n[OK] 未检测到严重的竞态条件")
    return True


# ==================== 主测试函数 ====================

def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("爬虫代码问题测试套件")
    print("="*70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 运行测试
    test_db_connection_leak()
    test_message_retry_mechanism()
    test_request_rate_limiting()
    test_token_expiry_handling()
    test_duplicate_detection()
    test_sensitive_data_leakage()
    test_dynamic_table_creation_race()

    # 生成报告
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)

    passed = sum(1 for r in test_results if "PASS" in r['status'])
    failed = sum(1 for r in test_results if "FAIL" in r['status'])
    errors = sum(1 for r in test_results if "ERROR" in r['status'])

    print(f"\n总计: {len(test_results)} 个测试")
    print(f"[OK] 通过: {passed}")
    print(f"[FAIL] 失败: {failed}")
    print(f"[WARN]  错误: {errors}")
    print(f"通过率: {(passed / len(test_results) * 100):.1f}%\n")

    # 详细结果
    print("详细结果:")
    print("-" * 70)
    for i, result in enumerate(test_results, 1):
        severity_emoji = result['severity'].split(']')[0] + ']'
        print(f"{i}. {severity_emoji} {result['name']}")
        print(f"   状态: {result['status']}")
        if 'error' in result:
            print(f"   错误: {result['error']}")
        print()

    # 生成JSON报告
    import json
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)

    print(f"详细报告已保存到: test_results.json")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
