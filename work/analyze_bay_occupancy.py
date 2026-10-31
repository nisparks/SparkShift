"""Occupancy around the C28 joint and the dry hotend bay: every carriage and Bambu part, by category."""
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
from matplotlib.patches import Patch

import r43_c28_mechanical as M
from audit_tool_owned_2510 import bounds

scene = S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
read = lambda f: cq.Shape.importBrep(str(scene / f))
window = (-14, 14, -47, -8, -76, -34)


def near(shape):
    b = bounds(shape)
    return b[1] > window[0] and b[0] < window[1] and b[3] > window[2] and b[2] < window[3] and \
        b[5] > window[4] and b[4] < window[5]


parts = []
clean22 = M.angled_p22(cq.Shape.importBrep(str(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep")))
for name, f in manifest["carriage"]:
    if name.startswith("P22_"):
        continue
    shape = read(f)
    if near(shape):
        cat = ("P21" if name.startswith("P21_") else "cable" if name.startswith("Probe_Cable") else
               "P20" if name.startswith("P20_") else "probe" if name.startswith(("Beacon", "P23", "R37_PROBE")) else
               "P01" if name.startswith("P01_") else "carriage")
        parts.append((name, cat, shape))
parts.append(("P22 clean C28", "P22", clean22))
for name, f in manifest["variants"]["Bambu"]["parts"]:
    shape = read(f)
    if near(shape):
        parts.append((f"Bambu {name}", "tool", shape))
COLORS = {"P21": "#f08a24", "P22": "#4f8fa8", "cable": "#c2408f", "P20": "#e6b35a", "probe": "#222222",
          "P01": "#7b5ea7", "carriage": "#3f9c4f", "tool": "#8d949b"}
print(json.dumps([(n, c, [round(v, 2) for v in bounds(s)]) for n, c, s in parts], indent=0))


def section(shape, axis, value, extent=300):
    normal = {"z": (0, 0, 1), "x": (1, 0, 0)}[axis]
    origin = {"z": (0, -20, value), "x": (value, -20, -60)}[axis]
    face = cq.Face.makePlane(extent, extent, cq.Vector(*origin), cq.Vector(*normal))
    tris = []
    for f in shape.intersect(face).Faces():
        vertices, triangles = f.tessellate(.02, .15)
        pts = [v.toTuple() for v in vertices]
        keep = {"z": (0, 1), "x": (1, 2)}[axis]
        tris += [[(pts[i][keep[0]], pts[i][keep[1]]) for i in t] for t in triangles]
    return tris


planes = [("x", x) for x in (0, 2.4, 3.6, 4.8, 6.0)] + [("z", z) for z in (-40, -45, -49.5, -52, -55, -58.5, -62, -66, -69.5, -71)]
fig, axes = plt.subplots(3, 5, figsize=(32, 20))
for ax, (axis, value) in zip(axes.flat, planes):
    for name, cat, shape in parts:
        tris = section(shape, axis, value)
        if tris:
            ax.add_collection(PolyCollection(tris, facecolors=COLORS[cat], edgecolors="none", alpha=.85))
    if axis == "x":
        ax.set_xlim(-47, -8); ax.set_ylim(-76, -34); ax.set_xlabel("Y"); ax.set_ylabel("Z")
    else:
        ax.set_xlim(-14, 14); ax.set_ylim(-47, -8); ax.set_xlabel("X"); ax.set_ylabel("Y")
    ax.set_aspect("equal"); ax.grid(alpha=.35); ax.set_title(f"{axis.upper()} = {value} mm", fontsize=15)
axes.flat[0].legend(handles=[Patch(color=c, label=k) for k, c in COLORS.items()], loc="upper left", fontsize=10)
fig.tight_layout()
out = S / "swept_feed" / "flow_tweak"
fig.savefig(out / "bay_occupancy.png", dpi=60)
print("done")
