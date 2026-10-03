"""每日新聞：可搜尋的響應式閱報台，按需匯出 PDF。"""
from datetime import datetime
import logging
import streamlit as st
from news import SECTIONS, TPE, collect, roc_date, weekday_cn
from render import build_html
from ui import STYLE, masthead, reader_html, paginate_sections
from articles import enrich_sections, fetch_article
from prebuilt import load_today
from translate import translate_sections, translation_summary, ERROR_LABELS

@st.cache_data(ttl=3600, max_entries=256, show_spinner=False)
def cached_article(url):
    return fetch_article(url)

st.set_page_config(page_title="每日新聞 · 留一點時間，讀懂世界", page_icon="📰", layout="wide")
st.markdown(f"<style>{STYLE}</style>", unsafe_allow_html=True)

def clear_filters():
    st.session_state.category = "全部"
    st.session_state.query = ""
    st.session_state.paper_page = 0

def reset_page():
    st.session_state.paper_page = 0

def turn_page(delta):
    st.session_state.paper_page += delta

def select_all():
    st.session_state.edition_sections = [s["name"] for s in SECTIONS]

for key, value in {"edition": None, "pdf_bytes": None, "attempted": False, "paper_page": 0}.items():
    st.session_state.setdefault(key, value)
st.session_state.setdefault("edition_sections", [s["name"] for s in SECTIONS])

now = datetime.now(TPE)
st.markdown(masthead(roc_date(now), weekday_cn(now)), unsafe_allow_html=True)
with st.expander("訂製我的報紙 · 版組與篇數", expanded=False):
    st.caption("選擇收錄的版組，再按「更新本期」。下方分類與搜尋只篩選閱讀畫面。")
    names = st.multiselect("收錄版組", [s["name"] for s in SECTIONS], key="edition_sections")
    count = st.select_slider("每個版組最多篇數", options=[3, 5, 10], value=3)
    st.button("選取全部版組", on_click=select_all)
action, info = st.columns([1, 4], vertical_alignment="center")
refresh = action.button("更新本期 ↻", type="primary", use_container_width=True)
info.caption("擷取公開報導文字 · 重新編排 · 在這裡直接閱讀")
if refresh or (not st.session_state.attempted and st.session_state.edition is None):
    st.session_state.attempted = True
    prebuilt_today = load_today()
    if prebuilt_today is not None and not refresh:
        st.session_state.edition = prebuilt_today
        st.caption(f"已載入今日預產報紙（{prebuilt_today['issued']:%H:%M} 產出）。按「更新本期 ↻」可取得最新報導。")
    elif not names:
        st.warning("請至少選擇一個版組，再更新本期。")
    else:
        with st.spinner("正在取得新聞原文，整理正文並編排本期報紙…"):
            try:
                ids = [s["id"] for s in SECTIONS if s["name"] in names]
                sections, total = collect(ids, per_section=count)
                if not total:
                    st.warning("目前無法取得新聞。請稍後按「更新本期」重試；已有的報紙會保留。")
                else:
                    progress = st.progress(0, text="正在讀取各篇正文…")
                    try:
                        sections = enrich_sections(sections, fetch_fn=cached_article,
                            progress=lambda done, total: progress.progress(done / total, text=f"已整理 {done} / {total} 篇原文"))
                    finally:
                        progress.empty()
                    if any(s["id"].startswith("en_") for s in sections):
                        with st.spinner("正在翻譯英文版組為繁體中文…"):
                            progress = st.progress(0, text="正在翻譯…")
                            try:
                                sections = translate_sections(sections,
                                    progress=lambda done, total: progress.progress(done / total, text=f"已翻譯 {done} / {total} 篇英文報導"))
                            finally:
                                progress.empty()
                    issued = datetime.now(TPE)
                    st.session_state.edition = {"sections": sections, "total": total, "issued": issued}
                    st.session_state.pdf_bytes = None
                    clear_filters()
            except Exception:
                logging.exception("News refresh failed")
                st.error("更新暫時失敗，請稍後重試。你正在閱讀的報紙已保留。")
