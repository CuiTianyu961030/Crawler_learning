from urllib.parse import urlencode
from urllib.request import Request, urlopen
import requests
from lxml.html import fromstring
from pprint import pprint
import os
import json
import glob
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


LOGIN_URL = 'http://example.python-scraping.com/user/login'
LOGIN_EMAIL = 'example@python-scraping.com'
LOGIN_PASSWORD = 'example'
COUNTRY_OR_DISTRICT_URL = 'http://example.python-scraping.com/edit/United-Kingdom-239'


def failure_test():
    data = {'email': LOGIN_EMAIL, 'password': LOGIN_PASSWORD}
    # encoded_data = urlencode(data)
    # request = Request(LOGIN_URL, encoded_data.encode('utf-8'))
    # response = urlopen(request)
    # print(response.geturl())
    response = requests.post(LOGIN_URL, data)
    print(response.url)


def parse_form(html):
    tree = fromstring(html)
    data = {}
    for e in tree.cssselect('form input'):
        if e.get('name'):
            data[e.get('name')] = e.get('value')
    return data


def success_test():
    html = requests.get(LOGIN_URL)
    data = parse_form(html.content)
    # pprint(form)
    data['email'] = LOGIN_EMAIL
    data['password'] = LOGIN_PASSWORD
    response = requests.post(LOGIN_URL, data, cookies=html.cookies)
    print(response.url)
    # print(response.cookies.keys())
    # print(response.cookies.values())


def load_ff_sessions(session_filename):
    cookies = {}
    if os.path.exists(session_filename):
        json_data = json.loads(open(session_filename, 'rb').read())
        for window in json_data.get('windows', []):
            for cookie in window.get('cookies', []):
                cookies[cookie.get('name')] = cookie.get('value')
    else:
        print('Session filename does not exist:', session_filename)
    return cookies


def find_ff_sessions():
    path = '/Users/cuitianyu/Library/Application Support/Google/Chrome/Default/Session Storage'
    filename = os.path.join(path, '008555.ldb')
    matches = glob.glob(os.path.expanduser(filename))
    if matches:
        return matches[0]


def chrome_test():
    session_filename = find_ff_sessions()
    cookies = load_ff_sessions(session_filename)
    url = 'http://example.python-scraping.com'
    html = requests.get(url, cookies=cookies)
    tree = fromstring(html.content)
    tree.cssselect('ul#navbar li a')[0].text_content()


def login(session=None):
    if session is None:
        html = requests.get(LOGIN_URL)
    else:
        html = session.get(LOGIN_URL)
    data = parse_form(html.content)
    data['email'] = LOGIN_EMAIL
    data['password'] = LOGIN_PASSWORD
    if session is None:
        response = requests.post(LOGIN_URL, data, cookies=html.cookies)
    else:
        response = session.post(LOGIN_URL, data)
    assert 'login' not in response.url
    return response, session


def requests_edit():
    session = requests.Session()
    response, session = login(session=session)
    country_or_district_html = session.get(COUNTRY_OR_DISTRICT_URL)
    data = parse_form(country_or_district_html.content)
    pprint(data)
    data['population'] = int(data['population']) + 1
    response = session.post(COUNTRY_OR_DISTRICT_URL, data)


def get_driver():
    # try:
    #     return webdriver.PhantomJS()
    # except Exception:
    return webdriver.Chrome()


def login_selenium(driver):
    driver.get(LOGIN_URL)
    driver.find_element_by_id('auth_user_email').send_keys(LOGIN_EMAIL)
    driver.find_element_by_id('auth_user_password').send_keys(LOGIN_PASSWORD + Keys.RETURN)
    pg_loaded = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'results')))
    assert 'login' not in driver.current_url


def add_population(driver):
    driver.get(COUNTRY_OR_DISTRICT_URL)
    population = driver.find_element_by_id('places_population')
    new_population = int(population.get_attribute('value')) + 1
    population.clear()
    population.send_keys(new_population)
    driver.find_element_by_xpath('//input[@type="submit"]').click()
    pg_loaded = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "places_population__row")))
    test_population = int(driver.find_element_by_css_selector('#places_population__row .w2p_fw').text.replace(',', ''))
    assert test_population == new_population


if __name__ == '__main__':
    # failure_test()
    # success_test()
    # chrome_test()
    # requests_edit()
    driver = get_driver()
    login_selenium(driver)
    add_population(driver)
    driver.quit()
