#!/usr/bin/env python3
"""Usage: python3 scripts/gallery.py <run-dir> [--open]

Purpose: build one local `gallery.html` that puts every direction in a run side by side, so a
person can compare them and write feedback without opening a single file by hand.

It is a plain file on disk. No server, no upload, no Claude artifact — `open gallery.html` and
it works offline, forever, including after this session ends.

What it reads: `<run-dir>/brief.md` for the header, then every `NN-<slug>/` folder in order (spec mode: every `<screen>/` folder with a `shots/`).
A direction's title comes from its `notes.md` first heading when there is one, else the folder
slug. Screenshots come from `shots/`; the HTML files are linked so a reviewer can open the real,
resizable thing rather than only a picture of it.

Feedback is a textarea per direction plus a copy button. The text never leaves the page — the
reviewer copies it back into the conversation. Persisting it would need a server, and a design
review that depends on a server is a design review that stops working next month.

Output sections:
  -#-#- GALLERY -#-#-   the file written, and what went into it
  -#-#- SUMMARY -#-#-   counts; exits non-zero when a run holds no direction
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

DIRECTION = re.compile(r"^\d\d-[a-z0-9-]+$")


def title_of(folder: Path) -> str:
    notes = folder / "notes.md"
    if notes.is_file():
        for line in notes.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return folder.name.split("-", 1)[-1].replace("-", " ").title()


def rationale_of(folder: Path) -> str:
    notes = folder / "notes.md"
    if not notes.is_file():
        return ""
    body = notes.read_text(encoding="utf-8")
    after = body.split("\n", 1)[-1].strip() if body.startswith("# ") else body.strip()
    return after.split("\n\n")[0].strip() if after else ""


def build(run: Path) -> tuple[str, int, int]:
    brief = ""
    if (run / "brief.md").is_file():
        brief = (run / "brief.md").read_text(encoding="utf-8").strip()

    dirs = sorted(d for d in run.iterdir() if d.is_dir() and DIRECTION.match(d.name))
    if not dirs:  # spec mode: one folder per screen, named for the screen, each with shots/
        dirs = sorted(d for d in run.iterdir() if d.is_dir() and (d / "shots").is_dir())
    cards, shots = [], 0
    for d in dirs:
        pages = sorted(p for p in d.glob("*.html"))
        imgs = sorted(p for p in (d / "shots").glob("*.png")) if (d / "shots").is_dir() else []
        shots += len(imgs)

        figures = "\n".join(
            f'<figure><img loading="lazy" src="{html.escape(str(p.relative_to(run)))}" '
            f'alt="{html.escape(p.stem)}"><figcaption>{html.escape(p.stem)}</figcaption></figure>'
            for p in imgs
        ) or '<p class="empty">No screenshot yet. Run scripts/render.sh.</p>'

        links = " · ".join(
            f'<a href="{html.escape(str(p.relative_to(run)))}" target="_blank">{html.escape(p.stem)}</a>'
            for p in pages
        ) or "—"

        why = rationale_of(d)
        cards.append(f"""<section class="dir" id="{html.escape(d.name)}">
  <header>
    <h2><span class="num">{html.escape(d.name.split('-')[0])}</span> {html.escape(title_of(d))}</h2>
    <p class="links">Open live: {links}</p>
    {f'<p class="why">{html.escape(why)}</p>' if why else ''}
  </header>
  <div class="shots">{figures}</div>
  <label class="fb">Feedback on {html.escape(title_of(d))}
    <textarea rows="4" data-dir="{html.escape(title_of(d))}"
      placeholder="What works, what does not, what to try next."></textarea>
  </label>
