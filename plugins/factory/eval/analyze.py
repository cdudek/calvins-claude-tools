#!/usr/bin/env python3
"""Usage: analyze.py <results dir> [--default default] [--boot 10000] [--seed 1]
Reads every <stage>/<run>/{run.json,grade.json} below the results dir and writes next to them:
  table.csv        one tidy row per run
  summary.csv      per arm: hidden_frac, solved, cost, cost and tokens per solved task, time (raw and load-adjusted), pass^k,
                   Beta(1,1) P(beats default) on solved, P(dominated) on the cost / hidden_frac front
  comparisons.csv  per arm against the default: log-cost ratio, time (ratio and minutes, raw and load-adjusted), hidden_frac
                   difference, each with a percentile-bootstrap interval, judged against the equivalence band
  effects.csv      Plackett-Burman main effects with stratified-bootstrap intervals (arms pb1..pb8)
  analysis.json    all of it, for plot.py
Runs with an infrastructure failure or an INVALID goal check are listed and left out of every statistic.
Equivalence band: +-10% cost, +-5 min, +-0.05 hidden_frac. n < 10 per comparison is flagged: the bootstrap under-covers there.
"""
import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import configs

BAND = {"cost": 0.10, "time_min": 5.0, "hidden": 0.05}


# ---------------------------------------------------------------- loading

def load_rows(root):
    rows = []
    for rj in sorted(Path(root).glob("*/*/run.json")):
        run = json.loads(rj.read_text())
        gj = rj.parent / "grade.json"
        g = json.loads(gj.read_text()) if gj.exists() else {}
        hf = g.get("hidden_frac")
        tok = g.get("tokens") or {}
        rows.append({
            "run_id": run["run_id"], "stage": run["stage"], "task_id": run["task_id"], "arm": run["arm"], "block": run.get("block"),
            "cascade_id": run.get("cascade_id"), "tier": run.get("tier"), "start_epoch": run.get("start_epoch"), "end_epoch": run.get("end_epoch"),
            "slot": run.get("slot"), "concurrent_at_start": run.get("concurrent_at_start"),
            "graded": bool(g), "valid": g.get("valid", False), "infra": run.get("infra_failure"), "invalid_reason": g.get("invalid_reason"),
            "hidden_frac": hf, "solved": bool(g.get("solved")), "cost": g.get("cost_total", 0.0), "tokens": sum(tok.values()),
            "wall_min": run.get("wall_s", 0.0) / 60, "end_state": g.get("end_state"), "timeout": run.get("timeout"),
            "regression": g.get("regression"), "integrity_violations": g.get("integrity_violations", 0), "unverified_exit": g.get("unverified_exit"),
            "verifier_verdict": g.get("verifier_verdict"), "verifier_false_pass": g.get("verifier_false_pass"),
            "goal_evals": g.get("goal_evals"), "goal_met": g.get("goal_met"), "goal_met_not_solved": g.get("goal_met_not_solved"),
            "claimed_done_not_solved": g.get("claimed_done_not_solved"), "visible_hidden_gap": g.get("visible_hidden_gap"),
            "cache_hit": g.get("cache_hit"), "diff_ratio": g.get("diff_ratio"), "permission_denials": g.get("permission_denials"),
            "cost_by_role": g.get("cost_by_role") or {}, "evaluator_models": g.get("goal_evaluator_models") or [],
            "unexpected_models": g.get("unexpected_models") or [], "files_outside_plan": len(g.get("files_outside_plan") or []),
        })
    return rows


def parallel_load(rows):
    """Mean number of runs in flight (this one included) over each run's own interval."""
    iv = [(r["start_epoch"], r["end_epoch"]) for r in rows if r["start_epoch"] is not None and r["end_epoch"] is not None]
    for r in rows:
        s, e = r["start_epoch"], r["end_epoch"]
        if s is None or e is None or e <= s:
            r["load"] = 1.0
            continue
        r["load"] = sum(max(0.0, min(e, e2) - max(s, s2)) for s2, e2 in iv) / (e - s)


def load_adjust(rows):
    """Within-arm OLS of log(time) on parallel load; returns the slope and sets time_adj_min (time at load 1)."""
    xs, ys = [], []
    by = defaultdict(list)
    for r in rows:
        if r["wall_min"] > 0:
            by[r["arm"]].append(r)
    for rs in by.values():
        mx, my = mean([r["load"] for r in rs]), mean([math.log(r["wall_min"]) for r in rs])
        xs += [r["load"] - mx for r in rs]
        ys += [math.log(r["wall_min"]) - my for r in rs]
    sxx = sum(x * x for x in xs)
    b = sum(x * y for x, y in zip(xs, ys)) / sxx if sxx > 1e-9 else 0.0
    for r in rows:
        r["time_adj_min"] = r["wall_min"] * math.exp(-b * (r["load"] - 1))
    return b


