"""
抓取 FinMind 的台股籌碼/估值/營收/股利資料：三大法人買賣超、融資融券、本益比/淨值比/殖利率、
月營收年增率、最新現金股利。FinMind 目前只提供台股資料，美股持倉不適用。

用法: python fetch_finmind.py            # 抓 portfolio.csv 里的实际台股持仓
      python fetch_finmind.py 2330 2317  # 抓指定的台股代号（不含 .TW/.TWO 后缀）
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import csv
import json
import os
import time
import datetime

import requests

from config import TW_WATCHLIST, FINMIND_API_TOKEN, DATA_DIR

API_URL = "https://api.finmindtrade.com/api/v4/data"
PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "portfolio.csv")


def bare_code(ticker: str) -> str:
    return ticker.replace(".TWO", "").replace(".TW", "")


def load_portfolio_tw_codes() -> list:
    codes = []
    with open(PORTFOLIO_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r.get("ticker") or r["ticker"].startswith("#"):
                continue
            if r["market"].strip().upper() != "TW":
                continue
            codes.append(bare_code(r["ticker"].strip()))
    return codes


def resolve_name(code: str) -> str:
    for ticker, name in TW_WATCHLIST.items():
        if bare_code(ticker) == code:
            return name
    return code


def finmind_get(dataset: str, data_id: str = None, start_date: str = None, end_date: str = None) -> list:
    params = {"dataset": dataset, "token": FINMIND_API_TOKEN}
    if data_id:
        params["data_id"] = data_id
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    resp = requests.get(API_URL, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != 200:
        raise RuntimeError(payload.get("msg", "FinMind 回传错误"))
    return payload.get("data", [])


def fetch_one(code: str) -> dict:
    today = datetime.date.today()
    since_10d = (today - datetime.timedelta(days=10)).isoformat()
    since_1y = (today - datetime.timedelta(days=450)).isoformat()

    row = {"code": code, "name": resolve_name(code)}

    try:
        rows = finmind_get("TaiwanStockInstitutionalInvestorsBuySell", code, since_10d)
        recent_dates = sorted({r["date"] for r in rows})[-5:]
        recent = [r for r in rows if r["date"] in recent_dates]
        row["institutional_net_5d"] = {
            "foreign": sum(r["buy"] - r["sell"] for r in recent if r["name"] == "Foreign_Investor"),
            "investment_trust": sum(r["buy"] - r["sell"] for r in recent if r["name"] == "Investment_Trust"),
            "dealer": sum(r["buy"] - r["sell"] for r in recent if str(r["name"]).startswith("Dealer")),
        }
    except Exception as e:
        print(f"[warn] {code} 三大法人资料抓取失败: {e}", file=sys.stderr)

    try:
        rows = finmind_get("TaiwanStockMarginPurchaseShortSale", code, since_10d)
        if rows:
            latest = rows[-1]
            row["margin_latest"] = {
                "date": latest.get("date"),
                "margin_balance": latest.get("MarginPurchaseTodayBalance"),
                "short_balance": latest.get("ShortSaleTodayBalance"),
            }
    except Exception as e:
        print(f"[warn] {code} 融资融券资料抓取失败: {e}", file=sys.stderr)

    try:
        rows = finmind_get("TaiwanStockPER", code, since_10d)
        if rows:
            latest = rows[-1]
            row["valuation"] = {
                "date": latest.get("date"),
                "per": latest.get("PER"),
                "pbr": latest.get("PBR"),
                "dividend_yield_pct": latest.get("dividend_yield"),
            }
    except Exception as e:
        print(f"[warn] {code} 本益比资料抓取失败: {e}", file=sys.stderr)

    try:
        rows = finmind_get("TaiwanStockMonthRevenue", code, since_1y)
        if rows:
            rows = sorted(rows, key=lambda r: r["date"])
            latest = rows[-1]
            prev_year = [
                r for r in rows
                if r.get("revenue_year") == latest.get("revenue_year") - 1
                and r.get("revenue_month") == latest.get("revenue_month")
            ]
            yoy = None
            if prev_year and prev_year[0].get("revenue"):
                yoy = round((latest["revenue"] / prev_year[0]["revenue"] - 1) * 100, 2)
            row["monthly_revenue"] = {
                "year_month": f"{latest.get('revenue_year')}-{latest.get('revenue_month'):02d}",
                "revenue": latest.get("revenue"),
                "yoy_pct": yoy,
            }
    except Exception as e:
        print(f"[warn] {code} 月营收资料抓取失败: {e}", file=sys.stderr)

    try:
        rows = finmind_get("TaiwanStockDividend", code, since_1y)
        if rows:
            rows = sorted(rows, key=lambda r: r["date"])
            latest = rows[-1]
            row["dividend_latest"] = {
                "date": latest.get("date"),
                "cash_dividend": latest.get("CashEarningsDistribution"),
                "stock_dividend": latest.get("StockEarningsDistribution"),
            }
    except Exception as e:
        print(f"[warn] {code} 股利资料抓取失败: {e}", file=sys.stderr)

    return row


def main():
    if not FINMIND_API_TOKEN:
        print("缺少 FINMIND_API_TOKEN（请检查 .env），无法呼叫 FinMind API。")
        return

    if len(sys.argv) > 1:
        codes = sys.argv[1:]
    else:
        codes = load_portfolio_tw_codes()
        if not codes:
            print("portfolio.csv 里没有台股持仓，也没有指定代号，没有资料可抓。")
            return

    results = []
    for code in codes:
        results.append(fetch_one(code))
        time.sleep(0.5)  # FinMind 有请求频率限制，避免过快被限流

    os.makedirs(DATA_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(DATA_DIR, f"finmind_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"generated_at": ts, "stocks": results}, f, ensure_ascii=False, indent=2)

    print(f"已写入 {out_path}")
    for r in results:
        print(f"\n{r['code']} {r['name']}")
        if "institutional_net_5d" in r:
            i = r["institutional_net_5d"]
            print(f"  三大法人近5日净买卖(股): 外资 {i['foreign']:+,} / 投信 {i['investment_trust']:+,} / 自营 {i['dealer']:+,}")
        if "margin_latest" in r:
            m = r["margin_latest"]
            print(f"  融资余额({m['date']}): {m['margin_balance']:,} ｜ 融券余额: {m['short_balance']:,}")
        if "valuation" in r:
            v = r["valuation"]
            print(f"  估值({v['date']}): 本益比 {v['per']} ｜ 股价净值比 {v['pbr']} ｜ 殖利率 {v['dividend_yield_pct']}%")
        if "monthly_revenue" in r:
            rv = r["monthly_revenue"]
            yoy_str = f"{rv['yoy_pct']:+}%" if rv["yoy_pct"] is not None else "N/A"
            print(f"  月营收({rv['year_month']}): {rv['revenue']:,} ｜ 年增率 {yoy_str}")
        if "dividend_latest" in r:
            d = r["dividend_latest"]
            print(f"  最新股利({d['date']}): 现金 {d['cash_dividend']} ｜ 股票 {d['stock_dividend']}")


if __name__ == "__main__":
    main()