</section>""")

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Design directions — {html.escape(run.name)}</title>
<style>
  :root {{ --bg:#fbfbfa; --fg:#141413; --muted:#6b6a66; --line:#e4e3de; --card:#fff; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#141413; --fg:#f5f4ef; --muted:#a3a199; --line:#2c2b28; --card:#1c1b19; }}
  }}
  * {{ box-sizing:border-box }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
         font:16px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
  .wrap {{ max-width:1600px; margin:0 auto; padding:32px 24px 96px }}
  h1 {{ font-size:28px; margin:0 0 4px }}
  .sub {{ color:var(--muted); margin:0 0 24px }}
  .brief {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
            padding:16px 20px; margin:0 0 32px; white-space:pre-wrap; font-size:14px }}
  .dir {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
          padding:20px; margin:0 0 28px }}
  .dir h2 {{ font-size:20px; margin:0 0 6px; display:flex; align-items:baseline; gap:10px }}
  .num {{ color:var(--muted); font-variant-numeric:tabular-nums; font-size:14px }}
  .links, .why {{ margin:0 0 6px; font-size:14px; color:var(--muted) }}
  .why {{ color:var(--fg) }}
  a {{ color:inherit }}
  .shots {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
            align-items:start; margin:14px 0 }}
  figure {{ margin:0 }}
  img {{ width:100%; height:auto; display:block; border:1px solid var(--line); border-radius:10px }}
  figcaption {{ font-size:12px; color:var(--muted); margin-top:6px }}
  .empty {{ color:var(--muted); font-size:14px }}
  .fb {{ display:block; font-size:14px; color:var(--muted) }}
  textarea {{ display:block; width:100%; margin-top:6px; padding:10px; border-radius:10px;
              border:1px solid var(--line); background:var(--bg); color:var(--fg);
              font:inherit; font-size:14px; resize:vertical }}
  .bar {{ position:sticky; bottom:0; background:var(--bg); border-top:1px solid var(--line);
          padding:14px 24px; display:flex; gap:12px; align-items:center }}
  button {{ font:inherit; padding:9px 16px; border-radius:10px; border:1px solid var(--line);
            background:var(--card); color:var(--fg); cursor:pointer }}
  #said {{ color:var(--muted); font-size:14px }}
</style></head><body>
<div class="wrap">
  <h1>Design directions</h1>
  <p class="sub">{html.escape(run.name)} · {len(dirs)} directions · {shots} screenshots · generated by Codex, rendered locally</p>
  {f'<div class="brief">{html.escape(brief)}</div>' if brief else ''}
  {"".join(cards)}
</div>
<div class="bar">
  <button id="copy">Copy all feedback</button>
  <span id="said">Paste it back into the conversation to steer the next round.</span>
</div>
<script>
document.getElementById('copy').addEventListener('click', async () => {{
  const out = [...document.querySelectorAll('textarea')]
    .filter(t => t.value.trim())
    .map(t => '## ' + t.dataset.dir + '\\n' + t.value.trim()).join('\\n\\n');
  const said = document.getElementById('said');
  if (!out) {{ said.textContent = 'Nothing written yet.'; return; }}
  try {{ await navigator.clipboard.writeText(out); said.textContent = 'Copied. Paste it back.'; }}
  catch {{ said.textContent = 'Clipboard blocked — select the boxes and copy by hand.'; }}
}});
</script>
</body></html>"""
    return page, len(dirs), shots


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 1
    run = Path(args[0]).resolve()
    if not run.is_dir():
        print(f"✗ no such run folder: {run}", file=sys.stderr)
        return 1

    page, n_dirs, n_shots = build(run)
    out = run / "gallery.html"
    out.write_text(page, encoding="utf-8")

    print("-#-#- GALLERY -#-#-")
    print(f"- file: {out}")
    print(f"- directions: {n_dirs}")
    print(f"- screenshots: {n_shots}")

    if "--open" in sys.argv[1:] and sys.platform == "darwin":
        subprocess.run(["open", str(out)], check=False)
        print("- opened in the default browser")

    print("-#-#- SUMMARY -#-#-")
    if n_dirs == 0:
        print("- ✗ no NN-<slug>/ direction folders found", file=sys.stderr)
        return 1
    print(f"- ok, {n_dirs} directions in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
