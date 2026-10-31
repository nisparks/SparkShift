"""Clean-C28 joint sections only: P22 spine, P21 boss/sleeve, cable channel and duct air."""
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
old21 = read(scene / next(f for n, f in manifest["carriage"] if n.startswith("P21_")))
cable = read(scene / next(f for n, f in manifest["carriage"] if n.startswith("Probe_Cable")))
clean22 = M.angled_p22(read(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep"))
user = read(S / "swept_feed" / "userP21_20261030_193918" / "p21.brep")
post = user.cut(old21)
air = F.main_channel_air().cut(clean22).cut(old21)
out = S / "swept_feed" / "flow_tweak"
for name, body in (("clean22", clean22), ("old21", old21), ("cable", cable), ("air", air), ("post", post)):
    body.exportBrep(str(out / f"ref_{name}.brep"))

LAYERS = [("clean duct air", air, "#9fd3ff", .9), ("clean P22", clean22, "#4f8fa8", .75),
          ("original P21", old21, "#f08a24", .75), ("user post (added)", post, "#ffd23f", .45),
          ("cable", cable, "#c2408f", .9)]


def section(shape, axis, value, extent=200):
    normal = {"z": (0, 0, 1), "x": (1, 0, 0), "y": (0, 1, 0)}[axis]
    origin = {"z": (0, -20, value), "x": (value, -20, -60), "y": (0, value, -60)}[axis]
    face = cq.Face.makePlane(extent, extent, cq.Vector(*origin), cq.Vector(*normal))
    tris = []
    for f in shape.intersect(face).Faces():
        vertices, triangles = f.tessellate(.01, .1)
        pts = [v.toTuple() for v in vertices]
        keep = {"z": (0, 1), "x": (1, 2), "y": (0, 2)}[axis]
        tris += [[(pts[i][keep[0]], pts[i][keep[1]]) for i in t] for t in triangles]
    return tris


planes = [("z", z) for z in (-49.5, -50.5, -51.2, -52.0, -53.0, -54.5, -56.5, -59, -62, -64.5, -66.5, -68.5)] + \
         [("x", x) for x in (0, 1.2, 2.2, 3.0, 3.5, 4.0, 4.6, 5.5)] + [("y", y) for y in (-37, -35, -33, -30, -27, -24)]
fig, axes = plt.subplots(6, 5, figsize=(30, 33))
for ax, (axis, value) in zip(axes.flat, planes):
    for label, shape, color, alpha in LAYERS:
        tris = section(shape, axis, value)
        if tris:
            ax.add_collection(PolyCollection(tris, facecolors=color, edgecolors="none", alpha=alpha, label=label))
    if axis == "z":
        ax.set_xlim(-10, 10); ax.set_ylim(-46, -17); ax.set_xlabel("X"); ax.set_ylabel("Y")
    elif axis == "x":
        ax.set_xlim(-46, -15); ax.set_ylim(-71, -45); ax.set_xlabel("Y"); ax.set_ylabel("Z")
    else:
        ax.set_xlim(-12, 12); ax.set_ylim(-71, -45); ax.set_xlabel("X"); ax.set_ylabel("Z")
    ax.set_aspect("equal"); ax.grid(alpha=.35); ax.set_title(f"{axis.upper()} = {value} mm", fontsize=15)
for ax in list(axes.flat)[len(planes):]:
    ax.axis("off")
axes.flat[0].legend(loc="upper left", fontsize=10)
fig.tight_layout()
fig.savefig(out / "joint_sections_clean.png", dpi=62)
print("done")
