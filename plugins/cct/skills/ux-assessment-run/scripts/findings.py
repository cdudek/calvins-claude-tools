#!/usr/bin/env python3
# Usage:
#   python3 findings.py validate <file.json>... [--expect L1-L30,B1-B14]
#   python3 findings.py merge <pass.json>... --skill cct:ux-assessment-run -o <merged.json>
#   python3 findings.py render <merged.json> -o <findings.md> [--previous <prev.json>] [--title T] [--order impact|location]
#   python3 findings.py compare <previous.json> <current.json>
#
# Purpose: the one findings contract of the ux skills, enforced by script. Every pass writes JSON to
# references/findings.schema.json; this file checks it, merges the passes, renders findings.md in
# finding-format.md's shape and compares two rounds. Do not type the report by hand.
#
# Rules it holds: merge dedupes ONLY the same id at the same location and lists every source; it
# never splits or drops a finding. Output is deterministic (same input, same bytes). Python
# standard library only, no network: the schema is checked by a small validator that refuses any
# schema keyword it does not implement, so the schema cannot grow a rule that is silently skipped.
#
# Output sections (stdout):
#   validate  -#-#- VALIDATE -#-#-  one `- <file>: ok|FAIL` row per file, errors indented below
#             -#-#- SUMMARY -#-#-   files, failed; exit 1 when any file failed
#   merge     -#-#- MERGE -#-#-     passes, findings, duplicates merged, notes added, out
#   render    -#-#- RENDER -#-#-    out, findings
#   compare   -#-#- COMPARE -#-#-   regressed, new, persistent, fixed, not_rechecked
#             -#-#- BEGIN REPORT -#-#- / -#-#- END REPORT -#-#-  the markdown section

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "references" / "findings.schema.json"
IMPACTS = ["Critical", "High", "Medium", "Low", "Design choice"]
VERIFIED = {
    "seen": "seen on screen",
    "code": "read in the code",
    "measured": "measured",
    "assumption": "assumption, not checked",
    "preference": "owner's preference",
}
IMAGE = re.compile(r"\.(png|jpe?g|webp|gif)$", re.I)
FAMILY = re.compile(r"^([A-Za-z]+[0-9]+)\.")  # L7.2 belongs to law L7, B5.1 to B5

# -#-#- the validator: exactly the keywords the schema uses -#-#-

SUPPORTED = {
    "$schema", "$id", "$defs", "$ref", "title", "description", "type", "required", "properties",
    "additionalProperties", "items", "enum", "const", "pattern", "minLength", "maxLength",
    "minItems", "allOf", "if", "then",
}  # fmt: skip
TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
}


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _check(node: dict, value, path: str, errors: list[str], root: dict) -> None:
    unknown = set(node) - SUPPORTED
    if unknown:
        raise ValueError(f"schema keyword(s) not implemented by findings.py: {sorted(unknown)}")
    if "$ref" in node:
        target = root
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        _check(target, value, path, errors, root)
        return
    kind = node.get("type")
    if kind and not TYPES[kind](value):
        errors.append(f"{path}: expected {kind}")
        return
    if "const" in node and value != node["const"]:
        errors.append(f"{path}: must be {node['const']!r}")
    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: {value!r} is not one of {node['enum']}")
    if isinstance(value, str):
        pattern = node.get("pattern")
        # ECMA-262 `$` is end of input; Python's also matches before a final newline.
        if pattern and not re.search(re.sub(r"\$$", r"\\Z", pattern), value):
            errors.append(f"{path}: does not match {pattern}")
        if len(value) < node.get("minLength", 0):
            errors.append(f"{path}: empty")
        if "maxLength" in node and len(value) > node["maxLength"]:
            errors.append(f"{path}: longer than {node['maxLength']} characters")
    if isinstance(value, list):
        if len(value) < node.get("minItems", 0):
            errors.append(f"{path}: needs at least {node['minItems']} item(s)")
        for i, item in enumerate(value):
            if "items" in node:
                _check(node["items"], item, f"{path}[{i}]", errors, root)
    if isinstance(value, dict):
        for key in node.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing {key}")
        props = node.get("properties", {})
        for key, item in value.items():
            if key in props:
                _check(props[key], item, f"{path}.{key}", errors, root)
            elif node.get("additionalProperties") is False:
                errors.append(f"{path}: unknown field {key}")
    for sub in node.get("allOf", []):
        _check(sub, value, path, errors, root)
    if "if" in node:
        probe: list[str] = []
        _check(node["if"], value, path, probe, root)
        if not probe and "then" in node:
            _check(node["then"], value, path, errors, root)


