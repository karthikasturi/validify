"""
tests/test_pipeline.py — Unit tests for transforms/pipeline.py.

-----------------------------------------------------------------------
Day 5 implementation notes
-----------------------------------------------------------------------
These tests cover three functional pieces introduced in Day 3:

  pipe(*fns)           — compose functions left to right.
  normalize_record()   — strip whitespace from string values.
  DatasetLoader        — context manager that opens a CSV and returns a
                         DictReader; raises DataLoadError on missing file.

Key techniques used here:
  - tmp_path fixture (built into pytest) for temporary files/dirs.
  - Parametrize would also work well here, but explicit test functions
    make the failure messages clearer for beginners.
  - DatasetLoader is side-effect heavy (file I/O); we test the real
    behaviour rather than mocking. This is preferable when the side
    effect is cheap and deterministic.
-----------------------------------------------------------------------
"""

import pytest

from validify.core.exceptions import DataLoadError
from validify.transforms.pipeline import DatasetLoader, normalize_record, pipe

# ---------------------------------------------------------------------------
# pipe()
# ---------------------------------------------------------------------------

def test_pipe_single_function():
    """A pipeline with one function behaves identically to calling that function."""
    double = pipe(lambda x: x * 2)
    assert double(5) == 10


def test_pipe_two_functions():
    """pipe applies functions left to right: add1 then double."""
    add1 = lambda x: x + 1      # noqa: E731
    double = lambda x: x * 2    # noqa: E731
    transform = pipe(add1, double)
    assert transform(3) == 8    # (3+1)*2 = 8


def test_pipe_three_functions():
    """Functions are composed in left-to-right order."""
    result = pipe(str.upper, str.strip, lambda s: s + "!")(  "  hello  "  )
    # step 1: "  hello  " → "  HELLO  "  (str.upper)
    # step 2: "  HELLO  " → "HELLO"       (str.strip)
    # step 3: "HELLO"     → "HELLO!"      (append !)
    assert result == "HELLO!"


# ---------------------------------------------------------------------------
# normalize_record()
# ---------------------------------------------------------------------------

def test_normalize_strips_string_values():
    record = {"vendor_id": "  CMT  ", "passenger_count": "  2  "}
    assert normalize_record(record) == {"vendor_id": "CMT", "passenger_count": "2"}


def test_normalize_leaves_non_strings_unchanged():
    record = {"count": 5, "amount": 3.14, "flag": True}
    assert normalize_record(record) == {"count": 5, "amount": 3.14, "flag": True}


def test_normalize_returns_new_dict():
    original = {"field": "  value  "}
    result = normalize_record(original)
    # Must be a new dict, not a mutation of the original.
    assert result is not original


def test_normalize_empty_record():
    assert normalize_record({}) == {}


# ---------------------------------------------------------------------------
# DatasetLoader
# ---------------------------------------------------------------------------

def test_dataset_loader_reads_csv(tmp_path):
    """DatasetLoader __enter__ returns a DictReader over the given CSV file."""
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("vendor_id,passenger_count\nCMT,1\nVTS,2\n")

    with DatasetLoader(str(csv_file)) as reader:
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["vendor_id"] == "CMT"
    assert rows[1]["passenger_count"] == "2"


def test_dataset_loader_closes_file_after_context(tmp_path):
    """File handle is closed after exiting the context manager."""
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("a,b\n1,2\n")

    loader = DatasetLoader(str(csv_file))
    with loader as reader:
        list(reader)

    # DatasetLoader stores the open file handle as _file before returning
    # the DictReader. After __exit__, that handle must be closed.
    assert loader._file.closed


def test_dataset_loader_raises_on_missing_file():
    """DatasetLoader raises DataLoadError when the file does not exist."""
    with pytest.raises(DataLoadError), DatasetLoader("/nonexistent/path/to/file.csv"):
        pass   # pragma: no cover — body never reached
