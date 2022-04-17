# scp_crawler

This is a web crawler built with scrapy and designed to extract data from the SCP Wiki.

## Installation

```
python3 -m venv env
source ./env/bin/activate
pip install -r requirements.txt
```

## Simple Crawl

Then to run all of the spiders and create a full data dump of the SCP Wiki and SCP International Hub in the `data` directory:
```
python crawler.py
```

## Custom Crawl with scrapy cli

Individual spiders with custom settings can also be called using the `scrapy` command line tool.

To show Available Spiders:
```
scrapy list
```

To crawl the International Hub for SCP Items and save as json:
```
scrapy crawl scpint -o scp_international_items.json
```

## Content Structure

There are two types of content downloaded- SCP Items and SCP Tales.

All content (both SCP Items and Tales) contain the following:

* URL
* Title
* Rating
* Tags
* Raw Content (the HTML for the story or item, without the site navigation and other boilerplate)

In addition the SCP Items include:

* SCP Identifier (ie, SCP-3000)
* SCP Number (if available)
* SCP Series
  * 1-5 (with built in support for future published series)
  * joke, explained, and decommissioned
  * Generic International (from the main site)
  * Specific Nationality Tag (from the international hub)


## Generated Files

The crawler generates a series of json files containing an array of objects representing each crawled item.

| File         | Source        | Type |
|--------------|---------------|------|
| goi.json     | Main          | Tale |
| scp.json     | Main          | Item |
| scpint.json  | International | Item |
| tale.json    | Main          | Tale |
| taleint.json | International | Tale |


## Content Licensing

Text content on the SCP Wikis is available under the CC BY-SA 3.0 license.

This project does not download images.
