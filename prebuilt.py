# -*- coding: utf-8 -*-
"""每日預產報紙：讀取 build.py --json 產生的當日檔案；無檔或損壞回 None。"""
import json
import os
from datetime import datetime

from news import roc_date

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def daily_path(d: datetime | None = None) -> str:
    roc = roc_date(d).replace("年", "-").replace("月", "-").replace("日", "")
    return os.path.join(OUT_DIR, f"daily-{roc}.json")


def load_today(d: datetime | None = None) -> dict | None:
    """回傳今日預產 edition dict（含 prebuilt 標記）；無檔、空檔或結構不符回 None。"""
    try:
        with open(daily_path(d), encoding="utf-8") as f:
            data = json.load(f)
        sections = data["sections"]
        if not sections or not all(
            isinstance(s, dict) and all(k in s for k in ("id", "name", "items")) for s in sections
        ):
            return None
        return {
            "sections": sections,
            "total": sum(len(s["items"]) for s in sections),
            "issued": datetime.fromisoformat(data["issued"]),
            "prebuilt": True,
        }
    except Exception:
        return None
