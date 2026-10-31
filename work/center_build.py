import json, os, sys, time
CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, CAD); os.chdir(CAD)
import cadquery as cq
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
import build_and_verify_accessories_v26 as acc
import r37_parts as P37
import r42_parts as R42
import r43_centre_feed as CF
from audit_tool_owned_2510 import bounds
S = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
OUT = os.path.join(S, "center_feed")
t0 = time.time()
base = cq.Shape.importBrep(os.path.join(S, "cfd", "p22_r43.brep"))
p = CF.p22(base)
print("built", round(time.time() - t0, 1), "s; solids", len(p.Solids()), "valid", p.isValid(), "vol", round(p.Volume(), 1),
      "base vol", round(base.Volume(), 1), "shells", len(p.Shells()))
p.exportBrep(os.path.join(S, "cfd", "p22_r43_centre.brep"))
res = {"volume_mm3": round(p.Volume(), 3), "base_volume_mm3": round(base.Volume(), 3), "valid": p.isValid(),
       "shells": len(p.Shells()), "bounds": [round(v, 3) for v in bounds(p)]}

def dist(a_, b_):
    d = BRepExtrema_DistShapeShape(a_.wrapped, b_.wrapped)
    d.Perform()
    return round(d.Value(), 3) if d.IsDone() else None

def overlap(a_, b_):
    try:
        return round(a_.intersect(b_).Volume(), 4)
    except Exception as e:
        return str(e)

REG = cq.Solid.makeBox(40, 40, 16, cq.Vector(-20, -6, -80))   # region round the new duct
pr = p.intersect(REG)
SCENE = acc.WORK / "r43_scene"
man = json.loads((SCENE / "manifest.json").read_text())
checks = {}
b = P37.beacon()
for i, nm in enumerate(["bottom keepout", "top keepout", "component block", "board", "connector"]):
    if nm.endswith("keepout"):
        checks[f"Beacon {nm} overlap mm3 (plastic allowed)"] = overlap(pr, b[i])
    else:
        checks[f"Beacon {nm}: overlap mm3, distance"] = (overlap(pr, b[i]), dist(pr, b[i]))
c = R42.cartographer()
checks["Cartographer: overlap mm3, distance"] = (overlap(pr, c), dist(pr, c))
for label in ("Bambu", "RedLizard"):
    for n, f in man["variants"][label]["parts"]:
        s = cq.Shape.importBrep(str(SCENE / f))
        bb = bounds(s)
        if bb[4] > -60 or bb[3] < -6 or bb[2] > 34:
            continue
        checks[f"{label}:{n}: distance"] = dist(pr, s)
for n, f in man["carriage"]:
    if n.startswith(("R37_PROBE_", "Probe_Cable", "Core_", "P01_")):
        s = cq.Shape.importBrep(str(SCENE / f))
        if bounds(s)[4] < -60:
            checks[f"{n}: overlap mm3"] = overlap(pr, s)
res["checks"] = checks
pts = {"opening into +X channel": (15.9, 7.1, -71.0), "opening into -X channel": (-15.9, 7.1, -69.5),
       "feed under channel": (15.9, 7.1, -73.0), "across at X11.5": (11.5, 7.0, -72.0),
       "plenum over coil": (0.0, 3.0, -72.5), "on the board over coil": (0.0, 3.0, -74.4),
       "drop X0": (0.0, 12.3, -75.5), "drop X6": (6.0, 11.5, -75.8), "drop X8 below board": (8.0, 11.0, -76.8),
       "leg X8": (8.3, 14.5, -72.0), "manifold X0": (0.0, 14.0, -76.0), "jet X0": (0.0, 16.1, -76.2),
       "jet X5": (5.0, 16.1, -76.2)}
walls_ = {"roof over slot": (0.0, 11.0, -70.4), "roof over diamond": (0.0, -2.0, -70.4), "front wall": (0.0, 13.3, -72.0),
          "manifold roof": (0.0, 14.5, -74.2), "manifold floor": (0.0, 14.0, -77.5), "back wall under board X0": (0.0, 12.1, -76.8),
          "floor under feed": (15.9, 7.1, -74.3), "manifold front wall": (0.0, 16.1, -74.9), "leg inner wall": (6.7, 15.0, -72.0),
          "slot wall X9.8": (9.8, 12.0, -73.0)}
res["air_points_free"] = {k: (not p.isInside(cq.Vector(*v))) for k, v in pts.items()}
res["wall_points_solid"] = {k: p.isInside(cq.Vector(*v)) for k, v in walls_.items()}
json.dump(res, open(os.path.join(OUT, "build_checks.json"), "w"), indent=1)
print(json.dumps(res, indent=1))

def mesh_of(s, tol=0.02):
    q = os.path.join(OUT, "_t.stl"); cq.exporters.export(cq.Workplane().add(s), q, tolerance=tol, angularTolerance=0.15)
    m = trimesh.load_mesh(q); os.remove(q); return m
items = [("P22 centre-feed", mesh_of(pr), (0.0, 0.64, 0.61)), ("Beacon", mesh_of(b[3]), (0.45, 0.25, 0.6)),
         ("Beacon comp", mesh_of(b[2]), (0.45, 0.25, 0.6))]
for label, col in (("Bambu", (0.2, 0.45, 0.9)), ("RedLizard", (0.85, 0.2, 0.2))):
    for n, f in man["variants"][label]["parts"]:
        s = cq.Shape.importBrep(str(SCENE / f))
        bb = bounds(s)
        if bb[4] < -60 and bb[3] > -6 and bb[2] < 34:
            items.append((f"{label}:{n}", mesh_of(s.intersect(REG)), col))

def draw(ax, origin, normal, M, xl, yl, title, alpha_tool=0.45):
    for n, m, c in items:
        if len(m.faces) == 0: continue
        sec = m.section(plane_origin=origin, plane_normal=normal)
        if sec is None: continue
        p2, _ = sec.to_2D(to_2D=M)
        try: polys = p2.polygons_full
        except Exception: polys = []
        al = 0.85 if n.startswith(("P22", "Beacon")) else alpha_tool
        for poly in polys:
            xs, ys = poly.exterior.xy; ax.fill(xs, ys, color=c, alpha=al, lw=0)
            for h in poly.interiors:
                hx, hy = h.xy; ax.fill(hx, hy, color="white", lw=0)
        for d in p2.discrete: ax.plot(d[:, 0], d[:, 1], color="k", lw=0.35)
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_title(title, fontsize=10)

MYZ = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)
MXZ = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
fig, axes = plt.subplots(3, 3, figsize=(24, 19))
for ax, z in zip(axes[0], (-72.3, -75.5, -76.7)):
    draw(ax, [0, 0, z], [0, 0, 1], np.eye(4), (-21, 21), (-7, 24), f"plan Z {z}"); ax.plot([0], [22.7], "k+", ms=10)
for ax, x in zip(axes[1], (0.0, 5.0, 8.3)):
    draw(ax, [x, 0, 0], [1, 0, 0], MYZ, (-7, 25), (-80, -66), f"side X {x} (Y right)"); ax.plot([22.7], [-78.88], "k+", ms=10)
    ax.axhline(-79.08, color="0.4", lw=1.0)
for ax, y in zip(axes[2], (7.0, 12.7, 14.6)):
    draw(ax, [0, y, 0], [0, 1, 0], MXZ, (-21, 21), (-80, -66), f"front section Y {y} (X right)")
    ax.axhline(-79.08, color="0.4", lw=1.0)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "sections.png"), dpi=50); plt.close(fig)
print("done", round(time.time() - t0, 1))
