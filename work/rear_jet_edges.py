"""Rear-jet feasibility (session scratch): exact edges behind the nozzle, by ray casts on fine meshes.

For P23 (both builds), both probes, P22 and both hotends: along lines parallel to Y at given (X, Z), the first hit
from the front (a part's front edge) or from the back (a hotend's back edge). Writes rear_jet/edges.json."""
import json
import os
import sys

CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, CAD)
os.chdir(CAD)
import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

import build_and_verify_accessories_v26 as acc  # noqa: E402
import r42_parts as R42  # noqa: E402

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\rear_jet"
SCENE = acc.WORK / "r43_scene"
man = json.loads((SCENE / "manifest.json").read_text())
c = dict(man["carriage"])


def mesh_of(s, tol=0.005):
    p = os.path.join(OUT, "_e.stl")
    cq.exporters.export(cq.Workplane().add(s), p, tolerance=tol, angularTolerance=0.05)
    m = trimesh.load_mesh(p)
    os.remove(p)
    return m


shapes = {"P23_beacon": cq.Shape.importBrep(str(SCENE / c["P23_Probe_Mount_Raised_Rear_Ears_R37_REVIEW"])),
          "Beacon": cq.Shape.importBrep(str(SCENE / c["Beacon_RevH_Raised"])),
          "P22": cq.Shape.importBrep(str(SCENE / c["P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW"])),
          "P23_carto": R42.p23(), "Cartographer": R42.cartographer()}
for label in ("Bambu", "RedLizard"):
    for n, f in man["variants"][label]["parts"]:
        if "hotend" in n:
            shapes[f"{label}:{n}"] = cq.Shape.importBrep(str(SCENE / f))
meshes = {k: mesh_of(v if isinstance(v, cq.Shape) else cq.Shape.cast(v)) for k, v in shapes.items()}


def first_hit(m, origins, direction):
    loc, ri, _ = m.ray.intersects_location(origins, np.tile(direction, (len(origins), 1)), multiple_hits=False)
    out = [None] * len(origins)
    for p, r in zip(loc, ri):
        out[r] = p
    return out


xs = [0.0, 2.0, 4.0, 6.0, 7.0, 8.0, 9.0, 10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0]
res = {}
# front edges (largest Y): rays from Y+40 going -Y
for key, zs in (("P23_beacon", (-74.4, -73.5, -72.5, -71.2)), ("P23_carto", (-74.3, -73.5, -72.5, -71.2)),
                ("Beacon", (-77.9, -77.0, -76.2, -75.4, -74.8)), ("Cartographer", (-77.4, -77.0, -76.2, -75.4, -74.8))):
    res[key] = {}
    for z in zs:
        hits = first_hit(meshes[key], np.array([[x, 40.0, z] for x in xs]), np.array([0.0, -1.0, 0.0]))
        res[key][str(z)] = {str(x): (round(float(h[1]), 2) if h is not None else None) for x, h in zip(xs, hits)}
# hotends' back edges (smallest Y): rays from Y 0 going +Y
for key in [k for k in meshes if ":" in k]:
    res[key] = {}
    for z in (-78.0, -77.0, -76.0, -75.6, -75.3, -74.8, -74.0, -73.5, -73.2, -72.5, -71.5, -70.5, -69.0):
        hits = first_hit(meshes[key], np.array([[x, 0.0, z] for x in xs]), np.array([0.0, 1.0, 0.0]))
        res[key][str(z)] = {str(x): (round(float(h[1]), 2) if h is not None else None) for x, h in zip(xs, hits)}
# P22's underside (lowest Z) along vertical rays from below, on a grid behind the jets
grid = {}
for y in (9.0, 10.0, 11.0, 11.6, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0):
    hits = first_hit(meshes["P22"], np.array([[x, y, -85.0] for x in xs]), np.array([0.0, 0.0, 1.0]))
    grid[str(y)] = {str(x): (round(float(h[2]), 2) if h is not None else None) for x, h in zip(xs, hits)}
res["P22_underside_z"] = grid
json.dump(res, open(os.path.join(OUT, "edges.json"), "w"), indent=1)
for k, v in res.items():
    print("==", k)
    for z, row in v.items():
        print(f"  {z}: " + " ".join(f"{x}:{y}" for x, y in row.items()))
