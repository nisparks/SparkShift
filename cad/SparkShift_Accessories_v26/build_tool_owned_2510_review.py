"""One-piece Bambu toolhead with a tool-owned 2510 in the approved 45 mm envelope."""

import argparse
import json
from pathlib import Path

import cadquery as cq
import trimesh

from build_modular_toolhead import ROOT, STEP, STL, HOTEND_AXES, box, cylinder_y, load, volume, primitives

FAN_X_SHIFT = 0.65


def cylinder_x(y, z, x0, x1, radius):
    return cq.Solid.makeCylinder(radius, x1 - x0, cq.Vector(x0 + FAN_X_SHIFT, y, z), cq.Vector(1, 0, 0))


def build(core_path):
    core = cq.importers.importStep(str(core_path)).val()
    blue = load("P17M_Reusable_Carrier_3010_REVIEW").intersect(
        box(-16, 16, 10, 36, -19.2794, 50))
    yellow = load("Bambu_Reversed_Yellow_Reversed_Adapter_REVIEW")
    fan_hole_blank = (cq.Workplane("XY").add(yellow).section(-23.8)
                      .wires().toPending().extrude(-2.2, combine=False).val())
    hotend = load("Bambu_Reversed_Reversed_Hotend_Reference_REVIEW")
    old_hardware = load("Bambu_Reversed_M2_5_Hardware_REVIEW")
    shelf_blank = cq.Shape.cast(primitives.prism_xy_r([
        (-12.4, 11.5), (12.4, 11.5), (12.4, 26.8), (15, 29.4),
        (15, 32.05), (-15, 32.05), (-15, 29.4), (-12.4, 26.8),
    ], [1.8, 1.8, 1.2, 1.2, 0, 0, 1.2, 1.2], -26, -17.2794))
    apron_blank = box(-9.25, 9.25, 31.1, 37.9, -65.93, -24)
    cleanup_domain = shelf_blank.fuse(apron_blank)
    hardware = list(old_hardware.Solids()[:8])
    for x in (-6, 6):
        yellow = yellow.fuse(cylinder_y(x, -22.75, 11.5, 29, 1.56))
        yellow = yellow.fuse(cylinder_y(x, -22.75, 29, 32.15, 3.11).intersect(cleanup_domain))
        yellow = yellow.fuse(cylinder_y(x, -22.75, 32, 38, 2.51).intersect(cleanup_domain))
    for x in (-12, 12):
        yellow = yellow.fuse(cylinder_y(x, -25.5, 11.5, 32.05, 1.61).intersect(fan_hole_blank))
    old_hardware = cq.Compound.makeCompound(hardware)
    references = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
        "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount",
        "P24_EBB42_Controller_Mount", "P25_SparkShift_3010_Dock",
    )}
    blue = blue.cut(references["P18_Tool_docking_backplate_3010"]).clean()
    yellow = yellow.cut(blue).clean()
    fan_center_z = -35.3
    fan_center_y = 25.5
    fan_axes_y = (fan_center_y - 10, fan_center_y + 10)
    upper_axis_z = fan_center_z + 10
    fan_bottom, fan_top = fan_center_z - 12.5, fan_center_z + 12.5
    fan_envelope = box(10.8 + FAN_X_SHIFT, 20.8 + FAN_X_SHIFT, fan_center_y - 12.5, fan_center_y + 12.5, fan_bottom, fan_top)
    fan = fan_envelope.cut(cylinder_x(fan_center_y, fan_center_z, 10.7, 20.9, 11))
    fan = fan.fuse(cylinder_x(fan_center_y, fan_center_z, 11.3, 20.3, 4))
    fan = fan.fuse(box(18.8 + FAN_X_SHIFT, 20.3 + FAN_X_SHIFT, fan_center_y - 1, fan_center_y + 1, fan_bottom, fan_top))
    for y in fan_axes_y:
        for z in (upper_axis_z, fan_center_z - 10):
            fan = fan.cut(cylinder_x(y, z, 10.7, 20.9, 1.4))
    fan = fan.clean()

    # Relief is confined to the new adapter; core/CPAP/dock remain untouched.
    yellow = yellow.cut(box(10.55 + FAN_X_SHIFT, 21.05 + FAN_X_SHIFT, fan_center_y - 12.75, fan_center_y + 12.75, fan_bottom - 0.25, fan_top + 0.25))
    mount = box(6.8 + FAN_X_SHIFT, 9.25 + FAN_X_SHIFT, fan_axes_y[1] - 3.5, fan_axes_y[1], upper_axis_z - 2.5, upper_axis_z + 2)
    inserts, screws = [], []
    for y in fan_axes_y:
        mount = mount.fuse(cylinder_x(y, upper_axis_z, 6.8, 10.8, 2.5))
        inserts.append(cylinder_x(y, upper_axis_z, 6.8, 9.8, 1.75).cut(
            cylinder_x(y, upper_axis_z, 6.7, 9.9, 1.05)))
        screws.append(cylinder_x(y, upper_axis_z, 6.8, 20.8, 1.25).fuse(
            cylinder_x(y, upper_axis_z, 20.8, 21.6, 2.25)))
    blue = blue.cut(cylinder_x(fan_axes_y[1], upper_axis_z, 6.6, 11, 2.7))
    mount = mount.cut(blue)
    yellow = yellow.fuse(mount)
    body = blue.fuse(yellow).clean()
    for x in (-6, 6):
        body = body.cut(cylinder_y(x, -19.26, 31, 37, 2.28))
    for y in fan_axes_y:
        body = body.cut(cylinder_x(y, upper_axis_z, -16, 6.8, 2.2))
        body = body.cut(cylinder_x(y, upper_axis_z, 6.7, 9.8, 1.55))
        body = body.cut(cylinder_x(y, upper_axis_z, 9.8, 10.9, 1.4))
    body = body.clean()
    screws = cq.Compound.makeCompound(screws)
    inserts = cq.Compound.makeCompound(inserts)
    report = {
        "status": "CAD_REVIEW_NOT_PRINT_OR_THERMALLY_QUALIFIED",
        "ownership": "One-piece hotend-specific printed toolhead; one 2510 remains on each tool, including when parked",
        "airflow": "From +X side toward -X through heatsink; fan rotation/strut side must match actual airflow arrow",
        "fan_reference": "Generic 25x25x10 mm body, assumed 20 mm mounting pitch and diameter2.8 holes; not vendor CAD",
        "fan_center_mm": [15.8 + FAN_X_SHIFT, fan_center_y, fan_center_z],
        "shift_from_revision14_mm": [FAN_X_SHIFT, -4, 1],
        "shift_from_revision15_mm": [0, -4, 0],
        "fasteners": "Two upper M2.5x14 ultra-low-head screws, OD<=4.5 H<=0.8; lower mounting holes unused; actual hardware must be sourced/confirmed",
        "inserts": "M2.5 x L3 x OD3.5, inner entry X7.45, seat X7.45..10.45, outer shoulder X10.45..11.45",
        "insert_load_direction": "+X toward 1 mm printed shoulder, away from inner insertion mouth",
        "unchanged": "Physical hotend reference, core and P18/P20-P25",
        "construction": "Upper carrier and reversed Bambu mount fused into one connected printed solid; no modular shelf joint",
        "removed_hardware": "Two shelf M2.5x20 screws and two L3 inserts; no replacement joint hardware",
        "cleanup_revision": "18: obsolete clamp ears, clamp bores and 3010 bores removed; original P18 attachment passages restored; fan heatset corridors cut through entire body",
        "shroud": "None: two integrated upper mounting ears only; no duct, mask, lip, baffle or lower frame",
        "fan_inner_face_x_mm": 10.8 + FAN_X_SHIFT,
        "nominal_side_gap_to_fin_edge_mm": 2.5 + FAN_X_SHIFT,
        "heatset_installation": "Before hotend/fan assembly, from -X through diameter4.4 access corridors to the inner insert mouths",
        "limitations": [
            "Actual fan hole pitch, frame, connector and cable bend require vendor/physical confirmation.",
            "Inherited core overhangs outside X+/-22.5 are reported, not silently removed.",
            "Nominal fan-to-P22 clearance is 1.2 mm; physical tolerances and thermal movement still need assessment.",
            "Ultra-low-head screws must fit the explicit 0.8 mm head-height envelope; ordinary 1.5 mm heads exceed the width limit.",
            "No airflow, pressure-drop, heat-creep, bracket strength or physical insert qualification.",
            "Sampled rear nozzle path does not certify native H2D latch/finger access.",
            "Dock power/fan control must remain available after carriage separation; no electrical or firmware implementation is implied.",
            "Ten-tool rack pitch and full-machine motion are not certified by a 45 mm cross-section check.",
        ],
    }
    obstacles = dict(references, Core=core, Hotend=hotend, Existing_Hardware=old_hardware)
    report["fan_clearances_mm"] = {n: fan_envelope.distance(o) for n, o in obstacles.items()}
    if report["fan_clearances_mm"]["P22_CPAP_Lower_Plenum"] < 1.199:
        raise ValueError("Fan-to-P22 clearance is below the 1.2 mm target")
    existing_screws = cq.Compound.makeCompound([old_hardware.Solids()[i] for i in (1, 4, 7)])
    report["static_intersections_mm3"] = {}
    for name, shape in {"Fan": fan_envelope, "One_Piece_Body": body,
                        "Fan_Screws": screws, "Fan_Inserts": inserts}.items():
        checks = {n: volume(shape.intersect(existing_screws if name == "One_Piece_Body"
                                           and n == "Existing_Hardware" else o))
                  for n, o in obstacles.items()}
        report["static_intersections_mm3"][name] = checks
        if max(checks.values()) > 0.01:
            raise ValueError(f"{name} collision: {checks}")
    report["screws_to_print_mm3"] = volume(screws.intersect(body))
    report["fan_to_print_mm3"] = volume(fan_envelope.intersect(body))
    if max(report["screws_to_print_mm3"], report["fan_to_print_mm3"]) > 0.01:
        raise ValueError(f"Fan mounting interference: screws={report['screws_to_print_mm3']}, fan={report['fan_to_print_mm3']}")
    report["insert_seat_checks"] = []
    for y in fan_axes_y:
        shoulder = cylinder_x(y, upper_axis_z, 9.8, 10.8, 2.5).cut(
            cylinder_x(y, upper_axis_z, 9.8, 10.8, 1.4))
        surround = cylinder_x(y, upper_axis_z, 6.8, 9.8, 2.5).cut(
            cylinder_x(y, upper_axis_z, 6.8, 9.8, 1.75))
        check = {"y": y, "shoulder_missing_mm3": volume(shoulder.cut(body)),
                 "surround_missing_mm3": volume(surround.cut(body)),
                 "installation_corridor_obstruction_mm3": volume(
                     cylinder_x(y, upper_axis_z, -16, 6.8, 2.2).intersect(body))}
        report["insert_seat_checks"].append(check)
        if max(v for k, v in check.items() if k != "y") > 0.001:
            raise ValueError(f"Incomplete fan heatset seat: {check}")
    report["existing_insert_shoulders_missing_mm3"] = []
    for x, z in HOTEND_AXES:
        seat = cylinder_y(x, z, 31.1, 33.9, 2.5).cut(cylinder_y(x, z, 31.1, 33.9, 1.4))
        report["existing_insert_shoulders_missing_mm3"].append(volume(seat.cut(body)))
    if max(report["existing_insert_shoulders_missing_mm3"]) > 0.001:
        raise ValueError("Fan revision damaged an existing heatset shoulder")
    tool = cq.Compound.makeCompound([body, hotend, old_hardware, fan_envelope, screws, inserts])
    b = tool.BoundingBox()
    report["complete_tool_bounds_x_mm"] = [b.xmin, b.xmax]
    if b.xmin < -22.50001 or b.xmax > 22.50001:
        raise ValueError("Tool exceeds the 45 mm boundary")
    b = cq.Compound.makeCompound([tool, *references.values()]).BoundingBox()
    report["tool_and_accessory_bounds_x_mm_excluding_inherited_core"] = [b.xmin, b.xmax]
    if b.xmin < -22.50001 or b.xmax > 22.50001:
        raise ValueError("Accessory exceeds the 45 mm boundary")
    report["inherited_core_overhangs"] = [
        {"solid": i, "xmin": s.BoundingBox().xmin, "xmax": s.BoundingBox().xmax}
        for i, s in enumerate(core.Solids())
        if s.BoundingBox().xmin < -22.50001 or s.BoundingBox().xmax > 22.50001
    ]
    # Test newly added cooling against neighboring parked geometry at minimum 45 mm pitch.
    new_cooling = cq.Compound.makeCompound([fan_envelope, screws, inserts, mount])
    neighbor = cq.Compound.makeCompound([tool, references["P18_Tool_docking_backplate_3010"],
                                       references["P25_SparkShift_3010_Dock"]])
    report["adjacent_45mm_pitch_overlap_mm3"] = {
        str(offset): volume(new_cooling.intersect(neighbor.translate((offset, 0, 0))))
        for offset in (-45, 45)
    }
    if max(report["adjacent_45mm_pitch_overlap_mm3"].values()) > 0.01:
        raise ValueError("Cooling collides with adjacent tool/dock at 45 mm pitch")
    removable = cq.Compound.makeCompound(hotend.Solids()[3:5])
    fixed_new = cq.Compound.makeCompound([body, old_hardware, fan_envelope, screws, inserts])
    report["removed_tool_sampled_nozzle_path"] = []
    for down, rear in [(d, 0) for d in range(5)] + [(4, d) for d in range(2, 42, 2)]:
        overlap = volume(removable.translate((0, -rear, -down)).intersect(fixed_new))
        report["removed_tool_sampled_nozzle_path"].append(
            {"down_mm": down, "rearward_mm": rear, "overlap_mm3": overlap})
        if overlap > 0.01:
            raise ValueError(f"Fan obstructs sampled nozzle service: {down}/{rear}/{overlap}")
    assembly = cq.Assembly(name="18 One piece Bambu toolhead - approved side 2510")
    shapes = {
        "One_Piece_Bambu_Toolhead": (body, cq.Color(0.9, 0.65, 0.1)),
        "Single_Tool_Owned_2510_Nominal_Reference": (fan, cq.Color(0.16, 0.16, 0.18)),
        "Reversed_Bambu_Reference": (hotend, cq.Color(0.65, 0.65, 0.65)),
        "Existing_Tool_M2_5_Hardware": (old_hardware, cq.Color(0.4, 0.4, 0.4)),
        "Two_Upper_M2_5_Low_Head_Screws": (screws, cq.Color(0.35, 0.35, 0.35)),
        "Two_Inner_Entry_L3_Heatsets": (inserts, cq.Color(0.75, 0.52, 0.16)),
    }
    for name, (shape, color) in shapes.items():
        if not shape.isValid():
            raise ValueError(f"Invalid {name}")
        assembly.add(shape, name=name, color=color)
        cq.exporters.export(shape, str(STEP / f"Tool2510_{name}_REVIEW.step"))
    if len(body.Solids()) != 1:
        raise ValueError("One-piece toolhead is disconnected")
    mesh_path = STL / "Tool2510_One_Piece_Bambu_Toolhead_REVIEW.stl"
    cq.exporters.export(body, str(mesh_path), tolerance=0.03, angularTolerance=0.1)
    mesh = trimesh.load_mesh(mesh_path)
    if not mesh.is_watertight or len(mesh.split(only_watertight=False)) != 1:
        raise ValueError("One-piece toolhead mesh is disconnected or not watertight")
    assembly.add(core, name="Unchanged_Core_Reference", color=cq.Color(0.5, 0.52, 0.55))
    for name, shape in references.items():
        assembly.add(shape, name=name, color=cq.Color(0.22, 0.4, 0.32))
    output = STEP / "18_One_Piece_Bambu_Toolhead_2510_REVIEW.step"
    assembly.export(str(output))
    imported = cq.importers.importStep(str(output)).val()
    expected = sum(len(s.Solids()) for s in [core, *references.values(), *(v[0] for v in shapes.values())])
    if not imported.isValid() or len(imported.Solids()) != expected:
        raise ValueError("Incomplete STEP export")
    report["export_solids"] = expected
    (ROOT / "verification_tool_owned_2510.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-reference", type=Path, required=True)
    build(parser.parse_args().core_reference)
