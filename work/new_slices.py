"""The new P22 (review changes) at the places that had notches: the jet's back end (heel), its front end (front wall),
and the cable boss's nose with the rib. Plan slices, solid grey."""
from pathlib import Path

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
m = trimesh.load_mesh(str(HERE / "fusion_user_edit" / "new_p22.stl"))
VIEWS = [("back end (heel)", -72.8, (9.5, 14.0, 12.5, 19.0)), ("back end (heel)", -72.0, (9.5, 14.0, 12.5, 19.0)),
         ("back end (heel)", -71.0, (9.5, 14.0, 12.5, 19.0)), ("front end", -73.3, (9.5, 14.0, 23.0, 29.0)),
         ("front end", -72.6, (9.5, 14.0, 23.0, 29.0)), ("front end", -71.8, (9.5, 14.0, 23.0, 29.0)),
         ("rib and nose", -53.0, (-6.0, 6.0, -45.0, -33.0)), ("rib and nose", -60.0, (-6.0, 6.0, -45.0, -33.0)),
         ("rib and nose", -65.0, (-6.0, 6.0, -45.0, -33.0))]
fig, axes = plt.subplots(3, 3, figsize=(15, 15))
for ax, (title, z, (x0, x1, y0, y1)) in zip(axes.flat, VIEWS):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    p2, _ = s.to_2D(to_2D=np.eye(4))
    for poly in p2.polygons_full:
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, color="0.78", zorder=0)
        for h in poly.interiors:
            hx, hy = h.xy
            ax.fill(hx, hy, color="white", zorder=1)
    for d in s.discrete:
        ax.plot(d[:, 0], d[:, 1], "k", lw=0.8, zorder=2)
    if title.startswith("rib"):
        t = np.linspace(-np.pi / 2, 0.0, 60)
        for sx in (-1, 1):
            ax.plot(sx * (0.65 + 3 * np.cos(t)), -35.15 + 3 * np.sin(t), "r--", lw=0.8, zorder=3)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_title(f"{title}, Z {z}")
fig.suptitle("New P22: the right jet's round at its back and front ends, and the rib flaring into the cable boss "
             "(red dashes: the nose's r3 rounds)", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.97))
out = HERE / "fusion_user_edit" / "new_slices.png"
fig.savefig(out, dpi=70)
print(out)
