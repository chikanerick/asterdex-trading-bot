from decimal import Decimal, ROUND_DOWN, getcontext
import time
import random
from typing import List, Dict, Optional
import requests

from config.settings import (
    BASE_NOTIONAL_USDT, TOTAL_QTY_JITTER,
    HOLD_TIME_RANGE, BETWEEN_CYCLES_RANGE,
    DEFAULT_LEVERAGE
)
from network.client import public_get, private_post, private_get
from utils.formatting import format_float,format_float2
from utils.time_utils import now_ms

# === Фильтры по символам ===
symbol_filters: Dict[str, Dict[str, Decimal]] = {}

def load_symbol_filters(symbol: str):
    try:
        info = public_get("/fapi/v1/exchangeInfo", params={"symbol": symbol})
        
        symbols = info.get("symbols", [])
        s = next((x for x in symbols if x.get("symbol") == symbol), None)
        if not s:
            print(f"[ERROR] Symbol {symbol} not found in exchangeInfo response.")
            return

        
        filters = s.get("filters", [])
        quantity_precision = int(s.get("quantityPrecision", 2))  # ← вот он

        market_lot = next((f for f in filters if f.get("filterType") == "MARKET_LOT_SIZE"), None)
        lot = next((f for f in filters if f.get("filterType") == "LOT_SIZE"), None)
        qty_filter = market_lot or lot

        price_filter = next((f for f in filters if f.get("filterType") == "PRICE_FILTER"), None)
        tick_size = Decimal(str(price_filter["tickSize"])) if price_filter else Decimal("0.0001")

        if qty_filter:
            step_size = Decimal(str(qty_filter["stepSize"]))
            min_qty = Decimal(str(qty_filter["minQty"]))
            max_qty = Decimal(str(qty_filter["maxQty"]))

            symbol_filters[symbol] = {
                "LOT_STEP": step_size,
                "MIN_QTY": min_qty,
                "MAX_QTY": max_qty,
                "TICK_SIZE": tick_size,
                "QTY_PRECISION": quantity_precision
            }

            print(f"[FILTERS] {symbol}: step={step_size}, tick={tick_size}, precision={quantity_precision}, min={min_qty}, max={max_qty}")
        else:
            print(f"[FILTERS] {symbol}: No valid LOT_SIZE or MARKET_LOT_SIZE found")
    except Exception as e:
        print(f"[load_symbol_filters] Warning for {symbol}: {type(e).__name__} → {e}")

def get_mark_price(symbol: str) -> Decimal:
    url = f"https://fapi.asterdex.com/fapi/v1/premiumIndex"
    resp = requests.get(url, params={"symbol": symbol}, timeout=5)
    data = resp.json()
    return Decimal(data["markPrice"])

def adjust_qty(q: Decimal, symbol: str) -> Decimal:
    f = symbol_filters.get(symbol)
    if not f:
        raise RuntimeError(f"No filters loaded for symbol {symbol}")
    LOT_STEP = f["LOT_STEP"]
    MIN_QTY = f["MIN_QTY"]
    MAX_QTY = f["MAX_QTY"]
    QTY_PRECISION = f.get("QTY_PRECISION")

    if q <= 0:
        return Decimal("0")


    adj = (q // LOT_STEP) * LOT_STEP

    if adj < MIN_QTY:
        adj = MIN_QTY
    if adj > MAX_QTY:
        adj = MAX_QTY

    precision_format = Decimal(f"1e-{QTY_PRECISION}")
    adj = adj.quantize(precision_format, rounding=ROUND_DOWN)

    return adj


# === Ордеры ===
def place_market_order(account: Dict[str, str], side: str, quantity: Decimal, reduce_only: bool=False, symbol: str = "ETHUSDT") -> dict:
    adj_qty = adjust_qty(quantity, symbol)
    
    f = symbol_filters[symbol]
   
    print(format_float2(adj_qty, f["QTY_PRECISION"]))
    if adj_qty < f["MIN_QTY"]:
        raise ValueError(f"Adjusted qty {adj_qty} < MIN_QTY {f['MIN_QTY']}")
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": format_float2(adj_qty, f["QTY_PRECISION"]),
        "recvWindow": 10000
    }
    if reduce_only:
        params["reduceOnly"] = "true"
    return private_post("/fapi/v1/order", account, params)

def set_leverage(account: Dict[str, str], symbol: str, leverage: int):
    try:
        params = {
            "symbol": symbol,
            "leverage": leverage,
            "recvWindow": 10000
        }
        resp = private_post("/fapi/v1/leverage", account, params)
        print(f"[LEVERAGE] {account.get('name', '???')} | {symbol} → set to {leverage}")
        return resp
    except Exception as e:
        print(f"[LEVERAGE] Failed for {account.get('name', '???')} | {symbol}: {e}")

def get_order_status(account: Dict[str, str], order_id: Optional[int] = None, client_oid: Optional[str] = None, symbol: str = "ETHUSDT") -> dict:
    params = {"symbol": symbol}
    if order_id:
        params["orderId"] = order_id
    if client_oid:
        params["origClientOrderId"] = client_oid
    return private_get("/fapi/v1/order", account, params)

def wait_for_fill(account: Dict[str, str], order_id: Optional[int] = None, client_oid: Optional[str] = None,
                  timeout_s: float = 10, symbol: str = "ETHUSDT") -> dict:
    start = time.time()
    last = {}
    while time.time() - start < timeout_s:
        try:
            last = get_order_status(account, order_id, client_oid, symbol=symbol)
            if last.get("status", "").upper() == "FILLED":
                return last
        except Exception as e:
            print(f"[wait_for_fill] warning: {e}")
        time.sleep(1)
    return last

# === Стратегия ===
def choose_total_qty(mark_price: Decimal, leverage: int = DEFAULT_LEVERAGE) -> Decimal:
    factor = Decimal(str(random.uniform(float(1 - TOTAL_QTY_JITTER), float(1 + TOTAL_QTY_JITTER))))
    if BASE_NOTIONAL_USDT:
        raw_qty = (BASE_NOTIONAL_USDT * leverage) / mark_price
    else:
        raw_qty = Decimal("0")
    return raw_qty * factor

def sample_legs() -> List[Dict[str, Decimal]]:
    getcontext().prec = 10

    buy_raw = [Decimal(str(random.uniform(0.1, 1.0))) for _ in range(2)]
    buy_total = sum(buy_raw)

    buy_shares = [r / buy_total * Decimal("0.5") for r in buy_raw]


    return [
        {"side": "BUY", "share": buy_shares[0]},
        {"side": "BUY", "share": buy_shares[1]},
        {"side": "SELL", "share": Decimal("0.5")},
    ]

def random_hold_time() -> int:
    return random.randint(*HOLD_TIME_RANGE)

def random_between_pause() -> int:
    return random.randint(*BETWEEN_CYCLES_RANGE)

# === Экспортируемые функции ===
__all__ = [
    "load_symbol_filters", "adjust_qty", "place_market_order", "get_order_status", "wait_for_fill",
    "choose_total_qty", "sample_legs", "random_hold_time", "random_between_pause", "get_mark_price",
    "symbol_filters", "set_leverage"
]