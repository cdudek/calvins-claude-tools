"""The owner answers are parsed once per process (marks.answers); every test starts with none cached."""

import sys

import pytest

from test_chain_gate import repo as chain_repo  # noqa: F401
from test_gate_bash import repo as bash_repo  # noqa: F401
from test_pr_gate import repo as pr_repo  # noqa: F401
from test_sdlc_status import repo  # noqa: F401  # the shared repo fixture


@pytest.fixture(autouse=True)
def _forget_cached_owner_answers():
    for name in ("marks", "marks_under_test"):
        if name in sys.modules:
            sys.modules[name]._ANSWERS.clear()
    yield


@pytest.fixture(autouse=True)
def _private_machine_state(tmp_path_factory, monkeypatch):
    """The heavy queue and the test-database lock are per machine; tests never touch the real ones."""
    state = tmp_path_factory.mktemp("sdlc-state")
    monkeypatch.setenv("SDLC_HEAVY_DIR", str(state / "heavy"))
    monkeypatch.setenv("SDLC_DB_DIR", str(state / "db"))
    yield
