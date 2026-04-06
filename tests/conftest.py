"""tests/conftest.py — Shared pytest fixtures.

This file is provided in full. You do not need to modify it.
The fixtures here are available in all test files automatically.
"""

import pytest


@pytest.fixture
def sample_records() -> list[dict]:
    """
    Three test records:
      - Row 1: fully valid
      - Row 2: passenger_count is empty  → should fail NullCheckRule
      - Row 3: passenger_count is 12     → should fail RangeRule (max is 8)
    """
    return [
        {
            "vendor_id": "CMT",
            "pickup_datetime": "2024-01-15 08:23:00",
            "dropoff_datetime": "2024-01-15 08:41:00",
            "passenger_count": "1",
            "trip_distance": "3.4",
            "fare_amount": "13.50",
            "payment_type": "Credit",
        },
        {
            "vendor_id": "VTS",
            "pickup_datetime": "2024-01-15 09:05:00",
            "dropoff_datetime": "2024-01-15 09:18:00",
            "passenger_count": "",         # empty — NullCheckRule should catch this
            "trip_distance": "1.8",
            "fare_amount": "9.00",
            "payment_type": "Cash",
        },
        {
            "vendor_id": "CMT",
            "pickup_datetime": "2024-01-15 10:12:00",
            "dropoff_datetime": "2024-01-15 10:45:00",
            "passenger_count": "12",       # out of range — RangeRule should catch this
            "trip_distance": "6.2",
            "fare_amount": "22.00",
            "payment_type": "Credit",
        },
    ]


@pytest.fixture
def valid_record(sample_records) -> dict:
    """The single valid record from sample_records."""
    return sample_records[0]


@pytest.fixture
def null_record(sample_records) -> dict:
    """The record with an empty passenger_count field."""
    return sample_records[1]


@pytest.fixture
def out_of_range_record(sample_records) -> dict:
    """The record with passenger_count = 12 (max allowed is 8)."""
    return sample_records[2]
