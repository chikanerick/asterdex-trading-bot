import json
from typing import List, Dict
from config.settings import KEYS_FILE, PROXY_FILE

def load_keys_and_proxies() -> List[Dict[str, str]]:
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        keys = json.load(f)
    with open(PROXY_FILE, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip()]

    if len(keys) != len(proxies):
        raise ValueError(f"[CONFIG] Keys count ({len(keys)}) != proxies count ({len(proxies)})")

    accounts = []
    for i, k in enumerate(keys):
        if "api_key" not in k or "api_secret" not in k:
            raise ValueError(f"[CONFIG] Key entry #{i} missing api_key/api_secret")
        try:
            host, port, user, pwd = proxies[i].split(":")
            proxy_url = f"http://{user}:{pwd}@{host}:{port}"
        except Exception as e:
            raise ValueError(f"[CONFIG] Invalid proxy format at line {i+1}: {proxies[i]} → {e}")
        accounts.append({
            "api_key": k["api_key"],
            "api_secret": k["api_secret"],
            "proxy": {"http": proxy_url, "https": proxy_url}
        })

    return accounts