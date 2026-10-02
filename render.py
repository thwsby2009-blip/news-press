# -*- coding: utf-8 -*-
"""傳統報紙版面 HTML 產生 — 襯線字、報頭、多欄排版。"""
from news import roc_date, weekday_cn

GOOGLE_FONTS = ("https://fonts.googleapis.com/css2"
                "?family=Noto+Serif+TC:wght@400;700;900&display=swap")

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Noto Serif TC', 'Noto Serif CJK TC', 'Times New Roman', serif;
  color: #1a1611;
  background: #3a372f;
}

.paper {
  background: #f8f5ee;
  max-width: 920px;
  margin: 24px auto;
  padding: 46px 52px 60px;
  box-shadow: 0 3px 24px rgba(0,0,0,.45);
}

/* ── 報頭 ─────────────────────────── */
.masthead { text-align: center; }
.mast-top {
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 11px; letter-spacing: .12em; color: #5c5344;
  border-bottom: 1px solid #b9ae97; padding-bottom: 6px;
}
.masthead h1 {
  font-weight: 900; font-size: 54px; letter-spacing: .08em;
  margin: 18px 0 10px; color: #14100b;
}
.mast-sub {
  font-size: 12.5px; letter-spacing: .22em; color: #5c5344;
  padding-bottom: 10px;
}
.rules { border-top: 3px solid #14100b; margin-bottom: 2px; }
.rules + .rules-thin { border-top: 1px solid #14100b; }

/* ── 頭條 ─────────────────────────── */
.hero { padding: 22px 0 18px; border-bottom: 1px solid #b9ae97; }
.hero-tag {
  display: inline-block; font-size: 12px; font-weight: 700;
  letter-spacing: .3em; padding: 3px 10px 3px 13px;
  border: 1.5px solid #14100b; margin-bottom: 12px;
}
.hero h2 { font-weight: 900; font-size: 31px; line-height: 1.35; margin-bottom: 10px; }
.hero .meta { font-size: 12px; color: #6b6152; letter-spacing: .08em; }

/* ── 版組 ─────────────────────────── */
.section { margin-top: 26px; page-break-inside: avoid; }
.sect {
  display: flex; align-items: center; gap: 16px;
  margin-bottom: 14px;
}
.sect::before, .sect::after { content: ""; flex: 1; border-top: 1px solid #14100b; }
.sect span {
  font-weight: 700; font-size: 19px; letter-spacing: .5em;
  padding-left: .5em; color: #14100b;
}

.cols { columns: 2; column-gap: 34px; column-rule: 1px solid #cfc4ab; }

article { padding: 10px 0; break-inside: avoid; }
article + article { border-top: 1px solid #ddd3bc; }
article h3 {
  font-weight: 700; font-size: 15.5px; line-height: 1.5;
  margin-bottom: 5px;
}
article .meta {
  font-size: 11px; color: #6b6152; letter-spacing: .06em;
}
article .desc {
  font-size: 12.5px; line-height: 1.7; color: #3d362a;
  margin-top: 5px; text-align: justify;
}

a { color: inherit; text-decoration: none; }
h1 a, h2 a, h3 a { display: block; }
h3 a:hover, h2 a:hover { color: #7a2c14; }

.foot {
  margin-top: 34px; padding-top: 10px;
  border-top: 1px solid #b9ae97;
  display: flex; justify-content: space-between;
  font-size: 11px; letter-spacing: .15em; color: #5c5344;
}

/* ── 列印 ─────────────────────────── */
@page {
  size: A4;
  margin: 15mm 13mm 17mm;
  @bottom-center {
    content: string(papername) " · 第 " counter(page) " 版";
    font-family: 'Noto Serif TC', serif;
    font-size: 9px; letter-spacing: .15em; color: #5c5344;
  }
}
@page :first { @bottom-center { content: string(papername) " · 頭版"; } }

@media print {
  body { background: none; }
  .paper { max-width: none; margin: 0; padding: 0; box-shadow: none; }
  h2 a:hover, h3 a:hover { color: inherit; }
}
"""

HTML_SHELL = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>{paper} — {date}</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<style>{css}</style>
</head>
<body>
<div class="paper" style="string-set: papername '{paper}'">
{body}
</div>
</body>
</html>"""


def _esc(s: str) -> str:
    s = s.replace(chr(38), chr(38) + 'amp;')
    s = s.replace(chr(60), chr(38) + 'lt;')
    s = s.replace(chr(62), chr(38) + 'gt;')
    return s.replace(chr(34), chr(38) + 'quot;')


def build_html(paper: str, sections: list[dict]) -> str:
    # 頭條 = 頭條版組第一則，先抽出放大（避免之後重複出現在版組）
    hero_html = ""
    if sections and sections[0]["id"] == "top" and sections[0]["items"]:
        top = dict(sections[0])
        top["items"] = list(top["items"])
        lead = top["items"].pop(0)
        sections = [top] + list(sections[1:])
        hero_html = (
            '<div class="hero"><span class="hero-tag">頭條</span>'
            f'<h2><a href="{_esc(lead["link"])}" target="_blank" rel="noopener">{_esc(lead["title"])}</a></h2>'
            f'<p class="meta">{_esc(lead["source"])}'
            + (f' ｜ {lead["time"]}' if lead["time"] else "")
            + '</p></div>')

    d_parts = []
    for sec in sections:
        if not sec["items"]:
            continue
        arts = []
        for it in sec["items"]:
            desc = f'<p class="desc">{it["desc"]}</p>' if it.get("desc") else ""
            arts.append(
                f'<article><h3><a href="{_esc(it["link"])}" target="_blank" rel="noopener">{_esc(it["title"])}</a></h3>'
                f'<p class="meta">{_esc(it["source"])}'
                + (f' ｜ {it["time"]}' if it["time"] else "")
                + f'</p>{desc}</article>')
        d_parts.append(
            f'<section class="section"><h2 class="sect"><span>{sec["name"]}'
            f'</span></h2><div class="cols">{"".join(arts)}</div></section>')

    body_parts = [
        '<header class="masthead">'
        f'<div class="mast-top"><span>{roc_date()} 星期{weekday_cn()}</span>'
        f'<span>整合 Google 新聞 · Yahoo 新聞</span><span>臺北編印</span></div>'
        f'<h1>{paper}</h1>'
        f'<div class="mast-sub">即 時 新 聞 ｜ 每 日 發 行</div>'
        '</header>',
        '<div class="rules"></div><div class="rules rules-thin"></div>',
    ]

    body_parts.append(hero_html)

    body_parts.extend(d_parts)
    body_parts.append(
        '<div class="foot"><span>本報新聞由公開 RSS 來源自動彙整</span>'
        '<span>版權屬各原媒體所有</span></div>')

    return HTML_SHELL.format(paper=paper, date=roc_date(),
                             fonts=GOOGLE_FONTS, css=CSS,
                             body="\n".join(body_parts))
