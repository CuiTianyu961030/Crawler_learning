import csv
from zipfile import ZipFile
from io import BytesIO, TextIOWrapper
import requests
import time
import threading
from Chapter_3 import Downloader, get_robots, get_links
from urllib.parse import urljoin
from redis import StrictRedis
import multiprocessing

SLEEP_TIME = 1


class AlexaCallback:
    def __init__(self, max_urls=50):
        self.max_urls = max_urls
        self.seed_url = 'http://s3.amazonaws.com/alexa-static/top-1m.csv.zip'
        self.urls = []

    def __call__(self):
        resp = requests.get(self.seed_url, stream=True)

        with ZipFile(BytesIO(resp.content)) as zf:
            csv_filename = zf.namelist()[0]
            with zf.open(csv_filename) as csv_file:
                for _, website in csv.reader(TextIOWrapper(csv_file)):
                    self.urls.append('http://' + website)

                    if len(self.urls) == self.max_urls:
                        break
        return self.urls

class RedisQueue:
    def __init__(self, client=None, db=0, queue_name='TianyuCui'):
        self.client = (StrictRedis(host='localhost', port=6379, db=db)
                       if client is None else client)
        self.name = "queue:%s" % queue_name
        self.seen_set = "seen:%s" % queue_name
        self.depth = "depth:%s" % queue_name

    def __len__(self):
        return self.client.llen(self.name)

    def push(self, element):
        """Push an element to the tail of the queue"""
        if isinstance(element, list):
            element = [e for e in element if not self.already_seen(e)]
            self.client.lpush(self.name, *element)
            self.client.sadd(self.seen_set, *element)
        elif not self.already_seen(element):
            self.client.lpush(self.name, element)
            self.client.sadd(self.seen_set, element)

    def pop(self):
        """Pop an element from the head of the queue"""
        return self.client.rpop(self.name)

    def already_seen(self, element):
        """ determine if an element has already been seen """
        return self.client.sismember(self.seen_set, element)

    def set_depth(self, element, depth):
        """ Set the seen hash and depth """
        self.client.hset(self.depth, element, depth)

    def get_depth(self, element):
        """ Get the seen hash and depth """
        return self.client.hget(self.depth, element)


def threaded_crawler(seed_url, scrape_callback=None, user_agent='TianyuCui', delay=5,
                 max_depth=1, proxies=None, num_retries=2, cache=None, max_threads=10):
    if isinstance(seed_url, list):
        crawl_queue = seed_url
    else:
        crawl_queue = [seed_url]
    seen = {seed_url: 0}
    rp = get_robots(seed_url)
    D = Downloader(delay=delay, user_agent=user_agent, proxies=proxies, cache=cache)

    def process_queue():
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
                    links = scrape_callback(url, html) or []
                else:
                    links = []
                for link in get_links(html) + links:
                    # print(link)
                    # if re.match(link_regex, link):
                    abs_link = urljoin(seed_url, link)
                    # print("abs_link", abs_link)
                    if abs_link not in seen:
                        seen[abs_link] = depth + 1
                        crawl_queue.append(abs_link)
    threads = []
    while threads or crawl_queue:
        for thread in threads:
            if not thread.is_alive():
                threads.remove(thread)
        while len(threads) < max_threads and crawl_queue:
            thread = threading.Thread(target=process_queue)
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        time.sleep(SLEEP_TIME)


def threaded_crawler_rq(seed_url, scrape_callback=None, user_agent='TianyuCui', delay=5,
                 max_depth=1, proxies=None, num_retries=2, cache=None, max_threads=10):
    crawl_queue = RedisQueue()
    crawl_queue.push(seed_url)
    seen = {seed_url: 0}
    rp = get_robots(seed_url)
    D = Downloader(delay=delay, user_agent=user_agent, proxies=proxies, cache=cache)

    def process_queue():
        while len(crawl_queue):

            url = crawl_queue.pop()

            # check url passes robots.txt restrictions
            if rp.can_fetch(user_agent, url):
                depth = crawl_queue.get_depth(url) or 0

                if depth == max_depth:
                    print('Skipping %s due to depth' % url)
                    continue
                html = D(url, num_retries=num_retries)
                if not html:
                    continue
                if scrape_callback:
                    links = scrape_callback(url, html) or []
                else:
                    links = []
                for link in get_links(html) + links:
                    # print(link)
                    # if re.match(link_regex, link):
                    link = urljoin(seed_url, link)
                    # print("abs_link", abs_link)
                    crawl_queue.push(link)
                    crawl_queue.set_depth(link, depth + 1)

    threads = []
    while threads or crawl_queue:
        for thread in threads:
            if not thread.is_alive():
                threads.remove(thread)
        while len(threads) < max_threads and crawl_queue:
            thread = threading.Thread(target=process_queue)
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        time.sleep(SLEEP_TIME)


def mp_threaded_crawler(args, **kwargs):
    num_procs = kwargs.pop('num_procs')
    if not num_procs:
        num_cpus = multiprocessing.cpu_count()
    processes = []
    for i in range(num_procs):
        proc = multiprocessing.Process(
            target=threaded_crawler_rq, args=args,
            kwargs=kwargs)
        proc.start()
        processes.append(proc)
    # wait for processes to complete
    for proc in processes:
        proc.join()


if __name__ == '__main__':
    scrape_callback = AlexaCallback()
    print(scrape_callback)
    cache = StrictRedis(host='localhost', port=6379, db=0)
    threaded_crawler_rq(scrape_callback.seed_url, scrape_callback=scrape_callback, cache=cache)
