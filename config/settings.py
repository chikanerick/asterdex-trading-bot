from decimal import Decimal
from typing import Tuple

# === API и файлы ===
BASE_URL = "https://fapi.asterdex.com"
KEYS_FILE = "config/keys.json"       
PROXY_FILE = "config/proxies.txt"  

# === Торговый символ ===
SYMBOLS = ["BTCUSDT","ETHUSDT"]   # Торгуемые пары
DEFAULT_LEVERAGE = 10 # Плечо

# === Общая позиция и разброс по циклам ===
BASE_NOTIONAL_USDT = Decimal("20")           # базовая сумма позиции USDT
TOTAL_QTY_JITTER = Decimal("0.05")          # ±10% разброс

# === Время удержания позиции ===
HOLD_TIME_RANGE: Tuple[int, int] = (30, 110)        # в секундах

# === Пауза между циклами ===
BETWEEN_CYCLES_RANGE: Tuple[int, int] = (30, 200)     # в секундах