def validate(doc, schema: dict | None = None) -> list[str]:
    schema = schema or load_schema()
    errors: list[str] = []
    _check(schema, doc, "$", errors, schema)
    return errors


def expand(expect: str) -> list[str]:
    """`L1-L30,B1-B14,WCAG-1.1.1` -> every id named, ranges written out."""
    ids: list[str] = []
    for token in filter(None, (t.strip() for t in expect.split(","))):
        m = re.fullmatch(r"([A-Za-z]+)([0-9]+)-\1([0-9]+)", token)
        if m:
            ids += [f"{m[1]}{n}" for n in range(int(m[2]), int(m[3]) + 1)]
        else:
            ids.append(token)
    return ids


def family(ident: str) -> str:
    m = FAMILY.match(ident)
    return m[1] if m else ident


def unaccounted(doc: dict, expect: str) -> list[str]:
    """Expected ids that appear nowhere: a blank coverage row is a pass that did not run."""
    seen = set(doc["passed"]) | {f["id"] for f in doc["findings"]}
    seen |= {s["id"] for s in doc.get("not_applicable", []) + doc["did_not_run"]}
    seen |= {family(i) for i in seen}
    return [i for i in expand(expect) if i not in seen]


# -#-#- merge -#-#-


def _rank(finding: dict) -> tuple:
    return (IMPACTS.index(finding["impact"]), finding["location"], finding["id"])


def _union(*lists) -> list:
    out: list = []
    for items in lists:
        out += [i for i in items if i not in out]
    return out


