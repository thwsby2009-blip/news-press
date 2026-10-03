import copy
import io
import json
import unittest
import sys
import types
from urllib.error import HTTPError
from unittest.mock import patch

import news_translation as translate

class TranslationRecovery(unittest.TestCase):
    def test_app_starts_with_stale_translate_module(self):
        from datetime import datetime
        from news import TPE
        from streamlit.testing.v1 import AppTest
        stale = types.ModuleType("translate")
        stale.translate_sections = lambda sections: sections
        edition = {"issued": datetime.now(TPE), "total": 1, "sections": [
            {"id": "en_top", "name": "英文·頭條", "items": [
                {**self.item(), "source": "Test", "link": "https://example.com"}]}]}
        # 模擬舊版只有 translate_sections，缺少新版的 summary 與 labels。
        with patch.dict(sys.modules, {"translate": stale}), patch("prebuilt.load_today", return_value=edition), patch("news.collect") as collect:
            app = AppTest.from_file("../app.py").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)
        self.assertTrue(any(b.label == "重試缺少的中文註解" for b in app.button))
        collect.assert_not_called()

    def item(self):
        return {"title": "A report", "paragraphs": ["First paragraph", "Second paragraph"],
                "paragraphs_zh": ["第一段", ""], "title_zh": "報導"}

    def test_retry_only_missing_preserves_original_and_does_not_mutate_input(self):
        sections = [{"id": "en_top", "items": [self.item()]}]
        before = copy.deepcopy(sections)
        with patch("news_translation._gtx", return_value="第二段") as api:
            result = translate.translate_sections(sections)
        api.assert_called_once_with("Second paragraph", "en", "zh-TW")
        self.assertEqual(sections, before)
        self.assertEqual(result[0]["items"][0]["paragraphs_zh"], ["第一段", "第二段"])
        self.assertEqual(translate.translation_summary(result)["missing"], 0)

    def test_rate_limit_is_visible_and_stops_article(self):
        item = {"title": "Title", "paragraphs": ["A", "B", "C"]}
        error = HTTPError("https://example.com", 429, "limited", {}, None)
        with patch("news_translation._gtx", side_effect=error) as api, \
             patch("news_translation._mymemory", side_effect=error) as mm:
            result = translate.translate_item(item)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(mm.call_count, 1)
        self.assertEqual(result["translation_errors"], ["rate_limited"])
        self.assertEqual(result["translation_status"], "unavailable")

    def test_empty_translation_is_not_cached(self):
        translate._gtx.cache_clear()
        translate._mymemory.cache_clear()
        self.addCleanup(translate._gtx.cache_clear)
        self.addCleanup(translate._mymemory.cache_clear)
        def response():
            return io.BytesIO(json.dumps([[[""]]]).encode())
        with patch("news_translation.urllib.request.urlopen", side_effect=lambda *a, **k: response()) as api:
            # gtx 回空 → ValueError → 備援 MyMemory 也回空 → 兩後端各呼叫 2 次
            self.assertEqual(translate.to_zh("A new paragraph"), "")
            self.assertEqual(translate.to_zh("A new paragraph"), "")
            self.assertEqual(api.call_count, 4)

    def test_prebuilt_without_translations_reports_missing(self):
        self.assertEqual(translate.translation_summary([{"id":"en_top", "items":[{"title":"A", "paragraphs":["B"]}]}])["missing"], 1)

    def test_successful_translation_is_cached(self):
        translate._gtx.cache_clear()
        self.addCleanup(translate._gtx.cache_clear)
        with patch("news_translation.urllib.request.urlopen", side_effect=lambda *a, **k: io.BytesIO(json.dumps([[["成功譯文"]]]).encode())) as api:
            self.assertEqual(translate.to_zh("A new paragraph"), "成功譯文")
            self.assertEqual(translate.to_zh("A new paragraph"), "成功譯文")
            self.assertEqual(api.call_count, 1)

    def test_gtx_blocked_falls_back_to_mymemory(self):
        translate._gtx.cache_clear()
        translate._mymemory.cache_clear()
        self.addCleanup(translate._gtx.cache_clear)
        self.addCleanup(translate._mymemory.cache_clear)
        blocked = HTTPError("https://translate.googleapis.com", 403, "forbidden", {}, None)
        with patch("news_translation._gtx", side_effect=blocked), \
             patch("news_translation._mymemory", return_value="備援譯文") as mm:
            value, error = translate._translate("A paragraph to translate")
        self.assertIsNone(error)
        self.assertEqual(value, "備援譯文")
        mm.assert_called_once_with("A paragraph to translate", "zh-TW")
    def test_both_backends_failing_reports_reason(self):
        translate._gtx.cache_clear()
        translate._mymemory.cache_clear()
        self.addCleanup(translate._gtx.cache_clear)
        self.addCleanup(translate._mymemory.cache_clear)
        blocked = HTTPError("https://translate.googleapis.com", 403, "forbidden", {}, None)
        with patch("news_translation._gtx", side_effect=blocked), \
             patch("news_translation._mymemory", side_effect=blocked):
            value, error = translate._translate("A paragraph to translate")
        self.assertEqual(value, "")
        self.assertEqual(error, "blocked")
    def test_prebuilt_retry_updates_display_without_refetch(self):
        from datetime import datetime
        from news import TPE
        from streamlit.testing.v1 import AppTest
        edition = {"issued":datetime.now(TPE), "total":1, "sections":[{"id":"en_top", "name":"英文·頭條", "items":[{**self.item(), "source":"Test", "link":"https://example.com"}]}]}
        with patch("prebuilt.load_today", return_value=edition), patch("news.collect") as collect, patch("news_translation._gtx", return_value="第二段") as api:
            app = AppTest.from_file("../app.py").run()
            self.assertTrue(app.warning)
            next(b for b in app.button if b.label == "重試缺少的中文註解").click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.warning)
            self.assertEqual(collect.call_count, 0)
            self.assertEqual(api.call_count, 1)

if __name__ == "__main__":
    unittest.main()
