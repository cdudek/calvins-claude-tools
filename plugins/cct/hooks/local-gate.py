#!/usr/bin/env python3
# Usage: local-gate.py < PreToolUse JSON
# Refuse branch publication without a clean HEAD and repository-owned gate evidence.
# Output sections: none on allow; a blocking explanation on stderr (exit 2).
# Pure local: never evaluates shell input, runs a gate, or opens environment files.

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path


class Blocked(Exception):
    pass


def git(cwd, *args):
    result = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=10
    )
    if result.returncode:
        raise ValueError("git inspection failed")
    return result.stdout.strip()


def resolve(cwd, value):
    path = Path(value)
    return path if path.is_absolute() else cwd / path


def invocation(words, cwd):
    """Strip common execution prefixes; resolve repeated git -C options locally."""
    words = list(words)
    while words and (
        words[0]
        in ("command", "exec", "env", "then", "do", "else", "if", "while", "until", "!")
        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0])
    ):
        words.pop(0)
    if not words:
        return "", [], cwd
    name = Path(words.pop(0)).name
    if name == "git":
        while words and words[0].startswith("-"):
            flag = words.pop(0)
            if flag in ("-C", "-c", "--git-dir", "--work-tree") and words:
                value = words.pop(0)
                if flag in ("-C", "--work-tree"):
                    cwd = resolve(cwd, value)
            elif flag.startswith("-C"):
                cwd = resolve(cwd, flag[2:])
            elif flag.startswith("--work-tree="):
                cwd = resolve(cwd, flag.split("=", 1)[1])
    elif name == "gh":
        while words and words[0].startswith("-"):
            flag = words.pop(0)
            if flag in ("-R", "--repo", "--hostname") and words:
                words.pop(0)
    return name, words, cwd


def tag_or_delete(args, cwd):
    """Only all-tag pushes are exempt; --follow-tags/mixed branch pushes still gate."""
    positional = []
    remote_option = False
    tags = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--delete", "-d"):
            return True
        if arg == "--tags":
            tags = True
        elif arg in ("--all", "--branches", "--mirror", "--follow-tags"):
            return False
        elif arg in ("--repo", "--receive-pack", "--exec", "--push-option", "-o"):
            remote_option = remote_option or arg == "--repo"
            i += 1
        elif arg.startswith("--repo="):
            remote_option = True
        elif not arg.startswith("-"):
            positional.append(arg)
        i += 1
    refs = positional if remote_option else positional[1:]  # remote can be an option
    if not refs:
        return tags
    i = 0
    while i < len(refs):
        ref = refs[i].lstrip("+")
        if ref == "tag" and i + 1 < len(refs):
            i += 2
            continue
        source, _, destination = ref.partition(":")
        if not source:  # deletion refspec
            i += 1
            continue
        if destination:
            if not destination.startswith("refs/tags/"):
                return False
            i += 1
            continue
        if not source.startswith("refs/tags/"):
            try:
                git(cwd, "show-ref", "--verify", "refs/tags/" + source)
                try:
                    git(cwd, "show-ref", "--verify", "refs/heads/" + source)
                except ValueError:
                    pass
                else:
                    return False
            except ValueError:
                return False
        i += 1
    return True


def check(cwd, unsafe_prefix=False):
    try:
        root = Path(git(cwd, "rev-parse", "--show-toplevel"))
    except (ValueError, OSError):
        return  # outside a repository
    declared = (root / "scripts/ci-local").is_file()
    # Removing a gate in the dirty tree must not disable the guard. Inspect only
    # these two known paths in HEAD; never source files or follow package symlinks.
    if not declared:
        try:
            git(root, "cat-file", "-e", "HEAD:scripts/ci-local")
            declared = True
        except ValueError:
            pass
    if not declared:
        candidates = []
        package_path = root / "package.json"
        try:
            if not package_path.is_symlink():
                candidates.append(package_path.read_text())
        except OSError:
            pass
        try:
            candidates.append(git(root, "show", "HEAD:package.json"))
        except ValueError:
            pass
        for content in candidates:
            try:
                package = json.loads(content)
                scripts = package.get("scripts", {})
                declared = isinstance(scripts, dict) and "ci:local" in scripts
                if declared:
                    break
            except (ValueError, AttributeError):
                pass
    if not declared:
        return
    head = "unknown"
    try:
        head = git(root, "rev-parse", "--verify", "HEAD")
        common = resolve(root, git(root, "rev-parse", "--git-common-dir"))
        marker = common / "ci-local" / (head + ".ok")
        if not marker.is_file():
            raise Blocked(
                f"Run scripts/ci-local first: no green local run for HEAD {head}"
            )
        if git(
            root,
            "status",
            "--porcelain",
            "--untracked-files=normal",
            "--ignore-submodules=none",
        ):
            raise Blocked(
                f"Run scripts/ci-local first: worktree is dirty for HEAD {head}; commit the final changes and rerun the gate"
            )
        if unsafe_prefix:
            raise Blocked(
                "Run checks and publication in separate Bash calls: an earlier command could change the verified HEAD or worktree"
            )
    except (ValueError, OSError) as exc:
        raise Blocked(
            f"Run scripts/ci-local first: cannot verify a clean green local run for HEAD {head}"
        ) from exc


def inspect(command, cwd, unsafe_prefix=False):
    # shlex preserves quoted arguments as single words; text in echo/PR bodies is
    # never treated as a command. No expansion, sourcing, or shell execution.
    lexer = shlex.shlex(
        command.replace("\\\n", ""), posix=True, punctuation_chars=";&|()\n"
    )
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    words = []
    unsafe = unsafe_prefix
    stack = []

    def visit():
        nonlocal cwd, unsafe
        if not words:
            return
        name, args, location = invocation(words, cwd)
        if (
            name in ("bash", "sh", "zsh")
            and len(args) >= 2
            and args[0] in ("-c", "-lc")
        ):
            inspect(args[1], location, unsafe)
        elif name == "cd" and (len(args) == 1 or (len(args) == 2 and args[0] == "--")):
            cwd = resolve(cwd, args[-1])
            return
        elif name == "git" and args[:1] == ["push"]:
            if not tag_or_delete(args[1:], location):
                check(location, unsafe)
        elif name == "gh" and args[:2] in (["pr", "create"], ["pr", "ready"]):
            check(location, unsafe)
        unsafe = True

    try:
        for token in lexer:
            if token and all(c in ";&|()\n" for c in token):
                visit()
                words = []
                for char in token:
                    if char == "(":
                        stack.append(cwd)
                    elif char == ")" and stack:
                        cwd = stack.pop()
            else:
                words.append(token)
        visit()
    except ValueError:
        # Never run the shell to resolve ambiguous syntax. Publication must be
        # retried as a simple command when this repository declares a gate.
        if re.search(r"\b(?:git\s+push|gh\s+pr\s+(?:create|ready))\b", command):
            check(cwd, unsafe_prefix=True)


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get("tool_name", "Bash") != "Bash":
        return
    command = data.get("tool_input", {}).get("command", "")
    if not isinstance(command, str) or not command:
        return
    inspect(
        command,
        Path(data.get("tool_input", {}).get("cwd") or data.get("cwd") or Path.cwd()),
    )


if __name__ == "__main__":
    try:
        main()
    except (Blocked, subprocess.TimeoutExpired) as error:
        print(f"Local gate blocked publication: {error}", file=sys.stderr)
        sys.exit(2)
