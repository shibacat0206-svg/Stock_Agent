"""
抓取观察名单的价格、技术指标与基本面数据，输出成 JSON snapshot。
用法: python fetch_market.py tw              # 整份台股观察名单
      python fetch_market.py us              # 整份美股观察名单
      python fetch_market.py 3661.TW AAPL    # 只抓指定的 yfinance 代号（台股需带 .TW/.TWO 后缀）
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import json
import time
import datetime
import numpy as np
import pandas as pd
import os

from config import TW_WATCHLIST, US_WATCHLIST, DATA_DIR  # 须在 import yfinance 前执行，修正非 ASCII 路径下的憑證问题

import yfinance as yf


def compute_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff().dropna()
    if len(delta) < period:
        return None
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean().iloc[-1]
    avg_loss = loss.rolling(period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def pct_change(closes: pd.Series, days: int):
    if len(closes) <= days:
        return None
    return round((closes.iloc[-1] / closes.iloc[-1 - days] - 1) * 100, 2)


def fetch_one(ticker: str, name: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period="1y", auto_adjust=True)
    if hist.empty or len(hist) < 20:
        return None

    closes = hist["Close"]
    volumes = hist["Volume"]
    last_close = round(float(closes.iloc[-1]), 2)

    row = {
        "ticker": ticker,
        "name": name,
        "last_close": last_close,
        "chg_1d_pct": pct_change(closes, 1),
        "chg_5d_pct": pct_change(closes, 5),
        "chg_20d_pct": pct_change(closes, 20),
        "chg_60d_pct": pct_change(closes, 60),
        "sma20": round(float(closes.rolling(20).mean().iloc[-1]), 2) if len(closes) >= 20 else None,
        "sma60": round(float(closes.rolling(60).mean().iloc[-1]), 2) if len(closes) >= 60 else None,
        "rsi14": compute_rsi(closes),
        "52w_high": round(float(closes.max()), 2),
        "52w_low": round(float(closes.min()), 2),
        "vol_ratio_20d": None,
    }
    if len(volumes) >= 20 and volumes.rolling(20).mean().iloc[-1] > 0:
        row["vol_ratio_20d"] = round(float(volumes.iloc[-1] / volumes.rolling(20).mean().iloc[-1]), 2)

    try:
        info = t.get_info()
    except Exception:
        info = {}

    row.update({
        "pe_ratio": info.get("trailingPE"),
        "pb_ratio": info.get("priceToBook"),
        "dividend_yield_pct": round(info.get("dividendYield"), 2) if info.get("dividendYield") else None,
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector"),
        "earnings_growth_pct": round(info.get("earningsGrowth") * 100, 2) if info.get("earningsGrowth") else None,
        "revenue_growth_pct": round(info.get("revenueGrowth") * 100, 2) if info.get("revenueGrowth") else None,
        "analyst_target_mean": info.get("targetMeanPrice"),
        "analyst_recommendation": info.get("recommendationKey"),
        "roe_pct": round(info.get("returnOnEquity") * 100, 2) if info.get("returnOnEquity") else None,
    })
    return row


def _print_summary(row: dict) -> None:
    print(f"\n{row['ticker']} {row['name']}")
    print(f"  现价 {row['last_close']} ｜ 涨跌幅 1日 {row['chg_1d_pct']}% / 5日 {row['chg_5d_pct']}% "
          f"/ 20日 {row['chg_20d_pct']}% / 60日 {row['chg_60d_pct']}%")
    print(f"  RSI14 {row['rsi14']} ｜ 距52週高点 "
          f"{round((row['last_close'] / row['52w_high'] - 1) * 100, 1) if row.get('52w_high') else 'N/A'}% "
          f"｜ 量比(vs 20日均量) {row['vol_ratio_20d']}")
    if row.get("pe_ratio") or row.get("pb_ratio"):
        print(f"  本益比 {row['pe_ratio']} ｜ 股价净值比 {row['pb_ratio']} ｜ 分析师目标价 {row['analyst_target_mean']}")


def main():
    args = sys.argv[1:]
    explicit_tickers = args if args and args[0].lower() not in ("tw", "us") else []

    if explicit_tickers:
        name_lookup = {**TW_WATCHLIST, **US_WATCHLIST}
        watchlist = {t: name_lookup.get(t, t) for t in explicit_tickers}
        market = "explicit"
    else:
        market = args[0].lower() if args else "tw"
        watchlist = TW_WATCHLIST if market == "tw" else US_WATCHLIST

    results = []
    for ticker, name in watchlist.items():
        try:
            row = fetch_one(ticker, name)
            if row:
                results.append(row)
        except Exception as e:
            print(f"[warn] {ticker} 抓取失败: {e}", file=sys.stderr)
        time.sleep(0.3)  # 避免过快请求被限流

    os.makedirs(DATA_DIR, exist_ok=True)
    if explicit_tickers:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(DATA_DIR, f"market_snapshot_{ts}.json")
    else:
        today = datetime.date.today().isoformat()
        out_path = os.path.join(DATA_DIR, f"{market}_snapshot_{today}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"date": datetime.date.today().isoformat(), "market": market, "stocks": results}, f,
                   ensure_ascii=False, indent=2)

    print(f"已写入 {out_path}，共 {len(results)} 档")
    for row in results:
        _print_summary(row)


if __name__ == "__main__":
    main()
