"""
core/base.py — Abstract base classes for the Validify plugin system.

─────────────────────────────────────────────────────────
DAY 1 TASK
─────────────────────────────────────────────────────────
Implement BaseValidator(ABC):

  Abstract method:
      validate(self, record: dict) -> bool
      — Returns True if the record passes, False if it fails.

  Abstract property:
      message(self) -> str
      — Returns the human-readable error description when validate() is False.
      — Return "" (empty string) when there is no failure.

  Concrete method (provide this yourself):
      __call__(self, record: dict) -> ValidationResult
      — Calls self.validate(record)
      — Returns ValidationResult(
             field=self.field,   # the field name this rule checks
             rule=type(self).__name__,
             passed=<result>,
             message=self.message if not passed else "",
         )

Note: every concrete rule (NullCheckRule, RangeRule …) stores the target
field name in self.field. You will set this in each rule's __init__.

─────────────────────────────────────────────────────────
DAY 2 TASK
─────────────────────────────────────────────────────────
After implementing ValidatorRegistry in rules/registry.py,
add it as a second base class here:

    class BaseValidator(ValidatorRegistry, ABC):
        ...

This makes every subclass of BaseValidator automatically register itself.

─────────────────────────────────────────────────────────

Design notes
─────────────────────────────────────────────────────────
1. ABC / @abstractmethod
   - ABC itself does nothing at runtime except keep track of which methods
     are abstract. The enforcement happens at INSTANTIATION time — trying to
     instantiate a class that has not implemented every abstract member raises
     TypeError immediately.
   - This is the Python way of expressing an interface.

2. Abstract property vs abstract method
   - @property + @abstractmethod = subclass MUST define it as a property.
   - message is a property (not a plain method) because its value depends on
     the last call to validate() — it is not known at __init__ time.

3. __call__
   - Making a class callable (__call__) lets rule instances be used as
     functions: result = rule(record).
   - This is the Strategy pattern: the caller does not need to know which
     concrete rule it holds — it just calls it.

4. self.field
   - Every concrete rule stores the target column name in self.field.
   - BaseValidator references self.field in __call__ without declaring it.
   - This is a CONTRACT: every subclass must assign self.field in its
     __init__. Python raises AttributeError at runtime if a subclass forgets,
     which is an intentional design-by-contract signal.
"""

from abc import ABC, abstractmethod
from typing import Any

from validify.core.models import ValidationResult
from validify.rules.registry import ValidatorRegistry


class BaseValidator(ValidatorRegistry, ABC):
    """Abstract base for all validation rules.

    Inheriting from ValidatorRegistry means every concrete subclass is
    automatically registered under its snake_case name when imported.

    Subclasses MUST implement:
      - validate(record) -> bool
      - message property -> str

    Subclasses MUST set self.field in __init__.
    """

    field: str  # must be assigned in each concrete subclass __init__

    # ── abstract interface ────────────────────────────────────────────────

    @abstractmethod
    def validate(self, record: dict[str, Any]) -> bool:
        """Return True if the record's field passes this rule, False otherwise."""

    @property
    @abstractmethod
    def message(self) -> str:
        """Return a human-readable failure description.

        Should describe WHY the last call to validate() returned False.
        Return "" (empty string) when the last call passed — callers check
        this property only after a failure, but defensiveness is good practice.

        This is an @property, not a plain method — read as rule.message, not
        rule.message(). The value changes after each call to validate(), so it
        cannot be a class-level constant.
        """

    # ── concrete behaviour ────────────────────────────────────────────────

    def __call__(self, record: dict[str, Any]) -> ValidationResult:
        """Run this rule against one record and return a ValidationResult.

        This is the Template Method pattern: the base class defines the
        skeleton (call validate, wrap result) and subclasses supply only
        the varying part (the validation logic itself).

        Callers never need to know which concrete rule they hold:
            result = rule(record)   # works for any BaseValidator subclass
        """
        # validate() is called first so that self.message is populated
        # before it is read two lines below.
        passed = self.validate(record)
        return ValidationResult(
            field=self.field,        # set by each concrete rule's __init__
            rule=type(self).__name__,  # e.g. "NullCheckRule"
            passed=passed,
            message="" if passed else self.message,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Day 2 note — MRO with two base classes
# ─────────────────────────────────────────────────────────────────────────────
# class BaseValidator(ValidatorRegistry, ABC):
#
# Python resolves method calls along the MRO: BaseValidator → ValidatorRegistry
# → ABC → object. The order matters:
#   - ValidatorRegistry must come BEFORE ABC so that __init_subclass__ from
#     ValidatorRegistry fires correctly.
#   - ABCMeta (the metaclass behind ABC) cooperates with __init_subclass__
#     because both call super().__init_subclass__(**kwargs) in the chain.
#
# This is already applied above. No further changes needed here for Day 2.
