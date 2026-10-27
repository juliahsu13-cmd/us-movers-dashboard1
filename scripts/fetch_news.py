"""權值個股每日候選新聞（英文原文），寫入 data/news.json。

來源：Google 新聞 RSS（英文、美國版），以「公司名 stock」查詢，只留「前一交易日美股收盤 ~ 當日美東晚上」之間發布的新聞，
每檔每日取前 8 則（Google 依相關度排序），去掉重複標題。已抓過的日期不重抓；最新兩個交易日每次重抓以補進晚到的新聞。
這些只是候選：每日排程由 Claude 從中挑出當天影響股價的核心新聞，寫成中文重點存進 data/megacap_notes.json，頁面只顯示中文重點。
用法：py -I scripts/fetch_news.py <專案根目錄> [最多回補天數，預設 2]
"""
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

# 英文查詢詞：公司名＋stock，偏向市場與財經報導
QUERY = {
    "NVDA": "Nvidia stock", "TSM": "TSMC stock", "MSFT": "Microsoft stock", "AAPL": "Apple stock",
    "GOOGL": "Alphabet Google stock", "AMZN": "Amazon stock", "META": "Meta Platforms stock", "TSLA": "Tesla stock",
    "AVGO": "Broadcom stock", "AMD": "AMD stock", "ORCL": "Oracle stock", "INTC": "Intel stock",
    "SMCI": "Super Micro Computer stock", "DELL": "Dell stock", "HPQ": "HP Inc stock", "QCOM": "Qualcomm stock",
    "SWKS": "Skyworks stock", "MU": "Micron stock", "STX": "Seagate stock", "ON": "ON Semiconductor stock",
    "MRVL": "Marvell stock", "COHR": "Coherent stock", "LITE": "Lumentum stock",
}
# 油價、美元、美債：鍵名與 data/macro.json 相同（利差與 10 年期共用債市新聞）
MACRO_QUERY = {
    "brent": "Brent crude oil prices", "wti": "WTI crude oil futures settle",
    "dxy": "dollar index forex", "us10y": "Treasury yields 10-year note", "us2y": "two-year Treasury yield Fed",
}
PER_DAY = 8


def rss(q, start, end):
    query = f"{q} after:{start:%Y-%m-%d} before:{(end + timedelta(days=1)):%Y-%m-%d}"
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + "&hl=en-US&gl=US&ceid=US:en")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
        root = ET.fromstring(r.read())
    for it in root.iter("item"):
        yield (it.findtext("title") or "", it.findtext("source") or "", it.findtext("link") or "",
               parsedate_to_datetime(it.findtext("pubDate")))


def window(day, prev_day):
    """前一交易日 16:00 美東（約 20:00 UTC）到當日 20:00 美東（約隔日 00:00 UTC）。"""
    d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    p = datetime.strptime(prev_day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return p + timedelta(hours=20), d + timedelta(hours=24)


def main(root, back=2):
    root = Path(root)
    path = root / "data" / "news.json"
    store = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    names = json.loads((root / "data" / "megacap_names.json").read_text(encoding="utf-8"))
    # 交易日取郵件日期，加上盤中走勢已有 SPX 的日期（GitHub Actions 在郵件寄出前就先抓）
    ipath = root / "data" / "intraday.json"
    intra = json.loads(ipath.read_text(encoding="utf-8")) if ipath.exists() else {}
    days = sorted({f.name[:10] for f in (root / "data" / "mail").glob("*.md")}
                  | {d for d, v in intra.items() if "SPX" in v})[-back:]
    refresh = set(days[-2:])
    log, fetched = [], 0
    for i, day in enumerate(days):
        # 先前整天下載失敗（每項都空）的日期也重抓
        if day in store and day not in refresh and any(store[day].values()):
            continue
        prev = days[i - 1] if i else (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        lo, hi = window(day, prev)
        out = {}
        targets = {**{t: QUERY.get(t, f"{t} stock") for t in names}, **MACRO_QUERY}
        for t, q in targets.items():
            try:
                items, seen = [], set()
                for title, src, link, ts in rss(q, lo, hi):
                    head = title.rsplit(" - ", 1)[0].strip()
                    if not (lo <= ts <= hi) or head in seen:
                        continue
                    seen.add(head)
                    items.append({"t": head, "s": src, "u": link, "ts": ts.strftime("%Y-%m-%dT%H:%MZ")})
                    if len(items) >= PER_DAY:
                        break
                out[t] = items
                fetched += 1
            except Exception as e:  # 單檔失敗保留舊資料
                log.append(f"{day} {t} 新聞下載失敗：{e}")
                out[t] = store.get(day, {}).get(t, [])
            time.sleep(0.4)  # 放慢節奏，避免被 Google 限流
        store[day] = out
    path.write_text(json.dumps(store, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    latest = max(store)
    empty = [t for t, v in store[latest].items() if not v]
    log.append(f"抓取 {fetched} 次；最新 {latest}：{sum(len(v) for v in store[latest].values())} 則"
               + (f"，無新聞：{'、'.join(empty)}" if empty else ""))
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1],
         int(sys.argv[2]) if len(sys.argv) > 2 else 2)
