# 观察名单：可自行增删。key 是 yfinance 代号，value 是中文/显示名称。

TW_WATCHLIST = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2308.TW": "台達電",
    "2382.TW": "廣達", "2412.TW": "中華電", "2881.TW": "富邦金", "2882.TW": "國泰金",
    "2891.TW": "中信金", "2886.TW": "兆豐金", "2884.TW": "玉山金", "2892.TW": "第一金",
    "2880.TW": "華南金", "1301.TW": "台塑", "1303.TW": "南亞", "1326.TW": "台化",
    "6505.TW": "台塑化", "2002.TW": "中鋼", "3711.TW": "日月光投控", "2303.TW": "聯電",
    "3034.TW": "聯詠", "3037.TW": "欣興", "2379.TW": "瑞昱", "2357.TW": "華碩",
    "2395.TW": "研華", "2409.TW": "友達", "3008.TW": "大立光", "1216.TW": "統一",
    "2912.TW": "統一超", "9910.TW": "豐泰", "2603.TW": "長榮", "2609.TW": "陽明",
    "2615.TW": "萬海", "5880.TW": "合庫金", "2801.TW": "彰銀", "2887.TW": "台新金",
    "5871.TW": "中租-KY", "6669.TW": "緯穎", "2377.TW": "微星", "3231.TW": "緯創",
    "2356.TW": "英業達", "4904.TW": "遠傳", "3045.TW": "台灣大", "1101.TW": "台泥",
    "2207.TW": "和泰車",
    "2327.TW": "國巨", "2385.TW": "群光", "3443.TW": "創意", "3661.TW": "世芯-KY",
    "6415.TW": "矽力-KY", "8069.TWO": "元太", "2049.TW": "上銀", "1590.TW": "亞德客-KY",
    "4938.TW": "和碩", "2474.TW": "可成", "6488.TWO": "環球晶", "5347.TWO": "世界先進",
    "3406.TW": "玉晶光", "3105.TWO": "穩懋", "2408.TW": "南亞科", "2344.TW": "華邦電",
    "5269.TW": "祥碩", "2059.TW": "川湖", "1519.TW": "華城", "1513.TW": "中興電",
    "2618.TW": "長榮航", "2610.TW": "華航", "5522.TW": "遠雄", "2542.TW": "興富發",
    "2812.TW": "台中銀", "2492.TW": "華新科", "6770.TW": "力積電", "2890.TW": "永豐金",
    "5876.TW": "上海商銀", "2834.TW": "臺企銀", "6005.TW": "群益證", "6023.TWO": "元大期",
    "2855.TW": "統一證", "1210.TW": "大成", "1227.TW": "佳格", "2903.TW": "遠百",
    "2915.TW": "潤泰全", "9904.TW": "寶成", "9917.TW": "中保科", "9921.TW": "巨大",
    "9941.TW": "裕融", "9945.TW": "潤泰新", "1102.TW": "亞泥", "2201.TW": "裕隆",
    "2204.TW": "中華", "2231.TW": "為升", "9914.TW": "美利達", "6446.TW": "藥華藥",
    "1795.TW": "美時", "4162.TWO": "智擎", "1476.TW": "儒鴻", "1477.TW": "聚陽",
    "3576.TW": "聯合再生", "6182.TWO": "合晶", "8081.TW": "致新",
}

US_WATCHLIST = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet",
    "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla", "AVGO": "Broadcom",
    "BRK-B": "Berkshire Hathaway", "JPM": "JPMorgan", "V": "Visa", "MA": "Mastercard",
    "UNH": "UnitedHealth", "XOM": "Exxon Mobil", "JNJ": "Johnson & Johnson",
    "PG": "Procter & Gamble", "HD": "Home Depot", "MRK": "Merck", "ABBV": "AbbVie",
    "COST": "Costco", "PEP": "PepsiCo", "KO": "Coca-Cola", "WMT": "Walmart",
    "BAC": "Bank of America", "CRM": "Salesforce", "ADBE": "Adobe", "NFLX": "Netflix",
    "AMD": "AMD", "INTC": "Intel", "QCOM": "Qualcomm", "ORCL": "Oracle",
    "CSCO": "Cisco", "TXN": "Texas Instruments", "LIN": "Linde", "TMO": "Thermo Fisher",
    "ABT": "Abbott", "NKE": "Nike", "DIS": "Disney", "PFE": "Pfizer", "VZ": "Verizon",
    "T": "AT&T", "CAT": "Caterpillar", "BA": "Boeing", "GE": "GE Aerospace",
    "LMT": "Lockheed Martin", "RTX": "RTX", "GS": "Goldman Sachs", "MS": "Morgan Stanley",
    "C": "Citigroup", "PYPL": "PayPal", "UBER": "Uber",
}

# LINE Messaging API（取代已停止服務的 LINE Notify）
# 密钥放在 stock_report/.env（勿提交/外流），不要写死在这个档案里
import os
from dotenv import load_dotenv


# Windows 上若使用者路徑含非 ASCII 字元（例如中文使用者名），curl_cffi
# （yfinance 用來繞過 Yahoo 反爬蟲）讀取 certifi 憑證路徑會失敗，
# 這裡偵測到非 ASCII 路徑時自動把憑證複製到磁碟根目錄下的安全路徑。
def _ensure_ascii_cacert():
    import certifi
    path = certifi.where()
    try:
        path.encode("ascii")
        return
    except UnicodeEncodeError:
        pass
    import shutil
    safe_dir = os.path.join(os.environ.get("SystemDrive", "C:") + os.sep, "stock_agent_ca")
    os.makedirs(safe_dir, exist_ok=True)
    safe_path = os.path.join(safe_dir, "cacert.pem")
    if not os.path.exists(safe_path):
        shutil.copyfile(path, safe_path)
    certifi.where = lambda: safe_path


_ensure_ascii_cacert()

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

# Telegram Bot API（用於即時利多/利空快讯）
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# FinMind API（台股籌碼/估值/營收/股利資料，目前只提供台股，不含美股）
FINMIND_API_TOKEN = os.environ.get("FINMIND_API_TOKEN", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
