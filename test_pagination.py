#!/usr/bin/env python3
"""
Quick test script to verify hub pagination crawling.
Tests against the church-of-the-broken-god-hub which is known to have paginated pages.
"""

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scp_crawler.spiders.scp import ScpHubSpider


class TestHubSpider(ScpHubSpider):
    """Test spider that only crawls one specific hub and its paginated pages."""
    name = "test_hub_pagination"
    
    # Start with a known hub that has pagination
    start_urls = ["https://scp-wiki.wikidot.com/church-of-the-broken-god-hub"]
    
    # Override rules to be more restrictive for testing
    rules = (
        Rule(
            # Only follow pagination for this specific hub
            LinkExtractor(allow=[r"church-of-the-broken-god-hub/p/\d+"]),
            callback="parse_paginated_hub",
            follow=False,
        ),
        Rule(
            # Only parse the main hub page
            LinkExtractor(allow=[r"church-of-the-broken-god-hub$"]),
            callback="parse_hub",
            follow=False,
        ),
    )


if __name__ == "__main__":
    # Configure process
    process = CrawlerProcess({
        'USER_AGENT': 'SCP-Crawler-Test/1.0',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
        'ITEM_PIPELINES': {
            'scp_crawler.pipelines.HubPaginationPipeline': 300,
        },
        'FEEDS': {
            'test_hub_pagination.json': {
                'format': 'json',
                'overwrite': True,
            }
        },
        'LOG_LEVEL': 'INFO',
    })
    
    process.crawl(TestHubSpider)
    process.start()
    
    print("\n" + "="*60)
    print("Test complete! Check test_hub_pagination.json for results")
    print("="*60)
