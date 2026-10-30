# 排程修改：每日 US Market Wrap 與整合說明（2026-10-30）

兩個排程各改一處。規格在 `docs/us-wrap-spec.md`，範例在 `data/us_wrap/2026-10-29.md`。

## A. us-movers-markets-wrap（台北 08:50，trig_01PDV6ZvjuKyYSk6MkUJ1nxB）

到 https://claude.ai/code/routines/trig_01PDV6ZvjuKyYSk6MkUJ1nxB 編輯提示詞：

### ① 第一段改成
```
把 Bloomberg Markets Wrap 整理成中文，加到「美股漲跌榜」儀表板「重點新聞」分頁的首條、用它重寫當日導讀，並以頂尖外資交易員兼分析師的視角撰寫「US Market Wrap」完整報導（權值個股分頁、個股列表之後）與「今日市場整合說明」。桌面版 Artifact https://claude.ai/artifact/AbipxHhDsuLPwTmcFKkUGa、手機版 Artifact https://claude.ai/artifact/RyhY6fZo928B1SzZzqjZKL。全程以繁體中文回報。不要寄信、不要改郵件、不要改 scripts/ 底下任何檔案。
```

### ② 在「## 3. 用 wrap 整合重寫導讀」整節之後、「## 4. 產頁與發佈」之前，插入
```
## 3b. 撰寫 US Market Wrap 完整報導（這一步由你親自完成，不可省略）
先完整讀 `docs/us-wrap-spec.md`（寫作規格），再讀範例 `data/us_wrap/2026-10-29.md`。
事實底：第 1 步的 Bloomberg wrap 全文＋data/days.json 當日四封漲跌榜導讀與歸因＋data/key_news.json 當日 items（含盤後財報）＋data/megacap_notes.json 當日個股核心新聞＋data/intraday_turns.json 當日盤中轉折＋data/macro.json、data/megacaps.json 收盤值。不足的依規格第一節用 WebSearch 補（standard 模式、同一回合平行送出，至多兩輪；查盤後財報可用 extended）。
依規格第三節版型寫成 `data/us_wrap/{D}.md`（覆寫同日檔；其他日期的檔不動）。目標是深度、廣度與重點掌握都超過 Bloomberg Markets Wrap。版權規則同第 2 步。

## 3c. 重寫今日市場整合說明
依規格第六節，重寫 data/megacap_notes.json 的 D 日 `_summary`（h、b 以 "\n" 分 4–5 段、k 4–6 條核心重點與盯盤、s 來源），整合 US Market Wrap、重點新聞與四封漲跌榜；數字與 wrap 一致。D 日其他 29 項與其他日期一律不動。
驗證：megacap_notes.json 可讀、D 日 `_summary` 有 h、b、k；data/us_wrap/{D}.md 存在且含「**重點**」「**記分板速覽**」「**市場在等什麼**」「**企業焦點**」「**主要市場變動**」小標。依規格第七節自檢一遍。
```

### ③ 「## 4. 產頁與發佈」第 2 點的「除 NEWS 外」改成
```
除 NEWS、NOTES 與 USWRAP 的 D 日外
```

### ④ 「## 5. 提交」的檔案清單改成
```
把 data/key_news.json、data/megacap_notes.json、data/us_wrap/、out/us-movers.html、out/us-movers-mobile.html 提交到 main 並推送，訊息「YYYY-MM-DD Markets Wrap＋US Market Wrap」
```

### ⑤ 「## 6. 回報」加一句
```
US Market Wrap 標題與重點三條、整合說明標題、具名觀點是否缺件。
```

## B. us-movers-dashboard（台北 07:20，trig_01MEmjQPQuYzfdfM1Bf7qpRr）

07:20 時當日 wrap 還沒寫，build.py 會列出「{日期}: 無 US Market Wrap」。在「閘門」的 problems 那一行後面加一句：
```
「無 US Market Wrap」由 08:50 排程補寫，屬正常，不必處理、不擋發佈。
```
