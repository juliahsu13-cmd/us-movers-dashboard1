"""美股漲跌榜儀表板產生器。

讀 data/mail/YYYY-MM-DD_{SPX,NDX,SOX,INDU}.md（每日漲跌榜郵件的純文字版），
解析成 data/days.json，再把最近 MAX_DAYS 天塞進 template.html，輸出 out/us-movers.html，
並以同一份資料產出手機版 out/us-movers-mobile.html。
用法：py -I scripts/build.py <專案根目錄>
"""
import json
import re
import sys
from pathlib import Path

INDICES = ["SPX", "NDX", "SOX", "INDU"]
MAX_DAYS = 30

DESKTOP_URL = "https://claude.ai/artifact/AbipxHhDsuLPwTmcFKkUGa"
# 手機版＝template.html 套上這幾處替換，再在主樣式後接 scripts/mobile.css
MOBILE_PATCHES = [
    ("<title>美股漲跌榜</title>", "<title>美股漲跌榜 手機版</title>"),
    ('    <div class="controls">\n',
     '    <div class="controls">\n'
     f'      <a class="m-link" href="{DESKTOP_URL}" target="_top">完整版 ›</a>\n'),
    # 分頁在底部固定列，點了要捲到內容；圖表放大字級與邊距
    ("setTab(b.dataset.k, false))", "setTab(b.dataset.k, true))"),
    ('document.getElementById("tabs").scrollIntoView(',
     'document.getElementById(k === "MEGA" ? "mega" : "intra").scrollIntoView('),
    ("const CH = {W:720, H:240, L:46, R:12, T:12, B:26,",
     "const CH = {W:720, H:380, L:84, R:14, T:16, B:40,"),
    ("${[660, 780, 900].map(", "${[660, 780].map("),
]


def mobile_template(tpl, css):
    for old, new in MOBILE_PATCHES:
        if tpl.count(old) != 1:
            raise SystemExit(f"手機版替換點在 template.html 出現 {tpl.count(old)} 次：{old!r}")
        tpl = tpl.replace(old, new)
    return tpl.replace("</style>\n", "</style>\n<style>\n" + css + "</style>\n", 1)

NUM = r"([\d,]+\.\d+)"
PCT = r"([+\-−–]?\d+(?:\.\d+)?)%"


def to_float(s):
    return float(s.replace(",", "").replace("−", "-").replace("–", "-"))