def merge(docs: list[dict], skill: str) -> dict:
    passes: list[dict] = []
    scope: dict = {}
    by_key: dict[tuple, dict] = {}
    passed_by: dict[str, list[str]] = {}
    skipped = {"not_applicable": set(), "did_not_run": set()}
    exceptions: set[str] = set()
    notes: list[str] = []
    duplicates = 0

    for doc in docs:
        if doc.get("passes"):
            passes += doc["passes"]
            notes += doc["notes"]
        else:
            entry = {"skill": doc["skill"], "method": doc["method"]}
            if doc.get("degraded"):
                entry["degraded"] = doc["degraded"]
            passes.append(entry)
            notes += [f"{doc['skill']}: {n}" for n in doc["notes"]]
        for key, value in doc["scope"].items():
            if key == "pr":
                if scope.get("pr", value) != value:
                    notes.append(
                        f"merge: scope.pr differs ({scope['pr']} vs {value}); kept the first"
                    )
                scope.setdefault("pr", value)
            else:
                scope[key] = sorted(set(scope.get(key, [])) | set(value))
        for ident in doc["passed"]:
            passed_by.setdefault(ident, []).append(doc["skill"])
        for field in skipped:
            skipped[field] |= {(s["id"], s["reason"]) for s in doc.get(field, [])}
        exceptions |= set(doc["exceptions_used"])
        for f in doc["findings"]:
            f = dict(
                f, sources=_union(f.get("sources", []), [] if doc.get("passes") else [doc["skill"]])
            )
            key = (f["id"], f["location"])
            kept = by_key.get(key)
            if kept is None:
                by_key[key] = f
                continue
            duplicates += 1
            where = f"{f['id']} at {f['location']}"
            if kept["impact"] != f["impact"]:
                worse = min(kept["impact"], f["impact"], key=IMPACTS.index)
                notes.append(
                    f"merge: impact differs for {where}: {', '.join(kept['sources'])} said "
                    f"{kept['impact']}, {', '.join(f['sources'])} said {f['impact']}; kept {worse}"
                )
                kept["impact"] = worse
            if kept["verified"] != f["verified"]:
                notes.append(
                    f"merge: verified differs for {where}: {kept['verified']} vs {f['verified']}; kept the first"
                )
            kept["sources"] = _union(kept["sources"], f["sources"])
            kept["evidence"] = _union(kept["evidence"], f["evidence"])

    findings = sorted(by_key.values(), key=_rank)
    failing = {f["id"] for f in findings} | {family(f["id"]) for f in findings}
    for ident in sorted(passed_by):
        if ident in failing:
            fails = [f for f in findings if ident in (f["id"], family(f["id"]))]
            notes.append(
                f"merge: {ident} passed in {', '.join(passed_by[ident])} but failed in "
                f"{', '.join(_union(*(f['sources'] for f in fails)))}; reported as failed"
            )
    degraded = [p["skill"] for p in passes if p.get("degraded")]
    merged = {
        "skill": skill,
        "version": "1",
        "scope": scope,
        "method": f"merged from {len(passes)} pass file(s) by findings.py",
        "passes": passes,
        "findings": findings,
        "passed": sorted(i for i in passed_by if i not in failing),
        "not_applicable": [{"id": i, "reason": r} for i, r in sorted(skipped["not_applicable"])],
        "did_not_run": [{"id": i, "reason": r} for i, r in sorted(skipped["did_not_run"])],
        "exceptions_used": sorted(exceptions, key=lambda e: int(e[3:])),
        "notes": notes,
    }
    if degraded:
        merged["degraded"] = (
            f"{len(degraded)} pass(es) ran without their agent or skill: {', '.join(degraded)}"
        )
    merged["_duplicates"] = duplicates
    return merged


# -#-#- compare -#-#-


def _skills(doc: dict) -> set[str]:
    return {p["skill"] for p in doc.get("passes", [])} or {doc["skill"]}


def compare(prev: dict, cur: dict) -> dict[str, list[tuple[dict, str]]]:
    """Regressed, New, Persistent, Fixed by id + location; Not re-checked when nothing looked."""
    old = {(f["id"], f["location"]): f for f in prev["findings"]}
    new_keys = {(f["id"], f["location"]) for f in cur["findings"]}
    prev_passed = set(prev["passed"])
    ran = _skills(cur)
    not_run = {s["id"]: s["reason"] for s in cur["did_not_run"]}
    out: dict[str, list[tuple[dict, str]]] = {
        k: [] for k in ("Regressed", "New", "Persistent", "Fixed", "Not re-checked")
    }
    for f in cur["findings"]:
        was = old.get((f["id"], f["location"]))
        if was:
            note = (
                f"{f['impact']}, was {was['impact']}"
                if was["impact"] != f["impact"]
                else f["impact"]
            )
            out["Persistent"].append((f, note))
        elif f["id"] in prev_passed or family(f["id"]) in prev_passed:
            out["Regressed"].append((f, f"{f['impact']}, passed last round"))
        else:
            out["New"].append((f, f["impact"]))
    for key, f in old.items():
        if key in new_keys:
            continue
        reason = not_run.get(f["id"]) or not_run.get(family(f["id"]))
        if reason is None and f.get("sources") and not ran & set(f["sources"]):
            reason = f"{', '.join(f['sources'])} did not run this round"
        if reason:
            out["Not re-checked"].append((f, f"did not run: {reason}"))
        else:
            out["Fixed"].append((f, f["impact"]))
    for rows in out.values():
        rows.sort(key=lambda row: _rank(row[0]))
    return out


