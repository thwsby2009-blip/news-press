"""完整、可列印的報紙；內容自然分頁，不裁切固定高度。"""
from datetime import datetime
from html import escape
from news import roc_date, weekday_cn
from ui import READER_CSS, masthead, reader_html

PRINT_CSS = """
@page {size:A4;margin:14mm 14mm 18mm;@bottom-center{content:counter(page);font-size:9pt;color:#686e67}}
body {margin:0;background:#f7f5ef;font-family:Arial,'Microsoft JhengHei',sans-serif}
.paper {max-width:1100px;margin:auto;padding:24px}
@media print {
 body{background:white}.paper{padding:0;max-width:none}
 .mast-center h1{font-size:38pt!important}.mast-center{padding:15px 0}.mast-top{font-size:8pt}
 .front-grid{display:block;padding:16px 0}.front-lead{display:block;border:0;padding:0}
 .lead-story h3{font-size:23pt!important}.briefs{margin-top:18px}
 .story-grid{display:block;columns:2;column-gap:8mm}
 .story-grid .story{padding:12px 0}.story h3{font-size:12pt!important}.lead-story h3{font-size:23pt!important}
 .story{break-inside:avoid}.section-heading{break-after:avoid;padding-top:18px}
 .outbound,.lead-foot{display:none}.paper-footer{margin-top:22px}
 .newspaper-article{break-inside:auto;padding:15px 0}.newspaper-article h2{font-size:19pt!important;break-after:avoid}
 .article-body{columns:2;column-gap:7mm;font-size:10.5pt;line-height:1.8}
 .article-body p{orphans:3;widows:3}.article-byline{break-after:avoid;font-size:8pt}
}
"""

def build_html(paper: str, sections: list[dict], issued: datetime | None = None) -> str:
    header = masthead(roc_date(issued), weekday_cn(issued))
    if paper != "每日新聞":
        header = header.replace("每日新聞", escape(paper))
    return (f'<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(paper)}</title>'
            f'<style>{READER_CSS}{PRINT_CSS}</style></head><body><div class="paper">{header}{reader_html(sections)}<footer class="paper-footer"><p>報導文字重新排版 · 新聞內容版權屬原媒體所有。</p></footer></div></body></html>')
