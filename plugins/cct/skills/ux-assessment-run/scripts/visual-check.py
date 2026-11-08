#!/usr/bin/env python3
# Usage: python3 visual-check.py <run> [--repo <product-repo>]
# Purpose: reject incomplete screenshot inspection and ungrounded convention verdicts.
# Output sections: VISUAL_CHECK (status, errors); exit 1 means the visual review did not run.
# Input: <run>/visual.json, with one row per image anywhere under <run>.
# Python standard library only. See the shared references/visual-pass.md for the contract.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".bmp", ".tif", ".tiff"}
CONVENTION = re.compile(r"^(violates|allowed by) ([^#\n]+)#([^#\n]+)$")


def text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def walk_error(error: OSError) -> None:
    raise error


def check(run: Path, repo: Path) -> list[str]:
    errors: list[str] = []
    if not run.is_dir():
        return [f"{run}: run directory is missing"]
    images = {}
    for directory, dirs, files in os.walk(run, onerror=walk_error):
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                errors.append(f"{path}: linked directory cannot be inventoried; copy captures here")
        for name in files:
            path = Path(directory) / name
            if path.suffix.lower() in IMAGES:
                images[path.relative_to(run).as_posix()] = path
    if not images:
        errors.append(f"{run}: no screenshots captured")
    try:
        ledger = json.loads(
            (run / "visual.json").read_text(encoding="utf-8"), object_pairs_hook=unique_object
        )
    except (OSError, ValueError) as exc:
        return (
            errors
            + [f"visual.json: {exc}"]
            + [f"{name}: missing screenshot row" for name in sorted(images)]
        )
    if not isinstance(ledger, dict) or not isinstance(ledger.get("screenshots"), list):
        return (
            errors
            + ["visual.json: expected an object with a screenshots array"]
            + [f"{name}: missing screenshot row" for name in sorted(images)]
        )

    seen: set[str] = set()
    issue_ids: set[str] = set()
    for index, row in enumerate(ledger["screenshots"]):
        if not isinstance(row, dict) or not text(row.get("file")):
            errors.append(f"row {index + 1}: missing screenshot file")
            continue
        name = row["file"]
        if name in seen:
            errors.append(f"{name}: duplicate screenshot row")
        seen.add(name)
        image = images.get(name)
        if image is None:
            errors.append(f"{name}: not a captured screenshot (use a run-relative path)")
        elif row.get("sha256") != hashlib.sha256(image.read_bytes()).hexdigest():
            errors.append(f"{name}: image changed or sha256 is missing; open it again")
        for field in ("screen_state", "opened_with", "observations"):
            if not text(row.get(field)):
                errors.append(f"{name}: missing {field}")
        if type(row.get("width")) is not int or row["width"] <= 0:
            errors.append(f"{name}: width must be a positive integer in CSS pixels")
        issues = row.get("issues")
        if not isinstance(issues, list):
            errors.append(f"{name}: issues must be an array")
            continue
        verdict = row.get("verdict")
        if verdict not in ("compliant", "issues"):
            errors.append(f"{name}: verdict must be compliant or issues")
        elif (verdict == "issues") != bool(issues):
            errors.append(f"{name}: screenshot verdict disagrees with its issues")
        for number, issue in enumerate(issues, 1):
            label = f"{name} issue {number}"
            if not isinstance(issue, dict):
                errors.append(f"{label}: expected an issue object")
                continue
            issue_id = issue.get("id")
            if not text(issue_id):
                errors.append(f"{label}: missing id")
            elif issue_id in issue_ids:
                errors.append(f"{label}: duplicate issue id {issue_id}")
            else:
                issue_ids.add(issue_id)
            if not text(issue.get("summary")):
                errors.append(f"{label}: missing summary")
            decision = issue.get("verdict")
            if decision == "no convention":
                if not text(issue.get("proposal")):
                    errors.append(f"{label}: no convention needs a proposal for cct:ux-decision-log")
                continue
            match = CONVENTION.fullmatch(decision) if isinstance(decision, str) else None
            if not match:
                errors.append(
                    f"{label}: expected exactly one verdict: violates <document>#<section>, "
                    "allowed by <document>#<section>, or no convention"
                )
                continue
            _, document, section = match.groups()
            if not document.strip() or not section.strip():
                errors.append(f"{label}: empty document or section")
            quote = issue.get("quote")
            if not text(quote):
                errors.append(f"{label}: {decision} needs a quoted convention line")
                continue
            source = (repo / document).resolve()
            if not source.is_relative_to(repo.resolve()):
                errors.append(f"{label}: convention must be in the product repo")
                continue
            try:
                lines = source.read_text(encoding="utf-8").splitlines()
            except (OSError, ValueError) as exc:
                errors.append(f"{label}: cannot read convention {document}: {exc}")
                continue
            if quote.strip() not in [line.strip() for line in lines]:
                errors.append(f"{label}: quoted convention line not found in {document}")
    errors.extend(f"{name}: missing screenshot row" for name in sorted(images.keys() - seen))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        errors = check(args.run, args.repo)
    except OSError as exc:
        errors = [f"cannot read screenshot inventory: {exc}"]
    print("-#-#- VISUAL_CHECK -#-#-")
    print(f"- status: {'FAIL — review did not run' if errors else 'PASS — coverage checked'}")
    for error in errors:
        print(f"- error: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
