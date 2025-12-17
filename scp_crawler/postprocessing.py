import html
import json
import os
import re
import time
from datetime import date, datetime
from pathlib import Path

import httpx
import typer
from bs4 import BeautifulSoup
from tqdm import tqdm

cwd = os.getcwd()

MAIN_TOKEN = "123456"

cli = typer.Typer()


def json_serial(obj):
    # Convert datetimes to strings in ISO format.
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    # Convert anything else to a string.
    return str(obj)


def from_file(path):
    with open(path, "r") as fs:
        data = json.load(fs)
    return data


def to_file(obj, path):
    with open(path, "w") as fs:
        print(f"Saving data to {path}")
        json.dump(obj, fs, sort_keys=True, default=json_serial)


def get_images(html):
    content_soup = BeautifulSoup(html, "lxml")
    img_tags = content_soup.find_all("img")
    return [img["src"] for img in img_tags if not img["src"].startswith("https://www.wikidot.com/avatar.php")]


def process_history(history):
    if not history:
        return []

    if isinstance(history, dict):
        revisions = list(history.values())
    elif isinstance(history, list):
        revisions = history
    else:
        return []

    for revision in revisions:
        if not isinstance(revision, dict):
            continue
        revision_date = revision.get("date")
        if isinstance(revision_date, str):
            try:
                revision["date"] = datetime.strptime(revision_date, "%d %b %Y %H:%M")
            except Exception:
                # Keep original value if parsing fails.
                pass

    revisions.sort(key=lambda x: x.get("date") or datetime.min)
    return revisions


def get_wiki_source(page_id, domain, attempts=5):

    try:
        response = httpx.post(
            f"https://{domain}/ajax-module-connector.php",
            data={
                "wikidot_token7": MAIN_TOKEN,
                "page_id": str(page_id),
                "moduleName": "viewsource/ViewSourceModule",
            },
            cookies={"wikidot_token7": MAIN_TOKEN},
        )
        response.raise_for_status()
    except:
        print(f"Failed to load source for {page_id}")
        attempts -= 1
        if attempts > 0:
            print(f"Sleeping before retry- {attempts} attempts remaining.")
            time.sleep(1)
            return get_wiki_source(page_id, domain, attempts=attempts)
        return False

    try:
        page_response = response.json()
        soup = BeautifulSoup(page_response["body"], "lxml")
        raw_source = "".join(str(x) for x in soup.find("div", {"class": "page-source"}).contents)
        return re.sub("<br\s*?/?\s*?>", "\n", html.unescape(raw_source), flags=re.IGNORECASE)
    except:
        print(f"Unable to pull body for wikisource from {page_id}")
        return None



print("Processing Hub list.")

hub_list = from_file(cwd + "/data/scp_hubs.json")
hub_items = {}
hub_references = {}
for hub in tqdm(
    hub_list,
):
    # Convert history dict to list and sort by date.
    hub["history"] = process_history(hub.get("history"))

    if len(hub["history"]) > 0:
        hub["created_at"] = hub["history"][0]["date"]
        hub["creator"] = hub["history"][0]["author"]
    else:
        hub["created_at"] = "unknown"
        hub["creator"] = "unknown"

    hub_items[hub["link"]] = hub
    hub_references[hub["link"]] = set(hub["references"])

hub_dir = Path(cwd + "/data/processed/hubs")
os.makedirs(hub_dir, exist_ok=True)
to_file(hub_items, hub_dir / "index.json")


def get_hubs(link):
    in_hubs = []
    for hub_name, hub_links in hub_references.items():
        if link in hub_links:
            in_hubs.append(hub_name)
    return in_hubs


