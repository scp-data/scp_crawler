# scp_crawler

This is a web crawler built with scrapy and designed to extract data from the SCP Wiki.

## Installation

```
make install
```

## Simple Crawl

Then to run all of the spiders and create a full data dump of the SCP Wiki and SCP International Hub in the `data` directory:

```bash
make crawl
```

## Custom Crawl with scrapy cli

Individual spiders with custom settings can also be called using the `scrapy` command line tool.

To show Available Spiders:

```bash
scrapy list
```

To crawl the International Hub for SCP Items and save to a custom location:

```bash
scrapy crawl scp_int -o scp_international_items.json
```

To crawl pages tagged as `supplement` and save to a custom location:

```bash
scrapy crawl scp_supplement -o scp_supplement.json
```

## Raw Content Structure

There are multiple types of content downloaded (Items, Tales, GOI formats, and Supplements).

All content (both SCP Items and Tales) contain the following:

* URL
* Title
* Rating
* Tags
* History- revision ID, date, author, and comment.
* Raw Content (the HTML for the story or item, without the site navigation and other boilerplate)

In addition the SCP Items include:

* SCP Identifier (ie, SCP-3000)
* SCP Number (if available)
* SCP Series
  * 1-5 (with built in support for future published series)
  * joke, explained, and decommissioned
  * Generic International (from the main site)
  * Specific Nationality Tag (from the international hub)

### Generated Files

The crawler generates a series of json files containing an array of objects representing each crawled item.

| File                | Source        | Type  | Target  |
| ------------------- | ------------- | ----- | ------- |
| goi.json            | Main          | Tale  | goi     |
| scp_items.json      | Main          | Item  | scp     |
| scp_titles.json     | Main          | Title | scp     |
| scp_hubs.json       | Main          | Hub   | scp     |
| scp_tales.json      | Main          | Tale  | scp     |
| scp_supplement.json | Main          | Supplement | scp |
| scp_int.json        | International | Item  | scp_int |
| scp_int_titles.json | International | Title | scp_int |
| scp_int_tales.json  | International | Tale  | scp_int |

Running `make TARGET` (such as `make goi` or `make scp`) will generate the site specific files. Running `make data` will fill in any missing files.

To regenerate all files run `make fresh`.

## Post Processed Data

The postproc system takes Titles, Hubs, Items, Tales, GOI, and Supplements and uses them to generate a comprehensive set of objects. It combines and cross references data and expands on the data already there.

### Hub Pagination

Many hub pages have paginated sections that load additional content. The crawler automatically handles this by:

1. Extracting pagination URLs from hub content (e.g., `/chaos-insurgency-hub/p/2`)
2. Fetching links from all paginated pages via HTTP
3. Merging these links into the hub's `references` array during postprocessing

This ensures that all links from paginated pages are included in the hub data without needing to crawl full pages. See [PAGINATION.md](PAGINATION.md) for detailed documentation.

**Generated pagination data:**
- `data/paginated_links.json` - Intermediate file containing links from all paginated hub pages
- `data/processed/hubs/index.json` - Final hub data with merged pagination links in `references`

### Output Structure

Supplements are written to `data/processed/supplement/` and include additional fields like `parent_scp` and `parent_tale`.

Hubs are written to `data/processed/hubs/` and include enriched `references` arrays with links from both the main hub page and any paginated sections.


## Content Licensing

Text content on the SCP Wikis is available under the CC BY-SA 3.0 license.

This project does not download images.
