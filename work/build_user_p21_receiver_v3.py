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
CLEAN = S / "swept_feed" / "optC28_clean"
parser = argparse.ArgumentParser()
parser.add_argument("--lower-relief", action="store_true")
parser.add_argument("--open-front", action="store_true",
                    help="v3: clean angled base (no fork features), relieved socket open into the dry bay")
parser.add_argument("--sealed", action="store_true",
                    help="v4: v3 plus P21 rear seal skirt, P22 sleeve dam and 45 deg rear keel")
args = parser.parse_args()
if args.sealed:
    args.open_front = True
if args.open_front:
    args.lower_relief = True
name = "userP21_matched_v4" if args.sealed else "userP21_matched_v3" if args.open_front else (
    "userP21_matched_v2" if args.lower_relief else "userP21_matched_v1")
OUT = S / "swept_feed" / name
OUT.mkdir(exist_ok=True)
scene = S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
read = lambda file: cq.Shape.importBrep(str(scene / file))
old21 = read(next(f for n, f in manifest["carriage"] if n.startswith("P21_")))
cable = read(next(f for n, f in manifest["carriage"] if n.startswith("Probe_Cable")))
user_p21 = cq.Shape.importBrep(str(INPUT / "p21.brep"))
p21 = U.refine_lower_support(user_p21) if args.lower_relief else user_p21
clean22 = cq.Shape.importBrep(str(CLEAN / "p22_swept_beacon.brep"))
if args.open_front:
    base22 = U.receiver_base(M.angled_p22(clean22))
    base_label = "C28 clean Beacon + 45 deg mounts + screw boss (no fork features)"
else:
    base22 = cq.Shape.importBrep(str(INPUT / "p22.brep"))
    base_label = "Checked fork-receiver P22"
p22, construction = U.matched_receiver(p21, old21, base22, cable, lower_relief=args.lower_relief,
                                       open_front=args.open_front, sealed=args.sealed)
if args.sealed:
    unsealed21 = p21
    p21 = U.sealed_p21(p21)
    construction["skirt"] = p21.cut(unsealed21)
for key, body in {"p21": p21, "p22": p22, "base_p22": base22, **construction}.items():
    body.exportBrep(str(OUT / f"{key}.brep"))
shutil.copyfile(INPUT / "p01.brep", OUT / "p01.brep")


