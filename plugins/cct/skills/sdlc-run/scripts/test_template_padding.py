"""templates/tests/sdlc.test.ts satisfies the padding-line rule some repos lint their tests with.

The rule (eslint `padding-line-between-statements`, as a repo configures it): a blank line around every
multi-line const/let/var, before `return`, `if`, `for`, `while`, `switch` and `try`, after a block-like
statement (one that ends with the `}` of a block), and before a function declaration. Consecutive
single-line bindings may stay together, and the first statement of a block needs nothing before it.
`padding_gaps` is a small statement splitter for exactly this file's TypeScript, not a parser.
"""

from __future__ import annotations

import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "tests" / "sdlc.test.ts"
KEYWORD_BLOCKS = {"if", "for", "while", "switch", "try", "function", "class", "do", "async"}
NEEDS_BLANK_BEFORE = {"return", "if", "for", "while", "switch", "try"}
DECLARATIONS = {"const", "let", "var"}
REGEX_AFTER = set("(,=:[!&|?{};") | {"return", "=>", "typeof", "case"}


def tokens(text: str) -> list[tuple[str, int]]:
    """(token, line) for code only: comments dropped, a string or template literal one token, a regex one token."""
    out: list[tuple[str, int]] = []
    i, line, n = 0, 1, len(text)

    def skip_string(i: int, quote: str) -> int:
        i += 1
        while i < n and text[i] != quote:
            i += 2 if text[i] == "\\" else 1
        return i + 1

    def skip_template(i: int) -> int:
        i += 1
        while i < n and text[i] != "`":
            if text[i] == "\\":
                i += 2
            elif text.startswith("${", i):
                depth, i = 1, i + 2
                while i < n and depth:
                    if text[i] in "\"'":
                        i = skip_string(i, text[i])
                        continue
                    if text[i] == "`":
                        i = skip_template(i)
                        continue
                    depth += {"{": 1, "}": -1}.get(text[i], 0)
                    i += 1
            else:
                i += 1
        return i + 1

    while i < n:
        c = text[i]
        if c == "\n":
            line, i = line + 1, i + 1
        elif c.isspace():
            i += 1
        elif text.startswith("//", i):
            i = text.find("\n", i) if "\n" in text[i:] else n
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            line += text.count("\n", i, end)
            i = end
        elif c in "\"'":
            j = skip_string(i, c)
            out.append((text[i:j], line))
            i = j
        elif c == "`":
            j = skip_template(i)
            out.append((text[i:j], line))
            line += text.count("\n", i, j)
            i = j
        elif c == "/" and (not out or out[-1][0] in REGEX_AFTER):
            j, in_class = i + 1, False
            while j < n and (in_class or text[j] != "/"):
                in_class = in_class or text[j] == "["
                in_class = in_class and text[j] != "]"
                j += 2 if text[j] == "\\" else 1
            j += 1
            while j < n and text[j].isalpha():
                j += 1
            out.append((text[i:j], line))
            i = j
        elif m := re.match(r"[A-Za-z_$][\w$]*|\d[\w.]*|=>|\.\.\.|\S", text[i:]):
            out.append((m[0], line))
            i += len(m[0])
    return out


