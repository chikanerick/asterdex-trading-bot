import time
import random
from typing import List, Dict

from config.settings import SYMBOLS, BASE_NOTIONAL_USDT, DEFAULT_LEVERAGE
from trading.core import (
    choose_total_qty, sample_legs, random_hold_time, random_between_pause,
    adjust_qty, format_float, place_market_order, wait_for_fill, get_mark_price
)
from utils.stats_excel import update_stats_excel
from utils.logger import logger

MAX_ATTEMPTS = 5
MIN_NOTIONAL = 5

def run_cycle(accounts: List[Dict[str, str]], symbol: str):
    chosen = random.sample(accounts, 3)
    random.shuffle(chosen)

    mark_price = get_mark_price(symbol)
    total_qty = choose_total_qty(mark_price, DEFAULT_LEVERAGE)
    legs = sample_legs()
    hold_time = random_hold_time()

    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    roles_text = ", ".join([f"{int(round(float(x['share']) * 100))}% {x['side']}" for x in legs])

    logger.info("=" * 70)
    logger.info(f"[CYCLE START] {ts}")
    logger.info(f"[SETUP] Symbol: {symbol} | Mark: {format_float(mark_price)}")
    logger.info(f"[SETUP] Leverage: {DEFAULT_LEVERAGE}x")
    logger.info(f"[SETUP] Target notional: {BASE_NOTIONAL_USDT} USDT → Qty: {format_float(total_qty)} {symbol}")
    logger.info(f"[SETUP] Legs: {roles_text} | Hold: {hold_time}s")
    logger.info("=" * 70)

    opens = []
    for idx, (acct, leg) in enumerate(zip(chosen, legs), start=1):
        name = acct.get("name", f"#{idx}")
        raw_qty = total_qty * leg["share"]
        adj_qty = adjust_qty(raw_qty, symbol)
        side = leg["side"]
        notional = adj_qty * mark_price
        proxy_host = acct['proxy']['http'].split('@')[-1]

        logger.info(f"[ORDER OPEN] {name}")
        logger.info(f"  Proxy: {proxy_host}")
        logger.info(f"  Action: {side}")
        logger.info(f"  Raw Qty: {format_float(raw_qty)} → Adjusted: {format_float(adj_qty)} {symbol}")
        logger.info(f"  Notional: {format_float(notional)} USDT")

        if notional < MIN_NOTIONAL:
            logger.error(f"[SKIP] Notional {format_float(notional)} < {MIN_NOTIONAL} USDT — skipping order")
            continue

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = place_market_order(acct, side, adj_qty, symbol=symbol)
                order_id = resp.get("orderId")

                try:
                    filled = wait_for_fill(acct, order_id, symbol=symbol)
                    if not filled or filled.get("status", "").upper() != "FILLED":
                        raise RuntimeError("Order not filled or response empty")
                except Exception as e:
                    raise RuntimeError(f"wait_for_fill failed: {type(e).__name__} → {e}")

                try:
                    update_stats_excel(name, symbol, adj_qty, side, mark_price)
                except Exception as e:
                    logger.warning(f"[WARN] Stats update failed for {name}: {type(e).__name__} → {e}")

                logger.success(f"  → Order placed: orderId={order_id}, status=FILLED")
                opens.append({
                    "account": acct,
                    "qty": adj_qty,
                    "open_side": side,
                    "name": name
                })
                break

            except Exception as e:
                logger.error(f"[ERROR] Attempt {attempt}/{MAX_ATTEMPTS} failed to place open order")
                logger.error(f"  Name: {name} | Proxy: {proxy_host}")
                logger.error(f"  Reason: {type(e).__name__} → {e}")
                time.sleep(1.5 * attempt)
        else:
            logger.error(f"[ERROR] Giving up after {MAX_ATTEMPTS} failed attempts for {name}")

    logger.info(f"[HOLD] Holding positions for {hold_time}s...")
    time.sleep(hold_time)

    for info in opens:
        acct = info["account"]
        name = info.get("name", "???")
        qty = info["qty"]
        open_side = info["open_side"]
        close_side = "SELL" if open_side == "BUY" else "BUY"

        logger.info(f"[ORDER CLOSE] {name} | Action: {close_side} {format_float(qty)} {symbol} (reduceOnly)")

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = place_market_order(acct, close_side, qty, reduce_only=True, symbol=symbol)
                order_id = resp.get("orderId")

                try:
                    filled = wait_for_fill(acct, order_id, symbol=symbol)
                    if not filled or filled.get("status", "").upper() != "FILLED":
                        raise RuntimeError("Order not filled or response empty")
                except Exception as e:
                    raise RuntimeError(f"wait_for_fill failed: {type(e).__name__} → {e}")

                try:
                    update_stats_excel(name, symbol, qty, close_side, mark_price)
                except Exception as e:
                    logger.warning(f"[WARN] Stats update failed for {name}: {type(e).__name__} → {e}")

                logger.success(f"  → Close placed: orderId={order_id}, status=FILLED")
                break

            except Exception as e:
                logger.error(f"[ERROR] Attempt {attempt}/{MAX_ATTEMPTS} failed to place close order")
                logger.error(f"  Name: {name}")
                logger.error(f"  Reason: {type(e).__name__} → {e}")
                time.sleep(1.5 * attempt)
        else:
            logger.error(f"[ERROR] Giving up after {MAX_ATTEMPTS} failed close attempts for {name}")

    pause = random_between_pause()
    logger.info(f"[PAUSE] Cycle complete. Sleeping {pause}s before next cycle...")
    time.sleep(pause)
