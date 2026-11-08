"""Regression guards for the Codex co-review seams.

Codex enters review-code-run as a second *source* of findings, so its contract spans a
JSON Schema, two shell scripts and the prose that drives them. Nothing checks the
match at runtime — a field renamed in one place just produces findings the merge
step silently ignores — so the seams live here.

What this guards, each one a way the integration fails quietly:

1. The schema and the canonical field set drift apart, so Codex emits findings the
   pipeline drops.
2. `--sandbox read-only` is lost from `codex-review.sh`. `codex exec` defaults to
   write-capable, so the flag is the only thing standing between a review and an
   edited working tree.
3. `merge-prep.sh` stops reading `codex-findings.json`, so the Codex pass runs, costs
   money, and contributes nothing.
4. The `$CODEX` gate loses `auto`-degrades / `on`-stops, so a missing CLI either
   blocks every review or is silently dropped from one the user asked for.
5. The nested tail grows a second bare control token after `STATE_DIR=`, which
   `review-fix-run` step 2 reads as an unparseable result and stops the loop on.
6. The sanitize chain fails open — the scan reads a clean tree where it could not
   look, a withheld file reaches the mirror, or Codex is pointed at `$ROOT` again.
   This is the one where a quiet failure discloses a secret rather than losing a
   finding, so its guards are behavioural: they run the real scripts against fixture
   trees. A negative "pattern absent" assertion is not acceptable here — an earlier
   version of the `*.ejson` guard was exactly that, and it stayed green while the rule
   it covered was reverted.

Run: pytest plugins/cct/skills/review-code-run/scripts/test_codex_contract.py
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
PLUGIN = SKILL.parents[1]
REF = SKILL / "references"
SCRIPTS = SKILL / "scripts"

# The canonical pre-identity finding fields — everything `merge.md` assigns except
# `id` (minted at merge) and `suppressed_reason` (optional). A Codex finding must
# carry all of these or the merge step has nothing to collapse on.
PRE_IDENTITY_FIELDS = {
    "file",
    "line",
    "severity",
    "confidence",
    "dimension",
    "self_proving",
    "evidence",
    "body",
    "failure_scenario",
    "reversibility",
    "validation_effort",
}


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_schema_covers_the_canonical_field_set():
    """The schema is the wire contract; drift here loses findings without an error."""
    schema = json.loads(read(SCRIPTS / "codex-findings-schema.json"))
    props = schema["properties"]["findings"]["items"]["properties"]
    missing = PRE_IDENTITY_FIELDS - set(props)
    assert not missing, f"schema is missing canonical finding fields: {sorted(missing)}"
    assert "id" not in props, (
        "the Codex source is pre-identity — `id` is minted by merge.md, and a "
        "Codex-supplied id would collide with the ids merge assigns"
    )
    assert "suppressed_reason" in props, (
        "demote-don't-delete applies to the Codex reviewer too — without this field a "
        "judgment-call suppression is dropped instead of demoted"
    )


def test_schema_enums_match_the_pipeline_scales():
    """`validate-prep.sh` sorts on these numerically and a linter never sees them."""
    schema = json.loads(read(SCRIPTS / "codex-findings-schema.json"))
    props = schema["properties"]["findings"]["items"]["properties"]
    assert props["severity"]["enum"] == ["critical", "warning", "suggestion", "nit"]
    assert props["validation_effort"] == {
        "type": "integer",
        "minimum": 0,
        "maximum": 6,
        "description": props["validation_effort"]["description"],
    }, "validation_effort must stay an integer 0-6 — validate-prep.sh sorts on it"
    assert props["line"]["type"] == "string", (
        "`line` is a string everywhere in the pipeline; an integer here would not "
        "match the findings.json shape merge.md writes"
    )
    assert set(props["suppressed_reason"]["enum"]) == {"style", "out-of-scope", None}


def test_codex_runs_read_only():
    """Without the flag, `codex exec` can edit the tree it was asked to review."""
    script = read(SCRIPTS / "codex-review.sh")
    assert "--sandbox read-only" in script, (
        "codex-review.sh lost --sandbox read-only — codex exec defaults to "
        "write-capable and will modify the review target"
    )
    assert "--dangerously-bypass-approvals-and-sandbox" not in script
    for doc in ["references/codex-lane.md", "references/policies.md"]:
        assert "read-only" in read(SKILL / doc), (
            f"{doc} no longer states the read-only guarantee that makes co-review safe"
        )


def test_codex_review_stamps_provenance_and_never_aborts():
    """A Codex failure degrades the review; it must not fail the run."""
    script = read(SCRIPTS / "codex-review.sh")
    assert 'source:            "codex"' in script, (
        "codex-review.sh no longer stamps `source: codex` — merge.md cannot assign "
        "`both` (and its confidence bonus) without knowing which model found what"
    )
    assert "exit 0" in script, "the failure path must exit 0 so the review continues"
    assert "- status: failed" in script and "- status: ok" in script, (
        "the caller routes on `- status:`; both branches must be emitted"
    )


def test_merge_reads_the_codex_source():
    """A Codex pass that nothing merges is pure cost."""
    prep = read(SCRIPTS / "merge-prep.sh")
    assert "codex-findings.json" in prep, "merge-prep.sh no longer reads the Codex source"
    assert "CODEX FINDINGS" in prep, "the Codex section marker is gone from merge-prep.sh"
    merge = read(REF / "merge.md")
    assert "CODEX FINDINGS" in merge, (
        "merge.md must document the section marker it consumes, or the orchestrator "
        "will not know the Codex source exists"
    )
    assert '"source"' in merge or "`source`" in merge


def test_agreement_bonus_is_specified_and_single_sourced():
    """`both` raises confidence exactly once, and only merge may assign it."""
    merge = read(REF / "merge.md")
    assert "min(100, max(claude_confidence, codex_confidence) + 15)" in merge, (
        "the agreement bonus formula is gone — an unspecified bonus is applied "
        "inconsistently across runs"
    )
    synth = read(PLUGIN / "skills/role-code-analysis/references/synthesize.md")
    assert "Do not raise `confidence` again here" in synth, (
        "synthesize must not re-apply the agreement bonus merge already applied"
    )
    reviewer = read(PLUGIN / "agents/review-code-reviewer.md")
    assert "Never emit `codex` or `both`" in reviewer, (
        "only merge may assign `both`; a reviewer that self-reports agreement "
        "fabricates the one signal co-review exists to produce"
    )


def test_codex_gate_has_three_values_and_the_right_failure_modes():
    """`auto` degrades silently-but-disclosed; `on` stops. Conflating them is the bug."""
    skill = read(SKILL / "SKILL.md")
    for token in ["--codex", "--no-codex", "`auto`"]:
        assert token in skill, f"SKILL.md § Routing no longer defines {token}"
    lane = read(REF / "codex-lane.md")
    assert "degrade" in lane.lower(), "codex-lane.md lost the auto-degradation route"
    assert "stop" in lane.lower(), "codex-lane.md lost the --codex stop route"
    tail = read(REF / "pipeline-tail.md")
    assert "CODEX_STATUS" in tail, (
        "the report must disclose the co-review state — a degraded run that reads "
        "like a co-review overstates its own coverage"
    )


def test_codex_gate_auto_and_on_are_not_conflated():
    """A mutation that swaps which value degrades and which stops must fail this test —
    presence-only checks (`degrade` and `stop` appear *somewhere*) pass on a swap too."""
    lane = read(REF / "codex-lane.md")
    start = lane.index("Route on `- available:`:")
    end = lane.index("Degradation is silent-but-disclosed")
    block = lane[start:end]
    auto_row = next(line for line in block.splitlines() if "`auto`" in line and "|" in line)
    on_row = next(line for line in block.splitlines() if re.search(r"\|\s*`on`\s*\|", line))
    assert "degrade" in auto_row.lower() and "stop" not in auto_row.lower(), (
        "the `auto` row of the availability gate must degrade, not stop"
    )
    assert "stop" in on_row.lower() and "degrade" not in on_row.lower(), (
        "the `on` row of the availability gate must stop, not degrade"
    )


SECRET_FIXTURE = {
    # path -> must appear in the scan's SECRET_PATHS section
    ".env": True,
    ".env.local": True,
    ".env.prod,bak": True,  # a comma in the name must not mis-split the list
    "sub/id_rsa": True,
    "sub/id_ed25519": True,
    "server.pem": True,
    "client.key": True,
    "store.p12": True,
    "store.pfx": True,
    "credentials.json": True,
    "service-account-prod.json": True,
    ".netrc": True,
    ".npmrc": True,  # carries NPM_TOKEN in a typical frontend repo
    ".pypirc": True,
    ".zshrc": True,  # named as a secret file by the org's own CLAUDE.md
    ".bashrc": True,
    ".bash_profile": True,
    ".profile": True,
    ".envrc": True,  # direnv: `export AWS_SECRET_ACCESS_KEY=...`; no dot after env
    "deploy/.flaskenv": True,
    # templates and encrypted-by-design files are not secrets
    ".env.example": False,
    ".env.sample": False,
    "secrets.ejson": False,
    "config/settings.ejson": False,
    "notes.keynote": False,  # must not be swept up by the `*.key` pattern
    "app.py": False,
    "package.json": False,  # must not be swept up by a widened `*.json`
    # pruned trees: a dependency's fixture is not the user's secret
    "node_modules/pkg/.env": False,
    "vendor/bundle/id_rsa": False,
    "dist/.env": False,
    ".git/credentials.json": False,
}

SCAN = "codex-scan-secrets.sh"


def _run_scan(root: Path):
    """Run codex-scan-secrets.sh against `root`; return (exit_code, paths, rows)."""
    r = subprocess.run(
        ["bash", str(SCRIPTS / SCAN), str(root)],
        capture_output=True,
        text=True,
    )
    body = r.stdout
    paths = []
    if "-#-#- BEGIN SECRET_PATHS -#-#-" in body:
        block = body.split("-#-#- BEGIN SECRET_PATHS -#-#-", 1)[1]
        block = block.split("-#-#- END SECRET_PATHS -#-#-", 1)[0]
        paths = [line for line in block.splitlines() if line]
    rows = dict(re.findall(r"^- ([a-z_]+): ?(.*)$", body, re.MULTILINE))
    return r.returncode, paths, rows


def test_secrets_scan_matches_filenames_only():
    """Reading a secret to classify it would break the rule the scan serves.

    The organization rule is that secrets are never read directly. A name-based scan
    satisfies it; a content sniff would not, however much better it would work.
    """
    script = read(SCRIPTS / SCAN)
    body = "\n".join(line for line in script.splitlines() if not line.strip().startswith("#"))
    for reader in ["cat ", "grep ", "head ", "tail ", "awk ", "sed "]:
        assert reader not in body, (
            f"{SCAN} now runs `{reader.strip()}` over the tree — the scan must match "
            f"filenames and never open a candidate file"
        )
    assert "-print0" in script, "the scan must emit NUL-delimited paths"


def test_secrets_scan_matches_and_excludes_the_right_files(tmp_path):
    """Behavioural guard, because every exclusion here is implicit.

    `*.ejson` is excluded by simply not being in the find expression, so there is no
    construct to assert against — only behaviour pins it. Same for `.env.example` and
    the pruned vendor trees. A negative "pattern absent" assertion would survive any
    rename of the pattern it names, which is how the earlier version of this guard
    passed while the rule it covered was reverted.
    """
    for rel in SECRET_FIXTURE:
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()

    code, paths, rows = _run_scan(tmp_path)
    assert code == 0 and rows["status"] == "ok", f"scan failed unexpectedly: {rows}"
    found = set(paths)

    for rel, expected in SECRET_FIXTURE.items():
        if expected:
            assert rel in found, f"the scan stopped matching the secret-shaped {rel!r}"
        else:
            assert rel not in found, (
                f"the scan now reports {rel!r} as a secret; a false positive withholds a "
                f"file Codex needs and silently weakens the review"
            )
    assert int(rows["count"]) == len(found), "the reported count disagrees with the list"


def test_secrets_scan_matches_a_symlink(tmp_path):
    """`find -type f` alone misses a symlinked secret, which Codex would still follow."""
    (tmp_path / "real").mkdir()
    (tmp_path / "real/actual-secret").write_text("x")
    (tmp_path / ".env").symlink_to(tmp_path / "real/actual-secret")
    _, paths, _ = _run_scan(tmp_path)
    assert ".env" in paths, (
        "a symlink named .env is no longer withheld — the link resolves to a real "
        "secret and `codex exec` follows it when reading for context"
    )


def test_secrets_scan_fails_closed(tmp_path):
    """An empty list must mean "none found", never "the scan did not run".

    Under the withhold design the list IS the exclusion set, so a silently empty
    result ships the very files the scan exists to withhold. Every unusable-root case
    must therefore exit non-zero with `status: failed`, not exit 0 with an empty list.
    """
    for label, arg in [
        ("missing root", str(tmp_path / "does-not-exist")),
        ("root is a file", str(tmp_path / "afile")),
    ]:
        (tmp_path / "afile").write_text("x")
        code, paths, rows = _run_scan(Path(arg))
        assert code != 0, f"{label}: scan exited 0 — a caller would read this as a clean tree"
        assert rows["status"] == "failed", f"{label}: status is not `failed`"
        assert paths == [], f"{label}: a failed scan must emit no paths"

    r = subprocess.run(["bash", str(SCRIPTS / SCAN)], capture_output=True, text=True)
    assert r.returncode != 0, "the scan exits 0 with no root argument"


def test_preflight_reports_both_unavailable_branches(tmp_path):
    """Both `available: no` branches must be forced by something.

    The not-on-PATH branch is easy to reach; the on-PATH-but-not-authenticated branch
    is not, so a regression that broke only that emit call would pass a suite that
    never exercises it. A stub `codex` that fails `login status` forces it.
    """
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "codex").write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  --version) echo "codex-cli 0.0.0-stub" ;;\n'
        "  login) exit 1 ;;\n"
        "  *) exit 1 ;;\n"
        "esac\n"
    )
    (stub / "codex").chmod(0o755)

    env = {**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"}
    env.pop("OPENAI_API_KEY", None)
    out = subprocess.run(
        ["bash", str(SCRIPTS / "codex-available.sh")],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    ).stdout
    assert "- available: no" in out, "an unauthenticated CLI now reports as usable"
    assert "codex login" in out, "the reason no longer carries the fix command"
    assert "0.0.0-stub" in out, (
        "the version is dropped on the not-authenticated branch, so a stale install "
        "cannot be told apart from a missing one when troubleshooting"
    )

    env_no_cli = {**os.environ, "PATH": "/usr/bin:/bin"}
    env_no_cli.pop("OPENAI_API_KEY", None)
    out = subprocess.run(
        ["bash", str(SCRIPTS / "codex-available.sh")],
        capture_output=True,
        text=True,
        check=True,
        env=env_no_cli,
    ).stdout
    assert "- available: no" in out and "npm install" in out, (
        "the not-on-PATH branch lost its install instruction"
    )


def test_review_sends_a_sanitized_mirror_not_the_root():
    """`--sandbox read-only` stops writes, not reads, so a secret must be ABSENT.

    Pointing Codex at `$ROOT` and asking it not to look is not a control. The mirror is
    the control: the file is not there to read.
    """
    script = read(SCRIPTS / "codex-review.sh")
    assert '-C "$MIRROR"' in script, (
        "codex-review.sh points Codex at something other than the sanitized mirror"
    )
    assert '-C "$ROOT"' not in script.replace('`-C "$ROOT"`', ""), (
        "codex-review.sh hands the unsanitized review root to Codex again"
    )
    assert SCAN in script, "codex-review.sh no longer runs the secrets scan"
    assert "--exclude-from=" in script, "the mirror is built without the withhold list"
    assert "command -v rsync" in script, (
        "no rsync guard — without it the mirror step fails open on a machine lacking rsync"
    )


def test_mirror_is_verified_by_rescanning_it_not_by_replaying_the_list():
    """A list-replay check is structurally blind to the race that matters.

    A secret-shaped file created, renamed in or restored in `$ROOT` between the scan and
    the copy is absent from the exclude list, so iterating that list cannot see it — and
    `make secrets` writing a .env mid-review is a real race on a shared worktree. Only a
    re-scan of the finished mirror closes it.
    """
    script = read(SCRIPTS / "codex-review.sh")
    # The exact invocation, not the bare flag: the flag name also appears in the comment
    # that explains why it is load-bearing, so a presence check passes after the call
    # itself loses it (verified: it did).
    assert '"$MIRROR" --no-prune' in script, (
        "the post-copy verification no longer runs with --no-prune, so it inherits the "
        "source scan's blind spots and would miss a secret that reached the mirror "
        "through a mis-built prune argument"
    )
    assert "the mirror still holds" in script, (
        "the post-copy verification scan is gone; it is what makes the mechanism "
        "trustworthy, because it inspects the outcome rather than trusting the inputs"
    )
    assert script.count(SCAN) >= 2, (
        "the scan is run once, so the mirror is never verified — it must run against "
        "$ROOT to build the exclude list and again against $MIRROR to verify it"
    )


def test_exclude_list_is_escaped_and_cross_checked():
    """rsync reads --exclude-from as PATTERNS, and an unchecked extraction fails open."""
    script = read(SCRIPTS / "codex-review.sh")
    assert "s#^#/#" in script, (
        "exclude paths are no longer anchored with a leading `/`; an unanchored line "
        "starting with `#` or `;` is silently treated as a filter-file comment"
    )
    assert r"sed -e 's/[][\*?]/\\&/g'" in script, (
        "glob metacharacters are no longer escaped in the exclude list, so a path like "
        "pages/[id]/.env — ordinary in a Nuxt repo — fails to match"
    )
    assert "but the scan reported" in script, (
        "the extracted exclude list is no longer cross-checked against the scan's own "
        "count, so a marker drift could truncate it while everything believed it whole"
    )
    assert "SECRET_PATHS markers, expected exactly one pair" in script, (
        "nothing asserts the scan output has exactly one marker pair, so a diagnostic "
        "line added between the markers would silently become an exclude pattern"
    )


def test_prune_set_is_single_sourced_from_the_scan():
    """A directory the scan skipped must not reach the mirror, or the check goes blind."""
    review = read(SCRIPTS / "codex-review.sh")
    scan = read(SCRIPTS / SCAN)
    assert "- pruned:" in scan, "the scan no longer reports the directories it skipped"
    assert "pruned_csv" in review and "prune_args" in review, (
        "codex-review.sh no longer derives its rsync excludes from the scan's `- pruned:` "
        "field; a second hand-maintained list would drift, and a directory pruned from "
        "the scan but copied into the mirror is a fail-open path"
    )
    assert "refusing to mirror unpruned" in review, "an empty prune set is no longer refused"


def test_glob_metacharacter_paths_are_actually_withheld(tmp_path):
    """Behavioural: the escaping has to work, not merely be present."""
    root = tmp_path / "root"
    (root / "pages/[id]").mkdir(parents=True)
    (root / "pages/[id]/.env").write_text("SECRET=bracket\n")
    (root / "pages/we*ird.pem").write_text("SECRET=star\n")
    (root / "app.py").write_text("x = 1\n")

    _, paths, rows = _run_scan(root)
    assert rows["status"] == "ok"
    assert "pages/[id]/.env" in paths and "pages/we*ird.pem" in paths

    excl = tmp_path / "excl.txt"
    excl.write_text("".join("/" + re.sub(r"([][*?\\])", r"\\\1", p) + "\n" for p in paths))
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    subprocess.run(
        ["rsync", "-a", f"--exclude-from={excl}", f"{root}/", f"{mirror}/"],
        check=True,
        capture_output=True,
    )
    survivors = [str(f.relative_to(mirror)) for f in mirror.rglob("*") if f.is_file()]
    assert survivors == ["app.py"], (
        f"a glob-metacharacter path was not withheld from the mirror: {survivors}"
    )


@pytest.mark.skipif(
    os.geteuid() == 0,
    reason="root ignores file mode bits; the unreadable-subtree case cannot be constructed",
)
def test_scan_fails_on_an_unreadable_subtree(tmp_path):
    """`find` returns non-zero with a PARTIAL result; a partial exclusion set fails open."""
    root = tmp_path / "root"
    (root / "locked").mkdir(parents=True)
    (root / "locked/.env").write_text("SECRET=hidden\n")
    (root / "locked").chmod(0o000)
    try:
        code, paths, rows = _run_scan(root)
        assert code != 0, (
            "the scan exited 0 over a subtree it could not read — a caller would take "
            "the truncated list as complete and ship the secrets inside it"
        )
        assert rows["status"] == "failed"
    finally:
        (root / "locked").chmod(0o755)


def test_merge_prep_fails_on_a_broken_codex_source(tmp_path):
    """Broken and clean must not be the same outcome, and broken must not exit 0.

    A corrupted codex-findings.json left on disk is worse than a bad merge: the lane's
    "already done" checkpoint reads its presence as a completed pass, so the revision
    would never retry Codex.
    """
    (tmp_path / "dim-a.json").write_text('{"result": "a finding"}')

    (tmp_path / "codex-findings.json").write_text("not json at all")
    r = subprocess.run(
        ["bash", str(SCRIPTS / "merge-prep.sh"), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0, "a broken Codex source no longer fails the merge step"
    assert "broken, not clean" in r.stderr

    (tmp_path / "codex-findings.json").write_text('{"findings": []}')
    r = subprocess.run(
        ["bash", str(SCRIPTS / "merge-prep.sh"), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, "a genuinely clean Codex pass must not fail the merge step"
    assert "ran clean" in r.stderr
    assert "CODEX FINDINGS" not in r.stdout


def test_off_suppresses_a_cached_codex_source():
    """`--no-codex` must beat the resume checkpoint, or it honours the flag's letter only.

    A revision reviewed earlier with `auto` leaves a codex-findings.json behind. If the
    checkpoint is consulted first, a later `--no-codex` run silently merges that cached
    Codex source while reporting Claude-only.
    """
    lane = read(REF / "codex-lane.md")
    gate = lane[lane.index("## 1. Gate") : lane.index("## 2.")]
    off_pos = gate.index("Turned off?")
    cp_pos = gate.index("Already done?")
    assert off_pos < cp_pos, (
        "the resume checkpoint is consulted before the `off` check, so --no-codex would "
        "reuse a cached Codex source from an earlier auto/on pass"
    )
    assert "even when Codex is available" in read(SKILL / "SKILL.md"), (
        "SKILL.md no longer states what --no-codex means, which is what the ordering "
        "above exists to honour"
    )


def test_no_stale_status_values_survive_in_the_renderers():
    """A status value no consumer can produce is a trap for the next editor."""
    for rel in ["references/report-sections.md", "references/pipeline-tail.md"]:
        text = read(SKILL / rel)
        assert "secrets found:" not in text, (
            f"{rel} still enumerates the `secrets found:` status, which the withhold "
            f"design removed — the refusal branch that set it no longer exists"
        )


def test_the_gate_withholds_and_never_refuses():
    """Refusing on a found secret would disable co-review on every backend repo.

    `make secrets` writes a .env into the working tree there, so a refusal gate makes
    co-review unreachable on exactly the repos that most need it. The chosen design
    withholds the files and runs the pass.
    """
    lane = read(REF / "codex-lane.md")
    assert "There is no secrets gate" in lane, (
        "codex-lane.md no longer states that secrets are withheld rather than refused"
    )
    assert "secrets found:" not in lane, "a `secrets found:` refusal status is back in the gate"
    policies = read(SKILL / "references/policies.md")
    assert "withheld, not grounds to refuse" in policies
    # The honest limit must stay stated: name matching cannot see inside a file.
    assert "does not do" in policies and "config.py" in policies, (
        "policies.md dropped the statement that name-based withholding does not catch "
        "a secret inside a normally-named file — co-review reduces the exposure, it "
        "does not eliminate it, and the doc must not imply otherwise"
    )


def test_gate_checks_the_checkpoint_before_paying_for_anything():
    """A resumed run must not pay for a preflight or a full-tree scan it discards."""
    lane = read(REF / "codex-lane.md")
    gate = lane[lane.index("## 1. Gate") : lane.index("## 2.")]
    cp = gate.index("codex-findings.json")
    pre = gate.index("codex-available.sh")
    assert cp < pre, (
        "the skip-if-exists checkpoint moved below the preflight, so every resumed "
        "pass pays for work whose result is thrown away"
    )


def test_nested_tail_keeps_state_dir_as_the_only_final_token():
    """`review-fix-run` matches the LAST non-empty line; a second token breaks it."""
    tail = read(REF / "pipeline-tail.md")
    assert "Do not add a second bare control token" in tail, (
        "the nested tail no longer forbids a second bare KEY=value line after "
        "STATE_DIR=, which review-fix-run step 2 reads as an unparseable result"
    )
    # The instruction to emit CODEX_STATUS must sit in the counts line, not on its own.
    assert not re.search(r"^\s*`?CODEX_STATUS=", tail, re.MULTILINE), (
        "CODEX_STATUS is documented as a standalone line again"
    )


def test_split_decisions_routes_rejected_codex_findings():
    """A cross-model dispute is information; the demoted appendix hides it."""
    sections = read(REF / "report-sections.md")
    assert "## Split decisions" in sections, "the Split decisions section is gone"
    assert "Evidence decides" in sections, (
        "the section lost the rule that stops a dispute being settled by whichever "
        "side sounded more certain"
    )
    synth = read(PLUGIN / "skills/role-code-analysis/references/synthesize.md")
    assert "Cross-model exception" in synth, (
        "synthesize still sends a rejected Codex finding to the demoted appendix, "
        "so report-sections' Split decisions section would render empty"
    )


# ---------------------------------------------------------------------------
# Sanitize chain, second pass: symlinks, the diff text, and the resume gate.
# ---------------------------------------------------------------------------


def test_secrets_scan_withholds_every_symlink(tmp_path):
    """A symlink with an innocent name can point at ~/.ssh/id_rsa.

    Name matching cannot see that, `rsync -a` copies the link as a link, and the
    read-only sandbox stops writes, not reads — so Codex follows it. Every symlink is
    withheld, whatever its name. Behavioural: the exclusion is a `find` branch with no
    construct to grep for.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "real-secret").write_text("x")
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    (root / "logo.svg").symlink_to(outside / "real-secret")
    (root / "sub" / "assets").symlink_to(outside)  # a directory link
    (root / "app.py").write_text("print(1)")
    code, paths, rows = _run_scan(root)
    assert code == 0 and rows["status"] == "ok"
    assert "logo.svg" in paths, "a file symlink with an innocent name reached the mirror"
    assert "sub/assets" in paths, "a directory symlink reached the mirror"
    assert "app.py" not in paths
    assert int(rows["count"]) == 2


