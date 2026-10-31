"""Plan slices through the left jet's wall bottom (the bell-mouth round and its foot), revision 43 and the user's edit,
to see where the round starts and stops."""
from pathlib import Path

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
HERE = Path(__file__).parent
MESHES = {"R43": trimesh.load_mesh(str(ROOT / "stl" / "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW.stl")),
          "user": trimesh.load_mesh(str(HERE / "fusion_user_edit" / "user_p22_local.stl"))}
ZS = (-73.45, -73.0, -72.5, -71.8, -71.0, -70.4)
fig, axes = plt.subplots(2, len(ZS), figsize=(4 * len(ZS), 9.5), sharex=True, sharey=True)
for row, (tag, m) in enumerate(MESHES.items()):
    for ax, z in zip(axes[row], ZS):
        s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if s is not None:
            p2, T = s.to_2D(to_2D=np.eye(4))
            for poly in p2.polygons_full:
                xs, ys = poly.exterior.xy
                ax.fill(xs, ys, color="0.78", zorder=0)
                for h in poly.interiors:
                    hx, hy = h.xy
                    ax.fill(hx, hy, color="white", zorder=1)
            for d in s.discrete:
                ax.plot(d[:, 0], d[:, 1], color="k", lw=0.7, zorder=2)
        for x in (-10.2, -11.6, -12.6):
            ax.axvline(x, color="tab:blue", lw=0.5, ls=":")
        for y in (16.688, 17.6, 26.2, 27.88):
            ax.axhline(y, color="tab:red", lw=0.5, ls=":")
        ax.set_xlim(-15.5, -8.5)
        ax.set_ylim(13.5, 30.0)
        ax.set_aspect("equal")
        ax.set_title(f"{tag}: Z {z}")
fig.suptitle("Left jet, plan slices (grey: P22). Blue: X -10.2 slot face, -11.6 wall's duct face, -12.6 foot. "
             "Red: Y 16.69 heel, 17.6, 26.2 round's end, 27.88 front wall", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.96))
out = HERE / "fusion_user_edit" / "jet_slices.png"
fig.savefig(out, dpi=75)
print(out)
