"""
rules/registry.py — Auto-registration plugin system for validators.

─────────────────────────────────────────────────────────
DAY 2 TASK
─────────────────────────────────────────────────────────
Implement ValidatorRegistry using Python's __init_subclass__ hook.

Requirements:
  - Class-level dict: _registry: dict[str, type] = {}
  - __init_subclass__ must convert the subclass name to snake_case and store it.
    e.g. "NullCheckRule" → "null_check_rule"
  - Class method: get(name: str) -> type
    — Looks up the registry and returns the class.
    — Raises KeyError with a helpful message if the name is not found.

After implementation, make BaseValidator inherit from ValidatorRegistry:

    class BaseValidator(ValidatorRegistry, ABC):
        ...

Then any class that inherits from BaseValidator will auto-register itself
when its module is imported. No manual wiring needed.

─────────────────────────────────────────────────────────
HINT — converting CamelCase to snake_case:
─────────────────────────────────────────────────────────
    import re
    name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
    # "NullCheckRule" → "null_check_rule"

─────────────────────────────────────────────────────────
CHECKPOINT (paste into a Python REPL to verify your work):
─────────────────────────────────────────────────────────
    from validify.rules.built_in import NullCheckRule   # triggers registration
    from validify.rules.registry import ValidatorRegistry

    assert ValidatorRegistry.get("null_check_rule") is NullCheckRule
    print("Registry works!")
"""

"""
rules/registry.py — Auto-registration plugin system for validators.

─────────────────────────────────────────────────────────
Day 2 implementation notes
─────────────────────────────────────────────────────────
__init_subclass__ is called by Python automatically every time a class
inherits from ValidatorRegistry. The call happens at CLASS DEFINITION TIME
(when the module containing the subclass is imported), not at instantiation
time. Consequences:
  - No explicit registration call is ever needed.
  - Importing built_in.py is sufficient to register NullCheckRule, RangeRule,
    CoordinateRule, and DateFormatRule.
  - The registry is fully populated before any rule is instantiated.

_registry is a CLASS-LEVEL variable on ValidatorRegistry, so all subclasses
share the same dict through the MRO. Making it a module-level global would
work too, but keeping it on the class makes it easier to inspect, mock,
or reset in tests.

CamelCase → snake_case — how the regex works:
  re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
  (?<!^)   — not at the start of the string
  (?=[A-Z]) — at a position immediately before an uppercase letter
  This inserts "_" before each internal capital, then lowercases everything.
  "NullCheckRule" → "Null_Check_Rule" → "null_check_rule"
─────────────────────────────────────────────────────────
"""

import re


class ValidatorRegistry:
    """Mixin that auto-registers each concrete subclass by its snake_case name.

    Any class that inherits (directly or via BaseValidator) from
    ValidatorRegistry is recorded in _registry when its module is imported.
    No manual wiring needed.

    Checkpoint — paste into a Python REPL to verify:
        from validify.rules.built_in import NullCheckRule
        from validify.rules.registry import ValidatorRegistry
        assert ValidatorRegistry.get("null_check_rule") is NullCheckRule
        print("Registry works!")
    """

    _registry: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Convert CamelCase class name to snake_case registry key.
        # e.g. "NullCheckRule" → "null_check_rule"
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        ValidatorRegistry._registry[name] = cls

    @classmethod
    def get(cls, name: str) -> type:
        """Return the validator class registered under the given snake_case name.

        Raises KeyError with a helpful message listing available names if not
        found. Used by RuleFactory.from_config() on Day 3.
        """
        if name not in cls._registry:
            available = ", ".join(sorted(cls._registry))
            raise KeyError(
                f"No validator registered as {name!r}. "
                f"Available: {available or '(none yet — did you import built_in?)'}"
            )
        return cls._registry[name]
