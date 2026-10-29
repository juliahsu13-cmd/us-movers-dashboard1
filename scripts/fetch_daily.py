"""抓四大指數、權值個股與油價美元美債的日 K（Yahoo Finance），寫入 data/daily.json。

頁面的「年初至今／240 日／480 日／自訂區間」走勢圖用這份資料。
格式：{代號: [[YYYY-MM-DD, 開, 高, 低, 收, 成交量], ...]}（殖利率、美元指數等沒有成交量，記 0），代號與 data/intraday.json 相同；
每檔保留 START 之後的日 K（自訂區間可選到 2022 年初；多留一個月，2022 年第一天才有前一日收盤當起點）。某檔下載失敗就保留檔案裡的舊資料。
用法：python3 scripts/fetch_daily.py <專案根目錄>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_intraday import MACRO, SYMBOLS, by_day, get  # noqa: E402

START = "2021-12-01"


def main(root):
    root = Path(root)
    path = root / "data" / "daily.json"
    store = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    npath = root / "data" / "megacap_names.json"
    stocks = json.loads(npath.read_text(encoding="utf-8")) if npath.exists() else {}
    log = []
    for key, sym in {**SYMBOLS, **MACRO, **{t: t for t in stocks}}.items():
        try:
            days = by_day(get(sym, "10y", "1d"), 3 if key == "us10y" else 2)
        except Exception as e:  # 單一代號失敗不擋其他代號
            log.append(f"{key}: 下載失敗 {e}")
            continue
        # 期貨同日可能有兩根（晚盤新時段），取第一根才是當日收盤
        rows = [[d, bars[0][2], bars[0][3], bars[0][4], bars[0][1], bars[0][5]] for d, bars in sorted(days.items())]
        if rows:
            store[key] = [r for r in rows if r[0] >= START]
        log.append(f"{key}: {len(rows)} 根，最新 {rows[-1][0] if rows else '無'}")
    path.write_text(json.dumps(store, separators=(",", ":")), encoding="utf-8")
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
