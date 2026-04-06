"""
api/app.py — FastAPI application with three routes.

─────────────────────────────────────────────────────────
Day 4 implementation notes
─────────────────────────────────────────────────────────
create_app() is a factory function rather than a module-level assignment.
This pattern makes it easy to create isolated test instances with different
configurations without affecting the module-level `app` that uvicorn serves.

POST /validate accepts a CSV file upload. The key steps:
  1. Read uploaded bytes and decode to a string in memory.
  2. Parse with csv.DictReader(io.StringIO(...)) — no temp file needed.
  3. Normalise each row (strip whitespace) as in the CLI pipeline.
  4. Load rules from config/rules.yaml via RuleFactory.
  5. Run validation via run_sequential (or run_threaded for larger files).
  6. Aggregate at record level and build a Report.
  7. Store Report in REPORTS dict keyed by a UUID run_id.
  8. Return run_id + summary so the caller can retrieve full details later.

GET /reports/{run_id} demonstrates path parameters and 404 handling.
HTTPException is re-raised by FastAPI as a proper HTTP error response.

In-memory REPORTS store: intentionally simple for training. A real service
would use a database or cache (Redis) to persist reports across restarts and
share them between multiple server processes.

Run with:
    uvicorn validify.api.app:app --reload
(from the project root so that 'config/rules.yaml' resolves correctly)
─────────────────────────────────────────────────────────
"""

import csv
import io
import uuid

from fastapi import FastAPI, HTTPException, UploadFile

from validify.core.models import Report
from validify.engine.runner import run_sequential
from validify.rules.built_in import RuleFactory
from validify.transforms.pipeline import normalize_record

_CONFIG_PATH = "config/rules.yaml"

# In-memory report store: {run_id: Report}
REPORTS: dict = {}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Validify",
        version="0.1.0",
        description="Enterprise Data Validation & Processing Service",
    )

    @app.get("/health")
    def health() -> dict:
        """Liveness check — returns immediately with no dependencies."""
        return {"status": "ok", "version": "0.1.0"}

    @app.post("/validate")
    async def validate(file: UploadFile) -> dict:
        """Accept a CSV upload, run validation, store the report, return summary."""
        content = (await file.read()).decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        records = [normalize_record(row) for row in reader]

        rules = RuleFactory.from_config(_CONFIG_PATH)
        all_results = run_sequential(records, rules)

        # Aggregate at record level: a record passes only if ALL rule checks pass.
        n_rules = len(rules)
        records_passed = sum(
            1
            for i in range(len(records))
            if all(r.passed for r in all_results[i * n_rules: (i + 1) * n_rules])
        )
        records_failed = len(records) - records_passed

        report = Report(
            total=len(records),
            passed=records_passed,
            failed=records_failed,
            results=all_results,
        )
        run_id = str(uuid.uuid4())
        REPORTS[run_id] = report

        return {
            "run_id": run_id,
            "summary": {
                "total": report.total,
                "passed": report.passed,
                "failed": report.failed,
                "pass_rate": report.pass_rate,
            },
        }

    @app.get("/reports/{run_id}")
    def get_report(run_id: str) -> dict:
        """Return the stored report summary for a previous validation run."""
        if run_id not in REPORTS:
            raise HTTPException(
                status_code=404,
                detail=f"Report {run_id!r} not found. Valid IDs: {list(REPORTS)[:5]}",
            )
        report = REPORTS[run_id]
        return {
            "run_id": run_id,
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "pass_rate": report.pass_rate,
            "failure_count_by_rule": _count_by_rule(report),
        }

    return app


def _count_by_rule(report: Report) -> dict[str, int]:
    """Count failures grouped by rule class name (for the report detail endpoint)."""
    counts: dict[str, int] = {}
    for r in report.results:
        if not r.passed:
            counts[r.rule] = counts.get(r.rule, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


app = create_app()
