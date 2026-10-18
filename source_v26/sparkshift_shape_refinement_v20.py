"""Native structural-shape refinement of the preserved, user-edited assembly."""

import hashlib
import math
import sys
import time
from pathlib import Path

import adsk.core
import adsk.fusion


OUT = Path(__file__).resolve().parent / "sparkshift_shape_refinement_v20"
STATE = {}
LEFT_SCREW = "FRAME_M3x35_into_P01_insert"
LEFT_INSERT = "FRAME_M3_HEATSET_in_P01"
RIGHT_SCREW = "UPPER_RIGHT_SHARED_M3x40_FRAME"
RIGHT_INSERT = "UPPER_RIGHT_REAR_M3_HEATSET_4p6x4"
ARM_REAR = "PRINT_carrier_box_left"
ARM_FRONT = "PRINT_arm_front_half"
REAR_SCREW = "V20_REAR_PLATE_UPPER_M3x10_BUTTON"
REAR_INSERT = "V20_REAR_PLATE_UPPER_M3_HEATSET_4p6x4"


def shared():
    return sys.modules["sparkshift_open_frame_v19"]


def initialize(app, ui):
    if STATE:
        raise RuntimeError("The shape-refinement input was already preserved")
    b = shared()
    b.require(app)
    if ui.activeCommand == "FreeOrbitCommand":
        ui.terminateActiveCommand()
    if ui.activeCommand != "SelectCommand":
        raise RuntimeError("Finish the current native edit before preserving the new revision")
    b.STATE["tools"].normalize_edit_pose(app)
    for folder in (OUT, OUT / "cad", OUT / "images"):
        folder.mkdir(exist_ok=True)
    source = app.activeDocument
    design = adsk.fusion.Design.cast(app.activeProduct)
    path = OUT / "cad" / ("Input_before_intentional_shapes_" + time.strftime("%Y%m%d_%H%M%S") + ".f3d")
    if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("Could not preserve the complete user-edited input")
    document = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(str(path)))
    if document is None:
        raise RuntimeError("Could not isolate the shape-refinement revision")
    document.activate()
    document.name = "SparkShift v20 - intentional shapes and supported case clamps - WIP"
    s, _ = b.geometry()
    b.STATE["superseded_frozen_review"] = b.STATE.pop("frozen_review", None)
    b.STATE["document"] = document.creationId
    b.OUT = OUT
    b.PAYLOAD = OUT / "release"
    b.STATE["tools"].OUT = OUT
    b.STATE["tools"].PAYLOAD = b.PAYLOAD
    b.STATE["native"].OUT = OUT
    by, empty = b.physical_inventory(b.logical_bodies(app))
    if len(by) != 139:
        raise RuntimeError("The preserved input is not the expected 139 physical bodies")
    STATE.update(
        document=document.creationId, source_document=source.creationId, source_path=str(path),
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        definitions={name: s.tbm().copy(body.nativeObject) for name, body in by.items()},
        world={name: s.tbm().copy(body) for name, body in by.items()},
        paths={name: body.assemblyContext.fullPathName for name, body in by.items()},
        matrices={name: list(body.assemblyContext.transform2.asArray()) for name, body in by.items()},
        empty_history=empty, plans={}, applied={},
    )
    b.STATE["accepted_user_shapes"] = dict(STATE["definitions"])
    b.STATE["hardware"] = {name: s.tbm().copy(STATE["definitions"][name])
                            for name in b.STATE["hardware"]}
    b.STATE["candidate"] = {name: s.tbm().copy(STATE["definitions"][name])
                            for name in (b.BACK, b.PLATE, b.FRONT)}
    b.STATE["candidate_motion"] = []
    b.STATE["native_motion"] = []
    b.STATE.pop("candidate_motion_static", None)
    b.STATE.pop("native_motion_static", None)
    for key in ("native_model_verified", "readback_verified", "protected_verified",
                "assembly_verified", "motor_path_verified"):
        b.STATE[key] = False
    b.STATE["model_checks"] = []
    b.STATE["readback_checks"] = []
    b.CHANGED_PRINTS = {
        "P01": (b.BACK, "P01_Coherent_rear_bearing_frame_v20", (0, 1, 0)),
        "P02": (b.PLATE, "P02_7mm_small_keyway_lowered_heatset_v20", (0, -1, 0)),
        "P03": (b.FRONT, "P03_Tangent_receiver_supported_clamps_v20", (0, -1, 0)),
        "P05": (b.CAM, "P05_User_input_cam_v20", (0, 1, 0)),
    }
    report = {
        "source_document_preserved": source.creationId, "owned_document": document.creationId,
        "source_native": str(path), "source_sha256": STATE["source_sha256"],
        "physical_bodies": len(by), "empty_nonphysical_history_preserved": empty,
        "user_edited_cam_preserved_not_silently_replaced_with_v18": True,
        "native_seats_and_gearing_remain_guarded_against_original_geometry": True,
    }
    b.write("source_capture.json", report)
    return report