def render_compare(result: dict[str, list[tuple[dict, str]]]) -> str:
    counts = ", ".join(f"{k} {len(v)}" for k, v in result.items())
    lines = ["## Since the last round", "", f"{counts}.", ""]
    for name, rows in result.items():
        lines += [f"### {name}", ""]
        lines += [f"- {f['id']} at {f['location']}: {f['summary']} ({note})" for f, note in rows]
        lines += (["- none"] if not rows else []) + [""]
    return "\n".join(lines)


# -#-#- render -#-#-


def _finding(n: int, f: dict) -> str:
    images = [e for e in f["evidence"] if IMAGE.search(e)]
    other = [e for e in f["evidence"] if e not in images]
    visual = ", ".join(f"![F{n:03d}]({p})" for p in images) or "none attached"
    notes = [
        f"- Where: {f['location']}",
        f"- Broken: {f['id']} ({f['lens']})",
        f"- Rung: {f.get('conflict', f['rung'])}",
    ]
    notes += [f"- Evidence: {'; '.join(other)}"] if other else []
    notes += [f"- Component: {f['component']}"] if f.get("component") else []
    notes += [f"- {line}" for line in f.get("supporting_notes", [])]
    seen_by = f.get("sources", [])
    notes.append(
        f"- Seen by: {', '.join(seen_by)} ({len(seen_by)} pass{'es' if len(seen_by) != 1 else ''})"
    )
    return "\n".join(
        [
            f"### F{n:03d}: {f['summary']}",
            f"- **Impact:** {f['impact']}",
            f"- **Current experience:** {f['current']}",
            f"- **Visual:** {visual}",
            f"- **Recommendation:** {f['recommendation']}",
            f"- **Tradeoff:** {f['tradeoff']}",
            f"- **Decision needed:** {f['decision_needed']}",
            f"- **Verified:** {VERIFIED[f['verified']]}",
            f"- **Owner's words:** {f['owner_words']}",
            "",
            "<details><summary>Supporting notes</summary>",
            "",
            *notes,
            "",
            "</details>",
            "",
        ]
    )


def render(doc: dict, title: str, order: str = "impact", previous: dict | None = None) -> str:
    passes = doc.get("passes") or [{k: doc[k] for k in ("skill", "method", "degraded") if k in doc}]
    findings = doc["findings"]
    if order == "location":
        findings = sorted(findings, key=lambda f: (f["location"], *_rank(f)))
    out = [f"# {title}", ""]
    degraded = [p for p in passes if p.get("degraded")]
    if degraded:
        out += [
            f"> **Degraded run.** {len(degraded)} pass(es) ran without their agent or skill, so their "
            "findings rest on less evidence than a full run:",
            *[f"> - {p['skill']}: {p['degraded']}" for p in degraded],
            "",
        ]
    out += ["**Method**", "", *[f"- {p['skill']}: {p['method']}" for p in passes], ""]
    scope = doc["scope"]
    parts = [f"PR {scope['pr']}"] if scope.get("pr") else []
    parts += [f"{k}: {', '.join(map(str, v))}" for k, v in scope.items() if k != "pr" and v]
    out += [f"**Scope:** {'; '.join(parts) or 'not stated'}", ""]
    totals = ", ".join(f"{i} {sum(f['impact'] == i for f in findings)}" for i in IMPACTS)
    verified = ", ".join(f"{k} {sum(f['verified'] == k for f in findings)}" for k in VERIFIED)
    out += [f"**Totals:** {totals}. **Verified:** {verified}.", ""]
    if previous is not None:
        out += [render_compare(compare(previous, doc))]
    out += ["## Findings", ""]
    if findings:
        out += [_finding(n, f) for n, f in enumerate(findings, 1)]
    else:
        who = ", ".join(p["skill"] for p in passes)
        out += [
            f"No issues found by {who}. What they checked is listed under Passed; what they could "
            "not check is under Did not run.",
            "",
        ]
    out += ["## Passed", "", ", ".join(doc["passed"]) or "Nothing was reported as passed.", ""]
    out += ["## Not applicable", ""]
    out += [f"- {s['id']}: {s['reason']}" for s in doc.get("not_applicable", [])] or ["- none"]
    out += ["", "## Did not run", ""]
    out += [f"- {s['id']}: {s['reason']}" for s in doc["did_not_run"]] or ["- none"]
    out += ["", "## Exceptions relied on", "", ", ".join(doc["exceptions_used"]) or "None.", ""]
    out += ["## Notes", ""]
    out += [f"- {n}" for n in doc["notes"]] or ["- none"]
    return "\n".join(out) + "\n"


