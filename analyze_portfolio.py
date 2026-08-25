"""
读取 portfolio.csv（你的实际持仓），抓当前价格与技术/基本面数据，计算损益与部位权重。
用法: python analyze_portfolio.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import csv
import json
import os
import time
import datetime

from config import TW_WATCHLIST, US_WATCHLIST, DATA_DIR
from fetch_market import fetch_one

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "portfolio.csv")


def load_portfolio():
    rows = []
    with open(PORTFOLIO_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r.get("ticker") or r["ticker"].startswith("#"):
                continue
            rows.append({
                "ticker": r["ticker"].strip(),
                "market": r["market"].strip().upper(),
                "shares": float(r["shares"]),
                "avg_cost": float(r["avg_cost"]),
                "note": r.get("note", ""),
            })
    return rows


def resolve_name(ticker: str, market: str) -> str:
    if market == "TW":
        return TW_WATCHLIST.get(ticker, ticker)
    return US_WATCHLIST.get(ticker, ticker)


def main():
    holdings = load_portfolio()
    if not holdings:
        print("portfolio.csv 是空的，没有持仓可分析。")
        return

    results = []
    for h in holdings:
        name = resolve_name(h["ticker"], h["market"])
        try:
            data = fetch_one(h["ticker"], name)
        except Exception as e:
            print(f"[warn] {h['ticker']} 抓取失败: {e}", file=sys.stderr)
            data = None
        if not data:
            continue

        current_price = data["last_close"]
        market_value = round(current_price * h["shares"], 2)
        cost_value = round(h["avg_cost"] * h["shares"], 2)
        pnl = round(market_value - cost_value, 2)
        pnl_pct = round((current_price / h["avg_cost"] - 1) * 100, 2) if h["avg_cost"] else None

        row = {
            **data,
            "shares": h["shares"],
            "avg_cost": h["avg_cost"],
            "market_value": market_value,
            "cost_value": cost_value,
            "unrealized_pnl": pnl,
            "unrealized_pnl_pct": pnl_pct,
            "note": h["note"],
            "portfolio_market": h["market"],
        }
        results.append(row)
        time.sleep(0.3)

    # 台股(TWD)与美股(USD)是不同货币，总值与权重要分开算，不能混加
    by_market = {"TW": [r for r in results if r["portfolio_market"] == "TW"],
                 "US": [r for r in results if r["portfolio_market"] == "US"]}
    summary = {}
    for mkt, rows in by_market.items():
        mkt_total = sum(r["market_value"] for r in rows)
        for r in rows:
            r["weight_pct"] = round(r["market_value"] / mkt_total * 100, 2) if mkt_total else None
        summary[mkt] = {
            "currency": "TWD" if mkt == "TW" else "USD",
            "total_market_value": round(mkt_total, 2),
            "total_cost_value": round(sum(r["cost_value"] for r in rows), 2),
            "total_unrealized_pnl": round(sum(r["unrealized_pnl"] for r in rows), 2),
        }

    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.date.today().isoformat()
    out_path = os.path.join(DATA_DIR, f"portfolio_snapshot_{today}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": today,
            "summary_by_market": summary,
            "holdings": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"已写入 {out_path}，共 {len(results)} 笔持仓")


if __name__ == "__main__":
    main()
