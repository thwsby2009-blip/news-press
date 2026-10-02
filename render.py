# -*- coding: utf-8 -*-
"""懷舊翻頁報紙版面 — page-flip 翻頁書 + PDF 逐頁列印雙用途。

瀏覽器（有 JS）：StPageFlip 翻頁書，拖曳/點擊翻頁
PDF（WeasyPrint 不跑 JS）：.page 逐頁平鋪列印
"""
import re

from news import roc_date, weekday_cn

GOOGLE_FONTS = ("https://fonts.googleapis.com/css2"
                "?family=Noto+Serif+TC:wght@400;700;900&family=Cinzel:wght@700&display=swap")

DQ = chr(34)


def _esc(s: str) -> str:
    s = s.replace(chr(38), chr(38) + "amp;")
    s = s.replace(chr(60), chr(38) + "lt;")
    s = s.replace(chr(62), chr(38) + "gt;")
    return s.replace(chr(34), chr(38) + "quot;")


def build_html(paper: str, sections: list[dict]) -> str:
    """組版：頁面陣列 → 每頁 HTML。回傳完整 HTML（翻頁書 + 列印雙用途）。"""
    pages = _make_pages(paper, sections)
    pages_html = "\n".join(
        f'<div class="page" data-page="{i+1}">{p}</div>'
        for i, p in enumerate(pages))

    return SHELL.format(
        paper=_esc(paper), date=roc_date(), weekday=weekday_cn(),
        fonts=GOOGLE_FONTS, css=CSS, pages=pages_html,
        total_pages=len(pages))


# ── 組版邏輯 ──────────────────────────────────

def _article_html(it: dict, dropcap: bool = False) -> str:
    link = _esc(it.get("link") or "#")
    dc = ""
    if dropcap and it["title"]:
        t = _esc(it["title"])
        dc = (f'<p class="headline"><a href="{link}" target="_blank" rel="noopener"><span class="dc">{t[0]}</span>{t[1:]}</a></p>')
    else:
        dc = f'<p class="headline"><a href="{link}" target="_blank" rel="noopener">{_esc(it["title"])}</a></p>'
    meta = _esc(it["source"]) + (f' ｜ {it["time"]}' if it["time"] else "")
    return (f'<article>{dc}<p class="meta">{meta}</p></article>')


def _make_pages(paper: str, sections: list[dict]) -> list[str]:
    pages = []
    today = roc_date()

    # ── 頭版：報頭 + 頭條 + 精選 ──
    lead = None
    featured: list[dict] = []
    rest_sections = []
    for sec in sections:
        if not sec["items"]:
            continue
        if lead is None and sec["id"] == "top":
            items = list(sec["items"])
            lead = items.pop(0)
            if items:
                featured.append({**sec, "items": items[:2]})
            if items[2:]:
                featured.append({**sec, "name": "要聞", "items": items[2:6]})
            continue
        rest_sections.append(sec)

    hero = ""
    if lead:
        hero = _article_html(lead, dropcap=True)

    feat_html = ""
    for sec in featured:
        arts = "".join(_article_html(it) for it in sec["items"])
        feat_html += (f'<div class="sect"><span>{_esc(sec["name"])}</span></div>'
                      f'<div class="cols">{arts}</div>')

    pages.append(f"""
<div class="mast">
  <div class="mast-line">
    <span class="mast-date">{today}　星期{weekday_cn()}</span>
    <span class="mast-issue">第 一 號 ｜ 每 份 五 元</span>
  </div>
  <h1 class="mast-title">{_esc(paper)}</h1>
  <div class="mast-sub">MIN ZHONG NEWS ｜ TAIPEI</div>
  <div class="mast-rule"></div>
</div>
{f'<div class="lead"><div class="sect"><span>頭條</span></div>{hero}</div>' if hero else ''}
{feat_html}
<div class="pageno">— 1 —</div>
""")

    # ── 內頁：每頁 2 個版組 ──
    per_page = 2
    for chunk_start in range(0, len(rest_sections), per_page):
        chunk = rest_sections[chunk_start:chunk_start + per_page]
        body = ""
        for sec in chunk:
            arts = "".join(_article_html(it) for it in sec["items"])
            body += (f'<div class="sect"><span>{_esc(sec["name"])}</span></div>'
                     f'<div class="cols">{arts}</div>')
        pages.append(f"""
<div class="inner-head">
  <span>{_esc(paper)}</span><span>{today}</span>
</div>
{body}
<div class="pageno">— {chunk_start // per_page + 2} —</div>
""")

    return pages


