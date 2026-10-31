import json, os, sys, time
REPO = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, REPO); os.chdir(REPO)
import cadquery as cq
import fast_geometry as fg
from audit_bed_front_edge_r34 import frames, NOZZLE_LOCAL_Y
from build_modular_toolhead import primitives

W = primitives.WORK
f = frames()
dock_y = f["world_y_offset_mm"] - NOZZLE_LOCAL_Y
t0 = time.perf_counter()
fly = cq.Shape.importBrep(str(W / "rack_audit_Flying_Gantry_world.brep"))
fm = json.loads((W / "rack_audit_Flying_Gantry_world.json").read_text())
beam = cq.importers.importStep(str(W / "rack_audit_X_Gantry_world.step")).val().translate(
    (0, f["x_gantry_y_shift_to_dock_mm"], 0))
xm = json.loads((W / "rack_audit_X_Gantry_world.json").read_text())
RAILS = {"R1_GANTRY_Y_RAIL_left_400_NOMINAL", "R1_GANTRY_Y_RAIL_left_400_NOMINAL (1)"}
riders = [(m["name"], s) for s, m in zip(beam.Solids(), xm) if m["name"].startswith("_MGN9H")]
others = [(m["name"], s) for s, m in zip(beam.Solids(), xm) if not m["name"].startswith("_MGN9H")]
print("rail-riding block solids:", len(riders), "other beam solids:", len(others))
fixed_all = fg.index_group([(m["name"], s) for s, m in zip(fly.Solids(), fm)])
fixed_norail = [g for g in fixed_all if g.label not in RAILS]
G_riders, G_others = fg.index_group(riders), fg.index_group(others)

def dist(dy, cutoff=3.0):
    found = [h for h in (fg.min_distance(G_others, fixed_all, offset_a=(0, dy, 0), cutoff=cutoff),
                         fg.min_distance(G_riders, fixed_norail, offset_a=(0, dy, 0), cutoff=cutoff)) if h]
    return min(found, key=lambda h: h[0]) if found else None

base = dist(0.0, cutoff=10.0)
print("baseline at dock:", None if base is None else (round(base[0], 3), base[1], base[2]))
last, hit = None, None
for dy in [float(v) for v in range(0, 300, 10)] + [300.0 + 0.5 * i for i in range(0, 161)]:
    h = dist(dy)
    if h is not None and h[0] <= 1e-6:
        lo, hi = (last if last is not None else dy), dy
        while hi - lo > 0.05:
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if (dist(mid) or (9e9,))[0] <= 1e-6 else (mid, hi)
        hit = (round(dock_y + hi, 2), dist(hi)[1:3])
        last = lo
        break
    last = dy
print(f"X beam: last clear nozzle Y {round(dock_y + last, 2)}; first contact {hit}")
at = dist(359.0 - dock_y, cutoff=40.0)
print("X beam clearance at nozzle Y359:", None if at is None else (round(at[0], 3), at[1], at[2]))
print(f"total {time.perf_counter() - t0:.1f} s")