def step(plans, parts, name, tool, operation, label):
    b = shared()
    s, _ = b.geometry()
    shape = parts[name]
    s.op(shape, tool, operation)
    b.one_solid(shape, label)
    plans.setdefault(name, []).append({
        "tool": s.tbm().copy(tool), "operation": operation, "label": label,
        "expected": s.tbm().copy(shape),
    })


def prepare_clamps(drop_mm=3.0):
    if not 1.0 <= drop_mm <= 5.0:
        raise RuntimeError("The case-clamp drop is outside the bounded requested small relocation")
    b = shared()
    s, m = b.geometry()
    old_z, new_z = 41.72, 41.72 - drop_mm
    parts = {name: s.tbm().copy(STATE["definitions"][name]) for name in (b.BACK, b.PLATE, b.FRONT)}
    plans = {}
    front_y = parts[b.FRONT].preciseBoundingBox.maxPoint.y * 10
    step(plans, parts, b.PLATE, s.cyl(-16, old_z, -6.7, .3, 2.35), "join",
         "V20 retire old right rear insert and shank passage")
    step(plans, parts, b.BACK, s.cyl(18.1, old_z, .3, 4.6, 2.8), "join",
         "V20 retire old left heatset seat without filling the working cam clearance")
    for x, label in ((18.1, "left"), (-16.0, "right")):
        y0 = 4.6 if x > 0 else .3
        step(plans, parts, b.BACK, s.cyl(x, old_z, y0, 11.4, 1.71), "join",
             "V20 close retired " + label + " rear screw bore")
        head_y = 30.5 if x > 0 else 29.5
        step(plans, parts, b.FRONT, s.cyl(x, old_z, 11.4, head_y, 1.71), "join",
             "V20 close retired " + label + " receiver screw bore")
        step(plans, parts, b.FRONT, s.cyl(x, old_z, head_y, front_y, 3.06), "join",
             "V20 remove obsolete " + label + " head recess")
    for x, label in ((18.1, "left"), (-16.0, "right")):
        rear = s.cyl(x, new_z, .3, 11.4, 3.7)
        s.op(rear, parts[b.FRONT], "cut")
        step(plans, parts, b.BACK, rear, "join",
             "V20 continuous " + label + " rear load path with 2mm shaft wall")
        fore = s.cyl(x, new_z, 11.4, front_y, 3.7)
        s.op(fore, parts[b.BACK], "cut")
        step(plans, parts, b.FRONT, fore, "join",
             "V20 continuous " + label + " front load path respecting the case joint")
        head_y = 30.5 if x > 0 else 29.5
        step(plans, parts, b.FRONT, s.cyl(x, new_z, head_y, front_y, 4.25), "join",
             "V20 backed " + label + " head seat with 1p2mm minimum collar")
    step(plans, parts, b.BACK, s.cyl(18.1, new_z, .3, 4.6, 2.0), "cut",
         "V20 relocated original-size left heatset pilot")
    step(plans, parts, b.BACK, s.cyl(18.1, new_z, 4.6, 11.45, 1.7), "cut",
         "V20 relocated left straight shank bore")
    step(plans, parts, b.BACK, s.cyl(-16, new_z, .25, 11.45, 1.7), "cut",
         "V20 relocated right straight shank bore")
    step(plans, parts, b.PLATE, s.cyl(-16, new_z, -6.7, .3, 3.7), "join",
         "V20 backed rear-loaded right insert load path")
    right_pilot = s.cyl(-16, new_z, -6.45, -2.5, 2.1)
    s.op(right_pilot, m.cone_y(-16, new_z, -6.7, 2.308333333333333, -6.45, 2.1), "join")
    s.op(right_pilot, s.cyl(-16, new_z, -2.51, .35, 1.7), "join")
    step(plans, parts, b.PLATE, right_pilot, "cut",
         "V20 rear-open right insert pilot lead shoulder and shank")
    for x, label in ((18.1, "left"), (-16.0, "right")):
        head_y = 30.5 if x > 0 else 29.5
        radius = 1.65 if x > 0 else 1.7
        step(plans, parts, b.FRONT, s.cyl(x, new_z, 11.35, head_y, radius), "cut",
             "V20 straight " + label + " receiver screw bore")
        step(plans, parts, b.FRONT, s.cyl(x, new_z, head_y, front_y + .1, 3.05), "cut",
             "V20 flush " + label + " button-head access")
    hardware = {name: m.translated(STATE["definitions"][name], dz=-drop_mm)
                for name in (LEFT_SCREW, LEFT_INSERT, RIGHT_SCREW, RIGHT_INSERT)}
    report = {"drop_mm": drop_mm, "old_z_mm": old_z, "new_z_mm": new_z,
              "both_axes_level": True, "x_centres_unchanged_mm": [18.1, -16.0],
              "same_M3x30_left_M3x35_right_and_heatsets": True,
              "shaft_wall_min_mm": 2.0, "nominal_insert_radial_wall_min_mm": 1.4,
              "head_collar_min_mm": 1.2,
              "part_steps": {name: len(plan) for name, plan in plans.items()}}
    STATE.update(clamp_parts=parts, clamp_plans=plans, clamp_hardware=hardware, clamps=report)
    b.write("lowered_clamp_candidate.json", report)
    return report


