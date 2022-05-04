import json
import os
from datetime import date, datetime

from bs4 import BeautifulSoup

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
        json.dump(obj, fs, sort_keys=True, default=json_serial)


title_list = from_file(cwd + "/data/scp_titles.json")
title_index = {title["link"]: title["title"] for title in title_list}

item_list = from_file(cwd + "/data/scp_items.json")
items = {}
for item in item_list:
    if item["link"] in title_index:
        item["title"] = title_index[item["link"]]
    else:
        item["title"] = item["scp"]
    del item["link"]

    content_soup = BeautifulSoup(item["raw_content"], "lxml")
    img_tags = content_soup.find_all("img")
    item["images"] = [img["src"] for img in img_tags]

    # Convert history dict to list and sort by date.
    item["history"] = [v for v in item["history"].values()]
    for revision in item["history"]:
        revision["date"] = datetime.strptime(revision["date"], "%d %b %Y %H:%M")
    item["history"].sort(key=lambda x: x["date"])

    if len(item["history"]) > 0:
        item["created_at"] = item["history"][0]["date"]
        item["creator"] = item["history"][0]["author"]

    items[item["scp"]] = item

print("Saving indexed content.")
to_file(items, cwd + "/data/scp_indexed.json")

for item_id in items:
    del items[item_id]["raw_content"]

print("Saving metadata only.")
to_file(items, cwd + "/data/scp_metadata.json")
