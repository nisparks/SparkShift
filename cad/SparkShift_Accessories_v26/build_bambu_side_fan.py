"""Service-access Bambu concept: side 2510, fixed heating mount, open front."""

import argparse
import json
from pathlib import Path

import cadquery as cq
import trimesh

from build_modular_toolhead import ROOT, STEP, STL, box, cylinder_y, load, volume


def cylinder_x(y, z, x0, x1, radius):
    return cq.Solid.makeCylinder(radius, x1 - x0, cq.Vector(x0, y, z), cq.Vector(1, 0, 0))


def check_clear(name, shape, obstacles):
    result = {key: volume(shape.intersect(other)) for key, other in obstacles.items()}
    if max(result.values(), default=0) > 0.01:
        raise ValueError(f"{name} interference: {result}")
    return result


def build(core_path):
    old_blue = load("P17M_Reusable_Carrier_3010_REVIEW")
    baseline = load("P17M_Bambu_Adapter_3010_REVIEW")
    hotend = load("Hotend_Voron_Bambu_P2S").Solids()
    physical = cq.Compound.makeCompound(hotend[:6])
    core = cq.importers.importStep(str(core_path)).val()
    external = {name: load(name) for name in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet",
        "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
        "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
    )}
    external["core"] = core
    # The original common upper interface is retained; the front fan frame is not.
    blue = old_blue.intersect(box(-16, 16, 10, 36, -19.2794, 50)).clean()
    yellow = baseline.intersect(box(-16, 16, 11.5, 32.05, -26, -17.2794))
    yellow = yellow.fuse(box(-9.25, 9.25, 11.5, 14.3, -65.93, -24))
    for x in (-5.657, 5.657):
        for y in (17.043, 28.357):
            yellow = yellow.fuse(cq.Solid.makeCylinder(
                2.41, 8.7206, cq.Vector(x, y, -26), cq.Vector(0, 0, 1)))

    hardware = []
    retainers = []
    retention_axes = [(x, z) for x in (-12, 12) for z in (-39, -45)]
    for sign in (-1, 1):
        x0, x1 = (9.1, 14.75) if sign > 0 else (-14.75, -9.1)
        lip0, lip1 = (8.4, 14.75) if sign > 0 else (-14.75, -8.4)
        yellow = yellow.fuse(box(x0, x1, 11.5, 18.5, -47.75, -24))
        retainer = box(lip0, lip1, 17.3, 21.5, -47.75, -36.25).cut(hotend[0])
        for z in (-39, -45):
            x = sign * 12
            yellow = yellow.cut(cylinder_y(x, z, 11.4, 14.5, 1.55))
            yellow = yellow.cut(cylinder_y(x, z, 14.5, 18.6, 1.4))
            retainer = retainer.cut(cylinder_y(x, z, 17.2, 21.6, 1.4))
            insert = cylinder_y(x, z, 11.5, 14.5, 1.75).cut(cylinder_y(x, z, 11.4, 14.6, 1.05))
            screw = cylinder_y(x, z, 11.5, 21.5, 1.25).fuse(cylinder_y(x, z, 21.5, 24, 2.25))
            hardware.extend([insert, screw])
        yellow = yellow.cut(retainer)
        retainers.append(retainer.clean())

    # Mount yellow to the upper blue shelf independently of any fan screws.
    for x in (-10.5, 10.5):
        y = 29
        yellow = yellow.fuse(cq.Solid.makeCylinder(2.75, 4.7206, cq.Vector(x, y, -24), cq.Vector(0, 0, 1)))
        yellow = yellow.cut(cq.Solid.makeCylinder(1.55, 3.1, cq.Vector(x, y, -24.1), cq.Vector(0, 0, 1)))
        yellow = yellow.cut(cq.Solid.makeCylinder(1.4, 4, cq.Vector(x, y, -21), cq.Vector(0, 0, 1)))
        blue = blue.cut(cq.Solid.makeCylinder(1.4, 8, cq.Vector(x, y, -18), cq.Vector(0, 0, 1)))
    yellow = yellow.clean()

    # 25 x 25 x 10 envelope, inlet from -X, outlet toward the fin channels.
    fan = box(-26, -16, 22.5, 47.5, -50, -25).cut(cylinder_x(35, -37.5, -26.1, -15.9, 11.25))
    for y in (25, 45):
        for z in (-47.5, -27.5):
            fan = fan.cut(cylinder_x(y, z, -26.1, -15.9, 1.4))
    inlet = cq.Workplane("YZ", origin=(-16, 35, -37.5)).rect(24, 24).val()
    outlet = cq.Workplane("YZ", origin=(-9, 25, -40.5)).rect(12, 16).val()
    inner_in = cq.Workplane("YZ", origin=(-16.1, 35, -37.5)).rect(21, 21).val()
    inner_out = cq.Workplane("YZ", origin=(-8.9, 25, -40.5)).rect(9, 13).val()
    shroud = cq.Solid.makeLoft([inlet, outlet]).cut(cq.Solid.makeLoft([inner_in, inner_out]))
    # Only the top two fan holes are used; the lower edge is unsupported and open.
    yellow = yellow.fuse(box(-14, -9, 22, 48, -25, -22))
    for y in (25, 45):
        z = -27.5
        yellow = yellow.fuse(cylinder_x(y, z, -14, -10, 2.75))
        yellow = yellow.cut(cylinder_x(y, z, -13, -9.9, 1.55))
        yellow = yellow.cut(cylinder_x(y, z, -14.1, -13, 1.4))
        shroud = shroud.fuse(cylinder_x(y, z, -16, -14, 2.75))
        shroud = shroud.cut(cylinder_x(y, z, -16.1, -13.9, 1.4))
        hardware.extend([
            cylinder_x(y, z, -13, -10, 1.75).cut(cylinder_x(y, z, -13.1, -9.9, 1.05)),
            cylinder_x(y, z, -26, -10, 1.25).fuse(cylinder_x(y, z, -28.5, -26, 2.25)),
        ])
    yellow = yellow.clean()
    shroud = shroud.clean()
    shapes = {"Upper_Carrier": blue, "Yellow_Heating_Mount": yellow,
              "Retainer_Left": retainers[0], "Retainer_Right": retainers[1],
              "2510_Fan_Envelope": fan, "Side_Shroud": shroud}
    report = {
        "status": "SERVICE_LAYOUT_REVIEW_NOT_PRINT_RELEASE",
        "fan": {"size_mm": [25, 25, 10], "center_mm": [-21, 35, -37.5],
                "flow": "+X through fin channels; opposite side exhaust",
                "mounting": "Two upper M2.5x16 screws only, axes Y25/45 Z-27.5; user OD3.5 x L3 inserts installed from +X",
                "lower_mounts": "No lower ears or fasteners; generic fan retains its unused factory holes",
                "reference": "Generic envelope, not a selected fan or measured performance"},
        "retention": "M2.5 x L3 x OD3.5 user heatsets; rear installation; M2.5x10 retainer screws",
        "removed_bambu_top_holes": 4,
        "parts": {},
        "limitations": [
            "Exploratory service layout, not a qualified printable assembly.",
            "Two-top-bolt fan bracket needs vibration and stiffness qualification.",
            "Upper shelf fastener hardware and access are not qualified.",
            "Reconstructed Bambu reference does not establish exact H2D latch kinematics.",
            "No cooling, thermal, strength, dock-spacing or full motion qualification.",
        ],
    }
    for name, shape in shapes.items():
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f"{name}: invalid or disconnected")
        obstacles = dict(external)
        if name == "Upper_Carrier":
            obstacles.pop("P18_Tool_docking_backplate_3010")
            report["inherited_upper_P18_overlap_mm3"] = volume(shape.intersect(external["P18_Tool_docking_backplate_3010"]))
        checks = check_clear(name, shape, obstacles)
        if name != "Upper_Carrier":
            checks.update(check_clear(name, shape, {"hotend": physical, "blue": blue}))
        report["parts"][name] = {"volume_mm3": volume(shape), "clashes_mm3": checks}
    for i, retainer in enumerate(retainers):
        report["parts"][f"Retainer_{i}"] = {
            "bearing_mm2": volume(retainer.translate((0, -0.001, 0)).intersect(hotend[0])) / 0.001,
            "adapter_overlap_mm3": volume(retainer.intersect(yellow)),
        }
    report["fan_bracket_clearances_mm3"] = {
        "fan_yellow": volume(fan.intersect(yellow)),
        "shroud_yellow": volume(shroud.intersect(yellow)),
        "fan_shroud": volume(fan.intersect(shroud)),
    }
    if max(report["fan_bracket_clearances_mm3"].values()) > 0.01:
        raise ValueError(f"Fan mount overlaps: {report['fan_bracket_clearances_mm3']}")
    report["new_hardware_obstacles_mm3"] = check_clear(
        "New hardware", cq.Compound.makeCompound(hardware), dict(external, hotend=physical, blue=blue))
    # Conservative front withdrawal sweep after a short vertical disengagement.
    removable = cq.Compound.makeCompound([hotend[3], hotend[4]])
    service_checks = []
    for down in (0, 1, 2, 3, 4):
        position = removable.translate((0, 0, -down))
        service_checks.append({"down_mm": down, "forward_mm": 0,
                               "new_parts_overlap_mm3": sum(volume(position.intersect(s)) for s in shapes.values())})
    for forward in range(2, 42, 2):
        position = removable.translate((0, forward, -4))
        service_checks.append({"down_mm": 4, "forward_mm": forward,
                               "new_parts_overlap_mm3": sum(volume(position.intersect(s)) for s in shapes.values())})
    report["sampled_removal_path"] = service_checks
    report["sampled_path_clear"] = max(c["new_parts_overlap_mm3"] for c in service_checks) < 0.01
    report["limitations"].append("Sampled nozzle path excludes stationary vendor assembly; it is not proof of the real release sequence.")
    for name, shape in shapes.items():
        cq.exporters.export(shape, str(STEP / f"Bambu_Side2510_{name}_CONCEPT.step"))
        path = STL / f"Bambu_Side2510_{name}_CONCEPT.stl"
        cq.exporters.export(shape, str(path), tolerance=0.03, angularTolerance=0.1)
        mesh = trimesh.load_mesh(path)
        report["parts"][name]["mesh_watertight"] = bool(mesh.is_watertight)
        report["parts"][name]["mesh_components"] = len(mesh.split(only_watertight=False))
        if not mesh.is_watertight or len(mesh.split(only_watertight=False)) != 1:
            raise ValueError(f"{name}: invalid review mesh")
    assembly = cq.Assembly(name="Bambu side 2510 service concept")
    for name, shape in shapes.items():
        color = cq.Color(0.15, 0.5, 0.75) if name == "Upper_Carrier" else cq.Color(0.9, 0.65, 0.1)
        if "Fan" in name:
            color = cq.Color(0.2, 0.2, 0.2)
        assembly.add(shape, name=name, color=color)
    assembly.add(physical, name="Bambu_reconstructed_reference")
    assembly.add(cq.Compound.makeCompound(hardware), name="User_M2_5_insert_and_screw_envelopes")
    assembly.export(str(STEP / "Bambu_Side2510_Service_CONCEPT.step"))
    (ROOT / "verification_bambu_side2510.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-reference", type=Path, required=True)
    build(parser.parse_args().core_reference)
