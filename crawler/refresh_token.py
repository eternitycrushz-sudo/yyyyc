# -*- coding: utf-8 -*-
"""
热度星推 Token 刷新工具

使用方式：
    python crawler/refresh_token.py

流程：
    1. 获取图形验证码 key
    2. 输入手机号
    3. 发送短信验证码
    4. 输入验证码完成登录
    5. 自动更新项目中所有 TOKEN
"""

import sys
import os
import re
import json
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawler.dy_xingtui.ReduxSiger import ReduxSigner

BASE_URL = ReduxSigner.BASE_URL

# 需要更新 TOKEN 的文件列表
TOKEN_FILES = [
    "crawler/workers/handlers/base_handler.py",
    "crawler/workers/list_worker.py",
    "crawler/workers/detail_worker.py",
    "crawler/workers/debug_api.py",
    "crawler/dy_xingtui/ShopCrawler.py",
    "config.py",
    "backend/config.py",
]


def signed_get(path, params=None):
    """带签名的 GET 请求"""
    if params is None:
        params = {}
    ts = ReduxSigner.get_timestamp_by_server()
    signer = ReduxSigner.get_siger_by_params(params, ts)
    headers = ReduxSigner.get_headers(signer['header_sign'], signer['timestamp'], '')
    query_params = params.copy()
    query_params['sign'] = signer['url_sign']
    query_params['time'] = signer['timestamp']
    url = f"{BASE_URL}/api{path}"
    resp = requests.get(url, params=query_params, headers=headers, timeout=15)
    return resp.json()


def signed_post(path, data=None):
    """带签名的 POST 请求"""
    if data is None:
        data = {}
    ts = ReduxSigner.get_timestamp_by_server()
    signer = ReduxSigner.get_siger_by_params(data, ts)
    headers = ReduxSigner.get_headers(signer['header_sign'], signer['timestamp'], '')
    headers['Content-Type'] = 'application/json'
    post_data = data.copy()
    post_data['sign'] = signer['url_sign']
    post_data['time'] = signer['timestamp']
    url = f"{BASE_URL}/api{path}"
    resp = requests.post(url, json=post_data, headers=headers, timeout=15)
    return resp.json()


def get_verify_key():
    """获取图形验证码 key"""
    result = signed_get("/verify_code")
    if result.get("data") and result["data"].get("key"):
        return result["data"]["key"]
    # 有些接口直接返回 key
    if result.get("key"):
        return result["key"]
    print(f"  接口返回: {json.dumps(result, ensure_ascii=False)}")
    return None


def send_sms_code(key, phone):
    """发送短信验证码"""
    result = signed_post("/register/verify", {
        "key": key,
        "phone": phone,
        "type": "login"
    })
    return result


def login_by_mobile(phone, code):
    """手机号验证码登录"""
    result = signed_post("/login/mobile", {
        "phone": phone,
        "code": code
    })
    return result


def update_token_in_files(new_token, old_token=None, project_root=None):
    """更新项目中所有文件的 TOKEN，并写入 token.txt"""
    if project_root is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    updated = []
    for rel_path in TOKEN_FILES:
        filepath = os.path.join(project_root, rel_path)
        if not os.path.exists(filepath):
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content
        if old_token and old_token in content:
            new_content = content.replace(old_token, new_token)
        else:
            # 正则替换 TOKEN = "xxx" 模式
            new_content = re.sub(
                r'(TOKEN\s*=\s*["\'])([a-f0-9]{32})(["\'])',
                rf'\g<1>{new_token}\g<3>',
                new_content
            )
            new_content = re.sub(
                r"('API_TOKEN',\s*['\"])([a-f0-9]{32})(['\"])",
                rf"\g<1>{new_token}\g<3>",
                new_content
            )

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated.append(rel_path)

    # 写入 token.txt（新增）
    token_file_path = os.path.join(project_root, "token.txt")
    try:
        from crawler.token_manager import write_token_file
        write_token_file(new_token)
    except Exception as e:
        # fallback：如果 token_manager 导入失败，直接写文件
        with open(token_file_path, 'w', encoding='utf-8') as f:
            f.write(new_token.strip())

    return updated


def main():
    print("=" * 50)
    print("  热度星推 (reduxingtui.com) Token 刷新工具")
    print("=" * 50)
    print()

    old_token = "45114cedfddd64db6b0c5f0acf929487"
    print(f"当前 Token: {old_token}")
    print()
    print("请选择操作：")
    print("  1. 手机号短信登录获取 Token")
    print("  2. 直接输入 Token（从浏览器复制）")
    print()
    choice = input("请选择 (1/2): ").strip()

    if choice == "2":
        token = input("请粘贴新的 Token: ").strip()
        if not token:
            print("Token 不能为空")
            return
    elif choice == "1":
        # 获取验证码 key
        print()
        print("[1/4] 获取验证码 key...")
        key = get_verify_key()
        if not key:
            print("获取失败，请尝试方式2（从浏览器复制 Token）")
            return
        print(f"  key: {key}")

        # 输入手机号
        print()
        phone = input("[2/4] 请输入注册手机号: ").strip()
        if not phone or len(phone) != 11:
            print("手机号格式不正确")
            return

        # 发送短信
        print(f"[3/4] 向 {phone} 发送短信验证码...")
        sms_result = send_sms_code(key, phone)
        msg = sms_result.get('msg', str(sms_result))
        print(f"  结果: {msg}")

        if sms_result.get("status") not in (200, None) and "成功" not in msg:
            retry = input("  发送可能失败，是否继续输入验证码? (y/n): ").strip().lower()
            if retry != 'y':
                return

        # 输入验证码
        print()
        code = input("[4/4] 请输入短信验证码: ").strip()
        if not code:
            print("验证码不能为空")
            return

        # 登录
        print("正在登录...")
        login_result = login_by_mobile(phone, code)
        print(f"  结果: {json.dumps(login_result, ensure_ascii=False)}")

        token = None
        if login_result.get("data"):
            data = login_result["data"]
            token = data.get("token") or data.get("access_token") or data.get("token_new")
            if token:
                print(f"\n  新 Token: {token}")

        if not token:
            print()
            token = input("未自动提取到 Token，请手动输入: ").strip()
            if not token:
                return
    else:
        print("无效选择")
        return

    # 更新文件
    print(f"\n正在更新项目文件中的 Token...")
    updated = update_token_in_files(token, old_token)
    if updated:
        print(f"  已更新 {len(updated)} 个文件:")
        for f in updated:
            print(f"    - {f}")
    else:
        print("  没有文件需要更新（Token 可能相同）")

    print()
    print("完成! token.txt 已更新，Worker 进程将在下次请求时自动加载新 Token，无需重启。")
    print("如果 Worker 已停止，重启命令：python crawler/workers/run_workers.py")


if __name__ == '__main__':
    main()
