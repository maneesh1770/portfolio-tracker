"""Refresh data/prices.json (last closes + market cap) and data/news.json (company headlines).

Runs in GitHub Actions after the Indian market close. Reads data/symbols.csv.
Only public market data is written: no quantities or costs ever touch this repo.
"""
import csv, datetime as dt, email.utils, html, json, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
UA = {"User-Agent": "Mozilla/5.0 (portfolio-tracker)"}
MAX_PER_STOCK = 6      # headlines kept per company
NEWS_DAYS = 14         # how far back to look

TAGS = [
    ("Results", r"\b(results?|q[1-4]\s?fy\s?\d{2}|quarterly|net profit|profit (rises|jumps|surges|falls|drops|declines|slips)|earnings|revenue|ebitda|margins?)\b"),
    ("Orders & deals", r"\b(orders?|contracts?|wins?|bags?|acquires?|acquisition|stake|merger|demerger|deal|tie-?up|partnership)\b"),
    ("Ratings & targets", r"\b(target price|upgrade[sd]?|downgrade[sd]?|brokerage|initiates|overweight|underweight|outperform|buy rating|sell rating)\b"),
    ("Dividend & corporate", r"\b(dividend|bonus|stock split|buyback|ipo|qip|fund ?raise|rights issue)\b"),
]


def tag_headline(title: str) -> str:
    for name, pat in TAGS:
        if re.search(pat, title, re.I):
            return name
    return "Other"


def read_symbols():
    with open(DATA / "symbols.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------- prices ----------------
def fetch_prices(rows, old):
    import yfinance as yf
    out, ok = dict(old.get("prices", {})), 0
    for i in range(0, len(rows), 40):
        chunk = rows[i:i + 40]
        tickers = [r["ticker"] for r in chunk]
        try:
            data = yf.download(tickers, period="10d", interval="1d", group_by="ticker",
                               auto_adjust=False, progress=False, threads=True)
        except Exception as e:
            print("download failed:", e)
            continue
        for r in chunk:
            try:
                s = data[r["ticker"]]["Close"].dropna()
                if s.empty:
                    raise ValueError("no closes")
                entry = {"close": round(float(s.iloc[-1]), 2),
                         "prev": round(float(s.iloc[-2]), 2) if len(s) > 1 else None,
                         "date": s.index[-1].strftime("%Y-%m-%d"),
                         "mcap_cr": (out.get(r["symbol"]) or {}).get("mcap_cr")}
                out[r["symbol"]] = entry
                ok += 1
            except Exception:
                print("no price for", r["symbol"], r["ticker"])
    # market cap (stocks only), best effort
    for r in rows:
        if r["kind"] != "stock" or r["symbol"] not in out:
            continue
        try:
            fi = yf.Ticker(r["ticker"]).fast_info
            mc = fi["market_cap"] if "market_cap" in fi else fi["marketCap"]
            if mc:
                out[r["symbol"]]["mcap_cr"] = round(float(mc) / 1e7)
        except Exception:
            pass
        time.sleep(0.15)
    dates = sorted({v["date"] for v in out.values() if v.get("date")})
    return {"updated": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "asOf": dates[-1] if dates else None, "source": "Yahoo Finance via yfinance",
            "prices": out}, ok


# ---------------- news ----------------
def parse_rss(xml_text: str):
    items = []
    root = ET.fromstring(xml_text)
    for it in root.iter("item"):
        title = html.unescape((it.findtext("title") or "").strip())
        link = (it.findtext("link") or "").strip()
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3].strip()
        try:
            when = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
            iso = when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            iso = None
        if title and link:
            items.append({"title": title, "link": link, "source": source, "date": iso})
    return items


def fetch_news(rows):
    out = []
    for r in rows:
        if r["kind"] != "stock" or not r["name"]:
            continue
        q = urllib.parse.quote(f'{r["name"]} when:{NEWS_DAYS}d')
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as resp:
                items = parse_rss(resp.read().decode("utf-8", "replace"))
        except Exception as e:
            print("news failed for", r["symbol"], e)
            continue
        pat = re.compile(r["match"] or re.escape(r["name"].split()[0]), re.I)
        seen, kept = set(), 0
        for it in items:
            key = re.sub(r"\W+", " ", it["title"].lower())[:80]
            if key in seen or not pat.search(it["title"]):
                continue
            seen.add(key)
            out.append({"sym": r["symbol"], "title": it["title"], "link": it["link"], "source": it["source"],
                        "date": it["date"], "tag": tag_headline(it["title"])})
            kept += 1
            if kept >= MAX_PER_STOCK:
                break
        time.sleep(0.4)
    out.sort(key=lambda x: x["date"] or "", reverse=True)
    return {"updated": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "items": out}


def main():
    rows = read_symbols()
    pfile = DATA / "prices.json"
    old = json.loads(pfile.read_text()) if pfile.exists() else {}
    prices, ok = fetch_prices(rows, old)
    print(f"prices: {ok}/{len(rows)} refreshed")
    if ok == 0:
        print("No prices fetched; leaving data files unchanged.")
        sys.exit(1)
    pfile.write_text(json.dumps(prices, separators=(",", ":")))
    news = fetch_news(rows)
    print(f"news: {len(news['items'])} headlines")
    (DATA / "news.json").write_text(json.dumps(news, separators=(",", ":")))


if __name__ == "__main__":
    main()
