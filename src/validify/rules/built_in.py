"""
rules/built_in.py — Concrete validation rules and rule factory.

─────────────────────────────────────────────────────────
DAY 1 TASK
─────────────────────────────────────────────────────────
Implement concrete rules as subclasses of BaseValidator.
Each mirrors a function in starter/validate_trips.py:

  NullCheckRule(field: str)
    — Fails when the field is absent, None, or an empty/whitespace string.
    — Mirror of: check_not_null()

  RangeRule(field: str, min: float, max: float)
    — Fails when the field is not a number or is outside [min, max].
    — Mirror of: check_range()

  CoordinateRule(field: str, min: float, max: float)
    — Fails when a geographic coordinate is outside the bounding box.
    — Mirror of: check_coordinate()
    — Hint: the logic is almost identical to RangeRule — what does this
      tell you about inheritance or composition?

Part B (stretch):
  DateFormatRule(field: str, fmt: str = "%Y-%m-%d %H:%M:%S")
    — Fails when the field cannot be parsed as a datetime in the given format.
    — Mirror of: check_date_format()

Each rule must store self.field and any other config params in __init__.
The 'type' name used in config/rules.yaml is the snake_case class name:
  NullCheckRule  → null_check_rule
  RangeRule      → range_rule
  CoordinateRule → coordinate_rule
  DateFormatRule → date_format_rule

─────────────────────────────────────────────────────────
DAY 3 TASK — add RegexRule and RuleFactory
─────────────────────────────────────────────────────────
  RegexRule(field: str, pattern: str)
    — Fails when the field value does not match re.fullmatch(pattern, value).
    — Mirror of: check_allowed_values() but more general.
    — Needed for the payment_type rule in config/rules.yaml.
    — type name: regex_rule

  RuleFactory:
      @staticmethod
      def from_config(path: str) -> list[BaseValidator]:
          # 1. Open and parse the YAML file.
          # 2. For each entry, look up the class: ValidatorRegistry.get(entry["type"])
          # 3. Instantiate it passing the remaining keys as kwargs.
          # 4. Return the list.

─────────────────────────────────────────────────────────
DAY 5 — Git exercise
─────────────────────────────────────────────────────────
On a feature branch, add RegexRule if not done yet, confirm it is
registered and works via a unit test, then merge back to main.
"""

"""
─────────────────────────────────────────────────────────
Day 1 implementation notes
─────────────────────────────────────────────────────────
PATTERN: every rule has exactly three responsibilities
  __init__ : store config (field name + bounds/format)
  validate : one boolean check against a record dict
  message  : human-readable reason, populated after validate()

This is the Single Responsibility Principle at the method level —
each method does exactly one thing.

PATTERN: subclassing is meaningful here
  All four rules ARE-A BaseValidator (inheritance is appropriate).
  They differ only in the type of check, not in their lifecycle.
  Compare with starter/validate_trips.py where four standalone functions
  share no structure at all.

PATTERN: CoordinateRule vs RangeRule
  The validation logic is identical — the only difference is the name.
  Consider: should CoordinateRule inherit from RangeRule, or be its own
  class that duplicates the logic? Neither answer is wrong.
  The key insight is that naming communicates intent. A separate class
  makes coordinate checks instantly recognisable in code review and logs,
  and leaves room for coordinate-specific behaviour later (e.g. pair checks).
  In Day 3, config/rules.yaml refers to them by distinct type names.

PATTERN: message is a @property
  It returns a different string depending on what validate() stored in
  self._message. This is a computed attribute, not a constant.
  Compare: starter/validate_trips.py hardcoded messages as f-strings
  inside each function. Here the message belongs to the rule object and
  is constructed only when a failure actually occurs.
─────────────────────────────────────────────────────────
"""

import re  # needed by RegexRule (Day 3)
import yaml  # needed by RuleFactory (Day 3)
from datetime import datetime

from validify.core.base import BaseValidator
from validify.core.exceptions import ConfigError


