import asyncio
import os.path

import psycopg2
import redis

from NewsFinder.iocParser.iocparser import IOCParser
from NewsFinder.spiders import threatpost, darkreading, thehackernews, APTGithub
from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerProcess


def postgres_test():
    try:
        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES', 'localhost'),
            database=os.environ.get('POSTGRES_DB', 'articlesdb'),
            user=os.environ.get('POSTGRES_USER', 'iocsfinder'),
            password=os.environ.get('POSTGRES_PASSWORD', 'strongHeavyPassword4thisdb'))
        return conn
    except:
        return False


async def main():
    postgres_storage = None
    redis_storage = None
    try:
        settings = get_project_settings()
        process = CrawlerProcess(settings)

        script_dir = os.path.dirname(__file__)
        abs_ini_path = os.path.join(script_dir, "iocParser/ioc-patterns.ini")

        while not postgres_storage:
            postgres_storage = postgres_test()

        redis_storage = redis.Redis(host=os.environ.get('REDIS', 'localhost'), decode_responses=True)
        ioc_parser = IOCParser(abs_ini_path, redis_storage, postgres_storage)

        process.crawl(darkreading.DarkreadingSpider, ioc_parser, redis_storage)
        process.crawl(thehackernews.ThehackernewsSpider, ioc_parser, redis_storage)
        process.crawl(threatpost.ThreatpostSpider, ioc_parser, redis_storage)
        process.crawl(APTGithub.APTParser, parser=ioc_parser, redis=redis_storage)
        process.start() # the script will block here until all crawling jobs are finished
    except Exception as unexpected_error:
        message = "Crawl failed: "
        print(message, unexpected_error)
    finally:
        print("DISCONNECT STORAGE")
        if redis_storage is not None:
            redis_storage.close()
        if postgres_storage is not None:
            postgres_storage.close()

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")