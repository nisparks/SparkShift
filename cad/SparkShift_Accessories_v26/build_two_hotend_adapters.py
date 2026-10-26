"""Build interchangeable review adapters without changing the common blue carrier."""

import argparse
import json
from pathlib import Path

import cadquery as cq
import trimesh

from build_modular_toolhead import FAN_AXES, HOTEND_AXES, ROOT, STEP, STL, box, cylinder_y, load, volume

RETAINER_AXES = [(x, z) for x in (-12, 12) for z in (-39, -45)]


def shared_seats(shape):
    for x, z in FAN_AXES:
        # Move the receivers forward, beyond the Red Lizard fins.
        shape = shape.fuse(cylinder_y(x, z, 29, 32.05, 2.65))
        shape = shape.cut(cylinder_y(x, z, 28.9, 31, 1.4))
        shape = shape.cut(cylinder_y(x, z, 31, 32.15, 1.1))
        # Rear-open access to the short insert, rather than a long blind tunnel.
        shape = shape.cut(cylinder_y(x, z, 11.4, 29, 2.0))
    return shape.clean()


def build(core_path):
    blue = load("P17M_Reusable_Carrier_3010_REVIEW")
    baseline = load("P17M_Bambu_Adapter_3010_REVIEW")
    red_reference = load("P17M_RedLizard_Hotend_Reference")
    bambu_solids = load("Hotend_Voron_Bambu_P2S").Solids()
    bambu_reference = cq.Compound.makeCompound(bambu_solids[:6])
    bambu = shared_seats(baseline)
    # Close the abandoned direct mounting holes; side retainers take the load.
    for x, z in HOTEND_AXES:
        bambu = bambu.fuse(cylinder_y(x, z, 11.5, 14.3, 1.46))
    retainers = []
    for sign in (-1, 1):
        x0, x1 = (9.1, 14.75) if sign > 0 else (-14.75, -9.1)
        lip0, lip1 = (6, 10) if sign > 0 else (-10, -6)
        neck0, neck1 = (9.1, 10) if sign > 0 else (-10, -9.1)
        retainer = box(x0, x1, 18.5, 21.5, -47.75, -36.25)
        retainer = retainer.fuse(box(neck0, neck1, 18.5, 21.5, -52.5, -47))
        retainer = retainer.fuse(box(lip0, lip1, 18.5, 21.5, -52.5, -50.5))
        bambu = bambu.fuse(box(x0, x1, 11.5, 18.5, -46.5, -36.25))
        for z in (-39, -45):
            x = 12 * sign
            bambu = bambu.fuse(cylinder_y(x, z, 11.5, 18.5, 2.75))
            bambu = bambu.cut(cylinder_y(x, z, 11.4, 14.5, 1.55))
            bambu = bambu.cut(cylinder_y(x, z, 14.5, 18.6, 1.4))
            retainer = retainer.cut(cylinder_y(x, z, 18.4, 21.6, 1.4))
        bambu = bambu.cut(retainer)
        bridge0, bridge1 = (9.25, 15) if sign > 0 else (-15, -9.25)
        bambu = bambu.fuse(box(bridge0, bridge1, 29, 32.05, -44, -24.5))
        retainers.append(retainer.clean())
    redundant_holes = []
    for x in (-5.657, 5.657):
        for y in (17.043, 28.357):
            plug = cq.Solid.makeCylinder(2.41, 8.7206, cq.Vector(x, y, -26), cq.Vector(0, 0, 1))
            bambu = bambu.fuse(plug)
            redundant_holes.append((x, y))
    bambu = shared_seats(bambu)

    red = baseline.cut(box(-9.25, 9.25, 11.4, 32.15, -66, -17.2794))
    red = red.fuse(box(-12.4, 12.4, 11.5, 32.05, -24.2794048, -19.2794))
    red = red.fuse(baseline.intersect(box(-16, 16, 11.4, 32.15, -19.2794, -17.2794))).clean()
    pocket = cq.Solid.makeCylinder(11.15, 29.7205952, cq.Vector(0, 22.7, -54), cq.Vector(0, 0, 1))
    red = red.cut(pocket)
    for x in (-5.657, 5.657):
        for y in (17.043, 28.357):
            red = red.cut(cq.Solid.makeCylinder(1.35, 7.2, cq.Vector(x, y, -24.4), cq.Vector(0, 0, 1)))
            red = red.cut(cq.Solid.makeCylinder(2.4, 2.1, cq.Vector(x, y, -19.27940478477181), cq.Vector(0, 0, 1)))
    red = red.cut(cq.Solid.makeCylinder(2.1, 7.2, cq.Vector(0, 22.7, -24.4), cq.Vector(0, 0, 1)))
    red = shared_seats(red)
    fan = load("P17M_Fan_Reference")
    core = cq.importers.importStep(str(core_path)).val()
    external = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
        "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
    )}
    external.update(core=core, fan=fan)
    common_hardware = []
    for x, z in FAN_AXES:
        common_hardware.extend([
            cylinder_y(x, z, 29, 31, 1.6).cut(cylinder_y(x, z, 28.9, 31.1, 0.8)),
            cylinder_y(x, z, 28.43, 46.43, 1).fuse(cylinder_y(x, z, 46.43, 48.43, 1.9)),
            cylinder_y(x, z, 45.93, 46.43, 2.25).cut(cylinder_y(x, z, 45.8, 46.5, 1.1)),
        ])
    common_hardware = cq.Compound.makeCompound(common_hardware)
    bambu_hardware = []
    for x, z in RETAINER_AXES:
        insert = cylinder_y(x, z, 11.5, 14.5, 1.75).cut(cylinder_y(x, z, 11.4, 14.6, 1.05))
        screw = cylinder_y(x, z, 11.5, 21.5, 1.25).fuse(cylinder_y(x, z, 21.5, 24, 2.25))
        bambu_hardware.extend([insert, screw])
    bambu_hardware = cq.Compound.makeCompound(bambu_hardware)
    report = {
        "status": "CAD_REVIEW_PHYSICAL_QUALIFICATION_REQUIRED",
        "common_carrier": "P17M_Reusable_Carrier_3010_REVIEW; unchanged",
        "interface": {
            "seam_y_mm": 32.05,
            "shared_axes_xz_mm": FAN_AXES,
            "inserts": "4 x M2 OD3.2 x L2, rear-entry at Y29, pilot diameter2.8",
            "insert_shoulder_mm": 1.05,
            "verified_insert_surround_mm": 0.75,
            "screws": "4 x M2x18 with 0.5 mm washers, through 10 mm fan and blue carrier",
            "thread_engagement_mm": 2.0,
            "load_direction": "+Y, into the printed shoulder, opposite rear insertion opening",
        },
        "bambu_retention": {
            "hardware": "4 x M2.5x10 screws (head OD4.5 x H2.5), rear-entry user-supplied M2.5 OD3.5 x L3 heatsets, two removable edge retainers",
            "insert_entry_y_mm": 11.5,
            "insert_shoulder_y_mm": 14.5,
            "pilot_diameter_mm": 3.1,
            "retaining_wall_mm": 4.0,
            "thread_engagement_mm": 3.0,
            "axes_xz_mm": RETAINER_AXES,
            "reason": "Off-axis bosses accommodate the user's inserts without moving the hotend or cutting the core; retainers bear on ceramic outer edges",
            "removed_top_holes_xy_mm": redundant_holes,
        },
        "red_lizard_retention": "Original 4 x M2.5x8 screws into the metal heatsink; no inserts in metal threads",
        "hardware_sources": {
            "M2_short_insert_envelope": "https://www.amazon.com/kvohlum-Threaded-Inserts-Nut/dp/B0D3B4VDH4",
            "Bambu_insert": "User-supplied M2.5 x L3 x OD3.5 mm; pilot requires coupon calibration",
        },
        "parts": {},
        "limitations": [
            "CAD review only: no physical print, heat-creep, torque or repeatability qualification.",
            "M2 insert pilot must be coupon-calibrated for selected supplier and polymer.",
            "Do not substitute the old long M2.5 fan screws or old 4 mm inserts.",
            "Bambu edge retainers require physical ceramic-edge load, torque and heat-creep qualification.",
            "Bambu synthetic nozzle tip discrepancy remains; CPAP and hotend references are unchanged.",
            "Metal clearance checks retain the existing sensor top-keepout Z datum, not full sensor certification.",
            "Do not assume support-free printing from oriented exports; inspect slicer bridges and overhangs.",
        ],
    }
    outputs = {}
    for i, retainer in enumerate(retainers):
        checks = dict(external, hotend=bambu_reference, adapter=bambu, blue=blue)
        for name, other in checks.items():
            if volume(retainer.intersect(other)) > 0.001:
                raise ValueError(f"Bambu retainer {i} interferes with {name}")
        contact = volume(retainer.translate((0, -0.001, 0)).intersect(bambu_solids[0])) / 0.001
        if contact < 2:
            raise ValueError(f"Bambu retainer {i} has insufficient ceramic bearing: {contact}")
        outputs[f"P17M_Bambu_Retainer_{i+1}_V4_REVIEW"] = retainer
        report.setdefault("bambu_retainer_contact_mm2", []).append(contact)
    for label, shape, hotend in [("Bambu", bambu, bambu_reference), ("RedLizard", red, red_reference)]:
        if not shape.isValid() or len(shape.Solids()) != 1 or volume(shape) <= 0:
            raise ValueError(f"{label}: invalid or disconnected adapter")
        part = {"valid": True, "solids": 1, "volume_mm3": volume(shape), "checks": {}}
        part["checks"]["blue_overlap_mm3"] = volume(shape.intersect(blue))
        part["checks"]["hotend_overlap_mm3"] = volume(shape.intersect(hotend))
        for name, other in external.items():
            part["checks"][name + "_overlap_mm3"] = volume(shape.intersect(other))
        hardware = common_hardware if label == "RedLizard" else cq.Compound.makeCompound([common_hardware, bambu_hardware])
        for name, other in dict(external, hotend=hotend).items():
            part["checks"][name + "_hardware_overlap_mm3"] = volume(hardware.intersect(other))
        part["seats"] = []
        for x, z in FAN_AXES:
            shoulder = cylinder_y(x, z, 31, 32.05, 2.4).cut(cylinder_y(x, z, 31, 32.05, 1.1))
            surround = cylinder_y(x, z, 29, 31, 2.35).cut(cylinder_y(x, z, 29, 31, 1.6))
            seat = {
                "axis_xz_mm": [x, z],
                "missing_shoulder_mm3": volume(shoulder.cut(shape)),
                "missing_surround_mm3": volume(surround.cut(shape)),
                "blocked_pilot_mm3": volume(shape.intersect(cylinder_y(x, z, 29, 31, 1.4))),
                "blocked_shank_mm3": volume(shape.intersect(cylinder_y(x, z, 31, 32.05, 1.1))),
            }
            part["seats"].append(seat)
            if max(v for k, v in seat.items() if k != "axis_xz_mm") > 0.001:
                raise ValueError(f"{label}: incomplete seat {seat}")
        report["parts"][label] = part
        if max(part["checks"].values()) > 0.01:
            raise ValueError(f"{label}: interference {part['checks']}")
        outputs[f"P17M_{label}_Adapter_V4_REVIEW"] = shape
        outputs[f"P17M_{label}_Hardware_V4_REVIEW"] = hardware
        contact = volume(shape.intersect(blue.translate((0, -0.001, 0)))) / 0.001
        part["front_contact_finite_shift_mm2"] = contact
        if contact < 150:
            raise ValueError(f"{label}: insufficient common mating contact")
    # Verify that every retention screw actually bears on a seat, not just clears it.
    report["red_lizard_head_seating_contact_mm2"] = [
        volume(red.intersect(s.translate((0, 0, -0.001)))) / 0.001
        for s in red_reference.Solids()[8:12]
    ]
    if min(report["red_lizard_head_seating_contact_mm2"]) < 8:
        raise ValueError("A Red Lizard screw head does not seat on the shelf")
    insert_checks = []
    for x, z in RETAINER_AXES:
        shoulder = cylinder_y(x, z, 14.5, 18.5, 2.5).cut(cylinder_y(x, z, 14.5, 18.5, 1.4))
        surround = cylinder_y(x, z, 11.5, 14.5, 2.5).cut(cylinder_y(x, z, 11.5, 14.5, 1.75))
        check = {
            "axis_xz_mm": [x, z],
            "missing_retaining_wall_mm3": volume(shoulder.cut(bambu)),
            "missing_insert_surround_mm3": volume(surround.cut(bambu)),
            "blocked_pilot_mm3": volume(bambu.intersect(cylinder_y(x, z, 11.5, 14.5, 1.55))),
            "blocked_shank_mm3": volume(bambu.intersect(cylinder_y(x, z, 14.5, 18.5, 1.4))),
        }
        insert_checks.append(check)
        if max(v for k, v in check.items() if k != "axis_xz_mm") > 0.001:
            raise ValueError(f"A Bambu hotend insert seat is incomplete: {check}")
    report["bambu_hotend_insert_seats"] = insert_checks
    report["bambu_removed_top_holes_missing_material_mm3"] = [
        volume(cq.Solid.makeCylinder(2.4, 8.7206, cq.Vector(x, y, -26), cq.Vector(0, 0, 1)).cut(bambu))
        for x, y in redundant_holes
    ]
    if max(report["bambu_removed_top_holes_missing_material_mm3"]) > 0.001:
        raise ValueError("A redundant Bambu top hole remains")
    cq.exporters.export(bambu_reference, str(STEP / "P17M_Bambu_Physical_Reference_No_Screws.step"))
    report["new_metal_min_z_mm"] = min(common_hardware.BoundingBox().zmin, bambu_hardware.BoundingBox().zmin)
    if report["new_metal_min_z_mm"] < -56.6:
        raise ValueError("Hardware enters sensor top keepout Z range")
    # Export only after all interfaces pass.
    for name, shape in outputs.items():
        cq.exporters.export(shape, str(STEP / f"{name}.step"))
        if "Hardware" in name:
            continue
        cq.exporters.export(shape, str(STL / f"{name}.stl"), tolerance=0.03, angularTolerance=0.1)
        oriented = shape.rotate((0, 0, 0), (1, 0, 0), 90)
        oriented = oriented.translate((0, 0, -oriented.BoundingBox().zmin))
        path = STL / f"{name}_PRINT.stl"
        cq.exporters.export(oriented, str(path), tolerance=0.03, angularTolerance=0.1)
        mesh = trimesh.load_mesh(path)
        if not mesh.is_watertight or len(mesh.split(only_watertight=False)) != 1 or abs(mesh.bounds[0, 2]) > 0.01:
            raise ValueError(f"{name}: invalid print mesh")
        report["parts"][name.split("_")[1]]["mesh_watertight"] = True
    comparison = cq.Assembly(name="Two hotend adapters V4 - comparison offsets only")
    for label, hotend, offset in [("RedLizard", red_reference, -45), ("Bambu", bambu_reference, 45)]:
        location = cq.Location(cq.Vector(offset, 0, 0))
        comparison.add(blue, name=f"{label}_common_blue", loc=location, color=cq.Color(0.15, 0.5, 0.75))
        comparison.add(outputs[f"P17M_{label}_Adapter_V4_REVIEW"], name=f"{label}_yellow_adapter",
                       loc=location, color=cq.Color(0.9, 0.65, 0.1))
        comparison.add(hotend, name=f"{label}_hotend_reference", loc=location)
        comparison.add(fan, name=f"{label}_fan_reference", loc=location)
        comparison.add(outputs[f"P17M_{label}_Hardware_V4_REVIEW"], name=f"{label}_hardware", loc=location)
        if label == "Bambu":
            for i, retainer in enumerate(retainers):
                comparison.add(retainer, name=f"Bambu_edge_retainer_{i+1}", loc=location, color=cq.Color(0.9, 0.65, 0.1))
    comparison_path = STEP / "Two_Hotend_Adapters_V4_Comparison_REVIEW.step"
    comparison.export(str(comparison_path))
    reimported = cq.importers.importStep(str(comparison_path)).val()
    report["comparison_step_solid_count"] = len(reimported.Solids())
    if len(reimported.Solids()) != 59 or not reimported.isValid():
        raise ValueError("The persisted comparison assembly is incomplete")
    (ROOT / "verification_two_hotend_adapters.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-reference", type=Path, required=True)
    build(parser.parse_args().core_reference)