edition = st.session_state.edition
if edition:
    sections, issued = edition["sections"], edition["issued"]
    st.markdown(f'<div class="edition-line"><span>本期收錄 <b>{edition["total"]:02d}</b> 則新聞</span><span>{issued:%m.%d %H:%M} 更新 · 臺北</span></div>', unsafe_allow_html=True)
    empty = [s["name"] for s in sections if not s["items"]]
    ready = sum(bool(it.get("paragraphs")) for s in sections for it in s["items"])
    if ready < edition["total"]:
        st.caption(f"已收錄 {ready} 篇正文；另有 {edition['total'] - ready} 篇暫時無法讀取，於版面標示原因。")
    if empty:
        st.warning(f"{'、'.join(empty)}版暫無新聞，其他版組仍可閱讀。可稍後更新重試。")
    translations = translation_summary(sections)
    if translations["missing"]:
        reasons = "、".join(ERROR_LABELS.get(code, "翻譯服務暫時無法使用") for code in translations["errors"])
        st.warning(f"有 {translations['missing']} 篇英文報導的中文註解尚未完整。"
                   + (f"原因：{reasons}。" if reasons else "本期資料尚未包含完整譯文。")
                   + "英文原文與已完成的譯文仍可閱讀。")
        if st.button("重試缺少的中文註解"):
            with st.spinner("正在補齊中文註解，保留已完成的譯文…"):
                st.session_state.edition = {**edition, "sections": translate_sections(sections)}
                st.session_state.pdf_bytes = None
            st.rerun()
    options = ["全部"] + [s["name"] for s in sections]
    if st.session_state.get("category") not in options:
        st.session_state.category = "全部"
    category = st.pills("閱讀版組", options, key="category", on_change=reset_page, label_visibility="collapsed") or "全部"
    with st.expander("閱讀工具 · 搜尋、字級與下載"):
        query = st.text_input("搜尋本期", placeholder="搜尋標題、來源或內文…", key="query", on_change=reset_page)
        large = st.toggle("放大字級")
        bilingual = st.toggle("英文雙語（繁中對照）", value=True)
        make_pdf = st.button("匯出本期 PDF ↓")
    if make_pdf and st.session_state.pdf_bytes is None:
        with st.spinner("正在製作適合列印的報紙…"):
            try:
                from pdf import pdf_bytes
                st.session_state.pdf_bytes = pdf_bytes(build_html("每日新聞", sections, issued))
            except Exception:
                logging.exception("PDF export failed")
                st.error("PDF 暫時無法產生，請稍後重試。你仍可在網頁閱讀本期所有新聞。")
    if st.session_state.pdf_bytes is not None:
        st.download_button("下載已製作的本期 PDF", st.session_state.pdf_bytes, file_name=f"每日新聞-{issued:%Y-%m-%d}.pdf", mime="application/pdf")
        st.caption("PDF 包含本期全部收錄內容，不受閱讀分類與搜尋影響。")
    term = query.strip().casefold()
    filtered = [{**s, "items": [it for it in s["items"] if term in (it["title"] + " " + it["source"] + " " + "\n".join(it.get("paragraphs", []))).casefold()]} for s in sections if category == "全部" or category == s["name"]]
    shown = sum(len(s["items"]) for s in filtered)
    if query.strip() or category != "全部":
        st.caption(f"顯示 {shown} 則 · {category}")
        st.button("清除閱讀篩選", on_click=clear_filters)
    if shown:
        pages = paginate_sections(filtered)
        st.session_state.paper_page = min(st.session_state.paper_page, len(pages) - 1)
        page = st.session_state.paper_page
        previous, position, following = st.columns([1, 2, 1], vertical_alignment="center")
        previous.button("← 上一版", disabled=page == 0, on_click=turn_page, args=(-1,), use_container_width=True)
        position.markdown(f'<div style="text-align:center;font-size:14px">{pages[page]["name"]}版　·　第 {page + 1} / {len(pages)} 版</div>', unsafe_allow_html=True)
        following.button("下一版 →", disabled=page == len(pages) - 1, on_click=turn_page, args=(1,), use_container_width=True)
        st.markdown(reader_html([pages[page]], large=large, bilingual=bilingual), unsafe_allow_html=True)
        st.caption(f"第 {page + 1} 版完 · 每篇保留擷取到的全部正文段落")
        st.button("繼續讀下一版 →", disabled=page == len(pages) - 1, on_click=turn_page, args=(1,))
    else:
        st.info("沒有符合條件的新聞。試試其他關鍵字，或清除閱讀篩選。")
else:
    st.markdown('<div class="welcome"><span class="eyebrow">YOUR DAILY READING RITUAL</span><h2>今天的世界，等你翻開。</h2><p>選好你關心的版組，按「更新本期」開始閱讀。</p></div>', unsafe_allow_html=True)
st.markdown('<footer class="paper-footer"><strong>每日新聞 <small>THE DAILY PRESS</small></strong><span>閱讀，讓世界更近一點。</span><p>公開報導文字重新排版，非新聞原創媒體。保留作者與來源；內容版權屬原媒體。自動擷取的內容可能不完整。</p></footer>', unsafe_allow_html=True)
