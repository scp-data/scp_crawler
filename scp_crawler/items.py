import scrapy


class WikiPage(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    page_id = scrapy.Field()
    rating = scrapy.Field()
    tags = scrapy.Field()
    history = scrapy.Field()
    raw_content = scrapy.Field()


class ScpItem(WikiPage):
    link = scrapy.Field()
    scp = scrapy.Field()
    scp_number = scrapy.Field()
    series = scrapy.Field()


class ScpTale(WikiPage):
    pass


class ScpGoi(WikiPage):
    pass


class ScpTitle(scrapy.Item):
    title = scrapy.Field()
    scp = scrapy.Field()
    link = scrapy.Field()