# ── 樣式 ──────────────────────────────────────

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --paper: #f3ecd7;
  --paper-dark: #e8dfc0;
  --ink: #2b2317;
  --ink-soft: #4a3f2d;
  --ink-faint: #7a6f5c;
  --rule: #3a2f1e;
  --accent: #8c3b1b;
}

html, body {
  background: #26221b;
  font-family: 'Noto Serif TC', 'Times New Roman', serif;
  color: var(--ink);
}

/* ── 翻頁書容器（有 JS 時啟用）────────────── */
#flipbook { display: none; }

/* ── 平鋪模式（無 JS / 列印）───────────────── */
#flat { max-width: 880px; margin: 0 auto; }

/* ── 頁面 ─────────────────────────── */
.page {
  background: var(--paper);
  padding: 44px 48px 36px;
  position: relative;
  overflow: hidden;
}

/* 紙紋雜點 + 泛黃漸層（做舊） */
.page::before {
  content: "";
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse at 18% 12%, rgba(120,90,40,.10), transparent 55%),
    radial-gradient(ellipse at 85% 88%, rgba(110,80,35,.12), transparent 50%),
    radial-gradient(ellipse at 50% 50%, transparent 62%, rgba(90,65,25,.14));
  pointer-events: none;
}
/* 邊緣做舊陰影 */
.page::after {
  content: "";
  position: absolute; inset: 0;
  box-shadow: inset 0 0 60px rgba(70,50,20,.22);
  pointer-events: none;
}

/* ── 報頭（頭版）────────────────── */
.mast { text-align: center; position: relative; z-index: 1; }
.mast-line {
  display: flex; justify-content: space-between;
  font-size: 11.5px; letter-spacing: .14em; color: var(--ink-faint);
  border-bottom: 1px solid var(--rule); padding-bottom: 7px;
}
.mast-title {
  font-weight: 900; font-size: 64px; letter-spacing: .14em;
  color: var(--ink); margin: 22px 0 8px;
  text-shadow: 1px 1px 0 rgba(60,45,20,.18);
}
.mast-sub {
  font-size: 11px; letter-spacing: .5em; color: var(--ink-faint);
  font-family: 'Cinzel', 'Noto Serif TC', serif;
}
.mast-rule {
  margin-top: 14px; height: 0;
  border-top: 3px double var(--rule);
  border-bottom: 1px solid var(--rule);
  padding-top: 2px;
}

/* ── 版組標題 ─────────────────────────── */
.sect {
  display: flex; align-items: center; gap: 14px;
  margin: 20px 0 12px;
}
.sect::before, .sect::after {
  content: ""; flex: 1;
  border-top: 1px solid var(--rule);
}
.sect span {
  font-weight: 700; font-size: 20px; letter-spacing: .55em;
  padding-left: .55em; color: var(--ink);
}
.lead .sect { margin-top: 4px; }

/* ── 文章 ─────────────────────────── */
.cols {
  columns: 3; column-gap: 30px;
  column-rule: 1px solid rgba(58,47,30,.35);
}
.cols:has(article:only-child) { columns: 1; }

article { padding: 9px 0; break-inside: avoid; }
article + article { border-top: 1px solid rgba(58,47,30,.28); }

.headline {
  font-weight: 700; font-size: 15.5px; line-height: 1.55;
  margin-bottom: 5px; text-align: justify;
}
.headline a { color: inherit; text-decoration: none; }
.headline a:hover { color: var(--accent); }

