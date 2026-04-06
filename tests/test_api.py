"""
tests/test_api.py — Integration tests for the FastAPI application.

-----------------------------------------------------------------------
Day 5 implementation notes
-----------------------------------------------------------------------
FastAPI's TestClient (powered by httpx) lets us exercise the full HTTP
request-response cycle in a single process without starting a real server.

create_app() is the factory used in api/app.py. Calling it in the
fixture gives each test a fresh app instance (no shared REPORTS state
between tests).

The CSV payload in test_validate_returns_report uses only 2 rows to
keep the test fast and assertions simple. The key things to verify:
  - 200 status and a run_id are returned.
  - pass_rate, total, passed, failed are in the expected ranges.
  - GET /reports/{run_id} retrieves the same run.
  - GET /reports/<garbage> returns 404.
-----------------------------------------------------------------------
"""

import io
import csv
import pytest

from fastapi.testclient import TestClient

from validify.api.app import create_app


SAMPLE_CSV_ROWS = [
    {
        "vendor_id": "CMT",
        "pickup_datetime": "2024-01-15 08:23:00",
        "dropoff_datetime": "2024-01-15 08:41:00",
        "passenger_count": "1",
        "trip_distance": "3.4",
        "pickup_longitude": "-73.982",
        "pickup_latitude": "40.768",
        "dropoff_longitude": "-73.951",
        "dropoff_latitude": "40.784",
        "fare_amount": "13.50",
        "payment_type": "Credit",
    },
    {
        "vendor_id": "VTS",
        "pickup_datetime": "2024-01-15 09:05:00",
        "dropoff_datetime": "2024-01-15 09:18:00",
        "passenger_count": "",         # will fail NullCheckRule
        "trip_distance": "1.8",
        "pickup_longitude": "-73.951",
        "pickup_latitude": "40.784",
        "dropoff_longitude": "-73.935",
        "dropoff_latitude": "40.798",
        "fare_amount": "-5.00",        # will fail RangeRule
        "payment_type": "Cash",
    },
]


def _make_csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


# ---------------------------------------------------------------------------
# POST /validate
# ---------------------------------------------------------------------------

def test_validate_returns_200_and_run_id(client):
    payload = _make_csv_bytes(SAMPLE_CSV_ROWS)
    response = client.post(
        "/validate",
        files={"file": ("test.csv", payload, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "run_id" in body
    assert "summary" in body


def test_validate_summary_fields(client):
    payload = _make_csv_bytes(SAMPLE_CSV_ROWS)
    body = client.post(
        "/validate",
        files={"file": ("test.csv", payload, "text/csv")},
    ).json()

    summary = body["summary"]
    assert summary["total"] == 2
    assert summary["passed"] + summary["failed"] == 2
    assert 0.0 <= summary["pass_rate"] <= 100.0


# ---------------------------------------------------------------------------
# GET /reports/{run_id}
# ---------------------------------------------------------------------------

def test_get_report_after_validate(client):
    payload = _make_csv_bytes(SAMPLE_CSV_ROWS)
    run_id = client.post(
        "/validate",
        files={"file": ("test.csv", payload, "text/csv")},
    ).json()["run_id"]

    response = client.get(f"/reports/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert "pass_rate" in body


def test_get_report_404_for_unknown_run_id(client):
    response = client.get("/reports/does-not-exist")
    assert response.status_code == 404
