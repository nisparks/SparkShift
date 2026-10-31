"""Screening prototype: trim each side jet's floor lip back from the exit so the jet can leave lower.

Usage: python build_lip_variant.py <trim mm> <out folder name>
Starts from the audited v5d P22 (the CFD baseline). Removes only floor-lip material that lies directly under the
jet passage (the passage's air just above the lip, extruded down through the lip), from the exit plane |X| = 10.2
out to |X| = 10.2 + trim. The roof, front wall, heel, centre slot and everything else are unchanged. Not
print-qualified.
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
import r43_parts as R43  # noqa: E402
from audit_c28_mechanical_r43 import bounds, quick_overlap  # noqa: E402

trim, name = float(sys.argv[1]), sys.argv[2]
OUT = S / "swept_feed" / name
OUT.mkdir(exist_ok=True)
SOURCE = S / "swept_feed" / "userP21_flow_neutral_v5d"
X0 = R43.WALL_X[0]
TOP, UNDER = R43.LOW_FLOOR, R43.UNDER


def lip_cut(p22, side):
    """Air directly above the lip, in a thin slab on the floor, extruded down through the lip to below the underside."""
    slab = M.box(X0 - .05, X0 + trim, 14.0, 31.0, TOP + .02, TOP + .08).cut(p22)
    faces = [f for f in slab.Faces() if f.normalAt().z < -.99 and abs(f.Center().z - (TOP + .02)) < 1e-6]
    prisms = [cq.Solid.extrudeLinear(f, cq.Vector(0, 0, (UNDER - .1) - (TOP + .02))) for f in faces]
    cut = prisms[0].fuse(*prisms[1:]) if len(prisms) > 1 else prisms[0]
    return cut if side > 0 else cut.mirror("YZ")


p22 = cq.Shape.importBrep(str(SOURCE / "p22.brep"))
p21 = cq.Shape.importBrep(str(SOURCE / "p21.brep"))
right = lip_cut(p22, 1)
cuts = [right, right.mirror("YZ")]
removed = [c.intersect(p22) for c in cuts]
body = M.checked(p22.cut(*cuts, tol=1e-4), f"Side-jet lip trimmed {trim} mm P22")
manifest = json.loads((S / "r43_scene" / "manifest.json").read_text())
tool = {n: cq.Shape.importBrep(str(S / "r43_scene" / p)) for n, p in manifest["variants"]["Bambu"]["parts"]}
scene41 = dict(json.loads((S / "r41_scene" / "manifest.json").read_text())["carriage"])
p20 = cq.Shape.importBrep(str(S / "r41_scene" / scene41["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))
air_before, air_after = U.duct_air(p20, p21, p22), U.duct_air(p20, p21, body)


def open_area(shape, x):
    """Open area of the right jet's vertical exit plane at X, between the print side of the lip and the roof."""
    plane = M.box(x - .01, x + .01, 12.0, 30.0, UNDER - .05, -73.0).cut(shape)
    return plane.Volume() / .02


checks = {
    "trim_mm": trim, "lip_top_z": TOP, "underside_z": UNDER, "exit_x": X0,
    "removed_mm3": [r.Volume() for r in removed], "removed_bounds": [bounds(r) for r in removed],
    "mirror_symmetric_removal": abs(removed[0].Volume() - removed[1].Volume()) < 1e-3,
    "valid_single_solid": body.isValid() and len(body.Solids()) == 1,
    "volume_change_mm3": body.Volume() - p22.Volume(),
    "hotend_overlap_mm3": {n: quick_overlap(body, s) for n, s in tool.items()},
    "p21_overlap_mm3": quick_overlap(body, p21),
    "right_jet_open_area_mm2": {f"x {x}": {"before": open_area(p22, x), "after": open_area(body, x)}
                                for x in (X0 + .05, X0 + trim / 2)},
    "duct_air_mm3": {"before": air_before.Volume(), "after": air_after.Volume()},
}
assert checks["valid_single_solid"] and checks["mirror_symmetric_removal"], checks
assert max(checks["hotend_overlap_mm3"].values()) < 1e-4 and checks["p21_overlap_mm3"] < 1e-4, checks
body.exportBrep(str(OUT / "p22.brep"))
p21.exportBrep(str(OUT / "p21.brep"))
for i, r in enumerate(removed):
    r.exportBrep(str(OUT / f"removed_{'right' if i == 0 else 'left'}.brep"))
(OUT / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
print(json.dumps(checks, indent=1))