# -#-#- CLI -#-#-


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_valid(paths: list[str]) -> list[dict]:
    docs, bad = [], 0
    for path in paths:
        doc = _load(path)
        errors = validate(doc)
        for e in errors:
            print(f"- {path}: FAIL {e}")
        bad += bool(errors)
        docs.append(doc)
    if bad:
        raise SystemExit(
            f"{bad} file(s) do not match findings.schema.json; fix or re-dispatch the pass"
        )
    return docs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ux findings contract")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("files", nargs="+")
    v.add_argument("--expect", help="ids every file must account for, e.g. L1-L30,B1-B14")
    m = sub.add_parser("merge")
    m.add_argument("files", nargs="+")
    m.add_argument("--skill", required=True)
    m.add_argument("-o", "--out", required=True)
    r = sub.add_parser("render")
    r.add_argument("file")
    r.add_argument("-o", "--out", required=True)
    r.add_argument("--previous")
    r.add_argument("--title", default="UX findings")
    r.add_argument("--order", choices=["impact", "location"], default="impact")
    c = sub.add_parser("compare")
    c.add_argument("previous")
    c.add_argument("current")
    args = ap.parse_args(argv)

    if args.cmd == "validate":
        print("-#-#- VALIDATE -#-#-")
        failed = 0
        for path in args.files:
            try:
                doc = _load(path)
            except (OSError, json.JSONDecodeError) as exc:
                errors = [f"not readable JSON: {exc}"]
            else:
                errors = validate(doc)
                if not errors and args.expect:
                    errors = [
                        f"{i}: not accounted for (pass, finding, n/a or did not run)"
                        for i in unaccounted(doc, args.expect)
                    ]
            print(f"- {path}: {'FAIL' if errors else 'ok'}")
            print("".join(f"  - {e}\n" for e in errors), end="")
            failed += bool(errors)
        print(f"-#-#- SUMMARY -#-#-\n- files: {len(args.files)}\n- failed: {failed}")
        return 1 if failed else 0

    if args.cmd == "merge":
        merged = merge(_load_valid(args.files), args.skill)
        duplicates = merged.pop("_duplicates")
        errors = validate(merged)
        if errors:  # shortcut: a bug in merge itself, never the input; fail loudly
            raise SystemExit(f"merge produced an invalid file: {errors}")
        Path(args.out).write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print("-#-#- MERGE -#-#-")
        print(f"- passes: {len(merged['passes'])}\n- findings: {len(merged['findings'])}")
        print(
            f"- duplicates merged: {duplicates}\n- notes: {len(merged['notes'])}\n- out: {args.out}"
        )
        return 0

    if args.cmd == "render":
        (doc,) = _load_valid([args.file])
        previous = _load_valid([args.previous])[0] if args.previous else None
        Path(args.out).write_text(render(doc, args.title, args.order, previous), encoding="utf-8")
        print(f"-#-#- RENDER -#-#-\n- out: {args.out}\n- findings: {len(doc['findings'])}")
        return 0

    prev, cur = _load_valid([args.previous, args.current])
    result = compare(prev, cur)
    print("-#-#- COMPARE -#-#-")
    for name, rows in result.items():
        print(f"- {name.lower().replace(' ', '_').replace('-', '')}: {len(rows)}")
    print("-#-#- BEGIN REPORT -#-#-")
    print(render_compare(result), end="")
    print("-#-#- END REPORT -#-#-")
    return 0


if __name__ == "__main__":
    sys.exit(main())
