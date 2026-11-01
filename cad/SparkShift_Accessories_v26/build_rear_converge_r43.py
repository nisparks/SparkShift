"""Converge the rear (centre) outlet in plan so its two halves meet on the centreline, on FR1.

python build_rear_converge_r43.py review_fr1_rc24 --exit-x 5.0 --yaw 24.4
python build_rear_converge_r43.py review_fr1_rc36 --exit-x 6.5 --yaw 36
Each end of the rear passage is filled outboard of a vertical plane through (|X| exit-x, mouth Y) yawed inward by
--yaw degrees from +Y. The edge air leaves turned toward the centreline: at 24.4 degrees from |X| 5 it aims at the
nozzle axis; at 36 degrees from |X| 6.5 it crosses the centreline at about Y 20. Material is added only inside the
existing rear passage air (no extension past its mouth), so every hotend and probe gap is unchanged or larger.
The wall is a solid end wall, not a vane, and leans at most 45 degrees from the build axis.
"""
import argparse
import json
import math
from pathlib import Path

import cadquery as cq

import build_and_verify_accessories_v26 as acc
import r37_parts as Beacon
import r42_parts as Cartographer
import r43_c28_mechanical as M
import r43_swept_feed as F
from audit_c28_mechanical_r43 import quick_overlap
from build_cpap_outlet_r43 import print_oriented
from build_rvms_review_r43 import HOTEND_NAMES, difference, withdrawal
from cfd_provenance_r43 import digest

NOZZLE_Y = 22.7
ZONE = M.box(-10, 10, 3, 16, -79, -65)


def rear_air(params):
    # Same extended loft and mouth trim as the shell's passage, so the fill meets the lip exactly
    # (a flush, differently lofted mouth left knife-edge slivers at the slot corners).
    xs = (-F.HALF_WIDTH, -6.0, -3.0, 0.0, 3.0, 6.0, F.HALF_WIDTH)
    loft = cq.Solid.makeLoft([F.profile(x, 0.7, params["roof_raise_mm"], params["mouth_height_mm"],
                                        params["angle_deg"], params["floor_reference_height_mm"]) for x in xs])
    return loft.intersect(F.mouth_keep(params["angle_deg"]))


def fill(p22, params, exit_x, yaw_deg):
    y_exit = F.mouth(exit_x).y
    t = math.tan(math.radians(yaw_deg))
    # Plan line through (exit_x, y_exit) heading forward-inward; fill everything outboard of it.
    y_far, y_near = y_exit - (12.0 - exit_x) / t, y_exit + exit_x / t
    # Inboard edge: the yawed line from (12, y_far) to the centreline at y_near.
    plan = cq.Workplane("XY").polyline([(12.0, y_far), (0.0, y_near), (0.0, 30.0), (12.0, 30.0)]).close()
    prism = plan.extrude(20.0).translate((0, 0, -80.0)).val()
    right = prism.intersect(rear_air(params)).cut(p22.copy())
    return right, right.mirror("YZ")


