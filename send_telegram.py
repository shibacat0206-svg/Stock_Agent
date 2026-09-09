"""
用 Telegram Bot API 送文字讯息给你。
需要环境变量 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID（放在 stock_report/.env）。

用法（测试）: python send_telegram.py "测试讯息"
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

MAX_LEN = 4000  # Telegram 单则文字讯息上限 4096 字，留一点余裕


def _chunks(text: str, size: int = MAX_LEN):
    for i in range(0, len(text), size):
        yield text[i:i + size]


def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "尚未设定 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID（请确认 stock_report/.env 是否存在）。"
        )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chunk in _chunks(text):
        resp = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
        }, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Telegram 推播失败 ({resp.status_code}): {resp.text}")


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "股市快讯系统测试讯息"
    send_telegram_message(msg)
    print("已送出")
