"""Render P22 in its print orientation (back face down) with overhangs coloured, plus sections (session scratch)."""
import sys, os, math
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\fdm")
m = trimesh.load_mesh(str(OUT / "p22.stl"))
up = np.array([0.0, 1.0, 0.0])
N, A, C = m.face_normals, m.area_faces, m.triangles_center
h = C @ up
bed = (N @ up < -0.999) & (h - h.min() < 0.02)
down30 = (N @ up < -math.sin(math.radians(60))) & ~bed
down45 = (N @ up < -math.sin(math.radians(45))) & ~bed & ~down30
idx = np.nonzero(down30)[0]
hit = np.zeros(len(N), bool)
hit[idx] = m.ray.intersects_any(C[idx] - up * 0.02, np.tile(-up, (len(idx), 1)))
light = np.array([0.4, -0.5, 0.75]); light /= np.linalg.norm(light)


def colours():
    shade = 0.55 + 0.45 * np.clip(N @ light, 0, 1)
    base = np.tile([0.62, 0.78, 0.76], (len(N), 1))
    base[down45] = [0.98, 0.80, 0.25]
    base[down30 & ~hit] = [0.95, 0.45, 0.10]
    base[down30 & hit] = [0.85, 0.10, 0.15]
    base[bed] = [0.25, 0.35, 0.85]
    return np.clip(base * shade[:, None], 0, 1)


def view(ax, elev, azim, title):
    # print coordinates: X'=x, Y'=-z, Z'=y (rotate +90 about X), so 'up' is Z'
    v = m.vertices
    P = np.stack([v[:, 0], -v[:, 2], v[:, 1] + 45.4], 1)
    tris = P[m.faces]
    pc = Poly3DCollection(tris, facecolors=colours(), edgecolors="none", linewidths=0)
    ax.add_collection3d(pc)
    ax.set_xlim(-25, 25); ax.set_ylim(45, 80); ax.set_zlim(0, 76)
    ax.set_box_aspect((50, 35, 76))
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("X"); ax.set_ylabel("Y' (= -Z asm)"); ax.set_zlabel("print height")


fig = plt.figure(figsize=(22, 13))
for i, (el, az, t) in enumerate(((15, -60, "front-left, from slightly above"), (15, 120, "back-right"),
                                 (-25, -60, "from below (front-left)"), (-25, 120, "from below (back-right)"))):
    ax = fig.add_subplot(1, 4, i + 1, projection="3d")
    view(ax, el, az, t)
fig.suptitle("P22 (revision 43) on its back face. Red: overhang < 30 deg over the part (supports can't reach from the plate); "
             "orange: < 30 deg reachable from the plate; yellow: 30-45 deg; blue: on the plate", fontsize=12)
fig.tight_layout()
fig.savefig(OUT / "p22_overhangs_current.png", dpi=80)

# sections (assembly coordinates)
fig, axs = plt.subplots(2, 3, figsize=(22, 12))
for ax, (axis, at) in zip(axs.ravel(), (("x", 0.0), ("x", 17.0), ("x", 12.0), ("z", -64.0), ("z", -55.0), ("y", -5.0))):
    normal = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis]
    origin = [0, 0, 0]; origin["xyz".index(axis)] = at
    sec = m.section(plane_origin=origin, plane_normal=normal)
    if sec is None:
        continue
    pl, _ = sec.to_planar(to_2D=None) if False else (None, None)
    hv = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    for e in sec.entities:
        pts = sec.vertices[e.points]
        ax.plot(pts[:, hv[0]], pts[:, hv[1]], "k-", lw=0.8)
    ax.set_aspect("equal"); ax.grid(True, alpha=0.3)
    ax.set_title(f"section {axis} = {at} (assembly coordinates; print 'up' is +Y)")
    ax.set_xlabel("XYZ"[hv[0]]); ax.set_ylabel("XYZ"[hv[1]])
fig.tight_layout()
fig.savefig(OUT / "p22_sections.png", dpi=70)
print("done")
