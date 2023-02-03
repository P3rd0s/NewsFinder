import datetime
import hashlib
import locale

import scrapy
from redis.client import Redis

from NewsFinder.constants.constants import ARTICLES
from NewsFinder.iocParser.iocparser import IOCParser


class DarkreadingSpider(scrapy.Spider):
    name = 'darkreading'
    allowed_domains = ['darkreading.com']
    start_urls = ['https://www.darkreading.com/rss.xml/']

    ioc_parser = None
    redis = None

    def __init__(self, parser, redis):
        super().__init__()
        self.ioc_parser: IOCParser = parser
        self.redis: Redis = redis

    def parse(self, response):
        cards = response.xpath('.//item')

        for item in cards:
            link = item.xpath('.//link/text()').get()
            yield scrapy.Request(link, callback=self.parse_article)

    def parse_article(self, response):

        locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        date_str = response.xpath('.//*[@class="timestamp"]/text()').get()
        date_obj = datetime.datetime.strptime(date_str, '%B %d, %Y')

        report = {
            'Date': date_obj.strftime('%m/%d/%Y'),
            'Title': response.xpath('.//*[@class="article-title"]/text()').get(),
            'Year': date_obj.strftime('%Y'),
            'Source': response.xpath('.//*[@class="author-name"]/a/text()').get() or 'no_info',
            'Link': response.request.url,
            'Filename': 'no_data',
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
                'filename': report['Filename'],
                'ioc_count': 0
            })

            self.redis.hincrby(ARTICLES + ':' + report['SHA-1'], 'ioc_count',
                               self.ioc_parser.parse_data(''.join(
                                   response.xpath(
                                       './/*[contains(@class, "article-content")]/descendant::*[self::p or self::h4 or (self::a and not(ancestor::footer))]/text()').extract()),
                                   report))

        except Exception as unexpected_error:
            message = "[!] Scrap failure for {}".format(report['Title'])
            print(message, unexpected_error)
