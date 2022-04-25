import json
import os

cwd = os.getcwd()


def from_file(path):
    with open(path, "r") as fs:
        data = json.load(fs)
    return data


def to_file(obj, path):
    with open(path, "w") as fs:
        json.dump(obj, fs, sort_keys=True)


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
    items[item["scp"]] = item

print("Saving indexed content.")
to_file(items, cwd + "/data/scp_indexed.json")

for item_id in items:
    del items[item_id]["raw_content"]

print("Saving metadata only.")
to_file(items, cwd + "/data/scp_metadata.json")
