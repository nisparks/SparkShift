"""Screening prototype: lower each side jet's roof (with its bell-mouth round) so the jet passes under the heater block.

Usage: python build_visor_variant.py <roof z> <out folder name>
Starts from the audited v5d P22. Only adds material inside the duct's side channels at the jet exits; the hotend
slot (|X| < 10.2), the floor, the centre slot and everything else are unchanged. Not print-qualified.
"""
import json
import os
import sys
from pathlib import Path

CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
sys.path.insert(0, str(CAD))

import cadquery as cq  # noqa: E402

import r41_parts as R41  # noqa: E402
import r43_c28_mechanical as M  # noqa: E402
import r43_c28_user_joint as U  # noqa: E402
import r43_parts as R43  # noqa: E402
from audit_c28_mechanical_r43 import bounds, quick_overlap  # noqa: E402

roof, name = float(sys.argv[1]), sys.argv[2]
OUT = S / "swept_feed" / name
OUT.mkdir(exist_ok=True)
SOURCE = S / "swept_feed" / "optC28_flow_neutral_retainer"
Y0, Y1 = 16.0, 29.0


def visor(side):
    x0 = R43.WALL_X[0]
    xb, zc, ztop = x0 + R43.BELL_R, roof + R43.BELL_R, R43.ROOF + R43.BELL_R
    block = M.box(x0, xb, Y0, Y1, zc, ztop)
    disc = cq.Solid.makeCylinder(R43.BELL_R, Y1 - Y0, cq.Vector(x0, Y0, zc), cq.Vector(0, 1, 0))
    body = block.fuse(disc.intersect(M.box(x0, xb + .1, Y0, Y1, roof - .1, zc)))
    body = body.intersect(R41.shape(R43.inside(roof - 1, ztop + 1)))
    return body if side > 0 else body.mirror("YZ")


p22 = cq.Shape.importBrep(str(SOURCE / "p22.brep"))
p21 = cq.Shape.importBrep(str(SOURCE / "p21.brep"))
added = [visor(s).cut(p22) for s in (1, -1)]
body = M.checked(p22.fuse(*added, tol=1e-4), "Side-jet visor screening P22")
manifest = json.loads((S / "r43_scene" / "manifest.json").read_text())
tool = {n: cq.Shape.importBrep(str(S / "r43_scene" / p)) for n, p in manifest["variants"]["Bambu"]["parts"]}
scene41 = dict(json.loads((S / "r41_scene" / "manifest.json").read_text())["carriage"])
p20 = cq.Shape.importBrep(str(S / "r41_scene" / scene41["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))
air = U.duct_air(p20, p21, body)


def exit_area(shape):
    """Open area of the right jet's exit face just inside the hotend slot wall."""
    plane = M.box(10.24, 10.26, 12.0, 30.0, -77.5, -73.0).cut(shape)
    return plane.Volume() / .02


checks = {
    "roof_z": roof, "drop_mm": R43.ROOF - roof,
    "added_mm3": [a.Volume() for a in added], "added_bounds": [bounds(a) for a in added],
    "valid_single_solid": body.isValid() and len(body.Solids()) == 1,
    "hotend_overlap_mm3": {n: quick_overlap(body, s) for n, s in tool.items()},
    "p21_overlap_mm3": quick_overlap(body, p21),
    "right_jet_exit_open_area_mm2": {"before": exit_area(p22), "after": exit_area(body)},
    "duct_air_mm3": air.Volume(),
}
assert checks["valid_single_solid"] and max(checks["hotend_overlap_mm3"].values()) < 1e-4, checks
body.exportBrep(str(OUT / "p22.brep"))
p21.exportBrep(str(OUT / "p21.brep"))
(OUT / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
print(json.dumps(checks, indent=1))