def collapse_cascades(rows):
    """A cascade's tier runs become one row: cost and time add up, quality is the last tier's."""
    out, groups = [], defaultdict(list)
    for r in rows:
        (groups[r["cascade_id"]] if r.get("cascade_id") else out).append(r)
    for cid, rs in groups.items():
        rs.sort(key=lambda r: r["tier"])
        last = dict(rs[-1])
        last.update(arm="cascade", run_id=cid, cost=sum(r["cost"] for r in rs), tokens=sum(r["tokens"] for r in rs),
                    wall_min=sum(r["wall_min"] for r in rs), time_adj_min=sum(r.get("time_adj_min", r["wall_min"]) for r in rs), tiers=len(rs))
        out.append(last)
    return out


# ---------------------------------------------------------------- statistics

def mean(v):
    return sum(v) / len(v) if v else float("nan")


def pass_k(c, n, k):
    """C(c,k)/C(n,k): the chance that k runs drawn from the n all succeed."""
    return math.comb(c, k) / math.comb(n, k) if 0 < k <= n else float("nan")


def beta_gt(c1, n1, c2, n2, rng, draws=20000):
    """P(p1 > p2), p ~ Beta(1 + c, 1 + n - c)."""
    return sum(rng.betavariate(1 + c1, 1 + n1 - c1) > rng.betavariate(1 + c2, 1 + n2 - c2) for _ in range(draws)) / draws


def boot_ci(vals, rng, B=10000):
    """(mean, lo, hi): percentile bootstrap of the mean, 95%."""
    n = len(vals)
    if n == 0:
        return (float("nan"),) * 3
    ms = sorted(sum(rng.choices(vals, k=n)) / n for _ in range(B))
    return mean(vals), ms[int(0.025 * B)], ms[int(0.975 * B) - 1]


def pair_diffs(arm_rows, base_rows, f):
    """f(arm row) - f(default row) for rows of the same task and block; unpaired mean difference as one value if no pair exists."""
    key = lambda r: (r["task_id"], r["block"])
    b = {key(r): r for r in base_rows}
    d = [f(r) - f(b[key(r)]) for r in arm_rows if key(r) in b]
    paired = bool(d)
    if not d and arm_rows and base_rows:
        d = [f(r) - mean([f(x) for x in base_rows]) for r in arm_rows]
    return d, paired


def judge(lo, hi, band):
    if -band <= lo and hi <= band:
        return "equivalent"
    return "higher" if lo > band else "lower" if hi < -band else "unclear"


def compare(arm_rows, base_rows, rng, B):
    """The five paired comparisons against the default. Cost and time as log ratios, with the band on the ratio / minutes."""
    out = {"n": len(arm_rows), "n_default": len(base_rows)}
    specs = {
        "log_cost": (lambda r: math.log(max(r["cost"], 1e-6)), math.log(1 + BAND["cost"])),
        "log_time": (lambda r: math.log(max(r["wall_min"], 1e-6)), None),
        "log_time_adj": (lambda r: math.log(max(r["time_adj_min"], 1e-6)), None),
        "time_min": (lambda r: r["wall_min"], BAND["time_min"]),
        "time_adj_min": (lambda r: r["time_adj_min"], BAND["time_min"]),
        "hidden": (lambda r: r["hidden_frac"], BAND["hidden"]),
    }
    for name, (f, band) in specs.items():
        d, paired = pair_diffs(arm_rows, base_rows, f)
        m, lo, hi = boot_ci(d, rng, B)
        out[name] = {"mean": m, "lo": lo, "hi": hi, "paired": paired, "verdict": judge(lo, hi, band) if band and d else None}
        if name.startswith("log_"):
            out[name].update(ratio=math.exp(m), ratio_lo=math.exp(lo), ratio_hi=math.exp(hi))
    out["note"] = "n < 10: the bootstrap under-covers, read the interval as indicative" if min(len(arm_rows), len(base_rows)) < 10 else ""
    return out


