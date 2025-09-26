import requests
from config.settings import BASE_URL
from utils.time_utils import now_ms
from network.signer import sign

REQUEST_TIMEOUT = 10.0
def raise_with_body(r: requests.Response, path: str):
    try:
        msg = r.json()
    except Exception:
        msg = r.text
    raise RuntimeError(f"HTTP {r.status_code} {r.request.method} {path}: {msg}")

def public_get(path: str, params: dict = None) -> dict:
    url = f"{BASE_URL}{path}"
    r = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
    if not r.ok:
        raise_with_body(r, path)
    return r.json()

def private_post(path: str, account: dict, params: dict) -> dict:
    params = dict(params)
    params.setdefault("recvWindow", 5000)
    params.setdefault("timestamp", now_ms())
    params["signature"] = sign(params, account["api_secret"])
    headers = {
        "X-MBX-APIKEY": account["api_key"],
        "Content-Type": "application/x-www-form-urlencoded"
    }
    url = f"{BASE_URL}{path}"
    r = requests.post(url, headers=headers, data=params, timeout=REQUEST_TIMEOUT, proxies=account["proxy"])
    if not r.ok:
        raise_with_body(r, path)
    return r.json()

def private_get(path: str, account: dict, params: dict = None) -> dict:
    params = dict(params or {})
    params.setdefault("recvWindow", 5000)
    params.setdefault("timestamp", now_ms())
    params["signature"] = sign(params, account["api_secret"])
    headers = {"X-MBX-APIKEY": account["api_key"]}
    url = f"{BASE_URL}{path}"
    r = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT, proxies=account["proxy"])
    if not r.ok:
        raise_with_body(r, path)
    return r.json()