def supported_corridors():
    b = shared()
    s, m = b.geometry()
    z = STATE["clamps"]["new_z_mm"]
    rows = []
    for x, label in ((18.1, "left"), (-16.0, "right")):
        start, seat = (.3, 30.5) if x > 0 else (-6.7, 29.5)
        core = m.ring(x, z, start, seat, 3.7, 2.32)
        for body in STATE["clamp_parts"].values():
            s.op(core, body, "cut")
        missing = core.volume * 1000 if core.lumps.count else 0.0
        row = {"side": label, "continuous_supported_length_mm": seat - start,
               "missing_outer_support_mm3": missing}
        rows.append(row)
        if missing > 1e-6:
            raise RuntimeError("The relocated screw still crosses an unsupported gap: " + str(row))
    report = {"sides": rows, "both_entire_paths_supported": True,
              "checked_in_actual_three_part_material_not_only_bounding_boxes": True}
    b.write("supported_corridors.json", report)
    return report


def inspect_candidate_contacts():
    b = shared()
    s, _ = b.geometry()
    parts = STATE["clamp_parts"]
    hardware = STATE["clamp_hardware"]
    shapes = dict(STATE["world"])
    shapes.update(parts)
    shapes.update(hardware)
    changed = dict(parts)
    changed.update(hardware)
    allowed = {
        frozenset((b.BACK, LEFT_INSERT)),
        frozenset((b.BACK if STATE.get("top_down") else b.PLATE, RIGHT_INSERT)),
        frozenset((LEFT_SCREW, LEFT_INSERT)),
        frozenset((RIGHT_SCREW, RIGHT_INSERT)),
    }
    if STATE.get("top_down"):
        allowed.update((frozenset((b.BACK, REAR_INSERT)),
                        frozenset((REAR_SCREW, REAR_INSERT))))
    hits = []
    count = 0
    for name, shape in changed.items():
        for other, fixed in shapes.items():
            if other == name or (other in changed and other < name):
                continue
            count += 1
            overlap, _ = s.common_volume(shape, fixed)
            if overlap <= 1e-5 or frozenset((name, other)) in allowed:
                continue
            if name in STATE["world"] and other in STATE["world"]:
                previous, _ = s.common_volume(STATE["world"][name], STATE["world"][other])
            elif name in (REAR_SCREW, REAR_INSERT) or other in (REAR_SCREW, REAR_INSERT):
                previous = 0.0
            else:
                raise RuntimeError("A candidate reference is absent from the source inventory")
            if overlap > previous + 1e-5:
                hits.append({"changed": name, "against": other, "overlap_mm3": overlap,
                             "original_overlap_mm3": previous})
    report = {"pairs": count, "new_unexpected_contacts": hits,
              "nominal_thread_and_insert_pressfits_listed_separately": [sorted(p) for p in allowed]}
    b.write("clamp_candidate_contacts.json", report)
    return report


