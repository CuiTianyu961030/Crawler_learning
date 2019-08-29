from lxml.html import fromstring
import requests
from urllib.parse import parse_qs, urlparse
from selenium import webdriver
from lxml import etree
from Chapter_4 import threaded_crawler
import requests


def google_crawler():
    # proxies = {'http': 'http://138.128.202.109:23333', 'https': 'https://138.128.202.109:23333'}
    html = requests.get('https://www.google.com/search?q=test')
    tree = fromstring(html.content)
    results = tree.cssselect('div a')
    print(results[20])
    link = results[20].get('href')
    print(link)

    qs = urlparse(link).query
    parsed_qs = parse_qs(qs)
    print(parsed_qs)
    parsed_qs.get('q', [])

    links = []
    for result in results:
        link = result.get('href')
        qs = urlparse(link).query
        parsed_qs = parse_qs(qs).get('q', [])
        # print(parsed_qs)
        if len(parsed_qs) > 0 and 'http' in parsed_qs[0]:
            links.extend(parsed_qs)

    print(links)


def get_driver():
    try:
        return webdriver.PhantomJS()
    except:
        return webdriver.Chrome()


def facebook(username, password, url):
    driver = get_driver()
    driver.get('https://facebook.com')
    driver.find_element_by_id('email').send_keys(username)
    driver.find_element_by_id('pass').send_keys(password)
    driver.find_element_by_id('loginbutton').submit()
    driver.implicitly_wait(30)
    search = driver.find_element_by_name('q')
    driver.get(url)


def scrape_callback(url, html):
    if url.endswith('.xml'):
        # Parse the sitemap XML file
        resp = requests.get(url)
        tree = etree.fromstring(resp.content)
        links = [e[0].text for e in tree]
        return links
    else:
        # Add scraping code here
        pass


if __name__ == '__main__':
    google_crawler()

    sitemap = 'https: // www.gap.com / native - sitemap.xml'

    threaded_crawler(sitemap, scrape_callback=scrape_callback)
