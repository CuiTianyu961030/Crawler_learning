from Chapter_1 import Throttle
from random import choice
from urllib import robotparser
import requests
import os
import re
from urllib.parse import urlsplit
from urllib.parse import urljoin
import json
import zlib
from datetime import datetime, timedelta
import json
from redis import StrictRedis
# from bson.binary import Binary
from Chapter_2 import CsvCallback
import requests_cache


class Downloader:
    def __init__(self, delay=5, user_agent='wswp', proxies=None, cache=None):
        self.throttle = Throttle(delay)
        self.user_agent = user_agent
        self.proxies = proxies
        self.num_retries = None
        self.cache = cache

    def __call__(self, url, num_retries=2):
        self.num_retries = num_retries
        try:
            result = self.cache[url]
            print('Loaded from cache:', url)
        except KeyError:
            result = None
        if result and self.num_retries and 500 <= result['code'] < 600:
            result = None
        if result is None:
            self.throttle.wait(url)
            proxies = choice(self.proxies) if self.proxies else None
            headers = {'User-Agent': self.user_agent}
            result = self.download(url, headers, proxies)
            if self.cache:
                self.cache[url] = result
        return result['html']

    def download(self, url, headers={'User-Agent': 'wswp'}, proxies=None):
        print('Downloading:', url)
        # proxies = {'http': 'http://myproxy.net:1234', 'https': 'https://myproxy.net:1234'}
        try:
            resp = requests.get(url, headers=headers, proxies=proxies)
            html = resp.text
            if resp.status_code >= 400:
                print('Download error:', resp.text)
                html = None
                if self.num_retries and 500 <= resp.status_code < 600:
                    # recursively retry 5xx HTTP errors
                    self.num_retries -= 1
                    return self.download(url)
        except requests.exceptions.RequestException as e:
            print('Download error:', e.reason)
            html = None
        return {'html': html, 'code': resp.status_code}


class DiskCache:
    def __init__(self, cache_dir='cache', max_len=255, compress=True, encoding='UTF-8', expires=timedelta(days=30)):
        self.cache_dir = cache_dir
        self.max_len = max_len
        self.compress = compress
        self.encoding = encoding
        self.expires = expires

    def url_to_path(self, url):
        components = urlsplit(url)
        path = components.path
        if not path:
            path = '/index.html'
        elif path.endswith('/'):
            path += 'index.html'
        filename = components.netloc + path + components.query
        filename = re.sub('[^/0-9a-zA-Z\-.,;_ ]', '_', filename)
        filename = '/'.join(seg[:self.max_len] for seg in filename.split('/'))
        return os.path.join(self.cache_dir, filename)

    def __getitem__(self, url):
        path = self.url_to_path(url)
        mode = ('rb' if self.compress else 'r')
        if os.path.exists(path):
            with open(path, mode) as fp:
                if self.compress:
                    data = zlib.decompress(fp.read()).decode(self.encoding)
                    return json.loads(data)
                else:
                    data = json.load(fp)
                exp_date = data.get('expires')
                if exp_date and datetime.strptime(exp_date, '%Y-%m-%dT%H:%M:%S') <= datetime.utcnow():
                    print('Cache expires!', exp_date)
                    raise KeyError(url + ' has expired.')
                return data
        else:
            raise KeyError(url + ' does not exist')

    def __setitem__(self, url, result):
        path = self.url_to_path(url)
        folder = os.path.dirname(path)
        result['expires'] = (datetime.utcnow() + self.expires).isoformat(timespec='seconds')
        if not os.path.exists(folder):
            os.makedirs(folder)
        mode = ('wb' if self.compress else 'w')
        with open(path, mode) as fp:
            if self.compress:
                data = bytes(json.dumps(result), self.encoding)
                fp.write(zlib.compress(data))
            else:
                json.dump(result, fp)


class RedisCache:
    def __init__(self, client=None, expires=timedelta(days=30), encoding='utf-8', compress=True):
        self.client = StrictRedis(host='localhost', port=6379, db=0) if client is None else client
        self.expires = expires
        self.encoding = encoding
        self.compress = compress

    def __getitem__(self, url):
        record = self.client.get(url)
        if record:
            if self.compress:
                record = zlib.decompress(record)
            return json.loads(record.decode(self.encoding))
        else:
            raise KeyError(url + ' does not exist')

    def __setitem__(self, url, result):
        data = bytes(json.dumps(result), self.encoding)
        if self.compress:
            data = zlib.compress(data)
        self.client.setex(url, self.expires, data)


def link_crawler(seed_url, link_regex, scrape_callback=None, user_agent='wswp', delay=5,
                 max_depth=4, proxies=None, num_retries=2, cache=None):
    crawl_queue = [seed_url]
    seen = {seed_url: 0}
    rp = get_robots(seed_url)

    D = Downloader(delay=delay, user_agent=user_agent, proxies=proxies, cache=cache)
    while crawl_queue:

        url = crawl_queue.pop()

        # check url passes robots.txt restrictions
        if rp.can_fetch(user_agent, url):

            depth = seen.get(url, 0)
            if depth == max_depth:
                continue
            html = D(url, num_retries=num_retries)
            if not html:
                continue
            if scrape_callback:
                scrape_callback(url, html)
            for link in get_links(html):
                # print(link)
                if re.match(link_regex, link):
                    abs_link = urljoin(seed_url, link)
                    # print("abs_link", abs_link)
                    if abs_link not in seen:
                        seen[abs_link] = depth + 1
                        crawl_queue.append(abs_link)


def get_robots(robots_url):
    " Return the robots parser object using the robots_url "
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    print(robots_url)
    rp.read()
    return rp


def get_links(html):
    webpage_regex = re.compile("""<a[^>]+href=["'](.*?)["']""", re.IGNORECASE)
    return webpage_regex.findall(html)


def cache_test():
    cache = DiskCache(expires=timedelta(seconds=5))
    url = 'http://example.python-scraping.com'
    result = {'html': '...'}
    cache[url] = result
    print(cache[url])
    import time
    time.sleep(5)
    print(cache[url])


def redis_cache_test():
    cache = RedisCache(expires=timedelta(seconds=20))
    cache['test'] = {'html': '...', 'code': 200}
    import time
    time.sleep(20)
    print(cache['test'])


def requests_cache_test():
    requests_cache.install_cache(backend='redis', expire_after=timedelta(days=30))
    requests_cache.clear()
    url = 'http://example.python-scraping.com/view/United-Kingdom-239'
    resp = requests.get(url)
    print(resp.from_cache)
    resp = requests.get(url)
    print(resp.from_cache)

if __name__ == '__main__':
    # cache_test()
    # redis_cache_test()
    # link_crawler('http://example.python-scraping.com/places/default/view/Afghanistan-1', '.*/places/.*',
    #              max_depth=3, scrape_callback=CsvCallback(), cache=RedisCache())
    requests_cache_test()


