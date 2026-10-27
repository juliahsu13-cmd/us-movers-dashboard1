"""盤中市場新聞（英文標題＋發布時間），寫入 data/market_news.json，供撰寫盤中轉折標註時對照時間。

雲端 Claude 排程的 WebFetch 連不到 Yahoo、Reuters 等新聞網站，所以由 GitHub Actions 先把當日盤中報導的標題與發布時間抓下來。
來源：Google 新聞 RSS（英文、美國版），以大盤、油價、美債、Fed、盤中即時報導等查詢詞搜尋，
只留當日美東 04:00～20:00 發布的新聞，去掉重複標題，依時間排序；每筆附美東分鐘數 m（與 find_turns.py 的 m 相同）。
已抓過的日期不重抓；最新兩個交易日每次重抓以補進晚到的新聞。
用法：python3 scripts/fetch_market_news.py <專案根目錄> [最多回補天數，預設 2]
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_news import rss  # noqa: E402  同一個 Google 新聞 RSS 下載函式

ET = ZoneInfo("America/New_York")
# 盤中轉折常見的驅動：大盤即時報導、總經數據、公債標售、Fed、油價與地緣政治
QUERIES = [
    "stock market today", "stocks live updates Dow S&P 500 Nasdaq", "Wall Street stocks midday",
    "stocks afternoon trading", "stocks close Wall Street", "chip stocks semiconductor",
    "oil prices", "Treasury yields", "Treasury auction", "Fed officials rate",
    "economic data jobs inflation report", "Iran Middle East oil",
]
PER_QUERY = 30
MAX_PER_DAY = 150


def main(root, back=2):
    root = Path(root)
    path = root / "data" / "market_news.json"
    store = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    ipath = root / "data" / "intraday.json"
    intra = json.loads(ipath.read_text(encoding="utf-8")) if ipath.exists() else {}
    days = sorted({f.name[:10] for f in (root / "data" / "mail").glob("*.md")}
                  | {d for d, v in intra.items() if "SPX" in v})[-back:]
    refresh = set(days[-2:])
    log, fetched = [], 0
    for day in days:
        if store.get(day) and day not in refresh:
            continue
        d = datetime.strptime(day, "%Y-%m-%d")
        lo = datetime(d.year, d.month, d.day, 4, tzinfo=ET).astimezone(timezone.utc)
        hi = datetime(d.year, d.month, d.day, 20, tzinfo=ET).astimezone(timezone.utc)
        items, seen = [], set()
        for q in QUERIES:
            try:
                n = 0
                for title, src, link, ts in rss(q, lo - timedelta(days=1), hi):
                    head = title.rsplit(" - ", 1)[0].strip()
                    if not (lo <= ts <= hi) or head in seen:
                        continue
                    seen.add(head)
                    et = ts.astimezone(ET)
                    items.append({"m": et.hour * 60 + et.minute, "et": et.strftime("%H:%M"), "t": head,
                                  "s": src, "q": q, "u": link})
                    n += 1
                    if n >= PER_QUERY:
                        break
                fetched += 1
            except Exception as e:  # 單一查詢失敗不擋其他查詢
                log.append(f"{day} 「{q}」下載失敗：{e}")
            time.sleep(0.4)  # 放慢節奏，避免被 Google 限流
        if items or day not in store:
            store[day] = sorted(items, key=lambda x: x["m"])[:MAX_PER_DAY]
    path.write_text(json.dumps(store, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    latest = max(store) if store else "無"
    log.append(f"抓取 {fetched} 次；最新 {latest}：{len(store.get(latest, []))} 則")
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1],
         int(sys.argv[2]) if len(sys.argv) > 2 else 2)