def cylinder_z(x, y, z0, z1, radius):
    s, _ = shared().geometry()
    return s.tbm().createCylinderOrCone(
        s.P(x, y, z0), radius / 10, s.P(x, y, z1), radius / 10)


def rotate_y_to_z(shape, x, y, z):
    s, m = shared().geometry()
    result = s.tbm().copy(shape)
    origin = result.preciseBoundingBox
    centre = adsk.core.Point3D.create(
        (origin.minPoint.x + origin.maxPoint.x) / 2,
        (origin.minPoint.y + origin.maxPoint.y) / 2,
        (origin.minPoint.z + origin.maxPoint.z) / 2)
    rotation = adsk.core.Matrix3D.create()
    rotation.setToRotation(math.pi / 2, adsk.core.Vector3D.create(1, 0, 0), centre)
    if not s.tbm().transform(result, rotation):
        raise RuntimeError("The vertical insert rotation failed")
    return m.translated(result, dx=x - centre.x * 10,
                        dy=y - centre.y * 10, dz=z - centre.z * 10)


def prepare_top_down_clamps():
    b = shared()
    s, m = b.geometry()
    parts = {name: s.tbm().copy(STATE["definitions"][name])
             for name in (b.BACK, b.PLATE, b.FRONT)}
    plans = {}
    front_y = parts[b.FRONT].preciseBoundingBox.maxPoint.y * 10
    step(plans, parts, b.PLATE, s.cyl(-16, 41.72, -6.7, .3, 2.35), "join",
         "V20 retire the long shared case bolt rear insert")
    step(plans, parts, b.BACK, s.cyl(18.1, 41.72, .3, 4.6, 2.8), "join",
         "V20 close the old left case insert seat")
    for x, side in ((18.1, "left"), (-16.0, "right")):
        y0 = 4.6 if x > 0 else .3
        step(plans, parts, b.BACK, s.cyl(x, 41.72, y0, 11.4, 1.71), "join",
             "V20 retire the " + side + " unsupported rear through bore")
        seat = 30.5 if x > 0 else 29.5
        step(plans, parts, b.FRONT, s.cyl(x, 41.72, 11.4, seat, 1.71), "join",
             "V20 close the old " + side + " receiver through bore")
        step(plans, parts, b.FRONT, s.cyl(x, 41.72, seat, front_y, 3.06), "join",
             "V20 continuous front face without the old " + side + " head recess")
    for x, side in ((18.1, "left"), (-16.0, "right")):
        lug = cylinder_z(x, 25.5, 40.0, 45.5, 3.7)
        if x > 0:
            web = s.box(20.5, 22.5, 11.4, 29.2, 40.0, 45.5)
            end = s.box(x, 22.5, 21.8, 29.2, 40.0, 45.5)
            root = s.box(18.5, 20.5, 19.8, 21.8, 40.0, 45.5)
            s.op(root, cylinder_z(18.5, 19.8, 39.4, 45.6, 2.0), "cut")
            clearance = s.box(20.3, 22.6, 10.4, 29.4, 39.8, 45.5)
            fore_clearance = s.box(x, 22.6, 21.6, 29.4, 39.8, 45.5)
        else:
            web = s.box(-22.5, -20.5, 11.4, 29.2, 40.0, 45.5)
            end = s.box(-22.5, x, 21.8, 29.2, 40.0, 45.5)
            root = s.box(-20.5, -18.5, 19.8, 21.8, 40.0, 45.5)
            s.op(root, cylinder_z(-18.5, 19.8, 39.4, 45.6, 2.0), "cut")
            clearance = s.box(-22.6, -20.3, 10.4, 29.4, 39.8, 45.5)
            fore_clearance = s.box(-22.6, x, 21.6, 29.4, 39.8, 45.5)
        for shape in (web, end, root):
            s.op(lug, shape, "join")
        s.op(clearance, cylinder_z(x, 25.5, 39.8, 45.5, 3.9), "join")
        s.op(clearance, fore_clearance, "join")
        if x > 0:
            expanded_root = s.box(18.5, 20.3, 19.8, 21.6, 39.8, 45.5)
            s.op(expanded_root, cylinder_z(18.5, 19.8, 39.2, 45.6, 1.8), "cut")
        else:
            expanded_root = s.box(-20.3, -18.5, 19.8, 21.6, 39.8, 45.5)
            s.op(expanded_root, cylinder_z(-18.5, 19.8, 39.2, 45.6, 1.8), "cut")
        s.op(clearance, expanded_root, "join")
        step(plans, parts, b.FRONT, clearance, "cut",
             "V20 open-backed " + side + " lap pocket with print-fit side clearance")
        step(plans, parts, b.BACK, lug, "join",
             "V20 integrated " + side + " load rail and true R2 tangent lug root")
        pilot = cylinder_z(x, 25.5, 41.25, 45.6, 2.0)
        s.op(pilot, cylinder_z(x, 25.5, 39.9, 41.35, 1.7), "join")
        step(plans, parts, b.BACK, pilot, "cut",
             "V20 vertical " + side + " heatset pilot with bed-open screw clearance")
        step(plans, parts, b.FRONT, cylinder_z(x, 25.5, 45.4, 48.8, 1.7), "cut",
             "V20 short vertical " + side + " case clamp shank")
        step(plans, parts, b.FRONT, cylinder_z(x, 25.5, 47.05, 48.8, 3.05), "cut",
             "V20 flush " + side + " top button head")
    step(plans, parts, b.PLATE, s.cyl(-16, 40.72, -6.8, .4, 1.7), "cut",
         "V20 separate short rear plate clamp one millimetre lower")
    rear_pilot = s.cyl(-16, 40.72, .3, 4.6, 2.0)
    s.op(rear_pilot, s.cyl(-16, 40.72, 4.5, 5.5, 1.7), "join")
    step(plans, parts, b.BACK, rear_pilot, "cut",
         "V20 rear-loaded independent actuator plate heatset")
    hardware = {}
    for x, screw_name, insert_name in ((18.1, LEFT_SCREW, LEFT_INSERT),
                                        (-16.0, RIGHT_SCREW, RIGHT_INSERT)):
        screw = m.screw_shape(x, 0, 47.05, 2.85, 1.65, 41.05)
        rotation = adsk.core.Matrix3D.create()
        rotation.setToRotation(math.pi / 2, adsk.core.Vector3D.create(1, 0, 0),
                               adsk.core.Point3D.create(0, 0, 0))
        if not s.tbm().transform(screw, rotation):
            raise RuntimeError("The short top-down screw rotation failed")
        hardware[screw_name] = m.translated(screw, dy=25.5)
        hardware[insert_name] = rotate_y_to_z(
            STATE["definitions"][insert_name], x, 25.5, 43.5)
    hardware[REAR_SCREW] = m.screw_shape(-16, 40.72, -6.7, 2.85, 1.65, 3.3)
    hardware[REAR_INSERT] = m.translated(STATE["definitions"][LEFT_INSERT],
                                       dx=-34.1, dz=-1.0)
    for name, shape in hardware.items():
        b.one_solid(shape, name)
    report = {
        "long_through_bolts_replaced_not_forced_into_the_moving_arm": True,
        "top_clamps": "2 x M3x6 button head, recessed flush with Z48.7",
        "top_clamp_axes_xy_mm": [[18.1, 25.5], [-16.0, 25.5]],
        "under_head_z_mm": 47.05, "screw_tip_z_mm": 41.05,
        "insert_z_mm": [41.5, 45.5], "nominal_insert_thread_engagement_mm": 4.0,
        "insert_pilot_extra_depth_mm": .25, "central_tip_clearance_is_through_open": True,
        "tip_recess_above_lug_floor_mm": 1.05, "lap_contact_z_mm": 45.5,
        "lap_side_clearance_mm": .2, "load_rail_floor_z_mm": 40.0,
        "outboard_web_width_mm": 2.0, "load_lug_root_tangent_radius_mm": 2.0,
        "independent_rear_plate_clamp": "1 x M3x10, X-16/Z40.72, original-size M3 insert in P01",
        "rear_plate_clamp_drop_mm": 1.0, "nominal_rear_insert_thread_engagement_mm": 3.0,
        "two_added_hardware_bodies": [REAR_SCREW, REAR_INSERT],
        "plastic_case_width_mm": 45.0, "actuator_plate_thickness_mm": 7.0,
        "no_arm_thinning_required": True, "load_and_physical_fit_qualification_pending": True,
    }
    STATE.update(clamp_parts=parts, clamp_plans=plans, clamp_hardware=hardware,
                 clamps=report, top_down=True)
    b.write("supported_top_clamp_candidate.json", report)
    return report


