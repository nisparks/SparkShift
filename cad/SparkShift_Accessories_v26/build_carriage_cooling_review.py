"""Separate carriage/dock cooling ownership study; not a print release."""

import argparse
import json
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from build_modular_toolhead import ROOT, STEP, STL, box, load, volume
from build_bambu_side_fan import cylinder_x
from build_modular_toolhead import cylinder_y


def heating_mount():
    baseline = load("P17M_Bambu_Adapter_3010_REVIEW")
    ceramic = load("Hotend_Voron_Bambu_P2S").Solids()[0]
    yellow = baseline.intersect(box(-16, 16, 11.5, 32.05, -26, -17.2794))
    yellow = yellow.fuse(box(-9.25, 9.25, 11.5, 14.3, -65.93, -24))
    for x in (-5.657, 5.657):
        for y in (17.043, 28.357):
            yellow = yellow.fuse(cq.Solid.makeCylinder(2.41, 8.7206, cq.Vector(x, y, -26), cq.Vector(0, 0, 1)))
    retainers, hardware = [], []
    for sign in (-1, 1):
        x0, x1 = (9.1, 14.75) if sign > 0 else (-14.75, -9.1)
        lip0, lip1 = (8.4, 14.75) if sign > 0 else (-14.75, -8.4)
        yellow = yellow.fuse(box(x0, x1, 11.5, 18.5, -47.75, -24))
        retainer = box(lip0, lip1, 17.3, 21.5, -47.75, -36.25).cut(ceramic)
        for z in (-39, -45):
            x = sign * 12
            yellow = yellow.cut(cylinder_y(x, z, 11.4, 14.5, 1.55))
            yellow = yellow.cut(cylinder_y(x, z, 14.5, 18.6, 1.4))
            retainer = retainer.cut(cylinder_y(x, z, 17.2, 21.6, 1.4))
            hardware.extend([
                cylinder_y(x, z, 11.5, 14.5, 1.75).cut(cylinder_y(x, z, 11.4, 14.6, 1.05)),
                cylinder_y(x, z, 11.5, 21.5, 1.25).fuse(cylinder_y(x, z, 21.5, 24, 2.25)),
            ])
        yellow = yellow.cut(retainer)
        retainers.append(retainer.clean())
    return yellow.clean(), retainers, cq.Compound.makeCompound(hardware)


def cooling_unit(sign):
    fan = load("P17M_Fan_Reference").translate((0, -40.93, 37.5))
    fan = fan.rotate((0, 0, 0), (0, 0, 1), 90).translate((-30, 36, -36))
    outer0 = cq.Workplane("YZ", origin=(-25, 36, -36)).rect(29, 25).val()
    outer1 = cq.Workplane("YZ", origin=(-9, 25, -40.5)).rect(12, 16).val()
    inner0 = cq.Workplane("YZ", origin=(-25.1, 36, -36)).rect(25, 21).val()
    inner1 = cq.Workplane("YZ", origin=(-8.9, 25, -40.5)).rect(9, 13).val()
    duct = cq.Solid.makeLoft([outer0, outer1]).cut(cq.Solid.makeLoft([inner0, inner1]))
    for y in (24, 48):
        duct = duct.fuse(cylinder_x(y, -24, -25, -21, 2.75))
        duct = duct.cut(cylinder_x(y, -24, -25.1, -20.9, 1.4))
    if sign > 0:
        fan = fan.mirror("YZ")
        duct = duct.mirror("YZ")
    return fan.clean(), duct.clean()


