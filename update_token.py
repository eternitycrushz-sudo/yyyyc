# -*- coding: utf-8 -*-
"""
快速 Token 更新工具

用法:
    python update_token.py <TOKEN>

例如:
    python update_token.py aaaabbbbccccdddd1111222233334444
"""

import sys
import os
import re

def update_token(new_token):
    """更新项目中的 Token"""

    # 验证 Token 格式
    new_token = new_token.strip().lower()

    if len(new_token) != 32:
        print(f"ERROR: Token 长度为 {len(new_token)}，期望 32 位")
        return False

    if not all(c in '0123456789abcdef' for c in new_token):
        print("ERROR: Token 必须是 32 位十六进制字符串")
        return False

    print(f"Token: {new_token}")
    print("\n开始更新项目文件...")

    project_root = os.path.dirname(os.path.abspath(__file__))

    # 需要更新的文件
    files_to_update = [
        "config.py",
        "backend/config.py",
        "crawler/workers/handlers/base_handler.py",
        "crawler/workers/list_worker.py",
        "crawler/workers/detail_worker.py",
        "crawler/dy_xingtui/ShopCrawler.py",
    ]

    updated_count = 0

    for rel_path in files_to_update:
        filepath = os.path.join(project_root, rel_path)

        if not os.path.exists(filepath):
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 用正则表达式替换 Token
        new_content = re.sub(
            r'(["\'])([a-f0-9]{32})\1',
            rf'\g<1>{new_token}\g<1>',
            content
        )

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  OK - {rel_path}")
            updated_count += 1

    # 写入 token.txt
    token_file = os.path.join(project_root, "token.txt")
    with open(token_file, 'w', encoding='utf-8') as f:
        f.write(new_token)
    print(f"  OK - token.txt")

    print("\n" + "=" * 60)
    print("Token 更新完成!")
    print("=" * 60)
    print(f"\n已更新 {updated_count} 个源代码文件")
    print("已写入 token.txt")
    print("\nWorker 无需重启，下次请求时自动加载新 Token")

    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python update_token.py <TOKEN>")
        print("\n例如:")
        print("  python update_token.py aaaabbbbccccdddd1111222233334444")
        sys.exit(1)

    token = sys.argv[1]
    success = update_token(token)
    sys.exit(0 if success else 1)
