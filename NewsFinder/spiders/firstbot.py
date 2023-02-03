import scrapy


class FirstbotSpider(scrapy.Spider):
    name = 'firstbot'
    allowed_domains = ['https://www.avira.com/en/blog/technology-insights/all-articles']
    start_urls = ['https://www.avira.com/en/blog/technology-insights/all-articles/']

    def parse(self, response):
        pass
        # # Extracting the content using css selectors
        # titles = response.css('.staging-conten--article-inner .title a::text').extract() + response.css(
        #     '.entry-content .title a::text').extract()
        # description = response.css('.staging-conten--article-inner p::text').extract() + response.css(
        #     '.entry-content p::text').extract()
        #
        # # Give the extracted content row wise
        # for item in zip(titles, description):
        #     # create a dictionary to store the scraped info
        #     scraped_info = {
        #         'title': item[0],
        #         'description': item[1],
        #     }
        #
        #     # yield or give the scraped info to scrapy
        #     yield scraped_info
