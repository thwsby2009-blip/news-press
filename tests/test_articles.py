import unittest
from unittest.mock import patch
from articles import extract_article, ArticleUnavailable, public_url, enrich_sections
from ui import article_html, paginate_sections

class FullText(unittest.TestCase):
    def test_main_article_excludes_recommendations_and_escapes_output(self):
        paragraphs = [f"這是第{i}段正式報導，內容來自記者實際採訪，保留原來的段落與文字，重新編排讓讀者在報紙上直接閱讀。" * 2 for i in range(4)]
        raw = '<html><head><meta charset="utf-8"></head><body><nav>導覽</nav><article><h1>正式報導</h1>' + ''.join(f'<p>{p}</p>' for p in paragraphs) + '<p class="read-more-vendor">延伸新聞污染</p></article><aside><p>推薦其他新聞污染</p></aside></body></html>'
        result = extract_article(raw, "https://example.com/story")
        for p in paragraphs:
            self.assertIn(p, result["paragraphs"])
        self.assertNotIn("污染", "".join(result["paragraphs"]))
        result.update(title="測試標題", source="測試媒體", paragraphs=[*result["paragraphs"], '<img src=x onerror=alert(1)>'])
        rendered = article_html(result)
        self.assertNotIn('<img', rendered)
        self.assertIn('<h2>測試標題</h2>', rendered)
        self.assertIn(paragraphs[-1], rendered)
    def test_paid_content_not_extracted(self):
        raw = '<html><script type="application/ld+json">{"isAccessibleForFree":false}</script><article><p>' + '付費文章內容' * 200 + '</p></article></html>'
        with self.assertRaises(ArticleUnavailable):
            extract_article(raw, 'https://example.com/story')
    def test_short_body_is_not_passed_off_as_article(self):
        with self.assertRaises(ArticleUnavailable):
            extract_article('<article>請登入</article>', 'https://example.com/story')
    def test_bytes_with_meta_big5_decodes_and_utf8_default(self):
        # latin-1 誤判會讓「不」(UTF-8: E4 B8 8D) 變成 "ä¸"——位元組級亂碼的特徵
        utf8_bytes = '不滿罷工決定無限期罷工，這是足夠長的正文內容用來測試編碼處理是否正確，超過一百六十字元的最低門檻以避免被判定為不足，正文來自記者實際採訪與工會會員臨時投票的現場記錄，保留完整的段落與標點符號。' + '正文段落繼續延伸，確保測試通過長度檢查，並且保留完整段落不截斷，驗證位元組層級的編碼正確性，公司代表晚間召開臨時會員大會原訂的投票結果維持不變，勞資雙方後續將再進行協商。'
        raw = ('<html><head><meta charset="utf-8"></head><body><article><p>' + utf8_bytes + '</p></article></body></html>').encode('utf-8')
        result = extract_article(raw, "https://example.com/story")
        self.assertTrue(any('不滿罷工' in p for p in result["paragraphs"]))
        self.assertNotIn('ä¸', "".join(result["paragraphs"]))
    def test_private_url_rejected(self):
        with patch('articles.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaises(ArticleUnavailable):
                public_url('https://example.com/story')
    def test_failure_isolated_and_duplicates_fetched_once(self):
        sections = [{"id":"top", "name":"頭條", "items":[{"title":"A", "link":"https://example.com/ok"},{"title":"B", "link":"https://example.com/fail"},{"title":"C", "link":"https://example.com/ok"}]}]
        calls = []
        def fetch(url):
            calls.append(url)
            if url.endswith('fail'):
                raise ArticleUnavailable("暫時無法讀取")
            return {"paragraphs":["正文"], "content_status":"ready"}
        enriched = enrich_sections(sections, fetch_fn=fetch)
        self.assertEqual(len(calls), 2)
        self.assertEqual(enriched[0]['items'][1]['content_status'], 'unavailable')
        self.assertEqual(enriched[0]['items'][2]['paragraphs'], ['正文'])
        self.assertNotIn('paragraphs', sections[0]['items'][0])
        pages = paginate_sections(enriched)
        self.assertEqual([len(p['items']) for p in pages], [2, 1])

if __name__ == '__main__':
    unittest.main()
