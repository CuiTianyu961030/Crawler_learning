import requests
import string
from pprint import pprint
from csv import DictWriter
# from PySide2.QtGui import *
# from PySide2.QtCore import *
# from PySide2.QtWidgets import *
# from PySide2.QtWebEngineWidgets import *
from lxml.html import fromstring
# from PyQt5.QtWidgets import QApplication
# from PyQt5.QtCore import QUrl, QEventLoop
# from PyQt5.QtWebEngineWidgets import QWebEnginePage
from selenium import webdriver


def ajax_test():
    resp = requests.get('http://example.python-scraping.com/ajax/search.json?page'
                        '=0&page_size=10&search_term=a')
    pprint(resp.json())


def json_scraper():
    PAGE_SIZE = 10
    template_url = 'http://example.python-scraping.com/ajax/' + 'search.json?page={}' \
                                                                '&page_size={}&search_term={}'
    countries_or_districts = set()

    for letter in string.ascii_lowercase:
        print('Seaching with %s' % letter)
        page = 0
        while True:
            resp = requests.get(template_url.format(page, PAGE_SIZE, letter))
            data = resp.json()
            print('adding %d more records from page %d' % (len(data.get('records')), page))
            for record in data.get('records'):
                countries_or_districts.add(record['country_or_district'])
            page += 1
            if page >= data['num_pages']:
                break

    with open('countries_or_districts.txt', 'w') as countries_or_districts_file:
        countries_or_districts_file.write('n'.join(sorted(countries_or_districts)))


def json_scraper_plus():
    PAGE_SIZE = 1000
    template_url = 'http://example.python-scraping.com/ajax/' + 'search.json?page=0&' \
                                                                'page_size={}&search_term=.'
    resp = requests.get(template_url.format(PAGE_SIZE))
    data = resp.json()
    records = data.get('records')
    with open('countries_or_districts.csv', 'w') as countries_or_districts_file:
        wrtr = DictWriter(countries_or_districts_file, fieldnames=records[0].keys())
        wrtr.writeheader()
        wrtr.writerows(records)


# def pyside_test():
#     url = 'http://example.python-scraping.com/dynamic'
#     app = QApplication([])
#     webview = QWebEngineView()
#     loop = QEventLoop()
#     webview.loadFinished.connect(loop.quit)
#     webview.load(QUrl(url))
#     loop.exec_()
#     html = webview.page().toHtml()
#     tree = fromstring(html)
#     print(tree.cssselect('#result')[0].text_content())


def selenium_test():
    driver = webdriver.Chrome()
    driver.get('http://example.python-scraping.com/search')
    driver.find_element_by_id('search_term').send_keys('.')
    js = "document.getElementById('page_size').options[1].text = '1000';"
    driver.execute_script(js)
    driver.find_element_by_id('search').click()
    driver.implicitly_wait(30)
    links = driver.find_elements_by_css_selector('#results a')
    countries_or_districts = [link.text for link in links]
    print(countries_or_districts)
    driver.close()


if __name__ == '__main__':
    # ajax_test()
    # json_scraper()
    # json_scraper_plus()
    # pyside_test()
    selenium_test()
