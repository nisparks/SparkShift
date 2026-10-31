import json, os, sys
CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, CAD); os.chdir(CAD)
import cadquery as cq
import numpy as np
import trimesh
import build_and_verify_accessories_v26 as acc
import r37_parts as P37
import r42_parts as R42
from audit_tool_owned_2510 import bounds
OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\center_feed"

def mesh_of(s):
    p = os.path.join(OUT, "_t.stl"); cq.exporters.export(cq.Workplane().add(s), p, tolerance=0.01, angularTolerance=0.1)
    m = trimesh.load_mesh(p); os.remove(p); return m

def first_hit(m, origins, d):
    loc, idx_ray, _ = m.ray.intersects_location(origins, np.tile(d, (len(origins), 1)), multiple_hits=True)
    out = [None] * len(origins)
    for p, i in zip(loc, idx_ray):
        t = float(np.dot(p - origins[i], d))
        if t >= 0 and (out[i] is None or t < out[i]): out[i] = t
    return out

res = {}
b = P37.beacon()
board = b[3]
print("beacon parts bounds:", [[round(v, 2) for v in bounds(s)] for s in b])
mb = mesh_of(board)
xs = np.arange(0, 19.01, 1.0)
o = np.array([[x, 30.0, -75.5] for x in xs])
h = first_hit(mb, o, np.array([0, -1.0, 0]))
res["beacon_front_edge_y"] = {f"{x:g}": (round(30 - t, 3) if t is not None else None) for x, t in zip(xs, h)}
# Cartographer: everything above its board top in the front half
c = R42.cartographer()
cs = [s for s in c.Solids()]
items = []
for s in cs:
    bb = bounds(s)
    if bb[5] > -74.4 and bb[3] > -8 and bb[0] < 19 and bb[1] > -19:
        items.append([round(v, 2) for v in bb])
res["carto_solids_above_board_front"] = items
res["carto_n_solids"] = len(cs)
mc = mesh_of(c)
hc = first_hit(mc, np.array([[x, 30.0, -75.5] for x in xs]), np.array([0, -1.0, 0]))
res["carto_front_edge_y_at_z-75.5"] = {f"{x:g}": (round(30 - t, 3) if t is not None else None) for x, t in zip(xs, hc)}
# top surface of Cartographer over the front region: ray down from Z -60 at a grid
grid = [(x, y) for x in np.arange(-18, 18.1, 2.0) for y in np.arange(-6, 12.1, 2.0)]
hd = first_hit(mc, np.array([[x, y, -60.0] for x, y in grid]), np.array([0, 0, -1.0]))
tops = {}
for (x, y), t in zip(grid, hd):
    if t is not None: tops[f"{x:g},{y:g}"] = round(-60.0 - t, 3)
res["carto_top_z_grid"] = tops
hb = first_hit(mesh_of(P37.beacon()[2]), np.array([[x, y, -60.0] for x, y in grid]), np.array([0, 0, -1.0]))
res["beacon_component_block_hits"] = {f"{x:g},{y:g}": round(-60 - t, 3) for (x, y), t in zip(grid, hb) if t is not None}
# P22 final: arm air and floor around Y 2..12, |X| 10..21: vertical rays up from Z -71 (inside P22 floor?)
p22 = cq.Shape.importBrep(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\cfd\p22_r43.brep")
m22 = mesh_of(p22)
prof = {}
for y in (2.0, 4.0, 6.0, 8.0, 10.0, 11.0, 12.0):
    row = {}
    for x in (9.0, 10.0, 11.0, 11.5, 12.0, 12.5, 13.0, 14.0, 16.0, 18.0, 19.0, 19.5, 20.0, 21.0):
        orig = np.array([[x, y, -90.0]])
        loc, ir, _ = m22.ray.intersects_location(orig, np.array([[0, 0, 1.0]]), multiple_hits=True)
        zs = sorted(round(float(p[2]), 2) for p in loc if p[2] < -55)
        row[f"{x:g}"] = zs[:6]
    prof[f"{y:g}"] = row
res["p22_z_crossings_upward_by_y_then_x"] = prof
json.dump(res, open(os.path.join(OUT, "facts.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "p22_z_crossings_upward_by_y_then_x"}, indent=0)[:3000])
for y, row in prof.items(): print("Y", y, row)
