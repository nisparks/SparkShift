"""P22 print-oriented, from roughly the user's Bambu Studio camera, coloured by how each facet faces (session scratch)."""
import math
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

m = trimesh.load_mesh(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26\stl\P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW_PRINT_ORIENTED.stl")
lo, hi = m.bounds
print("bounds", np.round(m.bounds, 2).tolist())
n, c = m.face_normals, m.triangles_center
up = n[:, 2]
bed = (up < -0.999) & (c[:, 2] < 0.02)
col = np.tile([0.45, 0.62, 0.62], (len(n), 1))            # vertical walls: teal-grey
col[up > 0.1] = [0.55, 0.80, 0.45]                         # faces up: green (prints on what's below)
col[(up < -0.1) & (up >= -math.sin(math.radians(45)))] = [0.85, 0.85, 0.55]   # down, steeper than 45: pale (fine)
col[(up < -math.sin(math.radians(45))) & (up >= -math.sin(math.radians(60)))] = [0.98, 0.78, 0.2]  # 30-45: yellow
col[(up < -math.sin(math.radians(60))) & ~bed] = [0.9, 0.15, 0.15]  # flatter than 30: red (needs support)
col[bed] = [0.25, 0.35, 0.85]
light = np.array([0.3, 0.6, 0.75]); light /= np.linalg.norm(light)
col = np.clip(col * (0.6 + 0.4 * np.clip(n @ light, 0, 1))[:, None], 0, 1)
# the user's frame: the bosses' face toward the camera; P22 is centred on the plate
xm, ym = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
bosses = [(xm + s * 15.8, None) for s in (-1, 1)]
fig = plt.figure(figsize=(18, 10))
for i, (el, az) in enumerate(((28, 55), (28, 75), (12, 90))):
    ax = fig.add_subplot(1, 3, i + 1, projection="3d")
    ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolors=col, edgecolors="none"))
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(0, hi[2])
    ax.set_box_aspect(hi - [lo[0], lo[1], 0])
    ax.view_init(elev=el, azim=az)
    ax.set_title(f"elev {el}, azim {az}")
fig.suptitle("P22 as printed. Red: flatter than 30 deg facing down (needs support); yellow: 30-45 deg down; pale: steeper "
             "than 45 down; green: faces up; teal: vertical; blue: on the plate", fontsize=11)
fig.tight_layout()
out = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\fdm\p22_user_view.png"
fig.savefig(out, dpi=80)
print(out)
# what faces are near the window's sloped sides and the bosses, by class
def report(name, mask):
    a = m.area_faces[mask]
    cls = {"up": (up > 0.1), "vertical": (np.abs(up) <= 0.1), "down>45": (up < -0.1) & (up >= -0.7071),
           "down30-45": (up < -0.7071) & (up >= -0.866), "down<30": (up < -0.866) & ~bed}
    print(name, {k: round(float(m.area_faces[mask & v].sum()), 1) for k, v in cls.items()})
# window sloped sides: in print, X between 2.2 and 11.5 from centre, height 15.5..30.5, inside the part's Y' extent
win = (np.abs(c[:, 0] - xm) > 2.0) & (np.abs(c[:, 0] - xm) < 11.6) & (c[:, 2] > 15.0) & (c[:, 2] < 30.5)
report("window region (|x|2-11.6, z15-30.5)", win)
yb = c[:, 1].max()
boss = (np.abs(np.abs(c[:, 0] - xm) - 15.8) < 3.2) & (np.abs(c[:, 2] - (45.4 - 19.5)) < 3.2)
report("boss region", boss)
print("boss facets y range", np.round([c[boss, 1].min(), c[boss, 1].max()], 2), "part y range", np.round([lo[1], hi[1]], 2))