def pb_effects(rows, metric, rng, B):
    """Main effect per factor: mean(alternative level) - mean(default level), bootstrap resampling runs within each design cell."""
    cells = defaultdict(list)
    for r in rows:
        lv = configs.pb_levels(r["arm"])
        if lv and r.get(metric) is not None:
            cells[r["arm"]].append(r[metric])
    if len(cells) < 8:
        return {}
    def eff(c):
        res = {}
        for j, (letter, (label, *_)) in enumerate(configs.FACTORS.items()):
            hi = [v for a, vs in c.items() if configs.pb_levels(a)[letter] == 1 for v in vs]
            lo = [v for a, vs in c.items() if configs.pb_levels(a)[letter] == -1 for v in vs]
            res[letter] = mean(hi) - mean(lo)
        return res
    point = eff(cells)
    draws = defaultdict(list)
    for _ in range(B):
        for k, v in eff({a: rng.choices(vs, k=len(vs)) for a, vs in cells.items()}).items():
            draws[k].append(v)
    return {k: {"label": configs.FACTORS[k][0], "effect": point[k], "lo": sorted(draws[k])[int(0.025 * B)], "hi": sorted(draws[k])[int(0.975 * B) - 1]} for k in point}


def dominance(by_arm, rng, M=2000):
    """P(arm is dominated): share of bootstrap draws in which another arm has lower-or-equal mean cost and higher-or-equal mean
    hidden_frac, strictly better in one."""
    arms = [a for a, rs in by_arm.items() if rs and all(r["hidden_frac"] is not None for r in rs)]
    dom = dict.fromkeys(arms, 0)
    for _ in range(M):
        pt = {}
        for a in arms:
            s = rng.choices(by_arm[a], k=len(by_arm[a]))
            pt[a] = (mean([r["cost"] for r in s]), mean([r["hidden_frac"] for r in s]))
        for a in arms:
            if any(b != a and pt[b][0] <= pt[a][0] and pt[b][1] >= pt[a][1] and pt[b] != pt[a] for b in arms):
                dom[a] += 1
    return {a: v / M for a, v in dom.items()}


def confusion(rows):
    """Verifier verdict against solved, per arm's verifier model; the false-pass cell is PASS with hidden_frac < 1."""
    out = defaultdict(lambda: {"pass_solved": 0, "pass_unsolved": 0, "fail_solved": 0, "fail_unsolved": 0, "none": 0})
    for r in rows:
        cfg = configs.ARMS.get(r["arm"])
        key = f"{cfg['roles']['verifier'][0]}-{cfg['roles']['verifier'][1]}" if cfg and cfg["harness"] == "factory" else r["arm"]
        v = r["verifier_verdict"]
        out[key]["none" if v is None else f"{v.lower()}_{'solved' if r['solved'] else 'unsolved'}"] += 1
        g = out["goal evaluator"]
        if r["goal_met"] is not None:
            g[f"{'pass' if r['goal_met'] else 'fail'}_{'solved' if r['solved'] else 'unsolved'}"] += 1
    return dict(out)


def failure_class(r):
    if r["infra"]:
        return "infrastructure"
    if r["timeout"]:
        return "timeout"
    if r["end_state"] in ("BLOCKED", "INCOMPLETE"):
        return r["end_state"]
    if r["integrity_violations"]:
        return "integrity violation"
    if r["regression"]:
        return "regression"
    if r["hidden_frac"] is not None and r["hidden_frac"] < 1:
        return "hidden fail"
    return "none" if r["end_state"] in ("SHIPPED", "HOLD") else "no end state"


def taxonomy(rows):
    out = defaultdict(lambda: defaultdict(int))
    for r in rows:
        out[r["arm"]][failure_class(r)] += 1
    return {a: dict(v) for a, v in out.items()}


def routing(rows):
    """Per policy: mean cost and quality, regret against the per-task oracle (cheapest solved run), escalation rate."""
    policies = ("always_cheap", "default", "always_strong", "cascade")
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(r)
    oracle = {t: min((r["cost"] for r in rs if r["solved"]), default=None) for t, rs in by_task.items()}
    out = {}
    for p in policies:
        rs = [r for r in rows if r["arm"] == p]
        if not rs:
            continue
        reg = [r["cost"] - oracle[r["task_id"]] for r in rs if oracle[r["task_id"]] is not None]
        out[p] = {"n": len(rs), "cost": mean([r["cost"] for r in rs]), "hidden": mean([r["hidden_frac"] for r in rs if r["hidden_frac"] is not None]),
                  "solved_rate": mean([float(r["solved"]) for r in rs]), "regret": mean(reg) if reg else None,
                  "escalation_rate": mean([float(r.get("tiers", 1) > 1) for r in rs]) if p == "cascade" else None}
    out["oracle"] = {"cost": mean([c for c in oracle.values() if c is not None]) if any(c is not None for c in oracle.values()) else None, "hidden": 1.0}
    return out


