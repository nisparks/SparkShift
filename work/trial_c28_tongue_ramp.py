import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import r43_c28_mechanical as M
from audit_c28_mechanical_r43 import mesh_check

out = S / "swept_feed" / "optC28_tongue_ramp_trial"
out.mkdir(exist_ok=True)
base = cq.Shape.importBrep(str(S / "r43_scene" / "s0106.brep"))
cable = cq.Shape.importBrep(str(S / "r43_scene" / "s0109.brep"))
keep = M.yz_prism([(-50, -100), (0, -100), (0, -82.2), (-50, -32.2)], -10, 10)
lower = M.cylinder(0, M.RETAINER_Y, M.TONGUE_BOTTOM, M.TONGUE_TOP, M.TONGUE_R)
fork = M.cylinder(0, M.RETAINER_Y, M.TONGUE_TOP - .1, -49, M.TONGUE_R)
fork = fork.cut(M.box(-2, 2, -40, -20, M.TONGUE_TOP, -48.9)).intersect(keep)
yz = [(-33.6, -42), (-33.2, -42), (-33.2, -49),
      (-28.2, -54), (-28.2, -56.2), (-33.6, -50.8)]
roots = [M.yz_prism(yz, 2, 4), M.yz_prism(yz, -4, -2)]
tongue = M.checked(lower.fuse(fork, *roots, tol=.005), "45 degree printing-ramp tongue")
part = base.fuse(tongue, tol=.005).cut(M.cylinder(0, M.RETAINER_Y, -65.1, -61, 2.27),
                            M.cylinder(0, M.RETAINER_Y, -65.1, -60.5, 1.65))
part = M.checked(part, "P21 printing-ramp trial")
added = part.cut(base)
row = {"mesh": mesh_check(part), "cable_overlap_mm3": part.intersect(cable).Volume(),
       "new_material_cable_gap_mm": added.distance(cable),
       "added_in_nominal_channel_air_mm3": added.intersect(M.F.main_channel_air()).Volume(),
       "added_mm3": added.Volume()}
assert row["cable_overlap_mm3"] < 1e-4
part.exportBrep(str(out / "p21.brep"))
(out / "checks.json").write_text(json.dumps(row, indent=2) + "\n")
print(json.dumps(row), flush=True)
