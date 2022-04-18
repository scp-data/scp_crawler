import re

import scrapy
from bs4 import BeautifulSoup
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import ScpGoi, ScpItem, ScpTale, ScpTitle

DOMAIN = "scp-wiki.wikidot.com"
INT_DOMAIN = "scp-int.wikidot.com"


class ScpSpider(CrawlSpider):
    name = "scp"

    start_urls = [
        f"http://{DOMAIN}/",
        f"http://{DOMAIN}/system:page-tags/tag/scp",
    ]

    allowed_domains = [DOMAIN]

    rules = (
        Rule(LinkExtractor(allow=[r"scp-series(?:-\d*)?", "scp-ex"])),
        Rule(LinkExtractor(allow=[r"scp-\d{3,}(?:-[\w|\d]+)*"]), callback="parse_item"),
        Rule(LinkExtractor(allow=[r".*-proposal.*"]), callback="parse_item"),
    )

    def validate(self, tags):
        if "scp" not in tags:
            return False
        if "tale" in tags:
            return False
        return True

    def parse_item(self, response):
        self.logger.debug("Reviewing Potential SCP Item page: %s", response.url)
        content = response.css("#page-content").get()
        tags = response.css(".page-tags a::text").getall()
        if not content or not tags:
            return False
        if not self.validate(tags):
            return False

        self.logger.info("Processing SCP Item page: %s", response.url)
        content_soup = BeautifulSoup(content, "lxml")

        item = ScpItem()
        item["title"] = response.css("title::text").get()
        item["url"] = response.url
        item["tags"] = tags

        item["scp"] = self.get_scp_identifier(item)
        item["scp_number"] = self.get_scp_number(item)
        item["series"] = self.get_series(item)

        if item["scp_number"] == 2721:
            # Editorial choice- this SCP was locked due to trolls
            item["rating"] = 200
        else:
            item["rating"] = get_rating(response)

        item["raw_content"] = str(clean_content_soup(content_soup))
        return item

    def get_scp_identifier(self, item):
        try:
            return re.search("scp(?:-[\w|\d]*)?-\d{3,4}(?:-[\w|\d]*)?", item["url"])[0]
        except:
            pass
        if "proposal" in item["url"] or "001-proposal" in item["tags"]:
            return "scp-001"
        if item["url"].endswith("taboo") and "4000" in item["tags"]:
            return "scp-4000"
        return "unknown"

    def get_scp_number(self, item):
        matches = re.findall(r"[0-9]+", item["scp"])
        if matches:
            return int(matches[0])
        return 0

    def get_series(self, item):
        if item["scp"].lower().endswith("-j") or "joke" in item["tags"]:
            return "joke"
        if "proposal" in item["scp"] or item["scp"].lower() == "scp-001":
            return "scp-001"
        if item["scp"].lower().endswith("-d") or "decommissioned" in item["tags"]:
            return "decommissioned"
        if item["scp"].lower().endswith("-ex") or "explained" in item["tags"]:
            return "explained"
        if item["scp"].lower().endswith("-arc") or "archived" in item["tags"]:
            return "archived"
        if "international" in item["tags"]:
            return "international"

        number = self.get_scp_number(item)
        for x in range(1, 10):
            if number < x * 1000:
                return f"series-{x}"

        return "other"


class ScpTitleSpider(CrawlSpider):
    name = "scp_titles"

    start_urls = [f"http://{DOMAIN}/"]

    allowed_domains = [DOMAIN]

    rules = (Rule(LinkExtractor(allow=[r"scp-series(?:-\d*)?", "scp-ex"]), callback="parse_item"),)

    def parse_item(self, response):
        self.logger.warning("Reviewing SCP Index page: %s", response.url)

        listings = response.css(".content-panel > ul > li")
        for listing in listings:
            try:
                self.logger.info(listing.get())
                scp = listing.xpath("a/text()").get()
                if scp == "taboo":
                    scp = "scp-4000"
                    title = "Taboo"
                else:
                    title = listing.css("li::text").get().strip(" -")
                item = ScpTitle()
                item["scp"] = scp
                item["title"] = title
                yield item
            except:
                pass


