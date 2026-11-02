"""Fetch Google News RSS per game and merge new items into data/games.json.

Only the news list is touched. releaseDate/status stay manual: a human checks the
new headlines and edits them.
"""
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "games.json"
MAX_NEWS = 15
FEED = "https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"

QUERIES = {
    "azur-promilia": '"아주르 프로밀리아" OR "Azur Promilia"',
    "ananta": '"무한대" 넷이즈 OR "Ananta" NetEase',
    "silver-palace": '"실버 팰리스" OR "실버팰리스" OR "Silver Palace" 엘리멘타',
    "pareidolia": '"파레이돌리아" 넥슨 OR "Pareidolia" Nexon',
}


@dataclass(frozen=True)
class NewsItem:
    date: str
    title: str
    url: str

    def to_json(self) -> dict:
        return {"date": self.date, "title": self.title, "url": self.url}


def fetch(query: str) -> list[NewsItem]:
    url = FEED.format(q=urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={"User-Agent": "game-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        root = ET.fromstring(res.read())
    items = []
    for it in root.iter("item"):
        title, link, pub = it.findtext("title"), it.findtext("link"), it.findtext("pubDate")
        if not (title and link and pub):
            continue
        day = parsedate_to_datetime(pub).astimezone(timezone.utc).date().isoformat()
        items.append(NewsItem(day, title.strip(), link.strip()))
    return items


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    added = 0
    for game in data["games"]:
        query = QUERIES.get(game["id"])
        if not query:
            continue
        seen_urls = {n["url"] for n in game["news"]}
        seen_titles = {n["title"] for n in game["news"]}
        for item in fetch(query):
            if item.url in seen_urls or item.title in seen_titles:
                continue
            game["news"].append(item.to_json())
            seen_urls.add(item.url)
            added += 1
        game["news"].sort(key=lambda n: n["date"], reverse=True)
        game["news"] = game["news"][:MAX_NEWS]
    if added:
        data["updated"] = datetime.now(timezone.utc).date().isoformat()
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"added {added} items")


if __name__ == "__main__":
    main()
