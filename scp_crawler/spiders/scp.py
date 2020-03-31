import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from bs4 import BeautifulSoup
import re

DOMAIN = 'www.scp-wiki.net'

class ScpItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    rating = scrapy.Field()
    tags = scrapy.Field()
    scp = scrapy.Field()
    scp_number = scrapy.Field()
    series = scrapy.Field()

    raw_content = scrapy.Field()


class ScpSpider(CrawlSpider):
    name = 'scp'

    start_urls = [f"http://{DOMAIN}/"]

    allowed_domains = [DOMAIN]

    rules = (
        Rule(LinkExtractor(allow=[r'system:page-tags/tag/.*'])),
        Rule(LinkExtractor(allow=[r'scp-series(?:-\d*)?', 'scp-ex'])),
        Rule(LinkExtractor(allow=[r'scp-\d{3,}(?:-[\w|\d]+)*']), callback='parse_item'),
        Rule(LinkExtractor(allow=[r'.*-proposal.*']), callback='parse_item') )

    def parse_item(self, response):
        self.logger.debug('Reviewing Potential SCP Item page: %s', response.url)
        content = response.css('#page-content').get()
        tags = response.css('.page-tags a::text').getall()
        if not content or not tags:
            return False
        if 'scp' not in tags:
            return False

        self.logger.info('Processing SCP Item page: %s', response.url)
        content_soup = BeautifulSoup(content, 'lxml')

        item = ScpItem()
        item['title'] = response.css('title::text').get()
        item['url'] = response.url
        item['tags'] = tags

        item['scp'] = self.get_scp_identifier(item)
        item['scp_number'] = self.get_scp_number(item)

        item['series'] = self.get_series(item)
        item['rating'] = self.get_rating(response, item)

        item['raw_content'] = str(self.clean_content_soup(content_soup))
        return item


    def get_rating(self, response, item):
        try:
            return int(response.css('.rate-points .number::text').get())
        except:
            pass
        # Editorial choice- this SCP was locked due to trolls
        if item['scp_number'] == 2721:
            return 200
        return 0

    def get_scp_identifier(self, item):
        try:
            return re.search('scp-\d{3,4}(?:-[\w|\d]*)?', item['url'])[0]
        except:
            pass
        if 'proposal' in item['url'] or '001-proposal' in item['tags']:
            return 'scp-001'
        if item['url'].endswith('taboo') and '4000' in item['tags']:
            return 'scp-4000'
        return False

    def get_scp_number(self, item):
        return int(re.findall(r'[0-9]+', item['scp'])[0])

    def get_series(self, item):
        if item['scp'].lower().endswith('-j') or 'joke' in item['tags']:
            return 'joke'
        if 'proposal' in item['scp'] or item['scp'].lower() == 'scp-001':
            return 'scp-001'
        if item['scp'].lower().endswith('-d') or 'decommissioned' in item['tags']:
            return 'decommissioned'
        if item['scp'].lower().endswith('-ex') or 'explained' in item['tags']:
            return 'explained'
        if 'international' in item['tags']:
            return 'international'

        number = self.get_scp_number(item)
        for x in range(1, 10):
            if number < x * 1000:
                return f"series-{x}"

        return 'other'

    def clean_content_soup(self, content_soup):
        # Remove Footer
        [x.extract() for x in content_soup.find_all("div", {'class': 'footer-wikiwalk-nav'})]

        # Remove Ratings Bar
        [x.extract() for x in content_soup.find_all("div", {'class': 'page-rate-widget-box'})]

        # Remove Empty Divs
        [x.extract() for x in content_soup.find_all("div") if len(x.get_text(strip=True)) == 0]

        return content_soup