class ScpTaleSpider(CrawlSpider):
    name = "scp_tales"

    start_urls = [
        f"http://{DOMAIN}/tales-by-title",
        f"http://{DOMAIN}/system:page-tags/tag/tale",
    ]

    allowed_domains = [DOMAIN]

    rules = (
        Rule(
            LinkExtractor(
                allow=[
                    re.escape("tales-by-title"),
                    re.escape("system:page-tags/tag/tale"),
                ]
            )
        ),
        Rule(LinkExtractor(allow=[r".*"]), callback="parse_tale"),
    )

    def parse_tale(self, response):
        self.logger.debug("Reviewing Potential SCP Tale page: %s", response.url)
        content = response.css("#page-content").get()
        tags = response.css(".page-tags a::text").getall()
        if not content or not tags:
            return False
        if "tale" not in tags:
            return False

        self.logger.info("Processing SCP Tale page: %s", response.url)
        content_soup = BeautifulSoup(content, "lxml")

        item = ScpTale()
        item["title"] = response.css("title::text").get()
        item["url"] = response.url
        item["tags"] = tags
        item["rating"] = get_rating(response)
        item["raw_content"] = str(clean_content_soup(content_soup))
        return item


class ScpIntSpider(ScpSpider):
    name = "scp_int"

    start_urls = [f"http://{INT_DOMAIN}/"]

    allowed_domains = [INT_DOMAIN]

    rules = (
        Rule(LinkExtractor(allow=[r"system:page-tags/tag/.*"])),
        Rule(LinkExtractor(allow=[r".*-hub"])),
        Rule(LinkExtractor(allow=[r"scp-.*"]), callback="parse_item"),
    )

    def get_series(self, item):
        if item["scp"].lower().endswith("-j") or "joke" in item["tags"]:
            return "joke"

        name_chunks = item["scp"].split("-")
        for chunk in name_chunks:
            if chunk.lower() != "scp" and not chunk.isdigit():
                return chunk

        return "other"


class ScpIntTitleSpider(ScpTitleSpider):
    name = "scp_int_titles"

    start_urls = [f"http://{INT_DOMAIN}/"]

    allowed_domains = [INT_DOMAIN]

    rules = (Rule(LinkExtractor(allow=[r".*-hub?"]), callback="parse_item"),)


class ScpIntTaleSpider(ScpTaleSpider):
    name = "scp_int_tales"

    start_urls = [
        f"http://{INT_DOMAIN}/tales-by-title",
        f"http://{INT_DOMAIN}/system:page-tags/tag/tale",
    ]

    allowed_domains = [INT_DOMAIN]


class GoiSpider(CrawlSpider):
    name = "goi"

    start_urls = [
        f"http://{DOMAIN}/goi-formats",
        f"http://{DOMAIN}/system:page-tags/tag/goi-format",
    ]

    allowed_domains = [DOMAIN]

    rules = (
        Rule(
            LinkExtractor(
                allow=[
                    re.escape("tales-by-title"),
                    re.escape("system:page-tags/tag/goi-format"),
                ]
            )
        ),
        Rule(LinkExtractor(allow=[r".*"]), callback="parse_tale"),
    )

    def parse_tale(self, response):
        self.logger.debug("Reviewing Potential SCP GOI page: %s", response.url)
        content = response.css("#page-content").get()
        tags = response.css(".page-tags a::text").getall()
        if not content or not tags:
            return False
        if "goi-format" not in tags:
            return False

        self.logger.info("Processing SCP GOI page: %s", response.url)
        content_soup = BeautifulSoup(content, "lxml")

        item = ScpGoi()
        item["title"] = response.css("title::text").get()
        item["url"] = response.url
        item["tags"] = tags
        item["rating"] = get_rating(response)
        item["raw_content"] = str(clean_content_soup(content_soup))
        return item


def get_rating(response):
    try:
        return int(response.css(".rate-points .number::text").get())
    except:
        pass
    return 0


def clean_content_soup(content_soup):
    # Remove Footer
    [x.extract() for x in content_soup.find_all("div", {"class": "footer-wikiwalk-nav"})]

    # Remove Ratings Bar
    [x.extract() for x in content_soup.find_all("div", {"class": "page-rate-widget-box"})]

    # Remove Empty Divs
    [x.extract() for x in content_soup.find_all("div") if len(x.get_text(strip=True)) == 0]

    return content_soup
