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

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
