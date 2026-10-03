"""共用報刊視覺與安全的新聞 HTML。"""
from html import escape
from urllib.parse import urlsplit

def safe_link(value):
    value = str(value or "").strip()
    try:
        parsed = urlsplit(value)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return escape(value, quote=True)
    except ValueError:
        pass
    return ""

def masthead(date, weekday):
    return (f'<header class="masthead"><div class="mast-top"><span>獨立閱讀，自由視野</span><span>{escape(date)} · 星期{escape(weekday)}</span><span>TAIPEI EDITION</span></div>'
            '<div class="mast-center"><span class="mast-side">每一天<br>都值得好好讀</span><div><h1>每日新聞<span class="seal">閱</span></h1><p>THE DAILY PRESS</p></div><span class="mast-side right">一份報紙<br>看見更大的世界</span></div><div class="mast-bottom">留一點時間，讀懂世界。</div></header>')

def article_html(item, *, lead=False, index=None, bilingual=False):
    title = escape(str(item.get("title", "")))
    title_zh = escape(str(item.get("title_zh") or "")) if bilingual else ""
    href = safe_link(item.get("original_url") or item.get("link"))
    source = escape(str(item.get("source") or "新聞來源"))
    date = escape(str(item.get("time") or ""))
    author = escape(str(item.get("author") or ""))
    origin = f'<a href="{href}" target="_blank" rel="noopener noreferrer">來源：{source}</a>' if href else f'來源：{source}'
    paragraphs = item.get("paragraphs") or []
    zh_paragraphs = (item.get("paragraphs_zh") or []) if bilingual else []
    if paragraphs:
        parts = []
        for i, p in enumerate(paragraphs):
            zh = zh_paragraphs[i] if i < len(zh_paragraphs) else ""
            part = f'<p>{escape(str(p))}</p>'
            if zh:
                part += f'<p class="zh-line">{escape(zh)}</p>'
            parts.append(part)
        body = '<div class="article-body">' + ''.join(parts) + '</div>'
        if title_zh:
            body += f'<p class="title-zh-line">譯：{title_zh}</p>'
    else:
        reason = escape(str(item.get("content_error") or "尚未取得文章正文"))
        body = f'<div class="article-unavailable">本篇正文未收錄 · {reason}。此處僅保留報導標題。</div>'
    return (f'<article class="newspaper-article {"lead-article" if lead else ""}"><h2>{title}</h2>'
            f'<p class="article-byline">{origin}<span>{date}</span><span>{author}</span></p>{body}</article>')


def paginate_sections(sections, per_page=2):
    pages = []
    for section in sections:
        for start in range(0, len(section["items"]), per_page):
            pages.append({**section, "items": section["items"][start:start + per_page]})
    return pages


def reader_html(sections, large=False, bilingual=False, full_page=False):
    """full_page=True：整個版組連續排版（傳統報紙式，不逐頁翻）；False：單頁內容。"""
    parts = [f'<main class="reader newspaper {"large-type" if large else ""}">']
    for section in sections:
        if not section["items"]:
            continue
        parts.append(f'<section class="paper-section"><div class="section-heading"><h2>{escape(section["name"])}版</h2><span>THE DAILY PRESS</span></div>')
        for index, item in enumerate(section["items"]):
            parts.append(article_html(item, lead=(index == 0), bilingual=bilingual))
        parts.append('</section>')
    return ''.join(parts) + '</main>'

