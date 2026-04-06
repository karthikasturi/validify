"""
utils/decorators.py — Reusable function decorators.

─────────────────────────────────────────────────────────
Day 2 implementation notes
─────────────────────────────────────────────────────────
A decorator is a higher-order function: it takes a function and returns a
(usually enhanced) function. The canonical pattern is always the same:

    def my_decorator(fn):
        @functools.wraps(fn)  # copies __name__, __doc__, __module__ onto wrapper
        def wrapper(*args, **kwargs):
            # before
            result = fn(*args, **kwargs)
            # after
            return result
        return wrapper

functools.wraps is required, not optional: without it fn.__name__ becomes
"wrapper" everywhere the decorated function is inspected — including the
output of timeit itself, which prints the function name.

time.perf_counter() vs time.time():
  perf_counter() has the highest available resolution and is monotonic
  (never goes backward). time.time() is affected by NTP clock adjustments.
  Always use perf_counter() for elapsed-time measurement.

@log_call — the *args and **kwargs are already available inside wrapper.
repr() each argument to get a human-readable string. Be mindful of large
objects (e.g. a 200-row dataset); truncate if needed in production code.
─────────────────────────────────────────────────────────
"""

import functools
import time
from collections.abc import Callable
from typing import Any


def timeit[F: Callable[..., Any]](fn: F) -> F:
    """Print how long a function call takes.

    Output: [timeit] <function_name> took 0.042s

    Usage:
        @timeit
        def run_validation(records, rules):
            ...
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[timeit] {fn.__name__} took {elapsed:.3f}s")
        return result

    return wrapper  # type: ignore[return-value]


def log_call[F: Callable[..., Any]](fn: F) -> F:
    """Print each call to a function with its arguments (stretch).

    Output: [log_call] calling <function_name>(<arg1>, kwarg=<value>)

    Useful for tracing which rules are called on which records during
    debugging, without adding print statements to the rule classes.

    Usage:
        @log_call
        def validate(self, record):
            ...
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        arg_strs = [repr(a) for a in args]
        kwarg_strs = [f"{k}={v!r}" for k, v in kwargs.items()]
        all_args = ", ".join(arg_strs + kwarg_strs)
        print(f"[log_call] calling {fn.__name__}({all_args})")
        return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


# ─────────────────────────────────────────────────────────────────────────────
# TODO Day 5 stretch — async-aware timeit
# ─────────────────────────────────────────────────────────────────────────────
# When engine/runner.py uses asyncio, a synchronous wrapper silently skips
# timing the awaited work. An async-aware version branches on coroutine type:
#
#     import asyncio
#     def timeit(fn):
#         if asyncio.iscoroutinefunction(fn):
#             @functools.wraps(fn)
#             async def async_wrapper(*args, **kwargs):
#                 start = time.perf_counter()
#                 result = await fn(*args, **kwargs)
#                 print(f"[timeit] {fn.__name__} took {time.perf_counter()-start:.3f}s")
#                 return result
#             return async_wrapper
#         ... # existing sync wrapper
