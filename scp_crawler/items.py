import scrapy


class WikiPage(scrapy.Item):
    title = scrapy.Field()
    link = scrapy.Field()
    url = scrapy.Field()
    domain = scrapy.Field()
    page_id = scrapy.Field()
    rating = scrapy.Field()
    tags = scrapy.Field()
    history = scrapy.Field()
    raw_content = scrapy.Field()
    raw_source = scrapy.Field()
    references = scrapy.Field()


class ScpItem(WikiPage):
    scp = scrapy.Field()
    scp_number = scrapy.Field()
    series = scrapy.Field()


class ScpHub(WikiPage):
    paginated_content = scrapy.Field()


class ScpTale(WikiPage):
    pass


class ScpGoi(WikiPage):
    pass


class ScpSupplement(WikiPage):
    pass


class ScpTitle(scrapy.Item):
    title = scrapy.Field()
    scp = scrapy.Field()
    link = scrapy.Field()
