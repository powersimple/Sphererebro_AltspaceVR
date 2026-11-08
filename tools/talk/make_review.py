"""Writes review/REVIEW.md: what works, what doesn't, and every cue's screenshots in order (from review/cues and
review/motion, made by SphererebroTalkShots in Unity), with the per-cue counts from review/PERFORMANCE.md and the
clearance result from review/CLEARANCE.md. The judgement notes come from review/notes.json (written by hand during the run).
Run: <blender python> tools/talk/make_review.py
"""
import json, os, re, glob, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
R = os.path.join(REPO, "review")
show = json.load(open(os.path.join(REPO, "Assets", "_Sphererebro", "Config", "talk_show.json"), encoding="utf-8-sig"))
notes = json.load(open(os.path.join(R, "notes.json"), encoding="utf-8")) if os.path.exists(os.path.join(R, "notes.json")) else {}
perf = {}
if os.path.exists(os.path.join(R, "PERFORMANCE.md")):
    for line in open(os.path.join(R, "PERFORMANCE.md"), encoding="utf-8"):
        m = re.match(r"\| (\d+) \| (\S+) \| .* \| ([\d,]+) \| (\d+) \| (\d+) \| (.*) \|", line)
        if m: perf[m.group(2)] = (m.group(3), m.group(4), m.group(5))
clear = ""
if os.path.exists(os.path.join(R, "CLEARANCE.md")):
    for line in open(os.path.join(R, "CLEARANCE.md"), encoding="utf-8"):
        if line.startswith("Result:"): clear = line.strip()
out = ["# Talk review", "", f"Generated {time.strftime('%Y-%m-%d %H:%M')} by tools/talk/make_review.py.", ""]
out += ["## Summary", ""] + [f"- {s}" for s in notes.get("summary", [])] + [""]
out += ["## What works", ""] + [f"- {s}" for s in notes.get("works", [])] + [""]
out += ["## What doesn't (or is unverified)", ""] + [f"- {s}" for s in notes.get("doesnt", [])] + [""]
out += ["## Checks", "", f"- Clearance (3 m around every seat, every entrance and exit): {clear or 'not run'} (review/CLEARANCE.md)",
        f"- Show logic (XR Time Machine Show against a mock SDK; forward, back from every cue, late arrival, presenter-only, rehearsal): {notes.get('logic', 'see tools/harness/show_test.html')}",
        "- Per-cue triangles and draw calls: review/PERFORMANCE.md (Quest budget: < 300,000 triangles, < 150 draw calls).",
        "- Frame rate: not measurable without a headset; the browser harness's relative frame times are in review/HARNESS_FRAMES.md.", ""]
out += ["## Cue by cue", ""]
for i, c in enumerate(show["cues"], 1):
    cid = c["id"]
    out.append(f"### {i}. Cue {cid}: {c['name']}")
    p = perf.get(cid)
    if p: out.append(f"Talk triangles {p[0]}, draw calls {p[1]}, real-time lights {p[2]} (held pose).")
    if notes.get("cues", {}).get(cid): out.append(notes["cues"][cid])
    out.append("")
    for f in sorted(glob.glob(os.path.join(R, "cues", f"{i:02d}_{cid}*.png"))):
        out.append(f"![{os.path.basename(f)}](cues/{os.path.basename(f)})")
    for f in sorted(glob.glob(os.path.join(R, "motion", f"{i:02d}_{cid}_t*.png"))):
        if f.endswith("_wide.png"): continue
        out.append(f"![{os.path.basename(f)}](motion/{os.path.basename(f)})")
    out.append("")
open(os.path.join(R, "REVIEW.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("review/REVIEW.md written")
