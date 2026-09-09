"""
检查 Telegram Bot 有没有使用者传来的新讯息（例如持仓异动指令）。
用 offset 记录处理进度，避免重复处理同一则讯息；只接受来自 .env 设定的
TELEGRAM_CHAT_ID 的讯息，避免被别人冒用来篡改持仓。

用法: python check_telegram_inbox.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import json
import os
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DATA_DIR

OFFSET_PATH = os.path.join(DATA_DIR, "telegram_offset.json")
INBOX_PATH = os.path.join(DATA_DIR, "telegram_inbox_latest.json")


def load_offset() -> int:
    if not os.path.exists(OFFSET_PATH):
        return 0
    try:
        with open(OFFSET_PATH, encoding="utf-8") as f:
            return json.load(f).get("offset", 0)
    except (json.JSONDecodeError, OSError):
        return 0


def save_offset(offset: int) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OFFSET_PATH, "w", encoding="utf-8") as f:
        json.dump({"offset": offset}, f)


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("尚未设定 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID（请确认 stock_report/.env 是否存在）。")
        return

    offset = load_offset()
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    resp = requests.get(url, params={"offset": offset, "timeout": 0}, timeout=15)
    resp.raise_for_status()
    payload = resp.json()

    messages = []
    max_update_id = offset - 1
    for update in payload.get("result", []):
        max_update_id = max(max_update_id, update["update_id"])
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != str(TELEGRAM_CHAT_ID):
            continue  # 不是自己，忽略
        text = msg.get("text")
        if not text:
            continue
        messages.append({
            "message_id": msg.get("message_id"),
            "date": msg.get("date"),
            "text": text,
        })

    save_offset(max_update_id + 1)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(INBOX_PATH, "w", encoding="utf-8") as f:
        json.dump({"messages": messages}, f, ensure_ascii=False, indent=2)

    print(f"已写入 {INBOX_PATH}，共 {len(messages)} 则新讯息")


if __name__ == "__main__":
    main()