/* 頭條首字放大 */
.dc {
  float: left; font-weight: 900;
  font-size: 52px; line-height: .85;
  padding: 6px 10px 0 0;
  color: var(--accent);
}

.meta { font-size: 11px; color: var(--ink-faint); letter-spacing: .06em; }

/* ── 頁碼 ─────────────────────────── */
.pageno {
  text-align: center; margin-top: 26px;
  font-size: 12px; letter-spacing: .3em; color: var(--ink-faint);
}

/* ── 內頁報頭 ─────────────────────────── */
.inner-head {
  display: flex; justify-content: space-between;
  font-size: 11px; letter-spacing: .18em; color: var(--ink-faint);
  border-bottom: 1px solid var(--rule); padding-bottom: 6px;
  margin-bottom: 4px;
}

/* ── 翻頁書工具列 ─────────────────────── */
.toolbar {
  display: none;
  justify-content: center; align-items: center; gap: 18px;
  padding: 12px 0 4px;
}
.toolbar button {
  font-family: inherit; font-size: 14px; letter-spacing: .2em;
  background: var(--paper-dark); color: var(--ink);
  border: 1px solid var(--rule); border-radius: 3px;
  padding: 8px 22px; cursor: pointer;
  box-shadow: 0 2px 5px rgba(0,0,0,.35);
}
.toolbar button:hover { background: var(--paper); }
.toolbar .pinfo { font-size: 12.5px; color: var(--ink-faint); letter-spacing: .15em; }

/* ── 列印（PDF 用：逐頁平鋪）────────────── */
@page { size: A4; margin: 0; }
@media print {
  html, body { background: none; }
  #flipbook, .toolbar { display: none !important; }
  #flat { display: block !important; max-width: none; }
  .page {
    width: 210mm; height: 296mm;
    padding: 16mm 14mm 12mm;
    page-break-after: always;
    box-shadow: none;
  }
  .page:last-child { page-break-after: auto; }
  .headline a:hover { color: inherit; }
}
"""

SHELL = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{paper} — {date}</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<style>{css}</style>
</head>
<body>
<div id="flipbook"></div>
<div class="toolbar">
  <button id="prevBtn">◀ 上一頁</button>
  <span class="pinfo" id="pageInfo"></span>
  <button id="nextBtn">下一頁 ▶</button>
</div>
<div id="flat">{pages}</div>

<script src="https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.js"></script>
<script>
(function () {{
  var flat = document.getElementById('flat');
  var book = document.getElementById('flipbook');
  var toolbar = document.querySelector('.toolbar');

  if (typeof St === 'undefined' || !window.PageFlip) {{
    return; // CDN 沒載入 → 保持平鋪
  }}

  // 有 JS + 程式庫 → 翻頁書模式
  var pages = [];
  flat.querySelectorAll('.page').forEach(function (p) {{ pages.push(p); }});

  flat.style.display = 'none';
  book.style.display = 'block';
  toolbar.style.display = 'flex';

  var pf = new St.PageFlip(book, {{
    width: 560, height: 760,
    size: 'fixed',
    minWidth: 320, maxWidth: 1200,
    minHeight: 420, maxHeight: 1600,
    maxShadowOpacity: 0.45,
    showCover: true,
    mobileScrollSupport: false,
    flippingTime: 550,
    usePortrait: false,
    startZIndex: 0,
    autoSize: true
  }});

  // page-flip 需要自己的 DOM 結構：直接把頁面元素塞進去
  pf.loadFromHTML(document.querySelectorAll('#flat .page'));

  // 工具列
  var info = document.getElementById('pageInfo');
  function upd() {{
    info.textContent = '第 ' + pf.getCurrentPageIndex() + 1 + ' / ' + pf.getPageCount() + ' 頁';
  }}
  pf.on('flip', function (e) {{ upd(); }});
  document.getElementById('prevBtn').addEventListener('click', function () {{ pf.flipPrev(); }});
  document.getElementById('nextBtn').addEventListener('click', function () {{ pf.flipNext(); }});
  upd();
}})();
</script>
</body>
</html>"""
