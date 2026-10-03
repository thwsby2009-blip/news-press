# -*- coding: utf-8 -*-
"""英文正文繁中翻譯：限制同時請求、只快取成功结果，保留失敗原因。

後端鏈：DeepL（st.secrets／env 有 key 時優先）→ Google gtx → MyMemory。
雲端機房 IP 會被 gtx 擋（403）、MyMemory 匿名額度每日 5000 字，
提供 email（de 參數）可升至 50,000 字／日。
"""
import json
import logging
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from threading import BoundedSemaphore

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
# 所有閱報工作階段共用，避免逐篇與逐段的巢狀並行造成瞬間大量請求。
_REQUEST_SLOTS = BoundedSemaphore(2)
ERROR_LABELS = {"blocked": "翻譯服務拒絕存取", "rate_limited": "翻譯服務暫時限制請求頻率",
                "timeout": "翻譯連線逾時", "network": "無法連線至翻譯服務",
                "response": "翻譯服務未回傳有效譯文", "unavailable": "翻譯服務暫時無法使用"}

@lru_cache(maxsize=1024)
def _gtx(text: str, sl: str, tl: str) -> str:
    url = ("https://translate.googleapis.com/translate_a/single?"
           + urllib.parse.urlencode({"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": text}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with _REQUEST_SLOTS:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.load(r)
    translated = "".join(seg[0] for seg in data[0] if isinstance(seg[0], str)).strip()
    if not translated:
        raise ValueError("empty translation")
    return translated


@lru_cache(maxsize=1024)
def _mymemory(text: str, tl: str) -> str:
    """備援後端：MyMemory API。Google gtx 會擋雲端機房 IP（403），MyMemory 官方供程式化使用。"""
    url = ("https://api.mymemory.translated.net/get?"
           + urllib.parse.urlencode({"q": text, "langpair": f"en|{tl}"}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with _REQUEST_SLOTS:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.load(r)
    translated = (data.get("responseData") or {}).get("translatedText") or ""
    status = data.get("responseStatus")
    if status not in (200, "200") or "MYMEMORY WARNING" in translated.upper() or not translated.strip():
        raise ValueError("empty translation")
    return translated.strip()


@lru_cache(maxsize=1024)
def _deepl(text: str, tl: str, key: str) -> str:
    """正規後端：DeepL API free tier（每日 50 萬字），en→zh-TW 用 target_lang=ZH-TW。"""
    host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
    url = f"https://{host}/v2/translate"
    body = urllib.parse.urlencode({"text": text, "target_lang": "ZH-TW"}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"DeepL-Auth-Key {key}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with _REQUEST_SLOTS:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    translated = (data.get("translations") or [{}])[0].get("text") or ""
    if not translated.strip():
        raise ValueError("empty translation")
    return translated.strip()


def _deepl_key():
    key = os.environ.get("DEEPL_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st
        key = str(st.secrets.get("DEEPL_API_KEY", "")).strip()
        return key
    except Exception:
        return ""


def _translate(text):
    text = (text or "").strip()
    if not text:
        return "", None
    key = _deepl_key()
    backends = []
    if key:
        backends.append((_deepl, (text, "zh-TW", key)))
    backends.append((_gtx, (text, "en", "zh-TW")))
    backends.append((_mymemory, (text, "zh-TW")))
    last_code = "unavailable"
    for backend, args in backends:
        try:
            value = backend(*args).strip()
            if not value:
                raise ValueError("empty translation")
            return value, None
        except urllib.error.HTTPError as exc:
            last_code = {403: "blocked", 429: "rate_limited"}.get(exc.code, "unavailable")
            # 不記錄帶有文章文字的查詢網址或回應正文。
            logging.warning("Translation request failed: HTTP %s (%s)", exc.code, last_code)
            if last_code in ("blocked", "rate_limited") and backend is not backends[-1]:
                continue  # 拒絕或限速：試下一個後端
        except (TimeoutError, socket.timeout):
            last_code = "timeout"
            logging.warning("Translation request failed: timeout")
        except urllib.error.URLError:
            last_code = "network"
            logging.warning("Translation request failed: connection error")
        except (ValueError, TypeError, IndexError, KeyError):
            last_code = "response"
            logging.warning("Translation request failed: invalid response")
        except Exception:
            last_code = "unavailable"
            logging.warning("Translation request failed: unavailable")
    return "", last_code


def to_zh(text: str) -> str:
    return _translate(text)[0]


def translate_item(item: dict) -> dict:
    """只補缺少的段落與標題；保留已成功的譯文及原文順序。"""
    paragraphs = item.get("paragraphs") or []
    if not paragraphs:
        return item
    existing = item.get("paragraphs_zh") or []
    translated = [existing[i] if i < len(existing) else "" for i in range(len(paragraphs))]
    errors = set()
    for i, paragraph in enumerate(paragraphs):
        if translated[i] or not paragraph.strip():
            continue
        translated[i], error = _translate(paragraph)
        if error:
            errors.add(error)
        if error in ("blocked", "rate_limited"):
            break  # 服務明確拒絕時停止本篇，不連續送出剩餘段落。
    title_zh = item.get("title_zh") or ""
    if not title_zh and not errors.intersection({"blocked", "rate_limited"}):
        title_zh, error = _translate(item.get("title", ""))
        if error:
            errors.add(error)
    if any(translated):
        item["paragraphs_zh"] = translated
    if title_zh:
        item["title_zh"] = title_zh
    complete = all(value or not text.strip() for text, value in zip(paragraphs, translated))
    complete = complete and (bool(title_zh) or not item.get("title", "").strip())
    item["translation_status"] = "complete" if complete else ("partial" if any(translated) else "unavailable")
    item["translation_errors"] = sorted(errors)
    return item


def translation_summary(sections):
    total = missing = 0
    errors = set()
    for section in sections:
        if not section["id"].startswith("en_"):
            continue
        for item in section["items"]:
            paragraphs = item.get("paragraphs") or []
            if not paragraphs:
                continue
            total += 1
            zh = item.get("paragraphs_zh") or []
            incomplete = any(p.strip() and (i >= len(zh) or not zh[i]) for i, p in enumerate(paragraphs))
            incomplete = incomplete or (bool(item.get("title")) and not item.get("title_zh"))
            if incomplete:
                missing += 1
                errors.update(item.get("translation_errors", []))
    return {"total": total, "missing": missing, "errors": sorted(errors)}


def translate_sections(sections: list[dict], progress=None) -> list[dict]:
    result = [{**s, "items": [dict(it) for it in s["items"]]} for s in sections]
    en_items = [it for s in result for it in s["items"] if s["id"].startswith("en_")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for done, _ in enumerate(pool.map(translate_item, en_items), 1):
            if progress:
                progress(done, len(en_items))
    return result
