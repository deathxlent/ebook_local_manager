import os
import re
import time
import json
import random
import queue
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, List

from PyQt6.QtCore import QObject, pyqtSignal

import requests
from lxml import etree


DOUBAN_SEARCH_URL = "https://www.douban.com/search"
DOUBAN_BASE = "https://book.douban.com/"
DOUBAN_BOOK_CAT = "1001"
DOUBAN_BOOK_CACHE_SIZE = 10
DOUBAN_CONCURRENCY_SIZE = 1
DOUBAN_BOOK_URL_PATTERN = re.compile(r".*/subject/(\d+)/?")

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': DOUBAN_BASE
}


class DoubanParser(QObject):
    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal()
    parse_complete_signal = pyqtSignal(object, object)

    def __init__(self, config_path: str = None, parent=None):
        super().__init__(parent)
        self.cookie = ''
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), 'config.json')
        self.load_config()

        self.parse_queue = queue.Queue()
        self.is_running = False
        self.parse_thread = None
        self.last_parse_time = 0
        self.min_interval = 5

        self._book_cache = {}
        self._task_callbacks = {}

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.cookie = config.get('douban_cookie', '')
        except Exception as e:
            print(f"加载配置失败: {e}")

    def save_config(self, cookie: str):
        try:
            config = {'douban_cookie': cookie}
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.cookie = cookie
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def has_cookie(self) -> bool:
        return bool(self.cookie and self.cookie.strip())

    def _get_headers(self):
        headers = DEFAULT_HEADERS.copy()
        if self.cookie:
            headers['Cookie'] = self.cookie
        return headers

    def _random_sleep(self):
        random_sec = random.random() / 10
        time.sleep(random_sec)

    def search_book(self, title: str, author: str = '') -> Optional[Dict[str, Any]]:
        if not self.has_cookie():
            return {'error': '未配置豆瓣 Cookie'}

        try:
            search_keyword = f"{title} {author}".strip()
            print(f"搜索豆瓣: {search_keyword}")

            book_urls = self._search_book_urls(search_keyword)

            if not book_urls:
                print(f"未找到搜索结果")
                return None

            for book_url in book_urls[:DOUBAN_CONCURRENCY_SIZE]:
                book = self._load_book_detail(book_url)
                if book:
                    return book

            return None
        except Exception as e:
            print(f"搜索书籍失败: {e}")
            return {'error': str(e)}

    def _search_book_urls(self, query: str) -> List[str]:
        url = DOUBAN_SEARCH_URL
        params = {"cat": DOUBAN_BOOK_CAT, "q": query}
        headers = self._get_headers()

        try:
            res = requests.get(url, params=params, headers=headers, timeout=15)
            book_urls = []
            if res.status_code in [200, 201]:
                html = etree.HTML(res.content)
                alist = html.xpath('//a[@class="nbg"]')
                for link in alist:
                    href = link.attrib.get('href', '')
                    parsed = self._calc_url(href)
                    if parsed and len(book_urls) < DOUBAN_CONCURRENCY_SIZE:
                        book_urls.append(parsed)
            return book_urls
        except Exception as e:
            print(f"搜索页面请求失败: {e}")
            return []

    def _calc_url(self, href: str) -> Optional[str]:
        try:
            query = urllib.parse.urlparse(href).query
            params = {item.split('=')[0]: item.split('=')[1] for item in query.split('&')}
            url = urllib.parse.unquote(params.get('url', ''))
            if DOUBAN_BOOK_URL_PATTERN.match(url):
                return url
        except:
            pass
        return None

    def _load_book_detail(self, url: str) -> Optional[Dict[str, Any]]:
        if url in self._book_cache:
            print(f"使用缓存: {url}")
            return self._book_cache[url].copy()

        self._random_sleep()
        headers = self._get_headers()

        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code in [200, 201]:
                book_content = res.content.decode("utf8")
                book = self._parse_book_html(url, book_content)
                if book:
                    self._book_cache[url] = book.copy()
                    if len(self._book_cache) > DOUBAN_BOOK_CACHE_SIZE:
                        oldest_key = list(self._book_cache.keys())[0]
                        del self._book_cache[oldest_key]
                return book
            else:
                print(f"请求失败，状态码: {res.status_code}")
        except Exception as e:
            print(f"获取书籍详情失败: {e}")

        return None

    def _parse_book_html(self, url: str, book_content: str) -> Optional[Dict[str, Any]]:
        try:
            data = {
                'douban_url': url,
                'tags': [],
                'authors': []
            }

            html = etree.HTML(book_content)

            title_element = html.xpath("//span[@property='v:itemreviewed']")
            if title_element:
                data['title'] = title_element[0].text.strip() if title_element[0].text else ''

            share_element = html.xpath("//a[@data-url]")
            if share_element:
                data['douban_url'] = share_element[0].attrib.get('data-url', url)

            id_match = DOUBAN_BOOK_URL_PATTERN.match(data['douban_url'])
            if id_match:
                data['douban_id'] = id_match.group(1)

            img_element = html.xpath("//a[@class='nbg']")
            if img_element:
                cover = img_element[0].attrib.get('href', '')
                if not cover or cover.endswith('update_image'):
                    data['cover_url'] = ''
                else:
                    data['cover_url'] = cover

            rating_element = html.xpath("//strong[@property='v:average']")
            if rating_element and rating_element[0].text:
                try:
                    rating = float(rating_element[0].text.strip())
                    data['rating'] = rating
                except ValueError:
                    pass

            elements = html.xpath("//span[@class='pl']")
            for element in elements:
                text = element.text.strip() if element.text else ''
                if text.startswith("作者") or text.startswith("译者"):
                    authors = []
                    for author_element in element.findall("..//a"):
                        if author_element.text and ('/author' in author_element.attrib.get('href', '') or 
                            '/search' in author_element.attrib.get('href', '')):
                            authors.append(author_element.text.strip())
                    if authors:
                        data['authors'] = authors
                elif text.startswith("出版社"):
                    publisher = element.tail.strip() if element.tail else ''
                    if publisher:
                        data['publisher'] = publisher
                elif text.startswith("副标题"):
                    subtitle = element.tail.strip() if element.tail else ''
                    if subtitle:
                        data['subtitle'] = subtitle
                elif text.startswith("出版年"):
                    pubdate = element.tail.strip() if element.tail else ''
                    if pubdate:
                        date_match = re.match(r"(\d{4})-(\d+)", pubdate)
                        if date_match:
                            data['pubdate'] = f"{date_match.group(1)}-{date_match.group(2)}-1"
                        else:
                            data['pubdate'] = pubdate
                elif text.startswith("丛书"):
                    next_element = element.getnext()
                    if next_element is not None and next_element.text:
                        data['series'] = next_element.text.strip()
                elif text.startswith("ISBN"):
                    isbn = element.tail.strip() if element.tail else ''
                    if isbn:
                        data['isbn'] = isbn

            summary_element = html.xpath("//div[@id='link-report']//div[@class='intro']")
            if summary_element:
                summary_html = etree.tostring(summary_element[-1], encoding="utf8").decode("utf8").strip()
                summary = re.sub(r'<[^>]+>', '', summary_html)
                summary = re.sub(r'\s+', ' ', summary).strip()
                data['summary'] = summary[:1000] if len(summary) > 1000 else summary

            tag_elements = html.xpath("//a[contains(@class, 'tag')]")
            if tag_elements:
                data['tags'] = [tag.text.strip() for tag in tag_elements if tag.text]
            else:
                tag_pattern = re.compile(r"criteria = '(.+)'")
                tag_match = tag_pattern.findall(book_content)
                if tag_match:
                    data['tags'] = [tag.replace('7:', '') for tag in
                                   filter(lambda tag: tag and tag.startswith('7:'), tag_match[0].split('|'))]

            print(f"解析完成: {data.get('title', '未知')}")
            return data

        except Exception as e:
            print(f"解析HTML错误: {e}")
            import traceback
            traceback.print_exc()
            return None

    def download_cover(self, cover_url: str, save_path: str) -> bool:
        try:
            if os.path.exists(save_path):
                return True

            headers = self._get_headers()

            res = requests.get(cover_url, headers=headers, timeout=10)
            if res.status_code == 200:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(res.content)
                return True
            return False
        except Exception as e:
            print(f"下载封面失败: {e}")
            return False

    def add_to_queue(self, book_id: int, book_data: Dict[str, Any], callback=None):
        task_id = f"{book_id}_{int(time.time() * 1000)}"
        self._task_callbacks[task_id] = callback

        self.parse_queue.put({
            'task_id': task_id,
            'book_id': book_id,
            'book_data': book_data,
            'timestamp': time.time()
        })

        if not self.is_running:
            self.start_parser()

    def queue_size(self) -> int:
        return self.parse_queue.qsize()

    def start_parser(self):
        if self.is_running:
            return

        self.is_running = True
        self.parse_thread = threading.Thread(target=self._parse_worker, daemon=True)
        self.parse_thread.start()

    def stop_parser(self):
        self.is_running = False

    def _parse_worker(self):
        print("豆瓣解析队列已启动")

        while self.is_running:
            try:
                task = self.parse_queue.get(timeout=1)

                now = time.time()
                time_since_last = now - self.last_parse_time
                if time_since_last < self.min_interval:
                    wait_time = self.min_interval - time_since_last
                    print(f"等待 {wait_time:.1f} 秒后继续解析...")
                    time.sleep(wait_time)

                self.last_parse_time = time.time()

                self.status_signal.emit(f"正在解析: {task['book_data'].get('title', '未知')}")

                authors = task['book_data'].get('authors', [])
                if isinstance(authors, list):
                    author_str = ', '.join(authors)
                else:
                    author_str = str(authors) if authors else ''

                result = self.search_book(
                    task['book_data'].get('title', ''),
                    author_str
                )

                task_id = task['task_id']
                callback = self._task_callbacks.get(task_id)
                del self._task_callbacks[task_id]

                if result and 'error' not in result:
                    result['book_id'] = task['book_id']

                    if 'cover_url' in result and result['cover_url']:
                        file_hash = abs(hash(task['book_data'].get('physical_path', '') + str(task['book_id'])))
                        cover_filename = f"cover_{file_hash}.jpg"
                        covers_dir = os.path.join(os.path.dirname(__file__), 'covers')
                        cover_path = os.path.join(covers_dir, cover_filename)

                        if self.download_cover(result['cover_url'], cover_path):
                            result['cover_path'] = cover_path

                    if callback:
                        self.parse_complete_signal.emit(result, None)
                        callback(result, None)
                    else:
                        self.parse_complete_signal.emit(result, None)
                else:
                    error_msg = result.get('error', '解析失败') if result else '解析失败'
                    if callback:
                        callback(None, error_msg)
                    self.parse_complete_signal.emit(None, error_msg)

                self.progress_signal.emit()

                self.parse_queue.task_done()

            except queue.Empty:
                if self.parse_queue.qsize() == 0:
                    self.is_running = False
                    self.status_signal.emit("解析队列已空闲")
                    break
            except Exception as e:
                print(f"解析队列错误: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)

        print("豆瓣解析队列已停止")


import threading
