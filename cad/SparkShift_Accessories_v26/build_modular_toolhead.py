"""Build a review prototype from the user's exact Fusion Body1/Body2 split.

Requires CadQuery 2.8 and trimesh. This is not a print-qualified release.
"""

import argparse
import json
from pathlib import Path

import cadquery as cq
import trimesh

import build_and_verify_accessories_v26 as primitives

ROOT = Path(__file__).resolve().parent
STEP = ROOT / "step"
STL = ROOT / "stl"
FAN_AXES = [(x, z) for x in (-12.0, 12.0) for z in (-49.5, -25.5)]
HOTEND_AXES = [(-6.0, -40.13), (6.0, -40.13), (0.0, -50.63)]


def insert_entry(z):
    return 20.3 if z < -40 else 11.5


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def cylinder_y(x, z, y0, y1, radius):
    return cq.Solid.makeCylinder(radius, y1 - y0, cq.Vector(x, y0, z), cq.Vector(0, 1, 0))


def load(name):
    return cq.importers.importStep(str(STEP / f"{name}.step")).val()


def volume(shape):
    return sum(s.Volume() for s in shape.Solids())


def clean_fan_frame():
    """Retain the original outer envelope, not its intersecting legacy cavities."""
    outer = cq.Shape.cast(primitives.intersect_all(
        primitives.prism_xy_r([
            (-12.4, 11.5), (12.4, 11.5), (12.4, 26.8), (15, 29.4),
            (15, 35.93), (-15, 35.93), (-15, 29.4), (-12.4, 26.8),
        ], [1.8, 1.8, 1.2, 1.2, 0, 0, 1.2, 1.2], -52.5, -19.2794),
        [
            primitives.prism_xz_r([
                (-15, -52.5), (15, -52.5), (15, -22.5),
                (11.78, -19.2794), (-11.78, -19.2794), (-15, -22.5),
            ], [2.2, 2.2, 1, 0, 0, 1], 11, 36.5),
            primitives.prism_yz_r([
                (11.5, -52.5), (35.93, -52.5), (35.93, -22.5),
                (32.05, -22.5), (32.05, -19.2794), (11.5, -19.2794),
            ], [0] * 6, -16, 16),
        ],
    ))
    frame = outer.fuse(box(-9, 9, 32.05, 35.93, -22.5, -19.2794))
    frame = frame.intersect(box(-16, 16, 26.8, 35.93, -52.5, -19.2794))
    rear_air = cq.Shape.cast(primitives.prism_xz_r([
        (-9.6, -50.3), (9.6, -50.3), (9.6, -25.5), (-9.6, -25.5),
    ], 1.5, 26.7, 31.5))
    transition_face = next(
        f for f in rear_air.Faces()
        if f.geomType() == "PLANE" and abs(f.Center().y - 31.5) < 1e-5
    )
    inlet_wire = cq.Wire.makeCircle(13.6, cq.Vector(0, 35.5, -37.5), cq.Vector(0, 1, 0))
    transition = cq.Solid.makeLoft([transition_face.outerWire(), inlet_wire])
    air = rear_air.fuse(transition).fuse(cylinder_y(0, -37.5, 35.5, 36.1, 13.6)).clean()
    frame = frame.cut(air)
    # P18's two lower attachment holes straddle the upper/lower frame boundary.
    for x in (-6, 6):
        frame = frame.cut(cylinder_y(x, -19.26, 31, 36.1, 2.28))
    return frame.clean(), air


