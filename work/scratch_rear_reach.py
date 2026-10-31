import json, os, sys, time
REPO = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, REPO); os.chdir(REPO)
import cadquery as cq
import fast_geometry as fg
from audit_bed_front_edge_r34 import frames, NOZZLE_LOCAL_Y
from audit_low_z_bed_clearance import load_parked_variants
from audit_ten_tool_rack import world
from audit_tool_owned_2510 import bounds
from build_fan_mounts_r33 import carriage
from build_modular_toolhead import primitives

W = primitives.WORK
f = frames()
dock_y = f["world_y_offset_mm"] - NOZZLE_LOCAL_Y
t0 = time.perf_counter()
fly = cq.Shape.importBrep(str(W / "rack_audit_Flying_Gantry_world.brep"))
fm = json.loads((W / "rack_audit_Flying_Gantry_world.json").read_text())
for s, m in zip(fly.Solids(), fm):
    exp = [v for p in zip(m["min_mm"], m["max_mm"]) for v in p]
    assert max(abs(a - b) for a, b in zip(bounds(s), exp)) < 0.05, m["name"]
beam = cq.importers.importStep(str(W / "rack_audit_X_Gantry_world.step")).val().translate(
    (0, f["x_gantry_y_shift_to_dock_mm"], 0))
xm = json.loads((W / "rack_audit_X_Gantry_world.json").read_text())
assert len(beam.Solids()) == len(xm) and len(fly.Solids()) == len(fm)
RAILS = {"R1_GANTRY_Y_RAIL_left_400_NOMINAL", "R1_GANTRY_Y_RAIL_left_400_NOMINAL (1)"}
BEARINGS = {"_MGN9H (10)", "_MGN9H (11)", "_MGN9H (12)", "_MGN9H (13)"}
fixed_all = fg.index_group([(m["name"], s) for s, m in zip(fly.Solids(), fm)])
fixed_norail = [g for g in fixed_all if g.label not in RAILS]
bear = fg.index_group([(m["name"], s) for s, m in zip(beam.Solids(), xm) if m["name"] in BEARINGS])
rest = fg.index_group([(m["name"], s) for s, m in zip(beam.Solids(), xm) if m["name"] not in BEARINGS])
by = [bounds(s) for s, m in zip(beam.Solids(), xm) if m["name"] in BEARINGS]
rails = [m for m in fm if m["name"] in RAILS]
rmin, rmax = max(m["min_mm"][1] for m in rails), min(m["max_mm"][1] for m in rails)
print(f"dock nozzle Y {dock_y:.2f}; X-beam bearings Y {min(b[2] for b in by):.2f}..{max(b[3] for b in by):.2f} at dock; rails Y {rmin}..{rmax}")
print(f"rail-length limit on nozzle Y: {dock_y - (min(b[2] for b in by) - rmin):.2f} .. {dock_y + rmax - max(b[3] for b in by):.2f}")
v = load_parked_variants()
rig = [(n, world(s, 0.0, f)) for n, s in carriage()]
car = {k: fg.index_group(rig + [(f"{k}_tool", world(v[k]["tool"], 0.0, f))]) for k in v}
print(f"indexed in {time.perf_counter() - t0:.1f} s", flush=True)

def dist(a, b, off, cutoff=3.0):
    h = fg.min_distance(a, b, offset_a=off, cutoff=cutoff)
    return None if h is None else (round(h[0], 3), h[1], h[2])

def contact(r):
    return r is not None and r[0] <= 1e-6

def limit(check, samples):
    """Last collision-free dy before the first contact, refined by bisection to 0.05 mm."""
    last = None
    for dy in samples:
        if contact(check(dy)):
            if last is None:
                return None, dy
            lo, hi = last, dy
            while hi - lo > 0.05:
                mid = 0.5 * (lo + hi)
                lo, hi = (lo, mid) if contact(check(mid)) else (mid, hi)
            return lo, check(hi)
        last = dy
    return last, None

base = [dist(rest, fixed_all, (0, 0, 0)), dist(bear, fixed_norail, (0, 0, 0))]
print("baseline at dock (beam, bearings):", base)
samples = [float(dy) for dy in range(40, 300, 10)] + [300.0 + i for i in range(0, 76)]
beam_dy, beam_hit = limit(lambda dy: min([r for r in (dist(rest, fixed_all, (0, dy, 0)), dist(bear, fixed_norail, (0, dy, 0))) if r is not None] or [None], key=lambda r: r[0] if r else 9e9), samples)
print(f"X beam: last clear nozzle Y {None if beam_dy is None else round(dock_y + beam_dy, 2)}; first contact {beam_hit}", flush=True)
for k in car:
    for x in (0.0, 25.0, 175.0, 325.0, 350.0):
        dy, hit = limit(lambda dy: dist(car[k], fixed_all, (x, dy, 0)), samples)
        at359 = dist(car[k], fixed_all, (x, 359.0 - dock_y, 0), cutoff=40.0)
        print(f"{k:9s} nozzle X {x:5.1f}: last clear nozzle Y {None if dy is None else round(dock_y + dy, 2)}; first contact {hit}; clearance at Y359 {at359}", flush=True)
print(f"total {time.perf_counter() - t0:.1f} s")
