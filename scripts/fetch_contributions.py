#!/usr/bin/env python3
"""
Fetch a GitHub user's public 53-week contribution calendar from the HTML
endpoint (no token, no third-party stats service) and cache it as JSON
for the heatmap generator.

GitHub's contribution page renders each day as:
    <td data-date="YYYY-MM-DD" data-level="0-4" id="contribution-day-component-W-D">
and puts the *exact* count in a separate element:
    <tool-tip for="contribution-day-component-W-D">N contributions on ...</tool-tip>
so the two are joined here by that shared id.
"""
import json
import re
import sys
import os

import requests
from bs4 import BeautifulSoup

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")


def fetch(username: str) -> dict:
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Exact count per cell id, from the sibling <tool-tip for="...">.
    counts_by_id = {}
    count_re = re.compile(r"^(No|\d+)\s+contributions?\s+on\s+(.+?)\.?\s*$", re.IGNORECASE)
    for tip in soup.find_all("tool-tip"):
        cell_id = tip.get("for")
        if not cell_id:
            continue
        text = tip.get_text(strip=True)
        m = count_re.match(text)
        if not m:
            continue
        n = 0 if m.group(1).lower() == "no" else int(m.group(1))
        counts_by_id[cell_id] = n

    days = []
    total = 0
    for td in soup.find_all("td", attrs={"data-date": True}):
        date = td["data-date"]
        level = int(td.get("data-level", 0))
        cell_id = td.get("id")
        count = counts_by_id.get(cell_id, 0)
        total += count
        days.append({"date": date, "level": level, "count": count})

    days.sort(key=lambda d: d["date"])

    # Header line, e.g. "97 contributions in the last year".
    header = soup.find(id="js-contribution-activity-description")
    header_text = re.sub(r"\s+", " ", header.get_text(strip=True)) if header else f"{total} contributions in the last year"

    return {
        "username": username,
        "total": total,
        "header_text": header_text,
        "days": days,
    }


def main():
    if len(sys.argv) != 2:
        print("usage: fetch_contributions.py <github-username>", file=sys.stderr)
        sys.exit(1)
    username = sys.argv[1]
    data = fetch(username)
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"fetched {len(data['days'])} days, {data['total']} total contributions -> {CACHE_PATH}")


if __name__ == "__main__":
    main()
