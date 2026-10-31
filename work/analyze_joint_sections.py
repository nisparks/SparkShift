"""Plan and side sections through the C28 joint: clean channel air vs the user post and the v4 receiver."""
import json
import os
import sys
from pathlib import Path

CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

import r43_c28_mechanical as M
import r43_swept_feed as F

scene = S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
read = lambda f: cq.Shape.importBrep(str(f))
carriage = {n: f for n, f in manifest["carriage"]}
old21 = read(scene / next(f for n, f in manifest["carriage"] if n.startswith("P21_")))
cable = read(scene / next(f for n, f in manifest["carriage"] if n.startswith("Probe_Cable")))
clean22 = M.angled_p22(read(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep"))
v4 = S / "swept_feed" / (sys.argv[1] if len(sys.argv) > 1 else "optC28_user_retainer")
user21 = read(v4 / "p21.brep")
v4p22 = read(v4 / "p22.brep")
corridor = F.main_channel_air()
air = cq.Shape.importBrep(str(S / "swept_feed" / "flow_tweak" / "clean_duct_air.brep"))

LAYERS = [
    ("clean channel air", air, "#9fd3ff"),
    ("clean P22", clean22, "#c9cdd2"),
    ("original P21", old21, "#f4c38b"),
    ("variant P22", v4p22, "#1b9db5"),
    ("user P21 (sealed)", user21, "#f08a24"),
    ("cable", cable, "#c2408f"),
]


def section(shape, axis, value, extent=200):
    if axis == "z":
        face = cq.Face.makePlane(extent, extent, cq.Vector(0, -20, value), cq.Vector(0, 0, 1))
    else:
        face = cq.Face.makePlane(extent, extent, cq.Vector(value, -20, -60), cq.Vector(1, 0, 0))
    cut = shape.intersect(face)
    tris = []
    for f in cut.Faces():
        vertices, triangles = f.tessellate(.02, .1)
        pts = [v.toTuple() for v in vertices]
        for t in triangles:
            p = [pts[i] for i in t]
            tris.append([(q[0], q[1]) if axis == "z" else (q[1], q[2]) for q in p])
    return tris, sum(f.Area() for f in cut.Faces())


planes = [("z", z) for z in (-50, -52, -54, -56, -58, -60, -62, -64, -66, -68)] + \
         [("x", x) for x in (0, 2.5, 3.6, 4.2, 5.0, 5.8)]
fig, axes = plt.subplots(4, 4, figsize=(24, 24))
rows = {}
for ax, (axis, value) in zip(axes.flat, planes):
    row = {}
    for label, shape, color in LAYERS:
        tris, area = section(shape, axis, value)
        row[label] = round(area, 2)
        if tris:
            alpha = .55 if label in ("clean P22", "original P21") else .8
            ax.add_collection(PolyCollection(tris, facecolors=color, edgecolors="none", alpha=alpha,
                                             label=label))
    rows[f"{axis}={value}"] = row
    if axis == "z":
        ax.set_xlim(-22, 22); ax.set_ylim(-46, -16); ax.set_xlabel("X"); ax.set_ylabel("Y")
    else:
        ax.set_xlim(-46, -16); ax.set_ylim(-72, -46); ax.set_xlabel("Y"); ax.set_ylabel("Z")
    ax.set_aspect("equal"); ax.grid(alpha=.3)
    ax.set_title(f"{axis.upper()} = {value} mm")
axes.flat[0].legend(loc="lower left", fontsize=8)
fig.tight_layout()
out = S / "swept_feed" / "flow_tweak"
out.mkdir(exist_ok=True)
fig.savefig(out / f"joint_sections_{v4.name}.png", dpi=80)
(out / f"joint_sections_{v4.name}.json").write_text(json.dumps(rows, indent=1))
print(json.dumps(rows, indent=1))
