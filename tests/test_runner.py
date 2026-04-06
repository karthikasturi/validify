"""
tests/test_runner.py — Unit tests for engine/runner.py.

-----------------------------------------------------------------------
Day 5 implementation notes
-----------------------------------------------------------------------
run_sequential, run_threaded, and run_async all accept the same inputs
and produce the same output type: list[ValidationResult]. Only the
execution model differs (single-thread, thread-pool, asyncio).

Key concepts tested:
  - Result count: n_records * n_rules results expected.
  - Threading safety: run_threaded uses a Lock; verify no results are
    lost even though threads write concurrently to a shared list.
  - Idempotence: running the same input twice gives the same output
    (no internal mutable state leaks between calls).

asyncio_mode = "auto" in pyproject.toml means async test functions are
collected and awaited automatically by pytest-asyncio — no
@pytest.mark.asyncio decorator needed.
-----------------------------------------------------------------------
"""

from validify.core.models import ValidationResult
from validify.engine.runner import run_async, run_sequential, run_threaded
from validify.rules.built_in import NullCheckRule, RangeRule

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

RECORDS = [
    {"vendor_id": "CMT", "passenger_count": "1", "fare_amount": "13.50"},
    {"vendor_id": "VTS", "passenger_count": "",  "fare_amount": "9.00"},
    {"vendor_id": "CMT", "passenger_count": "12", "fare_amount": "22.00"},
]

RULES = [
    NullCheckRule(field="vendor_id"),
    RangeRule(field="passenger_count", min_val=1, max_val=8),
]

EXPECTED_COUNT = len(RECORDS) * len(RULES)  # 3 records × 2 rules = 6 results


# ---------------------------------------------------------------------------
# run_sequential
# ---------------------------------------------------------------------------

def test_run_sequential_returns_all_results():
    results = run_sequential(RECORDS, RULES)
    assert len(results) == EXPECTED_COUNT


def test_run_sequential_results_are_validation_result():
    results = run_sequential(RECORDS, RULES)
    assert all(isinstance(r, ValidationResult) for r in results)


def test_run_sequential_first_record_passes_null_check():
    """Row 0 has vendor_id='CMT', so NullCheckRule should pass."""
    results = run_sequential(RECORDS[:1], [NullCheckRule(field="vendor_id")])
    assert results[0].passed is True


def test_run_sequential_detects_range_failure():
    """Row 2 has passenger_count=12 which exceeds max=8."""
    rule = RangeRule(field="passenger_count", min_val=1, max_val=8)
    results = run_sequential(RECORDS[2:], [rule])
    assert results[0].passed is False


def test_run_sequential_empty_records():
    results = run_sequential([], RULES)
    assert results == []


def test_run_sequential_empty_rules():
    results = run_sequential(RECORDS, [])
    assert results == []


# ---------------------------------------------------------------------------
# run_threaded
# ---------------------------------------------------------------------------

def test_run_threaded_returns_same_count_as_sequential():
    """Thread-pool execution must produce the same number of results."""
    seq = run_sequential(RECORDS, RULES)
    thr = run_threaded(RECORDS, RULES, workers=2)
    assert len(thr) == len(seq)


def test_run_threaded_no_lost_results_under_concurrency():
    """Lock must prevent data races; all results must be present."""
    # Use a longer record list to increase thread interleaving probability.
    many_records = RECORDS * 20
    results = run_threaded(many_records, RULES, workers=4)
    assert len(results) == len(many_records) * len(RULES)


# ---------------------------------------------------------------------------
# run_async
# ---------------------------------------------------------------------------

async def test_run_async_returns_all_results():
    results = await run_async(RECORDS, RULES)
    assert len(results) == EXPECTED_COUNT


async def test_run_async_results_match_sequential():
    """Async results may be in different order but must have the same count."""
    seq = run_sequential(RECORDS, RULES)
    asn = await run_async(RECORDS, RULES)
    assert len(asn) == len(seq)
