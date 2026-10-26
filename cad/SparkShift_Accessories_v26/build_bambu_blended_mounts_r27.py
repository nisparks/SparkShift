"""Blend the closed fan seats into the shelf without changing mating geometry."""

import hashlib
import json

import cadquery as cq
import trimesh

from audit_tool_owned_2510 import bounds, overlaps
from build_bambu_closed_mounts_r26 import NAME as SOURCE_NAME, cut_stock
from build_bambu_continuous_guide import cylinder_x, cylinder_z
from build_modular_toolhead import ROOT, STEP, STL, box, load, volume


NAME = "Bambu_Blended_Closed_Fan_Seats_R27_REVIEW"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_edges(body, predicate, expected):
    edges = [e for e in body.Edges() if e.geomType() == "LINE" and predicate(bounds(e))]
    if len(edges) != expected:
        raise ValueError(f"Ambiguous blend edges: expected {expected}, got {len(edges)}")
    return edges


def build(*, localized_bosses=False):
    revision = 28 if localized_bosses else 27
    output_name = "Bambu_Flat_Shelf_Local_Fan_Bosses_R28_REVIEW" if localized_bosses else NAME
    assembly_label = "Flat_Shelf" if localized_bosses else "Blended_Mounts"
    report_path = ROOT / "verification_bambu_closed_mounts_r26.json"
    source_report = json.loads(report_path.read_text())
    for item in source_report["exports"]:
        if sha(ROOT / item["file"]) != item["sha256"]:
            raise ValueError(f"Revision-26 source changed since verification: {item['file']}")
    baseline = load(SOURCE_NAME).Solids()[0]
    body = baseline
    print("Blending exposed pad corners", flush=True)
    for radius, predicate in (
        (1.2, lambda q: abs(q[0] + 13.5) < 0.001 and abs(q[1] + 13.5) < 0.001
         and q[4] < -28.29 and q[5] > -22.31 and q[3] - q[2] < 0.001
         and any(abs(q[2] - y) < 0.001 for y in (32.5, 38))),
        (0.8, lambda q: abs(q[0] + 13.5) < 0.001 and abs(q[1] + 13.5) < 0.001
         and q[4] < -28.29 and abs(q[5] + 26) < 0.001 and q[3] - q[2] < 0.001),
        (0.5, lambda q: abs(q[4] + 14) < 0.001 and abs(q[5] + 14) < 0.001
         and abs(abs(q[0]) - 10) < 0.001 and abs(q[1] - q[0]) < 0.001 and q[2] >= 31.79),
    ):
        body = body.fillet(radius, select_edges(body, predicate, 2)).clean()
    if not localized_bosses:
        print("Tapering mounting webs into the existing shelf underside", flush=True)
        for y0, y1 in ((12.5, 18.5), (32.5, 38)):
            taper = cq.Workplane("XZ").polyline([
                (-13.51, -28.31), (-13.51, -26), (7.2, -28.31),
            ]).close().extrude(y1 - y0 + 0.02).val().translate((0, y1 + 0.01, 0))
            body = cut_stock(body, taper)
    print("Removing thin cap lips and consolidating the core connector clearance", flush=True)
    old_print = load("Bambu_Continuous_Guide_Clean_Fan_Mount_R25_REVIEW")
    upper_back = box(-10, 10, 31.8, 35.93, -22.5, -14)
    for y0, y1 in ((12.5, 18.5), (32.5, 38)):
        lip = box(-13.51, 11.21, y0 - 0.001, y1 + 0.001, -22.5, -22.299)
        lip = lip.cut(old_print, tol=1e-6).cut(upper_back, tol=1e-6)
        body = cut_stock(body, lip)
    body = cut_stock(body, box(-9.01, 9.01, 11.49, 11.8, -19.6, -13.99))
    pocket = box(-1.87, 1.87, 11.49, 16, -16.1294, -15)
    body = cut_stock(body, pocket)
    body = cut_stock(body, box(11.2, 15.01, 12.75, 32.05, -26.001, -22.5)).clean()
    underside_clearances = []
    if localized_bosses:
        print("Flattening the shelf underside outside two localized round insert bosses", flush=True)
        for y0, y1, axis_y in ((12.5, 18.5, 15.5), (32.5, 38, 35.5)):
            clearance = box(-13.51, 11.21, y0 - 0.001, y1 + 0.001, -28.31, -26)
            clearance = clearance.cut(old_print, tol=1e-6)
            clearance = clearance.cut(cylinder_x(axis_y, 5.7, 11.21, 3), tol=1e-6)
            body = cut_stock(body, clearance)
            underside_clearances.append(clearance)
        body = body.clean()
    if not body.isValid() or len(body.Solids()) != 1 or volume(body) <= 0:
        raise ValueError("Blended body is invalid, disconnected or nonpositive")
    if max(abs(a - b) for a, b in zip(bounds(body), bounds(baseline))) > 0.001:
        raise ValueError("Blending changed the approved overall bounding envelope")
    outside = volume(body.cut(baseline, tol=1e-6))
    common = volume(body.intersect(baseline, tol=1e-6))
    if abs(outside) > 0.001 or abs(common - volume(body)) > 0.001:
        raise ValueError("Blended print is not a verified subtractive subset of revision26")
    print("Checking seating walls, closed inner faces and unchanged functional regions", flush=True)
    gauges = {}
    for i, clearance in enumerate(underside_clearances):
        gauges[f"removed_broad_wedge_{i}_remaining_mm3"] = volume(
            body.intersect(clearance, tol=1e-6))
    for y in (15.5, 35.5):
        wall = cylinder_x(y, 7.3, 10.9, 2.45).cut(cylinder_x(y, 7.29, 10.91, 1.76))
        gauges[f"seat_{y}_missing_wall_mm3"] = volume(wall.cut(body, tol=1e-6))
        gauges[f"seat_{y}_blocked_pilot_mm3"] = volume(
            cylinder_x(y, 7.201, 10.94, 1.549).intersect(body, tol=1e-6))
        gauges[f"old_access_axis_{y}_unfilled_mm3"] = volume(
            cylinder_x(y, -13.4, 7.19, 0.6).cut(body, tol=1e-6))
    gauges["connector_pocket_blocked_mm3"] = volume(pocket.intersect(body, tol=1e-6))
    gauges["fan_recess_razor_lip_remaining_mm3"] = volume(
        box(11.201, 14.99, 12.751, 32.049, -22.549, -22.501).intersect(body, tol=1e-6))
    for name, region in (
        ("upper_rear_screw_seats", box(-8.4, 8.4, 30.9, 36, -22.2, 49)),
        ("upper_coupling", box(-14, 16, 19.7, 39, -13.9, 49)),
        ("hotend_mount_and_enclosed_guide", box(-14, 16, 18.6, 32.4, -66, -22.6)),
    ):
        before = baseline.intersect(region, tol=1e-6)
        after = body.intersect(region, tol=1e-6)
        gauges[f"{name}_removed_mm3"] = volume(before) - volume(after)
    gauges["filament_axis_blocked_mm3"] = volume(
        cylinder_z(0.9, -29.48, -8.31).intersect(body, tol=1e-6))
    sleeve = cylinder_z(3.8, -30.39, -25.1).cut(cylinder_z(2.8, -30.4, -25))
    gauges["inlet_sleeve_missing_wall_mm3"] = volume(sleeve.cut(body, tol=1e-6))
    if any(abs(v) > 0.001 for v in gauges.values()):
        raise ValueError(f"Blending damaged a functional feature: {gauges}")
    protected = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet",
        "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
        "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
        "Core_With_Restrained_AHG_Lead_References_REVIEW",
        "Tool2510_Reversed_Bambu_Reference_REVIEW",
        "Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")}
    hits = overlaps(body, protected)
    if hits:
        raise ValueError(f"Blended body has protected-part interference: {hits}")
    step = STEP / f"{output_name}.step"
    stl = STL / f"{output_name}.stl"
    cq.exporters.export(body, str(step))
    cq.exporters.export(body, str(stl), tolerance=0.03, angularTolerance=0.1)
    back = cq.importers.importStep(str(step)).val()
    mesh = trimesh.load_mesh(stl)
    if not back.isValid() or len(back.Solids()) != 1 or abs(volume(back) - volume(body)) > 0.001:
        raise ValueError("Blended print STEP readback failed")
    if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split(only_watertight=False)) != 1:
        raise ValueError("Blended print STL is invalid")
    exports = [step, stl]
    for source_name, target_name, expected_count in (
        ("26_Bambu_Closed_Mounts_Toolhead_REVIEW", f"{revision}_Bambu_{assembly_label}_Toolhead_REVIEW", 20),
        ("26_Bambu_Closed_Mounts_Complete_REVIEW", f"{revision}_Bambu_{assembly_label}_Complete_REVIEW", 145),
    ):
        source = load(source_name)
        matches = [i for i, s in enumerate(source.Solids())
                   if max(abs(a - b) for a, b in zip(bounds(s), bounds(baseline))) < 0.001
                   and abs(volume(s) - volume(baseline)) < 0.001]
        if len(matches) != 1:
            raise ValueError(f"Ambiguous print replacement in {source_name}")
        assembly = cq.Assembly(name=target_name)
        assembly.add(body, name=f"R{revision}_Bambu_Print", color=cq.Color(0.95, 0.67, 0.1))
        for i, s in enumerate(source.Solids()):
            if i != matches[0]:
                assembly.add(s, name=f"Unchanged_R26_Reference_{i}", color=cq.Color(0.55, 0.57, 0.6))
        path = STEP / f"{target_name}.step"
        assembly.export(str(path))
        readback = cq.importers.importStep(str(path)).val()
        if not readback.isValid() or len(readback.Solids()) != expected_count:
            raise ValueError(f"Assembly readback failed: {target_name}")
        exports.append(path)
    report = {
        "status": "LOCAL_GEOMETRY_REFINEMENT_NOT_PRINT_OR_MACHINE_APPROVAL",
        "source_report_sha256": sha(report_path),
        "source_body_sha256": sha(STEP / f"{SOURCE_NAME}.step"),
        "bounds_mm": bounds(body), "body_volume_mm3": volume(body),
        "removed_vs_r26_mm3": volume(baseline) - volume(body),
        "additions_outside_r26_mm3": outside, "common_with_r26_mm3": common,
        "feature_gauges_mm3": gauges, "protected_intersections_mm3": hits,
        "changes": [
            ("Broad wedge removed: flat Z-26 shelf underside outside localized radius3mm insert bosses, X5.7..11.2, retaining inherited hotend material."
             if localized_bosses else
             "Tapered web undersides run from the inherited Z-26 shelf to full-depth Z-28.3 seats at X7.2; no new bounding space."),
            "R1.2 rear and R0.8 front exposed inner pad corners; R0.5 upper rear external corners.",
            "Removed added 0.2mm top lips without trimming the inherited print or upper rear attachment.",
            "Removed 0.05-0.15mm front membrane remnants; planar Y11.8 interface setback.",
            "Consolidated three tiny core connector cutouts and fragile separating webs into one 3.74mm-wide by1.1294mm-high clearance pocket, ending at Y16.",
            "Removed the inherited 0.05mm overhanging membrane along the top of the fan recess; retained the adjacent solid shelf and insert seats.",
        ],
        "unchanged": "Fan position, L4 outer-entry inserts, fan screw engagement, hotend mount, guide/socket, upper rear screw seats and coupling, core, dock, 37.3mm pitch and hardware.",
        "inherited_clearance_evidence": {
            "basis": f"Verified R{revision} is a subtractive subset of hash-matched R26. All other assembly solids are reused unchanged; subtraction cannot increase swept rigid intersection volume.",
            "r26_dock_samples": source_report["dock_samples"],
            "r26_neighbor_checks": source_report["neighbor_checks"],
            "r26_hotend_service_samples": source_report["removed_hotend_service_samples"],
            "note": "Not a new continuous-motion or structural qualification.",
        },
        "limitations": source_report["limitations"] + [
            "Outer-entry heatsets require physical pullout, material and tightening qualification.",
            "Core-clearance pocket and mounting stiffness require print/fit review; this is not acceptance by visual appearance alone.",
        ],
        "exports": [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in exports],
    }
    report_name = "verification_bambu_flat_shelf_r28.json" if localized_bosses else "verification_bambu_blended_mounts_r27.json"
    (ROOT / report_name).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    build()
