import time
from functools import wraps
from typing import Any, Callable

CACHE_TTL = 300


class DashboardCache:
    def __init__(self, ttl: int = CACHE_TTL):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Any:
        if key in self._cache:
            ts, value = self._cache[key]
            if time.time() - ts < self._ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        self._cache[key] = (time.time(), value)

    def invalidate(self, key: str = None):
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()


_cache = DashboardCache()


def cached(key_fn: Callable = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = key_fn(*args, **kwargs) if key_fn else f"{func.__name__}:{args}:{kwargs}"
            result = _cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            _cache.set(key, result)
            return result
        return wrapper
    return decorator