"""
检查观察名单（config.py 的 TW_WATCHLIST / US_WATCHLIST）有没有刚公布的新财报
（EPS 实际 vs 预期）。比对上次纪录的 data/seen_earnings_<market>.json，只留下
这次新出现的已公布财报，交给 Claude 判断是不是「好消息」，决定要不要即时推播。

用法: python fetch_earnings.py tw   或   python fetch_earnings.py us
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import json
import os
import time
import pandas as pd
import yfinance as yf

from config import TW_WATCHLIST, US_WATCHLIST, DATA_DIR


def load_seen(market: str) -> dict:
    path = os.path.join(DATA_DIR, f"seen_earnings_{market}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_seen(market: str, seen: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"seen_earnings_{market}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False)


def main():
    market = sys.argv[1].lower() if len(sys.argv) > 1 else "tw"
    watchlist = TW_WATCHLIST if market == "tw" else US_WATCHLIST

    seen = load_seen(market)
    is_first_run = len(seen) == 0
    new_reports = []

    for ticker, name in watchlist.items():
        try:
            t = yf.Ticker(ticker)
            df = t.get_earnings_dates(limit=8)
        except Exception as e:
            print(f"[warn] {ticker} 财报资料抓取失败: {e}", file=sys.stderr)
            continue
        if df is None or df.empty:
            continue

        for date, row in df.iterrows():
            reported = row.get("Reported EPS")
            if pd.isna(reported):
                continue  # 还没公布
            key = f"{ticker}_{date.date().isoformat()}"
            if key in seen:
                continue
            seen[key] = True
            estimate = row.get("EPS Estimate")
            surprise = row.get("Surprise(%)")
            new_reports.append({
                "ticker": ticker,
                "name": name,
                "report_date": date.date().isoformat(),
                "eps_estimate": None if pd.isna(estimate) else round(float(estimate), 4),
                "eps_reported": round(float(reported), 4),
                "surprise_pct": None if pd.isna(surprise) else round(float(surprise), 2),
            })
        time.sleep(0.3)

    save_seen(market, seen)

    os.makedirs(DATA_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(DATA_DIR, f"{market}_earnings_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "market": market,
            "is_first_run": is_first_run,
            "new_reports": new_reports,
        }, f, ensure_ascii=False, indent=2)

    note = "（第一次执行，只是建立基准线，不该照常发送）" if is_first_run else ""
    print(f"已写入 {out_path}，共 {len(new_reports)} 笔新财报{note}")


if __name__ == "__main__":
    main()
