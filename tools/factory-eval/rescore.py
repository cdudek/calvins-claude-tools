#!/usr/bin/env python3
"""Usage: rescore.py <task dir> <run dir>... - re-keys each graded run's saved test units under the task's current lists
(fail_to_pass, pass_to_pass_hidden, implementation_coupled, out_of_scope) and recomputes every quality field with
grade.score. Reruns no test, so it works on runs whose work dirs were pruned. Rewrites grade.json in place, keeping
the previous file as grade.json.bak once.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grade  # noqa: E402

FILE_UNITS = ("f2p:", "p2p:hidden:", "coupled:", "outside:")


def rescore(task, run_dir):
    path = Path(run_dir) / "grade.json"
    g = json.loads(path.read_text())
    if not g.get("units"):
        return None  # an infrastructure failure: nothing was graded
    units = {}
    for k, v in g["units"].items():
        pre = next((p for p in FILE_UNITS if k.startswith(p)), None)
        units[grade.unit_key(task, k[len(pre):]) if pre else k] = v
    g["units"] = units
    grade.score(g, task)
    bak = path.with_suffix(".json.bak")
    if not bak.exists():
        shutil.copy(path, bak)
    path.write_text(json.dumps(g, indent=1, default=str) + "\n")
    return g


if __name__ == "__main__":
    task = json.loads((Path(sys.argv[1]).expanduser() / "task.json").read_text())
    for d in sys.argv[2:]:
        g = rescore(task, d)
        if g:
            print(f"{Path(d).name}: hidden_frac={g['hidden_frac']} solved={g['solved']} outside_fixed={g['outside_fixed']}")
