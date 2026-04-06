"""
tests/test_rules.py — Unit tests for built-in validation rules.

─────────────────────────────────────────────────────────
Day 5 implementation notes
─────────────────────────────────────────────────────────
Each test follows the Arrange-Act-Assert (AAA) pattern:
  Arrange — create the rule and prepare the test record (via fixture).
  Act     — call rule.validate(record) or rule(record).
  Assert  — check the return value and, on failure, the message.

Using fixtures from conftest.py (valid_record, null_record, out_of_range_record)
avoids repeating dict literals in every test. If the fixture is wrong, ALL
tests that use it fail — an early signal that the test data is the problem,
not the rule.

The @dataclass __eq__ generated for ValidationResult means:
    assert rule(record) == ValidationResult(field, rule_name, passed, message)
is a valid assertion without any custom __eq__ on our part.

Run with:
    pytest --cov=src/validify --cov-fail-under=70 --cov-report=term-missing
─────────────────────────────────────────────────────────
"""

from validify.rules.built_in import NullCheckRule, RangeRule, RegexRule, RuleFactory
from validify.rules.registry import ValidatorRegistry

# ---------------------------------------------------------------------------
# Test 1 — NullCheckRule passes when field is present
# ---------------------------------------------------------------------------

def test_null_check_passes_when_field_present(valid_record):
    """NullCheckRule.validate() should return True for a non-empty vendor_id."""
    # Arrange
    rule = NullCheckRule(field="vendor_id")
    # Act + Assert
    assert rule.validate(valid_record) is True


# ---------------------------------------------------------------------------
# Test 2 — NullCheckRule fails when field is empty string
# ---------------------------------------------------------------------------

def test_null_check_fails_when_field_empty(null_record):
    """NullCheckRule.validate() should return False when passenger_count is ''."""
    rule = NullCheckRule(field="passenger_count")
    assert rule.validate(null_record) is False
    # Also verify the message is populated after a failure.
    assert "null or empty" in rule.message


# ---------------------------------------------------------------------------
# Test 3 — RangeRule passes within bounds
# ---------------------------------------------------------------------------

def test_range_rule_passes_within_bounds(valid_record):
    """RangeRule should pass when passenger_count == 1 and bounds are [1, 8]."""
    rule = RangeRule(field="passenger_count", min_val=1, max_val=8)
    assert rule.validate(valid_record) is True


# ---------------------------------------------------------------------------
# Test 4 — RangeRule fails above max
# ---------------------------------------------------------------------------

def test_range_rule_fails_above_max(out_of_range_record):
    """RangeRule should fail when passenger_count == 12 and max is 8."""
    rule = RangeRule(field="passenger_count", min_val=1, max_val=8)
    assert rule.validate(out_of_range_record) is False
    assert "outside" in rule.message


# ---------------------------------------------------------------------------
# Test 5 — Registry auto-registers NullCheckRule on import
# ---------------------------------------------------------------------------

def test_registry_has_null_check_rule():
    """Importing NullCheckRule auto-registers it; get() returns the exact class."""
    # NullCheckRule is already imported at the top, which triggered registration.
    assert ValidatorRegistry.get("null_check_rule") is NullCheckRule


# ---------------------------------------------------------------------------
# Stretch tests
# ---------------------------------------------------------------------------

def test_range_rule_fails_below_min():
    record = {"fare_amount": "-5.0"}
    rule = RangeRule(field="fare_amount", min_val=0.01, max_val=500.0)
    assert rule.validate(record) is False


def test_null_check_fails_when_field_missing():
    rule = NullCheckRule(field="vendor_id")
    assert rule.validate({}) is False  # key absent entirely


def test_regex_rule_passes_valid_payment():
    record = {"payment_type": "Credit"}
    rule = RegexRule(field="payment_type", pattern=r"^(Credit|Cash|No Charge|Dispute)$")
    assert rule.validate(record) is True


def test_regex_rule_fails_invalid_payment():
    record = {"payment_type": "bitcoin"}
    rule = RegexRule(field="payment_type", pattern=r"^(Credit|Cash|No Charge|Dispute)$")
    assert rule.validate(record) is False


def test_rule_factory_loads_from_yaml(tmp_path):
    """RuleFactory.from_config() should load rules from a YAML file."""
    yaml_text = """rules:
  - name: vendor_null
    type: null_check_rule
    field: vendor_id
  - name: pcount_range
    type: range_rule
    field: passenger_count
    min: 1
    max: 8
"""
    cfg = tmp_path / "rules.yaml"
    cfg.write_text(yaml_text)
    rules = RuleFactory.from_config(str(cfg))
    assert len(rules) == 2
    assert isinstance(rules[0], NullCheckRule)
    assert isinstance(rules[1], RangeRule)


def test_validation_result_eq():
    """@dataclass __eq__: two ValidationResult objects with same values are equal."""
    from validify.core.models import ValidationResult
    r1 = ValidationResult("vendor_id", "NullCheckRule", False, "'vendor_id' is null or empty")
    r2 = ValidationResult("vendor_id", "NullCheckRule", False, "'vendor_id' is null or empty")
    assert r1 == r2


def test_report_pass_rate():
    """Report.pass_rate returns the correct percentage rounded to 1 decimal."""
    from validify.core.models import Report
    report = Report(total=200, passed=110, failed=90, results=[])
    assert report.pass_rate == 55.0

    zero_report = Report(total=0, passed=0, failed=0)
    assert zero_report.pass_rate == 0.0
