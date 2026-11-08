#!/usr/bin/env bash
# Usage: gather-ecosystem.sh
# Detects project ecosystem, version files, and changelog.
# Output: sections delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- ECOSYSTEM -#-#-    (list, one detected file per line, or `- unknown`)
#   -#-#- VERSION_FILES -#-#- (key-value: file: version-string; or `- none`)
#   -#-#- BEGIN CHANGELOG -#-#- ... -#-#- END CHANGELOG -#-#- (changelog_file: <path> then first 20 lines; or `- none`)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "-#-#- ECOSYSTEM -#-#-"
FOUND=0
for f in pyproject.toml package.json Gemfile go.mod Cargo.toml build.gradle pom.xml \
         CLAUDE.md agents.md .ruby-version docker-compose.yml Dockerfile \
         pnpm-lock.yaml .yarnrc; do
  if [ -f "$f" ]; then
    echo "- $f"
    FOUND=1
  fi
done
for f in *.gemspec; do
  if [ -f "$f" ]; then
    echo "- $f"
    FOUND=1
  fi
done
[ "$FOUND" -eq 0 ] && echo "- unknown"

echo ""
echo "-#-#- VERSION_FILES -#-#-"
FOUND_VER=0
for f in pyproject.toml package.json Cargo.toml build.gradle pom.xml version.txt VERSION; do
  if [ -f "$f" ]; then
    VER=$(grep -oE 'version\s*[:=]\s*"?[0-9]+\.[0-9]+\.[0-9]+[^"]*"?' "$f" | head -1 || true)
    if [ -n "$VER" ]; then
      echo "- $f: $VER"
      FOUND_VER=1
    fi
  fi
done
for f in *.gemspec; do
  if [ -f "$f" ]; then
    VER=$(grep -oE "version\s*=\s*['\"][0-9]+\.[0-9]+\.[0-9]+[^'\"]*['\"]" "$f" | head -1 || true)
    if [ -n "$VER" ]; then
      echo "- $f: $VER"
      FOUND_VER=1
    fi
  fi
done
[ "$FOUND_VER" -eq 0 ] && echo "- none"

echo ""
echo "-#-#- BEGIN CHANGELOG -#-#-"
FOUND_CL=0
for f in CHANGELOG.md CHANGELOG CHANGES.md CHANGES.rst HISTORY.md; do
  if [ -f "$f" ]; then
    echo "- changelog_file: $f"
    head -20 "$f"
    FOUND_CL=1
  fi
done
[ "$FOUND_CL" -eq 0 ] && echo "- none"
echo "-#-#- END CHANGELOG -#-#-"
