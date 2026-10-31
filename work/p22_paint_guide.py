"""Where to paint support enforcers on revision 43's P22 (print-oriented), and why the window's sloped sides need none
(session scratch, for the user's Bambu Studio question)."""
import math

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

STL = (r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26\stl"
       r"\P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW_PRINT_ORIENTED.stl")
OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\fdm\p22_paint_guide.png"
CHEEK_Z, CHEEK_X = 15.9 + 45.4, (13.6, 22.6)
BOSS_X, BOSS_Z, BOSS_R, BORE_R = 15.8, -19.5 + 45.4, 3.05, 2.27

m = trimesh.load_mesh(STL)
lo, hi = m.bounds
xm = (lo[0] + hi[0]) / 2
n, c = m.face_normals, m.triangles_center
up = n[:, 2]
cheeks = (up < -0.999) & (np.abs(c[:, 2] - CHEEK_Z) < 0.05) & (np.abs(c[:, 0] - xm) > CHEEK_X[0]) & \
         (np.abs(c[:, 0] - xm) < CHEEK_X[1])
bosses, bores = np.zeros(len(n), bool), np.zeros(len(n), bool)
for s in (-1, 1):
    rx, rz = c[:, 0] - (xm + s * BOSS_X), c[:, 2] - BOSS_Z
    rad = np.hypot(rx, rz)
    radial = (n[:, 0] * rx + n[:, 2] * rz) / np.maximum(rad, 1e-9)
    bosses |= (np.abs(rad - BOSS_R) < 0.08) & (radial > 0.9) & (up < -0.5)
    bores |= (np.abs(rad - BORE_R) < 0.08) & (radial < -0.9)
window = (up > 0.3) & (np.abs(c[:, 0] - xm) > 2.0) & (np.abs(c[:, 0] - xm) < 11.6) & (c[:, 2] > 15.0) & (c[:, 2] < 30.5)
area = m.area_faces
print(f"cheeks {area[cheeks].sum():.1f} mm2, boss undersides {area[bosses].sum():.1f} mm2, bores {area[bores].sum():.1f} mm2,"
      f" window sides facing up {area[window].sum():.1f} mm2 (n_z {np.median(up[window]):.2f})")

col = np.tile([0.72, 0.74, 0.76], (len(n), 1))
col[window] = [0.35, 0.75, 0.35]
col[bores] = [0.2, 0.55, 0.95]
col[bosses] = [0.92, 0.12, 0.12]
col[cheeks] = [0.85, 0.2, 0.85]
light = np.array([0.25, 0.75, 0.6])
light /= np.linalg.norm(light)
shade = 0.55 + 0.45 * np.abs(n @ light)
col = np.clip(col * shade[:, None], 0, 1)

fig = plt.figure(figsize=(18, 7.4))
# (title, elevation, azimuth, crop box (x0, x1, y0, y1, z0, z1) or None)
views = (("Whole part, from the P23 side (your screenshot)", 14, 80, None),
         ("A boss (P23's rear ear), from below", -30, 60, (xm + 9.5, xm + 22.5, 2.0, hi[1], 18.0, 34.0)),
         ("The cheeks (top of the part), from below", -28, -62, (lo[0], hi[0], lo[1], hi[1], 47.0, hi[2])))
for i, (title, el, az, box) in enumerate(views):
    ax = fig.add_subplot(1, 3, i + 1, projection="3d")
    if box is None:
        tris, fc = m.vertices[m.faces], col
    else:
        # split the facets that reach into the box into pieces under 0.6 mm, so the crop has clean edges
        tv = m.vertices[m.faces]
        near = ((tv[:, :, 0].max(1) >= box[0]) & (tv[:, :, 0].min(1) <= box[1]) & (tv[:, :, 1].max(1) >= box[2]) &
                (tv[:, :, 1].min(1) <= box[3]) & (tv[:, :, 2].max(1) >= box[4]) & (tv[:, :, 2].min(1) <= box[5]))
        sv, sf, parent = trimesh.remesh.subdivide_to_size(m.vertices, m.faces[near], max_edge=0.6, max_iter=12,
                                                          return_index=True)
        sc = sv[sf].mean(axis=1)
        keep = ((sc[:, 0] >= box[0]) & (sc[:, 0] <= box[1]) & (sc[:, 1] >= box[2]) & (sc[:, 1] <= box[3]) &
                (sc[:, 2] >= box[4]) & (sc[:, 2] <= box[5]))
        tris, fc = sv[sf[keep]], col[np.nonzero(near)[0][parent[keep]]]
    ax.add_collection3d(Poly3DCollection(tris, facecolors=fc, edgecolors="none"))
    b = (lo[0], hi[0], lo[1], hi[1], 0.0, hi[2]) if box is None else box
    ax.set_xlim(b[0], b[1])
    ax.set_ylim(b[2], b[3])
    ax.set_zlim(b[4], b[5])
    ax.set_box_aspect((b[1] - b[0], b[3] - b[2], b[5] - b[4]))
    ax.view_init(elev=el, azim=az)
    ax.set_title(title, fontsize=12)
    if box is not None:
        ax.set_axis_off()
        continue
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("height (mm)")
fig.legend(handles=[Patch(color=[0.85, 0.2, 0.85], label="Paint (enforcer): the cheeks' bearing faces"),
                    Patch(color=[0.92, 0.12, 0.12], label="Paint (enforcer): the lower third of each boss (P23's rear ears)"),
                    Patch(color=[0.35, 0.75, 0.35], label="Window's sloping sides: face up, so they need no support"),
                    Patch(color=[0.2, 0.55, 0.95], label="Boss bores: keep support out (where 'Remove small overhangs' off puts it)")],
           loc="lower center", ncol=2, fontsize=11, frameon=False)
fig.suptitle("Revision 43's P22 on its back face: what to paint as support enforcers", fontsize=14)
fig.tight_layout(rect=(0, 0.09, 1, 0.95))
fig.savefig(OUT, dpi=90)
print(OUT)
