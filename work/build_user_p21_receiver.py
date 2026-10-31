import argparse
import json
import shutil
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import r43_c28_user_joint as U
import r43_c28_mechanical as M
import r43_swept_feed as F
from audit_c28_mechanical_r43 import bounds, mesh_check, quick_overlap, digest

INPUT = S / "swept_feed" / "userP21_20261030_193918"
parser = argparse.ArgumentParser()
parser.add_argument("--lower-relief", action="store_true")
args = parser.parse_args()
OUT = S / "swept_feed" / ("userP21_matched_v2" if args.lower_relief else "userP21_matched_v1")
OUT.mkdir(exist_ok=True)
scene = S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
read = lambda file: cq.Shape.importBrep(str(scene / file))
old21 = read(next(f for n, f in manifest["carriage"] if n.startswith("P21_")))
cable = read(next(f for n, f in manifest["carriage"] if n.startswith("Probe_Cable")))
user_p21 = cq.Shape.importBrep(str(INPUT / "p21.brep"))
p21 = U.refine_lower_support(user_p21) if args.lower_relief else user_p21
old22 = cq.Shape.importBrep(str(INPUT / "p22.brep"))
p22, construction = U.matched_receiver(p21, old21, old22, cable, lower_relief=args.lower_relief)
for key, body in {"p21": p21, "p22": p22, **construction}.items():
    body.exportBrep(str(OUT / f"{key}.brep"))
shutil.copyfile(INPUT / "p01.brep", OUT / "p01.brep")
air = F.main_channel_air().cut(old22).cut(old21)
report = {
    "lower_relief": args.lower_relief,
    "removed_from_user_p21_mm3": user_p21.cut(p21).Volume(),
    "user_p21_upper_connection_change_mm3": user_p21.cut(p21).intersect(
        M.box(-24, 24, -47, 2, U.RELIEF_TOP, 0)).Volume(),
    "p22": {"valid": p22.isValid(), "mesh": mesh_check(p22), "bounds_mm": bounds(p22),
            "volume_mm3": p22.Volume()},
    "p21_p22_overlap_mm3": quick_overlap(p21, p22),
    "p22_cable_overlap_mm3": quick_overlap(p22, cable),
    "added_material_in_original_channel_air_mm3": p22.cut(old22).intersect(air).Volume(),
    "combined_material_in_original_channel_air_mm3": p22.intersect(air).Volume() + p21.intersect(air).Volume(),
    "hardware_overlaps_mm3": {n: quick_overlap(p22, h) for n, h in M.hardware()},
}
remaining = air.cut(p22).cut(p21).cut(construction["socket"])
assert remaining.isValid()
report["geometric_sections_mm2"] = {}
for axis, values in (("z", (-50, -52, -54, -56, -58, -60)),
                     ("y", (-39, -37, -35, -33, -31, -29, -27))):
    rows = []
    for value in values:
        slab = (M.box(-24, 24, -46, 30, value-.01, value+.01) if axis == "z"
                else M.box(-24, 24, value-.01, value+.01, -79, -48))
        before, after = air.intersect(slab), remaining.intersect(slab)
        assert before.isValid() and after.isValid()
        a, b = before.Volume()/.02, after.Volume()/.02
        rows.append({"position_mm": value, "before": a, "after": b,
                     "change_percent": 100*(b/a-1) if a > 1e-6 else None})
    report["geometric_sections_mm2"][axis] = rows
report["section_scope"] = (
    "Original main-channel corridor remaining after new material and the dry receiver pocket are excluded. "
    "Planes through a curved flow path are geometric diagnostics, not pressure/flow/thermal predictions.")
report["source_sha256"] = {
    "generator": digest(CAD / "r43_c28_user_joint.py"), "p21": digest(INPUT / "p21.brep"),
    "previous_p22": digest(INPUT / "p22.brep"), "original_p21": digest(
        scene / next(f for n, f in manifest["carriage"] if n.startswith("P21_")))}
report["body_sha256"] = {key: digest(OUT / f"{key}.brep") for key in ("p01", "p21", "p22")}
shutil.copyfile(CAD / "r43_c28_user_joint.py", OUT / "generator_snapshot.py")
print(json.dumps(report, indent=2), flush=True)
(OUT / "initial_checks.json").write_text(json.dumps(report, indent=2) + "\n")
