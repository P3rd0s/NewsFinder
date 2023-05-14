import datetime
import hashlib
import locale

import scrapy
from redis.client import Redis

from NewsFinder.constants.constants import ARTICLES
from NewsFinder.modules.IocParser.iocparser import IOCParser


class ThehackernewsSpider(scrapy.Spider):
    name = 'thehackernews'
    start_urls = ['https://thehackernews.com/']

    MAX_PAGES = 30

    ioc_parser = None
    redis = None

    def __init__(self, parser, redis):
        super().__init__()
        self.ioc_parser: IOCParser = parser
        self.redis: Redis = redis

    def parse(self, response):
        self.MAX_PAGES -= 1

        attacks = response.xpath('//*[@class="story-link"]')

        for item in attacks:
            yield scrapy.Request(item.xpath(".//@href").get(), callback=self.parse_article)

        if self.MAX_PAGES != 0:
            next_page = response.css('a.blog-pager-older-link-mobile::attr(href)').get()
            yield scrapy.Request(next_page, callback=self.parse)

    def parse_article(self, response):

        locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        date_str = response.xpath('.//*[@class=\'author\']/text()').get()
        if date_str is None:
            date_str = 'Jan 1, 1980'
        date_obj = datetime.datetime.strptime(date_str, '%b %d, %Y')

        report = {
            'Date': date_obj.strftime('%m/%d/%Y'),
            'Title': response.xpath('.//h1[@class=\'story-title\']/a/text()').get(),
            'Year': date_obj.strftime('%Y'),
            'Source': response.xpath('.//*[@class=\'author\'][2]/text()').get() or 'no_info',
            'Link': response.request.url,
            'SHA-1': hashlib.sha1(str.encode(response.request.url)).hexdigest()
        }

        try:
            if self.redis.sismember(ARTICLES, report['SHA-1']) or not report['SHA-1']:
                return

            self.redis.sadd(ARTICLES, report['SHA-1'])
            self.redis.hmset(ARTICLES + ':' + report['SHA-1'], {
                'date': report['Date'],
                'title': report['Title'],
                'year': report['Year'],
                'source': report['Source'],
                'link': report['Link'],
                'ioc_count': 0
            })

            self.redis.hincrby(ARTICLES + ':' + report['SHA-1'], 'ioc_count',
                               self.ioc_parser.parse_data(
                                   '\n'.join(
                                       response.xpath('.//div[@id=\'articlebody\']/descendant::*/text()').extract()),
                                   report))

        except Exception as unexpected_error:
            message = "[!] Scrap failure for {}".format(report['Title'])
            print(message, unexpected_error)