# ─────────────────────────────────────────────────────────────────────────────
# Day 1 — Mandatory rules
# ─────────────────────────────────────────────────────────────────────────────


class NullCheckRule(BaseValidator):
    """Fail when a field is absent, None, or blank/whitespace.

    In a CSV file, "null" is just an empty string. strip() is applied so
    that a cell containing only spaces is also treated as empty.
    self._message is written only when a failure is detected, so the string
    always reflects the actual bad value rather than a generic placeholder.
    """

    def __init__(self, field: str) -> None:
        self.field = field
        self._message = ""

    def validate(self, record: dict) -> bool:
        value = record.get(self.field)
        if value is None or str(value).strip() == "":
            self._message = f"{self.field!r} is null or empty"
            return False
        return True

    @property
    def message(self) -> str:
        return self._message


class RangeRule(BaseValidator):
    """Fail when a numeric field is outside the closed interval [min_val, max_val].

    CSV values are always strings, so float() conversion is required.
    The try/except around float() means a non-numeric cell produces a
    descriptive failure message instead of an unhandled ValueError that
    would crash the whole pipeline.
    """

    def __init__(self, field: str, min_val: float, max_val: float) -> None:
        self.field = field
        self.min_val = min_val
        self.max_val = max_val
        self._message = ""

    def validate(self, record: dict) -> bool:
        raw = record.get(self.field)
        if raw is None or str(raw).strip() == "":
            self._message = f"{self.field!r} is missing"
            return False
        try:
            value = float(raw)
        except (ValueError, TypeError):
            self._message = f"{self.field!r} is not a number: {raw!r}"
            return False
        if not (self.min_val <= value <= self.max_val):
            self._message = (
                f"{self.field!r} = {value} is outside [{self.min_val}, {self.max_val}]"
            )
            return False
        return True

    @property
    def message(self) -> str:
        return self._message


class CoordinateRule(BaseValidator):
    """Fail when a geographic coordinate is outside a bounding box.

    Logically identical to RangeRule — a separate class is justified because:
      1. The config/rules.yaml type name 'coordinate_rule' is self-documenting.
      2. Any reader immediately understands what kind of data this checks.
      3. Coordinate-specific behaviour (e.g. validating lon/lat as a pair)
         can be added here without touching the general RangeRule.
    """

    def __init__(self, field: str, min_val: float, max_val: float) -> None:
        self.field = field
        self.min_val = min_val
        self.max_val = max_val
        self._message = ""

    def validate(self, record: dict) -> bool:
        raw = record.get(self.field)
        if raw is None or str(raw).strip() == "":
            self._message = f"{self.field!r} coordinate is missing"
            return False
        try:
            value = float(raw)
        except (ValueError, TypeError):
            self._message = f"{self.field!r} is not a number: {raw!r}"
            return False
        if not (self.min_val <= value <= self.max_val):
            self._message = (
                f"{self.field!r} = {value} out of bounds "
                f"[{self.min_val}, {self.max_val}]"
            )
            return False
        return True

    @property
    def message(self) -> str:
        return self._message


# ─────────────────────────────────────────────────────────────────────────────
# Day 1 (stretch) — DateFormatRule
# ─────────────────────────────────────────────────────────────────────────────


