"""Check gantry-mounted parked tools against the bed at printing height."""

import hashlib
import json

import cadquery as cq

from audit_tool_owned_2510 import bounds, overlaps, compound
from build_modular_toolhead import ROOT, STEP, box, load, primitives
from build_refined_docking_review import DOCK_NAMES, DOCK_STANDOFF_MM, translated_hits


def audit_bed_clearance(variants, report):
    path = primitives.WORK / "rack_audit_Bed_world.step"
    bed = cq.importers.importStep(str(path)).val()
    meta_path = primitives.WORK / "rack_audit_Bed_world.json"
    meta = json.loads(meta_path.read_text())
    expected = [v for pair in zip(meta["min_mm"], meta["max_mm"]) for v in pair]
    if len(bed.Solids()) != 1 or not bed.isValid() or max(
            abs(a - b) for a, b in zip(bounds(bed), expected)) > 0.001:
        raise ValueError("Bed snapshot and source-world metadata disagree")
    frame_y, frame_z = 36.91 + DOCK_STANDOFF_MM, 191.2794
    centers = [7 + 37.3 * i for i in range(10)]
    result = report["low_z_bed_clearance"] = {
        "bed_source": {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "metadata_sha256": hashlib.sha256(meta_path.read_bytes()).hexdigest(),
                       "bounds_mm": bounds(bed)},
        "world_y_offset_mm": frame_y, "world_z_offset_mm": frame_z,
        "active_nozzle_world_z_mm": 0.2, "cases": [], "clearance_boundaries": []}
    for active_label, active in variants.items():
        source_nozzle_z = frame_z + active["hotend"].BoundingBox().zmin
        z_shift = 0.2 - source_nozzle_z
        for parked_label, parked in variants.items():
            dock_parts = list(parked["dock"].Solids())
            if len(dock_parts) != len(DOCK_NAMES):
                raise ValueError("Unexpected dock solid order/count")
            for bay, x in enumerate(centers):
                def place(shape):
                    return shape.rotate((0, 0, 0), (0, 0, 1), 180).translate(
                        (x, frame_y, frame_z + z_shift))

                targets = {name: place(s) for name, s in zip(DOCK_NAMES, dock_parts)}
                targets.update({f"Parked_Tool_Solid_{i}": place(s)
                                for i, s in enumerate(parked["tool"].Solids())})
                hits = overlaps(bed, targets)
                result["cases"].append({
                    "active_hotend": active_label, "parked_hotend": parked_label,
                    "bay": bay, "gantry_z_delta_mm": z_shift,
                    "bed_intersections_mm3": hits})
    bed_bounds = bounds(bed)
    column = box(bed_bounds[0], bed_bounds[1], bed_bounds[2], bed_bounds[3], -1000, 1000)
    occupied_ymax, rear_translations = [], []
    for parked_label, parked in variants.items():
        world = compound([parked["dock"], parked["tool"]]).rotate(
            (0, 0, 0), (0, 0, 1), 180).translate((156.2, frame_y, frame_z))
        occupied_ymax.append(bounds(world)[3])
        projected = [s.intersect(column) for s in world.Solids()]
        projected = [s for s in projected if s.Solids()]
        lowest = min(bounds(s)[4] for s in projected)
        for active_label, active in variants.items():
            source_nozzle_z = frame_z + active["hotend"].BoundingBox().zmin
            low_column = box(-1000, 1000, -1000, 1000, -1000, source_nozzle_z - 0.2)
            low_parts = [s.intersect(low_column) for s in world.Solids()]
            low_parts = [s for s in low_parts if s.Solids()]
            low_ymin = min(bounds(s)[2] for s in low_parts)
            rear_translations.append(bed_bounds[3] + 1 - low_ymin)
            result["clearance_boundaries"].append({
                "active_hotend": active_label, "parked_hotend": parked_label,
                "parked_lowest_z_over_bed_footprint_mm": lowest,
                "active_nozzle_z_at_first_bed_top_contact_mm": source_nozzle_z - lowest,
                "same_orientation_low_hardware_ymin_mm": low_ymin})
    result["forward_translation_for_1mm_bed_edge_gap_mm"] = max(occupied_ymax) - bed_bounds[2] + 1
    result["same_orientation_rear_translation_for_1mm_bed_edge_gap_mm"] = max(rear_translations)
    result["collision_case_count"] = sum(bool(c["bed_intersections_mm3"]) for c in result["cases"])
    result["qualification"] = (
        "Source-world rigid bed contact at first-layer height; no printed-object, heater wiring, "
        "thermal expansion or bed-motion envelope is included. Reserving a print-area strip does "
        "not prevent the dock hardware itself hitting the bed.")
    if result["collision_case_count"]:
        report["failures"].append({
            "check": "Gantry-mounted parked tools/docks intersect bed at first-layer height",
            "colliding_cases": result["collision_case_count"], "total_cases": len(result["cases"])})
    return result


