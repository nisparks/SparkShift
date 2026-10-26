"""Compare fan alignment without changing the approved toolhead geometry."""

import hashlib
import json

import cadquery as cq

from audit_tool_owned_2510 import bounds, compound
from build_modular_toolhead import ROOT, STEP, box, load, volume
from build_refined_docking_review import translated_hits


def main():
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    fin_solid = hotend.Solids()[3]
    fin_faces = [
        f for f in fin_solid.Faces()
        if bounds(f)[5] - bounds(f)[4] < 0.001
        and -55 < bounds(f)[4] < -25 and f.Area() > 100
    ]
    if len(fin_faces) != 14:
        raise ValueError("Expected seven Bambu fins with fourteen broad horizontal faces")
    fb = bounds(compound(fin_faces))
    target_y, target_z = (fb[2] + fb[3]) / 2, (fb[4] + fb[5]) / 2
    # One-millimeter extrusion measures the side-projected fin-stack rectangle.
    projection = box(0, 1, fb[2], fb[3], fb[4], fb[5])
    body = load("Bambu_One_Piece_Docking_Audited_REVIEW")
    targets = {
        "Hotend": hotend, "Existing_printed_body": body,
        "Existing_hotend_hardware": load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"),
        "Dock": load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW"),
        **{n: load(n) for n in (
            "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet",
            "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
            "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
            "Core_With_Restrained_AHG_Lead_References_REVIEW")},
    }
    centers = [
        ("Current", (16.45, 25.5, -35.3)),
        ("Halfway_to_fin_center", (16.45, (25.5 + target_y) / 2, (-35.3 + target_z) / 2)),
        ("Fin_center", (16.45, target_y, target_z)),
        ("Fin_center_inward_1mm", (15.45, target_y, target_z)),
        ("Inward_only_1mm", (15.45, 25.5, -35.3)),
        ("Lower_only_0p5mm", (16.45, 25.5, -35.8)),
        ("Lower_only_1mm", (16.45, 25.5, -36.3)),
        ("Lower_only_2mm", (16.45, 25.5, -37.3)),
        ("Forward_only_0p5mm", (16.45, 25.0, -35.3)),
        ("Forward_only_1mm", (16.45, 24.5, -35.3)),
        ("Forward_only_2mm", (16.45, 23.5, -35.3)),
        ("Forward_lower_0p5mm", (16.45, 25.0, -35.8)),
    ]
    report = {
        "status": "ALIGNMENT_STUDY_ONLY_NO_MOUNT_OR_THERMAL_APPROVAL",
        "fin_face_count": len(fin_faces), "fin_bounds_mm": fb,
        "fin_projected_center_yz_mm": [target_y, target_z],
        "candidates": [],
        "limitations": [
            "Side-projected rectangular coverage is a geometry comparison, not airflow or heat-transfer prediction.",
            "Generic fan opening radius11 and hub radius4; actual blade sweep and frame require vendor confirmation.",
            "Lowering or translating the fan requires redesigned mounting ears and screw/insert access.",
            "No candidate is installed into the existing body or released for manufacture.",
            "Neighbor intake, complete carriage wiring, probe-metal keepout and full-machine paths require re-audit after any mounting redesign.",
            "Existing low-Z rack/bed blocker is unchanged.",
        ],
    }
    assembly = cq.Assembly(name="24 Bambu fan alignment comparison - unmounted candidates")
    assembly.add(body, name="Unchanged_Bambu_print", color=cq.Color(0.9, 0.65, 0.1))
    assembly.add(hotend, name="Unchanged_Bambu_hotend", color=cq.Color(0.7, 0.7, 0.7))
    for name, (x, y, z) in centers:
        fan = box(x - 5, x + 5, y - 12.5, y + 12.5, z - 12.5, z + 12.5)
        disk = cq.Solid.makeCylinder(11, 1, cq.Vector(0, y, z), cq.Vector(1, 0, 0))
        hub = cq.Solid.makeCylinder(4, 1, cq.Vector(0, y, z), cq.Vector(1, 0, 0))
        aperture = disk.cut(hub)
        collisions = translated_hits(fan, targets, (0, 0, 0), tolerance=0.001)
        report["candidates"].append({
            "name": name, "center_mm": [x, y, z],
            "center_offset_from_current_mm": [x - 16.45, y - 25.5, z + 35.3],
            "projected_rectangle_area_mm2": volume(projection),
            "disk_coverage_fraction": volume(projection.intersect(disk)) / volume(projection),
            "annular_coverage_fraction": volume(projection.intersect(aperture)) / volume(projection),
            "fan_to_hotend_mm": fan.distance(hotend),
            "fan_to_P22_mm": fan.distance(targets["P22_CPAP_Lower_Plenum"]),
            "fan_to_core_mm": fan.distance(targets["Core_With_Restrained_AHG_Lead_References_REVIEW"]),
            "fan_envelope_intersections_mm3": collisions,
        })
        if name in ("Current", "Fin_center"):
            assembly.add(fan, name=name + "_FAN_ENVELOPE_NOT_MOUNTED",
                         color=cq.Color(0.2, 0.4, 0.9, 0.35) if name == "Current"
                         else cq.Color(0.1, 0.8, 0.4, 0.35))
    output = STEP / "24_Bambu_Fan_Alignment_Comparison_UNMOUNTED.step"
    assembly.export(str(output))
    imported = cq.importers.importStep(str(output)).val()
    if not imported.isValid() or len(imported.Solids()) != len(hotend.Solids()) + 3:
        raise ValueError("Alignment comparison STEP roundtrip failed")
    report["comparison_export"] = {
        "file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "solid_count": len(imported.Solids()), "valid": True}
    report["geometry_source_sha256"] = {
        n: hashlib.sha256((STEP / f"{n}.step").read_bytes()).hexdigest()
        for n in (
            "Tool2510_Reversed_Bambu_Reference_REVIEW", "Bambu_One_Piece_Docking_Audited_REVIEW",
            "Tool2510_Existing_Tool_M2_5_Hardware_REVIEW",
            "21_Bambu_Closed_Panel_Dock_Complete_REVIEW",
            "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet",
            "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
            "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
            "Core_With_Restrained_AHG_Lead_References_REVIEW")}
    report["decision"] = (
        "Retain current position within the unchanged design. The 0.5mm lower candidate improves "
        "projected annular coverage only from about56.1% to58.2% while reducing P22 clearance "
        "from1.2 to0.7mm. Larger lowering/centering collides with rigid existing parts. Inward-only "
        "movement requires printed-mount changes and does not improve projected alignment. "
        "No demonstrated thermal benefit justifies sacrificing the approved clearance cushion.")
    path = ROOT / "verification_bambu_fan_alignment.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
