#!/usr/bin/env bash
# Source this dispatch from scripts/ci-local --decision4, passing body/files/map arguments.
# Dependencies (in the gate environment): Python 3, PyYAML 6.0.3, jsonschema 4.26.0.
set -euo pipefail
shared_sha=770383e955d0b66199f13bbae0e825aa9fface08
checker_sha256=9dfdef3fbe9b013f40cd90cf36b906aec4288f8acd66dbf542c231a5339ef888
cache="$(git rev-parse --path-format=absolute --git-common-dir)/ci-local"
mkdir -p "$cache"
checker="$cache/decision4-$shared_sha.py"
verify_checker() {
  python3 -c 'import hashlib,sys; sys.exit(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest() != sys.argv[2])' "$1" "$checker_sha256"
}
if [ ! -f "$checker" ] || ! verify_checker "$checker"; then
  scratch=$(mktemp "$cache/decision4.XXXXXX")
  trap 'rm -f "$scratch"' EXIT
  curl --fail --silent --show-error --location \
    "https://raw.githubusercontent.com/cdudek/blueprints/$shared_sha/.github/scripts/decision4.py" > "$scratch"
  verify_checker "$scratch" || { echo 'Decision4 checker checksum mismatch' >&2; exit 1; }
  mv "$scratch" "$checker"
  trap - EXIT
fi
python3 "$checker" "$@"
