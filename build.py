# -*- coding: utf-8 -*-
"""新聞日報 — 產生 + 匯出 PDF（命令列）。

用法：
  python build.py                    # 全部版組 → 今日報紙 PDF
  python build.py --json only        # 只產生當日預產 JSON（給網頁預先載入）
  python build.py --html only        # 只產生 HTML 預覽
  python build.py --out my.pdf       # 指定輸出檔名
  python build.py --sections top,world
"""
import argparse
import json
import os

from news import collect, roc_date
from render import build_html

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def build(section_ids=None, per_section=10, want_html=False, out=None, want_json=False):
    sections, total = collect(section_ids, per_section=per_section)
    from articles import enrich_sections
    sections = enrich_sections(sections)
    os.makedirs(OUT_DIR, exist_ok=True)
    if want_json:
        from datetime import datetime, timezone, timedelta
        from news import TPE
        issued = datetime.now(TPE)
        data = {"issued": issued.isoformat(), "total": total, "sections": sections}
        json_path = out or os.path.join(
            OUT_DIR, f"daily-{roc_date(issued).replace('年', '-').replace('月', '-').replace('日', '')}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        # 只保留最近 7 天的預產檔
        import glob
        for old in sorted(glob.glob(os.path.join(OUT_DIR, "daily-*.json")), key=os.path.getmtime)[:-7]:
            try:
                os.remove(old)
            except OSError:
                pass
        return json_path, total
    paper = "每日新聞"
    html = build_html(paper, sections)
    if out is None:
        out = os.path.join(OUT_DIR, f"news-{roc_date().replace('年', '-').replace('月', '-').replace('日', '')}.pdf")
    if want_html:
        html_path = out.rsplit(".", 1)[0] + ".html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return html_path, total
    from pdf import html_to_pdf
    html_to_pdf(html, out)
    return out, total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", default=None, help="逗號分隔版組 id：top,world,biz,tech,ent,sports")
    ap.add_argument("--out", default=None, help="輸出檔名")
    ap.add_argument("--html", default=None, help="設為 only 只產生 HTML 預覽")
    ap.add_argument("--json", default=None, help="設為 only 只產生當日預產 JSON")
    a = ap.parse_args()
    path, total = build(a.sections and [s.strip() for s in a.sections.split(",")],
                        want_html=(a.html == "only"), want_json=(a.json == "only"), out=a.out)
    print(f"{path}  ({total} 則)")
