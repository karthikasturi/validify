"""
core/models.py — Domain models for Validify.

─────────────────────────────────────────────────────────
DAY 1 TASK
─────────────────────────────────────────────────────────
Implement ValidationResult as a plain class (not a dataclass yet):

    class ValidationResult:
        def __init__(self, field, rule, passed, message):
            ...

Fields:
  field   (str)  — the CSV column name that was checked
  rule    (str)  — the rule class name (e.g. "NullCheckRule")
  passed  (bool) — True if the check succeeded
  message (str)  — human-readable description of the failure ("" if passed)

─────────────────────────────────────────────────────────
DAY 2 TASK
─────────────────────────────────────────────────────────
1. Convert ValidationResult to @dataclass.
   Add __repr__ (automatic with dataclass) and confirm __eq__ works.

2. Add DataRecord dataclass:
      row_number : int
      fields     : dict[str, str]

3. Add Report dataclass:
      total   : int
      passed  : int
      failed  : int
      results : list[ValidationResult]   ← use field(default_factory=list)

   Add a @property:
      pass_rate -> float   (0.0 to 100.0, rounded to 1 decimal)

Hint: import dataclass and field from the dataclasses module.
"""

"""
core/models.py — Domain models for Validify.

─────────────────────────────────────────────────────────
Day 2 implementation notes
─────────────────────────────────────────────────────────
ValidationResult is now a @dataclass. Compare with the Day 1 plain class:
  - @dataclass generates __init__, __repr__, and __eq__ automatically.
  - The 15 lines of manual boilerplate (__init__ + __repr__) reduce to
    4 annotated field declarations. The data itself does not change at all.
  - __eq__ is now generated too — two ValidationResult objects with the same
    field values are considered equal. This is essential for test assertions:
        assert result == ValidationResult("vendor_id", "NullCheckRule", False, ...)

DataRecord pairs a row number with the raw CSV fields so callers can report
WHERE in the file a failure occurred without passing those two things separately.

Report aggregates per-record counts (not per-check counts) and exposes
pass_rate as a @property. The formula lives in one place and is easy to test;
no caller ever computes pass_rate manually again.
─────────────────────────────────────────────────────────
"""

from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# Day 2 — @dataclass versions
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Outcome of a single rule applied to a single record.

    @dataclass generates __init__, __repr__, and __eq__ automatically.
    Compare with Day 1: the data is identical; the boilerplate is gone.
    """

    field: str    # CSV column name that was checked
    rule: str     # rule class name, e.g. "NullCheckRule"
    passed: bool  # True if the check succeeded
    message: str  # human-readable failure description ("" if passed)


@dataclass
class DataRecord:
    """A single CSV row labelled with its 1-based position in the file.

    Keeping row_number alongside fields avoids passing them as separate
    arguments to every reporting function.
    """

    row_number: int
    fields: dict[str, str]


@dataclass
class Report:
    """Aggregated outcome of running all rules against all records.

    total, passed, failed are record-level counts: a record counts as
    failed if even one rule check failed on it.

    results holds every ValidationResult across all records and rules.
    field(default_factory=list) ensures each Report instance gets its own
    list rather than sharing one mutable default across instances.

    pass_rate is a @property so the formula lives in one place and callers
    never compute it manually.
    """

    total: int
    passed: int
    failed: int
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Percentage of records that passed all checks (0.0–100.0, 1 decimal)."""
        if self.total == 0:
            return 0.0
        return round(self.passed / self.total * 100, 1)
