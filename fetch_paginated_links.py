"""Fetch links from paginated hub pages without full crawling.

This is much more reliable than crawling with Scrapy since we only need
the links, not the full page content.
"""
import json
import re
import time
from urllib.parse import urljoin
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup
from tqdm import tqdm


def extract_links_from_page(url, timeout=30):
    """Fetch a paginated page and extract all links from the content area."""
    try:
        with urlopen(url, timeout=timeout) as response:
            html = response.read().decode('utf-8')
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Find the main content area (same as in WikiMixin)
        content_div = soup.find('div', id='page-content')
        if not content_div:
            return []
        
        # Extract all links from the content
        links = []
        for a_tag in content_div.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip external links, anchors, and special pages
            if href.startswith('http') or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Clean the link (remove leading /)
            clean_link = href.lstrip('/')
            
            # Skip pagination links themselves
            if '/p/' in clean_link:
                continue
                
            links.append(clean_link)
        
        return links
    
    except (HTTPError, URLError) as e:
        print(f"  ✗ Failed to fetch {url}: {e}")
        return []
    except Exception as e:
        print(f"  ✗ Error processing {url}: {e}")
        return []


def fetch_paginated_links(hub_file="data/scp_hubs.json", output_file="data/paginated_links.json"):
    """Extract pagination URLs and fetch links from each page."""
    
    try:
        with open(hub_file) as f:
            hubs = json.load(f)
    except FileNotFoundError:
        print(f"❌ {hub_file} not found")
        return
    
    # Extract pagination URLs from hub raw_content
    pagination_pattern = re.compile(r'href="(/[^"]*-hub/p/\d+)"')
    base_domain = "https://scp-wiki.wikidot.com"
    
    all_pagination_urls = set()
    for hub in hubs:
        raw_content = hub.get("raw_content", "")
        if not raw_content:
            continue
        
        matches = pagination_pattern.findall(raw_content)
        for match in matches:
            full_url = urljoin(base_domain, match)
            all_pagination_urls.add(full_url)
    
    print(f"Found {len(all_pagination_urls)} paginated URLs to fetch")
    
    # Fetch links from each paginated page
    results = {}
    
    for url in tqdm(sorted(all_pagination_urls), desc="Fetching paginated links"):
        # Extract hub name and page number from URL
        match = re.search(r'/([^/]+-hub)/p/(\d+)', url)
        if not match:
            continue
        
        hub_name = match.group(1)
        page_num = int(match.group(2))
        
        # Fetch the links
        links = extract_links_from_page(url)
        
        if links:
            if hub_name not in results:
                results[hub_name] = {}
            
            results[hub_name][page_num] = {
                "url": url,
                "links": links,
                "link_count": len(links)
            }
            print(f"  ✓ {hub_name}/p/{page_num}: {len(links)} links")
        
        # Be nice to the server
        time.sleep(0.5)
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, sort_keys=True)
    
    print(f"\n✅ Saved paginated links to {output_file}")
    print(f"   Total hubs with pagination: {len(results)}")
    total_pages = sum(len(pages) for pages in results.values())
    print(f"   Total pages fetched: {total_pages}")


if __name__ == "__main__":
    fetch_paginated_links()
