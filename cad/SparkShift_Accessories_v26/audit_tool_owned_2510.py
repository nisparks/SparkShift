"""Second-pass geometric audit of the one-piece, approved-position Bambu toolhead."""

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import trimesh

from build_modular_toolhead import ROOT, STEP, STL, HOTEND_AXES, box, cylinder_y, load, volume, primitives
from build_tool_owned_2510_review import cylinder_x


def compound(shapes):
    return cq.Compound.makeCompound(list(shapes))


@lru_cache(maxsize=4096)
def bounds(shape):
    b = shape.BoundingBox()
    return [b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax]


def boxes_overlap(a, b):
    return all(a[2 * i + 1] >= b[2 * i] and b[2 * i + 1] >= a[2 * i] for i in range(3))


@lru_cache(maxsize=4096)
def solid_bounds(shape):
    return [(s, bounds(s)) for s in shape.Solids()]


def overlaps(shape, targets, tolerance=0.001):
    hits = {}
    b = bounds(shape)
    for name, target in targets.items():
        t = bounds(target)
        if not boxes_overlap(b, t):
            continue
        v = sum(volume(a.intersect(c)) for a, ab in solid_bounds(shape)
                for c, cb in solid_bounds(target) if boxes_overlap(ab, cb))
        if v > tolerance:
            hits[name] = v
    return hits