def screen_gantry_translation(delta_y):
    work = primitives.WORK
    frames = json.loads((work / "rack_audit_frames.json").read_text())
    x_path, flying_path = (work / "rack_audit_X_Gantry_world.step",
                           work / "rack_audit_Flying_Gantry_world.step")
    x = cq.importers.importStep(str(x_path)).val().translate(
        (0, frames["x_gantry_y_shift_to_dock_mm"] + DOCK_STANDOFF_MM, 0))
    flying = cq.importers.importStep(str(flying_path)).val()
    xm = json.loads(x_path.with_suffix(".json").read_text())
    fm = json.loads(flying_path.with_suffix(".json").read_text())
    if len(x.Solids()) != len(xm) or len(flying.Solids()) != len(fm):
        raise ValueError("Gantry snapshot metadata/count mismatch")
    for shape, metadata, dy in (
            (x, xm, frames["x_gantry_y_shift_to_dock_mm"] + DOCK_STANDOFF_MM),
            (flying, fm, 0)):
        for solid, item in zip(shape.Solids(), metadata):
            expected = [v for pair in zip(item["min_mm"], item["max_mm"]) for v in pair]
            expected[2] += dy
            expected[3] += dy
            if max(abs(a - b) for a, b in zip(bounds(solid), expected)) > 0.05:
                raise ValueError(f"Gantry snapshot body order/frame mismatch: {item['name']}")
    rail_names = {"R1_GANTRY_Y_RAIL_left_400_NOMINAL", "R1_GANTRY_Y_RAIL_left_400_NOMINAL (1)"}
    bearings = {"_MGN9H (10)", "_MGN9H (11)", "_MGN9H (12)", "_MGN9H (13)"}
    if sum(m["name"] in rail_names for m in fm) != 2 or sum(
            m["name"] in bearings for m in xm) != 4:
        raise ValueError("Unexpected source bearing/rail references")
    nonbearing = compound(s for s, m in zip(x.Solids(), xm) if m["name"] not in bearings)
    rails = {f"{i}:{m['name']}": s for i, (s, m) in enumerate(zip(flying.Solids(), fm))
             if m["name"] in rail_names}
    fixed = {f"{i}:{m['name']}": s for i, (s, m) in enumerate(zip(flying.Solids(), fm))
             if m["name"] not in rail_names}
    hits = translated_hits(x, fixed, (0, delta_y, 0))
    hits.update(translated_hits(nonbearing, rails, (0, delta_y, 0)))
    bearing_y = [bounds(s)[i] + delta_y for s, m in zip(x.Solids(), xm)
                 if m["name"] in bearings for i in (2, 3)]
    rail_min = max(m["min_mm"][1] for m in fm if m["name"] in rail_names)
    rail_max = min(m["max_mm"][1] for m in fm if m["name"] in rail_names)
    return {
        "rack_world_y_translation_mm": delta_y,
        "gantry_intersections_mm3": hits,
        "named_bearing_reference_y_envelope_mm": [min(bearing_y), max(bearing_y)],
        "nominal_y_rail_extent_mm": [rail_min, rail_max],
        "named_bearing_references_within_rail_length": (
            min(bearing_y) >= rail_min and max(bearing_y) <= rail_max),
        "source_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (x_path, flying_path)},
        "qualification": "Necessary X-gantry reach screen only; not a redesigned support or docking path. "
                         "Only the four named bearings' own Y-rail contacts are exempted."}