def build(name, exit_x, yaw_deg, source_name):
    if Path(name).name != name or not name.startswith("review_") or Path(source_name).name != source_name:
        raise ValueError("Use a new review_* name and a source folder name")
    if not (3.0 <= exit_x <= 8.0 and 10.0 <= yaw_deg <= 45.0):
        raise ValueError("Bounded to exit |X| 3-8 mm and yaw 10-45 degrees")
    root = acc.WORK / "swept_feed"
    out, source, baseline = root / name, root / source_name, root / "userP21_flow_neutral_v5d"
    if out.exists():
        raise FileExistsError(out)
    checks = json.loads((source / "checks.json").read_text())
    params = checks["rear_slot"]
    p22 = cq.Shape.importBrep(str(source / "p22.brep"))
    released = cq.Shape.importBrep(str(baseline / "p22.brep"))
    p21 = cq.Shape.importBrep(str(source / "p21.brep"))
    right, left = fill(p22, params, exit_x, yaw_deg)
    fused = p22.copy().fuse(right.copy(), left.copy()).clean()
    if not fused.isValid():
        fused = p22.copy().fuse(right.copy(), left.copy(), tol=1e-4).clean()
    candidate = M.checked(fused, name)
    added = right.Volume() + left.Volume()
    grown = candidate.Volume() - p22.Volume()
    if added < 1.0 or abs(grown - added) > .02 or len(candidate.Shells()) != 1:
        raise ValueError(f"Fill did not fuse cleanly: added {added}, grew {grown}")
    symmetry = difference(candidate, candidate.mirror("YZ"))
    outside = difference(candidate.copy().cut(ZONE.copy()), p22.copy().cut(ZONE.copy()))
    bb = candidate.BoundingBox()
    if bb.zmin < -77.851 or symmetry > .02 or outside > .01:
        raise ValueError(f"Limit failure: zmin {bb.zmin}, symmetry {symmetry}, outside zone {outside}")
    scene_path = acc.WORK / "r43_scene" / "manifest.json"
    scene = json.loads(scene_path.read_text())
    tools = {n: cq.Shape.importBrep(str(scene_path.parent / f)) for n, f in scene["variants"]["Bambu"]["parts"]}
    overlaps = {n: quick_overlap(candidate.copy(), t.copy()) for n, t in tools.items()}
    if max(overlaps.values()) > 1e-4 or quick_overlap(candidate.copy(), p21.copy()) > 1e-4:
        raise ValueError(f"Assembly interference: {overlaps}")
    mounted = {}
    for label, solid in zip(HOTEND_NAMES, tools["hotend"].Solids()):
        a, b = released.distance(solid), candidate.distance(solid)
        if b < a - .001:
            raise ValueError(f"{label} mounted gap decreases: {a} -> {b}")
        mounted[label] = {"released_mm": a, "candidate_mm": b}
    probes = {}
    for label, probe in (("Beacon", Beacon.beacon()[3]), ("Cartographer", Cartographer.cartographer())):
        a, b = p22.distance(probe), candidate.distance(probe)
        if b < a - .005:
            raise ValueError(f"{label} clearance decreases: {a} -> {b}")
        probes[label] = {"source_mm": a, "candidate_mm": b}
    print(f"{name}: fill {added:.2f} mm3; solid, limits, mounted and probe gaps passed; checking withdrawal", flush=True)
    motion = withdrawal(released, candidate, tools["hotend"])
    y_exit = F.mouth(exit_x).y
    report = {
        "status": "GEOMETRY_SCREENED_SEPARATE_CFD_CANDIDATE", "source": source_name, "rear_slot": params,
        "side_rake": checks.get("side_rake"),
        "rear_converge": {"exit_abs_x_mm": exit_x, "exit_y_mm": y_exit, "yaw_deg": yaw_deg,
                          "approach_angles_deg_0_front": [180 - yaw_deg, 180 + yaw_deg],
                          "edge_lines_cross_centreline_y_mm": y_exit + exit_x / math.tan(math.radians(yaw_deg)),
                          "mouth_width_mm": [2 * exit_x, 2 * F.HALF_WIDTH]},
        "source_sha256": {str(p.relative_to(acc.WORK)): digest(p) for p in (
            source / "p22.brep", source / "p21.brep", baseline / "p22.brep", scene_path)},
        "generator_sha256": {Path(__file__).name: digest(Path(__file__)), Path(F.__file__).name: digest(Path(F.__file__))},
        "fill_mm3": added, "mirror_difference_mm3": symmetry, "outside_rear_zone_difference_mm3": outside,
        "lowest_z_mm": bb.zmin, "mounted_gap_mm": mounted, "probe_gaps_mm": probes,
        "withdrawal": motion, "hotend_overlap_mm3": overlaps,
        "constraint": "Adds material only inside the rear passage's existing air. Solid end walls, no vanes.",
        "limitations": "Not thermally or physically print-qualified.",
    }
    out.mkdir()
    candidate.exportBrep(str(out / "p22.brep"))
    p21.exportBrep(str(out / "p21.brep"))
    cq.exporters.export(candidate, str(out / "p22.step"))
    restored = cq.importers.importStep(str(out / "p22.step")).val()
    report["step_roundtrip_difference_mm3"] = difference(candidate, restored)
    if report["step_roundtrip_difference_mm3"] > .01:
        raise ValueError("STEP round trip changes the solid")
    cq.exporters.export(print_oriented(candidate), str(out / "p22_print_oriented.stl"), tolerance=.01,
                        angularTolerance=.1)
    report["outputs_sha256"] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
    (out / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(out), "rear_converge": report["rear_converge"], "fill_mm3": added}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--exit-x", type=float, required=True)
    parser.add_argument("--yaw", type=float, required=True)
    parser.add_argument("--source", default="review_rvms_fr1")
    a = parser.parse_args()
    build(a.name, a.exit_x, a.yaw, a.source)
