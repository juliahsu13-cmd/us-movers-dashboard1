"""找出四大指數盤中轉折點，並列出每段走勢中漲跌最多的權值個股，供撰寫轉折標註。

讀 data/intraday.json（5 分鐘線），對指定交易日（預設最新一天）的 SPX／NDX／SOX／INDU
用 zigzag 找轉折：價格自上一個極值反向超過門檻才算轉折，門檻＝max(0.15%, 當日振幅 × 25%)。
每段走勢（轉折到下一個轉折）另算 intraday.json 裡各權值個股同時段的漲跌幅，列出領漲、領跌各 3 檔。
只印出結果，不寫檔。
用法：python3 scripts/find_turns.py <專案根目錄> [YYYY-MM-DD]
"""
import json
import sys
from pathlib import Path

INDICES = ["SPX", "NDX", "SOX", "INDU"]
MIN_TH = 0.15     # 最小反轉門檻（%）
RANGE_FRAC = 0.25  # 門檻占當日振幅的比例


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def tpe(m):  # 美東 → 台北（+12 小時，跨日）
    return hm((m + 12 * 60) % (24 * 60))


def series(x):
    return [(m, (p / x["pc"] - 1) * 100, p) for m, p in x["s"] if 570 <= m <= 960]


def zigzag(pts):
    vs = [p[1] for p in pts]
    th = max(MIN_TH, (max(vs) - min(vs)) * RANGE_FRAC)
    piv = [0]
    trend, ext = 0, 0  # trend: 1 上升段、-1 下降段；ext＝目前段落的極值索引
    for i in range(1, len(pts)):
        if trend >= 0 and vs[i] >= vs[ext] or trend <= 0 and vs[i] <= vs[ext]:
            if trend == 0 and abs(vs[i] - vs[0]) < th:
                continue
            ext = i
            trend = trend or (1 if vs[i] > vs[0] else -1)
        elif abs(vs[i] - vs[ext]) >= th:
            piv.append(ext)
            trend, ext = -trend, i
    if ext != piv[-1]:
        piv.append(ext)
    if piv[-1] != len(pts) - 1:
        piv.append(len(pts) - 1)
    return piv, th


def leg_movers(day, a, b):
    out = []
    for t, x in day.items():
        if t in INDICES:
            continue
        s = dict((m, p) for m, p in x["s"])
        pa = s.get(a) or s.get(min(s, key=lambda m: abs(m - a)))
        pb = s.get(b) or s.get(min(s, key=lambda m: abs(m - b)))
        if pa and pb:
            out.append((t, (pb / pa - 1) * 100))
    out.sort(key=lambda r: r[1], reverse=True)
    return out[:3], out[-3:][::-1]


def main(root, date=None):
    intra = json.loads((Path(root) / "data" / "intraday.json").read_text(encoding="utf-8"))
    date = date or sorted(intra)[-1]
    day = intra[date]
    print(f"交易日 {date}（時間為美東；括號內為台北）")
    for idx in INDICES:
        if idx not in day:
            print(f"\n{idx}：無盤中資料")
            continue
        pts = series(day[idx])
        piv, th = zigzag(pts)
        print(f"\n{idx}  前收 {day[idx]['pc']:,.2f}  轉折門檻 {th:.2f}%")
        for n, i in enumerate(piv):
            m, v, p = pts[i]
            kind = "開盤" if i == 0 else "收盤" if i == len(pts) - 1 else (
                "高點" if v >= pts[piv[n - 1]][1] else "低點")
            line = f"  m={m:<4} {hm(m)}（{tpe(m)}）{kind:　<2} {p:,.2f} {v:+.2f}%"
            if n + 1 < len(piv):
                m2, v2, _ = pts[piv[n + 1]]
                up, dn = leg_movers(day, m, m2)
                line += (f"  → 至 {hm(m2)} {v2 - v:+.2f} 個百分點"
                         f"｜領漲 {', '.join(f'{t} {c:+.2f}%' for t, c in up)}"
                         f"｜領跌 {', '.join(f'{t} {c:+.2f}%' for t, c in dn)}")
            print(line)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1],
         sys.argv[2] if len(sys.argv) > 2 else None)
