"""
src/validify/main.py — CLI entry point for the validation pipeline.

─────────────────────────────────────────────────────────
Day 1 implementation notes
─────────────────────────────────────────────────────────
This file produces the same summary output as starter/validate_trips.py,
but the internal structure is fundamentally different:

  1. Rules are objects, not free functions.
     rule(record) calls __call__ on BaseValidator — the object owns its logic.
  2. The rules list IS the pipeline configuration.
     On Day 3 this hardcoded list is replaced by RuleFactory.from_config().
  3. Results are ValidationResult objects collected into a plain list.
     On Day 2 these are wrapped in a Report dataclass with a pass_rate property.
  4. The CSV is opened with plain open() + csv.DictReader.
     On Day 3 a DatasetLoader context manager replaces this.

Compare this file with starter/validate_trips.py side-by-side:
  - Same behaviour, same summary format.
  - Different structure: standalone functions → class hierarchy.
  - Same dataset, reproducible counts — a good self-check after each day.

Progression:
  Day 1 → hardcoded rule list, plain open(), plain list of results
  Day 2 → @timeit decorator, Report dataclass, pass_rate property
  Day 3 → RuleFactory.from_config(), normalize_record(), DatasetLoader
  Day 4 → runner moves to engine/runner.py, exposed via FastAPI
─────────────────────────────────────────────────────────

Run with:
    python src/validify/main.py data/taxi_trips_sample.csv
"""

import sys
from pathlib import Path

from validify.core.models import Report, ValidationResult
from validify.engine.runner import run_sequential
from validify.rules.built_in import RuleFactory
from validify.transforms.pipeline import DatasetLoader, normalize_record

# Day 3: config path relative to CWD (run from the project root).
_CONFIG_PATH = "config/rules.yaml"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python src/validify/main.py <path/to/trips.csv>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: file not found — {csv_path}")
        sys.exit(1)

    # Day 3: load rules from YAML instead of a hardcoded list.
    rules = RuleFactory.from_config(_CONFIG_PATH)

    # Day 3: DatasetLoader context manager — file is always closed on exit.
    # normalize_record strips whitespace from every cell before validation.
    with DatasetLoader(str(csv_path)) as reader:
        records = [normalize_record(row) for row in reader]

    record_count = len(records)
    # Day 4: run_sequential is now in engine/runner.py.
    results = run_sequential(records, rules)

    # ── aggregate results at the record level ─────────────────────────────────
    # A record "passes" only when EVERY rule check on it passes.
    n_rules = len(rules)
    records_passed = 0
    records_failed = 0
    failed_record_details: dict[int, list[ValidationResult]] = {}

    for i in range(record_count):
        chunk = results[i * n_rules: (i + 1) * n_rules]
        failures = [r for r in chunk if not r.passed]
        if failures:
            records_failed += 1
            failed_record_details[i + 1] = failures
        else:
            records_passed += 1

    # Day 2: Report replaces the manual pass_rate formula.
    report = Report(
        total=record_count,
        passed=records_passed,
        failed=records_failed,
        results=results,
    )

    print(f"\nValidation complete — {csv_path.name}")
    print(f"  Records   : {report.total}")
    print(f"  Passed    : {report.passed}")
    print(f"  Failed    : {report.failed}")
    print(f"  Pass rate : {report.pass_rate}%")  # @property — no manual calc

    if failed_record_details:
        print("\nFirst 5 failing records:")
        for rec_idx, failures in list(failed_record_details.items())[:5]:
            print(f"  Record #{rec_idx}:")
            for r in failures:
                print(f"    [{r.rule}] {r.message}")


if __name__ == "__main__":
    main()

