"""
用 LINE Messaging API 广播文字讯息给所有加了这个官方帐号好友的人
（个人使用情境下=只有你自己）。LINE Notify 已於 2025-03-31 停止服务，改用这个。
需要环境变量 LINE_CHANNEL_ACCESS_TOKEN（放在 stock_report/.env）。

用法（测试）: python send_line.py "测试讯息"
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import json
import requests

from config import LINE_CHANNEL_ACCESS_TOKEN

BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
MAX_LEN = 4900  # LINE 单则文字讯息上限 5000 字，留一点余裕


def _chunks(text: str, size: int = MAX_LEN):
    for i in range(0, len(text), size):
        yield text[i:i + size]


def send_line_message(text: str) -> None:
    if not LINE_CHANNEL_ACCESS_TOKEN:
        raise RuntimeError(
            "尚未设定 LINE_CHANNEL_ACCESS_TOKEN（请确认 stock_report/.env 是否存在）。"
        )

    messages = [{"type": "text", "text": chunk} for chunk in _chunks(text)][:5]  # 一次最多 5 则

    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    resp = requests.post(BROADCAST_URL, headers=headers, data=json.dumps({
        "messages": messages,
    }), timeout=15)

    if resp.status_code != 200:
        raise RuntimeError(f"LINE 推播失败 ({resp.status_code}): {resp.text}")


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "股市报告系统测试讯息"
    send_line_message(msg)
    print("已送出")
