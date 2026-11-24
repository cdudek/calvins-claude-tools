"""Runner bugs found before a first live run: object packages on the approval screen, board rows in the builder brief."""
from pathlib import Path

import discover
import engine
import store
import testkit as tk
from test_runner_canvas import board_row


def test_the_screen_lists_edge_packages_given_as_name_dir_objects(tmp_path):
    repo, rid = tk.feature_run(tmp_path)
    d = store.run_dir(rid)
    c = store.read_json(d / "contract.json")
    c["edges"] = [{"producer": "app", "consumer": "app", "packages": [{"name": "@kit/ui", "dir": "packages/ui"}, "@kit/core"],
                   "release": {"kind": "vendored-tarball"}, "pin": {"dir": "vendor/kit"}}]
    store.write_json(d / "contract.json", c)
    assert "packages @kit/ui, @kit/core" in discover.screen(rid).read_text()


def test_the_builder_brief_for_a_task_covered_by_a_board_row_names_the_board_command(tmp_path):
    repo, rid = tk.feature_run(tmp_path)
    d = store.run_dir(rid)
    row = board_row()
    del row["runner"]
    row["task"] = "t1"
    row["repo"] = "app"
    c = store.read_json(d / "contract.json")
    c["checks"] = [row]
    store.write_json(d / "contract.json", c)
    engine.validate_plan(rid)
    tk.approve(rid)
    info = engine.dispatch(rid, "t1")
    assert "board.py check specs/web.json" in Path(info["brief"]).read_text()