def build(core_path):
    core = cq.importers.importStep(str(core_path)).val()
    hotend = cq.Compound.makeCompound(load("Hotend_Voron_Bambu_P2S").Solids()[:6])
    blue = load("P17M_Reusable_Carrier_3010_REVIEW")
    dock = load("P25_SparkShift_3010_Dock")
    obstacles = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
        "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
    )}
    obstacles.update(core=core, hotend=hotend)
    fan, duct = cooling_unit(-1)
    dock_fan, dock_duct = cooling_unit(1)
    yellow, retainers, retention_hardware = heating_mount()
    bracket = box(-39, -36, 1.5, 15, -56.5, -18)
    bracket = bracket.fuse(box(-39, -36, 12, 51, -22, -18))
    for z in (-22.4794, -53.0794):
        bracket = bracket.fuse(cylinder_x(5.3, z, -36.1, -22.3, 3))
        bracket = bracket.cut(cylinder_x(5.3, z, -39.1, -22.2, 1.7))
    for y in (24, 48):
        bracket = bracket.fuse(cylinder_x(y, -24, -39, -35, 2.75))
        bracket = bracket.cut(cylinder_x(y, -24, -39.1, -34.9, 1.4))
    bracket = bracket.clean()
    upper = blue.intersect(box(-16, 16, 10, 36, -19.2794, 50)).clean()
    shelf_hardware = []
    for x in (-6, 6):
        z = -22.75
        upper = upper.fuse(cylinder_y(x, z, 29, 35.93, 3))
        upper = upper.fuse(box(x-3, x+3, 32.05, 35.93, -22.75, -18.5))
        yellow = yellow.cut(cylinder_y(x, z, 29, 32.15, 3.1))
        yellow = yellow.fuse(cylinder_y(x, z, 11.5, 29, 1.46))
        yellow = yellow.cut(cylinder_y(x, z, 11.4, 14.5, 1.55))
        yellow = yellow.cut(cylinder_y(x, z, 14.5, 29.1, 1.4))
        upper = upper.cut(cylinder_y(x, z, 28.9, 32, 1.4))
        upper = upper.cut(cylinder_y(x, z, 32, 36, 2.4))
        shelf_hardware.extend([
            cylinder_y(x, z, 11.5, 14.5, 1.75).cut(cylinder_y(x, z, 11.4, 14.6, 1.05)),
            cylinder_y(x, z, 12, 32, 1.25).fuse(cylinder_y(x, z, 32, 34.5, 2.25)),
        ])
    yellow, upper = yellow.clean(), upper.clean()
    dock_modified = dock
    dock_bracket = box(35, 38, 21, 64, -26.75, -21.25)
    for z in (-30, -42):
        dock_modified = dock_modified.fuse(cylinder_x(60, z, 16.9, 23, 3))
        dock_modified = dock_modified.cut(cylinder_x(60, z, 16.9, 20, 1.55))
        dock_modified = dock_modified.cut(cylinder_x(60, z, 20, 23.1, 1.4))
        dock_bracket = dock_bracket.fuse(box(23, 38, 56, 64, z-3, z+3))
    dock_bracket = dock_bracket.fuse(box(35, 38, 56, 64, -45, -21.25))
    for z in (-30, -42):
        dock_bracket = dock_bracket.cut(cylinder_x(60, z, 22.9, 38.1, 1.4))
    for y in (24, 48):
        dock_bracket = dock_bracket.fuse(cylinder_x(y, -24, 35, 38, 2.75))
        dock_bracket = dock_bracket.cut(cylinder_x(y, -24, 34.9, 38.1, 1.4))
    dock_bracket, dock_modified = dock_bracket.clean(), dock_modified.clean()
    parts = {
        "Carriage_3010_Fan": fan, "Carriage_Side_Duct": duct,
        "Carriage_Bracket_Proposal": bracket, "Dock_3010_Fan": dock_fan,
        "Dock_Opposite_Side_Duct": dock_duct,
        "Bambu_Upper_Carrier_No_Front_Frame": upper,
        "Bambu_Yellow_Fixed_Heating_Mount": yellow,
        "Bambu_Fixed_Retainer_Left": retainers[0],
        "Bambu_Fixed_Retainer_Right": retainers[1],
        "Dock_Cooling_Bracket": dock_bracket,
    }
    report = {
        "status": "OWNERSHIP_AND_CLEARANCE_REVIEW_NOT_PRINT_RELEASE",
        "ownership": {
            "carriage": ["Carriage_3010_Fan", "Carriage_Side_Duct", "Carriage_Bracket_Proposal"],
            "dock": ["Dock_3010_Fan", "Dock_Opposite_Side_Duct"],
            "tool": ["Bambu_Upper_Carrier_No_Front_Frame", "Existing fixed heating assembly"],
        },
        "fan_mounting": "Only two upper fan holes; lower fan holes unused",
        "carriage_bracket_mount": "Outboard bracket with integral tubular stand-offs to existing left core X-axis fasteners at Y5.3, Z-22.4794/-53.0794; screw engagement and contact tolerance need qualification",
        "cooling": "Carriage feeds -X heatsink face; dock feeds +X face so the two supplies do not occupy the same space at pickup",
        "checks": {},
        "limitations": [
            "Carriage attachment is a proposal, not a load-qualified mount or fastener specification.",
            "Dock revision adds two outward bosses at Y60, Z-30/-42; only this separate P25 variant is modified.",
            "M2.5 insert retainers capture fixed ceramic side edges; physical ceramic load and heat-creep qualification remain required.",
            "No actual H2D release kinematics or finger envelope available; service samples are exploratory.",
            "Dock pitch, rack layout, whole-printer X travel and cable routing are not qualified.",
            "No airflow, pressure-loss, thermal or heat-creep qualification.",
            "Dock fan controls must run throughout standby and cooldown with a cooling-loss heater interlock.",
        ],
    }
    for name, shape in parts.items():
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f"Invalid part: {name}")
        checks = {n: volume(shape.intersect(o)) for n, o in obstacles.items()}
        report["checks"][name] = checks
        if name != "Bambu_Upper_Carrier_No_Front_Frame" and max(checks.values()) > 0.01:
            raise ValueError(f"{name}: {checks}")
    report["carriage_vs_dock_cooling_mm3"] = volume(
        cq.Compound.makeCompound([fan, duct, bracket]).intersect(cq.Compound.makeCompound([dock_fan, dock_duct])))
    report["dock_cooling_vs_P25_mm3"] = volume(cq.Compound.makeCompound([dock_fan, dock_duct]).intersect(dock))
    report["dock_bracket_vs_P25_mm3"] = volume(dock_bracket.intersect(dock_modified))
    report["dock_revision_valid"] = dock_modified.isValid() and len(dock_modified.Solids()) == 1
    if not report["dock_revision_valid"] or report["dock_bracket_vs_P25_mm3"] > 0.01:
        raise ValueError("Dock mount invalid or overlapping")
    report["proposed_bracket_vs_duct_mm3"] = volume(bracket.intersect(duct))
    report["internal_cooling_intersections_mm3"] = {}
    cooling_parts = {n: s for n, s in parts.items() if not n.startswith("Bambu")}
    for i, (name, shape) in enumerate(cooling_parts.items()):
        for other_name, other_shape in list(cooling_parts.items())[i + 1:]:
            key = name + "__" + other_name
            report["internal_cooling_intersections_mm3"][key] = volume(shape.intersect(other_shape))
    if max(report["internal_cooling_intersections_mm3"].values()) > 0.01:
        raise ValueError(f"Cooling assembly self-intersection: {report['internal_cooling_intersections_mm3']}")
    removable = cq.Compound.makeCompound(load("Hotend_Voron_Bambu_P2S").Solids()[3:5])
    fixed_new = cq.Compound.makeCompound([fan, duct, bracket, upper, yellow, *retainers])
    report["exploratory_service_path"] = [
        {"down_mm": down, "forward_mm": forward,
         "new_cooling_overlap_mm3": volume(removable.translate((0, forward, -down)).intersect(fixed_new))}
        for down, forward in [(d, 0) for d in range(5)] + [(4, y) for y in range(2, 42, 2)]
    ]
    moving = cq.Compound.makeCompound([fan, duct, bracket])
    stationary = cq.Compound.makeCompound([dock_fan, dock_duct])
    report["exploratory_dock_retreat_minus_y"] = [
        {"travel_mm": distance, "cooling_to_cooling_overlap_mm3": volume(
            moving.translate((0, -distance, 0)).intersect(stationary)),
         "cooling_to_parked_tool_overlap_mm3": volume(
             moving.translate((0, -distance, 0)).intersect(hotend)),
         "cooling_to_P25_overlap_mm3": volume(
             moving.translate((0, -distance, 0)).intersect(dock))}
        for distance in range(0, 62, 2)
    ]
    hardware = []
    for y in (24, 48):
        z = -24
        insert = cylinder_x(y, z, -24, -21, 1.75).cut(cylinder_x(y, z, -24.1, -20.9, 1.05))
        bolt = cylinder_x(y, z, -39, -21, 1.25).fuse(cylinder_x(y, z, -41.5, -39, 2.25))
        hardware.extend([insert, bolt])
    hardware = cq.Compound.makeCompound(hardware)
    report["fan_hardware"] = "Two upper M2.5x18 screws; user OD3.5 x L3 rear receivers at X-24..-21; opposing insertion from +X"
    for y in (24, 48):
        duct = duct.cut(cylinder_x(y, -24, -24, -20.9, 1.55))
    parts["Carriage_Side_Duct"] = duct.clean()
    report["new_hardware_external_intersections_mm3"] = {
        n: volume(hardware.intersect(o)) for n, o in obstacles.items()
    }
    if max(report["new_hardware_external_intersections_mm3"].values()) > 0.01:
        raise ValueError("Fan hardware interferes with existing parts")
    report["shelf_hardware_checks_mm3"] = {
        n: volume(cq.Compound.makeCompound(shelf_hardware).intersect(o)) for n, o in obstacles.items()
    }
    if max(report["shelf_hardware_checks_mm3"].values()) > 0.01:
        raise ValueError(f"Upper shelf fastener interference: {report['shelf_hardware_checks_mm3']}")
    dock_hardware = []
    for z in (-30, -42):
        dock_hardware.extend([
            cylinder_x(60, z, 17, 20, 1.75).cut(cylinder_x(60, z, 16.9, 20.1, 1.05)),
            cylinder_x(60, z, 18, 38, 1.25).fuse(cylinder_x(60, z, 38, 40.5, 2.25)),
        ])
    for y in (24, 48):
        dock_duct = dock_duct.cut(cylinder_x(y, -24, 20.9, 24, 1.55))
        dock_hardware.extend([
            cylinder_x(y, -24, 21, 24, 1.75).cut(cylinder_x(y, -24, 20.9, 24.1, 1.05)),
            cylinder_x(y, -24, 20, 38, 1.25).fuse(cylinder_x(y, -24, 38, 40.5, 2.25)),
        ])
    parts["Dock_Opposite_Side_Duct"] = dock_duct.clean()
    dock_hardware = cq.Compound.makeCompound(dock_hardware)
    report["dock_hardware"] = "Bracket: 2 x M2.5x20 with 2 mm engagement; fan: 2 x M2.5x18 with 3 mm engagement; all receivers OD3.5 x L3"
    report["tool_hardware"] = "Shelf clamp: 2 x M2.5x20 with 2.5 mm engagement; fixed-heating retainers: 4 x M2.5x10 with 3 mm engagement; OD3.5 x L3 receivers"
    report["retainer_bearing_finite_shift_mm2"] = [
        volume(r.translate((0, -0.001, 0)).intersect(load("Hotend_Voron_Bambu_P2S").Solids()[0])) / 0.001
        for r in retainers
    ]
    if min(report["retainer_bearing_finite_shift_mm2"]) < 1:
        raise ValueError("Fixed heating retainer lacks ceramic bearing")
    report["tool_pair_intersections_mm3"] = {
        "blue_yellow": volume(upper.intersect(yellow)),
        "left_retainer_yellow": volume(retainers[0].intersect(yellow)),
        "right_retainer_yellow": volume(retainers[1].intersect(yellow)),
    }
    if max(report["tool_pair_intersections_mm3"].values()) > 0.01:
        raise ValueError(f"Tool joint interference: {report['tool_pair_intersections_mm3']}")
    if any(max(v for k, v in sample.items() if k != "travel_mm") > 0.01
           for sample in report["exploratory_dock_retreat_minus_y"]):
        raise ValueError("The sampled dock retreat is obstructed")
    if any(sample["new_cooling_overlap_mm3"] > 0.01
           for sample in report["exploratory_service_path"]):
        raise ValueError("The sampled service path is obstructed")
    report["fan_options"] = {}
    for size, radius in [(30, 13.6), (25, 11.25)]:
        envelope = box(-35, -25, 36-size/2, 36+size/2, -36-size/2, -36+size/2)
        report["fan_options"][str(size)+"10"] = {
            "body_size_mm": [size, size, 10],
            "center_mm": [-30, 36, -36],
            "body_clashes_mm3": {n: volume(envelope.intersect(o)) for n, o in obstacles.items()},
            "selection": "Preferred pending mount and thermal qualification" if size == 30 else "Smaller fallback; different shroud required",
        }
    report["dual_2510"] = {
        "status": "NOT_SELECTED",
        "reason": "Opposite-side carriage pull fan would occupy dock cooling space at pickup. Requires a separate dock interface and thermal justification.",
    }
    assembly = cq.Assembly(name="Carriage and dock cooling ownership review")
    for name, shape in parts.items():
        color = cq.Color(0.15, 0.5, 0.75) if name.startswith("Carriage") else cq.Color(0.9, 0.65, 0.1)
        assembly.add(shape, name=name, color=color)
        cq.exporters.export(shape, str(STEP / f"CoolingOwnership_{name}_CONCEPT.step"))
        mesh_path = STL / f"CoolingOwnership_{name}_CONCEPT.stl"
        cq.exporters.export(shape, str(mesh_path), tolerance=0.03, angularTolerance=0.1)
        mesh = trimesh.load_mesh(mesh_path)
        if not mesh.is_watertight or len(mesh.split(only_watertight=False)) != 1:
            raise ValueError(f"{name}: review mesh is not connected and watertight")
    assembly.add(hotend, name="Bambu_reconstructed_reference")
    assembly.add(core, name="Core_reference")
    assembly.add(dock_modified, name="Dock_with_cooling_mount_bosses")
    assembly.add(hardware, name="Two_upper_M2_5_fan_fasteners")
    assembly.add(retention_hardware, name="Fixed_heating_M2_5_fasteners")
    assembly.add(cq.Compound.makeCompound(shelf_hardware), name="Upper_shelf_M2_5_fasteners")
    assembly.add(dock_hardware, name="Dock_M2_5_fasteners")
    cq.exporters.export(dock_modified, str(STEP / "P25_Cooling_Boss_Variant_CONCEPT.step"))
    path = STEP / "Carriage_And_Dock_Cooling_CONCEPT.step"
    assembly.export(str(path))
    persisted = cq.importers.importStep(str(path)).val()
    if not persisted.isValid() or len(persisted.Solids()) != 142:
        raise ValueError("Comparison export is incomplete")
    report["export_solid_count"] = len(persisted.Solids())
    figure = plt.figure(figsize=(14, 10))
    axes = figure.add_subplot(projection="3d")
    def draw(shape, color, opacity=1):
        vertices, triangles = shape.tessellate(0.15)
        points = np.array([v.toTuple() for v in vertices])
        faces = points[np.array(triangles)]
        axes.add_collection3d(Poly3DCollection(faces, facecolor=color, alpha=opacity,
                                              edgecolor="none"))
    draw(core, "#89939f", 0.3)
    draw(hotend, "#b9bfc8")
    draw(upper, "#3989b6", 0.65)
    for name, shape in parts.items():
        if name == "Bambu_Upper_Carrier_No_Front_Frame":
            continue
        draw(shape, "#3b88bf" if name.startswith("Carriage") else "#d8a636",
             0.6 if "Duct" in name else 1)
    axes.set(xlim=(-45, 45), ylim=(-15, 65), zlim=(-85, 50),
             xlabel="X (mm)", ylabel="Y (mm)", zlabel="Z (mm)")
    axes.set_box_aspect((90, 80, 135))
    axes.view_init(elev=20, azim=125)
    figure.suptitle("COOLING OWNERSHIP STUDY - NOT PRINT READY\nBlue: carriage 3010 / Yellow: dock cooling\nFront fan frame removed; mounting details incomplete")
    figure.savefig(ROOT / "images" / "33_carriage_dock_cooling_study.png", dpi=140)
    plt.close(figure)
    (ROOT / "verification_carriage_cooling_review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-reference", type=Path, required=True)
    build(parser.parse_args().core_reference)
