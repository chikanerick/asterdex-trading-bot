import hmac
import hashlib
from urllib.parse import urlencode

def sign(params: dict, secret: str) -> str:
    query = urlencode(params, doseq=True)
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()