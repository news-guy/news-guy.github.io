#!/usr/bin/env python3
"""Write the CrossInk plugin catalog listing the newest .epub editions in this repository."""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

DEFAULT_REPOSITORY = "news-guy/news-guy.github.io"
DEFAULT_BRANCH = "main"
DEFAULT_LIMIT = 30
DEFAULT_OUTPUT = "crossink/catalog.json"
DAILY_NEWS_PATTERN = re.compile(r"^DailyNews_(\d{4}-\d{2}-\d{2})$")


def fetch_tree(repository, branch, token):
    url = f"https://api.github.com/repos/{repository}/git/trees/{urllib.parse.quote(branch)}?recursive=1"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": "crossink-news-catalog"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:
        tree = json.load(response)
    if tree.get("truncated"):
        raise RuntimeError("GitHub returned a truncated tree; the catalog would be incomplete")
    return tree["tree"]


def edition_title(stem):
    match = DAILY_NEWS_PATTERN.match(stem)
    if not match:
        return stem
    date = datetime.date.fromisoformat(match.group(1))
    return f"Daily News - {date.strftime('%a %d %b %Y')}"


def format_size(size):
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{max(1, round(size / 1024))} KB"


def build_catalog(entries, repository, branch, limit):
    epubs = [entry for entry in entries if entry.get("type") == "blob" and entry["path"].lower().endswith(".epub")]
    epubs.sort(key=lambda entry: entry["path"], reverse=True)

    books = []
    for entry in epubs[:limit]:
        path = entry["path"]
        stem = os.path.splitext(os.path.basename(path))[0]
        books.append({
            "id": stem,
            "title": edition_title(stem),
            "author": format_size(entry.get("size", 0)),
            "url": f"https://raw.githubusercontent.com/{repository}/{branch}/{urllib.parse.quote(path)}",
        })
    return {"title": "Daily News", "books": books}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY))
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    entries = fetch_tree(args.repository, args.branch, os.environ.get("GITHUB_TOKEN"))
    catalog = build_catalog(entries, args.repository, args.branch, args.limit)
    if not catalog["books"]:
        print("No .epub files found; leaving the existing catalog unchanged", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as output:
        json.dump(catalog, output, indent=2, ensure_ascii=True)
        output.write("\n")
    print(f"Wrote {len(catalog['books'])} editions to {args.output}; newest is {catalog['books'][0]['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
