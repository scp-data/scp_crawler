# Hub Pagination Support

## Overview

Some hub pages on the SCP Wiki have paginated versions that load additional content. These pages have URLs in the format `/hub-name/p/1`, `/hub-name/p/2`, etc.

Examples:
- https://scp-wiki.wikidot.com/church-of-the-broken-god-hub/p/2
- https://scp-wiki.wikidot.com/chaos-insurgency-hub/p/5

The paginated pages typically only contain lists of links to additional SCP items, tales, or other content that didn't fit on the main hub page.

## Implementation

### 1. Approach

Since paginated pages only contain **lists of links** (not full content), we use a lightweight approach:

1. **Main Hub Crawl**: The `ScpHubSpider` crawls only the main hub pages
2. **Link Extraction**: `fetch_paginated_links.py` extracts pagination URLs from hub content and fetches the links from each paginated page using simple HTTP requests
3. **Link Integration**: During postprocessing, the extracted links are merged into the hub's `references` array

This is much more reliable and efficient than trying to crawl paginated pages with Scrapy, as it avoids rate limiting issues.

### 2. Link Extraction Script

The `fetch_paginated_links.py` script:

```python
def extract_links_from_page(url, timeout=30):
    """Fetch a paginated page and extract all links from the content area."""
    with urlopen(url, timeout=timeout) as response:
        html = response.read().decode('utf-8')
    
    soup = BeautifulSoup(html, 'lxml')
    content_div = soup.find('div', id='page-content')
    
    links = []
    for a_tag in content_div.find_all('a', href=True):
        href = a_tag['href']
        if not (href.startswith('http') or href.startswith('#') or '/p/' in href):
            links.append(href.lstrip('/'))
    
    return links
```

The script:
- Scans all hub `raw_content` for pagination links (pattern: `/hub-name/p/digit`)
- Fetches each paginated URL via HTTP
- Extracts all content links from the page
- Saves results to `data/paginated_links.json`

### 3. Data Structure

The `paginated_links.json` file has this format:

```json
{
  "chaos-insurgency-hub": {
    "1": {
      "url": "https://scp-wiki.wikidot.com/chaos-insurgency-hub/p/1",
      "links": ["scp-xxxx", "tale-yyyy", ...],
      "link_count": 50
    },
    "2": {
      "url": "https://scp-wiki.wikidot.com/chaos-insurgency-hub/p/2",
      "links": [...],
      "link_count": 48
    }
  }
}
```

### 4. Postprocessing

The postprocessing script (`scp_crawler/postprocessing.py`):

1. Loads `data/paginated_links.json` if available
2. For each hub with paginated links:
   - Collects all links from all paginated pages
   - Merges them into the hub's existing `references` array
   - Removes duplicates
3. Outputs the enriched hubs to `data/processed/hubs/index.json`

```python
if link in paginated_links_data:
    all_paginated_links = []
    for page_num, page_data in paginated_links_data[link].items():
        all_paginated_links.extend(page_data.get("links", []))
    
    existing_refs = set(hub.get("references", []))
    new_refs = existing_refs.union(set(all_paginated_links))
    hub["references"] = list(new_refs)
```

### 5. Makefile Integration

The makefile automatically handles pagination:

```makefile
data/scp_hubs.json: .venv
	@echo "==> Crawling main hubs..."
	@rm -f data/scp_hubs.json data/paginated_links.json
	@$(PYTHON_VENV) python -m scrapy crawl scp_hubs -o data/scp_hubs.json
	@echo "==> Fetching links from paginated pages..."
	@$(PYTHON_VENV) python fetch_paginated_links.py
```

## Usage

### Full Pipeline

```bash
make data/scp_hubs.json      # Crawl main hubs + fetch paginated links
make data/processed/hubs     # Merge paginated links into references
```

### Manual Steps

```bash
# 1. Crawl main hubs
scrapy crawl scp_hubs -o data/scp_hubs.json

# 2. Extract paginated links
source .venv/bin/activate
python fetch_paginated_links.py

# 3. Process and merge
make data/processed/hubs
```

## Benefits

✅ **Reliable**: Simple HTTP requests avoid Scrapy rate limiting  
✅ **Efficient**: Only fetches what's needed (links, not full pages)  
✅ **Complete**: All paginated URLs are successfully fetched  
✅ **Clean**: No duplicate content, all links merged into `references`

## Example Result

A hub with pagination will have an enriched `references` array:

```json
{
  "chaos-insurgency-hub": {
    "title": "Chaos Insurgency Hub",
    "references": [
      "scp-001",
      "scp-002",
      "tale-insurgency-rising",
      // ... links from main page
      "scp-9999",
      "scp-10000",
      // ... links from paginated pages
    ]
  }
}
```
