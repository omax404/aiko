"""
AIKO UTILITIES
Common helpers and decorators.
"""

import time
import asyncio
from functools import wraps
from typing import TypeVar, Callable

T = TypeVar('T')

def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Retry decorator with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        sleep_time = backoff_factor ** attempt
                        print(f" [Retry] {func.__name__} failed ({e}). Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                        continue
                    raise
            raise last_exception
        return wrapper
    return decorator

def async_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Async Retry decorator."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        sleep_time = backoff_factor ** attempt
                        print(f" [Retry] {func.__name__} failed ({e}). Retrying in {sleep_time}s...")
                        await asyncio.sleep(sleep_time)
                        continue
                    raise
            raise last_exception
        return wrapper
    return decorator
