"""Build the faded-foot study, check it, slice the jet's ends, and write its BREP for the CFD (session scratch)."""
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import os  # noqa: E402

os.chdir(CAD)
import cadquery as cq  # noqa: E402
import matplotlib  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import r43_parts as R  # noqa: E402

HERE = Path(__file__).parent
s = R.review_fade_study()
full = R.p22()
print("fade study: valid", s.isValid(), "solids", len(s.Solids()), "volume", round(s.Volume(), 2), "faces", len(s.Faces()),
      "| full", round(full.Volume(), 2))
s.exportBrep(str(HERE / "cfd" / "p22_r43_revfade.brep"))
stl = HERE / "fusion_user_edit" / "fade_p22.stl"
cq.exporters.export(cq.Workplane().add(s), str(stl), tolerance=0.01, angularTolerance=0.08)
cq.exporters.export(cq.Workplane().add(s), str(HERE / "fusion_user_edit" / "fade_p22.step"))
m = trimesh.load_mesh(str(stl))
fig, axes = plt.subplots(2, 4, figsize=(17, 10))
for ax, z in zip(axes.flat, (-73.3, -72.8, -72.2, -71.6, -71.0, -70.6, -70.3, -73.45)):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    p2, _ = sec.to_2D(to_2D=np.eye(4))
    for poly in p2.polygons_full:
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, color="0.78", zorder=0)
        for h in poly.interiors:
            hx, hy = h.xy
            ax.fill(hx, hy, color="white", zorder=1)
    for d in sec.discrete:
        ax.plot(d[:, 0], d[:, 1], "k", lw=0.8, zorder=2)
    ax.set_xlim(9.5, 13.5)
    ax.set_ylim(13.0, 29.0)
    ax.set_aspect("equal")
    ax.set_title(f"right jet, Z {z}")
fig.suptitle("Faded-foot study: plan slices through the right jet's wall bottom (grey solid)")
fig.tight_layout()
fig.savefig(HERE / "fusion_user_edit" / "fade_slices.png", dpi=70)
print("ok")
