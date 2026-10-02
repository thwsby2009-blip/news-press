# 寰宇日報 news-press

把 Google 新聞、Yahoo 新聞等大網站的即時新聞，自動彙整成一份傳統報紙版面，並可匯出成 PDF。

## 功能

- 六個版組：頭條、國際、財經、科技、影劇、體育
- 新聞來源：Google 新聞 / Yahoo 新聞官方 RSS（zh-TW），跨來源自動去重
- 傳統報紙版面：報頭（民國紀元日期）、頭條放大、雙欄排版、襯線字型（Noto Serif TC）
- 一鍵匯出 PDF（WeasyPrint，A4 多頁、頁碼）

## 使用

### 網頁（Streamlit）

```bash
pip install -r requirements.txt
streamlit run app.py
```

或部署到 [Streamlit Cloud](https://streamlit.io/cloud)：選 repo / branch `main` / file `app.py`。

### 命令列

```bash
python build.py                    # 全部版組 → output/news-YYYY-M-D.pdf
python build.py --html only        # 只產生 HTML 預覽
python build.py --sections top,world,biz
python build.py --out my-paper.pdf
```

## 版組對應 RSS

| 版組 | 來源 |
|------|------|
| 頭條 | Google 新聞頭條 + Yahoo 政治 |
| 國際 | Google 新聞國際 |
| 財經 | Google 新聞財經 |
| 科技 | Google 新聞科技 + Yahoo 科技 |
| 影劇 | Google 新聞影劇 + Yahoo 影劇 |
| 體育 | Google 新聞體育 + Yahoo 體育 |

新增來源：編輯 `news.py` 的 `SECTIONS`，每版組可掛多個 RSS。

## 授權

MIT。新聞內容版權屬各原媒體所有，本工具僅做公開 RSS 彙整。
