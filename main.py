import random
import time
from config.accounts import load_keys_and_proxies
from config.settings import SYMBOLS, DEFAULT_LEVERAGE
from trading.core import load_symbol_filters, symbol_filters, set_leverage
from runner.cycle_runner import run_cycle

def main():
    print("=== AsterDex Trader ===")
    try:
        accounts = load_keys_and_proxies()
        if accounts is None or len(accounts) == 0:
            print("[ERROR] Failed to load accounts.")
            return
    except Exception as e:
        print(f"[ERROR] Failed to load keys/proxies: {e}")
        return

    if len(accounts) < 3:
        print(f"[ERROR] Need at least {3} accounts. Found: {len(accounts)}")
        return

    print(f"[INIT] Loaded {len(accounts)} accounts.")
    time.sleep(1)

    for symbol in SYMBOLS:
        load_symbol_filters(symbol)
        f = symbol_filters.get(symbol)
        if f:
            print(f"[INIT] Filters for {symbol}: step={f['LOT_STEP']}, minQty={f['MIN_QTY']}")
        else:
            print(f"[WARN] No filters loaded for {symbol}")
        time.sleep(0.5)

    for symbol in SYMBOLS:
        for acct in accounts:
            name = acct.get("name", "???")
            try:
                set_leverage(acct, symbol, DEFAULT_LEVERAGE)
            except Exception as e:
                print(f"[LEVERAGE] Failed for {name} | {symbol}: {e}")
            time.sleep(0.2)

    print("[INFO] Press Ctrl+C to stop.\n")

    try:
        while True:
            symbol = random.choice(SYMBOLS) if isinstance(SYMBOLS, list) else SYMBOLS
            run_cycle(accounts, symbol)
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user. Exiting gracefully.")

if __name__ == "__main__":
    main()