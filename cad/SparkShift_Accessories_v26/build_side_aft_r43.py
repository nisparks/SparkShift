"""Move each side jet's opening aft: open the feed floor behind it and rake its front end back (on design A).

python build_side_aft_r43.py review_a_aftc --floor chamfer --y-aft 16.8 --inner-y 23.45 --exit-y 25.95
python build_side_aft_r43.py review_a_aftf --floor flat --y-aft 16.5 --inner-y 21.95 --exit-y 24.45

The aft end of each side opening is the feed's thin descending floor (Z -77.2 at Y 22 rising to the passage roof
at Y ~16-17). Inside the side passage only (|X| 10.2-12.65), that shell is cut back to a new floor at the existing
floor height (Z -77.2, 0.65 mm above the -77.85 underside), closed by new material below the old shell:
- chamfer: the pocket's aft end and its new underside run at 45 degrees from the old shell's top, so it prints
  without support back face down; the shift is smaller.
- flat: the floor runs flat to y-aft with a vertical aft wall; its 0.8 x ~3 mm underside needs support.
The front end wall is then raked (build_side_rake_r43.rake) so the opening moves aft rather than only growing.
All new material is outboard of |X| 10.2, at or above Z -77.85, and outside the hotend's mounted and withdrawal
envelope (checked). No vanes.
"""
import argparse
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np

import build_and_verify_accessories_v26 as acc
import r37_parts as Beacon
import r42_parts as Cartographer
import r43_c28_mechanical as M
from audit_c28_mechanical_r43 import quick_overlap
from build_cpap_outlet_r43 import print_oriented
from build_rvms_review_r43 import HOTEND_NAMES, difference, withdrawal
from build_side_rake_r43 import rake
from cfd_provenance_r43 import digest

X0, X_OUT, WALL = 10.2, 12.65, .8
FLOOR_TOP, UNDER, TOP = -77.2, -77.85, -74.5
PASSAGE_POINT = cq.Vector(11.0, 23.0, -75.0)
ZONE = (X0 - .06, X_OUT + WALL + .05, 11.0, 30.0, UNDER - .01, -70.0)


def yz_prism(points, x0, x1):
    return cq.Workplane("YZ").polyline(points).close().extrude(x1 - x0).translate((x0, 0, 0)).val()


def pocket_and_fill(p22, floor, y_aft):
    """Right-hand (+X) pocket air and the new material that closes it from below."""
    rise = TOP - FLOOR_TOP
    if floor == "chamfer":
        air = yz_prism([(y_aft, TOP), (23.0, TOP), (23.0, FLOOR_TOP), (y_aft + rise, FLOOR_TOP)], X0 - .05, X_OUT)
        y_face = y_aft - WALL * math.sqrt(2)
        bound = yz_prism([(y_face, TOP), (30.0, TOP), (30.0, UNDER), (y_face + TOP - UNDER, UNDER)],
                         X0, X_OUT + WALL)
    else:
        air = M.box(X0 - .05, X_OUT, y_aft, 23.0, FLOOR_TOP, TOP)
        bound = M.box(X0, X_OUT + WALL, y_aft - WALL, 30.0, UNDER, TOP)
    region = M.box(X0, X_OUT + WALL, y_aft - 8.0, 23.0, UNDER, TOP)
    pieces = region.cut(p22.copy()).Solids()
    under = [s for s in pieces if not s.isInside(PASSAGE_POINT) and not s.isInside(cq.Vector(12.0, 21.0, -76.0))]
    fill = None
    for s in under:
        part = s.intersect(bound.copy())
        if part.Solids():
            fill = part if fill is None else fill.fuse(part)
    return air, fill


def fuse(a, *others):
    out = a.copy().fuse(*[o.copy() for o in others]).clean()
    if not out.isValid():
        out = a.copy().fuse(*[o.copy() for o in others], tol=1e-4).clean()
    return out


def slot_opening(shape):
    """Air area and Y extent of the +X side opening on a thin slab just outboard of the slot face."""
    slab = M.box(X0 + .01, X0 + .03, 12.0, 30.0, UNDER, -73.0)
    air = [s for s in slab.cut(shape.copy()).Solids() if s.isInside(cq.Vector(X0 + .02, 21.5, -75.8))]
    if len(air) != 1:
        raise ValueError("Side opening not found on the slot-face slab")
    air = air[0]
    bb = air.BoundingBox()
    return {"area_mm2": round(air.Volume() / .02, 2), "y_mm": [round(bb.ymin, 2), round(bb.ymax, 2)],
            "area_centroid_y_mm": round(air.Center().y, 2)}


def overhang_mm2(shape):
    v, t = print_oriented(shape).tessellate(.02, .2)
    p = np.array([x.toTuple() for x in v])
    tri = p[np.array(t)]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    nz = n[:, 2] / np.maximum(2 * area, 1e-12)
    z = tri[:, :, 2].mean(1)
    return float(area[(nz < -math.cos(math.radians(45))) & (z > p[:, 2].min() + .05)].sum())


