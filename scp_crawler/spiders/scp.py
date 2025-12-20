import json
import re
import sys
from pprint import pprint

import requests
import scrapy
from bs4 import BeautifulSoup
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import ScpGoi, ScpHub, ScpItem, ScpSupplement, ScpTale, ScpTitle

DOMAIN = "scp-wiki.wikidot.com"
INT_DOMAIN = "scp-int.wikidot.com"
MAX_HISTORY_PAGES = 5
MAIN_TOKEN = "123456"


class WikiMixin:

    skip_pages = [
        "",
        "/licensing-guide",
        "/licensing-master-list",
    ]

    def parse_history(self, response, item, history_page=1):
        self.logger.info(f"Reviewing Page {item['page_id']} history")

        page_id = item["page_id"]
        changes = item.get("history", {})
        item["history"] = changes  # Ensure history key always exists

        try:
            response_text = getattr(response, "text", "") or ""
            if not response_text.strip():
                self.logger.error(
                    "Empty response when fetching history for %s (status=%s, page=%s)",
                    item.get("url"),
                    getattr(response, "status", None),
                    history_page,
                )
                return self.get_page_source_request(page_id, item)

            history = response.json()
            if not isinstance(history, dict) or "body" not in history:
                self.logger.error(
                    "Missing 'body' in history lookup for %s (status=%s, page=%s). Keys=%s",
                    item.get("url"),
                    getattr(response, "status", None),
                    history_page,
                    list(history.keys()) if isinstance(history, dict) else type(history),
                )
                return self.get_page_source_request(page_id, item)

            body = history.get("body")
            if not body:
                self.logger.error(
                    "Empty 'body' in history lookup for %s (status=%s, page=%s)",
                    item.get("url"),
                    getattr(response, "status", None),
                    history_page,
                )
                return self.get_page_source_request(page_id, item)

            soup = BeautifulSoup(body, "lxml")
            if soup.table is None:
                self.logger.error(
                    "Missing <table> in history HTML for %s (status=%s, page=%s)",
                    item.get("url"),
                    getattr(response, "status", None),
                    history_page,
                )
                return self.get_page_source_request(page_id, item)
            rows = soup.table.find_all("tr")

        except (json.JSONDecodeError, ValueError):
            self.logger.error(
                "JSON decode error in history lookup for %s (status=%s, page=%s)",
                item.get("url"),
                getattr(response, "status", None),
                history_page,
            )
            return self.get_page_source_request(page_id, item)
        except Exception:
            self.logger.exception(
                "Unable to parse history lookup for %s (status=%s, page=%s)",
                item.get("url"),
                getattr(response, "status", None),
                history_page,
            )
            return self.get_page_source_request(page_id, item)
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

        # Update item history after processing all rows
        item["history"] = changes
        
        # The "0" change is the first revision, and the last one that shows up.
        # If we have it then we're done.
        if "0" in changes:
            return self.get_page_source_request(page_id, item)

        next_page = history_page + 1
        if next_page > MAX_HISTORY_PAGES:
            self.logger.warning(f"Failed to retrieve complete history for {item['url']}")
            return self.get_page_source_request(page_id, item)

        return self.get_history_request(page_id, history_page + 1, item)

    def get_history_request(self, page_id, history_page, item):
        # return self.get_page_source_request(page_id=page_id, item=item)

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

    def get_page_source_request(self, page_id, item):
        # Getting source in preprocessing phase
        return item
        return scrapy.http.FormRequest(
            url=f"https://{self.domain}/ajax-module-connector.php",
            method="POST",
            formdata={
                "wikidot_token7": MAIN_TOKEN,
                "page_id": str(page_id),
                "moduleName": "viewsource/ViewSourceModule",
            },
            cookies={"wikidot_token7": MAIN_TOKEN},
            callback=self.parse_source,
            errback=self.err_callback_page_source,
            cb_kwargs={
                "item": item,
            },
        )

    def err_callback_page_source(self, failure):
        self.logger.error(failure)
        if "item" in failure.request.cb_kwargs:
            return failure.request.cb_kwargs["item"]

    def parse_source(self, response, item):
        self.logger.info(f"Reviewing Page {item['page_id']} wiki source")
        page_response = response.json()
        soup = BeautifulSoup(page_response["body"], "lxml")
        item["raw_source"] = "".join(str(x) for x in soup.find("div", {"class": "page-source"}).contents).replace(
            "<br/>", ""
        )
        return item

    def get_page_id(self, response):
        return re.search(r"WIKIREQUEST\.info\.pageId\s+=\s+(\d+);", response.text)[1]

    def get_tags(self, response):
        return response.css(".page-tags a::text").getall()

    def get_content(self, response):
        return response.css("#page-content").get()

    def get_title(self, response):
        title = response.css("title::text").get()
        # @TODO - expand to include international wikis
        if title.endswith(" - SCP Foundation"):
            title = title.replace(" - SCP Foundation", "")
        return title

    def get_simple_link(self, url):
        return url.replace(f"http://{self.domain}/", "").replace(f"https://{self.domain}/", "")

    def get_content_references(self, response):
        current_link = self.get_simple_link(response.url)
        extractor = LinkExtractor(allow_domains=self.allowed_domains, restrict_css="#page-content")
        references = []
        for x in extractor.extract_links(response):
            link = self.get_simple_link(x.url)
            if link in self.skip_pages or link == current_link:
                continue
            references.append(link)
        return references

    def follow_splash_redirects(self, response, tags, callback):
        if not "splash" in tags:
            return False

        if "adult" in tags:
            # Test Case - https://scp-wiki.wikidot.com/scp-597
            redirect_path = response.css("#u-adult-warning a").attrib["href"]
            return scrapy.http.Request(
                url=f"https://{self.domain}{redirect_path}",
                callback=callback,
                cb_kwargs={"original_link": self.get_simple_link(response.url)},
            )

        return False


