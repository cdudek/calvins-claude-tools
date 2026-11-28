"""Arm definitions for the factory eval, as data. An arm is a plain dict; run_eval.py turns it into agent
frontmatter overrides, CLI flags and a system-prompt addendum. Nothing here talks to a model.

Roles: coordinator (the main session), builder, verifier, security (the risky-milestone review when the
reviewer is an Opus agent), ux_verifier. Each is (model alias, effort).
"""
import copy

ROLES = ("coordinator", "builder", "verifier", "security", "ux_verifier")
ABLATIONS = ("integrity", "verifier", "security", "worktrees")

DEFAULT = {
    "name": "default",
    "harness": "factory",          # factory | plain (one agent, same /goal condition, no factory agents)
    "roles": {
        "coordinator": ("sonnet", "medium"),
        "builder": ("sonnet", "high"),
        "verifier": ("opus", "high"),
        "security": ("opus", "high"),
        "ux_verifier": ("sonnet", "medium"),
    },
    "builder_kind": "claude",      # claude | codex-sol (builders delegate to `codex exec -m gpt-6.2-sol`)
    "advisor": None,               # None | "opus"  (claude --advisor)
    "context": "spec",             # spec (delta + intent) | raw (the task's ticket-delta.md)
    "parallel": 3,                 # builders at once: 1 | 3
    "reviewer": "opus",            # opus | codex-astra | off  (security / second-opinion pass)
    "enforcement": "gate",         # gate (test-integrity.sh in code) | prompt (the rule as text only)
    "ablate": [],                  # subset of ABLATIONS
    "cascade": None,               # list of arm names, cheapest first (routing stage)
    "sizing": None,                # {task id: (model, effort)} written into the replay plan, prose and json (adaptive arm)
}

# The planner's sizing rules (SKILL.md "Models and effort") applied by hand to the replayed milestone (HeyDiff M1):
# T1 is a migration, T2 an access and billing rule, T3 and T5 guest read scope (privacy): sonnet high. T4 is a 4-file
# repair that covers no requirement: haiku high. Not every task is small, so the milestone verifier stays Opus high.
ADAPTIVE_SIZING = {"T1": ("sonnet", "high"), "T2": ("sonnet", "high"), "T3": ("sonnet", "high"),
                   "T4": ("haiku", "high"), "T5": ("sonnet", "high")}


def make(name, roles=None, **kw):
    a = copy.deepcopy(DEFAULT)
    a["name"] = name
    for r, v in (roles or {}).items():
        a["roles"][r] = tuple(v)
    a.update(kw)
    bad = set(a["ablate"]) - set(ABLATIONS)
    if bad or a["harness"] not in ("factory", "plain") or a["enforcement"] not in ("gate", "prompt") \
            or a["context"] not in ("spec", "raw") or a["reviewer"] not in ("opus", "codex-astra", "off"):
        raise ValueError(f"bad arm {name}: {bad or a}")
    return a


# Plackett-Burman, 8 runs, 7 two-level factors. Level -1 is the default, +1 the alternative, so an effect
# reads "what changes when I move away from the default".
FACTORS = {
    "A": ("verifier model", "opus", "sonnet", lambda a: a["roles"].__setitem__("verifier", ("sonnet", a["roles"]["verifier"][1]))),
    "B": ("builder effort", "high", "medium", lambda a: a["roles"].__setitem__("builder", (a["roles"]["builder"][0], "medium"))),
    "C": ("advisor", "off", "opus", lambda a: a.__setitem__("advisor", "opus")),
    "D": ("context", "spec", "raw", lambda a: a.__setitem__("context", "raw")),
    "E": ("parallel builders", 3, 1, lambda a: a.__setitem__("parallel", 1)),
    "F": ("reviewer", "opus", "codex-astra", lambda a: a.__setitem__("reviewer", "codex-astra")),
    "G": ("verifier effort", "high", "medium", lambda a: a["roles"].__setitem__("verifier", (a["roles"]["verifier"][0], "medium"))),
}
_GEN = [1, 1, 1, -1, 1, -1, -1]  # the standard N=8 generator row; the other rows are its cyclic shifts, plus all -1
PB_MATRIX = [[_GEN[(j - i) % 7] for j in range(7)] for i in range(7)] + [[-1] * 7]


def pb_arm(i):
    a = make(f"pb{i + 1}")
    for (key, (_, _, _, apply)), lvl in zip(FACTORS.items(), PB_MATRIX[i]):
        if lvl == 1:
            apply(a)
    return a


def pb_levels(arm_name):
    """{factor letter: -1 | +1} for pb1..pb8, else None."""
    if arm_name.startswith("pb") and arm_name[2:].isdigit() and 1 <= int(arm_name[2:]) <= 8:
        return dict(zip(FACTORS, PB_MATRIX[int(arm_name[2:]) - 1]))
    return None


# Builder-only mode: the arm's own verifier and security review are off, so quality comes from the fixed grading.
BUILDER_ONLY = ["verifier", "security"]
GRID_MODELS = ("haiku", "sonnet", "opus")
GRID_EFFORTS = ("low", "medium", "high")


def grid_arms():
    return [make(f"grid_{m}_{e}", roles={"builder": (m, e)}, ablate=list(BUILDER_ONLY))
            for m in GRID_MODELS for e in GRID_EFFORTS]


def routing_arms(cheap=("haiku", "medium"), strong=("opus", "high")):
    """Always-cheap / default / always-strong tiers and the cascade over them. `cheap` comes from the grid result."""
    return [
        make("always_cheap", roles={"builder": cheap, "verifier": ("sonnet", "high")}, reviewer="off"),
        make("always_strong", roles={"builder": strong}),
        make("cascade", cascade=["always_cheap", "default", "always_strong"]),
    ]


def _arms():
    arms = [make("default")]
    arms += grid_arms()
    arms += [pb_arm(i) for i in range(8)]
    arms += [
        make("plain_sonnet", harness="plain", roles={"coordinator": ("sonnet", "high")}),
        make("plain_opus", harness="plain", roles={"coordinator": ("opus", "high")}),
        make("codex_builder", builder_kind="codex-sol"),
        make("ablate_integrity", ablate=["integrity"]),
        make("ablate_verifier", ablate=["verifier"]),
        make("ablate_security", ablate=["security"]),
        make("ablate_worktrees", ablate=["worktrees"]),
        make("enforce_prompt", enforcement="prompt"),
        make("adaptive", sizing=ADAPTIVE_SIZING),
    ]
    return arms + routing_arms()


ARMS = {a["name"]: a for a in _arms()}

STAGES = {
    "0": ["default"],  # calibrate: 3 repeats; also read the factor-level smoke checks in the README
    "grid": [a["name"] for a in grid_arms()],  # builder model x effort, builder-only, 3 repeats
    "1": [f"pb{i}" for i in range(1, 9)] + ["plain_sonnet", "plain_opus", "codex_builder", "default",
          "ablate_integrity", "ablate_verifier", "ablate_security", "ablate_worktrees", "enforce_prompt"],
    "2": ["default"],  # plus the three finalists, by name on the command line
    "3": ["always_cheap", "default", "always_strong", "cascade"],
}


def get(name):
    if name not in ARMS:
        raise KeyError(f"unknown arm {name}; known: {', '.join(ARMS)}")
    return ARMS[name]
