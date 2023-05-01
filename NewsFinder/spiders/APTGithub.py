import json
from functools import partial

import requests
import scrapy
from aioredis import Redis

from NewsFinder.constants.constants import ARTICLES


class APTParser(scrapy.Spider):
    name = 'APTSources'
    start_urls = ['https://raw.githubusercontent.com/aptnotes/data/master/APTnotes.json']
    notes = []

    ioc_parser = None
    redis = None

    MAX_PAGES = 120

    def __init__(self, parser, redis):
        super().__init__()
        self.ioc_parser = parser
        self.redis: Redis = redis

    def parse(self, response):
        notes = json.loads(response.body)
        notes.reverse()

        self.notes = notes

        for count, item in enumerate(notes):
            if count == self.MAX_PAGES:
                break
            yield scrapy.Request(item['Link'], callback=partial(self.parse_article, report=item))

    def parse_article(self, response, report):
        scripts = response.xpath('//body/script/text()')
        sections = scripts[-1].get().split(';')
        app_api = json.loads(sections[0].split('=')[1])['/app-api/enduserapp/shared-item']

        box_url = "https://app.box.com/index.php"
        box_args = "?rm=box_download_shared_file&shared_name={}&file_id={}"
        file_url = box_url + box_args.format(app_api['sharedName'], 'f_{}'.format(app_api['itemID']))

        self.download_report(report, file_url)

    def download_report(session, report, file_url):
        report_date = report['Date']
        report_title = report['Title']
        report_year = report['Year']
        report_source = report['Source']
        report_link = report['Link']
        report_filename = report['Filename']
        report_sha1 = report['SHA-1']

        try:
            if session.redis.sismember(ARTICLES, report_sha1) or not report_sha1:
                return

            report_file = requests.get(file_url, stream=True)

            session.redis.sadd(ARTICLES, report_sha1)
            session.redis.hmset(ARTICLES + ':' + report_sha1, {
                'date': report_date,
                'title': report_title,
                'year': report_year,
                'source': report_source,
                'link': report_link,
                'filename': report_filename,
                'ioc_count': 0
            })

            session.redis.hincrby(ARTICLES + ':' + report_sha1, 'ioc_count',
                                  session.ioc_parser.parse_pdf(report_file, report))

        except Exception as unexpected_error:
            message = "[!] Download failure for {}".format(report_filename)
            print(message, unexpected_error)
