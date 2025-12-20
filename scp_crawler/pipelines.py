# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from scrapy.exceptions import DropItem
from scp_crawler.items import ScpHub


class ScpCrawlerPipeline(object):
    def process_item(self, item, spider):
        return item


class HubPaginationPipeline(object):
    """Pipeline to merge paginated hub pages into the main hub item.
    
    This pipeline collects paginated content and attaches it to hub items.
    Since paginated pages may be crawled before or after the main hub page,
    we attach pagination data immediately when available.
    """
    
    def __init__(self):
        self.paginated_data = {}  # Store paginated data by base_link
        self.processed_hubs = set()  # Track which hubs we've seen
    
    def open_spider(self, spider):
        """Initialize for each spider run."""
        self.paginated_data.clear()
        self.processed_hubs.clear()
    
    def process_item(self, item, spider):
        # Only process for hub spiders
        if spider.name not in ["scp_hubs", "scp_int_hubs"]:
            return item
            
        # Handle dict returned from parse_paginated_hub
        if isinstance(item, dict) and "base_link" in item:
            base_link = item["base_link"]
            page_number = item["page_number"]
            
            if base_link not in self.paginated_data:
                self.paginated_data[base_link] = []
            
            self.paginated_data[base_link].append({
                "page": page_number,
                "url": item["url"],
                "content": item["content"]
            })
            
            spider.logger.info(
                f"Stored paginated content for {base_link}, page {page_number}"
            )
            
            # Drop paginated items - don't yield them separately
            raise DropItem(f"Paginated content collected for {base_link}")
        
        # Handle ScpHub items - attach any paginated content we've collected
        if isinstance(item, ScpHub):
            link = item.get("link")
            if link:
                self.processed_hubs.add(link)
                if link in self.paginated_data:
                    # Sort by page number and attach to hub
                    paginated_list = self.paginated_data[link]
                    paginated_list.sort(key=lambda x: x["page"])
                    item["paginated_content"] = paginated_list
                    spider.logger.info(
                        f"✓ Merged {len(paginated_list)} paginated pages into hub {link}"
                    )
            return item
        
        return item
