"""Apply the current (v5d) flow-neutral P21/P22 joint to a different clean C28 outlet, for balance CFD.

Usage: python build_balance_variant.py <clean p22 beacon brep> <out folder name>
The outlet variant must differ from the clean C28 P22 only at the outlets; the joint, mounts and post are
rebuilt exactly as v5d. Writes swept_feed/<out>/{p21,p22}.brep and checks.json.
"""
import json
import os
import sys
from pathlib import Path

CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
sys.path.insert(0, str(CAD))

import cadquery as cq  # noqa: E402

import r43_c28_mechanical as M  # noqa: E402
import r43_c28_user_joint as U  # noqa: E402
from audit_c28_mechanical_r43 import bounds, quick_overlap  # noqa: E402

source, name = Path(sys.argv[1]), sys.argv[2]
OUT = S / "swept_feed" / name
OUT.mkdir(exist_ok=True)
scene = json.loads((S / "r43_scene" / "manifest.json").read_text())
old21 = cq.Shape.importBrep(str(S / "r43_scene" / next(f for n, f in scene["carriage"] if n.startswith("P21_"))))
scene41 = dict(json.loads((S / "r41_scene" / "manifest.json").read_text())["carriage"])
p20 = cq.Shape.importBrep(str(S / "r41_scene" / scene41["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))
user, _ = U.load_user_p21(S / "swept_feed" / "userP21_20261030_193918" / "p21_user_snapshot.step")
clean = cq.Shape.importBrep(str(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep"))
variant = cq.Shape.importBrep(str(source))
added, removed = variant.cut(clean), clean.cut(variant)
angled = M.angled_p22(variant)
air = U.clean_duct_air(p20, old21, angled)
p21, p22, parts = U.flow_neutral_parts(user, old21, angled, air, print_bevels=True, full_recess=True)
reference = {k: cq.Shape.importBrep(str(S / "swept_feed" / "optC28_flow_neutral_retainer" / f"{k}.brep"))
             for k in ("p21", "p22")}
checks = {
    "source": str(source),
    "outlet_change_vs_clean_c28_mm3": {"added": added.Volume(), "removed": removed.Volume(),
                                        "added_bounds": bounds(added) if added.Volume() > 1e-6 else None,
                                        "removed_bounds": bounds(removed) if removed.Volume() > 1e-6 else None},
    "p21_difference_vs_v5d_mm3": p21.cut(reference["p21"]).Volume() + reference["p21"].cut(p21).Volume(),
    "p22_difference_vs_v5d_mm3": {"added": p22.cut(reference["p22"]).Volume(),
                                  "removed": reference["p22"].cut(p22).Volume()},
    "p21_p22_overlap_mm3": quick_overlap(p21, p22),
    "duct_air_mm3": U.duct_air(p20, p21, p22).Volume(),
    "valid": p21.isValid() and p22.isValid(),
}
p21.exportBrep(str(OUT / "p21.brep"))
p22.exportBrep(str(OUT / "p22.brep"))
(OUT / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
print(json.dumps(checks, indent=1))
