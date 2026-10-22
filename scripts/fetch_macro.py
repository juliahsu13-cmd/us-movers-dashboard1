"""油價、美元指數、美債殖利率每日收盤，寫入 data/macro.json。

全部取網路報價：
- 布蘭特原油 BZ=F、西德州原油 CL=F、美元指數 DX-Y.NYB：Yahoo Finance 日線（油價為期貨近月，換月日的漲跌幅會含價差）。
- 美國 2 年、10 年期公債殖利率：美國財政部每日公布的殖利率曲線（官方收盤值；Yahoo 的 2 年期報價不會更新，故不用）。
用法：py -I scripts/fetch_macro.py <專案根目錄>
"""
import csv
import io
import json
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
YAHOO = {"brent": "BZ=F", "wti": "CL=F", "dxy": "DX-Y.NYB"}
TREASURY = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            "daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv")


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def yahoo_daily(sym):
    res = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=6mo&interval=1d"))["chart"]["result"][0]
    off = timedelta(seconds=res["meta"]["gmtoffset"])
    out = {}
    for ts, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        d = (datetime.fromtimestamp(ts, timezone.utc) + off).strftime("%Y-%m-%d")
        if c is not None and d not in out:  # 同日第二根是盤中未收的新交易時段，略過
            out[d] = round(c, 2)
    return out


def treasury():
    out = {}
    this = date.today().year
    for y in (this - 1, this):
        for row in csv.DictReader(io.StringIO(get(TREASURY.format(y=y)).decode("utf-8-sig"))):
            d = datetime.strptime(row["Date"], "%m/%d/%Y").strftime("%Y-%m-%d")
            if row.get("2 Yr") and row.get("10 Yr"):
                out[d] = (float(row["2 Yr"]), float(row["10 Yr"]))
    return out


def with_change(series, kind):
    """series: {日期: 值} → {日期: {v, chg}}；kind=pct 算百分比，bp 把百分點換成基點，diff 直接相減（值已是基點）。"""
    days, out = sorted(series), {}
    for i, d in enumerate(days[1:], 1):
        v, prev = series[d], series[days[i - 1]]
        chg = (v / prev - 1) * 100 if kind == "pct" else (v - prev) * (100 if kind == "bp" else 1)
        out[d] = {"v": v, "chg": round(chg, 2 if kind == "pct" else 1)}
    return out


def main(root):
    root = Path(root)
    path = root / "data" / "macro.json"
    store = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    log = []
    for key, sym in YAHOO.items():
        try:
            for d, rec in with_change(yahoo_daily(sym), "pct").items():
                store.setdefault(d, {})[key] = rec
        except Exception as e:
            log.append(f"{key}（{sym}）下載失敗：{e}")
    try:
        t = treasury()
        for key, idx in (("us2y", 0), ("us10y", 1)):
            for d, rec in with_change({d: v[idx] for d, v in t.items()}, "bp").items():
                store.setdefault(d, {})[key] = rec
        sp = {d: round((v[1] - v[0]) * 100, 1) for d, v in t.items()}
        for d, rec in with_change(sp, "diff").items():
            store.setdefault(d, {})["spread"] = rec
    except Exception as e:
        log.append(f"財政部殖利率下載失敗：{e}")
    path.write_text(json.dumps(store, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    latest = max(store)
    log.append(f"最新 {latest}：{', '.join(sorted(store[latest]))}")
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
