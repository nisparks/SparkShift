"""Build a separately named RVMS rear-slot experiment without touching the released part.

python build_rvms_review_r43.py review_rvms_a40 --angle 40 --height 2
Requires the frozen RVM and v5d session BREPs. Splices only the rear outlet region;
records the actual passage, source hashes and clearance checks before exporting.
"""
import argparse
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np

import build_and_verify_accessories_v26 as acc
import fast_geometry as G
import r37_parts as Beacon
import r42_parts as Cartographer
import r43_c28_mechanical as M
import r43_swept_feed as F
from audit_c28_mechanical_r43 import quick_overlap
from audit_swept_feed_cleanup_r43 import wall_screen
from build_cpap_outlet_r43 import print_oriented
from cfd_provenance_r43 import digest

ZONE = M.box(-10, 10, 3, 16, -75, -65)
HOTEND_NAMES = ("ceramic block", "heater cradle", "bail", "nozzle and heatsink", "silicone sock", "magnet")


def difference(a, b):
    values = []
    # Fuzzy OCC booleans can modify shared input topology. Never audit a mutated reference.
    for shape in (a.copy().cut(b.copy()), b.copy().cut(a.copy())):
        if not shape.isValid() or any(s.Volume() < -1e-5 for s in shape.Solids()):
            raise ValueError("Invalid or inverted boolean difference; cannot use its volume as evidence")
        values.append(sum(max(0.0, s.Volume()) for s in shape.Solids()))
    return max(values)


def withdrawal(reference, candidate, hotend):
    old, new = [G.index_of(s) for s in reference.Solids()], [G.index_of(s) for s in candidate.Solids()]
    parts = [[G.index_of(s)] for s in hotend.Solids()]
    rows = {name: {"reference_min_mm": None, "candidate_min_mm": None} for name in HOTEND_NAMES}
    for retreat in np.arange(0, 60.01, .5):
        for name, tool in zip(HOTEND_NAMES, parts):
            before = G.min_distance(old, tool, offset_a=(0, -float(retreat), 0), cutoff=50)
            after = G.min_distance(new, tool, offset_a=(0, -float(retreat), 0), cutoff=50)
            if before is None and after is None:
                continue
            a, b = before[0] if before else 50, after[0] if after else 50
            if b < a - .005:
                raise ValueError(f"{name} at retreat {retreat}: gap decreases {a:.6f} -> {b:.6f} mm")
            for key, value in (("reference_min_mm", a), ("candidate_min_mm", b)):
                prev = rows[name][key]
                rows[name][key] = value if prev is None else min(prev, value)
    return {"length_mm": 60, "step_mm": .5, "axis": "-Y", "parts": rows,
            "limitation": "Sampled rigid-body withdrawal, not continuous-motion or thermal qualification"}


