#!/usr/bin/env python3
"""Usage: plot.py <results dir> [--boot 10000]
Runs analyze.py, then writes the 11 plots as PNGs into <results dir>/plots/ and one self-contained report.html
(images embedded) beside them. Local only: nothing is published anywhere.
  01 cost vs hidden_frac    which arms are on the front (credible crosses, time as size)
  02 cost per solved task   what a working result costs
  03 per-role cost          where the money goes
  04 time ECDFs             tails for unattended runs
  05 pass^k                 reliability decay
  06 forest vs default      paired differences against the equivalence band
  07 screening effects      which factor moves what (Plackett-Burman)
  08 verifier confusion     false passes of the verifier and of the goal evaluator
  09 failure taxonomy       how runs fail
  10 routing                cheap / default / strong / cascade against the oracle
  11 cache hit vs cost      outliers that flag cache or version confounds
"""
import argparse
import base64
import html
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import analyze  # noqa: E402

NAMES = {}


def new(title, w=7, h=4.5):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_title(title, fontsize=10)
    return fig, ax


def done(fig, ax, path, empty=False):
    if empty:
        ax.text(0.5, 0.5, "no data yet", ha="center", va="center", transform=ax.transAxes, color="gray")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def by_arm(rows):
    d = defaultdict(list)
    for r in rows:
        d[r["arm"]].append(r)
    return d


def p01(res, rows, path):
    fig, ax = new("Cost vs quality (size = wall time, cross = 80% interval)")
    S = res["summary"]
    rng = __import__("random").Random(1)
    for arm, rs in by_arm(rows).items():
        c = [r["cost"] for r in rs]
        h = [r["hidden_frac"] for r in rs]
        cl, ch = sorted(c)[int(0.1 * len(c))], sorted(c)[min(len(c) - 1, int(0.9 * len(c)))]
        hl, hh = sorted(h)[int(0.1 * len(h))], sorted(h)[min(len(h) - 1, int(0.9 * len(h)))]
        x, y = S[arm]["cost"], S[arm]["hidden_frac"]
        colour = "tab:red" if arm == res["default"] else ("lightgray" if S[arm]["drop"] else "tab:blue")
        ax.errorbar(x, y, xerr=[[x - cl], [ch - x]], yerr=[[y - hl], [hh - y]], color=colour, alpha=0.5, lw=1)
        ax.scatter(x, y, s=30 + 8 * S[arm]["time_min"], color=colour, alpha=0.8)
        ax.annotate(arm, (x, y), fontsize=7, xytext=(4, 4), textcoords="offset points")
    front = sorted((S[a]["cost"], S[a]["hidden_frac"]) for a in S)
    best, line = -1, []
    for x, y in front:
        if y > best:
            best = y
            line.append((x, y))
    if line:
        ax.step(*zip(*line), where="post", color="black", lw=0.8)
    ax.set_xlabel("cost per run, USD")
    ax.set_ylabel("hidden_frac")
    done(fig, ax, path, not rows)


def p02(res, rows, path):
    fig, ax = new("Cost per solved task")
    S = res["summary"]
    arms = [a for a in S if S[a]["cost_per_solved"] is not None]
    ax.barh(arms, [S[a]["cost_per_solved"] for a in arms], color="tab:blue")
    for i, a in enumerate(arms):
        ax.text(S[a]["cost_per_solved"], i, f"  {S[a]['solved']}/{S[a]['n']}", va="center", fontsize=7)
    ax.set_xlabel("USD per solved task")
    done(fig, ax, path, not arms)


def p03(res, rows, path):
    fig, ax = new("Cost per role")
    roles = sorted({k for r in rows for k in r["cost_by_role"]})
    arms = list(by_arm(rows))
    left = [0.0] * len(arms)
    for role in roles:
        vals = [analyze.mean([r["cost_by_role"].get(role, 0.0) for r in by_arm(rows)[a]]) for a in arms]
        ax.barh(arms, vals, left=left, label=role)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_xlabel("mean USD per run")
    if roles:
        ax.legend(fontsize=6)
    done(fig, ax, path, not roles)


