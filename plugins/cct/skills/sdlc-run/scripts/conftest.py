"""The owner answers are parsed once per process (marks.answers); every test starts with none cached."""

import sys

import pytest


@pytest.fixture(autouse=True)
def _forget_cached_owner_answers():
    for name in ("marks", "marks_under_test"):
        if name in sys.modules:
            sys.modules[name]._ANSWERS.clear()
    yield
