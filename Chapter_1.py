import re
import urllib.request
from urllib.error import URLError, HTTPError, ContentTooShortError
import itertools
from urllib.parse import urljoin
from urllib import robotparser
from urllib.parse import urlparse
import time
import requests
from Chapter_2 import CsvCallback

# def download(url, user_agent='wswp', num_retries=2, charset='utf-8', proxy=None):
#     print('Downloading:', url)
#     request = urllib.request.Request(url)
#     request.add_header('User-agent', user_agent)
#     try:
#         if proxy:
#             proxy_support = urllib.request.ProxyHandler({'http': proxy})
#             opener = urllib.request.build_opener(proxy_support)
#             urllib.request.install_opener(opener)
#         resp = urllib.request.urlopen(request)
#         cs = resp.headers.get_content_charset()
#         if not cs:
#             cs = charset
#         html = resp.read().decode(cs)
#     except (URLError, HTTPError, ContentTooShortError) as e:
#         print('Download error:', e.reason)
#         html = None
#         if num_retries > 0:
#             if hasattr(e, 'code') and 500 <= e.code < 600:
#                 return download(url, num_retries - 1)
#     return html


def download(url, user_agent='wswp', num_retries=2, ):
    print('Downloading:', url)
    headers = {'User-Agent': user_agent}
    # proxies = {'http': 'http://myproxy.net:1234', 'https': 'https://myproxy.net:1234'}
    try:
        resp = requests.get(url, headers=headers, proxies=proxies)
        html = resp.text
        if resp.status_code >= 400:
            print('Download error:', resp.text)
            html = None
            if num_retries and 500 <= resp.status_code < 600:
                # recursively retry 5xx HTTP errors
                return download(url, num_retries - 1)
    except requests.exceptions.RequestException as e:
        print('Download error:', e.reason)
        html = None
    return html


def crawl_sitemap(url):
    sitemap = download(url)
    links = re.findall('<loc>(.*?)</loc>', sitemap)
    for link in links:
        html = download(link)


def crawl_site(url, max_errors=5):
    num_errors = 0
    for page in itertools.count(1):
        pg_url = '{}{}'.format(url, page)
        html = download(pg_url)
        if html is None:
            num_errors += 1
            if num_errors == max_errors:
                break
            else:
                num_errors = 0


def link_crawler(start_url, link_regex, robots_url=None, user_agent='wswp', delay=5, max_depth=4, scrape_callback=None):
    throttle = Throttle(delay)
    crawl_queue = [start_url]
    # seen = set(crawl_queue)
    seen = {start_url: 0}
    # print(seen.items())
    if not robots_url:
        robots_url = '{}/robots.txt'.format(start_url)
    rp = get_robots_parser(robots_url)
    while crawl_queue:
        url = crawl_queue.pop()
        if rp.can_fetch(user_agent, url):
            depth = seen.get(url, 0)
            if depth == max_depth:
                print('Skipping %s due to depth' % url)
                continue
            throttle.wait(url)
            html = download(url, user_agent=user_agent)
        else:
            print('Blocked by robots.txt:', url)
            html = 0

        if not html:
            continue
        data = []
        if scrape_callback:
            scrape_callback(url, html)
        for link in get_links(html):
            # print("link", link)
            if re.match(link_regex, link):
                abs_link = urljoin(start_url, link)
                # print("abs_link", abs_link)
                if abs_link not in seen:
                    seen[abs_link] = depth + 1
                    crawl_queue.append(abs_link)


def get_links(html):
    webpage_regex = re.compile("""<a[^>]+href=["'](.*?)["']""", re.IGNORECASE)
    return webpage_regex.findall(html)


def get_robots_parser(robots_url):
    " Return the robots parser object using the robots_url "
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    return rp


class Throttle:
    """Add a delay between downloads to the same domain
    """
    def __init__(self, delay):
        # amount of delay between downloads for each domain
        self.delay = delay
        # timestamp of when a domain was last accessed
        self.domains = {}

    def wait(self, url):
        domain = urlparse(url).netloc
        last_accessed = self.domains.get(domain)

        if self.delay > 0 and last_accessed is not None:
            sleep_secs = self.delay - (time.time() - last_accessed)
            if sleep_secs > 0:
                # domain has been accessed recently
                # so need to sleep
                time.sleep(sleep_secs)
            # update the last accessed time
            self.domains[domain] = time.time()


if __name__ == "__main__":
    # crawl_sitemap('http://example.python-scraping.com/sitemap.xml')
    # crawl_site('http://example.python-scraping.com/view/-')
    # link_crawler('http://example.python-scraping.com', '.*/view/')
    link_crawler('http://example.python-scraping.com/places/default/view/Afghanistan-1', '.*/places/.*',
                 max_depth=3, scrape_callback=CsvCallback())
