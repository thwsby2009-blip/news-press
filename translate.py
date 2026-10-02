# -*- coding: utf-8 -*-
"""英文正文繁中翻譯 — Google translate gtx 端點（免 key），逐段快取。"""
import json
import urllib.parse
import urllib.request
from functools import lru_cache

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


@lru_cache(maxsize=1024)
def _gtx(text: str, sl: str, tl: str) -> str:
    url = ("https://translate.googleapis.com/translate_a/single?"
           + urllib.parse.urlencode({"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": text}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=12) as r:
        data = json.load(r)
    return "".join(seg[0] for seg in data[0])


def to_zh(text: str) -> str:
    """英→繁中；失敗回空字串（雙語版面退回只顯原文）。"""
    text = (text or "").strip()
    if not text:
        return ""
    try:
        return _gtx(text, "en", "zh-TW").strip()
    except Exception:
        return ""


def translate_item(item: dict) -> dict:
    """為單篇加上 paragraphs_zh（與 paragraphs 逐段對應；標題加 title_zh）。
    個別段落翻譯失敗保留空字串；全部失敗時不掛欄位，版面乾淨退回只顯原文。"""
    paragraphs = item.get("paragraphs") or []
    if not paragraphs:
        return item
    from concurrent.futures import ThreadPoolExecutor
    tasks = list(paragraphs) + [item.get("title", "")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        zh_all = list(pool.map(to_zh, tasks))
    zh, title_zh = zh_all[:len(paragraphs)], zh_all[len(paragraphs)]
    if not any(zh):
        return item
    item["paragraphs_zh"] = zh
    if title_zh:
        item["title_zh"] = title_zh
    return item


def translate_sections(sections: list[dict], progress=None) -> list[dict]:
    """只翻譯英文版組（id 以 en_ 開頭）；逐篇並行、每篇獨立處理失敗。"""
    result = [{**s, "items": [dict(it) for it in s["items"]]} for s in sections]
    en_items = [it for s in result for it in s["items"] if s["id"].startswith("en_")]
    from concurrent.futures import ThreadPoolExecutor
    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in pool.map(translate_item, en_items):
            done += 1
            if progress:
                progress(done, len(en_items))
    return result
