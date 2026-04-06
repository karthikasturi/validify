"""
transforms/pipeline.py — Functional transformation pipeline.

─────────────────────────────────────────────────────────
DAY 3 TASK — Part A (mandatory)
─────────────────────────────────────────────────────────
1. Implement pipe(*fns) using functools.reduce:

       pipe(f, g, h)(x)  ==  h(g(f(x)))

   Each function takes one value and returns one value.
   Use functools.reduce to chain them left to right.

   Example:
       strip  = lambda d: {k: v.strip() for k, v in d.items()}
       result = pipe(strip, normalize_record)(raw_record)

2. Implement normalize_record(record: dict) -> dict:
   - Strip leading/trailing whitespace from all string values.
   - That is the minimum. Keep it simple.

─────────────────────────────────────────────────────────
DAY 3 TASK — Part B (stretch)
─────────────────────────────────────────────────────────
3. Implement DatasetLoader as a context manager:

       class DatasetLoader:
           def __init__(self, path: str) -> None: ...
           def __enter__(self) -> Iterator[dict]: ...
           def __exit__(self, *args) -> None: ...

   - Opens the CSV file in __enter__.
   - Yields a generator of dict rows (one per CSV row).
   - Does NOT load the full file into memory (use csv.DictReader lazily).
   - Closes the file handle in __exit__.
   - Raises DataLoadError (from core.exceptions) if the file is not found.

   Usage in main.py (after implementation):
       with DatasetLoader("data/taxi_trips_sample.csv") as records:
           for record in records:
               ...
"""

import csv  # noqa: F401
from functools import reduce  # noqa: F401
from typing import Callable, Iterator, TypeVar  # noqa: F401

from validify.core.exceptions import DataLoadError  # noqa: F401

T = TypeVar("T")


# ─────────────────────────────────────────────────────────────────────────────
# Day 3 implementation notes
# ─────────────────────────────────────────────────────────────────────────────
# pipe() is the functional composition primitive. functools.reduce chains the
# functions left-to-right: pipe(f, g, h)(x) == h(g(f(x))). Contrast with the
# math convention where composition is right-to-left.
#
# normalize_record() is intentionally minimal — strip whitespace, nothing else.
# More transforms (type coercion, field renaming) follow the same pattern and
# can be added to the pipe without changing any rule code.
#
# DatasetLoader implements the context manager protocol (__enter__/__exit__).
# The key property: __exit__ is ALWAYS called when leaving the with block,
# even if an exception is raised inside it. This is why context managers are
# the standard pattern for resource management in Python.
# ─────────────────────────────────────────────────────────────────────────────


def pipe(*fns: Callable) -> Callable:
    """Return a function that applies *fns left to right to a single value.

    pipe(f, g, h)(x)  ==  h(g(f(x)))

    Each function receives the output of the previous one. This is the
    functional-programming equivalent of a Unix pipe: data flows through
    a sequence of transformations, each doing one thing.

    Example:
        clean = pipe(
            lambda d: {k: v.strip() for k, v in d.items()},
            normalize_record,
        )
        cleaned_record = clean(raw_record)
    """
    return reduce(lambda acc, fn: lambda x: fn(acc(x)), fns)


def normalize_record(record: dict) -> dict:
    """Return a copy of record with all string values stripped of whitespace.

    CSV cells often carry leading/trailing spaces from export tools. Stripping
    them here means every downstream rule sees clean values without needing its
    own .strip() call. Non-string values (None, numbers) are passed through.
    """
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in record.items()}


class DatasetLoader:
    """Context manager that opens a CSV file and yields dict rows lazily.

    Usage:
        with DatasetLoader("data/taxi_trips_sample.csv") as records:
            for record in records:
                ...   # record is one dict row; file is not loaded into memory

    The file is opened in __enter__ and closed in __exit__, so the file handle
    is always released even if an exception occurs inside the with block.
    Raises DataLoadError if the file does not exist.

    Lazy iteration (via csv.DictReader) means an arbitrarily large CSV file
    never needs to fit in memory at once.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._file = None

    def __enter__(self) -> Iterator[dict]:
        try:
            self._file = open(self.path, newline="", encoding="utf-8")
        except FileNotFoundError as exc:
            raise DataLoadError(path=self.path, reason="file not found") from exc
        # csv.DictReader is a lazy iterator — it reads one line at a time.
        return csv.DictReader(self._file)

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._file:
            self._file.close()  # always runs, even if the with body raised an error