class ScpSpider(CrawlSpider, WikiMixin):
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

    def parse_item(self, response, original_link=None):
        self.logger.debug("Reviewing Potential SCP Item page: %s", response.url)
        content = self.get_content(response)
        tags = self.get_tags(response)

        if not content or not tags:
            return False

        redirect = self.follow_splash_redirects(response, tags, self.parse_item)
        if redirect:
            return redirect

        if not self.validate(tags):
            return False

        self.logger.info("Processing SCP Item page: %s", response.url)
        content_soup = BeautifulSoup(content, "lxml")

        item = ScpItem()
        item["title"] = self.get_title(response)
        item["url"] = response.url
        item["domain"] = self.domain
        item["link"] = original_link if original_link else self.get_simple_link(response.url)
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
        item["references"] = self.get_content_references(response)

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
        for x in range(1, 20):
            if number < x * 1000:
                return f"series-{x}"

        return "other"


class ScpTitleSpider(CrawlSpider):
    name = "scp_titles"

    start_urls = [f"http://{DOMAIN}/"]

    allowed_domains = [DOMAIN]

    domain = DOMAIN

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


class ScpTaleSpider(CrawlSpider, WikiMixin):
    name = "scp_tales"

    start_urls = [
        f"http://{DOMAIN}/tales-by-title",
        f"http://{DOMAIN}/system:page-tags/tag/tale",
    ]

    allowed_domains = [DOMAIN]

    domain = DOMAIN

    rules = (
        Rule(LinkExtractor(allow=[re.escape("tales-by-title"), re.escape("system:page-tags/tag/tale")])),
        Rule(LinkExtractor(allow=[r".*"]), callback="parse_tale"),
    )

    def parse_tale(self, response, original_link=None):
        self.logger.debug("Reviewing Potential SCP Tale page: %s", response.url)
        content = response.css("#page-content").get()
        tags = response.css(".page-tags a::text").getall()
        if not content or not tags:
            return False

        redirect = self.follow_splash_redirects(response, tags, self.parse_tale)
        if redirect:
            return redirect

        if "tale" not in tags:
            return False

        self.logger.info("Processing SCP Tale page: %s", response.url)
        content_soup = BeautifulSoup(content, "lxml")

        item = ScpTale()
        item["title"] = response.css("title::text").get()
        item["url"] = response.url
        item["domain"] = self.domain
        item["link"] = original_link if original_link else self.get_simple_link(response.url)
        item["tags"] = tags
        item["page_id"] = self.get_page_id(response)
        item["rating"] = get_rating(response)
        item["raw_content"] = str(clean_content_soup(content_soup))
        item["references"] = self.get_content_references(response)
        return self.get_history_request(item["page_id"], 1, item)


