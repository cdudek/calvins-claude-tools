import io
import json
import tarfile

import check_coupled


def task(tmp_path, files, test, plan="# plan\n"):
    with tarfile.open(tmp_path / "start.tar.gz", "w:gz") as tf:
        for name, body in {**files, "changes/x/plan.md": plan}.items():
            data = body.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    (tmp_path / "hidden-tests/test").mkdir(parents=True)
    (tmp_path / "hidden-tests/test/a.test.ts").write_text(test)
    (tmp_path / "task.json").write_text(json.dumps({"plan": "changes/x/plan.md", "fail_to_pass": ["test/a.test.ts"]}))
    return tmp_path


def test_reexported_symbol_is_found_and_unnamed_new_symbol_is_coupled(tmp_path):
    files = {"src/db/schema.ts": "export * from './tables';\n", "src/db/tables.ts": "export const users = 1;\n"}
    test = "import { users } from '../src/db/schema';\nimport { hasTeam } from '../src/teams/rules';\n"
    assert check_coupled.coupled(task(tmp_path, files, test)) == [("test/a.test.ts", ["hasTeam@src/teams/rules"])]


def test_symbol_named_in_the_plan_is_not_coupled(tmp_path):
    test = "import { hasTeam } from '../src/teams/rules';\n"
    assert check_coupled.coupled(task(tmp_path, {}, test, plan="T1 exports `hasTeam` from src/teams/rules.ts\n")) == []


def test_alias_reexport_from_an_index_module(tmp_path):
    files = {"src/db/schema/index.ts": "export * from '@/teams/teams.tables';\nexport * from './common';\n",
             "src/teams/teams.tables.ts": "export const teams = 1;\n", "src/db/schema/common.ts": "export const role = 1;\n"}
    test = "import { teams, role } from '../src/db/schema';\n"
    assert check_coupled.coupled(task(tmp_path, files, test)) == []