def parse_mail(text):
    head, _, body = text.partition("\n---\n")
    meta = dict(
        (k.strip(), v.strip())
        for k, _, v in (ln.partition(":") for ln in head.splitlines() if ":" in ln)
    )
    # 有些期別小標下一行直接接表格、中間沒空行，先補空行讓表格自成一塊
    body = re.sub(r"(?m)^([^|\n][^\n]*)\n(?=\|)", r"\1\n\n", body)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body.strip()) if b.strip()]

    # 版面各期略有差異（結論句有無 *…*、小標是否寫「漲幅／跌幅」），
    # 所以以表格為錨：表格前的短段落＝結論句或小標，第一個表格之前的長段落＝導讀。
    lead, sections, note, pending = [], [], "", []
    for b in blocks:
        if b.startswith("|"):
            rows = []
            for ln in b.splitlines():
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if len(cells) < 6 or cells[0] == "代號" or set(cells[0]) <= set("-: "):
                    continue
                tick, zh, en, biz, pct = cells[:5]
                why = "|".join(cells[5:]).strip()
                rows.append({
                    "t": tick.strip("*"), "zh": "" if zh in ("—", "-") else zh,
                    "en": en, "biz": biz, "pct": to_float(pct.rstrip("%")), "why": why,
                })
            short = [p for p in pending if len(p) < 120]
            if not sections:
                lead = [p.strip("*").strip() for p in pending if len(p) >= 120]
            subtitle = [p for p in short if re.search(r"收盤對|前\s*\d+\s*名|前[五十]名", p)]
            # 有 *…* 的優先當結論句；表格後的補充說明（如「QCOM…實際為下跌」）排在後面
            heads = sorted((p for p in short if p not in subtitle), key=lambda p: not p.startswith("*"))
            if heads:
                head = re.sub(r"^\*+|\*+$", "", heads[0]).strip()
            else:  # 結論句與小標寫在同一行：「*能源與防禦股領漲道瓊：漲幅榜前 5 檔（…）*」
                starred = [p for p in subtitle if p.startswith("*")]
                head = re.split(r"[：:]", starred[0].strip("*"))[0].strip() if starred else ""
                head = re.sub(r"（[^（）]*收盤對[^（）]*）", "", head).strip()
            head = re.sub(r"^(漲幅榜|跌幅榜)[：:]\s*", "", head)
            sections.append({"side": "", "head": head, "rows": rows,
                             "label": " ".join(subtitle + heads)})
            pending = []
        elif b.startswith(("資料來源", "資料狀態")):
            note = b
        else:
            pending.append(b)
    for n, s in enumerate(sections):
        lbl = s.pop("label")
        if "跌幅" in lbl and "漲幅" not in lbl:
            s["side"] = "down"
        elif "漲幅" in lbl and "跌幅" not in lbl:
            s["side"] = "up"
        else:
            s["side"] = "up" if n == 0 else "down"

    close = pct = None
    for p in lead:
        m = re.search(r"收約?\s*" + NUM + r"\s*點?\s*[（(、,，]\s*" + PCT, p)
        if m:
            close, pct = to_float(m.group(1)), to_float(m.group(2))
            break
        m = re.search(r"收(漲|跌)\s*(\d+\.\d+)%\s*至\s*" + NUM, p)
        if m:
            pct = to_float(m.group(2)) * (1 if m.group(1) == "漲" else -1)
            close = to_float(m.group(3))
            break
        # 「收 12,208.79、僅跌 0.23%」「收 7,811.54，上漲 0.59%」
        m = re.search(r"收\s*" + NUM + r"\s*[、，,]\s*(?:僅|上|下)?(漲|跌)\s*(\d+\.\d+)%", p)
        if m:
            close = to_float(m.group(1))
            pct = to_float(m.group(3)) * (1 if m.group(2) == "漲" else -1)
            break
    if pct is None:  # 例：「SOX 收約 11,315 點（…推算），收 +1.6%」
        joined = "\n".join(lead)
        m1 = re.search(r"收約?\s*([\d,]{5,}(?:\.\d+)?)", joined)
        m2 = (re.search(r"收\s*([+\-−]\d+(?:\.\d+)?)%", joined)
              # 「收 51,850.55 點，+195.60 點（+0.38%）」：取收盤數字之後第一個括號內百分比
              or (m1 and re.search(r"[（(]([+\-−]\d+\.\d+)%[）)]", joined[m1.end():])))
        if m1 and m2:
            close, pct = to_float(m1.group(1)), to_float(m2.group(1))
    breadth = None
    for p in lead:
        m = re.search(r"(\d+)\s*檔上漲、\s*(\d+)\s*檔下跌", p)
        if m:
            breadth = [int(m.group(1)), int(m.group(2))]
            break

    return {
        "subject": meta.get("subject", ""), "sent": meta.get("sent", ""),
        "close": close, "pct": pct, "breadth": breadth,
        "lead": lead, "sections": sections, "note": note,
    }


