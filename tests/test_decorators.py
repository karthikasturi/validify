"""
tests/test_decorators.py — Unit tests for utils/decorators.py.

-----------------------------------------------------------------------
Day 5 implementation notes
-----------------------------------------------------------------------
@timeit and @log_call are higher-order functions (decorators). Testing
them means:
  1. The wrapped function still returns the correct value (wraps doesn't
     break the return value).
  2. The side-effect (print to stdout, elapsed > 0) is observable.
  3. functools.wraps preserves __name__ and __doc__.

capsys is a built-in pytest fixture that captures stdout/stderr. Use it
with capsys.readouterr() to assert on printed output.
-----------------------------------------------------------------------
"""

from validify.utils.decorators import log_call, timeit

# ---------------------------------------------------------------------------
# @timeit
# ---------------------------------------------------------------------------

def test_timeit_returns_correct_value():
    @timeit
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_timeit_prints_elapsed_time(capsys):
    @timeit
    def noop():
        return None

    noop()
    out = capsys.readouterr().out
    assert "[timeit]" in out
    assert "noop" in out
    assert "took" in out


def test_timeit_preserves_function_name():
    @timeit
    def my_function():
        """My docstring."""

    assert my_function.__name__ == "my_function"


def test_timeit_preserves_docstring():
    @timeit
    def documented():
        """This is the docstring."""

    assert documented.__doc__ == "This is the docstring."


def test_timeit_elapsed_is_positive(capsys):
    """The reported time must be a non-negative float."""
    @timeit
    def work():
        total = 0
        for i in range(1000):
            total += i
        return total

    work()
    out = capsys.readouterr().out
    # Extract the float from "took X.XXXs"
    import re
    match = re.search(r"took\s+([\d.]+)s", out)
    assert match is not None
    elapsed = float(match.group(1))
    assert elapsed >= 0.0


# ---------------------------------------------------------------------------
# @log_call
# ---------------------------------------------------------------------------

def test_log_call_returns_correct_value():
    @log_call
    def multiply(x, y):
        return x * y

    assert multiply(3, 4) == 12


def test_log_call_prints_call_info(capsys):
    @log_call
    def greet(name):
        return f"Hello, {name}"

    greet("Alice")
    out = capsys.readouterr().out
    # log_call should print the function name and argument(s).
    assert "greet" in out
    assert "Alice" in out


def test_log_call_preserves_function_name():
    @log_call
    def important():
        pass

    assert important.__name__ == "important"
