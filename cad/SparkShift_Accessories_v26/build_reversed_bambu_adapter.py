"""Reversed Bambu heating assembly with front-entry user-supplied heatsets."""

import argparse
import json
from pathlib import Path

import cadquery as cq
import trimesh
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from build_modular_toolhead import ROOT, STEP, STL, HOTEND_AXES, box, cylinder_y, load, volume


def reverse(shape):
    return shape.rotate((0, 22.7, 0), (0, 22.7, 1), 180)


def build(core_path):
    reference = load("Hotend_Voron_Bambu_P2S").Solids()
    physical = reverse(cq.Compound.makeCompound(reference[:6]))
    core = cq.importers.importStep(str(core_path)).val()
    blue = load("P17M_Reusable_Carrier_3010_REVIEW").intersect(box(-16, 16, 10, 36, -19.2794, 50))
    baseline = load("P17M_Bambu_Adapter_3010_REVIEW")
    adapter = baseline.intersect(box(-16, 16, 11.5, 32.05, -26, -17.2794))
    for x in (-5.657, 5.657):
        for y in (17.043, 28.357):
            adapter = adapter.fuse(cq.Solid.makeCylinder(2.41, 8.7206, cq.Vector(x, y, -26), cq.Vector(0, 0, 1)))
    adapter = adapter.fuse(box(-9.25, 9.25, 31.1, 37.9, -65.93, -24))
    hardware, seats = [], []
    for x, z in HOTEND_AXES:
        adapter = adapter.cut(cylinder_y(x, z, 33.9, 38, 1.55))
        adapter = adapter.cut(cylinder_y(x, z, 31, 33.9, 1.4))
        hardware.extend([
            cylinder_y(x, z, 33.9, 37.9, 1.75).cut(cylinder_y(x, z, 33.8, 38, 1.05)),
            cylinder_y(x, z, 28.9, 38.9, 1.25).fuse(cylinder_y(x, z, 27.2, 28.9, 2.25)),
        ])
        if x:
            hardware.append(cylinder_y(x, z, 28.9, 29.4, 2.25).cut(cylinder_y(x, z, 28.8, 29.5, 1.35)))
    # Front-access structural clamp ears, independent of cooling hardware.
    for x in (-6, 6):
        z = -22.75
        blue = blue.fuse(cylinder_y(x, z, 29, 35.93, 3))
        blue = blue.fuse(box(x-3, x+3, 32.05, 35.93, -22.75, -18.5))
        adapter = adapter.cut(cylinder_y(x, z, 29, 32.15, 3.1))
        adapter = adapter.fuse(cylinder_y(x, z, 11.5, 29, 1.46))
        adapter = adapter.cut(cylinder_y(x, z, 11.4, 14.5, 1.55))
        adapter = adapter.cut(cylinder_y(x, z, 14.5, 29.1, 1.4))
        blue = blue.cut(cylinder_y(x, z, 28.9, 32, 1.4))
        blue = blue.cut(cylinder_y(x, z, 32, 36, 2.4))
        adapter = adapter.cut(cylinder_y(x, z, 32, 38, 2.5))
        hardware.extend([
            cylinder_y(x, z, 11.5, 14.5, 1.75).cut(cylinder_y(x, z, 11.4, 14.6, 1.05)),
            cylinder_y(x, z, 12, 32, 1.25).fuse(cylinder_y(x, z, 32, 34.5, 2.25)),
        ])
    adapter, blue = adapter.cut(blue).clean(), blue.clean()
    hardware = cq.Compound.makeCompound(hardware)
    obstacles = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
        "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
    )}
    obstacles.update(core=core)
    report = {
        "status": "CAD_REVIEW_NOT_PHYSICALLY_QUALIFIED",
        "rotation": "180 degrees about vertical filament axis X0 Y22.7; no translation",
        "hotend_mount": {
            "thread": "M2.5 x 0.45",
            "inserts": "User-supplied M2.5 x length4 x OD3.5 mm",
            "entry": "Front +Y face Y37.9; insertion toward -Y",
            "insert_range_y_mm": [33.9, 37.9],
            "retaining_shoulder_mm": 2.8,
            "wall_thickness_mm": 6.8,
            "pilot_diameter_mm": 3.1,
            "hardware": "3 x M2.5x10 low-head screws, head maximum OD4.5 x H1.7; upper two 0.5 mm washers OD4.5 ID2.7",
            "thread_engagement_mm": 4,
            "front_screw_protrusion_mm": 1,
            "load_direction": "-Y, into the shoulder, away from the front insert mouth",
        },
        "shelf_clamp": "2 x M2.5x20; rear-entry user inserts; independent of carriage fan",
        "unused_top_holes_removed": 4,
        "checks": {},
        "limitations": [
            "Reconstructed Bambu geometry, not certified exact H2D vendor CAD.",
            "Select actual screw heads and coupon-calibrate the insert pilot.",
            "No physical torque, creep, thermal, cooling or repeatability qualification.",
            "Original synthetic nozzle tip ends at Z-78.1312, not the intended -78.88; reference unchanged.",
            "Rear-facing nozzle service is intended with tool removed from carriage.",
            "Sampled removal path is exploratory and excludes native fixed assembly latch kinematics.",
            "Heater wiring needs rear-facing strain relief and physical fit assessment.",
        ],
    }
    shapes = {"Blue_Upper_Carrier": blue, "Yellow_Reversed_Adapter": adapter,
              "Reversed_Hotend_Reference": physical, "M2_5_Hardware": hardware}
    for name, shape in shapes.items():
        if not shape.isValid():
            raise ValueError(f"Invalid {name}")
        checks = {n: volume(shape.intersect(o)) for n, o in obstacles.items()}
        if name == "Blue_Upper_Carrier":
            report["inherited_blue_P18_mm3"] = checks.pop("P18_Tool_docking_backplate_3010")
        if max(checks.values()) > 0.01:
            raise ValueError(f"{name} clash: {checks}")
        report["checks"][name] = checks
    for name, a, b in [("blue_adapter", blue, adapter), ("adapter_hotend", adapter, physical),
                       ("hardware_hotend", hardware, physical)]:
        report["checks"][name] = volume(a.intersect(b))
        if report["checks"][name] > 0.01:
            raise ValueError(f"Interference: {name}")
    for x, z in HOTEND_AXES:
        shoulder = cylinder_y(x, z, 31.1, 33.9, 2.5).cut(cylinder_y(x, z, 31.1, 33.9, 1.4))
        surround = cylinder_y(x, z, 33.9, 37.9, 2.5).cut(cylinder_y(x, z, 33.9, 37.9, 1.75))
        check = {"axis_xz_mm": [x, z], "missing_shoulder_mm3": volume(shoulder.cut(adapter)),
                 "missing_surround_mm3": volume(surround.cut(adapter)),
                 "pilot_obstruction_mm3": volume(adapter.intersect(cylinder_y(x, z, 33.9, 37.9, 1.55)))}
        if max(v for k, v in check.items() if k != "axis_xz_mm") > 0.001:
            raise ValueError(f"Insert seat failure: {check}")
        seats.append(check)
    report["insert_seats"] = seats
    report["shelf_insert_seats"] = []
    for x in (-6, 6):
        z = -22.75
        shoulder = cylinder_y(x, z, 14.5, 17, 2.5).cut(cylinder_y(x, z, 14.5, 17, 1.4))
        surround = cylinder_y(x, z, 11.5, 14.5, 2.5).cut(cylinder_y(x, z, 11.5, 14.5, 1.75))
        check = {"x_mm": x, "missing_shoulder_mm3": volume(shoulder.cut(adapter)),
                 "missing_surround_mm3": volume(surround.cut(adapter))}
        if max(check["missing_shoulder_mm3"], check["missing_surround_mm3"]) > 0.001:
            raise ValueError(f"Shelf insert seat failure: {check}")
        report["shelf_insert_seats"].append(check)
    # Inserts intentionally displace the undersized pilot; screws must not hit plastic.
    report["screw_printed_parts_clearance_mm3"] = [
        volume(hardware.Solids()[i].intersect(cq.Compound.makeCompound([blue, adapter])))
        for i in (1, 4, 7, 9, 11)
    ]
    if max(report["screw_printed_parts_clearance_mm3"]) > 0.001:
        raise ValueError("A mounting screw intersects the printed parts")
    removable = reverse(cq.Compound.makeCompound(reference[3:5]))
    fixed_prints = cq.Compound.makeCompound([adapter, blue, hardware])
    report["service_path"] = []
    for down, rear in [(d, 0) for d in range(5)] + [(4, d) for d in range(2, 42, 2)]:
        moved = removable.translate((0, -rear, -down))
        report["service_path"].append({
            "down_mm": down, "rearward_mm": rear,
            "printed_mount_overlap_mm3": volume(moved.intersect(fixed_prints)),
            "carriage_overlap_mm3": volume(moved.intersect(core)),
        })
    if max(s["printed_mount_overlap_mm3"] for s in report["service_path"]) > 0.01:
        raise ValueError("New adapter obstructs sampled removed-tool service path")
    report["in_carriage_sampled_path_clear"] = max(s["carriage_overlap_mm3"] for s in report["service_path"]) < 0.01
    report["removed_top_hole_missing_material_mm3"] = [
        volume(cq.Solid.makeCylinder(2.4, 8.7206, cq.Vector(x, y, -26), cq.Vector(0, 0, 1)).cut(adapter))
        for x in (-5.657, 5.657) for y in (17.043, 28.357)
    ]
    # The structural clamp ear replaces part of the shelf at the front hole axes.
    report["removed_top_hole_missing_combined_material_mm3"] = [
        volume(cq.Solid.makeCylinder(2.4, 8.7206, cq.Vector(x, y, -26), cq.Vector(0, 0, 1)).cut(adapter.fuse(blue)))
        for x in (-5.657, 5.657) for y in (17.043, 28.357)
    ]
    for name, shape in shapes.items():
        cq.exporters.export(shape, str(STEP / f"Bambu_Reversed_{name}_REVIEW.step"))
        if name not in ("Blue_Upper_Carrier", "Yellow_Reversed_Adapter"):
            continue
        if len(shape.Solids()) != 1:
            raise ValueError(f"Disconnected {name}")
        path = STL / f"Bambu_Reversed_{name}_REVIEW.stl"
        cq.exporters.export(shape, str(path), tolerance=0.03, angularTolerance=0.1)
        mesh = trimesh.load_mesh(path)
        if not mesh.is_watertight or len(mesh.split(only_watertight=False)) != 1:
            raise ValueError(f"Invalid mesh: {name}")
        oriented = shape.rotate((0, 0, 0), (1, 0, 0), -90 if name.startswith("Yellow") else 90)
        oriented = oriented.translate((0, 0, -oriented.BoundingBox().zmin))
        print_path = STL / f"Bambu_Reversed_{name}_REVIEW_PRINT.stl"
        cq.exporters.export(oriented, str(print_path), tolerance=0.03, angularTolerance=0.1)
        print_mesh = trimesh.load_mesh(print_path)
        if not print_mesh.is_watertight or abs(print_mesh.bounds[0, 2]) > 0.01:
            raise ValueError(f"Invalid print orientation export: {name}")
    assembly = cq.Assembly(name="Reversed Bambu - front heatsets - removed-tool rear service")
    for name, shape in shapes.items():
        color = cq.Color(0.9, 0.65, 0.1) if "Yellow" in name else cq.Color(0.2, 0.5, 0.75)
        if "Reference" in name or "Hardware" in name:
            color = cq.Color(0.65, 0.65, 0.65)
        assembly.add(shape, name=name, color=color)
    assembly.export(str(STEP / "Bambu_Reversed_M2_5_Adapter_REVIEW.step"))
    reimported = load("Bambu_Reversed_M2_5_Adapter_REVIEW")
    report["persisted_assembly_valid"] = reimported.isValid()
    report["persisted_assembly_solids"] = len(reimported.Solids())
    if not reimported.isValid() or len(reimported.Solids()) != 20:
        raise ValueError("Reversed assembly export is incomplete")
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(projection="3d")
    for name, shape in shapes.items():
        vertices, triangles = shape.tessellate(0.12)
        points = np.array([v.toTuple() for v in vertices])
        color = "#e3ac34" if "Yellow" in name else "#3c8db9"
        if "Reference" in name or "Hardware" in name:
            color = "#aaaaaa"
        ax.add_collection3d(Poly3DCollection(points[np.array(triangles)], facecolor=color,
                                            edgecolor="none"))
    ax.set(xlim=(-20, 20), ylim=(8, 45), zlim=(-85, 50),
           xlabel="X (mm)", ylabel="Y (mm)", zlabel="Z (mm)")
    ax.set_box_aspect((40, 37, 135))
    ax.view_init(elev=12, azim=60)
    fig.suptitle("REVERSED BAMBU ADAPTER - CAD REVIEW\nFront-entry M2.5 x L4 x OD3.5 inserts\nRear nozzle service: remove tool from carriage first")
    fig.savefig(ROOT / "images" / "34_reversed_bambu_m2_5_review.png", dpi=140)
    plt.close(fig)
    (ROOT / "verification_bambu_reversed.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-reference", type=Path, required=True)
    build(parser.parse_args().core_reference)