def build(name, floor, y_aft, inner_y, exit_y, source_name):
    if Path(name).name != name or not name.startswith("review_") or Path(source_name).name != source_name:
        raise ValueError("Use a new review_* name and a source folder name")
    if not (15.5 <= y_aft <= 20.0):
        raise ValueError("y-aft bounded to 15.5-20 mm")
    lean = 0.0 if inner_y is None else math.degrees(math.atan2(exit_y - inner_y, X_OUT - (X0 - .05)))
    if inner_y is not None and (not (20.0 <= inner_y < exit_y <= 27.6) or lean > 45.5):
        raise ValueError(f"Front rake must lean forward inboard at <= 45 degrees ({lean:.1f})")
    root = acc.WORK / "swept_feed"
    out, source, baseline = root / name, root / source_name, root / "userP21_flow_neutral_v5d"
    if out.exists():
        raise FileExistsError(out)
    checks = json.loads((source / "checks.json").read_text())
    p22 = cq.Shape.importBrep(str(source / "p22.brep"))
    released = cq.Shape.importBrep(str(baseline / "p22.brep"))
    p21 = cq.Shape.importBrep(str(source / "p21.brep"))

    air, fill = pocket_and_fill(p22, floor, y_aft)
    stage = fuse(p22, fill, fill.mirror("YZ")).cut(air.copy()).cut(air.mirror("YZ")).clean()
    if inner_y is None:
        candidate = M.checked(stage, name)  # keep the source's front edge; the opening only grows aft
    else:
        right, left = rake(stage, inner_y, exit_y)
        candidate = M.checked(fuse(stage, right, left), name)
    if len(candidate.Shells()) != 1:
        raise ValueError("Candidate is not one closed shell")

    symmetry = difference(candidate, candidate.mirror("YZ"))
    zone_r = M.box(*ZONE)
    zone_l = zone_r.mirror("YZ")
    outside = difference(candidate.copy().cut(zone_r.copy()).cut(zone_l.copy()),
                         p22.copy().cut(zone_r.copy()).cut(zone_l.copy()))
    added = candidate.copy().cut(p22.copy())
    inboard = added.copy().intersect(M.box(-X0 + 1e-3, X0 - 1e-3, 0, 40, -80, -60))
    inboard_mm3 = sum(s.Volume() for s in inboard.Solids())
    bb = candidate.BoundingBox()
    if bb.zmin < UNDER - .001 or symmetry > .02 or outside > .01 or inboard_mm3 > .01:
        raise ValueError(f"Limit failure: zmin {bb.zmin}, symmetry {symmetry}, outside {outside}, inboard {inboard_mm3}")

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
    opening = {"source": slot_opening(p22), "candidate": slot_opening(candidate)}
    print(f"{name}: solid, limits, mounted and probe gaps passed; opening {opening}; checking withdrawal", flush=True)
    motion = withdrawal(released, candidate, tools["hotend"])
    report = {
        "status": "GEOMETRY_SCREENED_SEPARATE_CFD_CANDIDATE", "source": source_name,
        "rear_slot": checks["rear_slot"], "rear_converge": checks.get("rear_converge"),
        "side_rake": {"inner_y_at_x12p65": inner_y, "exit_y_at_slot_face": exit_y, "lean_deg": lean},
        "side_aft": {"floor": floor, "y_aft_mm": y_aft, "floor_top_z_mm": FLOOR_TOP, "pocket_top_z_mm": TOP,
                     "x_mm": [X0, X_OUT], "outer_wall_mm": WALL},
        "slot_face_opening": opening,
        "overhang_over_45deg_mm2": {"source": round(overhang_mm2(p22), 1),
                                    "candidate": round(overhang_mm2(candidate), 1)},
        "source_sha256": {str(p.relative_to(acc.WORK)): digest(p) for p in (
            source / "p22.brep", source / "p21.brep", baseline / "p22.brep", scene_path)},
        "generator_sha256": {Path(__file__).name: digest(Path(__file__))},
        "volume_change_mm3": candidate.Volume() - p22.Volume(), "mirror_difference_mm3": symmetry,
        "outside_side_zone_difference_mm3": outside, "added_inboard_of_x10p2_mm3": inboard_mm3,
        "lowest_z_mm": bb.zmin, "mounted_gap_mm": mounted, "probe_gaps_mm": probes,
        "withdrawal": motion, "hotend_overlap_mm3": overlaps,
        "constraint": "Changes only the side passages outboard of |X| 10.2. No vanes.",
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
    print(json.dumps({"output": str(out), "side_aft": report["side_aft"], "opening": opening,
                      "overhang": report["overhang_over_45deg_mm2"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--floor", choices=("chamfer", "flat"), required=True)
    parser.add_argument("--y-aft", type=float, required=True)
    parser.add_argument("--inner-y", type=float, help="front rake start; omit with --exit-y for no rake")
    parser.add_argument("--exit-y", type=float)
    parser.add_argument("--source", default="review_fr1_rc24m")
    a = parser.parse_args()
    if (a.inner_y is None) != (a.exit_y is None):
        parser.error("give both --inner-y and --exit-y, or neither")
    build(a.name, a.floor, a.y_aft, a.inner_y, a.exit_y, a.source)