class ScpHubSpider(CrawlSpider, WikiMixin):
    name = "scp_hubs"

    start_urls = [f"https://{DOMAIN}/system:page-tags/tag/hub"]

    allowed_domains = [DOMAIN]

    domain = DOMAIN

    rules = (
        Rule(
            # Crawl everything except tag pages, which slam the system and give 503s.
            LinkExtractor(allow=[r".*"], deny=[r"system:page-tags.*", re.escape("tag-search")]),
            callback="parse_hub",
        ),
    )

    excluded_hubs = [
        "/new-pages-feed",
        "/shortest-pages-this-month",
        "/top-rated-pages-this-month",
        "/user-curated-lists",
        "/curated-tale-series",
        "/foundation-tales",
        "/groups-of-interest",
        "/canon-hub",
        "/young-and-under-30",
        "/tales-by-title",
        "/tales-by-author",
    ]

    def parse_hub(self, response):
        tags = self.get_tags(response)
        if not "hub" in tags:
            return False
        link = self.get_simple_link(response.url)
        if link in self.excluded_hubs:
            self.logger.debug(f"Skipping hub at {link}")
            return False
        if link.startswith("/scp-series"):
            return False

        self.logger.info("Reviewing Potential SCP Hub page: %s", response.url)

        content = self.get_content(response)
        if not content:
            return False

        item = ScpHub()
        item["title"] = self.get_title(response)
        item["url"] = response.url
        item["domain"] = self.domain
        item["link"] = link
        item["tags"] = tags
        item["page_id"] = self.get_page_id(response)
        item["references"] = self.get_content_references(response)
        item["raw_content"] = content

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

    domain = INT_DOMAIN


class GoiSpider(CrawlSpider, WikiMixin):
    name = "goi"

    start_urls = [
        f"http://{DOMAIN}/goi-formats",
        f"http://{DOMAIN}/system:page-tags/tag/goi-format",
    ]

    allowed_domains = [DOMAIN]

    domain = DOMAIN

    rules = (
        Rule(LinkExtractor(allow=[re.escape("tales-by-title"), re.escape("system:page-tags/tag/goi-format")])),
        Rule(LinkExtractor(allow=[r".*"]), callback="parse_tale"),
    )

    def parse_tale(self, response, original_link=None):
        self.logger.debug("Reviewing Potential SCP GOI page: %s", response.url)
        content = response.css("#page-content").get()
        tags = response.css(".page-tags a::text").getall()
        if not content or not tags:
            return False
        redirect = self.follow_splash_redirects(response, tags, self.parse_tale)
        if redirect:
            return redirect
        if "goi-format" not in tags:
            return False

        self.logger.info("Processing SCP GOI page: %s", response.url)
        content_soup = BeautifulSoup(content, "lxml")

        item = ScpGoi()
        item["title"] = response.css("title::text").get()
        item["url"] = response.url
        item["domain"] = self.domain
        item["link"] = original_link if original_link else self.get_simple_link(response.url)
        item["tags"] = tags
        item["page_id"] = self.get_page_id(response)
        item["rating"] = get_rating(response)
        item["raw_content"] = str(clean_content_soup(content_soup))
        return self.get_history_request(item["page_id"], 1, item)


class ScpSupplementSpider(CrawlSpider, WikiMixin):
    name = "scp_supplement"

    start_urls = [
        f"http://{DOMAIN}/system:page-tags/tag/supplement",
    ]

    allowed_domains = [DOMAIN]

    domain = DOMAIN

    rules = (
        Rule(LinkExtractor(allow=[re.escape("system:page-tags/tag/supplement")])),
        Rule(LinkExtractor(allow=[r".*"]), callback="parse_supplement"),
    )

    def parse_supplement(self, response, original_link=None):
        self.logger.debug("Reviewing Potential SCP Supplement page: %s", response.url)
        content = self.get_content(response)
        tags = self.get_tags(response)
        
        if not content or not tags:
            return None

        redirect = self.follow_splash_redirects(response, tags, self.parse_supplement)
        if redirect:
            return redirect

        if "supplement" not in tags:
            return None

        self.logger.info("Processing SCP Supplement page: %s", response.url)
        content_soup = BeautifulSoup(content, "lxml")

        item = ScpSupplement()
        item["title"] = self.get_title(response)
        item["url"] = response.url
        item["domain"] = self.domain
        item["link"] = original_link if original_link else self.get_simple_link(response.url)
        item["tags"] = tags
        item["page_id"] = self.get_page_id(response)
        item["rating"] = get_rating(response)
        item["raw_content"] = str(clean_content_soup(content_soup))
        item["references"] = self.get_content_references(response)
