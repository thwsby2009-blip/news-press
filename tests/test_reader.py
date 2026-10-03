import os
import tempfile
import unittest
from datetime import datetime
from html.parser import HTMLParser
from unittest.mock import patch

from news import TPE, collect
from render import build_html
from ui import article_html

def fixture():
    return [{"id": ident, "name": name, "items": [
        {"title": f"{name}新聞第{i}則：城市與世界的新觀察", "source": "測試來源", "time": "08:30", "link": f"https://example.com/{ident}/{i}", "paragraphs": [f"正文識別碼{ident}{i}。這是測試用文章段落。"], "content_status": "ready"}
        for i in range(10)]} for ident, name in [("top", "頭條"), ("tech", "科技")]]

class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs)["href"])

class Rendering(unittest.TestCase):
    def test_every_article_once_including_last_headlines(self):
        data = fixture()
        html = build_html("報紙", data, datetime(2026, 1, 2, tzinfo=TPE))
        links = Links(html).links
        self.assertCountEqual(links, [it["link"] for s in data for it in s["items"]])
        self.assertIn("民國115年1月2日", html)
        self.assertEqual(len(Links(build_html("報紙", data[1:])).links), 10)
    def test_untrusted_feed_content(self):
        html = article_html({"title": '<script>alert(1)</script>', "source": '<img>', "time": '<svg>', "link": 'javascript:alert(1)'})
        self.assertNotIn('<script>', html)
        self.assertNotIn('<svg>', html)
        self.assertEqual(Links(html).links, [])
    def test_unused_items_do_not_hide_later_sections(self):
        def fetch(url):
            return [{"title": str(i), "link": "https://example.com", "source": "", "time": ""} for i in range(4)]
        sections, total = collect(["top", "tech"], per_section=2, fetch_fn=fetch)
        self.assertEqual(total, 4)
        self.assertEqual([it["title"] for it in sections[1]["items"]], ["2", "3"])

class AppFlows(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.mock = patch("news.collect", return_value=(fixture(), 20)).start()
        patch("articles.enrich_sections", side_effect=lambda sections, **kwargs: sections).start()
        patch("prebuilt.load_today", return_value=None).start()
        self.addCleanup(patch.stopall)
        self.app = AppTest.from_file("../app.py").run(timeout=15)
        self.assertEqual(len(self.app.exception), 0)
    def button(self, label):
        return next(b for b in self.app.button if b.label == label)
    def test_search_reset_and_font_do_not_refetch(self):
        self.app.text_input[0].set_value("找不到這個詞").run()
        self.assertTrue(self.app.info)
        self.button("清除閱讀篩選").click().run()
        self.assertEqual(self.app.text_input[0].value, "")
        self.app.toggle[0].set_value(True).run()
        self.assertTrue(any('newspaper large-type' in m.value for m in self.app.markdown))
        self.assertEqual(self.mock.call_count, 1)
        self.assertFalse(self.app.exception)
    def test_select_all_callback_and_empty_refresh(self):
        self.app.multiselect[0].set_value([]).run()
        self.button("更新本期 ↻").click().run()
        self.assertTrue(self.app.warning)
        self.assertEqual(self.mock.call_count, 1)
        self.button("選取全部版組").click().run()
        self.assertEqual(len(self.app.multiselect[0].value), 10)
        self.assertFalse(self.app.exception)
    def test_category_filter(self):
        self.app.get("button_group")[0].set_value("科技").run()
        self.assertFalse(self.app.exception)
        reader = next(m.value for m in self.app.markdown if '<main class="reader' in m.value)
        self.assertEqual(len(Links(reader).links), 2)
        self.assertNotIn("頭條新聞", reader)
        self.assertEqual(self.mock.call_count, 1)
    def test_failed_refresh_keeps_edition(self):
        previous = self.app.session_state["edition"]
        self.mock.return_value = ([], 0)
        self.button("更新本期 ↻").click().run()
        self.assertEqual(self.app.session_state["edition"], previous)
        self.assertTrue(self.app.warning)
    def test_pdf_is_lazy_cached_and_reset_on_refresh(self):
        with patch("pdf.pdf_bytes", return_value=b"%PDF-test") as pdf:
            self.assertIsNone(self.app.session_state["pdf_bytes"])
            self.button("匯出本期 PDF ↓").click().run()
            self.app.text_input[0].set_value("科技").run()
            self.button("匯出本期 PDF ↓").click().run()
            self.assertEqual(pdf.call_count, 1)
            self.button("更新本期 ↻").click().run()
            self.assertIsNone(self.app.session_state["pdf_bytes"])
            self.assertFalse(self.app.exception)
    def test_pdf_failure_keeps_reader(self):
        with patch("pdf.pdf_bytes", side_effect=RuntimeError("missing library")):
            self.button("匯出本期 PDF ↓").click().run()
        self.assertTrue(self.app.error)
        self.assertFalse(self.app.exception)
        self.assertTrue(any('<main class="reader newspaper' in m.value for m in self.app.markdown))
    def test_turn_pages_and_search_body(self):
        self.button("下一版 →").click().run()
        self.assertEqual(self.app.session_state["paper_page"], 1)
        self.app.text_input[0].set_value("正文識別碼tech9").run()
        self.assertEqual(self.app.session_state["paper_page"], 0)
        reader = next(m.value for m in self.app.markdown if '<main class="reader' in m.value)
        self.assertIn("正文識別碼tech9", reader)
        self.assertNotIn("正文識別碼tech8", reader)
        self.assertEqual(self.mock.call_count, 1)

class Prebuilt(unittest.TestCase):
    def _edition(self):
        sections, total = collect(["top"], per_section=2, fetch_fn=lambda url: [
            {"title": "預產測試", "link": "https://example.com/pre", "source": "", "time": ""}])
        for s in sections:
            for it in s["items"]:
                it.update({"paragraphs": ["預產正文。"], "content_status": "ready"})
        return {"sections": sections, "total": total,
                "issued": datetime.now(TPE), "prebuilt": True}
    def test_load_today_missing_or_broken_returns_none(self):
        import prebuilt
        with patch("prebuilt.daily_path", return_value="/nonexistent/daily-x.json"):
            self.assertIsNone(prebuilt.load_today())
    def test_load_today_roundtrip_and_app_prefers_prebuilt(self):
        import json as json_mod
        import prebuilt
        edition = self._edition()
        with patch("prebuilt.daily_path") as p:
            p.return_value = os.path.join(tempfile.mkdtemp(), "daily-test.json")
            with open(p.return_value, "w", encoding="utf-8") as f:
                json_mod.dump({"issued": edition["issued"].isoformat(),
                               "total": edition["total"], "sections": edition["sections"]}, f, ensure_ascii=False)
            loaded = prebuilt.load_today()
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["total"], edition["total"])
            self.assertTrue(loaded["prebuilt"])
            self.assertEqual(loaded["sections"][0]["items"][0]["title"], "預產測試")
            from streamlit.testing.v1 import AppTest
            with patch("news.collect", return_value=(loaded["sections"], loaded["total"])) as mock:
                with patch("articles.enrich_sections", side_effect=lambda sections, **kw: sections):
                    with patch("prebuilt.load_today", return_value=loaded):
                        app = AppTest.from_file("../app.py").run(timeout=15)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(mock.call_count, 0)  # 預產檔存在：開啟不重抓
            self.assertEqual(app.session_state["edition"]["total"], loaded["total"])
            self.assertTrue(any("預產" in m.value for m in app.caption))

