"""權值個股每日收盤與漲跌幅，寫入 data/megacaps.json。

報價與漲跌幅一律取網路即時報價（Yahoo Finance 日線），因為 bloomberg data.xlsb 不會即時更新。
bloomberg data.xlsb 只用來決定「追蹤哪些個股」：讀「SPX PRICE」分頁第 4 列的代號（「NVDA US Equity」這類），
去掉指數與 ETF，得到個股清單；母檔新增或刪除個股，這裡會自動跟著變。讀不到母檔時沿用 STOCKS 的預設清單。
用法：py -I scripts/fetch_megacaps.py <專案根目錄>
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

XLSB = [Path(r"\\SHUYE07\fileserver\書業(新)\Julia\0更新捷徑\bloomberg data.xlsb"),
        Path(r"C:\Claude 臨時讀取\更新捷徑自動更新檔\bloomberg data.xlsb")]
SKIP = {"SPY"}  # 母檔裡的 ETF，不算個股

# 代號 → (中文名, 族群)；母檔出現新代號而此處沒有時，頁面先顯示代號
STOCKS = {
    "NVDA": ("輝達", "AI 運算"), "TSM": ("台積電 ADR", "晶圓代工"), "MSFT": ("微軟", "雲端平台"),
    "AAPL": ("蘋果", "消費電子"), "GOOGL": ("Alphabet", "雲端平台"), "AMZN": ("亞馬遜", "雲端平台"),
    "META": ("Meta", "雲端平台"), "TSLA": ("特斯拉", "電動車"), "AVGO": ("博通", "AI 運算"),
    "AMD": ("超微", "AI 運算"), "ORCL": ("甲骨文", "雲端平台"), "INTC": ("英特爾", "CPU／代工"),
    "SMCI": ("美超微", "AI 伺服器"), "DELL": ("戴爾", "AI 伺服器"), "HPQ": ("惠普", "PC"),
    "QCOM": ("高通", "手機晶片"), "SWKS": ("思佳訊", "手機晶片"), "MU": ("美光", "記憶體"),
    "STX": ("希捷", "儲存"), "ON": ("安森美", "車用功率"), "MRVL": ("邁威爾", "AI 互連"),
    "COHR": ("高意", "光通訊"), "LITE": ("Lumentum", "光通訊"),
}


def tickers_from_bloomberg():
    src = max((p for p in XLSB if p.exists()), key=lambda p: p.stat().st_mtime, default=None)
    if not src:  # 雲端排程碰不到本機與網路磁碟，走這條
        return list(STOCKS), "讀不到 bloomberg data.xlsb，沿用預設清單"
    try:
        from pyxlsb import open_workbook
    except ImportError:
        return list(STOCKS), "未安裝 pyxlsb，沿用預設清單"
    with open_workbook(str(src)) as wb, wb.get_sheet("SPX PRICE") as sh:
        for i, row in enumerate(sh.rows()):
            if i == 3:
                out = [c.v.split()[0] for c in row
                       if isinstance(c.v, str) and c.v.split()[-1] == "Equity" and c.v.split()[0] not in SKIP]
                return out, f"個股清單取自 {src.name}（{len(out)} 檔）"
    return list(STOCKS), "SPX PRICE 分頁讀不到代號列，沿用預設清單"


def from_yahoo(t):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=3mo&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)["chart"]["result"][0]
    off = timedelta(seconds=res["meta"]["gmtoffset"])
    pts = [((datetime.fromtimestamp(ts, timezone.utc) + off).strftime("%Y-%m-%d"), c)
           for ts, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
    return {d: {"c": round(c, 2), "p": round((c / pts[i - 1][1] - 1) * 100, 2)}
            for i, (d, c) in enumerate(pts) if i > 0}


def main(root):
    root = Path(root)
    path = root / "data" / "megacaps.json"
    store = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    tickers, note = tickers_from_bloomberg()
    log, ok = [note], 0
    for t in tickers:
        try:
            for d, rec in from_yahoo(t).items():
                store.setdefault(d, {})[t] = rec
            ok += 1
        except Exception as e:  # 單檔失敗不擋其他檔，舊資料保留
            log.append(f"{t} 報價下載失敗：{e}")
    for d in store:  # 母檔已刪除的個股不再顯示
        store[d] = {t: v for t, v in store[d].items() if t in tickers}
    path.write_text(json.dumps(store, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    names = {t: STOCKS.get(t, (t, "")) for t in tickers}
    (root / "data" / "megacap_names.json").write_text(json.dumps(names, ensure_ascii=False), encoding="utf-8")
    latest = max(store)
    log.append(f"網路報價 {ok}/{len(tickers)} 檔成功；最新 {latest}：{len(store[latest])} 檔")
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
