# -*- coding: utf-8 -*-

import csv
import json
import random
import re
import time
from datetime import datetime
from html import unescape
from urllib.parse import quote

import usaddress
from scrapy import Spider, Request, Selector
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome, Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from .send_email_notifications import SendEmailNotifications

# Please Put Your Facebook Login Credentials
user_email = 'alifarslan786@gmail.com'
user_password = """arslan'"'1  """


def get_search_terms_from_file():
    with open('../input/search terms.csv', mode='r', encoding='utf-8') as csv_file:
        return [x.get('search keyword') for x in csv.DictReader(csv_file)
                if x.get('search keyword', '').strip()]


def clean(text):
    text = re.sub(u'"', u"\u201C", unescape(text or ''))
    text = re.sub(u"'", u"\u2018", text)
    for c in ['\r\n', '\n\r', u'\n', u'\r', u'\t', u'\xa0']:
        text = text.replace(c, ' ')
    return re.sub(' +', ' ', text).strip()


class FacebookPublicGroupsSpider(Spider):
    name = 'fb_login_search_pages_spider'
    allowed_domains = ['www.facebook.com']
    base_url = 'https://www.facebook.com/'

    pages_search_url_t = 'https://web.facebook.com/search/pages/?q='

    # options = webdriver.ChromeOptions()
    options = webdriver.FirefoxOptions()
    options.add_argument('--disable-gpu')

    # driver = Chrome(ChromeDriverManager().install(), options=options)
    driver = Firefox(executable_path="../geckodriver", options=options)
    driver.get("https://facebook.com/")
    # driver.set_window_position(10, 10)
    # driver.set_window_size(500, 500)
    time.sleep(5)

    email = driver.find_element_by_id('email').send_keys(user_email)
    time.sleep(0.5)
    password = driver.find_element_by_id('pass').send_keys(user_password)
    time.sleep(0.5)
    driver.find_element_by_name('login').click()
    time.sleep(7)

    # driver.get('https://www.facebook.com/imagedentclinic/about')
    # time.sleep(4)
    # response = Selector(text=driver.page_source)
    # address = re.findall('full_address\":\"(.*)', driver.page_source)
    # if address:
    #     address = address[0].split('}')[0].strip('"').strip()
    #     address_item = get_address_parts(address)
    #     print(address_item)

    today_date = datetime.today().strftime('%d%b%y')
    email_sender = SendEmailNotifications()

    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': f'../output/facebook_pages_{today_date}.csv',
        'FEED_EXPORT_FIELDS': [
            'search_keyword', 'page_name', 'phone', 'email', 'country',
            'street_address', 'city', 'state', 'postal_code', 'page_link'
            ]
    }

    def start_requests(self):
        yield Request(url=self.base_url, callback=self.parse, meta={'handle_httpstatus_all': True})

    def parse(self, response):
        for keyword in get_search_terms_from_file()[:]:
            url = self.pages_search_url_t + quote(keyword)
            response = self.get_response_from_web_driver(url)
            time.sleep(30)

            for page in response.css('.nc684nl6 a::attr(href)').getall()[:]:
                page_url = page
                if 'facebook.com' not in page_url:
                    page_url = 'https://www.facebook.com/' + page_url.lstrip('/')
                item = dict()
                item['page_link'] = page_url
                item['search_keyword'] = keyword

                yield self.parse_details(
                    self.get_response_from_web_driver(page_url.rstrip('/') + '/about', scroll=False), item)

    def parse_details(self, response, item):
        item['page_name'] = (response.css('.bi6gxh9e.aov4n071 span::Text').getall() or [''])[0]
        if not item['page_name']:
            return

        phone = re.findall('phone_number\":\"(.*)\"', self.driver.page_source)
        if phone:
            phone = phone[0].split('"')[0]
        item['phone'] = phone

        if not item['phone']:
            phone_numbers = re.findall(r'[+0-9 ]+', self.driver.page_source)
            time.sleep(0.2)
            phone = [p for p in phone_numbers if p and p.strip() and len(p) > 10]
            if phone:
                item['phone'] = phone[0]

        email = ''.join([a for a in response.css('a::attr(href)').getall() if 'mailto' in a][-1:])
        email = email.replace('mailto:', '')
        item['email'] = email if len(email) < 30 else ''

        address = re.findall('full_address\":\"(.*)', self.driver.page_source)
        time.sleep(0.2)
        if address:
            address = address[0].split('}')[0].strip('"').strip()
            address = clean(address.replace("\\n", ' '))
            address_item = self.get_address_parts(address)
            item.update(address_item)

        if item['email']:
            self.email_sender.send_message(item['email'], '')

        return item

    def get_response_from_web_driver(self, url, scroll=True):
        self.driver.get(url)

        if not scroll:
            time.sleep(4)
            return Selector(text=self.driver.page_source)

        time.sleep(random.choice([1, 1.5, 2, 2.5]))
        start_point = 0
        end_point = 8000

        # self.driver.find_elements_by_css_selector('.n8z77nuh.knvmm38d.qzhwtbm6.buofh1pr span span')[0].click()
        # time.sleep(3)
        # self.driver.find_elements_by_css_selector('ul.buofh1pr.cbu4d94t.j83agx80 li.k4urcfbm')[0].click()
        # time.sleep(1)

        while True:
            if "end of results" in self.driver.page_source.lower():
                break

            self.driver.execute_script(f"window.scrollTo({start_point}, {end_point});")
            time.sleep(0.2)
            start_point, end_point = end_point, end_point + 8000

        return Selector(text=self.driver.page_source)

    def is_exists(self, css_selector, timeout=4.0):
        try:
            WebDriverWait(self.driver, timeout=timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))

            return True  # success

        except TimeoutException:
            return False  # fail

    def close(spider, reason):
        try:
            spider.driver.close()
        except:
            pass

    def get_address_parts(self, address):
        if not address:
            return {}
        address1, city, state, zip_code = '', '', '', ''

        for value, key in usaddress.parse(address):
            value = value.replace(',', '') + ' '
            if key in ['OccupancyIdentifier', 'Recipient']:
                continue
            if key == 'PlaceName':
                city += value
            elif key == 'StateName':
                state += value
            elif key == 'ZipCode':
                zip_code += value
            else:
                address1 += value

        address_item = dict(
            street_address=clean(address),
            city=clean(city),
            state=state.strip().upper(),
            postal_code=zip_code,
            country=clean((address or ' ').split(',')[-1].strip())
        )

        # if not address_item['country'].strip():
        #     address_item['country'] = clean(''.join(city.split(',')[-1:]))

        return address_item


"""
Dentist in saudi arabia
Medical Complex in Saudi Arabia
Doctors in Saudi Arabia
Family dentist
Emergency dentist in UAE
Pediatric dentist
Family dentist
Kids dentist
Dental Clinics in United Arab Emirates
Dental Clinics in Saudi Arab
medical complex in UAE
medical complex
Dental Clinics in Saudi Arabia
Dentist clinic
Dentist near me
Dentist in United Arab Emirates
"""