def padding_gaps(text: str) -> list[tuple[int, str]]:
    """(line of the statement that needs a blank line before it, why) for every missing padding line."""
    toks, lines = tokens(text), text.split("\n")
    problems: list[tuple[int, str]] = []
    # one frame per open bracket: ["block" | "other", statements so far, current statement start, kind]
    stack: list[dict] = [{"kind": "block", "stmts": [], "start": None}]
    pending_fn = False

    def blank_between(a: int, b: int) -> bool:
        return any(not lines[k - 1].strip() for k in range(a + 1, b))

    def close_statements(frame: dict) -> None:
        stmts = frame["stmts"]
        for prev, nxt in zip(stmts, stmts[1:]):
            why = (
                f"before `{nxt['first']}`" if nxt["first"] in NEEDS_BLANK_BEFORE
                else "around a multi-line declaration" if (prev["multi"] and prev["decl"]) or (nxt["multi"] and nxt["decl"])
                else "after a block-like statement" if prev["block_like"]
                else "before a function" if nxt["first"] in ("function", "async") and nxt["is_fn"]
                else ""
            )  # fmt: skip
            if why and not blank_between(prev["end_line"], nxt["start_line"]):
                problems.append((nxt["start_line"], why))

    def end_statement(frame: dict, index: int, block_like: bool) -> None:
        first, start_line = frame["start"]
        first_tok = toks[frame["start_index"]][0]
        end_line = toks[index][1]
        words = [t for t, _ in toks[frame["start_index"] : frame["start_index"] + 3]]
        if first_tok == "export":
            words = words[1:] + [""]
        frame["stmts"].append({
            "first": words[0], "start_line": start_line, "end_line": end_line, "block_like": block_like,
            "decl": words[0] in DECLARATIONS, "multi": start_line != end_line,
            "is_fn": words[0] == "function" or words[:2] == ["async", "function"],
        })  # fmt: skip
        frame["start"] = None

    i = 0
    while i < len(toks):
        tok, line = toks[i]
        frame = stack[-1]
        if tok == "function":
            pending_fn = True
        if frame["kind"] == "block" and frame["start"] is None and tok not in (";", "}"):
            frame["start"], frame["start_index"] = (tok, line), i
            frame["depth0_block"] = False
        if tok in "([":
            stack.append({"kind": "other", "stmts": [], "start": None})
        elif tok == "{":
            prev = toks[i - 1][0] if i else ""
            if pending_fn and prev not in (":", "|", "&", "<", ","):
                is_block, pending_fn = True, False
            else:
                is_block = prev in (")", "=>", "else", "try", "finally", "do", ";", "{", "}", "catch") or i == 0
            stack.append({"kind": "block" if is_block else "other", "stmts": [], "start": None, "owner": frame})
        elif tok in ")]}":
            done = stack.pop()
            if done["kind"] == "block":
                close_statements(done)
            parent = stack[-1]
            if tok == "}" and done["kind"] == "block" and parent["kind"] == "block" and parent["start"] is not None:
                nxt = toks[i + 1][0] if i + 1 < len(toks) else ""
                starter = parent["start"][0] in ("export", *KEYWORD_BLOCKS, "{")
                if starter and nxt not in ("else", "catch", "finally"):
                    end_statement(parent, i, True)
                else:
                    parent["last_brace"] = i
        elif tok == ";" and frame["kind"] == "block" and frame["start"] is not None:
            nxt = toks[i + 1][0] if i + 1 < len(toks) else ""
            if nxt != "else":
                prev_brace = frame.get("last_brace") == i - 1
                end_statement(frame, i, prev_brace and toks[i - 1][0] == "}")
        i += 1
    close_statements(stack[0])
    return sorted(problems)


def test_the_node_guardrail_template_satisfies_the_padding_line_rule() -> None:
    gaps = padding_gaps(TEMPLATE.read_text(encoding="utf-8"))
    assert not gaps, "a blank line is missing before these lines:\n" + "\n".join(f"  line {n}: {why}" for n, why in gaps)


def test_the_checker_flags_what_the_rule_forbids_and_allows_what_it_allows() -> None:
    bad = "function a() {\n  const x = 1;\n  if (x) {\n    return 1;\n  }\n  return 2;\n}\nconst y = {\n  a: 1,\n};\nconst z = 2;\n"
    assert [why for _, why in padding_gaps(bad)] == ["before `if`", "before `return`", "around a multi-line declaration", "around a multi-line declaration"]
    good = "function a() {\n  const x = 1;\n  const w = 2;\n\n  if (x) {\n    return 1;\n  }\n\n  return 2;\n}\n\nconst y = {\n  a: 1,\n};\n\nconst z = 2;\n"
    assert padding_gaps(good) == []