def main(root):
    root = Path(root)
    mail_dir = root / "data" / "mail"
    days = {}
    problems = []
    for f in sorted(mail_dir.glob("*.md")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})_([A-Z]+)\.md$", f.name)
        if not m or m.group(2) not in INDICES:
            continue
        d, idx = m.groups()
        rec = parse_mail(f.read_text(encoding="utf-8"))
        n_up = sum(len(s["rows"]) for s in rec["sections"] if s["side"] == "up")
        n_dn = sum(len(s["rows"]) for s in rec["sections"] if s["side"] == "down")
        if not n_up or not n_dn:
            problems.append(f"{f.name}: 漲榜 {n_up} 檔／跌榜 {n_dn} 檔")
        if rec["pct"] is None:
            problems.append(f"{f.name}: 未解析到指數收盤與漲跌幅")
        days.setdefault(d, {})[idx] = rec

    ipath = root / "data" / "intraday.json"
    intra_all = json.loads(ipath.read_text(encoding="utf-8")) if ipath.exists() else {}
    # 郵件沒寫出指數收盤（例：「SOX 收盤資料查證中」）時，用盤中走勢的最後一筆補上並標記
    for d, recs in days.items():
        for idx, rec in recs.items():
            x = intra_all.get(d, {}).get(idx)
            if rec["pct"] is None and x:
                rec["close"] = x["s"][-1][1]
                rec["pct"] = round((x["s"][-1][1] / x["pc"] - 1) * 100, 2)
                rec["close_src"] = "intraday"
    problems = [p for p in problems if not (p.endswith("未解析到指數收盤與漲跌幅")
                and days[p[:10]][p[11:].split(".")[0]]["pct"] is not None)]

    (root / "data" / "days.json").write_text(
        json.dumps(days, ensure_ascii=False, indent=1), encoding="utf-8")

    keep = sorted(days)[-MAX_DAYS:]
    payload = {d: days[d] for d in keep}
    tpl = (root / "scripts" / "template.html").read_text(encoding="utf-8")
    data_js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    intra = {d: intra_all[d] for d in keep if d in intra_all}
    for d in keep:
        if d not in intra:
            problems.append(f"{d}: 無盤中走勢資料")
    mpath, npath = root / "data" / "megacaps.json", root / "data" / "megacap_names.json"
    mega_all = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    mega = {"names": json.loads(npath.read_text(encoding="utf-8")) if npath.exists() else {},
            "days": {d: mega_all[d] for d in keep if d in mega_all}}
    for d in keep:
        if d not in mega_all:
            problems.append(f"{d}: 無權值個股資料")
    xpath = root / "data" / "macro.json"
    macro_all = json.loads(xpath.read_text(encoding="utf-8")) if xpath.exists() else {}
    macro = {d: macro_all[d] for d in keep if d in macro_all}
    npath2 = root / "data" / "megacap_notes.json"
    notes_all = json.loads(npath2.read_text(encoding="utf-8")) if npath2.exists() else {}
    notes = {d: notes_all[d] for d in keep if d in notes_all}
    tpath = root / "data" / "intraday_turns.json"
    turns_all = json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else {}
    turns = {d: turns_all[d] for d in keep if d in turns_all}
    if keep and keep[-1] not in turns:
        problems.append(f"{keep[-1]}: 無盤中轉折標註")

    def render(t):
        return (t.replace("/*__NOTES__*/null", json.dumps(notes, ensure_ascii=False, separators=(",", ":")))
                 .replace("/*__TURNS__*/null", json.dumps(turns, ensure_ascii=False, separators=(",", ":")))
                 .replace("/*__MACRO__*/null", json.dumps(macro, separators=(",", ":")))
                 .replace("/*__MEGA__*/null", json.dumps(mega, ensure_ascii=False, separators=(",", ":")))
                 .replace("/*__DATA__*/null", data_js)
                 .replace("/*__INTRA__*/null", json.dumps(intra, separators=(",", ":"))))
    out = root / "out" / "us-movers.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(tpl), encoding="utf-8")
    css = (root / "scripts" / "mobile.css").read_text(encoding="utf-8")
    out_m = root / "out" / "us-movers-mobile.html"
    out_m.write_text(render(mobile_template(tpl, css)), encoding="utf-8")

    latest = keep[-1] if keep else None
    summary = {
        "latest_date": latest,
        "latest_indices": sorted(days[latest]) if latest else [],
        "missing_indices": [i for i in INDICES if latest and i not in days[latest]],
        "days_in_page": len(keep),
        "problems": problems,
        "out": str(out),
        "bytes": out.stat().st_size,
        "out_mobile": str(out_m),
        "bytes_mobile": out_m.stat().st_size,
    }
    (root / "data" / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
