"""
抓取观察名单个股 + 大盘总经新闻，比对上次执行时看过的纪录（data/seen_news_<market>.json），
只留下「这次新出现」的新闻标题，写成 JSON 给 Claude 判断是否为利多/利空、决定要不要即时推播。

用法: python fetch_alerts.py tw   或   python fetch_alerts.py us
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import json
import time
import datetime
import email.utils
import os
import re
import hashlib
import urllib.parse
import zoneinfo
import feedparser
import requests

from config import TW_WATCHLIST, US_WATCHLIST, DATA_DIR

MACRO_QUERIES = {
    "tw": ["台股 大盘", "台湾央行 利率", "台湾 出口 经济"],
    "us": ["美股 大盘 Fed", "美国 通膨 利率", "Wall Street stock market"],
}

RSS_TEMPLATE = "https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

# 额外来源：Yahoo 股市（个股 + 大盘）、MarketWatch（美股焦点新闻）
YAHOO_TW_TICKER_URL = "https://tw.stock.yahoo.com/rss?s={ticker}"
YAHOO_TW_MACRO_URL = "https://tw.stock.yahoo.com/rss?category=tw-market"
YAHOO_US_TICKER_URL = "https://finance.yahoo.com/rss/headline?s={ticker}"
MARKETWATCH_MACRO_URL = "https://feeds.content.dowjones.io/public/rss/mw_topstories"

# 官方重大讯息公告：台股上市 (TWSE) + 上柜 (TPEx) 公开资讯观测站资料
TWSE_MATERIAL_NEWS_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"
TPEX_MATERIAL_NEWS_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O"

# SEC EDGAR：美股 8-K 重大事件申报。SEC 要求请求带可识别的 User-Agent。
SEC_HEADERS = {"User-Agent": "PersonalStockAlertBot/1.0 (non-commercial personal use)"}
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_8K_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K&dateb=&owner=include&count=5&output=atom"
SEC_CIK_CACHE_PATH = os.path.join(DATA_DIR, "sec_cik_map.json")
SEC_CIK_CACHE_MAX_AGE_DAYS = 30

SEEN_MAX_AGE_DAYS = 14  # seen 纪录只保留最近 N 天，避免档案无限长大

# 「评论/分析」类文章常常是引用旧数据重新包装成新文章（例如一个月前的营收数据被拿来写
# 「还能追吗」的评论），文章发布时间虽新但内容不算新消息。这里只是标记，不做硬过滤，
# 让 Claude 判断时格外留意这类文章引用的数据是否真的是最新的。
# 注意：台湾新闻来源（Google News / Yahoo奇摩股市 / CMoney 等）标题跟来源名称几乎都是
# 繁体中文，这里的关键字必须用繁体写，简体字不会匹配到任何东西。
COMMENTARY_SOURCE_HINTS = ("網誌", "部落格", "專欄", "投資網", "觀點")
COMMENTARY_TITLE_PATTERNS = [
    r"還能.{0,4}(追|買|抱|進場)",
    r"該不該",
    r"值得.{0,4}(買|投資|留意|進場)",
    r"怎麼看",
    r"能不能.{0,4}(追|買)",
    r"該[買賣].{0,4}嗎",
]


def is_likely_commentary(title: str, source: str) -> bool:
    if any(h in source for h in COMMENTARY_SOURCE_HINTS):
        return True
    return any(re.search(p, title) for p in COMMENTARY_TITLE_PATTERNS)

# 市场时区 + 收盘时间，用来算「今天第一次执行」该回推到哪个时间点
MARKET_TZ = {
    "tw": ("Asia/Taipei", 13, 30),
    "us": ("America/New_York", 16, 0),
}


def load_last_run(market: str) -> dict:
    path = os.path.join(DATA_DIR, f"last_run_{market}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_last_run(market: str, now: datetime.datetime) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"last_run_{market}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": now.date().isoformat(), "timestamp": now.isoformat()}, f)


def get_freshness_cutoff(market: str, now: datetime.datetime) -> datetime.datetime:
    """算这次执行该只看『几点之后』发布的新闻：
    - 今天已经跑过：用上次执行的时间点，盘中只看最新的新闻。
    - 今天第一次跑（例如刚开盘）：回推到上一个交易日收盘，涵盖隔夜累积的新闻。
    """
    _, close_h, close_m = MARKET_TZ[market]
    today_str = now.date().isoformat()

    last_run = load_last_run(market)
    if last_run.get("date") == today_str:
        try:
            return datetime.datetime.fromisoformat(last_run["timestamp"])
        except ValueError:
            pass

    prev_day = now.date() - datetime.timedelta(days=1)
    while prev_day.weekday() >= 5:  # 5=周六, 6=周日，回推到上个交易日
        prev_day -= datetime.timedelta(days=1)
    return datetime.datetime.combine(prev_day, datetime.time(close_h, close_m), tzinfo=now.tzinfo)


def parse_published(published: str):
    if not published:
        return None
    try:
        return email.utils.parsedate_to_datetime(published)
    except (TypeError, ValueError):
        return None


def is_fresh(item: dict, cutoff: datetime.datetime) -> bool:
    dt = parse_published(item.get("published", ""))
    if dt is None:
        return True  # 抓不到发布时间就不主动过滤，避免漏掉正常消息
    return dt >= cutoff


def fetch_headlines(query: str, limit: int = 5):
    q = urllib.parse.quote(query)
    url = RSS_TEMPLATE.format(q=q)
    return fetch_rss(url, limit=limit)


def fetch_rss(url: str, limit: int = 5, default_source: str = "", headers: dict = None):
    """通用 RSS 解析：Google News 的 entry 自带 <source>，其他来源没有就用 default_source。"""
    d = feedparser.parse(url, request_headers=headers) if headers else feedparser.parse(url)
    out = []
    for e in d.entries[:limit]:
        src = e.get("source", {}).get("title", "") if hasattr(e, "source") else ""
        title = e.get("title", "")
        source = src or default_source
        out.append({
            "title": title,
            "source": source,
            "published": e.get("published", ""),
            "link": e.get("link", ""),
            "is_commentary": is_likely_commentary(title, source),
        })
    return out


def fetch_yahoo_tw_ticker(ticker: str, limit: int = 3):
    return fetch_rss(YAHOO_TW_TICKER_URL.format(ticker=ticker), limit=limit, default_source="Yahoo奇摩股市")


def fetch_yahoo_tw_macro(limit: int = 5):
    return fetch_rss(YAHOO_TW_MACRO_URL, limit=limit, default_source="Yahoo奇摩股市")


def fetch_yahoo_us_ticker(ticker: str, limit: int = 3):
    return fetch_rss(YAHOO_US_TICKER_URL.format(ticker=ticker), limit=limit, default_source="Yahoo Finance")


def fetch_marketwatch_macro(limit: int = 5):
    return fetch_rss(MARKETWATCH_MACRO_URL, limit=limit, default_source="MarketWatch")


def safe_fetch(label: str, fn, *args, default=None, **kwargs):
    """个别来源失败不该拖垮其他来源，各自吃掉例外、印警告就好。"""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"[warn] {label} 抓取失败: {e}", file=sys.stderr)
        return [] if default is None else default


def load_sec_cik_map() -> dict:
    """美股 ticker -> CIK 对照表，本机快取，超过 N 天才重新下载。"""
    if os.path.exists(SEC_CIK_CACHE_PATH):
        age_days = (time.time() - os.path.getmtime(SEC_CIK_CACHE_PATH)) / 86400
        if age_days < SEC_CIK_CACHE_MAX_AGE_DAYS:
            try:
                with open(SEC_CIK_CACHE_PATH, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
    try:
        resp = requests.get(SEC_TICKERS_URL, headers=SEC_HEADERS, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        mapping = {v["ticker"].upper(): v["cik_str"] for v in raw.values()}
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SEC_CIK_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(mapping, f)
        return mapping
    except Exception as e:
        print(f"[warn] SEC CIK 对照表下载失败: {e}", file=sys.stderr)
        return {}


def _clean_8k_summary(summary_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", summary_html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if "Item" in text:
        text = text[text.index("Item"):]
    return text


def fetch_sec_8k(cik, limit: int = 3):
    url = SEC_8K_URL.format(cik=str(cik).zfill(10))
    d = feedparser.parse(url, request_headers=SEC_HEADERS)
    out = []
    for e in d.entries[:limit]:
        title = _clean_8k_summary(e.get("summary", "")) or e.get("title", "")
        published = ""
        updated = e.get("updated", "")
        if updated:
            try:
                dt = datetime.datetime.fromisoformat(updated)
                published = email.utils.format_datetime(dt)
            except ValueError:
                pass
        out.append({
            "title": f"[8-K] {title}",
            "source": "SEC EDGAR",
            "published": published,
            "link": e.get("link", ""),
        })
    return out


def _roc_to_rfc822(date_str: str, time_str: str, tz: zoneinfo.ZoneInfo) -> str:
    """民国年日期 (YYYMMDD) + 时间 (HMMSS/HHMMSS) 转成跟其他来源一致的 RFC822 字串。"""
    date_str = (date_str or "").strip()
    time_str = (time_str or "0").strip().zfill(6)
    if len(date_str) < 7:
        return ""
    try:
        roc_year, month, day = int(date_str[:3]), int(date_str[3:5]), int(date_str[5:7])
        hour, minute, second = int(time_str[:2]), int(time_str[2:4]), int(time_str[4:6])
        dt = datetime.datetime(roc_year + 1911, month, day, hour, minute, second, tzinfo=tz)
        return email.utils.format_datetime(dt)
    except ValueError:
        return ""


def fetch_tw_official_filings(watchlist: dict) -> dict:
    """一次抓上市 (TWSE) + 上柜 (TPEx) 当日全部重大讯息公告，过滤出观察名单命中的。"""
    codes = {ticker.split(".")[0]: ticker for ticker in watchlist}
    tz = zoneinfo.ZoneInfo("Asia/Taipei")
    result: dict = {}

    sources = [
        (TWSE_MATERIAL_NEWS_URL, "公司代號", "主旨 ", "公开资讯观测站(TWSE)"),
        (TPEX_MATERIAL_NEWS_URL, "SecuritiesCompanyCode", "主旨", "证券柜买中心(TPEx)"),
    ]
    for url, code_field, subject_field, source_label in sources:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            resp.raise_for_status()
            rows = resp.json()
        except Exception as e:
            print(f"[warn] 官方重大讯息（{source_label}）抓取失败: {e}", file=sys.stderr)
            continue
        for row in rows:
            code = row.get(code_field, "")
            if code not in codes:
                continue
            subject = (row.get(subject_field) or "").replace("\r\n", " ").replace("\n", " ").strip()
            if not subject:
                continue
            ticker = codes[code]
            published = _roc_to_rfc822(row.get("發言日期", ""), row.get("發言時間", ""), tz)
            result.setdefault(ticker, []).append({
                "title": subject,
                "source": source_label,
                "published": published,
                "link": "",
            })
    return result


def item_key(item: dict) -> str:
    # Google News 的 link 每次抓都带不同的重导向 token，不能拿来当去重 key，
    # 改用「标题+来源」的正规化字串做 key。
    raw = f"{item.get('title', '').strip()}|{item.get('source', '').strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def load_seen(market: str) -> dict:
    path = os.path.join(DATA_DIR, f"seen_news_{market}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_seen(market: str, seen: dict) -> None:
    cutoff = (datetime.date.today() - datetime.timedelta(days=SEEN_MAX_AGE_DAYS)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"seen_news_{market}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False)


def main():
    market = sys.argv[1].lower() if len(sys.argv) > 1 else "tw"
    watchlist = TW_WATCHLIST if market == "tw" else US_WATCHLIST
    today = datetime.date.today().isoformat()
    tz_name, _, _ = MARKET_TZ[market]
    now = datetime.datetime.now(zoneinfo.ZoneInfo(tz_name))
    cutoff = get_freshness_cutoff(market, now)

    seen = load_seen(market)
    is_first_run = len(seen) == 0

    new_macro = []
    for q in MACRO_QUERIES[market]:
        try:
            for item in fetch_headlines(q, limit=5):
                k = item_key(item)
                if k not in seen and is_fresh(item, cutoff):
                    new_macro.append(item)
                seen[k] = today
            time.sleep(0.3)
        except Exception as e:
            print(f"[warn] 总经新闻 {q} 抓取失败: {e}", file=sys.stderr)

    # 额外大盘来源：TW 用 Yahoo奇摩股市，US 用 MarketWatch 焦点新闻
    extra_macro = safe_fetch("Yahoo奇摩股市大盘", fetch_yahoo_tw_macro, limit=8) if market == "tw" \
        else safe_fetch("MarketWatch焦点新闻", fetch_marketwatch_macro, limit=8)
    for item in extra_macro:
        k = item_key(item)
        if k not in seen and is_fresh(item, cutoff):
            new_macro.append(item)
        seen[k] = today

    sec_cik_map = load_sec_cik_map() if market == "us" else {}

    new_stock = {}
    for ticker, name in watchlist.items():
        try:
            query = name if market == "tw" else f"{name} stock"
            items = fetch_headlines(query, limit=3)
            if market == "tw":
                items += safe_fetch(f"Yahoo奇摩股市（{name}）", fetch_yahoo_tw_ticker, ticker, limit=3)
            else:
                items += safe_fetch(f"Yahoo Finance（{name}）", fetch_yahoo_us_ticker, ticker, limit=3)
                cik = sec_cik_map.get(ticker.upper())
                if cik:
                    items += safe_fetch(f"SEC EDGAR 8-K（{name}）", fetch_sec_8k, cik, limit=3)
            fresh = []
            for item in items:
                k = item_key(item)
                if k not in seen and is_fresh(item, cutoff):
                    fresh.append(item)
                seen[k] = today
            if fresh:
                new_stock[ticker] = {"name": name, "items": fresh}
            time.sleep(0.3)
        except Exception as e:
            print(f"[warn] {name} 新闻抓取失败: {e}", file=sys.stderr)

    # 台股官方重大讯息公告（TWSE 上市 + TPEx 上柜），一次抓当日全部再比对观察名单
    if market == "tw":
        official = safe_fetch("官方重大讯息公告", fetch_tw_official_filings, watchlist, default={})
        for ticker, items in official.items():
            fresh = []
            for item in items:
                k = item_key(item)
                if k not in seen and is_fresh(item, cutoff):
                    fresh.append(item)
                seen[k] = today
            if fresh:
                entry = new_stock.setdefault(ticker, {"name": watchlist[ticker], "items": []})
                entry["items"].extend(fresh)

    save_seen(market, seen)
    save_last_run(market, now)

    os.makedirs(DATA_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(DATA_DIR, f"{market}_alerts_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": ts,
            "market": market,
            "is_first_run": is_first_run,
            "new_macro_news": new_macro,
            "new_stock_news": new_stock,
        }, f, ensure_ascii=False, indent=2)

    total_new = len(new_macro) + sum(len(v["items"]) for v in new_stock.values())
    note = "（第一次执行，seen 纪录是空的，这些不是真的都是刚发生的新消息，只是还没建立过基准线，不该照常发送）" if is_first_run else ""
    print(f"已写入 {out_path}，共 {total_new} 则新消息（时间门槛：{cutoff.strftime('%m-%d %H:%M %Z')} 之后）{note}")


if __name__ == "__main__":
    main()
