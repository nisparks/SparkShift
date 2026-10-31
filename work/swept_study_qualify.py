import argparse
import json
import os
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
OUT = S / "swept_feed"
parser = argparse.ArgumentParser()
parser.add_argument("--roof-raise", type=float, default=0.0)
parser.add_argument("--mouth-height", type=float, default=1.3)
parser.add_argument("--angle", type=float, default=32.0)
parser.add_argument("--tag")
parser.add_argument("--clean-direct-mount", action="store_true")
parser.add_argument("--conformal-outlet", action="store_true")
parser.add_argument("--clear-feed-intrusions", action="store_true")
parser.add_argument("--mouth-floor-reference", type=float)
parser.add_argument("--printable-c28", action="store_true")
parser.add_argument("--bambu-only", action="store_true")
args = parser.parse_args()
RAISE, HEIGHT, ANGLE = args.roof_raise, args.mouth_height, args.angle
if args.tag:
    OUT = OUT / args.tag
elif RAISE:
    OUT = OUT / f"roof{RAISE:g}"
sys.path.insert(0, str(CAD))
os.chdir(CAD)
import cadquery as cq
import numpy as np
import trimesh
import fast_geometry as fg
import build_and_verify_accessories_v26 as acc
import build_cpap_outlet_r43 as V
import r43_swept_feed as R
import r42_parts as C
import r37_parts as B

result = json.loads((OUT / "checks.json").read_text())
assert result["outlet_angle_deg"] == ANGLE and result["mouth_height_mm"] == HEIGHT
assert result["roof_raise_mm"] == RAISE
assert result.get("conformal_outlet_wall", False) == args.conformal_outlet
assert result.get("full_height_feed_clearance", False) == args.clear_feed_intrusions
assert result.get("mouth_floor_reference_height_mm") == args.mouth_floor_reference
assert result.get("printable_c28_variant", False) == args.printable_c28
assert result.get("hotend_scope", "Bambu and Red Lizard") == (
    "Bambu only" if args.bambu_only else "Bambu and Red Lizard")
assert result["obsolete_rear_mounts_removed"] == args.clean_direct_mount
result["source"] = ("r43_swept_printable.py applied to cleaned C28; released r43_parts.py unchanged"
                    if args.printable_c28 else "r43_swept_feed.py; released r43_parts.py unchanged")
result["status"] = "Geometry study; CFD pending; not print-qualified"
part = cq.Shape.importBrep(str(OUT / "p22_swept_beacon.brep"))
carto = cq.Shape.importBrep(str(OUT / "p22_swept_cartographer.brep"))
base = cq.Shape.importBrep(str(S / "cfd" / "p22_r43.brep"))
manifest = json.loads((acc.WORK / "r43_scene" / "manifest.json").read_text())
br = lambda f: cq.Shape.importBrep(str(acc.WORK / "r43_scene" / f))
group = [fg.index_of(s) for s in part.Solids()]
withdrawal = {}
for label in (("Bambu",) if args.bambu_only else ("Bambu", "RedLizard")):
    near = [(n, br(f)) for n, f in manifest["variants"][label]["parts"]]
    near = [(n, s) for n, s in near if s.BoundingBox().zmin < -60]
    other = fg.index_group(near)
    best = None
    for retreat in np.arange(0, 60.01, 0.5):
        hit = fg.min_distance(group, other, offset_a=(0, -float(retreat), 0), cutoff=8)
        if hit and (best is None or hit[0] < best["gap_mm"]):
            best = {"gap_mm": hit[0], "retreat_mm": float(retreat), "tool_part": hit[2]}
    withdrawal[label] = best
    print("withdrawal", label, best, flush=True)
result["withdrawal"] = {"carriage_retreat": "-Y", "length_mm": 60, "sample_step_mm": 0.5, "tools": withdrawal,
                        "limitation": "Sampled rigid-body path, not a continuous-motion or thermal validation"}
nozzle = [fg.index_of(s) for s in R.nozzle(
    True, RAISE, HEIGHT, ANGLE, conformal_outlet=args.conformal_outlet,
    floor_reference_height=args.mouth_floor_reference).Solids()]
gaps = {}
for label, probe in (("Beacon", B.beacon()[3]), ("Cartographer", C.cartographer())):
    hit = fg.min_distance(nozzle, [fg.index_of(s) for s in probe.Solids()], cutoff=10)
    gaps[label] = round(hit[0], 4) if hit else None
result["nozzle_to_probe_gap_mm"] = gaps

def mesh(s):
    vertices, triangles = s.tessellate(0.02, 0.1)
    return trimesh.Trimesh([v.toTuple() for v in vertices], triangles, process=True)

result["print"] = {
    "orientation": "Original back face down, same as R43; study only",
    "support_threshold_deg": V.SUPPORT_DEG,
    "released_r43": V.overhang(mesh(V.print_oriented(base))),
    "swept_study": V.overhang(mesh(V.print_oriented(part))),
    "orientation_sweep": V.orientation_sweep(mesh(part)),
    "limitation": "Geometric overhang screening only; not sliced or physically printed. Do not trap HIPS "
                  "inside the narrow outlet. Internal bridge access still requires slicer review.",
}
print("print", result["print"], flush=True)
rebuilt = R.p22(base, "Cartographer", roof_raise=RAISE, mouth_height=HEIGHT, angle_deg=ANGLE,
                conformal_outlet=args.conformal_outlet, clear_feed_intrusions=args.clear_feed_intrusions,
                floor_reference_height=args.mouth_floor_reference)
if args.clean_direct_mount:
    rebuilt = R.clean_direct_mount(rebuilt)
if args.printable_c28:
    import r43_swept_printable as DFM
    rebuilt = DFM.p22(rebuilt, "Cartographer")
result["cartographer_rebuild_difference_mm3"] = {
    "export_only": carto.cut(rebuilt).Volume(),
    "rebuild_only": rebuilt.cut(carto).Volume(),
}
result["cartographer_generator_matches_export"] = all(
    volume < 1e-4 for volume in result["cartographer_rebuild_difference_mm3"].values())
assert result["valid"] and result["solids"] == result["shells"] == 1
assert result["cartographer_valid"] and result["cartographer_solids"] == result["cartographer_shells"] == 1
assert result["connected_air_solids"] == 1 and result["air_cut_obstruction_mm3"] < 1e-4
assert result["mesh_watertight"] and result["sampled_wall_check"]["outside_solid"] == 0
assert result["cartographer_generator_matches_export"]
for label in ("Beacon", "Cartographer"):
    assert result["assembly"][label]["probe_overlap_mm3"] < 1e-4
    assert result["assembly"][label]["bottom_sensing_keepout_overlap_mm3"] < 1e-4
    assert result["assembly"][label]["metal_in_top_keepout_mm3"] < 1e-4
for label, row in result["assembly"].items():
    if "overlap_mm3" in row:
        assert row["overlap_mm3"] <= row.get("baseline_overlap_mm3", 0) + 1e-4, label
assert withdrawal["Bambu"]["gap_mm"] > 1.9
if not args.bambu_only:
    assert withdrawal["RedLizard"]["gap_mm"] > 0.5
result["geometry_checks_pass"] = True
(OUT / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
report_name = (f"verification_swept_feed_{args.tag}_r43.json" if args.tag else
               f"verification_swept_feed_roof{RAISE:g}_r43.json" if RAISE else "verification_swept_feed_r43.json")
(CAD / report_name).write_text(json.dumps(result, indent=2) + "\n")
print("geometry checks passed", gaps, flush=True)