class DateFormatRule(BaseValidator):
    """Fail when a field cannot be parsed as a datetime in the given format.

    datetime.strptime raises ValueError for any string that does not match
    the format exactly. Catching it and returning False is idiomatic Python
    ("easier to ask forgiveness than permission").
    The default format matches the one used in starter/validate_trips.py,
    so the two implementations are directly comparable.
    """

    def __init__(self, field: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> None:
        self.field = field
        self.fmt = fmt
        self._message = ""

    def validate(self, record: dict) -> bool:
        raw = record.get(self.field)
        if raw is None or str(raw).strip() == "":
            self._message = f"{self.field!r} is missing"
            return False
        try:
            datetime.strptime(str(raw), self.fmt)
            return True
        except ValueError:
            self._message = (
                f"{self.field!r} = {raw!r} does not match format {self.fmt!r}"
            )
            return False

    @property
    def message(self) -> str:
        return self._message


# ─────────────────────────────────────────────────────────────────────────────
# Day 3 — RegexRule and RuleFactory
# ─────────────────────────────────────────────────────────────────────────────
# RegexRule generalises check_allowed_values() from the starter script.
# Instead of a hardcoded list of allowed values, any valid Python regex works.
# re.fullmatch() requires the ENTIRE string to match (not just a substring).
#
# RuleFactory reads rules.yaml and builds the rule list without any hardcoding
# in Python. Adding a new rule requires only a new entry in the YAML file.
#
# Key mapping note: rules.yaml uses "min"/"max" (human-friendly) but
# RangeRule/CoordinateRule expect "min_val"/"max_val". RuleFactory remaps
# these keys before passing kwargs to the constructor.

import re as _re_module  # already imported at top as 're'; alias to avoid shadowing
from validify.rules.registry import ValidatorRegistry


class RegexRule(BaseValidator):
    """Fail when a field value does not fully match a regular expression.

    re.fullmatch() is used rather than re.search() so that the pattern must
    cover the entire cell value, not just a substring. This is important for
    enumerations like payment_type: '^(Credit|Cash)$' would reject 'Cash extra'
    rather than silently matching the 'Cash' substring.
    """

    def __init__(self, field: str, pattern: str) -> None:
        self.field = field
        self.pattern = pattern
        self._compiled = re.compile(pattern)
        self._message = ""

    def validate(self, record: dict) -> bool:
        raw = record.get(self.field)
        if raw is None or str(raw).strip() == "":
            self._message = f"{self.field!r} is missing"
            return False
        if not self._compiled.fullmatch(str(raw)):
            self._message = (
                f"{self.field!r} = {raw!r} does not match pattern {self.pattern!r}"
            )
            return False
        return True

    @property
    def message(self) -> str:
        return self._message


class RuleFactory:
    """Create a list of BaseValidator instances from a YAML config file.

    Replacing the hardcoded rule list in main.py with a single call to
    RuleFactory.from_config() decouples configuration from code: thresholds,
    patterns, and new rules can be changed without touching any Python.
    """

    @staticmethod
    def from_config(path: str) -> list[BaseValidator]:
        """Parse rules.yaml and return a ready-to-use list of validators.

        Each YAML entry must have a 'type' key that matches a registered
        snake_case class name. All other keys are passed as keyword arguments
        to the class constructor.

        The 'name' key is a human-readable label for the YAML; it is not
        a constructor argument and is stripped before instantiation.

        The YAML keys 'min'/'max' are remapped to 'min_val'/'max_val' to
        match the RangeRule and CoordinateRule constructor signatures while
        keeping the YAML readable ("min" is more natural than "min_val").
        """
        try:
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError as exc:
            raise ConfigError(f"Rules config not found: {path}") from exc

        rules: list[BaseValidator] = []
        for entry in config.get("rules", []):
            kwargs = dict(entry)
            rule_type = kwargs.pop("type")
            kwargs.pop("name", None)  # metadata only, not a constructor arg
            # remap YAML-friendly keys to constructor parameter names
            if "min" in kwargs:
                kwargs["min_val"] = kwargs.pop("min")
            if "max" in kwargs:
                kwargs["max_val"] = kwargs.pop("max")
            cls = ValidatorRegistry.get(rule_type)
            rules.append(cls(**kwargs))
        return rules


# ─────────────────────────────────────────────────────────────────────────────
# TODO Day 5 stretch — add a TripDurationRule (two-field rule)
# ─────────────────────────────────────────────────────────────────────────────
# A rule that derives a value from two fields (pickup/dropoff datetime) rather
# than one cannot follow the single-field BaseValidator contract without
# adaptation. Design question: change the interface, compose two rules, or
# add an optional second field? Explore the tradeoffs on Day 5.
