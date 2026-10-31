"""Audit the print set's STL files: present, tracked, sealed, and matching their STEP or v26 body."""
import json
import os
import re
import subprocess
import sys

REPO = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner"
ACC = os.path.join(REPO, "cad", "SparkShift_Accessories_v26")
sys.path.insert(0, ACC)
os.chdir(ACC)
import trimesh  # noqa: E402
import cadquery as cq  # noqa: E402
import build_and_verify_accessories_v26 as acc  # noqa: E402
import r37_parts as P37  # noqa: E402
from build_print_colour_review import CORE_PRINTS  # noqa: E402

text = open(os.path.join(REPO, "PRINT_PARTS.md"), encoding="utf-8").read()
section = text[text.index("## Current print set"):text.index("### Hardware that differs from BOM.md")]
links = []
for line in section.splitlines():
    if not line.startswith("| ") or ".stl" not in line:
        continue
    part = line.split("|")[1].strip()
    for label, path in re.findall(r"\[([^\]]+)\]\(([^)]+\.stl)\)", line):
        links.append((part, label, path))
tracked = set(subprocess.run(["git", "-C", REPO, "ls-files"], capture_output=True, text=True).stdout.splitlines())
meta = json.loads((acc.WORK / "v26_meta.json").read_text())
v26 = {m["name"]: s for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))}
by_key = {}
for name, key in CORE_PRINTS.items():
    by_key.setdefault(key, []).append(name)


def step_twin(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    p = os.path.join(ACC, "step", stem + ".step")
    return p if os.path.exists(p) else None


def v26_body(stem):
    key = stem.split("_")[0]
    names = by_key.get(key, [])
    side = "left" if "Left" in stem else "right" if "Right" in stem else None
    for n in names:
        if side is None or n.endswith(side):
            return n, P37.shape(v26[n])
    return None, None


rows = []
for part, label, path in links:
    full = os.path.join(REPO, path.replace("/", os.sep))
    r = {"part": part, "file": path, "exists": os.path.exists(full), "tracked": path in tracked}
    if r["exists"]:
        m = trimesh.load(full, force="mesh")
        r.update(facets=len(m.faces), watertight=bool(m.is_watertight), winding=bool(m.is_winding_consistent),
                 bodies=len(m.split(only_watertight=False)), volume=round(float(m.volume), 2),
                 size=[round(float(v), 2) for v in m.extents], mb=round(os.path.getsize(full) / 1e6, 2))
        stem = os.path.splitext(os.path.basename(path))[0]
        twin = step_twin(path)
        if twin:
            s = cq.importers.importStep(twin).val()
            r["reference"] = "step/" + os.path.basename(twin)
        else:
            n, s = v26_body(stem)
            r["reference"] = f"v26 body {n}" if n else None
        if s is not None:
            bb = s.BoundingBox()
            sv = s.Volume()
            r["ref_volume"] = round(sv, 2)
            r["volume_diff_pct"] = round(100 * (r["volume"] - sv) / sv, 3)
            lo = [float(v) for v in m.bounds[0]]
            hi = [float(v) for v in m.bounds[1]]
            r["bounds_diff_mm"] = round(max(abs(lo[0] - bb.xmin), abs(lo[1] - bb.ymin), abs(lo[2] - bb.zmin),
                                            abs(hi[0] - bb.xmax), abs(hi[1] - bb.ymax), abs(hi[2] - bb.zmax)), 3)
    rows.append(r)
json.dump(rows, open(os.path.join(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files", "stl_audit.json"), "w"), indent=1)
for r in rows:
    flag = "OK " if r["exists"] and r["tracked"] and r.get("watertight") and r.get("winding") and r.get("bodies") == 1 \
        and abs(r.get("volume_diff_pct", 99)) < 0.5 and r.get("bounds_diff_mm", 99) < 0.1 else "!! "
    print(flag, f"{r['part'][:26]:26} {os.path.basename(r['file'])[:58]:58} trk={r['tracked']!s:5} wt={r.get('watertight')!s:5} "
          f"bodies={r.get('bodies')} facets={r.get('facets')} dV={r.get('volume_diff_pct')}% dB={r.get('bounds_diff_mm')} ref={r.get('reference')}")
print(len(rows), "links")