def duct_cavity(p21_body, p22_body):
    """Inlet-connected air after removing the CFD outlet box; a sealed duct stays inside the carriage."""
    scene41 = dict(json.loads((S / "r41_scene" / "manifest.json").read_text())["carriage"])
    p20 = cq.Shape.importBrep(str(S / "r41_scene" / scene41["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))
    duct = p20.fuse(p21_body).fuse(p22_body)
    cap = cq.Solid.makeCylinder(8.2 + 2.5, 2.0, cq.Vector(0, -48.5, 29.0))
    space = M.box(-40, 40, -70, 60, -110, 45).cut(duct).cut(cap).cut(M.box(-30, 30, -20, 50, -79.08, -45))
    cavity = next(s for s in space.Solids() if s.isInside(cq.Vector(0, -48.5, 20.0)))
    b = bounds(cavity)
    return {"volume_mm3": cavity.Volume(), "bounds_mm": b,
            "sealed": b[0] > -39 and b[1] < 39 and b[2] > -69 and b[5] < 44}
corridor = F.main_channel_air()
air_fork = corridor.cut(cq.Shape.importBrep(str(INPUT / "p22.brep"))).cut(old21)
air_clean = corridor.cut(clean22).cut(old21)
after_air = corridor.cut(p22).cut(p21)
report = {
    "variant": name, "base_p22": base_label,
    "lower_relief": args.lower_relief, "open_front": args.open_front,
    "removed_from_user_p21_mm3": user_p21.cut(p21).Volume(),
    "user_p21_upper_connection_change_mm3": user_p21.cut(p21).intersect(
        M.box(-24, 24, -47, 2, U.RELIEF_TOP, 0)).Volume(),
    "p22": {"valid": p22.isValid(), "mesh": mesh_check(p22), "bounds_mm": bounds(p22),
            "volume_mm3": p22.Volume()},
    "p21_p22_overlap_mm3": quick_overlap(p21, p22),
    "p21_p22_gap_mm": p21.distance(p22),
    "p22_cable_overlap_mm3": quick_overlap(p22, cable),
    "p22_cable_gap_mm": p22.distance(cable),
    "p21_cable_gap_mm": p21.distance(cable),
    "material_in_fork_reference_channel_air_mm3": p22.intersect(air_fork).Volume() + p21.intersect(air_fork).Volume(),
    "material_in_clean_c28_channel_air_mm3": {
        "p22": p22.intersect(air_clean).Volume(), "p21": p21.intersect(air_clean).Volume()},
    "remaining_channel_air_mm3": {"clean_c28": air_clean.Volume(), "after": after_air.Volume()},
    "hardware_overlaps_mm3": {n: quick_overlap(p22, h) for n, h in M.hardware()},
    "duct_cavity": duct_cavity(p21, p22),
    "baseline_duct_cavity_mm3": 27775.6,
    "construction_volumes_mm3": {k: v.Volume() for k, v in construction.items()},
}
print("duct cavity", json.dumps(report["duct_cavity"]), flush=True)
if args.sealed:
    assert report["duct_cavity"]["sealed"], "The sealed receiver still leaks duct air"
if args.open_front:
    opening = construction["front_opening"]
    removed = base22.fuse(construction["reinforcement"], tol=.005).intersect(opening)
    report["front_opening"] = {
        "original_channel_corridor_overlap_mm3": opening.intersect(corridor).Volume(),
        "gap_to_remaining_channel_air_mm": opening.distance(after_air),
        "removed_dry_material_mm3": removed.Volume(),
        "removed_material_gap_to_remaining_channel_air_mm": removed.distance(after_air) if removed.Volume() > 1e-6 else None,
        "cable_gap_mm": opening.distance(cable),
    }
    assert report["front_opening"]["original_channel_corridor_overlap_mm3"] < 1e-4, report["front_opening"]
remaining = after_air.cut(construction["socket"])
assert remaining.isValid()
report["geometric_sections_mm2"] = {}
for axis, values in (("z", (-50, -52, -54, -56, -58, -60)),
                     ("y", (-39, -37, -35, -33, -31, -29, -27))):
    rows = []
    for value in values:
        slab = (M.box(-24, 24, -46, 30, value-.01, value+.01) if axis == "z"
                else M.box(-24, 24, value-.01, value+.01, -79, -48))
        before, after = air_clean.intersect(slab), remaining.intersect(slab)
        assert before.isValid() and after.isValid()
        a, b = before.Volume()/.02, after.Volume()/.02
        rows.append({"position_mm": value, "clean_c28": a, "after": b,
                     "change_percent": 100*(b/a-1) if a > 1e-6 else None})
    report["geometric_sections_mm2"][axis] = rows
report["section_scope"] = (
    "Clean-C28 main-channel corridor versus the remaining corridor after this variant. Planes through a "
    "curved flow path are geometric diagnostics, not pressure/flow/thermal predictions.")
report["source_sha256"] = {
    "generator": digest(CAD / "r43_c28_user_joint.py"), "p21": digest(INPUT / "p21.brep"),
    "clean_c28_beacon": digest(CLEAN / "p22_swept_beacon.brep"), "original_p21": digest(
        scene / next(f for n, f in manifest["carriage"] if n.startswith("P21_")))}
report["body_sha256"] = {key: digest(OUT / f"{key}.brep") for key in ("p01", "p21", "p22")}
shutil.copyfile(CAD / "r43_c28_user_joint.py", OUT / "generator_snapshot.py")
print(json.dumps(report, indent=2), flush=True)
(OUT / "initial_checks.json").write_text(json.dumps(report, indent=2) + "\n")
