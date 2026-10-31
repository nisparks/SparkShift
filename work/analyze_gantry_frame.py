"""X gantry and flying gantry in the carriage frame, sectioned with the duct, cable and bay."""
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
from audit_c28_mechanical_r43 import SOURCE
from audit_tool_owned_2510 import bounds
from build_inlet_screws_r40 import DOCK_NOZZLE_Y, GANTRY_CENTERS, REAR_LIMITS

manifest = json.loads((SOURCE / "manifest.json").read_text())
read = lambda p: cq.Shape.importBrep(str(SOURCE / p))
f = manifest["frames"]


def to_carriage(shape, center, dy=0.0):
    """Inverse of world(): world = rot180z(carriage) + (center, wy, wz); dy is the carriage's extra world Y move."""
    moved = shape.translate((-center, -(f["world_y_offset_mm"] + dy), -f["world_z_offset_mm"]))
    return moved.rotate((0, 0, 0), (0, 0, 1), 180)


box = M.box(-30, 30, -60, 10, -90, -20)
xg = to_carriage(read(manifest["fixed"]["xgantry"]).translate((0, f["x_gantry_y_shift_to_dock_mm"], 0)), 175).intersect(box)
fly = []
for rear in REAR_LIMITS:
    dy = rear - DOCK_NOZZLE_Y
    fly.append(to_carriage(read(manifest["fixed"]["flying"]), 175, dy).intersect(box))
print("x gantry (carriage frame, clipped) bounds:", [round(v, 2) for v in bounds(xg)] if xg.Solids() else None)
for rear, s in zip(REAR_LIMITS, fly):
    print("flying at rear", rear, [round(v, 2) for v in bounds(s)] if s.Solids() else None)
carriage = dict(manifest["carriage"])
p21 = read(next(v for k, v in carriage.items() if k.startswith("P21_")))
cable = read(next(v for k, v in carriage.items() if k.startswith("Probe_Cable")))
p22 = M.angled_p22(cq.Shape.importBrep(str(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep")))
layers = [("P22", p22, "#4f8fa8"), ("P21", p21, "#f08a24"), ("cable", cable, "#c2408f"),
          ("X gantry", xg, "#d62728")] + [(f"flying {r}", s, "#9467bd") for r, s in zip(REAR_LIMITS, fly)]


def section(shape, axis, value, extent=400):
    normal = {"z": (0, 0, 1), "x": (1, 0, 0)}[axis]
    origin = {"z": (0, -20, value), "x": (value, -20, -60)}[axis]
    face = cq.Face.makePlane(extent, extent, cq.Vector(*origin), cq.Vector(*normal))
    tris = []
    for fc in shape.intersect(face).Faces():
        vertices, triangles = fc.tessellate(.02, .15)
        pts = [v.toTuple() for v in vertices]
        keep = {"z": (0, 1), "x": (1, 2)}[axis]
        tris += [[(pts[i][keep[0]], pts[i][keep[1]]) for i in t] for t in triangles]
    return tris


planes = [("x", x) for x in (0, 2.4, 4.8, 7.5, 12)] + [("z", z) for z in (-38, -44, -48, -52, -56)]
fig, axes = plt.subplots(2, 5, figsize=(32, 14))
for ax, (axis, value) in zip(axes.flat, planes):
    for name, shape, color in layers:
        if not shape.Solids():
            continue
        tris = section(shape, axis, value)
        if tris:
            ax.add_collection(PolyCollection(tris, facecolors=color, edgecolors="none", alpha=.6))
    if axis == "x":
        ax.set_xlim(-50, 0); ax.set_ylim(-75, -25); ax.set_xlabel("Y"); ax.set_ylabel("Z")
    else:
        ax.set_xlim(-25, 25); ax.set_ylim(-50, 0); ax.set_xlabel("X"); ax.set_ylabel("Y")
    ax.set_aspect("equal"); ax.grid(alpha=.35); ax.set_title(f"{axis.upper()} = {value} mm", fontsize=15)
axes.flat[0].legend(handles=[Patch(color=c, label=n) for n, _, c in layers[:5]], loc="lower left")
fig.tight_layout()
fig.savefig(S / "swept_feed" / "flow_tweak" / "gantry_carriage_frame.png", dpi=60)
xg.exportBrep(str(S / "swept_feed" / "flow_tweak" / "xgantry_carriage_frame.brep"))
print("done")
