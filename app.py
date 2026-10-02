# -*- coding: utf-8 -*-
"""新聞日報 — Streamlit 網頁。

本機執行：streamlit run app.py
Streamlit Cloud：repo 上傳後於 streamlit.io/cloud 選 repo/branch/main/app.py
"""
import base64
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news import SECTIONS, collect, roc_date, weekday_cn  # noqa: E402
from render import build_html  # noqa: E402
from pdf import html_to_pdf  # noqa: E402

st.set_page_config(page_title="新聞日報", page_icon="📰", layout="centered")

PAPER = "寰宇日報"

if "sections" not in st.session_state:
    st.session_state.sections = {s["id"]: True for s in SECTIONS}
if "result" not in st.session_state:
    st.session_state.result = None

st.markdown(
    f"""
    <div style="text-align:center;padding:18px 0 6px;">
      <div style="font-size:12px;letter-spacing:.35em;color:#6b6152;">民國紀元 ｜ 臺北編印</div>
      <div style="font-family:'Noto Serif TC',serif;font-weight:900;font-size:44px;
                  letter-spacing:.12em;color:#14100b;margin:8px 0;">寰宇日報</div>
      <div style="font-size:13px;color:#5c5344;letter-spacing:.2em;">
        {roc_date()}　星期{weekday_cn()}</div>
      <hr style="border:none;border-top:3px solid #14100b;margin-top:14px;">
      <hr style="border:none;border-top:1px solid #14100b;margin-top:2px;">
    </div>
    """,
    unsafe_allow_html=True)

st.caption("勾選版組 → 產生今日報紙 → 下載 PDF。新聞來源：Google 新聞、Yahoo 新聞官方 RSS。")

cols = st.columns(len(SECTIONS))
for c, s in zip(cols, SECTIONS):
    st.session_state.sections[s["id"]] = c.checkbox(s["name"], True, key=f"cb_{s['id']}")

c1, c2 = st.columns([1, 1])
do_build = c1.button("🖨 產生報紙", type="primary", use_container_width=True)
do_reset = c2.button("重新選擇", use_container_width=True)
if do_reset:
    st.session_state.result = None
    st.rerun()

if do_build:
    picked = [s["id"] for s in SECTIONS if st.session_state.sections.get(s["id"])]
    if not picked:
        st.error("至少勾選一個版組")
    else:
        with st.spinner("抓取新聞、排版中…（約 10 秒）"):
            try:
                sections, total = collect(picked, per_section=10)
                html = build_html(PAPER, sections)
                st.session_state.result = (html, total)
            except Exception as e:
                st.error(f"產生失敗：{e}")
                st.session_state.result = None

if st.session_state.result:
    html, total = st.session_state.result
    out_name = f"寰宇日報-{roc_date()}.pdf"
    st.success(f"完成：{total} 則新聞")

    # WeasyPrint 產生 PDF（位元組串流直接下載）
    pdf_bytes = html_to_pdf(html, out_name + ".tmp") and open(out_name + ".tmp", "rb").read()
    if os.path.exists(out_name + ".tmp"):
        os.remove(out_name + ".tmp")

    st.download_button(
        "⬇️ 下載 PDF",
        data=pdf_bytes,
        file_name=out_name,
        mime="application/pdf",
        use_container_width=True)
