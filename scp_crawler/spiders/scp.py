import re
import sys
from pprint import pprint

import requests
import scrapy
from bs4 import BeautifulSoup
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import ScpGoi, ScpItem, ScpTale, ScpTitle

DOMAIN = "scp-wiki.wikidot.com"
INT_DOMAIN = "scp-int.wikidot.com"
MAX_HISTORY_PAGES = 5
MAIN_TOKEN = "123456"


class HistoryMixin:
    def parse_history(self, response, item, history_page=1):
        self.logger.info(f"Reviewing Page {item['page_id']} history")

        page_id = item["page_id"]
        changes = item["history"] if "history" in item else {}
        try:
            history = response.json()
            soup = BeautifulSoup(history["body"], "lxml")
            rows = soup.table.find_all("tr")
        except:
            self.logger.exception(f"Unable to parse history lookup. {item['url']}")
            return item
        for row in rows:
            try:
                if not "id" in row.attrs:
                    continue
                columns = row.find_all("td")
                change_id = columns[0].text.replace(".", "").strip()

                if "deleted" in row.text:
                    change_author = "deleted"
                    change_author_href = False
                else:
                    change_author = columns[4].text.strip()
                    change_author_href = columns[4].span.a["href"].strip()

                change_date = columns[5].text.strip()
                change_comment = columns[6].text
                changes[change_id] = {
                    "author": change_author,
                    "author_href": change_author_href,
                    "date": change_date,
                    "comment": change_comment,
                }
            except:
                self.logger.exception("Could not process row.")
                self.logger.error(row)

            item["history"] = changes
            # The "0" change is the first revision, and the last one that shows up.
            # If we have it then we're done.
            if "0" in changes:
                return item

        next_page = history_page + 1
        if next_page > MAX_HISTORY_PAGES:
            self.logger.warning(f"Failed to retrieve complete history for {item['url']}")
            return item

        return self.get_history_request(page_id, history_page + 1, item)

    def get_history_request(self, page_id, history_page, item):
        return scrapy.http.FormRequest(
            url=f"https://{self.domain}/ajax-module-connector.php",
            method="POST",
            formdata={
                "wikidot_token7": MAIN_TOKEN,
                "page_id": str(page_id),
                "moduleName": "history/PageRevisionListModule",
                "page": str(history_page),
                "perpage": str(99999),
            },
            cookies={"wikidot_token7": MAIN_TOKEN},
            callback=self.parse_history,
            cb_kwargs={
                "item": item,
                "history_page": history_page,
            },
        )

    def get_page_id(self, response):
        return re.search(r"WIKIREQUEST\.info\.pageId\s+=\s+(\d+);", response.text)[1]


class ScpSpider(CrawlSpider, HistoryMixin):
    name = "scp"

    allowed_domains = [DOMAIN]

    domain = DOMAIN

    start_urls = [
        f"http://{DOMAIN}/",
        f"http://{DOMAIN}/system:page-tags/tag/scp",
    ]

    rules = (
        Rule(LinkExtractor(allow=[r"scp-series(?:-\d*)?", "scp-ex"])),
        Rule(LinkExtractor(allow=[r"scp-\d{3,}(?:-[\w|\d]+)*"]), callback="parse_item"),
        Rule(LinkExtractor(allow=[r".*-proposal.*"]), callback="parse_item"),
    )

    # rules = (Rule(LinkExtractor(allow=[r"scp-\d{3,}(?:-[\w|\d]+)*"]), callback="parse_item"),)
    # start_urls = [f"https://scp-wiki.wikidot.com/scp-3318"]

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
        item["link"] = response.url.replace(f"http://{self.domain}", "").replace(f"https://{self.domain}", "")
        item["tags"] = tags
        item["page_id"] = self.get_page_id(response)
        item["scp"] = self.get_scp_identifier(item).upper()
        item["scp_number"] = self.get_scp_number(item)
        item["series"] = self.get_series(item)

        if item["scp_number"] == 2721:
            # Editorial choice- this SCP was locked due to trolls
            item["rating"] = 200
        else:
            item["rating"] = get_rating(response)

        item["raw_content"] = str(clean_content_soup(content_soup))

        return self.get_history_request(item["page_id"], 1, item)

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

    rules = (Rule(LinkExtractor(allow=[r"scp-series(?:-\d*)?", "scp-ex"]), callback="parse_titles"),)

    def parse_titles(self, response):
        self.logger.info("Reviewing SCP Index page: %s", response.url)
        listings = response.css(".content-panel > ul > li")
        for listing in listings:
            try:
                self.logger.info(f"Processing Line: {listing.get()}")
                scp = listing.xpath("a/text()").get()
                link = listing.xpath("a/@href").get()
                if scp == "taboo":
                    scp = "SCP-4000"
                    title = "Taboo"
                if scp.lower().startswith("SCP-5309"):
                    scp = "SCP-5309"
                    title = "SCP-5309 is not to exist."
                elif not scp.lower().startswith("scp-"):
                    title = scp
                    scp = link.strip("/").upper()
                else:
                    listing_text = BeautifulSoup(listing.get()).get_text()
                    results = re.findall(r".* - (.*)", listing_text)
                    if len(results) > 0:
                        title = results[0]
                    else:
                        self.logger.warn(f"Assigning default to {scp} with '{listing_text}'")
                        title = scp

                item = ScpTitle()
                item["scp"] = scp
                item["title"] = title
                item["link"] = link
                yield item
            except:
                self.logger.exception("Failed to process line.")
                self.logger.error(listing)


class ScpTaleSpider(CrawlSpider, HistoryMixin):
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
        item["page_id"] = self.get_page_id(response)
        item["rating"] = get_rating(response)
        item["raw_content"] = str(clean_content_soup(content_soup))
        return self.get_history_request(item["page_id"], 1, item)


class ScpIntSpider(ScpSpider):
    name = "scp_int"

    start_urls = [f"http://{INT_DOMAIN}/"]

    allowed_domains = [INT_DOMAIN]

    domain = INT_DOMAIN

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

    rules = (Rule(LinkExtractor(allow=[r".*-hub?"]), callback="parse_titles"),)


class ScpIntTaleSpider(ScpTaleSpider):
    name = "scp_int_tales"

    start_urls = [
        f"http://{INT_DOMAIN}/tales-by-title",
        f"http://{INT_DOMAIN}/system:page-tags/tag/tale",
    ]

    allowed_domains = [INT_DOMAIN]


class GoiSpider(CrawlSpider, HistoryMixin):
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
        item["page_id"] = self.get_page_id(response)
        item["rating"] = get_rating(response)
        item["raw_content"] = str(clean_content_soup(content_soup))
        return self.get_history_request(item["page_id"], 1, item)


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
