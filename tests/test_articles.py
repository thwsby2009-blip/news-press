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
