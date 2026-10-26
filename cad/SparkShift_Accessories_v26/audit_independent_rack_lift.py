"""Screen independent rack lift before designing guides or actuation."""

import hashlib
import json

import cadquery as cq

from audit_low_z_bed_clearance import load_parked_variants
from audit_ten_tool_rack import snapshot, world
from audit_tool_owned_2510 import bounds, compound
from build_modular_toolhead import ROOT, box, primitives
from build_refined_docking_review import DOCK_STANDOFF_MM, translated_hits


def main():
    variants = load_parked_variants()
    frames = json.loads((primitives.WORK / "rack_audit_frames.json").read_text())
    frames["world_y_offset_mm"] += DOCK_STANDOFF_MM
    frames["x_gantry_y_shift_to_dock_mm"] += DOCK_STANDOFF_MM
    baseline_path = ROOT / "verification_low_z_bed_clearance.json"
    baseline = json.loads(baseline_path.read_text())
    sources = {}
    flying = snapshot("Flying_Gantry", sources)
    beam = snapshot("X_Gantry", sources).translate(
        (0, frames["x_gantry_y_shift_to_dock_mm"] + 60, 0))
    crossbar = snapshot("crossbar", sources)
    bed_path = primitives.WORK / "rack_audit_Bed_world.step"
    if hashlib.sha256(bed_path.read_bytes()).hexdigest() != (
            baseline["low_z_bed_clearance"]["bed_source"]["sha256"]):
        raise ValueError("Bed source changed since the validated low-Z audit")
    bed = cq.importers.importStep(str(bed_path)).val()
    lift = 15.0
    carriage_meta_path = primitives.WORK / "rack_lift_carriage_withdrawn_bounds.json"
    carriage_meta = json.loads(carriage_meta_path.read_text())
    archive_path = ROOT / carriage_meta["source_archive"]
    if (carriage_meta["bodies"] != 246 or hashlib.sha256(
            archive_path.read_bytes()).hexdigest() != carriage_meta["source_archive_sha256"]):
        raise ValueError("Carriage bounds do not identify the verified native diagnostic")
    report = {
        "status": "CONCEPT_SCREEN_NOT_BUILD_APPROVED",
        "lift_mm": lift,
        "x_gantry_withdrawal_mm": 60,
        "source_low_z_report_sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        "tool_sources": {k: v["source"] for k, v in variants.items()},
        "sources": sources,
        "bed_checks": [],
        "raised_parked_checks": [],
        "lift_path_samples": [],
        "conservative_swept_box_checks": [],
        "limitations": [
            "Independent rack motion requires new supports, guides, retention and actuation; none are designed here.",
            "Existing P29/P30 rack mounts cannot remain rigidly attached across an independent lift.",
            "The moving assembly assumed here consists of crossbar, docks and parked tools only.",
            "The X beam and active assembly must withdraw 60 mm before lift. Carriage contents are limited to the 246-body source reference.",
            "Per-solid swept bounding boxes give a sufficient clearance proof only where no target intersection is reported; potential hits are inconclusive.",
            "Flexible umbilical motion and added lifting-rack wiring are not modeled.",
            "No top-of-machine travel, enclosure, load, deflection, synchronization, thermal or firmware qualification.",
            "A clear bed result alone does not establish safe toolchange paths or usable print volume.",
        ],
    }
    targets = {"Flying_Gantry": flying, "Withdrawn_X_Gantry": beam}
    parked_ymax = bounds(crossbar)[3]
    parked_zmax = bounds(crossbar)[5] + lift
    for bay in range(10):
        for label, v in variants.items():
            parked = world(compound([v["tool"], v["dock"]]), 7 + 37.3 * bay, frames)
            parked_ymax = max(parked_ymax, bounds(parked)[3])
            parked_zmax = max(parked_zmax, bounds(parked)[5] + lift)
            swept_boxes = compound(box(b[0], b[1], b[2], b[3], b[4], b[5] + lift)
                                   for b in (bounds(s) for s in parked.Solids()))
            report["conservative_swept_box_checks"].append({
                "bay": bay, "variant": label,
                "potential_intersections_mm3": translated_hits(swept_boxes, targets, (0, 0, 0)),
                "minimum_distance_mm": min(swept_boxes.distance(t) for t in targets.values()),
            })
            report["raised_parked_checks"].append({
                "bay": bay, "variant": label,
                "intersections_mm3": translated_hits(parked, targets, (0, 0, lift)),
            })
            for active_label, active in variants.items():
                source_tip = frames["world_z_offset_mm"] + bounds(active["hotend"])[4]
                offset = (0, 0, 0.2 - source_tip + lift)
                report["bed_checks"].append({
                    "bay": bay, "parked_variant": label, "active_variant": active_label,
                    "bed_intersections_mm3": translated_hits(parked, {"Bed": bed}, offset),
                    "lowest_parked_world_z_mm": bounds(parked)[4] + offset[2],
                })
            if bay in (0, 4, 9):
                for sample in (0, 2.5, 5, 7.5, 10, 12.5, 15):
                    report["lift_path_samples"].append({
                        "bay": bay, "variant": label, "lift_mm": sample,
                        "intersections_mm3": translated_hits(parked, targets, (0, 0, sample)),
                    })
        print(f"Lift screen bay {bay} complete", flush=True)
    report["crossbar_lift_samples"] = [
        {"lift_mm": z, "intersections_mm3": translated_hits(crossbar, targets, (0, 0, z))}
        for z in (0, 2.5, 5, 7.5, 10, 12.5, 15)
    ]
    cb = bounds(crossbar)
    crossbar_swept = box(cb[0], cb[1], cb[2], cb[3], cb[4], cb[5] + lift)
    report["crossbar_conservative_swept_box"] = {
        "potential_intersections_mm3": translated_hits(crossbar_swept, targets, (0, 0, 0)),
        "minimum_distance_mm": min(crossbar_swept.distance(t) for t in targets.values())}
    carriage_bounds = carriage_meta["bounds_mm"]
    report["active_assembly_whole_envelope_separation"] = {
        "carriage_source": carriage_meta,
        "carriage_metadata_sha256": hashlib.sha256(carriage_meta_path.read_bytes()).hexdigest(),
        "lifted_rack_ymax_mm": parked_ymax,
        "checks": [],
        "qualification": "Positive Y-envelope separation proves rigid active tool/carriage to raised rack clearance at any X and any lift in 0..15 mm, only after the specified 60 mm withdrawal.",
    }
    for label, v in variants.items():
        active = world(v["tool"], 0, frames).translate((0, 60, 0))
        ymin = min(bounds(active)[2], carriage_bounds[2])
        report["active_assembly_whole_envelope_separation"]["checks"].append({
            "variant": label, "active_assembly_ymin_mm": ymin,
            "y_gap_mm": ymin - parked_ymax})
    source_bambu_tip = frames["world_z_offset_mm"] + bounds(variants["Bambu"]["hotend"])[4]
    report["raised_rack_height_requirement"] = {
        "highest_rack_source_world_z_mm": parked_zmax,
        "highest_rack_z_with_active_Bambu_nozzle_at_z_0_2_mm": parked_zmax + 0.2 - source_bambu_tip,
        "carriage_source_world_zmax_at_nozzle_z_0_2_mm": carriage_bounds[5],
        "qualification": "Record for future enclosure/top-travel checking; not a verified machine Z limit.",
    }
    first_contact = max(c["active_nozzle_z_at_first_bed_top_contact_mm"]
                        for c in baseline["low_z_bed_clearance"]["clearance_boundaries"])
    report["unimplemented_mechanism_requirements"] = {
        "minimum_lift_for_1mm_clearance_above_active_nozzle_plane_mm": first_contact + 1,
        "nominal_lift_mm": lift,
        "nominal_z_hop_before_lowering_rack_relative_to_current_print_plane_mm": 15,
        "required_withdrawal_before_lift_mm": 60,
        "requirements": [
            "Replace rigid rack supports with guided independent Z motion while preserving dock-down coupling datums.",
            "Account for P30 spacers and all crossbar-mounted hardware in the final moving/fixed partition.",
            "Positively retain and synchronize both crossbar ends; verify loaded repeatability at every bay.",
            "Provide raised-state retention on power loss; an unpowered rack must not fall toward the bed or print.",
            "Interlock rack position, coupling state and machine Z; do not lower over an existing print without the required Z clearance.",
            "Lift only after carriage withdrawal and secured active-tool pickup; the selected dock must be empty.",
            "Provide flexible fan-power wiring for all parked tools and the additional rack stroke.",
            "Verify highest machine Z, enclosure clearance, loads, deflection and physical motion before release.",
        ],
        "firmware_implemented": False,
        "qualification": "Design requirements only; not executable motion instructions or an approved lifting mechanism.",
    }
    summary = report["summary"] = {
        "bed_collision_cases": sum(bool(c["bed_intersections_mm3"]) for c in report["bed_checks"]),
        "raised_parked_collision_cases": sum(bool(c["intersections_mm3"]) for c in report["raised_parked_checks"]),
        "sampled_lift_collision_cases": sum(bool(c["intersections_mm3"]) for c in report["lift_path_samples"]),
        "crossbar_collision_samples": sum(bool(c["intersections_mm3"]) for c in report["crossbar_lift_samples"]),
        "conservative_swept_box_potential_hits": sum(
            bool(c["potential_intersections_mm3"]) for c in report["conservative_swept_box_checks"]
        ) + bool(report["crossbar_conservative_swept_box"]["potential_intersections_mm3"]),
        "active_assembly_envelope_overlap_cases": sum(
            c["y_gap_mm"] <= 0 for c in report["active_assembly_whole_envelope_separation"]["checks"]),
        "minimum_conservative_swept_clearance_mm": min(
            [c["minimum_distance_mm"] for c in report["conservative_swept_box_checks"]]
            + [report["crossbar_conservative_swept_box"]["minimum_distance_mm"]]),
        "minimum_parked_z_at_active_nozzle_z_0_2_mm": min(
            c["lowest_parked_world_z_mm"] for c in report["bed_checks"]),
    }
    report["status"] = (
        "REJECTED_LIFT_CONCEPT_COLLISIONS" if any(summary[k] for k in (
            "bed_collision_cases", "raised_parked_collision_cases",
            "sampled_lift_collision_cases", "crossbar_collision_samples",
            "active_assembly_envelope_overlap_cases"))
        else "INCONCLUSIVE_LIFT_SWEPT_BOX_POTENTIAL_HITS" if (
            summary["conservative_swept_box_potential_hits"]
            or summary["minimum_conservative_swept_clearance_mm"] <= 0.001)
        else "LIMITED_LIFT_GEOMETRY_SCREEN_CLEAR_NOT_BUILD_APPROVED")
    path = ROOT / "verification_independent_rack_lift.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], **summary, "report": str(path)}, indent=2))


if __name__ == "__main__":
    main()