def build(core_reference=None):
    split = load("P17_Modular_User_Revision_v4_Reference")
    bodies = sorted(split.Solids(), key=lambda b: b.BoundingBox().zmax, reverse=True)
    if len(bodies) != 2:
        raise ValueError("The reference must contain exactly the user's two solids")
    carrier, adapter = bodies
    original_carrier, original_adapter = carrier, adapter

    frame, fan_air = clean_fan_frame()
    frame = frame.intersect(box(-16, 16, 32.05, 36, -53, 50))
    upper = carrier.intersect(box(-16, 16, 10, 36, -19.2794, 50))
    carrier = upper.fuse(frame).clean()
    # Restore the upstream curved hob opening and close filament-guide lips.
    guide_region = box(-3.1, 3.1, 19, 26.1, -8.3, 8.5)
    guide = load("P17_YUDX_Hob_Guide_Reference")
    guide = guide.cut(cq.Solid.makeCone(1.8, 1.15, 0.65, cq.Vector(0, 22.68, -8.3), cq.Vector(0, 0, 1)))
    guide = guide.cut(cq.Solid.makeCone(1.15, 1.8, 0.65, cq.Vector(0, 22.68, 7.85), cq.Vector(0, 0, 1)))
    carrier = carrier.cut(guide_region).fuse(guide).clean()

    # Heal the two 0.05 mm remnants of the obsolete cylindrical K1 pocket.
    for sign in (-1, 1):
        x0, x1 = (9.2, 9.4) if sign > 0 else (-9.4, -9.2)
        adapter = adapter.fuse(box(x0, x1, 16, 17.5, -27.5, -24.0)).clean()
    # Unify the lower wall and sidebar width instead of preserving a 0.05 mm step.
    adapter = adapter.fuse(box(-9.25, 9.25, 11.5, 14.3, -65.93, -32.38))
    for x, z in HOTEND_AXES:
        adapter = adapter.cut(cylinder_y(x, z, 11.4, 14.4, 1.45))
    for x in (-6, 6):
        for z in (-55.93, -63.93):
            adapter = adapter.cut(cylinder_y(x, z, 13.4, 14.4, 1.6))
    adapter = adapter.clean()

    # Lower rear recesses clear P22; the user's full-depth rails remain above.
    for x, z in FAN_AXES:
        x0, x1 = (9.25, 15.0) if x > 0 else (-15.0, -9.25)
        if z < -40:
            adapter = adapter.cut(box(x0, x1, 11.4, 20.3, z - 3, z + 3))
            rib_x0, rib_x1 = (9.25, 13.5) if x > 0 else (-13.5, -9.25)
            adapter = adapter.fuse(box(rib_x0, rib_x1, 13.3, 32.05, -46.5, -43.5))
        entry = insert_entry(z)
        # Fill the rough straight bore before recutting its stepped seat.
        adapter = adapter.fuse(cylinder_y(x, z, entry, 32.05, 1.61))
        carrier = carrier.cut(cylinder_y(x, z, 32, 36.1, 1.4)).clean()
        adapter = adapter.cut(cylinder_y(x, z, entry - 0.1, entry + 4, 1.6))
        adapter = adapter.cut(cylinder_y(x, z, entry + 4, 32.15, 1.4)).clean()

    shapes = {
        "P17M_Reusable_Carrier_3010_REVIEW": carrier,
        "P17M_Bambu_Adapter_3010_REVIEW": adapter,
    }
    report = {
        "status": "REVIEW_ONLY_NOT_PRINT_QUALIFIED",
        "reference": "User revised 09_Modular_Toolhead_3010_Review version 4",
        "interface": {
            "fan_axes_xz_mm": FAN_AXES,
            "seam_y_mm": 32.05,
            "upper_shoulder_z_mm": -17.2794,
            "carrier_clearance_diameter_mm": 2.8,
            "adapter_insert_pilot_diameter_mm": 3.2,
            "adapter_insert_pilot_depth_mm": 4.0,
            "adapter_insert_entry_y_mm": {"upper": 11.5, "lower": 20.3},
            "adapter_insert_shoulder_y_mm": {"upper": 15.5, "lower": 24.3},
            "adapter_shoulder_thickness_mm": {"upper": 16.55, "lower": 7.75},
            "adapter_shoulder_hole_diameter_mm": 2.8,
            "insertion_direction": "+Y from rear rail face (upper) or rear recess (lower); bolt head on +Y front",
            "pull_direction": "+Y, into the smaller-diameter printed shoulder, not toward the pocket mouth",
            "provisional_insert": "M2.5, maximum OD 4.0 mm, length 4.0 mm; select and coupon-test before printing",
            "provisional_screw": "Upper: 2 x M2.5 x 35 with 1 mm washer; lower: 2 x M2.5 x 25 without washer; assumes 10 mm fan",
            "insert_outer_edge_wall_min_mm": 1.0,
            "insert_all_sides_wall_min_mm": 0.75,
            "screw_thread_engagement_mm": {"upper": 3.57, "lower": 3.37},
            "screw_tip_to_rear_entry_mm": {"upper": 0.43, "lower": 0.63},
            "intended_nozzle_datum_mm": [0, 22.7, -78.88],
        },
        "parts": {},
        "clashes_mm3": {},
        "limitations": [
            "No slicer/support qualification, FEA, thermal-creep or physical repeatability testing.",
            "Insert dimensions are a provisional envelope, not a selected manufacturer's specification.",
            "3010 interface only; other hotends need adapter-specific cooling, wiring and clearance checks.",
            "No new nozzle metal, sensor mount, gantry, docking geometry or CPAP geometry is generated.",
            "Existing synthetic Bambu nozzle ends above the intended Z datum; unchanged here.",
            "BLOCKER: three existing Bambu M3 holes are in a 2.8 mm wall with only 0.1 mm rear clearance to the core. A 4 mm rear insert plus shoulder cannot fit; mounting retention is not approved.",
            "Rear-face inserts resist withdrawal toward the seam; plastic shoulder failure and thermal creep remain possible.",
            "Thin front frame no longer contains breached wire tunnels. Yellow cradle retains internal reliefs; complete cable routing still needs a fit check.",
        ],
    }
    for name, shape in shapes.items():
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f"{name}: invalid or disconnected solid")
        bb = shape.BoundingBox()
        report["parts"][name] = {
            "valid": shape.isValid(),
            "solid_count": len(shape.Solids()),
            "volume_mm3": volume(shape),
            "bounds_mm": [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax],
        }
    report["interpart_overlap_mm3"] = volume(carrier.intersect(adapter))
    if report["interpart_overlap_mm3"] > 1e-4:
        raise ValueError("Carrier and adapter overlap")
    report["fan_paths"] = [
        {
            "axis_xz_mm": [x, z],
            "carrier_obstruction_mm3": volume(carrier.intersect(cylinder_y(x, z, 32.05, 35.93, 1.4))),
            "adapter_pilot_obstruction_mm3": volume(adapter.intersect(cylinder_y(x, z, insert_entry(z), insert_entry(z) + 4, 1.6))),
            "adapter_shank_obstruction_mm3": volume(adapter.intersect(cylinder_y(x, z, insert_entry(z) + 4, 32.05, 1.4))),
            "shoulder_material_mm3": volume(adapter.intersect(
                cylinder_y(x, z, insert_entry(z) + 4, insert_entry(z) + 6.5, 2.0).cut(
                    cylinder_y(x, z, insert_entry(z) + 4, insert_entry(z) + 6.5, 1.4))
            )),
            "missing_insert_surround_mm3": volume(
                cylinder_y(x, z, insert_entry(z), insert_entry(z) + 4, 2.75).cut(
                    cylinder_y(x, z, insert_entry(z), insert_entry(z) + 4, 2.0)).cut(adapter)
            ),
        }
        for x, z in FAN_AXES
    ]
    if any(max(p["carrier_obstruction_mm3"], p["adapter_pilot_obstruction_mm3"], p["adapter_shank_obstruction_mm3"]) > 1e-4 for p in report["fan_paths"]):
        raise ValueError("A shared fastener path is obstructed")
    expected_shoulder = volume(cylinder_y(12, -25.5, 24.3, 26.8, 2.0).cut(
        cylinder_y(12, -25.5, 24.3, 26.8, 1.4)
    ))
    if any(abs(p["shoulder_material_mm3"] - expected_shoulder) > 1e-4 for p in report["fan_paths"]):
        raise ValueError("An insert shoulder is incomplete")
    if any(p["missing_insert_surround_mm3"] > 1e-4 for p in report["fan_paths"]):
        raise ValueError("An insert has less than 0.75 mm surrounding plastic")

    report["hotend_mount_audit"] = {
        "axes_xz_mm": HOTEND_AXES,
        "status": "BLOCKED_NOT_APPROVED_FOR_PRINT",
        "wall_thickness_mm": 2.8,
        "rear_clearance_to_live_core_mm": 0.1,
        "reason": "A 4 mm rear heatset plus load-bearing shoulder cannot fit without changing this mounting architecture. Original holes retained, not represented as an approved joint.",
    }

    upper_changed = volume(carrier.intersect(box(-16, 16, 10, 36, -19.2794, 50)).cut(upper).cut(guide_region))
    upper_changed += volume(upper.cut(carrier).cut(guide_region))
    report["cutout_audit"] = {
        "HGX_hob_access_window_and_filament_guides": "Restored from official YUDX Tool.step commit 52e8ef6e04b93c1fa63bea4beb5c3a67a4b704aa. Local 2.3 mm bore, tapered to existing 3.6 mm bore at replacement boundaries.",
        "cam_hook_and_magnet_pockets": "Retained; locking and coupling interfaces.",
        "upper_geometry_change_outside_guide_region_mm3": upper_changed,
        "P18_lower_attachment_holes": "Retained and recut through clean material; old intersecting wire cuts removed below seam.",
        "fan_opening_notches": "Replaced overlapping K1 bore and enclosed tunnels with a single lofted air passage.",
        "fan_air_obstruction_mm3": volume(carrier.intersect(fan_air)),
        "wiring": "Upper stem trough retained; lower yellow cradle reliefs require cable routing and strain-relief review.",
        "adapter_pinhole_remnants": "Two 0.05 mm K1-pocket remnants filled; tiny cylindrical faces removed.",
        "lower_apron_sidebar_step": "Rear wall normalized to X=+/-9.25 mm; obsolete rounded transition and 0.05 mm ledges removed, original holes and tip dimples recut.",
        "lower_adapter_pad_connection": "Two 3 mm high side bridges join the rear-access pads to the adapter; reduced exhaust opening remains unqualified.",
        "insert_access": "Upper inserts at the outer rear rail face; lower rear recesses clear P22. User seam remains Y=32.05.",
        "guide_reference_missing_mm3": volume(guide.cut(carrier)),
        "guide_reference_extra_mm3": volume(carrier.intersect(guide_region).cut(guide)),
        "guide_filament_path_obstruction_mm3": volume(carrier.intersect(cq.Solid.makeCylinder(
            1.15, 16.8, cq.Vector(0, 22.68, -8.3), cq.Vector(0, 0, 1)
        ))),
    }
    if upper_changed > 1e-4 or report["cutout_audit"]["fan_air_obstruction_mm3"] > 1e-4:
        raise ValueError("Upper functional geometry changed or fan passage obstructed")
    if any(report["cutout_audit"][k] > 1e-4 for k in (
        "guide_reference_missing_mm3", "guide_reference_extra_mm3", "guide_filament_path_obstruction_mm3"
    )):
        raise ValueError("Restored YUDX guide does not match its local reference or blocks filament")
    tiny_pocket_faces = [
        f for f in adapter.Faces() if f.geomType() == "CYLINDER" and f.Area() < 0.3
        and 9.19 < abs(f.Center().x) < 9.26 and -27.5 < f.Center().z < -24
    ]
    report["cutout_audit"]["remaining_tiny_K1_pocket_faces"] = len(tiny_pocket_faces)
    if tiny_pocket_faces:
        raise ValueError("An obsolete adapter pocket remnant remains")

    hardware = cq.Compound.makeCompound([
        cylinder_y(x, z, 20.93 if z < -40 else 11.93, 45.93 if z < -40 else 46.93, 1.25).fuse(
            cylinder_y(x, z, 45.93 if z < -40 else 46.93, 48.43 if z < -40 else 49.43, 2.25))
        for x, z in FAN_AXES
    ] + [
        cylinder_y(x, z, insert_entry(z), insert_entry(z) + 4, 2.0)
        for x, z in FAN_AXES
    ] + [
        cylinder_y(x, -25.5, 45.93, 46.93, 2.5).cut(cylinder_y(x, -25.5, 45.93, 46.93, 1.4))
        for x in (-12, 12)
    ])
    report["new_metal_min_z_mm"] = hardware.BoundingBox().zmin
    report["sensor_keepout_top_z_mm"] = -56.6
    report["new_metal_above_sensor_keepout_mm"] = hardware.BoundingBox().zmin + 56.6
    if report["new_metal_above_sensor_keepout_mm"] < 0:
        raise ValueError("New hardware enters the sensor keepout's Z range")

    reference_exports = {}
    for name in (
        "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
        "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
        "Hotend_Voron_Bambu_P2S", "P18_Tool_docking_backplate_3010", "Fan_3010_Axial",
    ):
        other = load(name)
        inherited_hardware_clash = 0.0
        if name == "Fan_3010_Axial":
            fan_solids = other.Solids()
            if len(fan_solids) != 5:
                raise ValueError("Unexpected fan reference structure")
            other = max(fan_solids, key=lambda s: s.Volume())
        if name == "Hotend_Voron_Bambu_P2S":
            # Replace the three synthetic screw references, not the ceramic/cradle.
            hotend_solids = other.Solids()
            if len(hotend_solids) != 9:
                raise ValueError("Unexpected Bambu reference structure")
            other = cq.Compound.makeCompound(hotend_solids[:6])
            inherited_hardware_clash = volume(cq.Compound.makeCompound(hotend_solids[6:]).intersect(other))
        before = volume(original_carrier.intersect(other)) + volume(original_adapter.intersect(other))
        after = volume(carrier.intersect(other)) + volume(adapter.intersect(other))
        report["clashes_mm3"][name] = {"before": before, "after": after, "increase": after - before}
        if after - before > 0.01:
            raise ValueError(f"New interference with {name}: {after - before:.4f} mm3")
        hw_clash = volume(hardware.intersect(other))
        report["clashes_mm3"][name]["new_hardware"] = hw_clash
        report["clashes_mm3"][name]["inherited_hardware"] = inherited_hardware_clash
        if hw_clash - inherited_hardware_clash > 0.01:
            raise ValueError(f"New hardware interference with {name}: {hw_clash:.4f} mm3")
        if hw_clash > 0.01:
            report["limitations"].append(
                f"{name}: inherited lower screw-head/sock overlap ({hw_clash:.4f} mm3); "
                "physical sock relief and actual screw head must be verified before release."
            )
        if name == "Hotend_Voron_Bambu_P2S":
            reference_exports["P17M_Bambu_Hotend_Reference"] = load(name)
            if inherited_hardware_clash > 0.01:
                report["limitations"].append(
                    f"Existing lower Bambu screw-head/sock model overlap: {inherited_hardware_clash:.4f} mm3; "
                    "actual screw head and physical sock relief need verification."
                )
        elif name == "Fan_3010_Axial":
            reference_exports["P17M_Fan_Reference"] = other

    if core_reference is not None:
        core = cq.importers.importStep(str(core_reference)).val()
        before = volume(original_carrier.intersect(core)) + volume(original_adapter.intersect(core))
        after = volume(carrier.intersect(core)) + volume(adapter.intersect(core))
        hw_clash = volume(hardware.intersect(core))
        report["core_interface_audit_mm3"] = {"before": before, "after": after, "new_hardware": hw_clash}
        if after - before > 0.01 or hw_clash > 0.01:
            raise ValueError("New interference with the live core carriage reference")
    else:
        report["core_interface_audit_mm3"] = None

    STL.mkdir(exist_ok=True)
    for name, shape in reference_exports.items():
        cq.exporters.export(shape, str(STEP / f"{name}.step"))
    cq.exporters.export(hardware, str(STEP / "P17M_Fastener_Envelopes_REVIEW.step"))
    for name, shape in shapes.items():
        cq.exporters.export(shape, str(STEP / f"{name}.step"))
        cq.exporters.export(shape, str(STL / f"{name}.stl"), tolerance=0.03, angularTolerance=0.1)
        mesh = trimesh.load_mesh(STL / f"{name}.stl")
        components = len(mesh.split(only_watertight=False))
        report["parts"][name].update(mesh_watertight=bool(mesh.is_watertight), mesh_components=components)
        if not mesh.is_watertight or components != 1:
            raise ValueError(f"{name}: non-watertight or disconnected mesh")
        sign, bed = (1, 35.93) if "Reusable" in name else (-1, 11.5)
        report["parts"][name]["bed_contact_mm2"] = sum(
            f.Area() for f in shape.Faces()
            if f.geomType() == "PLANE" and abs(f.Center().y - bed) < 1e-4
            and abs(f.normalAt().y) > 0.999
        )
        if report["parts"][name]["bed_contact_mm2"] < 500:
            raise ValueError(f"{name}: expected broad print face is missing")
        angle = -90 if sign == 1 else 90
        oriented = shape.rotate((0, 0, 0), (1, 0, 0), angle)
        oriented = oriented.translate((0, 0, -oriented.BoundingBox().zmin))
        cq.exporters.export(oriented, str(STL / f"{name}_PRINT.stl"), tolerance=0.03, angularTolerance=0.1)
        print_mesh = trimesh.load_mesh(STL / f"{name}_PRINT.stl")
        report["parts"][name]["print_mesh_min_z_mm"] = float(print_mesh.bounds[0, 2])
        if abs(print_mesh.bounds[0, 2]) > 0.05 or not print_mesh.is_watertight:
            raise ValueError(f"{name}: invalid print orientation export")
    (ROOT / "verification_modular_toolhead.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-reference", type=Path, help="Identity-transformed core carriage STEP for an optional live interface audit")
    args = parser.parse_args()
    build(args.core_reference)