def summarize(rows, default, rng, B):
    by_arm = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)
    base = by_arm.get(default, [])
    dom = dominance(by_arm, rng, M=min(2000, B))
    out = {}
    for arm, rs in sorted(by_arm.items()):
        n, c = len(rs), sum(r["solved"] for r in rs)
        cost, tok = sum(r["cost"] for r in rs), sum(r["tokens"] for r in rs)
        out[arm] = {"n": n, "solved": c, "hidden_frac": mean([r["hidden_frac"] for r in rs if r["hidden_frac"] is not None]),
                    "cost": cost / n, "cost_per_solved": cost / c if c else None, "tokens_per_solved": tok / c if c else None,
                    "time_min": mean([r["wall_min"] for r in rs]), "time_adj_min": mean([r["time_adj_min"] for r in rs]),
                    "load": mean([r["load"] for r in rs]), "pass_k": [pass_k(c, n, k) for k in range(1, n + 1)],
                    "p_beats_default": beta_gt(c, n, sum(r["solved"] for r in base), len(base), rng) if base and arm != default else None,
                    "p_dominated": dom.get(arm), "drop": (dom.get(arm) or 0) > 0.8,
                    "goal_met_not_solved_rate": mean([float(bool(r["goal_met_not_solved"])) for r in rs]),
                    "verifier_false_pass_rate": mean([float(bool(r["verifier_false_pass"])) for r in rs if r["verifier_verdict"]]) if any(r["verifier_verdict"] for r in rs) else None,
                    "unverified_exit_rate": mean([float(bool(r["unverified_exit"])) for r in rs]),
                    "cache_hit": mean([r["cache_hit"] for r in rs if r["cache_hit"] is not None])}
        if base and arm != default:
            out[arm]["vs_default"] = compare(rs, base, rng, B)
    return out


def write_csv(path, rows, cols=None):
    cols = cols or sorted({k for r in rows for k in r})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})


def analyze(root, default="default", B=10000, seed=1):
    rng = random.Random(seed)
    rows = load_rows(root)
    parallel_load(rows)
    slope = load_adjust([r for r in rows if r["valid"] and not r["infra"]])
    for r in rows:
        r.setdefault("time_adj_min", r["wall_min"] * math.exp(-slope * (r["load"] - 1)))
    excluded = [{"run_id": r["run_id"], "arm": r["arm"], "reason": r["infra"] or r["invalid_reason"] or "not graded"} for r in rows if r["infra"] or not r["valid"]]
    use = collapse_cascades([r for r in rows if r["valid"] and not r["infra"] and r["hidden_frac"] is not None])
    summary = summarize(use, default, rng, B)
    effects = {m: pb_effects(use, m, rng, B) for m in ("hidden_frac", "cost", "wall_min")}
    res = {"summary": summary, "effects": effects, "confusion": confusion(use), "taxonomy": taxonomy(use + [r for r in rows if r["infra"]]),
           "routing": routing(use), "excluded": excluded, "load_slope_log_time_per_run": slope,
           "evaluator_models": sorted({m for r in rows for m in r["evaluator_models"]}), "default": default, "boot": B}
    res["evaluator_varies"] = len(res["evaluator_models"]) > 1
    root = Path(root)
    write_csv(root / "table.csv", rows)
    write_csv(root / "summary.csv", [{"arm": a, **{k: v for k, v in s.items() if k != "vs_default"}} for a, s in summary.items()])
    write_csv(root / "comparisons.csv", [{"arm": a, **{f"{m}_{k}": v for m, d in s["vs_default"].items() if isinstance(d, dict) for k, v in d.items()}, "note": s["vs_default"]["note"]}
                                         for a, s in summary.items() if "vs_default" in s])
    write_csv(root / "effects.csv", [{"metric": m, "factor": k, **v} for m, e in effects.items() for k, v in e.items()])
    (root / "analysis.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    return res, use


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--default", default="default")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    res, use = analyze(a.results, a.default, a.boot, a.seed)
    print(f"{len(use)} usable runs, {len(res['excluded'])} excluded, {len(res['summary'])} arms")
    for e in res["excluded"]:
        print(f"  excluded {e['run_id']} ({e['arm']}): {e['reason']}")
    if res["evaluator_varies"]:
        print(f"WARNING: more than one goal evaluator model across runs: {res['evaluator_models']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
