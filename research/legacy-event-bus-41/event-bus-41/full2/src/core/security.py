import hmac
import hashlib
import secrets
import time
from typing import Optional, Tuple

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

def generate_api_key() -> Tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    hashed = hash_token(raw)
    return raw, hashed

def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(raw_key), stored_hash)

class RateLimiter:
    def __init__(self, max_per_minute: int = 120):
        self.max_per_minute = max_per_minute
        self._windows: dict = {}

    def check(self, user_id: str) -> bool:
        now = time.time()
        window_start = now - 60
        if user_id not in self._windows:
            self._windows[user_id] = []
        self._windows[user_id] = [t for t in self._windows[user_id] if t > window_start]
        if len(self._windows[user_id]) >= self.max_per_minute:
            return False
        self._windows[user_id].append(now)
        return True

    def remaining(self, user_id: str) -> int:
        now = time.time()
        window_start = now - 60
        if user_id not in self._windows:
            return self.max_per_minute
        active = [t for t in self._windows[user_id] if t > window_start]
        return max(0, self.max_per_minute - len(active))

rate_limiter = RateLimiter()
