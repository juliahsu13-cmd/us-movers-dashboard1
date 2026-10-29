"""抓四大指數 5 分鐘盤中走勢（Yahoo Finance），併入 data/intraday.json。

Yahoo 5 分線只保留約 60 天，所以每次執行都把新抓到的日期併進既有檔，舊日期保留。
前一交易日收盤取自同源日線，盤中走勢一律換算成「相對前一交易日收盤的漲跌幅」。
另抓油價、美元指數、10 年期殖利率與 2 年期公債期貨（Yahoo 沒有 2 年期殖利率的盤中報價，
以期貨價格代替，價格與殖利率反向）；時間一律換成美東。
用法：py -I scripts/fetch_intraday.py <專案根目錄>
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SYMBOLS = {"SPX": "%5EGSPC", "NDX": "%5ENDX", "SOX": "%5ESOX", "INDU": "%5EDJI"}
MACRO = {"brent": "BZ%3DF", "wti": "CL%3DF", "dxy": "DX-Y.NYB", "us10y": "%5ETNX", "us2y_fut": "ZT%3DF"}
TZ_SHIFT = {"America/Chicago": 60}  # 換成美東要加的分鐘數（^TNX 以芝加哥時間計）
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval={iv}"


def get(sym, rng, iv):
    req = urllib.request.Request(URL.format(sym=sym, rng=rng, iv=iv),
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["chart"]["result"][0]


def by_day(res, nd=2):
    """回傳 {YYYY-MM-DD: [(美東分鐘數, 收盤, 開盤, 最高, 最低, 成交量), ...]}，交易所不在美東時換算成美東。
    開高低缺值時以收盤代替；成交量缺值為 0。"""
    off = timedelta(seconds=res["meta"]["gmtoffset"],
                    minutes=TZ_SHIFT.get(res["meta"].get("exchangeTimezoneName"), 0))
    q = res["indicators"]["quote"][0]
    n = len(q["close"])
    ohl = [q.get(k) or [None] * n for k in ("open", "high", "low")]
    vol = q.get("volume") or [None] * n
    out = {}
    for ts, c, o, h, lo, v in zip(res.get("timestamp") or [], q["close"], *ohl, vol):
        if c is None:
            continue
        t = datetime.fromtimestamp(ts, timezone.utc) + off
        bar = [round(v if v is not None else c, nd) for v in (c, o, h, lo)]
        out.setdefault(t.strftime("%Y-%m-%d"), []).append((t.hour * 60 + t.minute, *bar, int(v or 0)))
    return out


def main(root):
    root = Path(root)
    path = root / "data" / "intraday.json"
    store = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    log = []
    # 權值個股也抓盤中走勢（清單沿用 fetch_megacaps.py 產生的 megacap_names.json）
    npath = root / "data" / "megacap_names.json"
    stocks = json.loads(npath.read_text(encoding="utf-8")) if npath.exists() else {}
    symbols = {**SYMBOLS, **MACRO, **{t: t for t in stocks}}
    for idx, sym in symbols.items():
        try:
            nd = 3 if idx == "us10y" else 2  # 殖利率要到 0.1bp 才看得出盤中起伏
            daily = by_day(get(sym, "6mo", "1d"), nd)
            intra = by_day(get(sym, "1mo", "5m"), nd)
        except Exception as e:  # 單一指數失敗不擋其他指數
            log.append(f"{idx}: 下載失敗 {e}")
            continue
        ddays = sorted(daily)
        n = 0
        for d, pts in intra.items():
            prev = [x for x in ddays if x < d]
            if not prev or len(pts) < 2:
                continue
            pc = daily[prev[-1]][0][1]  # 期貨同日第二根是晚盤新時段，取第一根才是當日收盤
            # s＝[分鐘, 收盤]（轉折偵測與舊版頁面用）；k＝[分鐘, 開, 高, 低, 收]（K 線用）
            store.setdefault(d, {})[idx] = {"pc": pc, "s": [[m, c] for m, c, *_ in pts],
                                             "k": [[m, o, h, lo, c] for m, c, o, h, lo, _ in pts]}
            n += 1
        log.append(f"{idx}: {n} 天，最新 {max(intra) if intra else '無'}")
    path.write_text(json.dumps(store, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
