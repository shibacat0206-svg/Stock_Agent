"""
用 Google News RSS（免费、不需 API key）抓总经/大盘新闻，以及观察名单内每档个股的新闻标题。
用法: python fetch_news.py tw   或   python fetch_news.py us
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import json
import time
import datetime
import os
import feedparser

from config import TW_WATCHLIST, US_WATCHLIST, DATA_DIR

MACRO_QUERIES = {
    "tw": ["台股 大盘", "台湾央行 利率", "台湾 出口 经济"],
    "us": ["美股 大盘 Fed", "美国 通膨 利率", "Wall Street stock market"],
}

RSS_TEMPLATES = {
    "tw": "https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "us": "https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
}


def fetch_headlines(query: str, market: str, limit: int = 5):
    import urllib.parse
    q = urllib.parse.quote(query)
    url = RSS_TEMPLATES[market].format(q=q)
    d = feedparser.parse(url)
    out = []
    for e in d.entries[:limit]:
        out.append({
            "title": e.get("title", ""),
            "source": e.get("source", {}).get("title", "") if hasattr(e, "source") else "",
            "published": e.get("published", ""),
            "link": e.get("link", ""),
        })
    return out


def main():
    market = sys.argv[1].lower() if len(sys.argv) > 1 else "tw"
    watchlist = TW_WATCHLIST if market == "tw" else US_WATCHLIST

    macro_news = []
    for q in MACRO_QUERIES[market]:
        try:
            macro_news.extend(fetch_headlines(q, market, limit=5))
            time.sleep(0.3)
        except Exception as e:
            print(f"[warn] 总经新闻 {q} 抓取失败: {e}", file=sys.stderr)

    stock_news = {}
    for ticker, name in watchlist.items():
        try:
            query = name if market == "tw" else f"{name} stock"
            stock_news[ticker] = fetch_headlines(query, market, limit=2)
            time.sleep(0.3)
        except Exception as e:
            print(f"[warn] {name} 新闻抓取失败: {e}", file=sys.stderr)
            stock_news[ticker] = []

    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.date.today().isoformat()
    out_path = os.path.join(DATA_DIR, f"{market}_news_{today}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "market": market, "macro_news": macro_news, "stock_news": stock_news},
                   f, ensure_ascii=False, indent=2)

    print(f"已写入 {out_path}")


if __name__ == "__main__":
    main()