@cli.command()
def run_postproc_items():
    processed_path = Path(cwd + "/data/processed/items")
    os.makedirs(processed_path, exist_ok=True)

    title_list = from_file(cwd + "/data/scp_titles.json")
    title_index = {title["link"]: title["title"] for title in title_list}

    print("Processing Item list.")

    item_list = from_file(cwd + "/data/scp_items.json")
    items = {}
    series_items = {}
    for item in tqdm(item_list, smoothing=0):
        if item["link"] in title_index:
            item["title"] = title_index[item["link"]]
        else:
            item["title"] = item["scp"]

        item["raw_source"] = get_wiki_source(item["page_id"], item["domain"])
        item["images"] = get_images(item["raw_content"])
        item["hubs"] = get_hubs(item["link"])

        # Convert history dict to list and sort by date.
        item["history"] = process_history(item.get("history"))

        if len(item["history"]) > 0:
            item["created_at"] = item["history"][0]["date"]
            item["creator"] = item["history"][0]["author"]

        items[item["scp"]] = item

        if item["series"].startswith("series-") and item["scp_number"] >= 5000:
            if item["scp_number"] % 1000 > 500:
                label = item["series"] + ".5"
            else:
                label = item["series"] + ".0"
        else:
            label = item["series"]

        if label not in series_items:
            series_items[label] = {}
        series_items[label][item["scp"]] = item

    item_files = {}
    series_index = {}
    for series, series_items in series_items.items():
        filename = f"content_{series}.json"
        series_index[series] = filename
        to_file(series_items, processed_path / filename)
        for item_key, item_value in series_items.items():
            item_files[item_value["link"]] = filename

    to_file(series_index, processed_path / "content_index.json")

    for item_id in items:
        del items[item_id]["raw_content"]
        del items[item_id]["raw_source"]
        items[item_id]["content_file"] = item_files[items[item_id]["link"]]

    to_file(items, processed_path / "index.json")


@cli.command()
def run_postproc_tales():

    processed_path = Path(cwd + "/data/processed/tales")
    os.makedirs(processed_path, exist_ok=True)

    print("Processing Tale list.")

    tale_list = from_file(cwd + "/data/scp_tales.json")
    tales = {}
    tale_years = {}
    for tale in tqdm(tale_list, smoothing=0):

        tale["images"] = get_images(tale["raw_content"])
        tale["hubs"] = get_hubs(tale["link"])
        tale["raw_source"] = get_wiki_source(tale["page_id"], tale["domain"])

        # Convert history dict to list and sort by date.
        tale["history"] = process_history(tale.get("history"))

        if len(tale["history"]) > 0:
            tale["created_at"] = tale["history"][0]["date"]
            tale["creator"] = tale["history"][0]["author"]
            tale["year"] = tale["created_at"].year
        else:
            tale["created_at"] = "unknown"
            tale["creator"] = "unknown"
            tale["year"] = "unknown"

        tale["link"] = tale["url"].replace("https://scp-wiki.wikidot.com/", "")
        tales[tale["link"]] = tale

        if tale["year"] not in tale_years:
            tale_years[tale["year"]] = {}
        tale_years[tale["year"]][tale["link"]] = tale

    year_index = {}
    for year in tale_years:
        filename = processed_path / f"content_{year}.json"
        year_index[year] = filename
        to_file(tale_years[year], filename)
    to_file(year_index, processed_path / f"content_index.json")

    for tale_id in tales:
        del tales[tale_id]["raw_content"]
        del tales[tale_id]["raw_source"]
        year = tales[tale_id]["year"]
        tales[tale_id]["content_file"] = f"content_{year}.json"

    to_file(tales, processed_path / "index.json")


@cli.command()
def run_postproc_goi():

    processed_path = Path(cwd + "/data/processed/goi")
    os.makedirs(processed_path, exist_ok=True)

    print("Processing GOI list.")

    tale_list = from_file(cwd + "/data/goi.json")
    tales = {}
    for tale in tqdm(tale_list, smoothing=0):

        tale["images"] = get_images(tale["raw_content"])
        tale["hubs"] = get_hubs(tale["link"])
        tale["raw_source"] = get_wiki_source(tale["page_id"], tale["domain"])

        # Convert history dict to list and sort by date.
        tale["history"] = process_history(tale["history"])

        if len(tale["history"]) > 0:
            tale["created_at"] = tale["history"][0]["date"]
            tale["creator"] = tale["history"][0]["author"]
        else:
            tale["created_at"] = "unknown"
            tale["creator"] = "unknown"

        tale["link"] = tale["url"].replace("https://scp-wiki.wikidot.com/", "")
        tales[tale["link"]] = tale

    to_file(tales, processed_path / f"content_goi.json")

    for tale_id in tales:
        del tales[tale_id]["raw_content"]
        del tales[tale_id]["raw_source"]
        tales[tale_id]["content_file"] = f"content_goi.json"

    to_file(tales, processed_path / "index.json")


if __name__ == "__main__":
    cli()
