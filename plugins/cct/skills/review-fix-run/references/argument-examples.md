# Argument shapes — worked examples

Read while parsing `$ARGUMENTS` (SKILL.md → Arguments): one row per shape, including both
error cases.

### Examples

| Input | max_iterations | review_mode | extra |
|-------|---------------|-------------|-------|
| *(empty)* | 5 | changes | — |
| `3` | 3 | changes | — |
| `files src/foo.py src/bar.py` | 5 | files | file_list=[src/foo.py, src/bar.py] |
| `3 files-max src/` | 3 | files-max | file_list=[src/] |
| `changes-max` | 5 | changes-max | — |
| `3 changes-max main` | 3 | changes-max | base_branch=main |
| `changes -- SUPPLY-301 focus on the auth path` | 5 | changes | INPUT.md commentary |
| `3 changes-max main --no-codex` | 3 | changes-max | base_branch=main, codex=off |
| `changes-max --no-codex` | 5 | changes-max | no base branch, codex=off |
| `3 files` | — | — | **Error: no file paths after `files`** |
| `3 changes-max files 1` | — | — | **Error: conflicting mode keywords (`changes-max` + `files`)** |