def build(name, height, angle):
    if not name or Path(name).name != name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in name):
        raise ValueError("Use a simple new experiment name")
    if not math.isfinite(height) or not .9 <= height <= 2.0 or not math.isfinite(angle) or not 28 <= angle <= 44:
        raise ValueError("This review is bounded to 0.9-2.0 mm height and 28-44 degrees")
    root = acc.WORK / "swept_feed"
    out = root / name
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite an experiment: {out}")
    source = root / "aim_v5d_RVM"
    baseline = root / "userP21_flow_neutral_v5d"
    p22 = cq.Shape.importBrep(str(source / "p22.brep"))
    released = cq.Shape.importBrep(str(baseline / "p22.brep"))
    p21 = cq.Shape.importBrep(str(source / "p21.brep"))
    base_file = acc.WORK / "cfd" / "p22_r43.brep"
    base = cq.Shape.importBrep(str(base_file))
    kw = dict(roof_raise=3, remove_rear_mounts=True, conformal_outlet=True, clear_feed_intrusions=True)
    reference = F.p22(base.copy(), mouth_height=.9, angle_deg=28, **kw)
    trial = F.p22(base.copy(), mouth_height=height, floor_reference_height=.9, angle_deg=angle, **kw)
    local_error = difference(p22.copy().intersect(ZONE.copy()), reference.copy().intersect(ZONE.copy()))
    if local_error > .01:
        raise ValueError(f"Source has unexpected edits inside the rear-slot zone: {local_error} mm3")
    candidate = M.checked(p22.copy().cut(ZONE.copy()).fuse(
        trial.copy().intersect(ZONE.copy()), tol=1e-4).clean(), name)
    outside_error = difference(candidate.copy().cut(ZONE.copy()), p22.copy().cut(ZONE.copy()))
    inside_error = difference(candidate.copy().intersect(ZONE.copy()), trial.copy().intersect(ZONE.copy()))
    local = candidate.copy().intersect(ZONE.copy())
    symmetry_error = difference(local, local.mirror("YZ"))
    if max(outside_error, inside_error, symmetry_error) > .01:
        raise ValueError(f"Splice or symmetry failure: {outside_error}, {inside_error}, {symmetry_error}")
    if candidate.BoundingBox().zmin < -77.851 or len(candidate.Shells()) != 1:
        raise ValueError("Height limit or shell count failure")
    params = {"mouth_height_mm": height, "floor_reference_height_mm": .9,
              "angle_deg": angle, "roof_raise_mm": 3.0}
    airway = F.nozzle(False, 3, height, angle, True, .9)
    old_outer, new_outer = F.nozzle(True, 3, .9, 28, True), F.nozzle(True, 3, height, angle, True, .9)
    if quick_overlap(candidate.copy(), airway.copy()) > 1e-4:
        raise ValueError("Candidate obstructs its declared rear airway")
    probe_gaps = {}
    for label, probe in (("Beacon", Beacon.beacon()[3]), ("Cartographer", Cartographer.cartographer())):
        a, b = old_outer.distance(probe), new_outer.distance(probe)
        if b < a - .005:
            raise ValueError(f"{label} clearance decreases: {a} -> {b}")
        probe_gaps[label] = {"reference_mm": a, "candidate_mm": b}
    scene_path = acc.WORK / "r43_scene" / "manifest.json"
    scene = json.loads(scene_path.read_text())
    tools = {n: cq.Shape.importBrep(str(scene_path.parent / f)) for n, f in scene["variants"]["Bambu"]["parts"]}
    overlaps = {n: quick_overlap(candidate.copy(), tool.copy()) for n, tool in tools.items()}
    if max(overlaps.values()) > 1e-4 or quick_overlap(candidate.copy(), p21.copy()) > 1e-4:
        raise ValueError(f"Assembly interference: {overlaps}")
    mounted = {}
    for label, solid in zip(HOTEND_NAMES, tools["hotend"].Solids()):
        a, b = released.distance(solid), candidate.distance(solid)
        if b < a - .001:
            raise ValueError(f"{label} mounted gap decreases: {a} -> {b}")
        mounted[label] = {"released_mm": a, "candidate_mm": b}
    print(f"{name}: solid, local splice, probe and mounted gaps passed; checking withdrawal", flush=True)
    motion = withdrawal(released, candidate, tools["hotend"])
    feed_air = F.air(3, height, angle, .9)
    walls = wall_screen(candidate, feed_air, F.main_channel_air(), angle=angle)
    if not all(s.isValid() for s in (p22, released, p21, reference, trial, candidate)):
        raise ValueError("An input or result became invalid during qualification")
    report = {
        "status": "GEOMETRY_SCREENED_SEPARATE_CFD_CANDIDATE",
        "rear_slot": params, "source": source.name,
        "source_sha256": {str(p.relative_to(acc.WORK)): digest(p) for p in (
            source / "p22.brep", source / "p21.brep", baseline / "p22.brep", base_file, scene_path)},
        "generator_sha256": {p.name: digest(p) for p in (Path(__file__), Path(F.__file__))},
        "valid_single_solid_shell": True, "source_local_difference_mm3": local_error,
        "outside_edit_zone_difference_mm3": outside_error, "splice_difference_mm3": inside_error,
        "rear_slot_mirror_difference_mm3": symmetry_error, "lowest_z_mm": candidate.BoundingBox().zmin,
        "volume_mm3": candidate.Volume(), "source_volume_mm3": p22.Volume(),
        "mounted_gap_mm": mounted, "probe_gaps_mm": probe_gaps, "withdrawal": motion,
        "hotend_overlap_mm3": overlaps, "wall_screen": walls,
        "side_jet_constraint": "Side jets and all material outside X+-10, Y3..16, Z-75..-65 are unchanged from RVM",
        "limitations": "No new hardware or metal. No louvers/vanes. Not thermally or physically print-qualified.",
    }
    out.mkdir()
    candidate.exportBrep(str(out / "p22.brep"))
    p21.exportBrep(str(out / "p21.brep"))
    airway.exportBrep(str(out / "rear_air.brep"))
    cq.exporters.export(candidate, str(out / "p22.step"))
    restored = cq.importers.importStep(str(out / "p22.step")).val()
    report["step_roundtrip_difference_mm3"] = difference(candidate, restored)
    if report["step_roundtrip_difference_mm3"] > .01:
        raise ValueError("STEP round trip changes the solid")
    cq.exporters.export(print_oriented(candidate), str(out / "p22_print_oriented.stl"), tolerance=.01,
                        angularTolerance=.1)
    report["outputs_sha256"] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
    (out / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(out), "rear_slot": params, "volume_mm3": candidate.Volume(),
                      "probe_gaps": probe_gaps, "status": report["status"]}), flush=True)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--height", type=float, required=True)
    parser.add_argument("--angle", type=float, required=True)
    args = parser.parse_args()
    build(args.name, args.height, args.angle)
