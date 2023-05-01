import datetime
import hashlib
import locale
from functools import partial

import scrapy
from redis.client import Redis
from scrapy.spiders import XMLFeedSpider

from NewsFinder.constants.constants import ARTICLES
from NewsFinder.iocParser.iocparser import IOCParser


class ThreatpostSpider(XMLFeedSpider):
    name = 'threatpost'
    custom_settings = {
        'ROBOTSTXT_OBEY': False
    }
    allowed_domains = ['threatpost.com']
    start_urls = [
        'https://threatpost.com/category/cloud-security/feed/',
        'https://threatpost.com/category/critical-infrastructure/feed/',
        'https://threatpost.com/category/cryptography/feed/',
        'https://threatpost.com/category/government/feed/',
        'https://threatpost.com/category/hacks/feed/',
        'https://threatpost.com/category/iot/feed/',
        'https://threatpost.com/category/mobile-security/feed/',
        'https://threatpost.com/category/privacy/feed/',
        'https://threatpost.com/category/vulnerabilities/feed/',
        'https://threatpost.com/category/web-security/feed/'
    ]

    iterator = 'iternodes'  # This is actually unnecesary, since it's the default value
    itertag = 'item'

    ioc_parser = None
    redis = None

    def __init__(self, parser, redis):
        super().__init__()
        self.ioc_parser: IOCParser = parser
        self.redis: Redis = redis

    def parse_node(self, response, node):

        items = response.xpath('.//item')

        for item in items:
            locale.setlocale(locale.LC_ALL, 'en_US.utf8')
            date_str = item.xpath('.//pubDate/text()').get()
            date_obj = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S +0000')

            article_info = {
                'Date': date_obj.strftime('%m/%d/%Y'),
                'Title': item.xpath('.//title/text()').get(),
                'Year': date_obj.strftime('%Y'),
                'Source': item.xpath('.//*[name()=\'dc:creator\']/text()').get() or 'no_info',
                'Link': item.xpath('.//link/text()').get(),
                'SHA-1': hashlib.sha1(str.encode(item.xpath('.//link/text()').get())).hexdigest()
            }

            yield scrapy.Request(item.xpath('.//link/text()').get(),
                                 callback=partial(self.parse_article, report=article_info))

    def parse_article(self, response, report):
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
                                       response.xpath(
                                           './/div[@class="c-article__main"]//p/text()').extract()),
                                   report))

        except Exception as unexpected_error:
            message = "[!] Scrap failure for {}".format(report['Title'])
            print(message, unexpected_error)