class Bilingual(unittest.TestCase):
    def _en_item(self):
        return {"title": "UK diesel price hits all time high", "source": "BBC 新聞", "time": "08:30",
                "link": "https://www.bbc.com/news/1", "paragraphs": [
                    "The United Kingdom diesel price reached a record level this week after new sanctions took effect, and drivers across the country faced higher costs at the pump.",
                    "Ministers said the measures were necessary, but motoring groups warned that households would feel the pressure for months to come."],
                "content_status": "ready",
                "paragraphs_zh": ["英國柴油價格本週在新制裁生效後達到創紀錄水準，全國駕駛人在加油站面臨更高成本。",
                                  "部長們表示這些措施是必要的，但汽車團體警告家庭將在未來幾個月感受到壓力。"],
                "title_zh": "英國柴油價格創歷史新高"}
    def test_bilingual_render_and_toggle_off(self):
        from ui import article_html
        item = self._en_item()
        html = article_html(item, bilingual=True)
        self.assertIn('class="zh-line"', html)
        self.assertIn("英國柴油價格本週", html)
        self.assertIn("The United Kingdom diesel price", html)
        self.assertIn("譯：英國柴油價格創歷史新高", html)
        plain = article_html(item, bilingual=False)
        self.assertNotIn("zh-line", plain)
        self.assertIn("The United Kingdom diesel price", plain)
    def test_translation_failure_falls_back_to_english_only(self):
        import news_translation as translate
        item = self._en_item()
        del item["paragraphs_zh"]
        del item["title_zh"]
        with patch("news_translation._gtx", side_effect=RuntimeError("network down")), \
             patch("news_translation._mymemory", side_effect=RuntimeError("network down")):
            result = translate.translate_item(item)
        self.assertNotIn("paragraphs_zh", result)
        self.assertEqual(result["paragraphs"][0][:10], "The United")
    def test_translate_sections_only_english(self):
        import news_translation as translate
        sections = [{"id": "top", "name": "頭條", "items": [dict(self._en_item())]},
                    {"id": "en_top", "name": "英文·頭條", "items": [dict(self._en_item())]}]
        for s in sections:
            for it in s["items"]:
                it.pop("paragraphs_zh", None)
                it.pop("title_zh", None)
        with patch("news_translation._gtx", return_value="繁中譯文"), \
             patch("news_translation._mymemory", return_value="") as mm:
            result = translate.translate_sections(sections)
        # 中文版組的項目不送翻譯：只翻 en_ 版組的 1 篇（2 段＋標題）；gtx 全成功，備援不被呼叫
        self.assertEqual(mm.call_count, 0)
        self.assertIsNone(result[0]["items"][0].get("paragraphs_zh"))

if __name__ == "__main__":
    unittest.main()
