import scrapy
from scrapy.crawler import CrawlerProcess
from scp_crawler.spiders import scp

DIRECTORY='data'

SPIDERS = [
    scp.ScpSpider,
    scp.ScpIntSpider,
    scp.TaleSpider,
    scp.TaleIntSpider,
    scp.GoiSpider,
]

process = CrawlerProcess(settings={
    'FEED_FORMAT': 'json',
    'FEED_URI': f"{DIRECTORY}/%(name)s.json",
    'LOG_LEVEL': 'INFO'
})

for spider in SPIDERS:
    process.crawl(spider)

process.start() # the script will block here until the crawling is finished
