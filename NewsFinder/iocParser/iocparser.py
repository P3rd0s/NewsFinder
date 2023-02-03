import io
import os
import argparse
import glob
import re


import pandas as pd
from PyPDF2 import PdfReader
from redis.client import Redis
from requests import Response

from NewsFinder.constants.constants import IOC_ID_KEY, IOC_TYPES, IOC_DATES

try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser


class WhiteList(dict):
    def __init__(self, basedir):
        super().__init__()
        whitelists = os.path.join(basedir, "whitelists/wl-*.ini")
        file_paths = glob.glob(whitelists)
        for path in file_paths:
            t = os.path.splitext(path)[0].split('-', -1)[-1]
            patterns = [line.strip() for line in open(path)]
            self[t] = [re.compile(p) for p in patterns]


class IOCParser(object):
    patterns = {}
    redis = None

    def __init__(self, patterns_ini, redis):
        basedir = os.path.dirname(os.path.abspath(__file__))
        self.load_patterns(patterns_ini)
        self.whitelist = WhiteList(basedir)
        self.redis: Redis = redis

    def load_patterns(self, fpath):
        config = ConfigParser.ConfigParser()
        with open(fpath) as f:
            config.read_file(f)

        for ioc_type in config.sections():
            try:
                ioc_pattern = config.get(ioc_type, 'pattern')
            except:
                continue

            if ioc_pattern:
                ind_regexp = re.compile(ioc_pattern)
                self.patterns[ioc_type] = ind_regexp

    def is_in_whitelist(self, ioc_match, ioc_type):
        if ioc_type not in self.whitelist.keys():
            return False
        for w in self.whitelist[ioc_type]:
            if w.findall(ioc_match):
                return True

        return False

    def parse_data(self, data, report):
        ioc_counter = 0

        for ioc_type, ioc_regexp in self.patterns.items():
            matches = ioc_regexp.findall(str(data))

            for ind_match in matches:
                if isinstance(ind_match, tuple):
                    ind_match = ind_match[0]

                if self.is_in_whitelist(ind_match, ioc_type):
                    continue

                try:
                    ioc_id = str(self.redis.incr(IOC_ID_KEY))
                    self.redis.hmset(IOC_ID_KEY + ":" + ioc_id, {
                        'type': ioc_type,
                        'id': ioc_id,
                        'ioc': ind_match,
                        'article_hash': report['SHA-1']
                    })
                    self.redis.sadd(IOC_TYPES + ":" + ioc_type, ioc_id)
                    self.redis.sadd(IOC_DATES + ":" + report['Date'][:2] + ":" + report['Year'], ioc_id)
                    ioc_counter += 1
                except Exception as unexpected_error:
                    message = "IOC saving failed for {}".format(ind_match)
                    print(message, unexpected_error)

        return ioc_counter

    def parse_csv(self, csvfile):
        try:
            for chunk in pd.read_csv(csvfile, usecols=['article'], chunksize=100000):
                self.parse_data(chunk.article.str.cat())

        except Exception:
            raise

    def parse_pdf(self, pdf_file_response: Response, report):
        ioc_counter = 0
        try:
            with io.BytesIO(pdf_file_response.content) as open_pdf_file:
                pdf = PdfReader(open_pdf_file)

                for page in pdf.pages:
                    data = page.extract_text()
                    ioc_counter = ioc_counter + self.parse_data(data, report)

        except Exception:
            raise

        return ioc_counter

    def parse(self, path):
        try:
            if os.path.isfile(path):
                with open(path, 'rb') as csvfile:
                    self.parse_csv(csvfile)
                return
        except Exception:
            raise


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('PATH', action='store', help='File to IOCs')
    argument_parser.add_argument('-p', dest='INI',
                                 default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patterns.ini'),
                                 help='Pattern file')

    args = argument_parser.parse_args()

    parser = IOCParser(args.INI)
    parser.parse(args.PATH)