def p04(res, rows, path):
    fig, ax = new("Wall time ECDF")
    for arm, rs in by_arm(rows).items():
        t = sorted(r["wall_min"] for r in rs)
        ax.step(t, [(i + 1) / len(t) for i in range(len(t))], where="post", label=arm)
    ax.set_xlabel("minutes (raw)")
    ax.set_ylabel("share of runs finished")
    if rows:
        ax.legend(fontsize=6)
    done(fig, ax, path, not rows)


def p05(res, rows, path):
    fig, ax = new("pass^k")
    for arm, s in res["summary"].items():
        ax.plot(range(1, len(s["pass_k"]) + 1), s["pass_k"], marker="o", ms=3, label=arm)
    ax.set_xlabel("k")
    ax.set_ylabel("pass^k")
    ax.set_ylim(0, 1.02)
    if res["summary"]:
        ax.legend(fontsize=6)
    done(fig, ax, path, not res["summary"])


def p06(res, rows, path):
    fig, axes = plt.subplots(1, 3, figsize=(10, 4.5), sharey=True)
    arms = [a for a, s in res["summary"].items() if "vs_default" in s]
    specs = [("log_cost", "cost ratio", math.log(1.1)), ("time_min", "minutes", 5.0), ("hidden", "hidden_frac diff", 0.05)]
    for ax, (key, label, band) in zip(axes, specs):
        for i, a in enumerate(arms):
            d = res["summary"][a]["vs_default"][key]
            ax.errorbar(d["mean"], i, xerr=[[d["mean"] - d["lo"]], [d["hi"] - d["mean"]]], fmt="o", ms=3)
        ax.axvspan(-band, band, color="green", alpha=0.12)
        ax.axvline(0, color="black", lw=0.5)
        ax.set_title(label + (" (log)" if key == "log_cost" else ""), fontsize=9)
    axes[0].set_yticks(range(len(arms)), arms, fontsize=7)
    fig.suptitle(f"Paired difference to {res['default']}, 95% bootstrap, green = equivalence band", fontsize=10)
    done(fig, axes[0], path, not arms)


def p07(res, rows, path):
    fig, axes = plt.subplots(1, 3, figsize=(10, 4))
    for ax, m in zip(axes, ("hidden_frac", "cost", "wall_min")):
        e = sorted(res["effects"].get(m, {}).items(), key=lambda kv: abs(kv[1]["effect"]))
        for i, (k, v) in enumerate(e):
            ax.errorbar(v["effect"], i, xerr=[[v["effect"] - v["lo"]], [v["hi"] - v["effect"]]], fmt="o", ms=3)
        ax.set_yticks(range(len(e)), [f"{k} {v['label']}" for k, v in e], fontsize=7)
        ax.axvline(0, color="black", lw=0.5)
        ax.set_title(m, fontsize=9)
    fig.suptitle("Plackett-Burman main effects (alternative minus default level)", fontsize=10)
    done(fig, axes[0], path, not any(res["effects"].values()))


def p08(res, rows, path):
    c = res["confusion"]
    fig, axes = plt.subplots(1, max(1, len(c)), figsize=(3.2 * max(1, len(c)), 3.4), squeeze=False)
    for ax, (name, m) in zip(axes[0], c.items()):
        grid = [[m["pass_solved"], m["pass_unsolved"]], [m["fail_solved"], m["fail_unsolved"]]]
        ax.imshow(grid, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, grid[i][j], ha="center", va="center")
        ax.set_xticks([0, 1], ["solved", "unsolved"], fontsize=7)
        ax.set_yticks([0, 1], ["PASS", "FAIL"], fontsize=7)
        pa = m["pass_solved"] + m["pass_unsolved"]
        ax.set_title(f"{name}\nfalse-pass {m['pass_unsolved']}/{pa}" if pa else name, fontsize=8)
    done(fig, axes[0][0], path, not c)


