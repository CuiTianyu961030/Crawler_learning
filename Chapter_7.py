from Chapter_6 import parse_form
import requests
from pprint import pprint
from io import BytesIO
from lxml.html import fromstring
from PIL import Image
import base64
import pytesseract
import string
from lxml.html import fromstring
import time
import re
from configparser import ConfigParser


REGISTER_URL = 'http://example.python-scraping.com/user/register'
API_URL = 'https://www.9kw.eu/index.cgi'
API_KEY = 'A8ZUEP379F13ZCBWPL'


def get_captcha_img(html):
    tree = fromstring(html)
    img_data = tree.cssselect('div#recaptcha img')[0].get('src')
    img_data = img_data.partition(',')[-1]
    binary_img_data = base64.b64decode(img_data)
    img = Image.open(BytesIO(binary_img_data))
    return img


def ocr_test():
    session = requests.Session()
    html = session.get(REGISTER_URL)
    form = parse_form(html.content)
    pprint(form)

    img = get_captcha_img(html.content)
    # print(pytesseract.image_to_string(img))
    img.save('captcha_original.png')
    gray = img.convert('L')
    gray.save('captcha_gray.png')
    bw = gray.point(lambda x: 0 if x < 1 else 255, '1')
    bw.save('captcha_thresholded.png')
    word = pytesseract.image_to_string(bw)
    print(word)
    ascii_word = ''.join(c for c in word.lower() if c in string.ascii_lowercase)
    print(ascii_word)


def register(first_name, last_name, email, password):
    session = requests.Session()
    html = session.get(REGISTER_URL)
    form = parse_form(html.content)
    form['first_name'] = first_name
    form['last_name'] = last_name
    form['email'] = email
    form['password'] = form['password_two'] = password
    img = get_captcha_img(html.content)
    captcha = ocr(img)
    form['recaptcha_response_field'] = captcha
    resp = session.post(html.url, form)
    success = '/userregister' not in resp.url
    if not success:
        form_errors = fromstring(resp.content).cssselect('div.error')
        print('Form Errors:')
        print('n'.join((' {}: {}'.format(f.get('id'), f.text) for f in form_errors)))
    return success

def ocr(img):
    bw = img_to_bw(img)
    captcha = pytesseract.image_to_string(bw)
    cleaned = ''.join(c for c in captcha.lower() if c in string.ascii_lowercase)
    if len(cleaned) != len(captcha):
        print('removed bad characters: {}'.format(set(captcha) - set(cleaned)))
    return cleaned


def img_to_bw(img):
    gray = img.convert('L')
    bw = gray.point(lambda x: 0 if x < 1 else 255, '1')
    return bw


def ocr_practice():
    first_name = 'Tianyu'
    last_name = 'Cui'
    email = 'crawler@test.com'
    password = 'stuipdegg'
    success = register(first_name, last_name, email, password)
    print(success)


def send_captcha(api_key, img_data):
    data = {
        'action': 'usercaptchaupload',
        'apikey': api_key,
        'file-upload-01': img_data,
        'base64': '1',
        'selfsolve': '1',
        'maxtimeout': '60',
        'json': '1'
    }
    response = requests.post(API_URL, data)
    return response.content


def get_captcha_text(api_key, captcha_id):
    data = {
        'action': 'usercaptchacorrectdata',
        'id': captcha_id,
        'apikey': api_key,
        'json': 1
    }
    response = requests.get(API_URL, data)
    return response.content


class CaptchaAPI:
    def __init__(self, api_key, timeout=120):
        self.api_key = api_key
        self.timeout = timeout
        self.url = 'https://www.9kw.eu/index.cgi'

    def solve(self, img):
        img_buffer = BytesIO()
        img.save(img_buffer, format="PNG")
        img_data = img_buffer.getvalue()
        captucha_id = self.send(img_data)
        start_time = time.time()
        while time.time() < start_time + self.timeout:
            try:
                resp = self.get(captucha_id)
            except CaptchaError:
                pass
            else:
                # print(resp.items())
                # if resp.get('answer') is not None:
                if resp.get('answer') != 'NO DATA':
                    if resp.get('answer') == 'ERROR NO USER':
                        raise CaptchaError(
                            'Error: no user available to solve CAPTCHA'
                        )
                    else:
                        print('CAPTCHA solved!')
                        return captucha_id, resp.get('answer')
            print('Waiting for CAPTCHA ...')
            time.sleep(1)
        raise CaptchaError('Error: API timeout')

    def send(self, img_data):
        print('Submitting CAPTCHA')
        data = {
            'action': 'usercaptchaupload',
            'apikey': self.api_key,
            'file-upload-01': base64.b64encode(img_data),
            'base64': '1',
            'selfsolve': '0', # 0
            'json': '1',
            'maxtimeout': str(self.timeout)
        }
        result = requests.post(self.url, data)
        self.check(result.text)
        return result.json().get('captchaid')

    def get(self, captcha_id):
        data = {
            'action': 'usercaptchacorrectdata',
            'id': captcha_id,
            'apikey': self.api_key,
            'info': '1',
            'json': '1'
        }
        result = requests.get(self.url, data)
        self.check(result.text)
        return result.json()

    def check(self, result):
        if re.match('00dd w+', result):
            raise CaptchaError('API error: ' + result)

    def report(self, captcha_id, correct):
        data = {
            'action': 'usercaptchacorrectback',
            'id': captcha_id,
            'apikey': self.api_key,
            'correct': (lambda c: 1 if c else 2)(correct),
            'json': '1',
        }
        resp = requests.get(self.url, data)
        return resp.json()


class CaptchaError(Exception):
    pass


def captcha_service():
    captcha = CaptchaAPI(API_KEY)
    img = Image.open('captcha_original.png')
    captcha_id, text = captcha.solve(img)
    print(text)


# def get_api_key():
#     config = ConfigParser()
#     config.read('../config/api.cfg')
#     return config.get('captcha_api', 'key')


def register_final(first_name, last_name, email, password):
    session = requests.Session()
    html = session.get(REGISTER_URL)
    form = parse_form(html.content)
    form['first_name'] = first_name
    form['last_name'] = last_name
    form['email'] = email
    form['password'] = form['password_two'] = password
    # api_key = get_api_key()
    api_key = API_KEY
    img = get_captcha_img(html.content)
    api = CaptchaAPI(api_key)
    captcha_id, captcha = api.solve(img)
    form['recaptcha_response_field'] = captcha
    resp = session.post(html.url, form)
    success = '/user/register' not in resp.url
    if success:
        api.report(captcha_id, 1)
    else:
        form_errors = fromstring(resp.content).cssselect('div.error')
        print('Form Errors:')
        print('n'.join(
            (' {}: {}'.format(f.get('id'), f.text) for f in form_errors)))
        if 'invalid' in [f.text for f in form_errors]:
            api.report(captcha_id, 0)
    return success


def captcha_service_practice():
    first_name = 'Tianyu'
    last_name = 'Cui'
    email = 'crawler@test.com'
    password = 'stuipdegg'
    success = register_final(first_name, last_name, email, password)
    print(success)


if __name__ == '__main__':
    # ocr_test()
    # ocr_practice()
    # captcha_service()
    captcha_service_practice()
