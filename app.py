# -*- coding: utf-8 -*-
"""新聞日報 — Streamlit 網頁（報紙即頁面 + PDF 下載）。

本機執行：streamlit run app.py
Streamlit Cloud：repo 上傳後於 streamlit.io/cloud 選 repo/branch/main/app.py
"""
import os
import sys
import tempfile

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news import SECTIONS, collect, roc_date, weekday_cn  # noqa: E402
from render import build_html  # noqa: E402
from pdf import html_to_pdf  # noqa: E402

st.set_page_config(page_title="每日新聞", page_icon="📰",
                   layout="wide", initial_sidebar_state="collapsed")

PAPER = "每日新聞"

# 隱藏 Streamlit 介面，讓報紙成為頁面本身
st.markdown("""
<style>
  header[data-testid="stHeader"] {display: none;}
  footer[data-testid="stFooter"] {display: none;}
  .block-container {padding: .6rem 1rem 0; max-width: 980px; margin: 0 auto;}
  div[data-testid="stStatusWidget"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

if "result" not in st.session_state:
    st.session_state.result = None

# ── 頂欄報頭 ──────────────────────────────
st.markdown(
    f"""
    <div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
                padding:2px 0 6px;border-bottom:3px solid #14100b;">
      <span style="font-family:'Noto Serif TC',serif;font-weight:900;font-size:28px;
                   letter-spacing:.12em;color:#14100b;">每日新聞</span>
      <span style="font-size:12.5px;color:#5c5344;letter-spacing:.15em;">
        {roc_date()}　星期{weekday_cn()}</span>
      <span style="font-size:11.5px;color:#8a8070;letter-spacing:.1em;margin-left:auto;">
        整合 Google 新聞 · Yahoo 新聞 ｜ 臺北編印</span>
    </div>
    """,
    unsafe_allow_html=True)

# ── 版組選擇（pills，單行、手機自動換行）────────────
picked_names = st.pills(
    "版組", [s["name"] for s in SECTIONS],
    selection_mode="multi",
    default=[s["name"] for s in SECTIONS],
    key="pills")

c1, c2, sp = st.columns([1, 1, 4])
do_build = c1.button("🖨 產生報紙", type="primary", use_container_width=True)
do_reset = c2.button("全部版組", use_container_width=True)
if do_reset:
    st.session_state.pills = [s["name"] for s in SECTIONS]
    st.rerun()

NAME2ID = {s["name"]: s["id"] for s in SECTIONS}
picked = [NAME2ID[n] for n in picked_names if n in NAME2ID]

if do_build:
    if not picked:
        st.error("至少選一個版組")
    else:
        with st.spinner("抓取新聞、排版中…（約 10 秒）"):
            try:
                sections, total = collect(picked, per_section=10)
                html = build_html(PAPER, sections)
                st.session_state.result = (html, total)
            except Exception as e:
                st.error(f"產生失敗：{e}")
                st.session_state.result = None

# ── 報紙即頁面（iframe 填滿）＋ PDF 下載 ────────────
if st.session_state.result:
    html, total = st.session_state.result
    out_name = f"每日新聞-{roc_date()}.pdf"

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "paper.pdf")
        html_to_pdf(html, p)
        with open(p, "rb") as f:
            pdf_bytes = f.read()

    dl, cap, sp2 = st.columns([1, 3, 2])
    dl.download_button(
        "⬇️ 下載 PDF",
        data=pdf_bytes,
        file_name=out_name,
        mime="application/pdf",
        use_container_width=True)
    cap.markdown(f"<div style='font-size:12px;color:#5c5344;padding-top:10px;'>"
                 f"本日共 {total} 則 ｜ 點新聞標題開新分頁讀原文</div>",
                 unsafe_allow_html=True)

    components.html(html, height=1600, scrolling=True)
