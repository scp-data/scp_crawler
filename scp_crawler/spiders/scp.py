import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from bs4 import BeautifulSoup
import re


class ScpItem(scrapy.Item):
    url = scrapy.Field()
    rating = scrapy.Field()
    tags = scrapy.Field()
    scp = scrapy.Field()

    raw_content = scrapy.Field()


class ScpSpider(CrawlSpider):
    name = 'scp'

    start_urls = ['http://www.scp-wiki.net/']

    rules = (
        Rule(LinkExtractor(allow=(r'scp-series(?:-\d*)?', 'scp-ex'))),
        Rule(LinkExtractor(allow=(r'scp-\d{3,4}(?:-[\w|\d]*)?', )), callback='parse_item'), )

    def parse_item(self, response):
        self.logger.info('This is an SCP Item page: %s', response.url)
        content = response.css('#page-content').get()
        if not content:
            return False
        content_soup = BeautifulSoup(content, 'lxml')

        item = ScpItem()
        item['scp'] = re.search('scp-\d{3,4}(?:-[\w|\d]*)?', response.url)[0]
        item['url'] = response.url
        item['rating'] = int(response.css('.rate-points .number::text').get())
        item['tags'] = response.css('.page-tags a::text').getall()

        # Remove Footer
        [x.extract() for x in content_soup.find_all("div", {'class': 'footer-wikiwalk-nav'})]

        # Remove Ratings Bar
        [x.extract() for x in content_soup.find_all("div", {'class': 'page-rate-widget-box'})]

        # Remove Empty Divs
        [x.extract() for x in content_soup.find_all("div") if len(x.get_text(strip=True)) == 0]


        item['raw_content'] = str(content_soup)
        return item
