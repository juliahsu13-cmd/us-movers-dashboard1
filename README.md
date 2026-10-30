# 美股漲跌榜儀表板

每日 SPX／NDX／SOX／INDU 漲跌榜、權值個股、油價美元美債與中文核心新聞的儀表板。
發佈位置：https://claude.ai/artifact/AbipxHhDsuLPwTmcFKkUGa

## 資料流

| 步驟 | 指令 | 產出 |
|---|---|---|
| 收郵件（Claude 用 Gmail 連接器） | — | `data/mail/YYYY-MM-DD_{SPX,NDX,SOX,INDU}.md` |
| 盤中走勢 | `python3 scripts/fetch_intraday.py .` | `data/intraday.json` |
| 油價、美元、美債 | `python3 scripts/fetch_macro.py .` | `data/macro.json` |
| 權值個股報價 | `python3 scripts/fetch_megacaps.py .` | `data/megacaps.json`、`data/megacap_names.json` |
| 英文候選新聞 | `python3 scripts/fetch_news.py .` | `data/news.json` |
| 盤中市場新聞（標題＋美東時間，供轉折標註對照） | `python3 scripts/fetch_market_news.py .` | `data/market_news.json` |
| 中文核心新聞與整合說明（Claude 撰寫） | — | `data/megacap_notes.json` |
| US Market Wrap（Claude 撰寫，規格見 `docs/us-wrap-spec.md`；權值個股分頁、個股列表之後） | — | `data/us_wrap/YYYY-MM-DD.md` |
| 產頁 | `python3 scripts/build.py .` | `out/us-movers.html`、`data/summary.json` |

雲端 Claude 排程的網路政策擋下 Yahoo、美國財政部與 Google 新聞，所以五支 fetch 腳本改由 GitHub Actions（`.github/workflows/fetch-data.yml`）在週一到週五 22:20 UTC 執行，抓好的 `data/*.json` 直接提交回 main；每日排程開頭先 `git pull origin main` 取得這些資料。需要補抓時，可在 Actions 頁面手動執行「抓取市場資料」。

所有 Python 腳本只用標準函式庫；`fetch_megacaps.py` 在本機會讀 `bloomberg data.xlsb` 決定個股清單（需 `pyxlsb`），讀不到時沿用程式內建的 23 檔清單。

報價一律用收盤價：頁面只列出有收盤後漲跌榜郵件的交易日。
