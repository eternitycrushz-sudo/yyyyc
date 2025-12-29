#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Flask框架的抖音电商热点数据可视化分析系统 - 爬虫模块
目标URL: https://fxg.jinritemai.com/ffa/mshop/homepage/index
"""

import time
import json
import csv
import os
import threading
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd


class DouyinCrawler:
    """抖音电商爬虫类"""
    
    def __init__(self, driver_path=None):
        """
        初始化爬虫
        :param driver_path: ChromeDriver路径，如果为None则需要手动指定
        """
        self.driver_path = driver_path
        self.driver = None
        self.wait = None
        self.target_url = "https://fxg.jinritemai.com/ffa/mshop/homepage/index"
        self.cookie_file = "douyin_cookies.json"
        self.api_data_file = "api_responses.json"
        self.captured_apis = []  # 存储捕获的API数据
        
    def setup_driver(self):
        """配置Chrome浏览器驱动，启用网络日志捕获"""
        try:
            # Chrome浏览器选项配置
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 网络优化配置
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-infobars')
            
            # 启用性能日志，用于捕获网络请求
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # 使用用户数据目录，保留缓存和登录状态
            user_data_dir = os.path.join(os.getcwd(), "../chrome_user_data")
            chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
            
            # 设置用户代理
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 优先使用手动指定的驱动路径，否则使用webdriver-manager自动管理
            if self.driver_path and os.path.exists(self.driver_path):
                print(f"使用指定的ChromeDriver: {self.driver_path}")
                service = Service(self.driver_path)
            else:
                print("使用webdriver-manager自动下载匹配的ChromeDriver...")
                service = Service(ChromeDriverManager().install())
                
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
            # 设置隐式等待和显式等待
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 20)
            
            # 执行反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("Chrome驱动配置成功")
            return True
            
        except Exception as e:
            print(f"驱动配置失败: {e}")
            return False
    
    def open_target_page(self):
        """打开目标页面"""
        try:
            print(f"正在访问目标URL: {self.target_url}")
            self.driver.get(self.target_url)
            
            # 等待页面加载
            time.sleep(5)
            
            # 验证页面是否正确加载
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            print(f"当前URL: {current_url}")
            print(f"页面标题: {page_title}")
            
            # 检查页面是否包含预期内容
            if "jinritemai" in current_url:
                print("✓ 页面访问成功")
                return True
            else:
                print("✗ 页面访问可能存在问题")
                return False
                
        except Exception as e:
            print(f"页面访问失败: {e}")
            return False
    
    def wait_for_page_load(self, timeout=60):
        """等待页面完全加载，支持长时间等待"""
        try:
            print(f"等待页面加载完成（最长等待{timeout}秒）...")
            
            # 等待页面DOM加载完成
            self.wait = WebDriverWait(self.driver, timeout)
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            print("✓ 页面DOM加载完成")
            
            # 等待关键元素出现，表示页面真正加载完成
            key_elements = [
                "//span[contains(text(), '商品')]",
                "//div[contains(@class, 'menu')]",
                "//li[contains(text(), '商品')]"
            ]
            
            element_found = False
            for selector in key_elements:
                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    print(f"✓ 关键元素已加载: {selector}")
                    element_found = True
                    break
                except:
                    continue
            
            if not element_found:
                print("⚠ 未找到预期的关键元素，但页面已加载")
            
            # 额外等待时间，确保动态内容加载
            print("等待动态内容加载...")
            time.sleep(5)
            return True
            
        except TimeoutException:
            print(f"✗ 页面加载超时（{timeout}秒）")
            return False
    
    def take_screenshot(self, filename="page_screenshot.png"):
        """截取当前页面截图"""
        try:
            self.driver.save_screenshot(filename)
            print(f"✓ 页面截图已保存: {filename}")
            return True
        except Exception as e:
            print(f"✗ 截图失败: {e}")
            return False
    
    def get_page_info(self):
        """获取页面基本信息"""
        try:
            page_info = {
                "url": self.driver.current_url,
                "title": self.driver.title,
                "page_source_length": len(self.driver.page_source),
                "window_size": self.driver.get_window_size()
            }
            
            print("页面基本信息:")
            for key, value in page_info.items():
                print(f"  {key}: {value}")
                
            return page_info
            
        except Exception as e:
            print(f"获取页面信息失败: {e}")
            return None
    
    def save_cookies(self):
        """保存当前会话的cookies"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            print(f"✓ Cookies已保存到: {self.cookie_file}")
            return True
        except Exception as e:
            print(f"✗ 保存cookies失败: {e}")
            return False
    
    def load_cookies(self):
        """加载已保存的cookies"""
        try:
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                # 先访问目标域名，然后添加cookies
                self.driver.get(self.target_url)
                time.sleep(2)
                
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"添加cookie失败: {e}")
                        continue
                
                print(f"✓ 已加载cookies: {len(cookies)}个")
                return True
            else:
                print("✗ 未找到cookies文件，需要重新登录")
                return False
        except Exception as e:
            print(f"✗ 加载cookies失败: {e}")
            return False
    
    def click_buttons_sequence(self):
        """按顺序点击指定的按钮：商品 -> 源头好货 -> 抖音爆款榜 -> 近30日"""
        try:
            print("开始按顺序点击按钮...")
            
            # 等待页面稳定
            time.sleep(2)
            
            # 第一个按钮：商品
            print("正在点击第一个按钮：商品")
            button1_clicked = self._click_element([
                "//span[text()='商品']",
                "//*[contains(@class, 'menu')]//span[text()='商品']",
                "//span[contains(text(), '商品')]"
            ])
            
            if not button1_clicked:
                input("请手动点击'商品'按钮，然后按Enter继续...")
            
            # 等待子菜单展开
            print("等待子菜单展开...")
            time.sleep(3)
            
            # 第二个按钮：源头好货
            print("正在点击第二个按钮：源头好货")
            button2_clicked = self._click_element([
                "//span[text()='源头好货']",
                "//*[contains(text(), '源头好货')]",
                "//a[contains(text(), '源头好货')]",
                "//div[contains(text(), '源头好货')]"
            ])
            
            if not button2_clicked:
                input("请手动点击'源头好货'按钮，然后按Enter继续...")
            
            # 等待页面加载，重新注入拦截器
            print("等待页面加载...")
            time.sleep(5)
            self.get_api_response_via_js()
            
            # 第三个按钮：抖音爆款榜
            print("正在点击第三个按钮：抖音爆款榜")
            button3_clicked = self._click_element([
                "//span[text()='抖音爆款榜']",
                "//*[contains(text(), '抖音爆款榜')]",
                "//div[contains(text(), '抖音爆款榜')]",
                "//a[contains(text(), '抖音爆款榜')]",
                "//*[contains(@class, 'card') and contains(., '抖音爆款榜')]"
            ])
            
            if not button3_clicked:
                input("请手动点击'抖音爆款榜'按钮，然后按Enter继续...")
            
            # 等待页面加载，重新注入拦截器
            print("等待页面加载...")
            time.sleep(5)
            self.get_api_response_via_js()
            
            # 第四个按钮：近30日（点击这个会触发queryHotProduct API）
            print("正在点击第四个按钮：近30日")
            button4_clicked = self._click_element([
                "//span[text()='近30日']",
                "//*[contains(text(), '近30日')]",
                "//div[contains(text(), '近30日')]",
                "//button[contains(text(), '近30日')]",
                "//*[text()='近30日']"
            ])
            
            if not button4_clicked:
                input("请手动点击'近30日'按钮，然后按Enter继续...")
            
            # 等待页面加载新内容
            print("等待页面加载新内容...")
            time.sleep(5)
            print("✓ 按钮点击序列完成")
            return True
            
        except Exception as e:
            print(f"✗ 按钮点击序列失败: {e}")
            return False
    
    def _click_element(self, selectors):
        """尝试多种选择器点击元素"""
        for i, selector in enumerate(selectors):
            try:
                print(f"  尝试选择器 {i+1}: {selector}")
                element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                element.click()
                print(f"  ✓ 点击成功")
                return True
            except Exception as e:
                print(f"  选择器 {i+1} 失败")
                continue
        
        # 尝试JavaScript点击
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements:
                    self.driver.execute_script("arguments[0].click();", elements[0])
                    print(f"  ✓ JavaScript点击成功")
                    return True
            except:
                continue
        
        print("  ✗ 所有方法都失败")
        return False
    
    def wait_for_api_response(self, target_api="queryHotProduct", timeout=60, check_interval=1):
        """
        等待并捕获目标API响应，一旦捕获到就立即返回
        :param target_api: 目标API关键字
        :param timeout: 超时时间（秒）
        :param check_interval: 检查间隔（秒）
        :return: 捕获到的API响应数据
        """
        print(f"等待捕获API响应（目标: {target_api}，超时: {timeout}秒）...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 检查是否有捕获到的响应
                responses = self.driver.execute_script("return window.capturedResponses || [];")
                
                if responses and len(responses) > 0:
                    print(f"✓ 成功捕获到 {len(responses)} 个API响应！")
                    return responses
                
                # 同时检查性能日志
                logs = self.driver.get_log('performance')
                for log in logs:
                    try:
                        message = json.loads(log['message'])
                        method = message.get('message', {}).get('method', '')
                        
                        if method == 'Network.responseReceived':
                            response = message['message']['params']['response']
                            url = response.get('url', '')
                            
                            if target_api in url:
                                print(f"✓ 检测到目标API响应: {url[:80]}...")
                    except:
                        continue
                
            except Exception as e:
                pass
            
            # 显示等待进度
            elapsed = int(time.time() - start_time)
            print(f"  等待中... {elapsed}/{timeout}秒", end='\r')
            
            time.sleep(check_interval)
        
        print(f"\n✗ 等待超时（{timeout}秒），未捕获到目标API")
        return []
    
    def get_api_response_via_js(self, target_apis=None):
        """
        通过JavaScript拦截XHR请求获取API响应数据
        :param target_apis: 目标API关键字列表
        """
        if target_apis is None:
            target_apis = ['queryHotProduct', 'querySpuDetailForDistributor']
        
        try:
            # 注入JavaScript代码来拦截XHR请求
            inject_script = f"""
            window.capturedResponses = window.capturedResponses || [];
            window.capturedUrls = window.capturedUrls || [];
            window.targetApis = {json.dumps(target_apis)};
            
            // 检查URL是否匹配目标API
            function isTargetApi(url) {{
                return window.targetApis.some(api => url.includes(api));
            }}
            
            // 拦截fetch请求
            if (!window.fetchIntercepted) {{
                const originalFetch = window.fetch;
                window.fetch = async function(...args) {{
                    const response = await originalFetch.apply(this, args);
                    const url = typeof args[0] === 'string' ? args[0] : args[0].url;
                    if (isTargetApi(url)) {{
                        window.capturedUrls.push({{
                            url: url,
                            timestamp: Date.now(),
                            type: url.includes('queryHotProduct') ? 'hotProduct' : 'productDetail'
                        }});
                        const clone = response.clone();
                        try {{
                            const data = await clone.json();
                            window.capturedResponses.push({{
                                url: url,
                                data: data,
                                timestamp: Date.now(),
                                type: url.includes('queryHotProduct') ? 'hotProduct' : 'productDetail'
                            }});
                        }} catch(e) {{}}
                    }}
                    return response;
                }};
                window.fetchIntercepted = true;
            }}
            
            // 拦截XMLHttpRequest
            if (!window.xhrIntercepted) {{
                const originalXHR = window.XMLHttpRequest;
                const originalOpen = originalXHR.prototype.open;
                
                originalXHR.prototype.open = function(method, url, ...args) {{
                    this._requestUrl = url;
                    return originalOpen.apply(this, [method, url, ...args]);
                }};
                
                const originalSend = originalXHR.prototype.send;
                originalXHR.prototype.send = function(...args) {{
                    this.addEventListener('load', function() {{
                        if (isTargetApi(this._requestUrl)) {{
                            window.capturedUrls.push({{
                                url: this._requestUrl,
                                timestamp: Date.now(),
                                type: this._requestUrl.includes('queryHotProduct') ? 'hotProduct' : 'productDetail'
                            }});
                            try {{
                                const data = JSON.parse(this.responseText);
                                window.capturedResponses.push({{
                                    url: this._requestUrl,
                                    data: data,
                                    timestamp: Date.now(),
                                    type: this._requestUrl.includes('queryHotProduct') ? 'hotProduct' : 'productDetail'
                                }});
                            }} catch(e) {{}}
                        }}
                    }});
                    return originalSend.apply(this, args);
                }};
                window.xhrIntercepted = true;
            }}
            
            return 'API拦截器已注入';
            """
            
            result = self.driver.execute_script(inject_script)
            print(f"✓ {result}")
            return True
            
        except Exception as e:
            print(f"✗ 注入拦截器失败: {e}")
            return False
    
    def get_captured_responses(self):
        """获取已捕获的API响应数据"""
        try:
            responses = self.driver.execute_script("return window.capturedResponses || [];")
            if responses:
                print(f"✓ 获取到 {len(responses)} 个API响应")
                return responses
            else:
                print("暂无捕获到的API响应")
                return []
        except Exception as e:
            print(f"✗ 获取响应失败: {e}")
            return []
    
    def save_api_data(self, data, filename=None):
        """保存API数据到文件"""
        try:
            if filename is None:
                filename = self.api_data_file
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ API数据已保存到: {filename}")
            return True
        except Exception as e:
            print(f"✗ 保存API数据失败: {e}")
            return False
    
    def click_product_and_get_detail(self, product_index=0):
        """
        点击商品进入详情页，捕获详情接口URL
        :param product_index: 要点击的商品索引
        :return: (API URL模板, cookies) 或 None
        """
        try:
            print(f"\n=== 点击第 {product_index + 1} 个商品获取详情API ===")
            
            # 记录当前窗口句柄
            main_window = self.driver.current_window_handle
            original_windows = set(self.driver.window_handles)
            
            # 清空之前的日志
            self.driver.get_log('performance')
            
            # 查找商品卡片并点击
            product_selectors = [
                "//div[contains(@class, 'productName')]/ancestor::div[@style and contains(@style, 'cursor')]",
                "//div[contains(@class, 'imgWrapper')]/parent::div[@style and contains(@style, 'cursor')]",
                "//div[contains(@class, 'content-')]/parent::div[@style and contains(@style, 'cursor')]",
                "//span[contains(text(), '昨日销量')]/ancestor::div[@style and contains(@style, 'cursor')]",
                "//span[contains(text(), '供货价')]/ancestor::div[@style and contains(@style, 'cursor')]"
            ]
            
            clicked = False
            for selector in product_selectors:
                try:
                    products = self.driver.find_elements(By.XPATH, selector)
                    if products and len(products) > product_index:
                        print(f"  找到 {len(products)} 个商品，点击第 {product_index + 1} 个")
                        self.driver.execute_script("arguments[0].click();", products[product_index])
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                print("  ✗ 未找到商品元素，请手动点击一个商品")
                input("  点击商品后按Enter继续...")
            
            # 等待新窗口打开
            time.sleep(3)
            
            # 检查是否有新窗口
            new_windows = set(self.driver.window_handles) - original_windows
            
            if new_windows:
                # 切换到新窗口
                new_window = new_windows.pop()
                self.driver.switch_to.window(new_window)
                print(f"  ✓ 已切换到新窗口: {self.driver.title}")
                
                # 获取cookies用于后续请求
                cookies = {c['name']: c['value'] for c in self.driver.get_cookies()}
                
                # 轮询等待API URL出现在日志中
                api_url = self.poll_for_detail_api(timeout=15)
                
                # 关闭详情页，切回主窗口
                self.driver.close()
                self.driver.switch_to.window(main_window)
                print("  ✓ 已切回主窗口")
                
                if api_url:
                    return api_url, cookies
                return None
            else:
                print("  未检测到新窗口")
                return None
                
        except Exception as e:
            print(f"  ✗ 获取商品详情失败: {e}")
            try:
                self.driver.switch_to.window(main_window)
            except:
                pass
            return None
    
    def poll_for_detail_api(self, timeout=15):
        """轮询Performance Log获取详情API URL"""
        print("  等待捕获API URL...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                logs = self.driver.get_log('performance')
                for log in logs:
                    try:
                        message = json.loads(log['message'])
                        method = message.get('message', {}).get('method', '')
                        
                        if method == 'Network.requestWillBeSent':
                            url = message['message']['params']['request']['url']
                            if 'querySpuDetailForDistributor' in url:
                                print(f"  ✓ 捕获到详情API URL")
                                return url
                    except:
                        continue
            except:
                pass
            
            elapsed = int(time.time() - start_time)
            print(f"  等待中... {elapsed}/{timeout}秒", end='\r')
            time.sleep(0.5)
        
        print(f"\n  ✗ 等待超时，未捕获到API URL")
        return None
    
    def build_detail_url(self, template_url, spu_id):
        """根据模板URL构建新的详情API URL"""
        parsed = urlparse(template_url)
        params = parse_qs(parsed.query)
        
        # 替换spuId
        params['spuId'] = [str(spu_id)]
        
        # 重新构建URL
        new_query = urlencode({k: v[0] for k, v in params.items()})
        new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', new_query, ''))
        return new_url
    
    def fetch_product_detail(self, url, cookies, headers=None):
        """通过requests获取商品详情"""
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Referer': 'https://douhuo.jinritemai.com/',
            }
        
        try:
            response = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"    请求失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"    请求异常: {e}")
            return None
    
    def crawl_multiple_products(self, product_ids, max_count=10):
        """
        批量爬取多个商品详情（通过浏览器直接访问API）
        :param product_ids: 商品ID列表
        :param max_count: 最大爬取数量
        :return: 商品详情列表
        """
        all_details = []
        
        print(f"\n=== 开始批量爬取商品详情 ===")
        
        # 记录当前页面URL，稍后返回
        current_url = self.driver.current_url
        
        # API基础URL
        base_url = "https://douhuo.jinritemai.com/api/dp/fxProduct/querySpuDetailForDistributor"
        
        count = min(len(product_ids), max_count)
        print(f"开始请求 {count} 个商品详情...\n")
        
        for i, spu_id in enumerate(product_ids[:count]):
            print(f"  [{i+1}/{count}] 获取商品 {spu_id}...", end=' ')
            
            try:
                # 构建API URL（只需要spuId和needSortSku，其他参数浏览器会自动处理）
                api_url = f"{base_url}?spuId={spu_id}&needSortSku=true"
                
                # 用浏览器访问API
                self.driver.get(api_url)
                time.sleep(1)
                
                # 获取页面内容（API返回的JSON）
                page_source = self.driver.find_element(By.TAG_NAME, "pre").text
                data = json.loads(page_source)
                
                if data.get('code') == 0 or data.get('data'):
                    all_details.append({
                        'spuId': spu_id,
                        'data': data
                    })
                    print("✓")
                else:
                    print(f"✗ {data.get('msg', 'unknown')}")
                    
            except Exception as e:
                print(f"✗ {e}")
            
            # 间隔避免请求过快
            time.sleep(0.5)
        
        # 返回原页面
        print("\n返回原页面...")
        self.driver.get(current_url)
        time.sleep(2)
        
        print(f"\n=== 批量爬取完成，成功获取 {len(all_details)} 个商品详情 ===")
        return all_details
    
    def extract_product_ids(self, api_response):
        """从热销列表中提取商品ID"""
        try:
            product_ids = []
            
            if isinstance(api_response, list):
                for resp in api_response:
                    data = resp.get('data', {})
                    items = data.get('data', {}).get('list', [])
                    for item in items:
                        pid = item.get('productId')
                        if pid:
                            product_ids.append(pid)
                        same_ids = item.get('sameCargoIdList', [])
                        product_ids.extend(same_ids)
            
            product_ids = list(set(product_ids))
            print(f"✓ 提取到 {len(product_ids)} 个商品ID")
            return product_ids
            
        except Exception as e:
            print(f"✗ 提取商品ID失败: {e}")
            return []
    
    def extract_hot_products(self, api_response):
        """从API响应中提取热销商品数据"""
        try:
            products = []
            
            if isinstance(api_response, list):
                for resp in api_response:
                    data = resp.get('data', {})
                    if 'data' in data:
                        items = data.get('data', {}).get('list', [])
                        products.extend(items)
            elif isinstance(api_response, dict):
                items = api_response.get('data', {}).get('list', [])
                products.extend(items)
            
            print(f"✓ 提取到 {len(products)} 个商品数据")
            return products
            
        except Exception as e:
            print(f"✗ 提取商品数据失败: {e}")
            return []


    def close_driver(self):
        """关闭浏览器驱动"""
        if self.driver:
            self.driver.quit()
            print("✓ 浏览器已关闭")


def main():
    """主函数 - 抖音电商热点数据爬取"""
    print("=== 抖音电商热点数据可视化分析系统 - 爬虫模块 ===")
    
    driver_path = "../driver/chromedriver.exe"
    
    if os.path.exists(driver_path):
        print(f"✓ 找到ChromeDriver: {driver_path}")
    else:
        print(f"⚠ 未找到ChromeDriver，将使用webdriver-manager自动下载")
        driver_path = None
    
    crawler = DouyinCrawler(driver_path=driver_path)
    
    try:
        # 步骤1: 配置驱动
        if not crawler.setup_driver():
            return
        
        # 步骤2: 登录
        cookies_loaded = crawler.load_cookies()
        
        if cookies_loaded:
            print("使用已保存的cookies访问页面...")
            crawler.driver.refresh()
            time.sleep(3)
        else:
            print("首次访问，需要登录...")
            if not crawler.open_target_page():
                return
            input("登录成功后，按Enter键继续...")
            crawler.save_cookies()
        
        # 步骤3: 等待页面加载
        crawler.wait_for_page_load(timeout=60)
        
        # 步骤4: 注入API拦截器
        crawler.get_api_response_via_js()
        
        # 步骤5: 点击按钮序列（商品 -> 源头好货 -> 抖音爆款榜 -> 近30日）
        print("\n=== 开始自动点击按钮 ===")
        crawler.click_buttons_sequence()
        
        # 步骤6: 捕获热销商品列表API
        print("\n=== 等待捕获热销商品列表 ===")
        hot_responses = crawler.wait_for_api_response("queryHotProduct", timeout=30)
        
        if hot_responses:
            crawler.save_api_data(hot_responses, "hot_products_api.json")
            product_ids = crawler.extract_product_ids(hot_responses)
            print(f"✓ 获取到 {len(product_ids)} 个商品ID")
        else:
            print("未捕获到热销列表，请手动操作...")
            input("操作完成后按Enter继续...")
            hot_responses = crawler.get_captured_responses()
            product_ids = crawler.extract_product_ids(hot_responses) if hot_responses else []
        
        # 步骤7: 爬取商品详情
        if product_ids:
            print("\n=== 开始爬取商品详情 ===")
            
            # 爬取商品详情（使用API模板方式）
            details = crawler.crawl_multiple_products(product_ids, max_count=50)
            
            if details:
                crawler.save_api_data(details, "product_details_api.json")
                print(f"✓ 成功保存 {len(details)} 个商品详情")
            else:
                print("✗ 未获取到商品详情数据")
        else:
            print("✗ 没有商品ID，跳过详情爬取")
        
        # 截图
        crawler.take_screenshot("final_page.png")
        
        print("\n=== 爬取完成 ===")
        print("生成的数据文件:")
        print("  - hot_products_api.json (热销商品列表)")
        print("  - product_details_api.json (商品详情)")
        
        input("按Enter键关闭浏览器...")
        
    except Exception as e:
        print(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        crawler.close_driver()


if __name__ == "__main__":
    main()