def p09(res, rows, path):
    fig, ax = new("Failure taxonomy")
    cats = sorted({k for v in res["taxonomy"].values() for k in v})
    arms = list(res["taxonomy"])
    left = [0] * len(arms)
    for cat in cats:
        vals = [res["taxonomy"][a].get(cat, 0) for a in arms]
        ax.barh(arms, vals, left=left, label=cat)
        left = [l + v for l, v in zip(left, vals)]
    if cats:
        ax.legend(fontsize=6)
    done(fig, ax, path, not cats)


def p10(res, rows, path):
    r = res["routing"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
    for name, v in r.items():
        if v.get("cost") is not None:
            a1.scatter(v["cost"], v["hidden"], label=name)
    a1.set_xlabel("mean cost, USD")
    a1.set_ylabel("hidden_frac")
    if a1.get_legend_handles_labels()[0]:
        a1.legend(fontsize=7)
    pol = [p for p, v in r.items() if p != "oracle" and v.get("regret") is not None]
    a2.bar(pol, [r[p]["regret"] for p in pol])
    a2.set_title("regret in USD against the per-task oracle", fontsize=8)
    a1.set_title("policies", fontsize=9)
    done(fig, a1, path, len(r) <= 1)


def p11(res, rows, path):
    fig, ax = new("Cache hit ratio vs cost")
    pts = [(r["cache_hit"], r["cost"], r["arm"]) for r in rows if r["cache_hit"] is not None]
    for x, y, a in pts:
        ax.scatter(x, y, s=12)
    ax.set_xlabel("cache hit ratio")
    ax.set_ylabel("cost, USD")
    done(fig, ax, path, not pts)


PLOTS = [("01_pareto", p01), ("02_cost_per_solved", p02), ("03_role_cost", p03), ("04_time_ecdf", p04), ("05_pass_k", p05), ("06_forest", p06),
         ("07_screening", p07), ("08_verifier_confusion", p08), ("09_failure_taxonomy", p09), ("10_routing", p10), ("11_cache_vs_cost", p11)]


def report(res, files, path):
    def f(x, nd=2):
        return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"
    rows = "".join(
        f"<tr><td>{html.escape(a)}</td><td>{s['n']}</td><td>{f(s['hidden_frac'])}</td><td>{s['solved']}</td><td>{f(s['cost'])}</td><td>{f(s['cost_per_solved'])}</td>"
        f"<td>{f(s['time_min'], 1)} / {f(s['time_adj_min'], 1)}</td><td>{f(s['p_beats_default'])}</td><td>{f(s['p_dominated'])}</td></tr>"
        for a, s in res["summary"].items())
    imgs = "".join(f"<h3>{n}</h3><img style='max-width:100%' src='data:image/png;base64,{base64.b64encode(Path(p).read_bytes()).decode()}'>" for n, p in files)
    warn = f"<p><b>Goal evaluator models differ across runs: {res['evaluator_models']}</b></p>" if res["evaluator_varies"] else ""
    ex = "".join(f"<li>{html.escape(e['run_id'])}: {html.escape(str(e['reason']))}</li>" for e in res["excluded"])
    Path(path).write_text(
        "<!doctype html><meta charset=utf-8><title>factory eval</title><body style='font:14px system-ui;max-width:960px;margin:1em auto'>"
        f"<h1>Factory eval</h1>{warn}<table border=1 cellpadding=4 style='border-collapse:collapse'><tr><th>arm</th><th>n</th><th>hidden_frac</th><th>solved</th>"
        "<th>cost</th><th>cost / solved</th><th>min raw / load-adj</th><th>P(beats default)</th><th>P(dominated)</th></tr>"
        f"{rows}</table><p>Excluded runs (infrastructure or invalid goal check): {len(res['excluded'])}</p><ul>{ex}</ul>{imgs}", encoding="utf-8")


def make_all(root, boot=10000):
    res, use = analyze.analyze(root, B=boot)
    out = Path(root) / "plots"
    out.mkdir(exist_ok=True)
    files = []
    for name, fn in PLOTS:
        p = out / f"{name}.png"
        fn(res, use, p)
        files.append((name, p))
    report(res, files, Path(root) / "report.html")
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args(argv)
    files = make_all(a.results, a.boot)
    print(f"{len(files)} plots and report.html in {a.results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
