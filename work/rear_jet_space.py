"""Rear-jet feasibility (session scratch): what occupies the space behind the nozzle, at and above the jets' height.

Plan sections of the revision-43 carriage (r43_scene: P22, P23 with the Beacon, screws, P01...), the Cartographer
build (r42_parts: its P23, probe and screws) and both mounted tools, at several heights, around the hotend slot; and
side sections (YZ) at X 0 and X 6. The nozzle tip is at (0, 22.7, -78.88); the jets' roof at Z-73.6, floor -77.05."""
import json
import os
import sys

CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, CAD)
os.chdir(CAD)
import cadquery as cq  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

import build_and_verify_accessories_v26 as acc  # noqa: E402
import r42_parts as R42  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\rear_jet"
os.makedirs(OUT, exist_ok=True)
SCENE = acc.WORK / "r43_scene"
REGION = (-26.0, 26.0, -12.0, 36.0, -82.0, -55.0)
man = json.loads((SCENE / "manifest.json").read_text())


def near(s, r=REGION):
    b = bounds(s)
    return b[1] > r[0] and b[0] < r[1] and b[3] > r[2] and b[2] < r[3] and b[5] > r[4] and b[4] < r[5]


def mesh_of(s):
    path = os.path.join(OUT, "_tmp.stl")
    cq.exporters.export(cq.Workplane().add(s), path, tolerance=0.02, angularTolerance=0.2)
    m = trimesh.load_mesh(path)
    os.remove(path)
    return m


carriage = []
for n, f in man["carriage"]:
    s = cq.Shape.importBrep(str(SCENE / f))
    if near(s):
        carriage.append((n, s))
tools = {}
for label, v in man["variants"].items():
    tools[label] = [(n, cq.Shape.importBrep(str(SCENE / f))) for n, f in v["parts"]]
    tools[label] = [(n, s) for n, s in tools[label] if near(s)]
carto = [("R42_P23", R42.p23()), ("Cartographer", R42.cartographer())] + [(n, s) for n, s in R42.hardware()]
carto = [(n, s if isinstance(s, cq.Shape) else cq.Shape.cast(s)) for n, s in carto]
carto = [(n, s) for n, s in carto if near(s)]
info = {"carriage": [(n, [round(v, 2) for v in bounds(s)]) for n, s in carriage],
        "tools": {k: [(n, [round(v, 2) for v in bounds(s)]) for n, s in v] for k, v in tools.items()},
        "cartographer_build": [(n, [round(v, 2) for v in bounds(s)]) for n, s in carto]}
json.dump(info, open(os.path.join(OUT, "parts_near_nozzle.json"), "w"), indent=1)


def colour(n):
    u = n.upper()
    if "P22" in u:
        return (0.0, 0.64, 0.61)
    if "P23" in u:
        return (0.95, 0.55, 0.12)
    if "BEACON" in u or "CARTOGRAPHER" in u:
        return (0.45, 0.25, 0.6)
    if "P01" in u or "CORE" in u:
        return (0.6, 0.6, 0.62)
    if "P20" in u or "P21" in u:
        return (0.3, 0.75, 0.7)
    return (0.25, 0.25, 0.25)


meshes = {"carriage": [(n, mesh_of(s), colour(n)) for n, s in carriage],
          "carto": [(n, mesh_of(s), colour(n)) for n, s in carto]}
tool_mesh = {k: [(n, mesh_of(s), (0.2, 0.45, 0.9) if k == "Bambu" else (0.85, 0.2, 0.2)) for n, s in v]
             for k, v in tools.items()}
# the Beacon build's own probe parts (in the r43 carriage) are left out of the Cartographer build's view
import r37_parts as P37  # noqa: E402
beacon_names = ("Beacon_", P37.NAMES["p23"], "R37_PROBE_", "R37_REAR_")


def draw(ax, items, origin, normal, M, xl, yl, title):
    for n, m, c in items:
        sec = m.section(plane_origin=origin, plane_normal=normal)
        if sec is None:
            continue
        p2, _ = sec.to_2D(to_2D=M)
        for poly in p2.polygons_full:
            xs, ys = poly.exterior.xy
            ax.fill(xs, ys, color=c, alpha=0.85, lw=0)
            for h in poly.interiors:
                hx, hy = h.xy
                ax.fill(hx, hy, color="white", lw=0)
        for d in p2.discrete:
            ax.plot(d[:, 0], d[:, 1], color="k", lw=0.4)
    ax.set_xlim(*xl)
    ax.set_ylim(*yl)
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.set_title(title, fontsize=9)


zs = (-78.0, -76.5, -75.0, -73.0, -71.0, -69.0, -66.0)
builds = [("Beacon build, Bambu", meshes["carriage"] + tool_mesh["Bambu"]),
          ("Beacon build, Red Lizard", meshes["carriage"] + tool_mesh["RedLizard"]),
          ("Cartographer build, Bambu", [x for x in meshes["carriage"] if not x[0].startswith(beacon_names)]
           + meshes["carto"] + tool_mesh["Bambu"])]
fig, axes = plt.subplots(len(builds), len(zs), figsize=(4.0 * len(zs), 4.6 * len(builds)))
for r, (label, items) in enumerate(builds):
    for c, z in enumerate(zs):
        ax = axes[r, c]
        draw(ax, items, [0, 0, z], [0, 0, 1], np.eye(4), (-16, 16), (2, 32), f"{label}\nplan, Z {z}")
        ax.plot([0], [22.7], "k+", ms=10, mew=1.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "rear_space_plan.png"), dpi=60)
plt.close(fig)

M = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)   # Y right, Z up
fig, axes = plt.subplots(len(builds), 3, figsize=(18, 4.6 * len(builds)))
for r, (label, items) in enumerate(builds):
    for c, x in enumerate((0.0, 4.0, 8.0)):
        ax = axes[r, c]
        draw(ax, items, [x, 0, 0], [1, 0, 0], M, (0, 32), (-82, -60), f"{label}\nside section X {x} (Y right, Z up)")
        ax.plot([22.7], [-78.88], "k+", ms=10, mew=1.5)
        for z in (-73.6, -77.05):
            ax.axhline(z, color="c", lw=0.6, ls=":")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "rear_space_side.png"), dpi=60)
print("ok", len(carriage), "carriage parts,", {k: len(v) for k, v in tools.items()}, "tool parts,", len(carto), "carto")
