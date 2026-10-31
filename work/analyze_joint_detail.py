"""Fine sections of the P21/P22 joint at the cable boss: clean parts, user post, cable and duct air."""
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

out = S / "swept_feed" / "flow_tweak"
read = lambda n: cq.Shape.importBrep(str(out / f"ref_{n}.brep"))
layers = [("air", read("air"), "#9fd3ff", .9), ("P22", read("clean22"), "#4f8fa8", .8),
          ("P21", read("old21"), "#f08a24", .8), ("post", read("post"), "#ffd23f", .45),
          ("cable", read("cable"), "#c2408f", .9)]


def section(shape, axis, value, extent=200):
    normal = {"z": (0, 0, 1), "x": (1, 0, 0)}[axis]
    origin = {"z": (0, -20, value), "x": (value, -20, -60)}[axis]
    face = cq.Face.makePlane(extent, extent, cq.Vector(*origin), cq.Vector(*normal))
    tris = []
    for f in shape.intersect(face).Faces():
        vertices, triangles = f.tessellate(.005, .05)
        pts = [v.toTuple() for v in vertices]
        keep = {"z": (0, 1), "x": (1, 2)}[axis]
        tris += [[(pts[i][keep[0]], pts[i][keep[1]]) for i in t] for t in triangles]
    return tris


planes = [("z", z) for z in (-48.8, -49.3, -49.8, -50.4, -51.0, -51.6, -52.4, -53.5)] + \
         [("x", x) for x in (0.0, 1.0, 2.1, 2.7, 3.3, 3.7, 4.1, 4.6)]
fig, axes = plt.subplots(4, 4, figsize=(28, 28))
for ax, (axis, value) in zip(axes.flat, planes):
    for label, shape, color, alpha in layers:
        tris = section(shape, axis, value)
        if tris:
            ax.add_collection(PolyCollection(tris, facecolors=color, edgecolors="none", alpha=alpha, label=label))
    if axis == "z":
        ax.set_xlim(-6.5, 6.5); ax.set_ylim(-41, -30); ax.set_xlabel("X"); ax.set_ylabel("Y")
        ax.set_xticks(range(-6, 7)); ax.set_yticks(range(-41, -29))
    else:
        ax.set_xlim(-41, -28); ax.set_ylim(-60, -46); ax.set_xlabel("Y"); ax.set_ylabel("Z")
        ax.set_xticks(range(-41, -27)); ax.set_yticks(range(-60, -45))
    ax.set_aspect("equal"); ax.grid(alpha=.4); ax.set_title(f"{axis.upper()} = {value} mm", fontsize=15)
axes.flat[0].legend(loc="lower left", fontsize=10)
fig.tight_layout()
fig.savefig(out / "joint_detail.png", dpi=58)
print("done")
