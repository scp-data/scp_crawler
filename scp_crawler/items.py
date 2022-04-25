import scrapy


class ScpTitle(scrapy.Item):
    title = scrapy.Field()
    scp = scrapy.Field()
    link = scrapy.Field()


class ScpItem(scrapy.Item):
    url = scrapy.Field()
    link = scrapy.Field()
    title = scrapy.Field()
    rating = scrapy.Field()
    tags = scrapy.Field()
    scp = scrapy.Field()
    scp_number = scrapy.Field()
    series = scrapy.Field()
    history = scrapy.Field()
    raw_content = scrapy.Field()


class ScpTale(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    rating = scrapy.Field()
    tags = scrapy.Field()
    raw_content = scrapy.Field()


class ScpGoi(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    rating = scrapy.Field()
    tags = scrapy.Field()
    raw_content = scrapy.Field()
