"""Plan slices around the cable boss's nose and the socket's front edge (user's edit and R43), where the user's first
screenshot has red marks (about X +-3.4, Y -36.4..-34.7)."""
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
ZS = (-51.2, -51.6, -53.0, -56.0, -60.0, -64.0)
fig, axes = plt.subplots(2, len(ZS), figsize=(4 * len(ZS), 8.5), sharex=True, sharey=True)
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
        for x in (-3.4, 3.4):
            ax.axvline(x, color="tab:red", lw=0.5, ls=":")
        for y in (-36.4, -34.7):
            ax.axhline(y, color="tab:red", lw=0.5, ls=":")
        ax.set_xlim(-10, 10)
        ax.set_ylim(-46, -26)
        ax.set_aspect("equal")
        ax.set_title(f"{tag}: Z {z}")
fig.suptitle("Cable boss and socket front, plan slices (grey: P22); red dots: where the screenshot's red marks are",
             fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.95))
out = HERE / "fusion_user_edit" / "boss_slices.png"
fig.savefig(out, dpi=75)
print(out)
