import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt

scene = S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())


def load_part(prefix):
    return cq.Shape.importBrep(str(scene / next(f for n, f in manifest["carriage"] if n.startswith(prefix))))


parts = {
    "P21": (load_part("P21_"), "#d58120"),
    "C28 P22": (cq.Shape.importBrep(str(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep")), "#168eb1"),
    "Cable": (load_part("Probe_Cable"), "#ba3b79"),
    "P01": (load_part("P01_"), "#4f5c69"),
}
frame = manifest["frames"]
gantry = cq.Shape.importBrep(str(scene / manifest["fixed"]["xgantry"]))
gantry = gantry.translate((0, frame["x_gantry_y_shift_to_dock_mm"], 0))
gantry = gantry.rotate((0, 0, 0), (0, 0, 1), 180).translate(
    (175, frame["world_y_offset_mm"], -frame["world_z_offset_mm"]))
parts["X gantry"] = (gantry, "#39452b")


def section(ax, normal, origin, columns, limits):
    for label, (body, color) in parts.items():
        algorithm = BRepAlgoAPI_Section(body.wrapped, gp_Pln(gp_Pnt(*origin), gp_Dir(*normal)), False)
        algorithm.Approximation(True)
        algorithm.Build()
        if not algorithm.IsDone():
            raise RuntimeError(f"Section failed: {label}, {origin}")
        shape = cq.Shape.cast(algorithm.Shape())
        first = True
        for edge in shape.Edges():
            points = np.array([edge.positionAt(float(t)).toTuple() for t in np.linspace(0, 1, 25)])
            ax.plot(points[:, columns[0]], points[:, columns[1]], color=color, lw=1.4,
                    label=label if first else None)
            first = False
    ax.set_xlim(*limits[:2])
    ax.set_ylim(*limits[2:])
    ax.set_aspect("equal")
    ax.grid(alpha=.2)


fig, axes = plt.subplots(2, 4, figsize=(18, 12))
for ax, z in zip(axes.flat[:6], (-47, -50, -54, -59, -63, -67)):
    section(ax, (0, 0, 1), (0, 0, z), (0, 1), (-10, 10, -42, -24))
    ax.set_title(f"XY at Z {z} mm")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
for ax, x in zip(axes.flat[6:], (0, 3.2)):
    section(ax, (1, 0, 0), (x, 0, 0), (1, 2), (-42, -23, -73, -43))
    ax.set_title(f"YZ at X {x} mm")
    ax.set_xlabel("Y")
    ax.set_ylabel("Z")
axes.flat[0].legend(loc="upper left")
fig.tight_layout()
fig.savefig(S / "c28_retainer_sections.png", dpi=150)
plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(15, 8))
for ax, x in zip(axes, (14.5, 18, 21.5)):
    section(ax, (1, 0, 0), (x, 0, 0), (1, 2), (8, 26, -68, -45))
    ax.set_title(f"Mount YZ at X {x} mm")
    ax.set_xlabel("Y")
    ax.set_ylabel("Z")
axes[0].legend()
fig.tight_layout()
fig.savefig(S / "c28_mount_sections.png", dpi=150)
print("Saved actual BREP sections for the retainer and paired mounts.")
