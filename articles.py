"""擷取公開文章正文，不執行來源腳本、不移除付費牆。"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import codecs
import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from lxml import etree, html as lxml_html
from trafilatura import extract

AGENT = "NewsPress/1.0"
MAX_BYTES = 4 * 1024 * 1024

class ArticleUnavailable(Exception):
    pass

def public_url(url):
    """只抓公開 HTTP(S) 網站；重新導向也必須檢查。"""
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ArticleUnavailable("原文網址無效")
    if parsed.port not in (None, 80, 443):
        raise ArticleUnavailable("不支援此原文網址")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ArticleUnavailable("原文網址不是公開網站")
    return url

def download(url, *, check_robots=True):
    with httpx.Client(timeout=12, follow_redirects=False, headers={"User-Agent": AGENT, "Accept-Language": "zh-TW,zh;q=0.9"}) as client:
        for _ in range(6):
            public_url(url)
            if check_robots and not robots_allowed(url):
                raise ArticleUnavailable("來源網站不允許自動擷取")
            with client.stream("GET", url) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if not location:
                        raise ArticleUnavailable("原文重新導向失敗")
                    url = urljoin(url, location)
                    continue
                response.raise_for_status()
                kind = response.headers.get("content-type", "").lower()
                if check_robots and not any(t in kind for t in ("text/html", "application/xhtml")):
                    raise ArticleUnavailable("來源不是可閱讀的網頁")
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ArticleUnavailable("原文頁面過大")
                    chunks.append(chunk)
                return b"".join(chunks), url
    raise ArticleUnavailable("原文重新導向過多")

@lru_cache(maxsize=128)
def robots_policy(origin):
    policy = RobotFileParser()
    try:
        data, _ = download(origin + "/robots.txt", check_robots=False)
        policy.parse(data.decode("utf-8", errors="replace").splitlines())
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            policy.allow_all = True
        else:
            policy.disallow_all = True
    except Exception:
        policy.disallow_all = True
    return policy

def robots_allowed(url):
    parsed = urlsplit(url)
    return robots_policy(f"{parsed.scheme}://{parsed.netloc}").can_fetch(AGENT, url)

def resolve_original(url):
    public_url(url)
    if urlsplit(url).hostname == "news.google.com":
        from googlenewsdecoder import gnewsdecoder
        result = gnewsdecoder(url, timeout=10)
        if not result.get("success"):
            raise ArticleUnavailable("暫時無法解析原文網址")
        url = result["decoded_url"]
    public_url(url)
    return url

def restricted(data):
    if isinstance(data, dict):
        if data.get("isAccessibleForFree") in (False, "false", "False"):
            return True
        return any(restricted(value) for value in data.values())
    if isinstance(data, list):
        return any(restricted(value) for value in data)
    return False

def _html_parser(raw: bytes):
    """bytes 一定要明確指定編碼解析：lxml 自動偵測在部分網站（ltn/ettoday/cna）
    誤判成 latin-1，會讓正文變成位元組級亂碼。meta 宣告優先，預設 utf-8。"""
    encodings = []
    meta = re.search(rb"""<meta[^>]*charset=["']?([A-Za-z0-9_-]+)""", raw[:3000])
    if meta:
        try:
            encodings.append(codecs.lookup(meta.group(1).decode("ascii", "ignore")).name)
        except Exception:
            pass
    encodings.append("utf-8")
    for enc in dict.fromkeys(encodings):
        try:
            tree = etree.fromstring(raw, etree.HTMLParser(encoding=enc, recover=True))
            if tree is not None:
                return tree
        except Exception:
            continue
    return lxml_html.fromstring(raw)


def extract_article(raw, url):
    tree = _html_parser(raw) if isinstance(raw, bytes) else lxml_html.fromstring(raw)
    for value in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            if restricted(json.loads(value)):
                raise ArticleUnavailable("此報導需要訂閱或登入")
        except (ValueError, TypeError):
            pass
    # 限縮在主報導，避免首頁推薦串也被正文辨識器納入。
    candidates = tree.xpath('//*[@itemprop="articleBody" and not(self::script)] | //div[contains(concat(" ",normalize-space(@class)," ")," caas-body ")]')
    if not candidates:
        candidates = tree.xpath('//article')
    content = candidates[0] if candidates else tree
    for node in list(content.xpath('.//script | .//style | .//nav | .//aside | .//figure | .//header | .//*[contains(@class,"read-more") or contains(@class,"recommendation") or contains(@class,"related-articles")]')):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    scoped_html = '<html><body>' + lxml_html.tostring(content, encoding="unicode") + '</body></html>' if candidates else lxml_html.tostring(content, encoding="unicode")
    body = extract(scoped_html, url=url, include_comments=False, include_tables=False,
                   include_images=False, include_links=False, favor_precision=True) or ""
    paragraphs = [line.strip() for line in body.splitlines() if line.strip()]
    visible = "\n".join(paragraphs)
    gate = ("訂閱後即可閱讀", "訂閱解鎖全文", "登入後閱讀全文", "subscribe to continue", "sign in to continue")
    if any(phrase in visible.lower() for phrase in gate):
        raise ArticleUnavailable("此報導需要訂閱或登入")
    if len(visible) < 160:
        raise ArticleUnavailable("未取得足夠的文章正文")
    authors = tree.xpath('//meta[@name="author"]/@content')
    return {"paragraphs": paragraphs, "author": authors[0].strip() if authors else "", "original_url": url, "content_status": "ready"}

def fetch_article(url):
    original = resolve_original(url)
    raw, final_url = download(original)
    return extract_article(raw, final_url)

def enrich_sections(sections, fetch_fn=None, progress=None):
    """每篇失敗獨立處理；成功保留所有段落，不以 RSS 摘要冒充正文。"""
    fetch = fetch_fn or fetch_article
    result = [{**s, "items": [dict(it) for it in s["items"]]} for s in sections]
    items = [it for s in result for it in s["items"]]
    unique = list(dict.fromkeys(it["link"] for it in items))
    content = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(fetch, url): url for url in unique}
        for completed, future in enumerate(as_completed(pending), 1):
            url = pending[future]
            try:
                content[url] = future.result()
            except Exception as exc:
                reason = str(exc) if isinstance(exc, ArticleUnavailable) else "來源暫時無法讀取"
                content[url] = {"paragraphs": [], "content_status": "unavailable", "content_error": reason}
            if progress:
                progress(completed, len(unique))
    for item in items:
        item.update(content[item["link"]])
        paragraphs = item.get("paragraphs") or []
        if paragraphs and paragraphs[0].strip() == item["title"].strip():
            item["paragraphs"] = paragraphs[1:]
    return result
