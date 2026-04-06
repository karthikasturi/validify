"""
engine/runner.py — Validation execution engines.

─────────────────────────────────────────────────────────
Day 4 implementation notes
─────────────────────────────────────────────────────────
run_sequential is the baseline: one record at a time, one thread.
All validation work in the starter script was also sequential; this is
its direct object-oriented equivalent.

run_threaded uses ThreadPoolExecutor to process records concurrently.
Each worker thread picks up one record, runs all rules on it, then
extends the shared results list under a Lock.

Why a Lock? Each rule call returns a separate ValidationResult. Without
a Lock, two threads could interleave their results.extend() calls and
produce a results list whose order is non-deterministic. With the Lock,
extend is atomic per record, so the list stays consistent.

GIL note: Python's Global Interpreter Lock means only one thread executes
CPython bytecode at a time. For CPU-bound pure-Python work (like field
validation) threading adds thread-switching overhead without true
parallelism. You will likely see run_threaded SLOWER than run_sequential
on small CSV files. For I/O-bound work (network calls, disk reads) or
CPython extensions that release the GIL (e.g. NumPy, regex on large
strings), threading does provide speedup. ProcessPoolExecutor avoids the
GIL entirely but has higher process-spawn overhead.

run_async uses asyncio coroutines. It is best suited for I/O-bound tasks
(e.g. rules that call an external API to validate a postcode). For pure
in-memory validation it provides no benefit over sequential, but it
demonstrates the async/await pattern and asyncio.gather.
─────────────────────────────────────────────────────────
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any

from validify.core.base import BaseValidator
from validify.core.models import ValidationResult
from validify.utils.decorators import timeit


@timeit
def run_sequential(
    records: list[dict[str, Any]], rules: list[BaseValidator]
) -> list[ValidationResult]:
    """Validate every record against every rule in a single thread.

    Returns a flat list of ValidationResult in row-major order:
    all rules for records[0], then all rules for records[1], etc.
    This ordering makes aggregation at the record level trivial.
    """
    results: list[ValidationResult] = []
    for record in records:
        for rule in rules:
            results.append(rule(record))
    return results


@timeit
def run_threaded(
    records: list[dict[str, Any]],
    rules: list[BaseValidator],
    workers: int = 4,
) -> list[ValidationResult]:
    """Validate records concurrently using a thread pool.

    Each worker validates one record (all rules) and appends its results
    to the shared list under a Lock. The ordering of records in the
    output list is non-deterministic (whichever thread finishes first
    writes first), so use this runner when order does not matter.

    Compare elapsed time with run_sequential on larger datasets:
    for pure in-memory validation the GIL means threading rarely wins.
    """
    results: list[ValidationResult] = []
    lock = Lock()

    def _validate_one(record: dict[str, Any]) -> None:
        local = [rule(record) for rule in rules]
        with lock:
            results.extend(local)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        pool.map(_validate_one, records)

    return results


async def run_async(
    records: list[dict[str, Any]], rules: list[BaseValidator]
) -> list[ValidationResult]:
    """Validate records concurrently using asyncio (stretch — Day 4).

    Each record is validated inside a coroutine. asyncio.gather() runs all
    coroutines on the event loop and collects their results. Because the
    validation logic is synchronous (no await points), the coroutines take
    turns rather than running in true concurrency, so performance is similar
    to run_sequential. The value is in learning the async/await pattern:
    if any rule ever needs to await an external service, this runner is ready.

    Usage (from an async context or main entry point):
        results = asyncio.run(run_async(records, rules))
    """

    async def _validate_one(record: dict[str, Any]) -> list[ValidationResult]:
        return [rule(record) for rule in rules]

    nested = await asyncio.gather(*[_validate_one(r) for r in records])
    # nested is a list of lists; flatten it.
    return [result for record_results in nested for result in record_results]
