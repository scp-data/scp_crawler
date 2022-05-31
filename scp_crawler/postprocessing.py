import json
import os
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

cwd = os.getcwd()


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
    history = [v for v in history.values()]
    for revision in history:
        revision["date"] = datetime.strptime(revision["date"], "%d %b %Y %H:%M")
    history.sort(key=lambda x: x["date"])
    return history


print("Processing Hub list.")

hub_list = from_file(cwd + "/data/scp_hubs.json")
hub_items = {}
hub_references = {}
for hub in tqdm(hub_list):
    # Convert history dict to list and sort by date.
    hub["history"] = process_history(hub["history"])

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


def run_postproc_items():
    processed_path = Path(cwd + "/data/processed/items")
    os.makedirs(processed_path, exist_ok=True)

    title_list = from_file(cwd + "/data/scp_titles.json")
    title_index = {title["link"]: title["title"] for title in title_list}

    print("Processing Item list.")

    item_list = from_file(cwd + "/data/scp_items.json")
    items = {}
    series_items = {}
    for item in tqdm(item_list):
        if item["link"] in title_index:
            item["title"] = title_index[item["link"]]
        else:
            item["title"] = item["scp"]

        item["images"] = get_images(item["raw_content"])
        item["hubs"] = get_hubs(item["link"])

        # Convert history dict to list and sort by date.
        item["history"] = process_history(item["history"])

        if len(item["history"]) > 0:
            item["created_at"] = item["history"][0]["date"]
            item["creator"] = item["history"][0]["author"]

        items[item["scp"]] = item

        if item["series"] not in series_items:
            series_items[item["series"]] = {}
        series_items[item["series"]][item["scp"]] = item

    series_index = {}
    for series, series_items in series_items.items():
        filename = f"content_{series}.json"
        series_index[series] = filename
        to_file(series_items, processed_path / filename)
    to_file(series_index, processed_path / "content_index.json")

    for item_id in items:
        del items[item_id]["raw_content"]
        items[item_id]["content_file"] = series_index[items[item_id]["series"]]

    to_file(items, processed_path / "index.json")


def run_postproc_tales():

    processed_path = Path(cwd + "/data/processed/tales")
    os.makedirs(processed_path, exist_ok=True)

    print("Processing Tale list.")

    tale_list = from_file(cwd + "/data/scp_tales.json")
    tales = {}
    tale_years = {}
    for tale in tqdm(tale_list):

        tale["images"] = get_images(tale["raw_content"])
        tale["hubs"] = get_hubs(tale["link"])

        # Convert history dict to list and sort by date.
        tale["history"] = process_history(tale["history"])

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

    for year in tale_years:
        to_file(tale_years[year], processed_path / f"content_{year}.json")

    for tale_id in tales:
        del tales[tale_id]["raw_content"]
        year = tales[tale_id]["year"]
        tales[tale_id]["content_file"] = f"content_{year}.json"

    to_file(tales, processed_path / "index.json")


def run_postproc_goi():

    processed_path = Path(cwd + "/data/processed/goi")
    os.makedirs(processed_path, exist_ok=True)

    print("Processing GOI list.")

    tale_list = from_file(cwd + "/data/goi.json")
    tales = {}
    for tale in tqdm(tale_list):

        tale["images"] = get_images(tale["raw_content"])
        tale["hubs"] = get_hubs(tale["link"])

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
        tales[tale_id]["content_file"] = f"content_goi.json"

    to_file(tales, processed_path / "index.json")


if __name__ == "__main__":
    run_postproc_items()
    run_postproc_tales()
    run_postproc_goi()
