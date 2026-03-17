from crawler.dy_xingtui.ReduxSiger import ReduxSigner
import requests
import json
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.dy_xingtui.db_callback import DBCallback
from logger import get_logger, init_logger

init_logger(log_dir="logs", log_level=logging.DEBUG)
log = get_logger("ShopCrawler")


class ShopCrawler:
    """
    ShopCrawler类用于爬取商品信息。
    """
    SHOP_SEARCH_PATH = "/api/douke/search"
    SHOP_VIEW_PATH = "/api/douke/view"

    @classmethod
    def _get_token(cls):
        """从统一配置获取 Token"""
        try:
            from config import get_config
            return get_config().API_TOKEN
        except Exception:
            return "7036afebb8e8c2449c74718738fa33bb"

    def __init__(self, token: str = None):
        self.TOKEN = token if token is not None else self._get_token()


    @classmethod
    def get_shop_list_by_page(cls , page: int = None) -> json:
        try:
            if page is None:
                raise ValueError("请传入页码参数")
            params = {
                    'page': str(page),
                    'limit': '10',
                    'sell_num_min': '1000',
                    'search_type': '11',
                    'sort_type': '1',
                    'source': '0',
                    'platform': 'douyin'
            }
            ts = ReduxSigner.get_timestamp_by_server() # 获取服务器时间戳

            signer = ReduxSigner.get_siger_by_params(params, ts)

            # 构造 Header
            headers = ReduxSigner.get_headers(signer['header_sign'], signer['timestamp'], cls._get_token())

            # 构造 URL 参数
            query_params = params.copy()
            query_params['sign'] = signer['url_sign']
            query_params['time'] = signer['timestamp']
            # 发送请求
            url = f"{ReduxSigner.BASE_URL}{cls.SHOP_SEARCH_PATH}"
            response = requests.get(url, params=query_params, headers=headers)
            return response.json()
        except ValueError as v:
            log.error(v)
        except Exception as e:
            log.error(e)

    @classmethod
    def get_all_shop_list(cls) -> json:
        page = 1
        while True:
            log.info(f"正在获取第{page}页数据...")

            result = cls.get_shop_list_by_page(page)
            if result is None:
                break
            # 直接检查data是否包含商品列表
            if 'data' in result and isinstance(result['data'], list):
                if len(result['data']) > 0:
                    yield result #暂停并返回继续
                    page += 1
                else:
                    # 数据为空，结束
                    break
            else:
                break

    @classmethod
    def get_all_shop_list_multithread(cls, start_page: int = 1, end_page: int = None,
                                       max_workers: int = 5, callback=None) -> int:
        """
        多线程爬取商品列表
        
        Args:
            start_page: 起始页码
            end_page: 结束页码，为None时自动判断（数据为空时停止）
            max_workers: 最大线程数
            callback: 每页完成后的回调函数，接收 (page, data) 参数
            
        Returns:
            int: 成功获取的总页数
        """
        current_page = start_page
        total_pages = 0
        
        while True:
            # 计算本批次结束页
            if end_page is not None:
                batch_end = min(current_page + max_workers - 1, end_page)
                if current_page > end_page:
                    break
            else:
                batch_end = current_page + max_workers - 1
            
            log.info(f"开始爬取第{current_page}-{batch_end}页...")
            
            empty_count = 0
            batch = list(range(current_page, batch_end + 1))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(cls._fetch_single_page, batch))
            
            for page, data in results:
                if data is not None:
                    total_pages += 1
                    if callback:
                        try:
                            callback(page, data)
                        except Exception as e:
                            log.error(f"回调执行失败: {e}")
                else:
                    empty_count += 1
            
            # 未指定end_page时，遇到空页则停止
            if end_page is None and empty_count > 0:
                log.info(f"检测到空页，停止爬取")
                break
            
            current_page = batch_end + 1
        
        log.info(f"多线程爬取完成，共获取{total_pages}页数据")
        return total_pages
    
    @classmethod
    def _fetch_single_page(cls, page: int):
        """单页爬取任务"""
        time.sleep(random.uniform(1, 1.5))
        log.info(f"正在获取第{page}页数据...")
        try:
            result = cls.get_shop_list_by_page(page)
            if result and 'data' in result and isinstance(result['data'], list) and result['data']:
                log.info(f"第{page}页获取成功，共{len(result['data'])}条数据")
                return page, result
            log.warning(f"第{page}页数据为空")
            return page, None
        except Exception as e:
            log.error(f"第{page}页获取失败: {e}")
            return page, None


if __name__ == '__main__':
    import os
    
    os.makedirs('output', exist_ok=True)
    
    def save_to_file(page, data):
        with open(f'output/page_{page}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"第{page}页已保存到文件")
    
    # end_page=None 自动判断结束，或指定 end_page=100
    with DBCallback(port=3306, user="root", password="123456", database="dy_analysis_system") as db:
        total = ShopCrawler.get_all_shop_list_multithread(
            start_page=1,
            end_page=6,
            max_workers=5,
            callback=db.save_page
        )
    print(f"爬取完成，共 {total} 页")
