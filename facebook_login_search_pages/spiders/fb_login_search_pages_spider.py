# -*- coding: utf-8 -*-

import csv
import json
import random
import re
import time
from datetime import datetime
from urllib.parse import quote

from scrapy import Spider, Request, Selector
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome, Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


user_email = '03041151082'
user_password = """pma'"'1  """


def get_search_terms_from_file():
    with open('../input/search terms.csv', mode='r', encoding='utf-8') as csv_file:
        return [x.get('search keyword') for x in csv.DictReader(csv_file)
                if x.get('search keyword', '').strip()]


class FacebookPublicGroupsSpider(Spider):
    name = 'fb_login_search_pages_spider'
    allowed_domains = ['www.facebook.com']
    base_url = 'https://www.facebook.com/'

    pages_search_url_t = 'https://web.facebook.com/search/pages/?q='

    # options = webdriver.ChromeOptions()
    options = webdriver.FirefoxOptions()
    options.add_argument('--disable-gpu')

    # driver = Chrome(ChromeDriverManager().install(), options=options)
    driver = Firefox(executable_path="../geckodriver")
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

    # driver.get('https://web.facebook.com/BritishCouncilSaudiArabia/')
    # time.sleep(4)
    # response = Selector(text=driver.page_source)

    today_date = datetime.today().strftime('%d%b%y')

    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': f'../output/facebook_pages_{today_date}.csv',
        'FEED_EXPORT_FIELDS': ['page_name', 'page_link', 'search_keyword', 'phone', 'email',
                               'street_address', 'city', 'state', 'postal_code', 'country']
    }

    def start_requests(self):
        yield Request(url=self.base_url, callback=self.parse, meta={'handle_httpstatus_all': True})

    def parse(self, response):
        for keyword in get_search_terms_from_file()[:2]:
            url = self.pages_search_url_t + quote(keyword)
            response = self.get_response_from_web_driver(url)
            time.sleep(30)

            for page in response.css('.nc684nl6 a::attr(href)').getall()[:5]:
                page_url = page
                item = dict()
                item['page_link'] = page_url
                item['search_keyword'] = keyword

                yield self.parse_details(
                    self.get_response_from_web_driver(page_url.rstrip('/') + '/about', scroll=False), item)

    def parse_details(self, response, item):
        item['page_name'] = (response.css('.bi6gxh9e.aov4n071 span::Text').getall() or [''])[0]
        if not item['page_name']:
            return

        phone = [a for a in response.css('[class="j83agx80"] .qzhwtbm6 span::text').getall() or ['']][0]
        phone = re.findall(r'[+0-9 ]+', phone)
        if len(phone) > 10:
            item['phone'] = phone

        email = ''.join([a for a in response.css('a::attr(href)').getall() if 'mailto' in a][-1:])
        email = email.replace('mailto:', '')
        item['email'] = email if len(email) < 30 else ''

        raw = json.loads(response.css('[type="application/ld+json"]::text').get('{}'))
        address = raw.get('address', {})
        if address:
            item["street_address"] = address['streetAddress']
            item["city"] = address['addressLocality'] or ''
            item["state"] = address['addressRegion']
            item["postal_code"] = address['postalCode']
            item['country'] = item["city"].split(',')[-1].strip()

        return item

    def get_response_from_web_driver(self, url, scroll=True):
        self.driver.get(url)

        if not scroll:
            time.sleep(4)
            return Selector(text=self.driver.page_source)

        time.sleep(random.choice([1, 1.5, 2, 2.5]))
        start_point = 0
        end_point = 8000

        self.driver.find_elements_by_css_selector('.n8z77nuh.knvmm38d.qzhwtbm6.buofh1pr span span')[0].click()
        time.sleep(3)
        self.driver.find_elements_by_css_selector('ul.buofh1pr.cbu4d94t.j83agx80 li.k4urcfbm')[0].click()
        time.sleep(1)

        while True:
            if "End of results" in self.driver.page_source:
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
