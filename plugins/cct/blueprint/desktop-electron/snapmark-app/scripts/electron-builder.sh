#!/bin/sh
# electron-builder, told the installed Electron version: npm workspaces hoist electron to the repo root,
# and electron-builder then reads "^45.0.0" from package.json and refuses a range.
set -e
cd "$(dirname "$0")/.."
version=$(node -p "require('electron/package.json').version")
exec npx electron-builder -c.electronVersion="$version" "$@"