def load_parked_variants():
    work = primitives.WORK
    source_path = work / "parked_intake_sources.json"
    rack_report = json.loads((ROOT / "verification_ten_tool_closed_panel_dock.json").read_text())
    variants = {}
    for meta in json.loads(source_path.read_text()):
        if meta["full_rack_source_sha256"] != rack_report["full_ten_tool_rack"]["export"]["sha256"]:
            raise ValueError("Tool snapshot belongs to a different full-rack source")
        label = meta["component"].split("_", 1)[1]
        tool_path = primitives.WORK / f"parked_intake_{meta['component']}.step"
        tool = cq.importers.importStep(str(tool_path)).val().translate(
            (-meta["bay_x_mm"], -meta["world_y_offset_mm"], -meta["world_z_offset_mm"])).rotate(
                (0, 0, 0), (0, 0, 1), 180)
        if len(tool.Solids()) != meta["bodies"]:
            raise ValueError("Tool snapshot solid count changed")
        hotend_name = ("Tool2510_Reversed_Bambu_Reference_REVIEW" if label == "Bambu"
                       else "P17M_RedLizard_Hotend_Reference")
        variants[label] = {
            "tool": tool, "hotend": load(hotend_name),
            "dock": load(f"21_{label}_Closed_Panel_Dock_Complete_REVIEW"),
            "source": {"tool_file": str(tool_path),
                       "tool_sha256": hashlib.sha256(tool_path.read_bytes()).hexdigest(),
                       "dock_file": f"21_{label}_Closed_Panel_Dock_Complete_REVIEW.step",
                       "dock_sha256": hashlib.sha256(
                           (STEP / f"21_{label}_Closed_Panel_Dock_Complete_REVIEW.step").read_bytes()).hexdigest()}}
    if set(variants) != {"Bambu", "RedLizard"}:
        raise ValueError("Both tool variants are required")
    return variants


def main():
    path = ROOT / "verification_low_z_bed_clearance.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    variants = load_parked_variants()
    report = {"status": "BLOCKED_LOW_Z_BED_COLLISION", "failures": [],
              "tool_sources": {label: v["source"] for label, v in variants.items()}}
    result = audit_bed_clearance(variants, report)
    report["forward_relocation_screen"] = screen_gantry_translation(
        -result["forward_translation_for_1mm_bed_edge_gap_mm"])
    report["same_orientation_rear_relocation_screen"] = screen_gantry_translation(
        result["same_orientation_rear_translation_for_1mm_bed_edge_gap_mm"])
    bed = cq.importers.importStep(result["bed_source"]["file"]).val()
    controls = []
    for active_label, active in variants.items():
        source_tip = result["world_z_offset_mm"] + active["hotend"].BoundingBox().zmin
        for parked_label, parked in variants.items():
            dock = parked["dock"].rotate((0, 0, 0), (0, 0, 1), 180).translate(
                (156.2, result["world_y_offset_mm"], result["world_z_offset_mm"] + 15 - source_tip))
            hits = overlaps(bed, {"Dock": dock})
            controls.append({
                "active_hotend": active_label, "parked_hotend": parked_label,
                "bed_intersections_mm3": hits})
            if hits:
                report["failures"].append({
                    "check": "Dock-only Z15 positive control unexpectedly intersects bed",
                    "result": controls[-1]})
    report["audit_regression_checks"] = {
        "first_layer_colliding_cases": result["collision_case_count"],
        "dock_only_positive_control_at_nozzle_z_mm": 15,
        "positive_control_combinations": len(controls),
        "positive_controls": controls,
        "qualification": "Positive control distinguishes low-Z contact from an always-colliding "
                         "or misframed bed test; not print-volume approval."}
    for key in ("diagnostic_archive", "diagnostic_image"):
        if key not in previous:
            continue
        if (previous.get("tool_sources") != report["tool_sources"] or
                previous.get("low_z_bed_clearance", {}).get("bed_source") != result["bed_source"]):
            raise ValueError("Diagnostic evidence belongs to different geometry; regenerate it")
        evidence = previous[key]
        evidence_path = (ROOT / evidence["file"]).resolve()
        if not evidence_path.is_relative_to(ROOT.resolve()) or hashlib.sha256(
                evidence_path.read_bytes()).hexdigest() != evidence["sha256"]:
            raise ValueError(f"Diagnostic evidence missing, changed or outside the CAD directory: {key}")
        report[key] = evidence
    report["passed"] = not report["failures"]
    if report["passed"]:
        report["status"] = "BED_SCREEN_CLEAR_NOT_MACHINE_QUALIFIED"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "failures": report["failures"],
                      "forward_relocation_screen": report["forward_relocation_screen"],
                      "rear_relocation_summary": {
                          "translation_mm": report["same_orientation_rear_relocation_screen"]["rack_world_y_translation_mm"],
                          "colliding_fixed_bodies": len(report["same_orientation_rear_relocation_screen"]["gantry_intersections_mm3"]),
                          "named_bearings_within_rail_length": report["same_orientation_rear_relocation_screen"]["named_bearing_references_within_rail_length"]},
                      "report": str(path)}, indent=2))
    if report["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