READER_CSS = """
:root {--paper:#f7f5ef;--ink:#242a28;--muted:#686e67;--line:#d9dbd2;--accent:#aa392c}
* {box-sizing:border-box}
.masthead,.reader,.paper-footer,.welcome {color:var(--ink)}
.mast-top {display:flex;justify-content:space-between;font-size:11px;letter-spacing:1.5px;border-bottom:1px solid var(--line);padding:0 0 15px;color:var(--muted)}
.mast-center {display:flex;align-items:center;justify-content:space-between;text-align:center;padding:27px 0 19px}
.mast-center h1 {font-family:'Noto Serif TC','PMingLiU',serif;font-size:64px!important;letter-spacing:12px;font-weight:900;line-height:1.25;padding:0;margin:0}
.mast-center p {font-size:11px;letter-spacing:6px;margin:10px 0 0}
.mast-side {font-size:12px;line-height:1.9;text-align:left;color:var(--muted);letter-spacing:2px}
.mast-side.right {text-align:right}
.seal {display:inline-block;font-family:serif;font-size:17px;letter-spacing:0;vertical-align:middle;background:var(--accent);color:#fff;padding:5px;margin-left:6px}
.mast-bottom {text-align:center;border-bottom:4px double var(--ink);padding:0 0 18px;font-size:12px;letter-spacing:3px;color:var(--muted)}
.edition-line {display:flex;justify-content:space-between;border-top:1px solid var(--line);padding:15px 0 4px;font-size:12px;color:var(--muted)}
.edition-line b {color:var(--accent);font-size:18px;margin:0 5px}
.reader {margin-top:18px}
.front-grid {display:grid;grid-template-columns:1.65fr 1fr;border-top:2px solid var(--ink);border-bottom:1px solid var(--ink);padding:28px 0;gap:32px}
.front-lead {display:flex;flex-direction:column;justify-content:space-between;padding-right:32px;border-right:1px solid var(--line)}
.eyebrow {font:11px/1.6 Arial,sans-serif;letter-spacing:2px;color:var(--accent);margin:0 0 18px}
.eyebrow span {color:var(--muted);letter-spacing:1px}
.story h3 {font-family:'Noto Serif TC','PMingLiU',serif;font-size:20px!important;font-weight:700;line-height:1.65;padding:0;margin:0 0 16px;overflow-wrap:anywhere}
.story a {color:var(--ink)!important;text-decoration:none!important}
.story a:hover {color:var(--accent)!important}
.story a:focus-visible {outline:2px solid var(--accent);outline-offset:4px}
.outbound {color:var(--accent);font:14px Arial,sans-serif;white-space:nowrap}
.lead-story h3 {font-size:36px!important;line-height:1.55;letter-spacing:.5px}
.story-meta {display:flex;gap:10px;align-items:center;flex-wrap:wrap;font:11px/1.8 Arial,sans-serif;color:var(--muted);margin:0}
.lead-foot {display:flex;justify-content:space-between;gap:15px;border-top:1px solid var(--line);margin-top:32px;padding-top:15px;font-size:10px;color:var(--muted);letter-spacing:1px}
.briefs h2 {font-size:15px!important;font-weight:600;padding:0 0 15px;margin:0;border-bottom:1px solid var(--line)}
.briefs h2 span {float:right;font:10px Arial,sans-serif;letter-spacing:2px;color:var(--muted)}
.briefs .story {display:flex;gap:16px;padding:18px 0;border-bottom:1px solid var(--line)}
.briefs .story:last-child {border-bottom:0;padding-bottom:0}
.briefs h3 {font-size:16px!important;line-height:1.7;margin-bottom:8px}
.story-number {font:italic 25px Georgia,serif;color:var(--accent)}
.section-heading {display:flex;justify-content:space-between;align-items:center;padding:27px 0 12px;border-bottom:1px solid var(--ink)}
.section-heading h2 {font-family:'Noto Serif TC','PMingLiU',serif;font-size:23px!important;font-weight:700;padding:0;margin:0}
.section-heading h2 span {font:10px Arial,sans-serif;letter-spacing:2px;color:var(--muted);margin-left:15px}
.section-heading>span {font-size:11px;color:var(--muted)}
.story-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));column-gap:30px}
.story-grid .story {border-bottom:1px solid var(--line);padding:23px 0}
.large-type .story h3 {font-size:24px!important}.large-type .lead-story h3 {font-size:42px!important}.large-type .briefs h3 {font-size:20px!important}
.reading-note {padding:30px 0}.reading-note p {font-family:serif;font-size:24px;line-height:1.7}.reading-note small {color:var(--muted)}
.paper-footer {border-top:3px double var(--ink);margin-top:50px;padding:24px 0 15px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:20px;font-size:12px}
.paper-footer strong {font-family:serif;font-size:19px;letter-spacing:2px}.paper-footer small {font:9px Arial,sans-serif;letter-spacing:1px;margin-left:10px}
.paper-footer p {width:100%;font-size:11px;color:var(--muted);margin:0;line-height:1.8}
.welcome {text-align:center;padding:70px 20px;border-block:1px solid var(--line);margin-top:20px}.welcome h2 {font-family:serif}
@media(max-width:760px) {
 .mast-center h1 {font-size:44px!important;letter-spacing:7px}.mast-side{display:none}.mast-center{justify-content:center}.mast-top>span:first-child{display:none}
 .front-grid {grid-template-columns:1fr;gap:25px;padding:22px 0}.front-lead{padding-right:0;border-right:0}.lead-story h3{font-size:29px!important}
 .story-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:0 22px}.lead-foot{margin-top:20px}.briefs{border-top:1px solid var(--line);padding-top:22px}
}
@media(max-width:480px) {.story-grid{grid-template-columns:1fr}.story h3{font-size:19px!important}.lead-story h3{font-size:28px!important}.mast-top{font-size:10px;letter-spacing:.5px}.mast-center h1{font-size:39px!important}.seal{font-size:14px}.edition-line{font-size:10px}.lead-foot span:last-child{display:none}.large-type .lead-story h3{font-size:34px!important}}
"""
READER_CSS += """
.newspaper {border-top:2px solid var(--ink)}
.newspaper-article {padding:28px 0;border-bottom:1px solid var(--ink)}
.newspaper-article h2 {font-family:'Noto Serif TC','PMingLiU',serif;font-size:28px!important;line-height:1.5;letter-spacing:.03em;font-weight:700;margin:0 0 14px;padding:0;overflow-wrap:anywhere}
.lead-article h2 {font-size:36px!important}
.article-byline {display:flex;flex-wrap:wrap;gap:16px;font-size:11px;color:var(--muted);padding-bottom:16px;border-bottom:1px solid var(--line);margin-bottom:22px}
.article-byline a {color:var(--muted)!important;text-decoration:none!important}.article-byline a:hover{text-decoration:underline!important}
.article-body {columns:3;column-gap:32px;column-rule:1px solid var(--line);font-family:'Noto Serif TC','PMingLiU',serif;font-size:17px;line-height:1.95;text-align:justify;overflow-wrap:anywhere}
.article-body p {font:inherit;line-height:inherit;margin:0 0 1em;text-indent:2em;orphans:3;widows:3}
.article-body p:first-child {text-indent:0}.article-body p:first-child::first-letter{font-size:2.3em;float:left;line-height:1.3;margin:0 5px 0 0;color:var(--accent)}
.article-unavailable {padding:22px;background:#eeeee6;color:var(--muted);font-size:14px;line-height:1.8}
.zh-line {font-family:'Microsoft JhengHei','Noto Sans TC',sans-serif!important;font-size:.82em;line-height:1.75;color:var(--muted);text-indent:0!important;margin:0 0 1em!important;border-left:2px solid var(--line);padding-left:10px}
.title-zh-line {font-family:'Microsoft JhengHei','Noto Sans TC',sans-serif;font-size:13px;color:var(--muted);margin:18px 0 0;text-align:right}
.large-type .article-body {font-size:21px}.large-type .newspaper-article h2 {font-size:38px!important}
@media(max-width:900px){.article-body{columns:2;column-gap:24px}}
@media(max-width:600px){.article-body{columns:1;font-size:18px}.newspaper-article h2,.lead-article h2{font-size:27px!important}.large-type .newspaper-article h2{font-size:32px!important}.newspaper-article{padding:22px 0}}
"""

STYLE = READER_CSS + """
header[data-testid="stHeader"] {background:transparent;height:0}header[data-testid="stHeader"]>*{display:none}
.stApp {background:var(--paper);color:var(--ink)}
.block-container {max-width:1180px;padding:28px 36px 20px}
[data-testid="stVerticalBlock"] {gap:14px}
[data-testid="stExpander"] {border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent}
[data-testid="stBaseButton-primary"] {background:var(--accent);border-color:var(--accent)}
[data-testid="stBaseButton-secondary"],[data-testid="stDownloadButton"] button {border:1px solid var(--line);background:transparent;color:var(--ink)}
[data-testid="stTextInput"] input {font-size:14px}
[data-testid="stButtonGroup"] button {border-radius:3px!important}
[data-testid="stWidgetLabel"] p {font-size:12px;color:var(--muted)}
@media(max-width:640px){.block-container{padding:20px 18px}[data-testid="stHorizontalBlock"]{gap:10px}}
"""
