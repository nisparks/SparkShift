"""Replace open fan access scallops with closed outer-entry heatset seats."""

import hashlib
import json

import cadquery as cq
import trimesh

from audit_tool_owned_2510 import bounds, boxes_overlap, compound, overlaps, solid_bounds
from build_bambu_continuous_guide import cylinder_x, cylinder_z
from build_modular_toolhead import ROOT, STEP, STL, box, cylinder_y, load, volume
from build_refined_docking_review import translated_hits


NAME = "Bambu_Closed_Fan_Seats_Continuous_Junction_R26_REVIEW"


def cut_stock(stock, cutter):
    result = stock.cut(cutter, tol=1e-6)
    before, after = volume(stock), volume(result)
    if not result.isValid() or after <= 0 or after > before + 0.001:
        raise ValueError(f"Nonphysical stock subtraction: {before} -> {after}")
    return result


def build():
    print("Loading baseline and protected references", flush=True)
    baseline = load("Bambu_Continuous_Guide_Clean_Fan_Mount_R25_REVIEW")
    refs = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet",
        "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
        "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
        "Core_With_Restrained_AHG_Lead_References_REVIEW")}
    front_seat = box(-13.5, 11.2, 12.5, 18.5, -28.3, -22.3)
    rear_seat = box(-13.5, 11.2, 32.5, 38, -28.3, -22.3)
    upper_back = box(-10, 10, 31.8, 35.93, -22.5, -14)
    upper_front = box(-9, 9, 11.5, 19.6, -19.6, -14)
    offsets = ((0, 0, 0), (-0.15, 0, 0), (0.15, 0, 0), (0, -0.15, 0),
               (0, 0.15, 0), (0, 0, -0.15), (0, 0, 0.15))
    print("Relieving new stock against individual protected solids", flush=True)
    for blank_name, ref_name in (
        ("rear", "P18_Tool_docking_backplate_3010"),
        ("front", "Core_With_Restrained_AHG_Lead_References_REVIEW"),
    ):
        blank = rear_seat if blank_name == "rear" else upper_front
        blank_bounds = bounds(blank)
        for delta in offsets:
            for solid, original_bounds in solid_bounds(refs[ref_name]):
                shifted_bounds = [v + delta[i // 2] for i, v in enumerate(original_bounds)]
                if boxes_overlap(blank_bounds, shifted_bounds):
                    blank = cut_stock(blank, solid.translate(delta))
        if blank_name == "rear":
            rear_seat = blank
        else:
            upper_front = blank
    additions = [front_seat, rear_seat, upper_back, upper_front]
    body = baseline.fuse(*additions, tol=1e-6)
    if not volume(baseline) <= volume(body) <= volume(baseline) + sum(map(volume, additions)) + 0.001:
        raise ValueError("Nonphysical added-stock union")
    for x in (-6, 6):
        body = cut_stock(body, cylinder_y(x, -19.26, 31, 37, 2.28))
    inserts = []
    for y in (15.5, 35.5):
        # Four-millimeter inserts enter from the exposed +X face before the fan.
        body = cut_stock(body, cylinder_x(y, 7.2, 11.21, 1.55))
        body = cut_stock(body, cq.Solid.makeCone(
            1.55, 1.8, 0.25, cq.Vector(10.95, y, -25.3), cq.Vector(1, 0, 0)))
        inserts.append(cylinder_x(y, 7.2, 11.2, 1.75).cut(
            cylinder_x(y, 7.19, 11.21, 1.05)))
    body = body.clean()
    if not body.isValid() or len(body.Solids()) != 1 or volume(body) <= 0:
        raise ValueError("Closed-seat body is not one valid solid")
    fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
    fan_box = box(11.45, 21.45, 13, 38, -47.8, -22.8)
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")
    hardware = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")
    insert_shape = compound(inserts)
    protected = dict(refs, Fan=fan_box, Hotend=hotend, Fan_Screws=screws,
                     Hotend_Screws=compound(hardware.Solids()[i] for i in (1, 4, 7)),
                     Hotend_Washers=compound(hardware.Solids()[i] for i in (2, 5)))
    print("Checking protected parts and exact feature witnesses", flush=True)
    hits = overlaps(body, protected)
    if hits:
        raise ValueError(f"Closed-seat geometry interferes with protected parts: {hits}")
    gauges = {}
    for y in (15.5, 35.5):
        # The old open access span is now solid, including its former bore.
        gauges[f"old_channel_{y}_unfilled_mm3"] = volume(
            cylinder_x(y, -13.4, 7.19, 2.19).cut(body))
        wall = cylinder_x(y, 7.3, 10.9, 2.45).cut(cylinder_x(y, 7.29, 10.91, 1.76))
        gauges[f"seat_{y}_missing_enclosing_wall_mm3"] = volume(wall.cut(body))
        gauges[f"seat_{y}_blocked_pilot_mm3"] = volume(
            cylinder_x(y, 7.201, 10.94, 1.549).intersect(body))
    back_witness = upper_back
    for x in (-6, 6):
        back_witness = back_witness.cut(cylinder_y(x, -19.26, 30, 38, 2.281))
    gauges["upper_back_unfilled_mm3"] = volume(back_witness.cut(body))
    gauges["upper_front_unfilled_outside_core_relief_mm3"] = volume(upper_front.cut(body))
    sleeve_wall = cylinder_z(3.8, -30.39, -25.1).cut(cylinder_z(2.8, -30.4, -25))
    gauges["inlet_sleeve_missing_wall_mm3"] = volume(sleeve_wall.cut(body))
    gauges["filament_axis_blocked_mm3"] = volume(cylinder_z(0.9, -29.48, -8.31).intersect(body))
    if any(abs(v) > 0.001 for v in gauges.values()):
        raise ValueError(f"Closed-seat/junction feature gauges failed: {gauges}")
    if any(abs(a - b) > 0.001 for a, b in zip(bounds(body), bounds(baseline))):
        raise ValueError("Closed-seat body changed the existing bounding envelope")
    dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")
    tool = compound([body, hotend, hardware, fan, screws, insert_shape])
    print("Checking dock withdrawal and hotend service", flush=True)
    motion_hits = []
    for sample in range(121):
        result = translated_hits(tool, {"Dock": dock}, (0, -0.5 * sample, 0))
        if result:
            motion_hits.append({"withdrawal_mm": sample * 0.5, "hits": result})
    if motion_hits:
        raise ValueError(f"Closed-seat dock path interference: {motion_hits}")
    removable = compound(hotend.Solids()[3:5])
    fixed = compound([body, hardware, fan_box, screws, insert_shape])
    for down, rear in [(i * 0.25, 0) for i in range(17)] + [(4, i) for i in range(1, 41)]:
        result = translated_hits(removable, {"Fixed": fixed}, (0, -rear, -down))
        if result:
            raise ValueError(f"Hotend service blocked at {down}/{rear}: {result}")
    print("Checking mixed neighbors", flush=True)
    from audit_low_z_bed_clearance import load_parked_variants
    neighbors = load_parked_variants()
    neighbor_checks = []
    for label, target in (
        ("Bambu", compound([tool, dock])),
        ("RedLizard", compound([neighbors["RedLizard"]["tool"], neighbors["RedLizard"]["dock"]])),
    ):
        for dx in (-37.3, 37.3):
            for sample in range(61):
                result = translated_hits(tool, {"Neighbor": target.translate((dx, 0, 0))}, (0, -sample, 0))
                if result:
                    raise ValueError(f"Neighbor collision: {label}/{dx}/{sample}: {result}")
            neighbor_checks.append({"variant": label, "offset_x_mm": dx, "samples": 61, "hits": []})
    step = STEP / f"{NAME}.step"
    stl = STL / f"{NAME}.stl"
    cq.exporters.export(body, str(step))
    cq.exporters.export(body, str(stl), tolerance=0.03, angularTolerance=0.1)
    mesh = trimesh.load_mesh(stl)
    if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split(only_watertight=False)) != 1:
        raise ValueError("Closed-seat STL invalid")
    back = cq.importers.importStep(str(step)).val()
    if not back.isValid() or len(back.Solids()) != 1 or abs(volume(back) - volume(body)) > 0.001:
        raise ValueError("Closed-seat print STEP readback failed")
    insert_path = STEP / "Bambu_Outer_Entry_M2p5_L4_Inserts_R26_REVIEW.step"
    cq.exporters.export(insert_shape, str(insert_path))
    tool_path = STEP / "26_Bambu_Closed_Mounts_Toolhead_REVIEW.step"
    cq.exporters.export(tool, str(tool_path))
    tool_back = cq.importers.importStep(str(tool_path)).val()
    if not tool_back.isValid() or len(tool_back.Solids()) != 20:
        raise ValueError("Closed-seat toolhead STEP readback failed")
    print("Checking full assembly regression and STEP readback", flush=True)
    source = load("21_Bambu_Toolhead_And_Closed_Panel_Dock_REVIEW")
    source_body = load("Bambu_One_Piece_Docking_Audited_REVIEW")
    old_inserts = load("Tool2510_Two_Inner_Entry_L3_Heatsets_REVIEW").Solids()
    replace_body = []
    replace_insert = []
    for i, s in enumerate(source.Solids()):
        if max(abs(a - b) for a, b in zip(bounds(s), bounds(source_body))) < 0.001:
            replace_body.append(i)
        elif any(max(abs(a - b) for a, b in zip(bounds(s), bounds(v))) < 0.001
                 for v in old_inserts):
            replace_insert.append(i)
    if len(replace_body) != 1 or len(replace_insert) != 2:
        raise ValueError("Ambiguous body/heatset replacement in full assembly")
    regression = []
    for i, s in enumerate(source.Solids()):
        if i in replace_body + replace_insert:
            continue
        before = sum(overlaps(source_body, {"Source": s}).values())
        after = sum(overlaps(body, {"Source": s}).values())
        if after - before > 0.001:
            raise ValueError(f"New complete assembly collision: solid{i}: {after-before}")
        regression.append({"solid_index": i, "intersection_increase_mm3": after - before})
    full = cq.Assembly(name="26 Bambu - closed fan mounts and continuous junction")
    full.add(body, name="R26_Bambu_Print", color=cq.Color(0.95, 0.67, 0.1))
    full.add(insert_shape, name="Outer_Entry_M2p5_L4_Heatsets", color=cq.Color(0.75, 0.5, 0.15))
    for i, s in enumerate(source.Solids()):
        if i not in replace_body + replace_insert:
            full.add(s, name=f"Unchanged_Reference_{i}", color=cq.Color(0.55, 0.57, 0.6))
    full_path = STEP / "26_Bambu_Closed_Mounts_Complete_REVIEW.step"
    full.export(str(full_path))
    full_back = cq.importers.importStep(str(full_path)).val()
    if not full_back.isValid() or len(full_back.Solids()) != len(source.Solids()):
        raise ValueError("Closed-seat complete assembly readback failed")
    report = {
        "status": "LOCAL_CAD_CORRECTION_NOT_PHYSICAL_OR_MACHINE_APPROVAL",
        "supersedes": "Revision25 open inner-entry fan channels and incomplete upper-front fill.",
        "fan_center_mm": [16.45, 25.5, -35.3],
        "bounds_mm": bounds(body), "solid_count": 1, "watertight": True,
        "body_volume_mm3": volume(body),
        "added_volume_vs_rejected_r25_mm3": volume(body) - volume(baseline),
        "feature_gauges_mm3": gauges, "protected_intersections_mm3": hits,
        "dock_samples": 121, "dock_hits": motion_hits,
        "neighbor_checks": neighbor_checks, "removed_hotend_service_samples": 57,
        "toolhead_solids": len(tool_back.Solids()),
        "complete_assembly_solids": len(full_back.Solids()), "regression_checks": regression,
        "fan_insert_change": {
            "size": "User-supplied M2.5 L4 OD3.5", "entry": "+X, fan removed",
            "x_extent_mm": [7.2, 11.2], "pilot_diameter_mm": 3.1,
            "minimum_screw_overlap_with_insert_mm": 3.75,
            "old_cross_body_channels": "Filled completely, not retained as slots or tunnels.",
            "note": "Outer-entry heatsets have no outward retaining shoulder; pullout/temperature/torque require physical qualification. Two existing M2.5x14 screws and fan pose retained.",
        },
        "upper_junction": "Filled rear transition and front strip, with actual fixed-core relief and required P18 screw passages preserved.",
        "limitations": [
            "Existing original rack bed collision and probe cable entry issue remain.",
            "Required clearance to a separate core/backplate is not a gap that may be arbitrarily bridged.",
            "Cool-side guide/socket fit and temperature, structural behavior, fan cooling and insert pullout are unqualified.",
        ],
        "exports": [
            {"file": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in (step, stl, insert_path, tool_path, full_path)],
    }
    (ROOT / "verification_bambu_closed_mounts_r26.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "regression_checks"}, indent=2))


if __name__ == "__main__":
    build()