def audit(core_path):
    print("Loading tool and stationary references", flush=True)
    core = cq.importers.importStep(str(core_path)).val()
    body = load("Tool2510_One_Piece_Bambu_Toolhead_REVIEW")
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    hardware = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW").Solids()
    fan = box(11.45, 21.45, 13, 38, -47.8, -22.8)
    fan_screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")
    fan_inserts = load("Tool2510_Two_Inner_Entry_L3_Heatsets_REVIEW")
    actual_fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
    if len(hardware) != 8:
        raise ValueError("One-piece version must not contain shelf clamp hardware")
    screws = compound(hardware[i] for i in (1, 4, 7))
    inserts = compound(hardware[i] for i in (0, 3, 6))
    washers = compound(hardware[i] for i in (2, 5))
    parts = dict(Body=body, Hotend=hotend, Screws=screws,
                 Inserts=inserts, Washers=washers, Fan=fan,
                 Fan_Screws=fan_screws, Fan_Inserts=fan_inserts)
    references = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
        "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount",
        "P24_EBB42_Controller_Mount", "P25_SparkShift_3010_Dock",
    )}
    report = {
        "status": "CAD_AUDIT_ONLY_NOT_PRINT_THERMAL_OR_FULL_MACHINE_QUALIFICATION",
        "fan_center_mm": [16.45, 25.5, -35.3],
        "failures": [],
        "findings_requiring_physical_confirmation": [],
        "parts": {},
    }
    for name, shape in parts.items():
        report["parts"][name] = {"valid": shape.isValid(), "solids": len(shape.Solids()),
                                 "volume_mm3": volume(shape), "bounds_mm": bounds(shape)}
        if not shape.isValid():
            report["failures"].append(f"Invalid {name}")
    report["pairwise_intersections_mm3"] = []
    print("Checking part pairs", flush=True)
    for i, (name, shape) in enumerate(parts.items()):
        for other, target in list(parts.items())[i + 1:]:
            pair_shape = actual_fan if name == "Fan" else shape
            pair_target = actual_fan if other == "Fan" else target
            v = sum(overlaps(pair_shape, {other: pair_target}).values())
            if v <= 0.001:
                continue
            pilot_fit = {name, other} in ({"Body", "Inserts"}, {"Body", "Fan_Inserts"})
            thread_fit = {name, other} in ({"Screws", "Inserts"}, {"Fan_Screws", "Fan_Inserts"})
            intentional = pilot_fit or thread_fit
            report["pairwise_intersections_mm3"].append(
                {"a": name, "b": other, "volume_mm3": v,
                 "classification": ("Heatset interference in undersized pilot" if pilot_fit else
                                    "Nominal screw/insert thread engagement" if thread_fit else "UNEXPECTED")})
            if not intentional:
                report["failures"].append(f"Unexpected intersection {name}/{other}: {v}")
    print("Checking stationary references", flush=True)
    report["tool_to_stationary_intersections_mm3"] = {
        n: overlaps(s, dict(Core=core, **references)) for n, s in parts.items()
    }
    if any(report["tool_to_stationary_intersections_mm3"].values()):
        report["failures"].append("Tool intersects stationary reference geometry")
    report["inherited_reference_intersections_mm3"] = []
    for i, (name, shape) in enumerate(references.items()):
        for other, target in list(references.items())[i + 1:]:
            v = volume(shape.intersect(target))
            if v > 0.001:
                report["inherited_reference_intersections_mm3"].append(
                    {"a": name, "b": other, "volume_mm3": v, "changed": False})
    report["printed_meshes"] = {}
    for name, filename in (("Body", "Tool2510_One_Piece_Bambu_Toolhead_REVIEW.stl"),):
        mesh = trimesh.load_mesh(STL / filename)
        check = {"watertight": bool(mesh.is_watertight), "winding_consistent": bool(mesh.is_winding_consistent),
                 "components": len(mesh.split(only_watertight=False))}
        report["printed_meshes"][name] = check
        if not check["watertight"] or not check["winding_consistent"] or check["components"] != 1:
            report["failures"].append(f"Invalid mesh {name}")

    print("Checking cleanup deltas and fastener access", flush=True)
    old = load("16_Rearward_Tool_Owned_2510_45mm_REVIEW").Solids()
    if abs(volume(old[0]) - 5354.130) > 0.001 or abs(volume(old[1]) - 8128.396) > 0.001:
        raise ValueError("Revision16 reference component order differs from the reviewed snapshot")
    report["revision16_to18_body_mm3"] = {
        "previous_total_print_volume": volume(old[0]) + volume(old[1]),
        "current_print_volume": volume(body),
        "net_change": volume(body) - volume(old[0]) - volume(old[1])}
    report["approved_fan_unchanged"] = (
        all(abs(a - b) < 0.001 for a, b in zip(bounds(old[2]), bounds(actual_fan)))
        and volume(old[2].cut(actual_fan)) + volume(actual_fan.cut(old[2])) < 0.001)
    if not report["approved_fan_unchanged"]:
        report["failures"].append("Approved fan geometry changed")

    report["fastener_access"] = []
    tool_targets = dict(Body=body, Hotend=hotend, Fan=fan)
    fixed_hotend = compound(s for i, s in enumerate(hotend.Solids()) if i not in (3, 4))
    for x, z in HOTEND_AXES:
        report["fastener_access"].append(
            {"joint": f"Hotend {x}/{z}, detached tool with snap-in nozzle removed", "driver_diameter_mm": 3,
             "blocked_by": overlaps(cylinder_y(x, z, 7.2, 27.2, 1.5),
                                    dict(Body=body, Fixed_Hotend=fixed_hotend, Fan=fan))})
        report["fastener_access"].append(
            {"joint": f"Hotend heatset {x}/{z}, before hotend installation", "tool_diameter_mm": 4.4,
             "blocked_by": overlaps(cylinder_y(x, z, 37.9, 47.9, 2.2), dict(Body=body))})
    for y in (15.5, 35.5):
        report["fastener_access"].append(
            {"joint": f"Fan {y}", "driver_diameter_mm": 3,
             "blocked_by": overlaps(cylinder_x(y, -25.3, 21.6, 41.6, 1.5), tool_targets)})
        report["fastener_access"].append(
            {"joint": f"Fan heatset {y}, before hotend installation", "tool_diameter_mm": 4.4,
             "blocked_by": overlaps(cylinder_x(y, -25.3, -16, 6.8, 2.2), dict(Body=body))})
    for check in report["fastener_access"]:
        if check["blocked_by"]:
            report["failures"].append(f"Fastener/tool access blocked: {check}")

    report["assembly_sequence"] = (
        "Install heatsets before heating assembly/fan. Install the three heating-assembly screws "
        "with the snap-in nozzle removed, then install nozzle. Remove complete tool before nozzle service.")
    report["thread_engagement_mm"] = {"fan_M2_5x14_L3": 3,
                                      "hotend_M2_5x10_L4": 4}
    report["retaining_shoulder_thickness_mm"] = {"fan": 1, "hotend": 2.8}
    report["minimum_radial_heatset_wall_mm"] = 0.75
    report["hotend_full_seat_checks"] = []
    for x, z in HOTEND_AXES:
        surround = cylinder_y(x, z, 33.9, 37.9, 2.5).cut(cylinder_y(x, z, 33.9, 37.9, 1.75))
        missing = volume(surround.cut(body))
        report["hotend_full_seat_checks"].append({"axis_xz_mm": [x, z], "missing_surround_mm3": missing})
        if missing > 0.001:
            report["failures"].append(f"Missing hotend insert surround {x}/{z}")
    report["filament_path_obstruction_mm3"] = volume(
        body.intersect(
            cq.Solid.makeCylinder(0.9, 74.1, cq.Vector(0, 22.7, -26), cq.Vector(0, 0, 1))))
    if report["filament_path_obstruction_mm3"] > 0.001:
        report["failures"].append("Filament passage obstructed")
    stem_region = box(-16, 16, 10, 36, -17.2794, 50)
    original_stem = load("P17M_Reusable_Carrier_3010_REVIEW").intersect(stem_region).cut(
        references["P18_Tool_docking_backplate_3010"])
    stem = body.intersect(stem_region)
    # Direct boundary distances avoid unstable booleans between coincident STEP surfaces.
    stem_check = {"volume_difference_mm3": abs(volume(stem) - volume(original_stem)),
                  "tessellation_tolerance_mm": 0.15, "maximum_boundary_sample_distance_mm": 0,
                  "boundary_samples": 0}
    for source, target in ((stem, original_stem), (original_stem, stem)):
        vertices, _ = source.tessellate(0.15, 0.2)
        stem_check["boundary_samples"] += len(vertices)
        stem_check["maximum_boundary_sample_distance_mm"] = max(
            stem_check["maximum_boundary_sample_distance_mm"],
            max(cq.Vertex.makeVertex(*p.toTuple()).distance(target) for p in vertices))
    report["functional_stem_preservation"] = stem_check
    if (stem_check["volume_difference_mm3"] > 0.001
            or stem_check["maximum_boundary_sample_distance_mm"] > 0.001):
        report["failures"].append("Functional stem/guide/coupling geometry changed")
    report["backplate_lower_passage_obstruction_mm3"] = [
        volume(body.intersect(cylinder_y(x, -19.26, 31, 37, 2.28))) for x in (-6, 6)]
    if max(report["backplate_lower_passage_obstruction_mm3"]) > 0.001:
        report["failures"].append("Original P18 lower attachment passage obstructed")

    print("Checking gantry, electronics and sensor keepouts", flush=True)
    gantry_meta = json.loads((primitives.WORK / "gantry_meta.json").read_text())
    gantry_raw = primitives.load_brep_list(primitives.WORK / "gantry_cache.brep")
    gantry = {m["name"]: cq.Shape.cast(s) for m, (s, _) in zip(gantry_meta, gantry_raw)}
    accessory_hw = {name: cq.Shape.cast(shape) for name, shape in primitives.build_accessory_hardware()}
    beacon = [cq.Shape.cast(s).translate((0, 3.2, -75)) for s in
              primitives.load_step(primitives.SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")]
    top_keepout = beacon[1].intersect(box(-20, 20, -20, 20, -76.61, -56.61))
    carto = compound(cq.Shape.cast(s).rotate((0, 0, 0), (0, 0, 1), 180).translate(
        (0, -13.00701, -75)) for s in primitives.load_step(
            primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")[:100])
    ebb = compound(cq.Shape.cast(s).translate((-20, -20, 0)).rotate(
        (0, 0, 0), (0, 1, 0), 180).rotate((0, 0, 0), (1, 0, 0), 90).translate(
            (-1.248, -31.630, 6.5)) for s, _ in
        primitives.load_brep_list(primitives.WORK / "ebb42_cache.brep"))
    cable = cq.Shape.cast(primitives.build_sensor_cable())
    external = dict(gantry, **accessory_hw, Beacon_Physical=compound(beacon[2:5]),
                    Beacon_Bottom_Keepout=beacon[0], Cartographer_Physical=carto,
                    EBB42_Physical=ebb, Probe_Cable=cable)
    report["tool_to_gantry_electronics_and_cable_mm3"] = {
        name: overlaps(shape, external) for name, shape in parts.items()}
    if any(report["tool_to_gantry_electronics_and_cable_mm3"].values()):
        report["failures"].append("Tool intersects gantry/electronics/cable reference")
    report["beacon_top_keepout_metal_mm3"] = overlaps(top_keepout, dict(
        Hotend=hotend, Screws=screws, Inserts=inserts, Washers=washers,
        Fan_Metal_Conservative_Whole_Envelope=fan, Fan_Screws=fan_screws,
        Fan_Inserts=fan_inserts, **gantry, **accessory_hw))
    source_meta = json.loads((primitives.WORK / "v26_meta.json").read_text())
    report["beacon_top_keepout_core_screen"] = []
    for i, solid in enumerate(core.Solids()):
        hit = overlaps(top_keepout, {"Core": solid})
        if not hit:
            continue
        b = bounds(solid)
        matches = [m for m in source_meta if
                   all(abs(b[2 * axis] - m["min_mm"][axis]) < 0.001
                       and abs(b[2 * axis + 1] - m["max_mm"][axis]) < 0.001
                       for axis in range(3))
                   and abs(volume(solid) - m["vol_mm3"]) / m["vol_mm3"] < 0.001]
        printed = len(matches) == 1 and matches[0]["is_print"] and not matches[0]["is_metal"]
        report["beacon_top_keepout_core_screen"].append(
            {"core_solid": i, "volume_mm3": hit["Core"],
             "matched_source": matches[0]["name"] if len(matches) == 1 else None,
             "classification": "Source-identified printed polymer, not metal" if printed else "Metal or unclassified"})
        if not printed:
            report["beacon_top_keepout_metal_mm3"][f"Core_{i}"] = hit["Core"]
    if report["beacon_top_keepout_metal_mm3"]:
        report["failures"].append("Metal enters Beacon top keepout")
    report["probe_qualification"] = (
        "Beacon supplied top/bottom keepouts checked; Cartographer physical reference checked, "
        "not a separate manufacturer-specific electromagnetic keepout certification.")
    report["input_shaping"] = (
        "Existing Cartographer onboard ADXL345 and EBB42 board references retained; "
        "no new accelerometer bracket, wiring, firmware or resonance measurement.")
    print("Checking sampled forward withdrawal", flush=True)
    report["forward_tool_withdrawal"] = []
    moving = compound([body, hotend, *hardware, fan, fan_screws, fan_inserts,
                       references["P18_Tool_docking_backplate_3010"]])
    stationary = dict(Core=core, **external, **{
        n: s for n, s in references.items() if n not in
        ("P18_Tool_docking_backplate_3010", "P25_SparkShift_3010_Dock")})
    for dy in range(0, 36):
        hits = overlaps(moving.translate((0, dy, 0)), stationary, tolerance=0.01)
        if hits:
            report["forward_tool_withdrawal"].append({"forward_mm": dy, "intersections_mm3": hits})
    if report["forward_tool_withdrawal"]:
        report["findings_requiring_physical_confirmation"].append(
            "Forward tool withdrawal has modeled interference; see path results. Cam release is not simulated.")
    report["path_sampling_mm"] = 1
    report["limitations"] = [
        "35 mm straight forward translation is a sampled geometry screen, not continuous cam/latch/dock motion.",
        "No detailed fan connector, motor internals, heater leads, cable bend or dock electrical interface.",
        "45 mm cross-section/neighbor checks do not establish ten-tool rack capacity.",
        "P18/dock inherited overlap is reported separately, not silently treated as collision-free.",
        "Nominal nozzle reference tip differs from intended master datum; physical Z calibration required.",
        "No thermal, structural, insert torque/creep, airflow, material or physical fit qualification.",
    ]
    output = STEP / "18_One_Piece_Bambu_Toolhead_2510_REVIEW.step"
    report["assembly_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    report["passed_hard_geometry_checks"] = not report["failures"]
    (ROOT / "verification_toolhead_second_pass.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in (
        "passed_hard_geometry_checks", "failures", "findings_requiring_physical_confirmation",
        "forward_tool_withdrawal")}, indent=2))
    if report["failures"]:
        raise ValueError("Second-pass audit failed: " + "; ".join(report["failures"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-reference", type=Path, required=True)
    audit(parser.parse_args().core_reference)
