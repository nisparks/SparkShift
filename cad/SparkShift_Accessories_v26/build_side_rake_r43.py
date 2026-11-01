"""Rake each side jet passage's front end wall forward (the opposite of RFT's toe-in), on the RVMS P22.

python build_side_rake_r43.py review_rvms_fr1 --inner-y 25.15 --exit-y 27.6
python build_side_rake_r43.py review_rvms_fr2 --inner-y 23.4 --exit-y 25.85
The passage (|X| 10.2-12.6) is filled ahead of a vertical plane from (|X| 12.65, inner-y) to (|X| 10.15, exit-y):
air entering from the chamber is turned forward as it runs inboard, and with exit-y < 27.55 the opening's front end
moves aft. Only the side passages change. The fill is inside today's passage air, so it is outboard of |X| 10.2 and
above Z -77.85; its exposed face overhangs no more than 45 degrees when printed back face down.
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
import r43_parts as R43
from audit_c28_mechanical_r43 import quick_overlap
from build_cpap_outlet_r43 import print_oriented
from build_rvms_review_r43 import HOTEND_NAMES, difference, withdrawal
from cfd_provenance_r43 import digest

X0 = R43.WALL_X[0]
SOURCE = "aim_v5d_RVMS"


def passage_air(p22):
    space = M.box(X0, 12.6, 14.0, 29.5, R43.UNDER - .1, -70.5).cut(p22.copy())
    return next(s for s in space.Solids() if s.isInside(cq.Vector(11.0, 23.0, -75.0)))


def rake(p22, inner_y, exit_y):
    z0, z1 = R43.UNDER - .2, R43.ROOF + R43.BELL_R + 1.0
    plan = cq.Workplane("XY").polyline([(X0 - .05, exit_y), (12.65, inner_y), (12.65, 29.6), (X0 - .05, 29.6)]).close()
    body = plan.extrude(z1 - z0).translate((0, 0, z0)).val().intersect(passage_air(p22))
    return body, body.mirror("YZ")


def build(name, inner_y, exit_y):
    if Path(name).name != name or not name.startswith("review_"):
        raise ValueError("Use a new review_* experiment name")
    if not (20.0 <= inner_y < exit_y <= 27.6):
        raise ValueError("The rake must lean forward inboard and stay within the opening")
    lean = math.degrees(math.atan2(exit_y - inner_y, 12.65 - (X0 - .05)))
    if lean > 45.5:
        raise ValueError(f"Face would overhang more than 45 degrees when printed back face down ({lean:.1f})")
    root = acc.WORK / "swept_feed"
    out = root / name
    if out.exists():
        raise FileExistsError(out)
    source, baseline = root / SOURCE, root / "userP21_flow_neutral_v5d"
    p22 = cq.Shape.importBrep(str(source / "p22.brep"))
    released = cq.Shape.importBrep(str(baseline / "p22.brep"))
    p21 = cq.Shape.importBrep(str(source / "p21.brep"))
    right, left = rake(p22, inner_y, exit_y)
    candidate = M.checked(p22.copy().fuse(right.copy(), left.copy(), tol=1e-4).clean(), name)
    added = right.Volume() + left.Volume()
    grown = candidate.Volume() - p22.Volume()
    if abs(grown - added) > .01 or len(candidate.Shells()) != 1:
        raise ValueError(f"Fill did not fuse cleanly: added {added}, grew {grown}")
    symmetry = difference(candidate, candidate.mirror("YZ"))
    bb = candidate.BoundingBox()
    inboard = candidate.copy().intersect(M.box(-X0 + 1e-3, X0 - 1e-3, 14.0, 30.0, -79.0, -70.0))
    if bb.zmin < -77.851 or symmetry > .02 or difference(inboard, p22.copy().intersect(
            M.box(-X0 + 1e-3, X0 - 1e-3, 14.0, 30.0, -79.0, -70.0))) > .01:
        raise ValueError(f"Limit failure: zmin {bb.zmin}, symmetry {symmetry}")
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
    opening = {}
    for side, x in (("right", X0 + .02), ("left", -X0 - .02)):
        plane = M.box(x - .01, x + .01, 12.0, 30.0, R43.UNDER - .05, R43.ROOF + 4.0)
        opening[side] = {"before_mm2": plane.copy().cut(p22.copy()).Volume() / .02,
                         "after_mm2": plane.copy().cut(candidate.copy()).Volume() / .02}
    report = {
        "status": "GEOMETRY_SCREENED_SEPARATE_CFD_CANDIDATE", "source": SOURCE,
        "side_rake": {"inner_y_at_x12p65": inner_y, "exit_y_at_slot_face": exit_y, "lean_deg": lean},
        "rear_slot": json.loads((source / "checks.json").read_text()).get("rear_slot",
                                                                          {"mouth_height_mm": 2.0, "angle_deg": 28,
                                                                           "floor_reference_height_mm": .9,
                                                                           "roof_raise_mm": 3.0}),
        "source_sha256": {str(p.relative_to(acc.WORK)): digest(p) for p in (
            source / "p22.brep", source / "p21.brep", baseline / "p22.brep", scene_path)},
        "generator_sha256": {Path(__file__).name: digest(Path(__file__))},
        "fill_mm3": added, "mirror_difference_mm3": symmetry, "lowest_z_mm": bb.zmin,
        "slot_face_opening_mm2": opening, "mounted_gap_mm": mounted, "probe_gaps_mm": probes,
        "withdrawal": motion, "hotend_overlap_mm3": overlaps,
        "constraint": "Adds material only inside each side passage's existing air, outboard of |X| 10.2. No vanes.",
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
    print(json.dumps({"output": str(out), "side_rake": report["side_rake"], "opening": opening}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--inner-y", type=float, required=True)
    parser.add_argument("--exit-y", type=float, required=True)
    a = parser.parse_args()
    build(a.name, a.inner_y, a.exit_y)
