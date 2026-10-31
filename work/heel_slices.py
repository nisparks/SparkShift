"""Revision 43's right jet at its back end (the heel): plan slices zoomed on the foot's taper, the wall's thickening duct
face and the hotend slot, to see how far the round and its foot can run back without touching the slot."""
from pathlib import Path

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
HERE = Path(__file__).parent
m = trimesh.load_mesh(str(ROOT / "stl" / "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW.stl"))
ZS = (-73.5, -73.2, -72.8, -72.3, -71.6, -70.9, -70.4, -69.8)
fig, axes = plt.subplots(2, 4, figsize=(17, 10))
for ax, z in zip(axes.flat, ZS):
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
    for x, c in ((10.2, "tab:blue"), (11.6, "tab:blue"), (11.65, "tab:purple"), (12.6, "tab:blue")):
        ax.axvline(x, color=c, lw=0.6, ls=":")
    for y in (16.5, 16.688, 17.6):
        ax.axhline(y, color="tab:red", lw=0.6, ls=":")
    zr = -76.65 + (19.6 - np.array([12.0, 20.0])) * (7.75 / 7.4)
    yh = 19.6 - (z + 76.65) * (7.4 / 7.75)   # where revision 41's heel ramp crosses this height
    ax.axhline(yh, color="tab:green", lw=0.8, ls="--")
    ax.set_xlim(9.5, 14.0)
    ax.set_ylim(12.5, 19.0)
    ax.set_aspect("equal")
    ax.set_title(f"Z {z} (heel ramp at Y {yh:.2f}, green)")
fig.suptitle("R43 right jet, back end. Blue: X 10.2 slot face, 11.6 wall's duct face, 12.6 foot; purple: 11.65 "
             "(slot widens behind Y16.5); red: Y 16.5, 16.69 heel, 17.6", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.96))
out = HERE / "fusion_user_edit" / "heel_slices.png"
fig.savefig(out, dpi=72)
print(out)
