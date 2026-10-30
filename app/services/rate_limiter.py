import time
import threading
from functools import wraps
from collections import defaultdict
from flask import request, jsonify, current_app


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Does not require Redis or external infrastructure.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # map key -> list of timestamps (float)
        self._hits = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """
        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            # Filter out timestamps outside current window
            timestamps = [t for t in self._hits[key] if t > window_start]
            if len(timestamps) >= limit:
                # Calculate remaining seconds until oldest hit expires
                oldest = timestamps[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                self._hits[key] = timestamps
                return False, retry_after

            timestamps.append(now)
            self._hits[key] = timestamps
            return True, 0

    def reset(self):
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowRateLimiter()


def rate_limit(limit: int = 60, window_seconds: int = 60, key_prefix: str = ""):
    """
    Decorator for rate limiting Flask routes by client IP address.
    Returns HTTP 429 when rate limit is exceeded.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Skip rate limiting in unit tests unless explicitly enabled
            if current_app.config.get("TESTING") and not current_app.config.get("ENABLE_RATE_LIMITS_IN_TESTS"):
                return fn(*args, **kwargs)

            # Get client IP (handle proxies if X-Forwarded-For is present)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            else:
                client_ip = request.remote_addr or "127.0.0.1"

            prefix = key_prefix or fn.__name__
            rate_key = f"{prefix}:{client_ip}"

            allowed, retry_after = limiter.is_allowed(rate_key, limit, window_seconds)
            if not allowed:
                response = jsonify({
                    "error": "Too many requests. Please slow down and try again later.",
                    "retry_after": retry_after,
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

            return fn(*args, **kwargs)
        return wrapper
    return decorator
