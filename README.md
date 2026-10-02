# 每日新聞 news-press

從 Google 新聞、Yahoo 新聞 RSS 發現報導，取得原文頁面的正文文字，再重新編成能直接閱讀的報紙。不複製來源網站版型，不以摘要代替原文。

## 功能

- 六個中文版組＋四個英文版組：頭條、國際、財經、科技、影劇、體育；英文·頭條／國際／財經／科技（BBC／衛報／NPR，學習用）
- 新聞來源：Google 新聞 / Yahoo 新聞官方 RSS（zh-TW）＋ BBC／衛報／NPR 官方 RSS，跨來源自動去重
- 實體報刊式閱讀：米白紙色、襯線標題、正文分欄與上一版／下一版
- 手機單欄、平板雙欄與桌面三欄閱讀，無嵌入式捲動框
- 首次開啟自動載入；自訂版組與每個版組 3／5／10 篇新聞
- 分類、搜尋標題／來源／內文、放大字級；翻版與篩選不會重新抓取新聞
- 按需製作本期 PDF（WeasyPrint，A4 自動分頁、頁碼）；製作後可重複下載
- 來源暫時失效時保留上一期，空版組與搜尋無結果皆有提示

PDF 包含本期全部收錄新聞，不受畫面的分類或搜尋影響。更新本期後會清除舊 PDF，待需要時再製作。
網頁使用系統中文字型；伺服器列印建議安裝 `fonts-noto-cjk`。PDF 套件無法載入時不影響網頁閱讀。

每版兩篇，保留擷取到的全部段落，長文自然延展、不截斷。原文擷取限制在主報導區塊，排除選單、圖片、推薦新聞與留言。來源網址與日期保留；可取得作者欄位時一併保留。

每篇獨立處理失敗；付費牆、需登入、robots 限制或解析失敗時只顯示標題與原因，不冒充完整報導。自動抽取不保證所有網站都能成功或完整；目前沒有使用瀏覽器執行 JavaScript，也不繞過存取限制。正文成功結果在伺服器記憶體快取一小時（最多 256 篇），失敗可以重新更新重試。

## 使用

### 網頁（Streamlit）

```bash
pip install -r requirements.txt
streamlit run app.py
```

或部署到 [Streamlit Cloud](https://streamlit.io/cloud)：選 repo / branch `main` / file `app.py`。

Python 3.11+，Streamlit 1.40+。Linux 的 PDF 系統套件列於 `packages.txt`；Windows 使用 WeasyPrint 前需另行安裝其 Pango 原生相依套件。

### 驗證

```bash
python -m unittest discover -s tests -v
```

測試以模擬 RSS 驗證搜尋、重設、更新失敗、PDF 按需製作與快取，以及新聞完整性；不依賴外部新聞服務。

### 命令列

```bash
python build.py                    # 全部版組 → output/news-YYYY-M-D.pdf
python build.py --json only        # 只產生當日預產 JSON（output/daily-民國Y-M-D.json）
python build.py --html only        # 只產生 HTML 預覽
python build.py --sections top,world,biz
python build.py --out my-paper.pdf
```

每日排程預產（搭配 cron 或工作排程器跑 `--json only`）：網頁開啟時會優先載入今日預產檔（`output/daily-*.json`），無檔或非當日才即時抓取；「更新本期」永遠即時。預產檔只保留最近 7 天。

## 版組對應 RSS

| 版組 | 來源 |
|------|------|
| 頭條 | Google 新聞頭條 + Yahoo 政治 |
| 國際 | Google 新聞國際 |
| 財經 | Google 新聞財經 |
| 科技 | Google 新聞科技 + Yahoo 科技 |
| 影劇 | Google 新聞影劇 + Yahoo 影劇 |
| 體育 | Google 新聞體育 + Yahoo 體育 |
| 英文·頭條 | BBC 新聞 + NPR |
| 英文·國際 | BBC 國際 + 衛報國際 |
| 英文·財經 | BBC 財經 |
| 英文·科技 | BBC 科技 |

新增來源：編輯 `news.py` 的 `SECTIONS`，每版組可掛多個 RSS。

## 授權

MIT。新聞內容版權屬各原媒體所有，程式授權不包含第三方新聞內容的轉載授權。
