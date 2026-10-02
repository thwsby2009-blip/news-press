# -*- coding: utf-8 -*-
"""新聞來源設定與抓取 — RSS 為主，官方來源，不易被鎖。"""
import re
from concurrent.futures import ThreadPoolExecutor
import email.utils
from datetime import datetime, timezone, timedelta

import urllib.request
import ssl
import xml.etree.ElementTree as ET

TPE = timezone(timedelta(hours=8))

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "zh-TW,zh;q=0.9",
           "Connection": "keep-alive"}

# 版組 → RSS 來源（priority 順序 = 去重時保留先出現者）
SECTIONS = [
    {"id": "top",    "name": "頭條",   "feeds": [
        ("Google 新聞", "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
        ("Yahoo 新聞",  "https://tw.news.yahoo.com/rss/politics"),
    ]},
    {"id": "world",  "name": "國際",   "feeds": [
        ("Google 新聞", "https://news.google.com/rss/headlines/section/topic/WORLD?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ]},
    {"id": "biz",    "name": "財經",   "feeds": [
        ("Google 新聞", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ]},
    {"id": "tech",   "name": "科技",   "feeds": [
        ("Google 新聞", "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
        ("Yahoo 新聞",  "https://tw.news.yahoo.com/rss/technology"),
    ]},
    {"id": "ent",    "name": "影劇",   "feeds": [
        ("Google 新聞", "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
        ("Yahoo 新聞",  "https://tw.news.yahoo.com/rss/entertainment"),
    ]},
    {"id": "sports", "name": "體育",   "feeds": [
        ("Google 新聞", "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
        ("Yahoo 新聞",  "https://tw.news.yahoo.com/rss/sports"),
    ]},
    # 英文版組（學習用）：BBC／衛報／NPR 官方 RSS，robots 允許自動擷取
    {"id": "en_top",   "name": "英文·頭條", "feeds": [
        ("BBC 新聞", "https://feeds.bbci.co.uk/news/rss.xml"),
        ("NPR 新聞", "https://feeds.npr.org/1001/rss.xml"),
    ]},
    {"id": "en_world", "name": "英文·國際", "feeds": [
        ("BBC 新聞", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("衛報",     "https://www.theguardian.com/world/rss"),
    ]},
    {"id": "en_biz",   "name": "英文·財經", "feeds": [
        ("BBC 新聞", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ]},
    {"id": "en_tech",  "name": "英文·科技", "feeds": [
        ("BBC 新聞", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ]},
]

_CTX = ssl.create_default_context()

_SUFFIX_RE = re.compile(r"\s+-\s+[^-\s][^-]*$")  # Google 標題尾端「 - 媒體名」


def _now() -> datetime:
    return datetime.now(TPE)


def roc_date(d: datetime | None = None) -> str:
    """民國日期：民國115年10月2日"""
    d = d or _now()
    return f"民國{d.year - 1911}年{d.month}月{d.day}日"


def weekday_cn(d: datetime | None = None) -> str:
    d = d or _now()
    return "一二三四五六日"[d.weekday()]


def fetch_feed(url: str, timeout: int = 15) -> list[dict]:
    """抓單一 RSS，回傳 [{title, link, source, time}]"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        data = r.read()
    root = ET.fromstring(data)
    items = []
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        if not title:
            continue
        link = (it.findtext("link") or "").strip()
        dt = None
        pub = it.findtext("pubDate")
        if pub:
            try:
                dt = email.utils.parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=TPE)
                dt = dt.astimezone(TPE)
            except Exception:
                dt = None
        publisher = (it.findtext("source") or "").strip()
        if publisher and title.endswith(" - " + publisher):
            title = title[:-(len(publisher) + 3)]
        items.append({"title": title, "link": link, "source": publisher,
                      "time": dt.strftime("%m/%d %H:%M") if dt else ""})
    return items


def normalize_title(title: str) -> str:
    """去來源後綴、去空白，用於跨來源去重"""
    t = _SUFFIX_RE.sub("", title)
    return re.sub(r"\s+", "", t).lower()


def collect(section_ids: list[str] | None = None, per_section: int = 10,
            fetch_fn=None) -> tuple[list[dict], int]:
    """抓全部版組，回傳 ([{id, name, items}], 總則數)。跨版組去重。"""
    fetch = fetch_fn or fetch_feed
    want = [s for s in SECTIONS if not section_ids or s["id"] in section_ids]
    # 同時等待各來源，維持原來的來源排序與去重優先順序。
    def load(url):
        try:
            return fetch(url)
        except Exception:
            return []

    urls = list(dict.fromkeys(url for sec in want for _, url in sec["feeds"]))
    with ThreadPoolExecutor(max_workers=8) as pool:
        fetched = dict(zip(urls, pool.map(load, urls)))
    seen: set[str] = set()
    out, total = [], 0
    for sec in want:
        raw: list[dict] = []
        for src_name, url in sec["feeds"]:
            raw.extend({**it, "source": it.get("source") or src_name, "feed_source": src_name} for it in fetched[url])
        items = []
        for it in raw:
            key = normalize_title(it["title"])
            if key in seen:
                continue
            seen.add(key)
            items.append(it)
            if len(items) >= per_section:
                break
        total += len(items)
        out.append({"id": sec["id"], "name": sec["name"], "items": items})
    return out, total
