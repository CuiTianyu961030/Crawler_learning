import re
# from Chapter_1 import download
from bs4 import BeautifulSoup
from pprint import pprint
from lxml.html import fromstring, tostring
import time
import csv


def regex():
    url = 'http://example.python-scraping.com/view/UnitedKingdom-239'
    html = download(url)
    print(re.findall(r'<td class="w2p_fw">(.*?)</td>', html)[1])
    # print(re.findall('''<tr id="places_ares__row">.*?<tds*class=["']w2p_fw["']>(.*?)</td>''', html))


def beautiful_soup_practice():
    broken_html = '<ul class=country_or_district><li>Area<li>Population</ul>'
    # soup = BeautifulSoup(broken_html, 'html.parser')
    soup = BeautifulSoup(broken_html, 'html5lib')
    fixed_html = soup.prettify()
    pprint(fixed_html)
    ul = soup.find('ul', attrs={'class': 'country_or_district'})
    print(ul.find('li'))
    print(ul.find_all('li'))


def beautiful_soup():
    url = 'http://example.python-scraping.com/view/United-Kingdom-239'
    html = download(url)
    # print(html)
    soup = BeautifulSoup(html, 'html5lib')
    tr = soup.find(attrs={'id': 'places_area__row'})
    td = tr.find(attrs={'class': 'w2p_fw'})
    area = td.text
    print(area)


def lxml_practice():
    url = 'http://example.python-scraping.com/view/United-Kingdom-239'
    html = download(url)
    tree = fromstring(html)
    fixed_html = tostring(tree, pretty_print=True)
    # print(fixed_html)
    td = tree.cssselect('tr#places_area__row > td.w2p_fw')[0]
    # print(td)
    area = td.text_content()
    print(area)


def xpath_practice():
    url = 'http://example.python-scraping.com/view/United-Kingdom-239'
    html = download(url)
    tree = fromstring(html)
    area = tree.xpath('//tr[@id="places_area__row"]/td[@class="w2p_fw"]/text()')[0]
    print(area)

FIELDS = ('area', 'population', 'iso', 'country_or_district', 'capital', 'continent', 'tld', 'currency_code',
          'currency_name', 'phone', 'postal_code_format', 'postal_code_regex', 'languages', 'neighbours')


def re_scraper(html):
    results = {}
    for field in FIELDS:
        results[field] = re.search('<tr id="places_%s__row">.*?<td class="w2p_fw">(.*?)</td>' % field, html).groups()[0]
    return results


def bs_scraper(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = {}
    for field in FIELDS:
        results[field] = soup.find('table').find('tr', id='places_%s__row' % field).find('td', class_='w2p_fw').text
    return results


def lxml_scraper(html):
    tree = fromstring(html)
    results = {}
    for field in FIELDS:
        results[field] = tree.cssselect('table > tr#places_%s__row > td.w2p_fw' % field)[0].text_content()
    return results


def lxml_xpath_scraper(html):
    tree = fromstring(html)
    results = {}
    for field in FIELDS:
        results[field] = tree.xpath('//tr[@id="places_%s__row"]/td[@class="w2p_fw"]' % field)[0].text_content()
    return results


def time_counter():
    NUM_ITERATIONS = 1000  # number of times to test each scraper
    html = download('http://example.python-scraping.com/view/United-Kingdom-239')
    scrapers = [
        ('Regular expressions', re_scraper),
        ('BeautifulSoup', bs_scraper),
        ('Lxml', lxml_scraper),
        ('Xpath', lxml_xpath_scraper)]
    for name, scraper in scrapers:
        # record start time of scrape
        start = time.time()
        for i in range(NUM_ITERATIONS):
            if scraper == re_scraper:
                re.purge()
            result = scraper(html)
            # check scraped result is as expected
            assert result['area'] == '0 square kilometres'
        # record end time of scrape and output the total
        end = time.time()
        print('%s: %.2f seconds' % (name, end - start))


def scrape_callback(url, html):
    fields = ('area', 'population', 'iso', 'country_or_district', 'capital',
                  'continent', 'tld', 'currency_code', 'currency_name',
                  'phone', 'postal_code_format', 'postal_code_regex',
                  'languages', 'neighbours')
    if re.search('/view/', url):
        tree = fromstring(html)
        all_rows = [tree.xpath('//tr[@id="places_%s__row"]/td[@class="w2p_fw"]' % field)[0].text_content()
                for field in fields]
        print(url, all_rows)


class CsvCallback:
    def __init__(self):
        self.writer = csv.writer(open('data.csv', 'w'))
        self.fields = ('area', 'population', 'iso', 'country_or_district',
                       'currency_name', 'capital', 'continent', 'tld',
                       'currency_code', 'phone', 'postal_code_format',
                       'postal_code_regex', 'languages', 'neighbours')
        self.writer.writerow(self.fields)

    def __call__(self, url, html):
        if re.search('places/default/view', html):
            tree = fromstring(html)
            if len(tree.xpath('//tr[@id="places_area__row"]/td[@class="w2p_fw"]')) != 0:
                all_rows = [tree.xpath('//tr[@id="places_%s__row"]/td[@class="w2p_fw"]' %
                        field)[0].text_content() for field in self.fields]
                self.writer.writerow(all_rows)


if __name__ == "__main__":
    # regex()
    # beautiful_soap_practice()
    # beautiful_soup()
    # lxml_practice()
    # xpath_practice()
    time_counter()