def top_clamp_support():
    b = shared()
    s, _ = b.geometry()
    rows = []
    for x, side in ((18.1, "left"), (-16.0, "right")):
        for label, z0, z1, outer, inner in (
                ("insert surround", 41.25, 45.5, 3.7, 2.3),
                ("clamping roof", 45.5, 47.05, 3.7, 1.7),
                ("head collar", 47.05, 48.7, 4.25, 3.05)):
            required = cylinder_z(x, 25.5, z0, z1, outer)
            s.op(required, cylinder_z(x, 25.5, z0 - .1, z1 + .1, inner), "cut")
            for part in STATE["clamp_parts"].values():
                s.op(required, part, "cut")
            missing = required.volume * 1000 if required.lumps.count else 0.0
            rows.append({"side": side, "region": label, "missing_stock_mm3": missing})
            if missing > 1e-6:
                raise RuntimeError("A clamp lacks its intended continuous support: " + str(rows[-1]))
    report = {"supported_regions": rows, "all_material_continuous": True,
              "actual_solid_check_not_bounding_box_or_visual_only": True}
    b.write("top_clamp_support.json", report)
    return report


def concept_motion(app):
    b = shared()
    s, _ = b.geometry()
    if b.STATE.get("frozen_review"):
        raise RuntimeError("Do not replace an active final-review snapshot")
    frozen = b.STATE["superseded_frozen_review"]
    for name, path in STATE["paths"].items():
        if path[:2] in {"05", "07", "09", "10", "11"}:
            if b.difference(STATE["definitions"][name], frozen["definitions"][name],
                            "current input moving body " + name):
                raise RuntimeError("The concept pose source is not the current preserved geometry")
    rows = []
    b.STATE["frozen_review"] = frozen
    try:
        for angle in (0., 30., 60., 90., 120., 150., 170., 175.):
            posed = b.pose_shapes(app, angle)
            moving = {name: shape for name, shape in posed.items()
                      if STATE["paths"][name][:2] in {"05", "07", "09", "10", "11"}}
            new = dict(STATE["clamp_parts"])
            new.update(STATE["clamp_hardware"])
            contacts, inherited = [], []
            for name, shape in new.items():
                for other, partner in moving.items():
                    overlap, _ = s.common_volume(shape, partner)
                    if overlap > 1e-5:
                        previous = 0.0
                        if name in STATE["world"]:
                            previous, _ = s.common_volume(STATE["world"][name], partner)
                        entry = {"part": name, "moving": other, "overlap_mm3": overlap,
                                 "preserved_input_overlap_mm3": previous}
                        if overlap <= previous + 1e-5:
                            inherited.append(entry)
                        else:
                            contacts.append(entry)
            rows.append({"cam_deg": angle, "new_part_vs_moving_contacts": contacts,
                         "preexisting_input_contacts_requiring_shape_refinement": inherited})
            b.write("top_clamp_concept_motion.json", {"poses": rows, "complete": False})
            if contacts:
                raise RuntimeError("A new clamp obstructs motion: " + str(contacts))
    finally:
        b.STATE.pop("frozen_review")
    STATE["concept_checked"] = True
    b.write("top_clamp_concept_motion.json", {"poses": rows, "complete": True})
    return {"sampled_poses": len(rows), "all_new_clamps_clear": True,
            "preexisting_input_contacts": sum(len(row[
                "preexisting_input_contacts_requiring_shape_refinement"]) for row in rows),
            "full_final_sweep_still_required": True}


