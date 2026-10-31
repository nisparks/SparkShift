"""Screen a candidate dry-bay retainer envelope: static gaps to carriage/tool parts and real-scene motion paths."""
import json
import os
import sys
from pathlib import Path

CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
sys.path.insert(0, str(CAD))

import cadquery as cq

import fast_geometry as fg
import r43_c28_mechanical as M
from audit_c28_mechanical_motion_r43 import check_path
from audit_c28_mechanical_r43 import SOURCE
from build_chute_chamfer_rack_r36 import CENTERS, PITCH, world
from build_inlet_screws_r40 import DOCK_NOZZLE_Y, GANTRY_CENTERS, REAR_LIMITS

manifest = json.loads((SOURCE / "manifest.json").read_text())
read = lambda p: cq.Shape.importBrep(str(SOURCE / p))
# Generous envelope: cheeks/block region in front of P21 and in the bay, plus the screw head below.
envelope = M.box(-4.7, 4.7, -33.2, -18.5, -65.5, -36.5).fuse(M.cylinder(0, -22.5, -72.6, -65.5, 3.1))
static = {}
for name, f in manifest["carriage"]:
    if name.startswith(("P21_", "P22_")):
        continue
    hit = fg.min_distance(fg.index_group([("env", envelope)]), fg.index_group([(name, read(f))]), cutoff=6)
    if hit:
        static[name] = round(hit[0], 3)
for name, f in manifest["variants"]["Bambu"]["parts"]:
    hit = fg.min_distance(fg.index_group([("env", envelope)]), fg.index_group([(name, read(f))]), cutoff=6)
    if hit:
        static[f"Bambu {name}"] = round(hit[0], 3)
print("static gaps under 6 mm:", json.dumps(static, indent=1), flush=True)

changed = [("envelope", envelope)]
f = manifest["frames"]
tool = [(f"Bambu_{n}", read(p)) for n, p in manifest["variants"]["Bambu"]["parts"]]
dock = read(manifest["variants"]["Bambu"]["dock_r36"])
local = tool + [("Dock", dock)]
rows = [check_path("Own tool and dock: withdrawal", changed, local, (0, 0, 0), (0, -60, 0), .5)]
for side in (-1, 1):
    rows.append(check_path(f"Adjacent bay {side}", changed, [(n, p.translate((side * PITCH, 0, 0))) for n, p in local],
                           (0, 0, 0), (0, -60, 0), 1))
moving = [(n, world(s, 0, f)) for n, s in changed]
xgantry = read(manifest["fixed"]["xgantry"]).translate((0, f["x_gantry_y_shift_to_dock_mm"], 0))
rows.append(check_path("X travel vs X gantry", moving, [("X_Gantry", xgantry)],
                       (GANTRY_CENTERS[0], 0, 0), (GANTRY_CENTERS[-1], 0, 0), 1))
flying = read(manifest["fixed"]["flying"])
for rear in REAR_LIMITS:
    dy = rear - DOCK_NOZZLE_Y
    rows.append(check_path(f"Rear {rear}", moving, [("Flying", flying)],
                           (GANTRY_CENTERS[0], dy, 0), (GANTRY_CENTERS[-1], dy, 0), 2))
fixed = [(k, read(manifest["fixed"][k])) for k in ("hardware", "crossbar", "flying")]
for i, c in enumerate(CENTERS[::3]):
    rows.append(check_path(f"Bay approach {c}", moving, fixed, (c, 0, 0), (c, 60, 0), 2))
print(json.dumps([{"path": r["label"], "min_sample_mm": r["minimum_sample"]["mm"],
                   "capped": r["minimum_sample"]["capped"], "bound_mm": r["continuous_clearance_lower_bound_mm"],
                   "obstacle": r["minimum_sample"]["obstacle"]} for r in rows], indent=1))
