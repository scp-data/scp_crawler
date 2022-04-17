import scrapy
from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from twisted.internet import defer, reactor

from scp_crawler.spiders import scp

SPIDERS = [
    scp.ScpSpider,
    scp.ScpIntSpider,
    scp.TaleSpider,
    scp.TaleIntSpider,
    scp.GoiSpider,
]

configure_logging()
runner = CrawlerRunner(get_project_settings())


@defer.inlineCallbacks
def crawl():
    for spider in SPIDERS:
        yield runner.crawl(spider)
    reactor.stop()


crawl()
reactor.run()