def replace_native_body(app, name, expected, target, label):
    b = shared()
    b.require(app)
    s, _ = b.geometry()
    body = b.logical_bodies(app)[name].nativeObject
    if b.difference(body, expected, "before coherent body " + name):
        raise RuntimeError("The live body changed since the preserved input: " + name)
    b.one_solid(target, name)
    component, appearance = body.parentComponent, body.appearance
    removed = component.features.removeFeatures.add(body)
    removed.name = "Retain source history before " + label
    feature = component.features.baseFeatures.add()
    feature.name = label
    if not feature.startEdit():
        raise RuntimeError("Could not start the coherent native replacement")
    try:
        new_body = component.bRepBodies.add(s.tbm().copy(target), feature)
        new_body.name = name
    finally:
        if not feature.finishEdit():
            raise RuntimeError("Could not finish the coherent native replacement")
    replacement = feature.bodies.item(0)
    replacement.name = name
    replacement.appearance = appearance
    delta = b.difference(target, replacement, "coherent native result " + name)
    if delta:
        raise RuntimeError("The coherent native replacement differs from its reviewed definition")
    return {"body": name, "exact_candidate_difference_mm3": delta,
            "source_history_retained_in_the_owned_copy": True, **b.stats(replacement)}


def apply_clamps(app, ui):
    b = shared()
    if not STATE.get("concept_checked") or STATE.get("clamps_applied"):
        raise RuntimeError("Review the clamp concept once before applying it")
    if ui.activeCommand == "FreeOrbitCommand":
        ui.terminateActiveCommand()
    if ui.activeCommand != "SelectCommand":
        raise RuntimeError("Finish the current native edit before applying the coherent revision")
    next(doc for doc in app.documents if doc.creationId == STATE["document"]).activate()
    b.STATE["tools"].normalize_edit_pose(app)
    s, _ = b.geometry()
    rows = []
    for name, target in STATE["clamp_parts"].items():
        rows.append(replace_native_body(app, name, STATE["definitions"][name], target,
                                        "V20 supported lap clamps - coherent " + name))
        b.STATE["candidate"][name] = s.tbm().copy(target)
        b.write("native_clamp_application.json", {"bodies": rows, "complete": False})
    for name, target in STATE["clamp_hardware"].items():
        if name in (REAR_SCREW, REAR_INSERT):
            continue
        rows.append(replace_native_body(app, name, STATE["definitions"][name], target,
                                        "V20 short supported clamp " + name))
        b.STATE["hardware"][name] = s.tbm().copy(target)
        b.write("native_clamp_application.json", {"bodies": rows, "complete": False})
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    fixed = next(o.component for o in root.occurrences if o.name.startswith("01 "))
    s.add_group(fixed, "V20 independent short rear plate clamp", [
        (STATE["clamp_hardware"][REAR_SCREW], REAR_SCREW, b.STATE["appearances"][RIGHT_SCREW]),
        (STATE["clamp_hardware"][REAR_INSERT], REAR_INSERT, b.STATE["appearances"][LEFT_INSERT]),
    ])
    by, _ = b.physical_inventory(b.logical_bodies(app))
    if len(by) != len(STATE["definitions"]) + 2:
        raise RuntimeError("The new clamp inventory is not the source plus exactly two new references")
    for name in (REAR_SCREW, REAR_INSERT):
        b.STATE["hardware"][name] = s.tbm().copy(STATE["clamp_hardware"][name])
        b.STATE["baseline_transforms"][name] = list(by[name].assemblyContext.transform2.asArray())
        b.STATE["appearances"][name] = by[name].appearance
    b.STATE["expected_physical_count"] = len(by)
    STATE["clamps_applied"] = True
    b.STATE["controller"].validate(adsk.fusion.Design.cast(app.activeProduct))
    b.write("native_clamp_application.json", {"bodies": rows, "complete": True,
                                             "physical_bodies": len(by)})
    return {"replaced_native_bodies": len(rows), "added_references": 2,
            "physical_bodies": len(by), "short_clamp_laps_applied": True}