def test_match_names_uses_the_same_patterns_without_touching_disk(tmp_path):
    """`--match-names` is the second consumer of the one pattern list.

    Paths that do not exist on disk must still match — the diff names files the mirror
    scan never sees (a deleted `.env` is only in the diff).
    """
    r = subprocess.run(
        ["bash", str(SCRIPTS / SCAN), "--match-names"],
        input="\n".join(
            [
                ".env",
                "config/.env.local",
                "src/app.py",
                "deploy/.envrc",
                ".env.example",
                "a/b/service-account-x.json",
                "notes.keynote",
                "",
            ]
        ),
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert r.returncode == 0, r.stdout
    block = r.stdout.split("-#-#- BEGIN SECRET_PATHS -#-#-", 1)[1]
    block = block.split("-#-#- END SECRET_PATHS -#-#-", 1)[0]
    got = {line for line in block.splitlines() if line}
    assert got == {".env", "config/.env.local", "deploy/.envrc", "a/b/service-account-x.json"}
    assert "- count: 4" in r.stdout


def test_diff_filter_drops_the_sections_of_secret_shaped_files(tmp_path):
    """The mirror cannot protect text that is already in the prompt.

    A diff that adds `.env` carries the secret in its `+` lines; one that deletes a
    `.pem` carries it in its `-` lines. Both sections must go, the ordinary file must
    stay, and a marker must say what was removed.
    """
    diff = (
        "diff --git a/.env b/.env\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/.env\n"
        "@@ -0,0 +1 @@\n"
        "+STRIPE_SECRET_KEY=sk_live_FIXTUREVALUE\n"
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1 +1 @@\n"
        "-print(1)\n"
        "+print(2)\n"
        "diff --git a/old.pem b/old.pem\n"
        "deleted file mode 100644\n"
        "--- a/old.pem\n"
        "+++ /dev/null\n"
        "@@ -1 +0,0 @@\n"
        "-PRIVATEKEYFIXTUREMATERIAL\n"
    )
    src = tmp_path / "pr.diff"
    src.write_text(diff)
    out = tmp_path / "filtered.diff"
    r = subprocess.run(
        ["bash", str(SCRIPTS / "codex-filter-diff.sh"), str(src), str(out)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and "- status: ok" in r.stdout, r.stdout
    assert "- withheld: 2" in r.stdout
    filtered = out.read_text()
    assert "sk_live_FIXTUREVALUE" not in filtered, "an added secret line reached the prompt"
    assert "PRIVATEKEYFIXTUREMATERIAL" not in filtered, "a deleted secret line reached the prompt"
    assert "+print(2)" in filtered and "-print(1)" in filtered, "an ordinary section was lost"
    assert "[withheld: .env" in filtered and "[withheld: old.pem" in filtered
    assert src.read_text() == diff, "the filter must not modify the reviewers' diff"


def test_diff_filter_withholds_symlinks_and_ambiguous_renames(tmp_path):
    """Two ways the first version failed open.

    A symlink's diff content is its target path, and the mirror withholds every symlink —
    so must the diff. And the `diff --git a/<a> b/<b>` header is ambiguous when a path
    contains " b/": the old `config b/.env` renamed to `safe.txt` split at the first " b/"
    into `config` and `.env b/safe.txt`, neither secret-shaped, and the `-` lines with the
    secret went through. Every split is now a candidate, so ambiguity withholds.
    """
    diff = (
        "diff --git a/logo.svg b/logo.svg\n"
        "new file mode 120000\n"
        "index 0000000..1111111\n"
        "--- /dev/null\n"
        "+++ b/logo.svg\n"
        "@@ -0,0 +1 @@\n"
        "+/Users/someone/.ssh/id_rsa\n"
        "\\ No newline at end of file\n"
        "diff --git a/config b/.env b/safe.txt\n"
        "similarity index 60%\n"
        "rename from config b/.env\n"
        "rename to safe.txt\n"
        "--- a/config b/.env\n"
        "+++ b/safe.txt\n"
        "@@ -1 +1 @@\n"
        "-STRIPE_SECRET_KEY=sk_live_RENAMEDFIXTURE\n"
        "+nothing here\n"
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1 +1 @@\n"
        "-print(1)\n"
        "+print(2)\n"
    )
    src = tmp_path / "pr.diff"
    src.write_text(diff)
    out = tmp_path / "filtered.diff"
    r = subprocess.run(
        ["bash", str(SCRIPTS / "codex-filter-diff.sh"), str(src), str(out)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and "- status: ok" in r.stdout, r.stdout
    assert "- withheld: 2" in r.stdout
    filtered = out.read_text()
    assert "/Users/someone/.ssh/id_rsa" not in filtered, "a symlink target reached the prompt"
    assert "sk_live_RENAMEDFIXTURE" not in filtered, "an ambiguous rename let the secret through"
    assert "+print(2)" in filtered, "an ordinary section was lost"


def test_codex_review_filters_the_diff_before_building_the_prompt():
    script = read(SCRIPTS / "codex-review.sh")
    assert "codex-filter-diff.sh" in script, (
        "codex-review.sh embeds the raw diff; the mirror does nothing for text that is "
        "already in the prompt"
    )
    # Anchor on the INVOCATION, not the bare filename: the header comment mentions the
    # script first, and a comment always precedes the prompt block, so the bare name
    # would pass even after the real call moved below prompt assembly.
    call = 'bash "$SCRIPT_DIR/codex-filter-diff.sh"'
    assert call in script, "the filter is mentioned but never invoked"
    assert script.index(call) < script.index("BEGIN DIFF"), (
        "the diff filter runs after the prompt is assembled, so the prompt holds the "
        "unfiltered diff"
    )
    assert "- diff_withheld:" in script, "the count of removed sections is not disclosed"


def _write_state(tmp_path, *, sources, codex_file):
    sd = tmp_path / "rev-abc"
    sd.mkdir(parents=True)
    (sd / "dim-security.json").write_text('{"result": "x"}')
    (sd / "findings.json").write_text(
        json.dumps(
            {
                "findings": [
                    {"id": i + 1, "file": "a", "line": "1", "source": s}
                    for i, s in enumerate(sources)
                ]
            }
        )
    )
    (sd / "verdicts.json").write_text("[]")
    (sd / "verdict-1.json").write_text("{}")
    (sd / "probe-1.pattern").write_text("x")
    if codex_file:
        (sd / "codex-findings.json").write_text('{"findings": []}')
    return sd


def _state_check(sd, mode):
    r = subprocess.run(
        ["bash", str(SCRIPTS / "state-codex-check.sh"), str(sd), mode],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    return dict(re.findall(r"^- ([a-z_]+): ?(.*)$", r.stdout, re.MULTILINE))


def test_state_codex_check_resets_a_merge_that_disagrees_with_the_flag(tmp_path):
    """The lanes skip their review when findings.json exists, so the Codex gate inside
    the review step is never reached on a resume. The check runs before the skip."""
    # --no-codex after a merge that holds Codex findings: reset, drop the Codex source
    sd = _write_state(tmp_path / "a", sources=["claude", "codex"], codex_file=True)
    rows = _state_check(sd, "off")
    assert rows["reset"] == "yes"
    assert not (sd / "findings.json").exists() and not (sd / "verdict-1.json").exists()
    assert not (sd / "probe-1.pattern").exists(), (
        "a re-merge renumbers ids; stale probe files must go"
    )
    assert not (sd / "codex-findings.json").exists(), "merge-prep.sh would re-add it"
    assert (sd / "dim-security.json").exists(), "the reviewer output must survive"

    # --codex after a merge that never had a Codex pass: reset, keep everything else
    sd = _write_state(tmp_path / "b", sources=["claude"], codex_file=False)
    rows = _state_check(sd, "on")
    assert rows["reset"] == "yes"
    assert not (sd / "findings.json").exists()
    assert (sd / "dim-security.json").exists()

    # agreement: nothing happens
    sd = _write_state(tmp_path / "c", sources=["claude"], codex_file=False)
    assert _state_check(sd, "off")["reset"] == "no"
    assert (sd / "findings.json").exists() and (sd / "verdict-1.json").exists()
    sd = _write_state(tmp_path / "d", sources=["claude", "codex"], codex_file=True)
    assert _state_check(sd, "on")["reset"] == "no"
    # auto accepts whatever is cached — a limit-stop resume must stay cheap
    sd = _write_state(tmp_path / "e", sources=["claude"], codex_file=False)
    assert _state_check(sd, "auto")["reset"] == "no"


def test_lanes_run_the_codex_state_check_before_the_skip():
    for lane in ["lane-deep.md", "lane-max.md"]:
        text = read(REF / lane)
        assert "state-codex-check.sh" in text, f"{lane} never reconciles $CODEX with the cache"
        assert text.index("state-codex-check.sh") < text.index("findings.json` exists, skip"), (
            f"{lane} checks the skip before the Codex state, so the check never runs"
        )


def test_deep_lane_always_merges():
    """The self-serialize branch minted no ids: every verdict-<id>.json collided on
    verdict-null.json. One path writes findings.json, and it is merge.md."""
    lane = read(REF / "lane-deep.md")
    assert "dim-full-spectrum.json" in lane
    assert "merge.md" in lane
    assert "yourself" not in lane, "the hand-written findings.json branch is back"
    # The interrupted-resume state: dim-full-spectrum.json present, findings.json absent.
    # Step 1 must skip only the reviewer spawn — the Codex line runs every time, because
    # codex-lane.md is the only thing that sets $CODEX_STATUS — and the flow must fall
    # through to step 3's merge, never to pipeline-tail.md.
    review = lane[lane.index("## 1. Review") : lane.index("## 2.")]
    assert "Skip the spawn when" in review, (
        "step 1 skips the whole step, so a resume never reaches the Codex pass"
    )
    assert review.index("Skip the spawn when") < review.index("run the Codex pass"), (
        "the Codex line sits under the spawn skip"
    )
    assert "Run it every time" in review
    between = lane[lane.index("## 1. Review") : lane.index("Follow `merge.md`. Always")]
    assert "pipeline-tail.md" not in between, (
        "a step between the review and the merge jumps to pipeline-tail.md — the old "
        "shortcut past merge.md, reworded"
    )
    prep = read(SCRIPTS / "merge-prep.sh")
    assert "has no dim files" not in prep, (
        "merge-prep.sh still describes a deep lane without a dim file"
    )


def test_codex_on_stops_when_the_pass_fails():
    """`--codex` means required. Availability already stops; execution failure must too."""
    lane = read(REF / "codex-lane.md")
    row = next(line for line in lane.splitlines() if line.startswith("| `failed` |"))
    assert "`on`" in row and "stop" in row.lower(), (
        "a Codex execution failure under --codex degrades to Claude-only instead of stopping"
    )
    assert "`auto`" in row and "continue" in row.lower(), (
        "the failed row lost the auto → continue branch"
    )


def test_codex_mode_is_relayed_into_the_fix_loop():
    """The loop runs review-code-run many times; without the relay each run defaults to auto
    and the user cannot keep the loop Claude-only."""
    loop = read(PLUGIN / "skills/review-fix-run/SKILL.md")
    assert "--no-codex" in loop and "--codex" in loop, "the loop does not accept the Codex flags"
    assert re.search(r"^Codex: `\{auto \| on \| off\}`$", loop, re.MULTILINE), (
        "the review-code-runner prompt has no Codex: line"
    )
    assert "Codex co-review:" in loop, "the loop summary does not disclose the Codex mode"
    runner = read(PLUGIN / "agents/review-code-runner.md")
    assert "`Codex:`" in runner and "--no-codex" in runner and "--codex" in runner, (
        "review-code-runner does not turn the Codex: line back into the routing token"
    )


def _run_review_with_stub_codex(tmp_path, *, env_extra, cache):
    """Run the real codex-review.sh with a stub `codex` that records its argv.

    Runs from a cwd holding a file named like a default glob, so a `*-sol` that the
    script lets the shell expand turns into `decoy-sol` and the case under test fails.
    Returns (stdout, argv or None). argv is None when `codex exec` never ran.
    """
    root = tmp_path / "root"
    root.mkdir()
    (root / "app.py").write_text("x = 1\n")
    (tmp_path / "decoy-sol").write_text("")
    diff = tmp_path / "surface.diff"
    diff.write_text(
        "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -0,0 +1 @@\n+x = 1\n"
    )
    stub = tmp_path / "stub"
    stub.mkdir()
    argv_file = tmp_path / "argv.txt"
    (stub / "codex").write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{argv_file}"\nexit 1\n')
    (stub / "codex").chmod(0o755)

    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    if cache is not None:
        (home / ".codex/models_cache.json").write_text(cache)

    env = {
        **os.environ,
        "PATH": f"{stub}:{os.environ['PATH']}",
        "HOME": str(home),
        "TMPDIR": str(tmp_path),
    }
    for var in ("CODEX_HOME", "CODEX_MODEL", "CODEX_MODELS"):
        env.pop(var, None)
    env.update(env_extra)
    out = subprocess.run(
        [
            "bash",
            str(SCRIPTS / "codex-review.sh"),
            str(root),
            "diff",
            str(diff),
            "master",
            "-",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=tmp_path,
    ).stdout
    argv = argv_file.read_text().splitlines() if argv_file.exists() else None
    return out, argv


def _models_cache(*models):
    """Each model is a slug or a (slug, priority) pair; priority defaults to position."""
    rows = []
    for i, m in enumerate(models):
        slug, priority = m if isinstance(m, tuple) else (m, i)
        rows.append({"slug": slug, "priority": priority})
    return json.dumps({"models": rows})


@pytest.mark.parametrize(
    "env_extra,cache,expected",
    [
        # explicit opt-in wins, even when the cache would choose differently
        ({"CODEX_MODEL": "gpt-6-astra"}, _models_cache("gpt-5.6-sol"), "gpt-6-astra"),
        # the default globs skip the frontier model the picker lists first
        ({}, _models_cache("gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-terra"), "gpt-5.6-sol"),
        # a new generation needs no edit: lowest priority among the glob's matches
        (
            {},
            _models_cache(("gpt-5.6-sol", 5), ("gpt-5.7-sol", 3)),
            "gpt-5.7-sol",
        ),
        # list order is the preference, priority only breaks ties within one entry
        (
            {},
            _models_cache(("gpt-5.6-terra", 1), ("gpt-5.6-sol", 9)),
            "gpt-5.6-sol",
        ),
        ({}, _models_cache("gpt-6-astra", "gpt-5.6-terra"), "gpt-5.6-terra"),
        (
            {"CODEX_MODELS": "x-cheap gpt-5.6-luna"},
            _models_cache("gpt-5.6-luna"),
            "gpt-5.6-luna",
        ),
        # no cache to consult: first literal entry, codex exec reports its own error
        ({"CODEX_MODELS": "*-sol gpt-5.6-terra"}, None, "gpt-5.6-terra"),
        ({"CODEX_MODELS": "gpt-5.6-terra"}, "not json", "gpt-5.6-terra"),
    ],
    ids=[
        "explicit",
        "skips-frontier",
        "newest-generation",
        "list-order-over-priority",
        "second-choice",
        "custom-list",
        "no-cache",
        "bad-cache",
    ],
)
def test_codex_exec_always_gets_an_explicit_resolved_model(tmp_path, env_extra, cache, expected):
    """Without `-c model=`, Codex falls back to the user's configured model, which may
    be a frontier one; a hardcoded single default is rejected by ChatGPT-account sign-ins
    with a 400. Every run must carry a model resolved from CODEX_MODEL or CODEX_MODELS."""
    out, argv = _run_review_with_stub_codex(tmp_path, env_extra=env_extra, cache=cache)
    assert argv is not None and argv[0] == "exec", f"codex exec never ran:\n{out}"
    models = [a for a in argv if a.startswith("model=")]
    assert models == [f"model={expected}"], (
        f"codex exec ran with {models or 'no model'}, expected model={expected}"
    )
    assert "- status: failed" in out and "codex exec failed" in out


def _reason(out):
    return next(line for line in out.splitlines() if line.startswith("- reason: "))


def test_no_allowlisted_model_fails_with_the_fix(tmp_path):
    """A cache that matches none of CODEX_MODELS must fail loudly — a silent fallback
    would pick whatever Codex defaults to, frontier models included. The reason is
    what a user acts on, so it names what to pick from and where to set it."""
    cache = json.dumps(
        {
            "models": [
                {
                    "slug": "gpt-6-astra",
                    "priority": 2,
                    "visibility": "list",
                    "description": "Frontier intelligence.",
                },
                {
                    "slug": "gpt-7-nova",
                    "priority": 3,
                    "visibility": "list",
                    "description": "Workhorse model.",
                },
                {"slug": "gpt-hidden", "priority": 4, "visibility": "hide"},
            ]
        }
    )
    out, argv = _run_review_with_stub_codex(tmp_path, env_extra={}, cache=cache)
    assert argv is None, "codex exec ran although no allowlisted model is available"
    reason = _reason(out)
    assert "*-sol *-terra" in reason, "the reason omits the preference list"
    assert "gpt-7-nova (Workhorse model.)" in reason, (
        "the reason must list each offered model with its description to choose from"
    )
    assert "gpt-hidden" not in reason, "hidden models are not something to suggest"
    assert '~/.claude/settings.json: {"env": {"CODEX_MODELS": "<slug>"}}' in reason, (
        "the reason lost the settings.json snippet that unblocks every later review"
    )


def test_globs_without_a_cache_fail_before_codex_runs(tmp_path):
    """A glob is not a model name; passing `*-sol` to codex exec would only move the
    failure into Codex with a worse message."""
    out, argv = _run_review_with_stub_codex(tmp_path, env_extra={}, cache=None)
    assert argv is None, "codex exec ran with no resolvable model"
    reason = _reason(out)
    assert "models_cache.json" in reason and "CODEX_MODEL" in reason


def test_no_hardcoded_single_model_default():
    """The 400 came from `${CODEX_MODEL:-gpt-5.5}`; any single-model default repeats it."""
    script = read(SCRIPTS / "codex-review.sh")
    assert not re.search(r"\$\{CODEX_MODEL:-[^}]", script), (
        "CODEX_MODEL has a default again — it must be an explicit opt-in only"
    )
    assert '-c model="$MODEL"' in script, "codex exec no longer passes the resolved model"
