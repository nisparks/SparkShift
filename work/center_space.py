"""Centre-feed feasibility (session scratch): P22's own air passages over and behind the probe, and what else is there.

Sections of the revision-43 scene (P22, P23 + Beacon, cable route, P01, cores) and both tools over Y-46..32, Z-80..-46.
P22's internal air shows as white holes inside the teal section."""
import json, os, sys
CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, CAD); os.chdir(CAD)
import cadquery as cq
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
import build_and_verify_accessories_v26 as acc
from audit_tool_owned_2510 import bounds

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\center_feed"
os.makedirs(OUT, exist_ok=True)
SCENE = acc.WORK / "r43_scene"
REGION = (-30.0, 30.0, -48.0, 36.0, -82.0, -44.0)
man = json.loads((SCENE / "manifest.json").read_text())

def near(s, r=REGION):
    b = bounds(s)
    return b[1] > r[0] and b[0] < r[1] and b[3] > r[2] and b[2] < r[3] and b[5] > r[4] and b[4] < r[5]

def mesh_of(s):
    path = os.path.join(OUT, "_tmp.stl")
    cq.exporters.export(cq.Workplane().add(s), path, tolerance=0.02, angularTolerance=0.2)
    m = trimesh.load_mesh(path); os.remove(path); return m

def colour(n):
    u = n.upper()
    if "P22" in u: return (0.0, 0.64, 0.61)
    if "P23" in u: return (0.95, 0.55, 0.12)
    if "BEACON" in u or "CARTOGRAPHER" in u: return (0.45, 0.25, 0.6)
    if "CABLE" in u: return (0.9, 0.8, 0.1)
    if "P01" in u or "CORE" in u: return (0.6, 0.6, 0.62)
    if "P20" in u or "P21" in u: return (0.3, 0.75, 0.7)
    return (0.25, 0.25, 0.25)

carriage = []
for n, f in man["carriage"]:
    s = cq.Shape.importBrep(str(SCENE / f))
    if near(s): carriage.append((n, s))
bambu = [(n, cq.Shape.importBrep(str(SCENE / f))) for n, f in man["variants"]["Bambu"]["parts"]]
bambu = [(n, s) for n, s in bambu if near(s)]
print("carriage near:", [n for n, _ in carriage])
items = [(n, mesh_of(s), colour(n)) for n, s in carriage] + [(n, mesh_of(s), (0.2, 0.45, 0.9)) for n, s in bambu]

def draw(ax, origin, normal, M, xl, yl, title):
    for n, m, c in items:
        sec = m.section(plane_origin=origin, plane_normal=normal)
        if sec is None: continue
        p2, _ = sec.to_2D(to_2D=M)
        try:
            polys = p2.polygons_full
        except Exception:
            polys = []
        for poly in polys:
            xs, ys = poly.exterior.xy
            ax.fill(xs, ys, color=c, alpha=0.85, lw=0)
            for h in poly.interiors:
                hx, hy = h.xy
                ax.fill(hx, hy, color="white", lw=0)
        for d in p2.discrete:
            ax.plot(d[:, 0], d[:, 1], color="k", lw=0.4)
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_title(title, fontsize=9)

M = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)
xs_ = (0.0, 5.0, 9.0, 12.0, 15.8, 19.0)
fig, axes = plt.subplots(2, 3, figsize=(27, 13))
for ax, x in zip(axes.flat, xs_):
    draw(ax, [x, 0, 0], [1, 0, 0], M, (-48, 32), (-82, -44), f"side section X {x} (Y right, Z up)")
    ax.plot([22.7], [-78.88], "k+", ms=10, mew=1.5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "side.png"), dpi=55); plt.close(fig)

zs = (-70.0, -68.5, -67.0, -65.0, -62.0, -59.0, -56.0, -53.0)
fig, axes = plt.subplots(2, 4, figsize=(26, 17))
for ax, z in zip(axes.flat, zs):
    draw(ax, [0, 0, z], [0, 0, 1], np.eye(4), (-26, 26), (-48, 32), f"plan Z {z}")
    ax.plot([0], [22.7], "k+", ms=10, mew=1.5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "plan.png"), dpi=50); plt.close(fig)
print("done")
