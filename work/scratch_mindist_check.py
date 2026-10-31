import json, os, sys, time
REPO = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, REPO); os.chdir(REPO)
import numpy as np
import cadquery as cq
import fast_geometry as fg
from audit_bed_front_edge_r34 import frames, NOZZLE_LOCAL_Y
from audit_low_z_bed_clearance import load_parked_variants
from audit_ten_tool_rack import world
from build_fan_mounts_r33 import carriage
from build_modular_toolhead import primitives

def old_min_distance(group_a, group_b, offset_a=(0, 0, 0), offset_b=(0, 0, 0), cutoff=5.0):
    oa, ob = np.asarray(offset_a, float), np.asarray(offset_b, float)
    pairs = []
    for a in group_a:
        for b in group_b:
            d = fg._box_distance(a.box_lo + oa, a.box_hi + oa, b.box_lo + ob, b.box_hi + ob)
            if d < cutoff:
                pairs.append((float(d), a, b))
    pairs.sort(key=lambda t: t[0])
    best, found = cutoff, None
    for box, a, b in pairs:
        if box >= best:
            break
        hit = fg.solid_distance(a, b, offset_a, offset_b, best)
        if hit is not None:
            best = hit[0]
            found = (hit[0], a.label, b.label, hit[1], hit[2])
    return found

W = primitives.WORK
f = frames()
dock_y = f["world_y_offset_mm"] - NOZZLE_LOCAL_Y
fly = cq.Shape.importBrep(str(W / "rack_audit_Flying_Gantry_world.brep"))
fm = json.loads((W / "rack_audit_Flying_Gantry_world.json").read_text())
fixed = fg.index_group([(m["name"], s) for s, m in zip(fly.Solids(), fm)])
v = load_parked_variants()
moving = fg.index_group([(n, world(s, 0.0, f)) for n, s in carriage()] + [("tool", world(v["Bambu"]["tool"], 0.0, f))])
print("groups", len(moving), len(fixed))
cases = [(0, 300), (0, 346.7), (0, 346.8), (0, 338.29), (25, 338.29), (175, 365.2), (350, 338.29), (350, 346.75), (175, 0)]
t_old = t_new = 0.0
same = True
for x, dy in cases:
    for cutoff in (3.0, 40.0):
        t = time.perf_counter(); a = old_min_distance(moving, fixed, (x, dy, 0), cutoff=cutoff); t_old += time.perf_counter() - t
        t = time.perf_counter(); b = fg.min_distance(moving, fixed, (x, dy, 0), cutoff=cutoff); t_new += time.perf_counter() - t
        ok = (a is None and b is None) or (a is not None and b is not None and a[0] == b[0] and a[1:3] == b[1:3] and a[3] == b[3] and a[4] == b[4])
        same &= ok
        print(f"x {x:5.1f} dy {dy:7.2f} cutoff {cutoff:4.1f}: {'same' if ok else 'DIFFERENT'} {None if b is None else (round(b[0], 4), b[1], b[2])}")
print(f"identical: {same}; old {t_old:.2f} s, new {t_new:.2f} s")
