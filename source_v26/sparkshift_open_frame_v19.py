"""Owned open-frame print-feedback revision; physical fit and load qualification pending."""

import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "sparkshift_open_frame_v19"
PAYLOAD = OUT / "release"
STATE = {}
BACK = "PRINT_motor_mount"
PLATE = "PRINT_REAR_MOTOR_SERVO_SPACER"
FRONT = "PRINT_000_outer_shell_of_extruder_1"
CAM = "PRINT_DIRECT_CAM"
SERVO = "HOBBY_SERVO_ENVELOPE"
SPLINE = "MG90S_21T_OD4p86_H3p36_M2p5_REFERENCE_FIT_PENDING"
REAR_BEARING = "CAM_REAR_MR128ZZ_8x12x3p5"
FORE_BEARING = "CAM_OUTBOARD_MF85ZZ_5x8x2p5"
CENTRE = (10.5, 50.72059521522819)
PLATE_REAR, PLATE_FRONT = -6.7, 0.3
HEAD_Z = 48.7
SEED_SHA = "49895ba329c2a875ec778425336047db081d8995684efec73d3f951abb87ccc9"
USER_DOCUMENT = "7208f78a-df02-4b3a-a161-dca32d189213"
CHANGED_PRINTS = {
    "P01": (BACK, "P01_Open_frame_back_v19", (0, 1, 0)),
    "P02": (PLATE, "P02_7mm_keyway_motor_servo_plate_v19", (0, -1, 0)),
    "P03": (FRONT, "P03_Open_receiver_with_MF85_support_v19", (0, -1, 0)),
    "P05": (CAM, "P05_Clocked_cam_v19_same_as_v18", (0, 1, 0)),
}


def load_file(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def require(app):
    if app.activeDocument.creationId != STATE.get("document"):
        raise RuntimeError("Activate only the owned v19 open-frame revision")


def require_review_input(app):
    if not STATE.get("frozen_review"):
        require(app)


def bodies(app):
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    rows = [body for occurrence in root.allOccurrences for body in occurrence.bRepBodies]
    if len(rows) != len({body.name for body in rows}):
        raise RuntimeError("The physical body names are not unique")
    return {body.name: body for body in rows}


def geometry():
    native = STATE["native"]
    return native.load("pancake_paths_study"), native.load("sparkshift_ahg_min")


def bounds(shape):
    box = shape.preciseBoundingBox if isinstance(shape, adsk.fusion.BRepBody) else shape.boundingBox
    return [[v * 10 for v in p.asArray()] for p in (box.minPoint, box.maxPoint)]


def stats(shape):
    return {"volume_mm3": shape.volume * 1000, "bounds_mm": bounds(shape),
            "solid": shape.isSolid, "lumps": shape.lumps.count,
            "boundary_shells": sum(lump.shells.count for lump in shape.lumps),
            "faces": shape.faces.count}


def difference(first, second, label):
    s, _ = geometry()
    frames = [
        None,
        (7.0, (1.0, 2.0, 3.0)),
        (90.0, (1.0, 1.0, 1.0)),
    ]
    preferred = STATE.setdefault("comparison_frames", {}).get(label, 0)
    order = [preferred] + [i for i in range(len(frames)) if i != preferred]
    errors = []
    for index in order:
        a, b = s.tbm().copy(first), s.tbm().copy(second)
        if frames[index] is not None:
            angle, xyz = frames[index]
            axis = adsk.core.Vector3D.create(*xyz)
            axis.normalize()
            matrix = adsk.core.Matrix3D.create()
            matrix.setToRotation(math.radians(angle), axis, adsk.core.Point3D.create(0, 0, 0))
            if not s.tbm().transform(a, matrix) or not s.tbm().transform(b, matrix):
                raise RuntimeError("Could not apply a common comparison measurement frame")
        try:
            value = STATE["native"].exact_difference(a, b)
        except RuntimeError as error:
            if not any(code in str(error) for code in
                       ("ASM_BODY_VERTEX_CRUMBLE", "ASM_INCONS_FACE", "ASM_NOT_HANDLED")):
                raise
            errors.append({"frame": index, "kernel_error": str(error)})
            write("comparison_frame_diagnostics.json",
                  {"label": label, "attempts": errors, "geometry_healing_not_called": True})
            continue
        STATE["comparison_frames"][label] = index
        if errors or index:
            STATE.setdefault("comparison_frame_receipts", []).append({
                "label": label, "common_rigid_frame": frames[index],
                "exact_symmetric_difference_mm3": value, "earlier_failures": errors,
                "both_solids_transformed_identically_without_healing": True})
            write("comparison_frame_receipts.json", STATE["comparison_frame_receipts"])
        return value
    raise RuntimeError("Exact comparison remains kernel-limited for " + label
                       + "; no equality result is inferred")


def one_solid(shape, label):
    if (not shape.isSolid or shape.lumps.count != 1 or shape.volume <= 0
            or not math.isfinite(shape.volume)):
        write("failed_candidate.json", {"label": label, "shape": stats(shape),
                                       "lumps": [{"volume_mm3": l.volume * 1000,
                                                  "bounds_mm": bounds(l)} for l in shape.lumps]})
        raise RuntimeError("Not one positive connected solid: " + label)
    if sum(lump.shells.count for lump in shape.lumps) != 1:
        write("failed_candidate.json", {"label": label, "shape": stats(shape)})
        raise RuntimeError("A sealed internal cavity remains: " + label)


def initialize(app, ui):
    if STATE:
        raise RuntimeError("The owned open-frame revision has already been initialized")
    if ui.activeCommand not in ("SelectCommand", "FreeOrbitCommand"):
        raise RuntimeError("An unrelated native editing command is active")
    if ui.activeCommand == "FreeOrbitCommand":
        ui.terminateActiveCommand()
    prior = sys.modules["sparkshift_slim_v18"]
    archive = BASE / "sparkshift_slim_v18" / "release" / "cad" / "SparkShift_slim_print_feedback_v18_WIP.f3d"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SEED_SHA:
        raise RuntimeError("The intact functional seed archive hash changed")
    OUT.mkdir(exist_ok=True)
    (OUT / "cad").mkdir(exist_ok=True)
    (OUT / "images").mkdir(exist_ok=True)
    user = next((doc for doc in app.documents if doc.creationId == USER_DOCUMENT), None)
    if user is None:
        raise RuntimeError("The user cut study must be preserved before starting")
    user_design = adsk.fusion.Design.cast(user.products.itemByProductType("DesignProductType"))
    manager = adsk.fusion.TemporaryBRepManager.get()
    user_shapes = {body.name: manager.copy(body.nativeObject or body)
                   for occurrence in user_design.rootComponent.allOccurrences
                   for body in occurrence.bRepBodies}
    user_archive = OUT / "cad" / ("Input_USER_open_frame_latest_" + time.strftime("%Y%m%d_%H%M%S") + ".f3d")
    if not user_design.exportManager.execute(
            user_design.exportManager.createFusionArchiveExportOptions(str(user_archive))):
        raise RuntimeError("Could not preserve the latest manual cut study")
    document = app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(archive)))
    if document is None or document.creationId == USER_DOCUMENT:
        raise RuntimeError("Could not isolate the intact seed as a new revision")
    document.activate()
    document.name = "SparkShift v19 - open frame and 7mm motor plate - WIP"
    native = load_file("sparkshift_v19_native", BASE / "sparkshift_opening_v14.py")
    tools = load_file("sparkshift_v19_shared_tools", BASE / "sparkshift_slim_v18.py")
    player = load_file("sparkshift_v19_player",
                       BASE / "sparkshift_dual_cam_bearings_v17" / "playback"
                       / "SparkShiftCamPlayback" / "SparkShiftCamPlayback.py")
    STATE.update(document=document.creationId, native=native, controller=player, tools=tools,
                 source_document=USER_DOCUMENT, source_shapes=user_shapes,
                 exact_readback_helper=prior.STATE["exact_readback_helper"],
                 plans={}, candidate={}, hardware={}, applied=[], model_checks=[])
    native.STATE = STATE
    native.OUT = OUT
    tools.STATE = STATE
    tools.OUT = OUT
    tools.PAYLOAD = PAYLOAD
    tools.normalize_edit_pose(app)
    by = bodies(app)
    if len(by) != 139:
        raise RuntimeError("The intact functional seed is not the expected 139-body assembly")
    STATE["before"] = {name: manager.copy(body.nativeObject or body) for name, body in by.items()}
    STATE["before_world"] = {name: manager.copy(body) for name, body in by.items()}
    STATE["appearances"] = {name: body.appearance for name, body in by.items()}
    STATE["baseline_transforms"] = {name: list(body.assemblyContext.transform2.asArray())
                                    for name, body in by.items()}
    report = {
        "owned_document": document.creationId, "seed_archive": str(archive), "seed_sha256": SEED_SHA,
        "user_study_document": USER_DOCUMENT, "user_study_archive": str(user_archive),
        "user_study_sha256": hashlib.sha256(user_archive.read_bytes()).hexdigest(),
        "user_study_bodies": len(user_shapes), "seed_bodies": len(by),
        "user_study_geometry_not_modified": True,
        "user_study_part_stats": {name: stats(user_shapes[name]) for name in
                                 (BACK, PLATE, FRONT) if name in user_shapes},
        "measured_servo_front_cover_width_mm": {"typical": [14.4, 14.5], "diagonal_max": 14.75},
        "servo_front_cover_axial_depth_mm": {"inherited_unmeasured": 1.9, "bench_fit_pending": True},
    }
    write("source_capture.json", report)
    return report


def parameters():
    if "parameters" not in STATE:
        s, _ = geometry()
        motor = s.centre(STATE["before"]["AHG laminated stator"])
        STATE["parameters"] = {
            "plate_y_mm": [PLATE_REAR, PLATE_FRONT], "overall_plate_thickness_mm": 7.0,
            "motor_facing_datum_unchanged_y_mm": PLATE_FRONT,
            "receiver_main_head_z_mm": HEAD_Z,
            "cam_axis_xz_mm": list(CENTRE), "motor_axis_xz_mm": list(motor),
            "motor_keyway_width_mm": 10.4,
            "motor_bore_radius_mm": 18.55, "motor_body_radius_mm": 18.25,
            "motor_keyway_max_extension_from_body_OD_mm": 6.0,
            "motor_keyway_max_extension_from_bore_mm": 5.7,
            "motor_keyway_outer_radius_mm": 24.25,
            "motor_keyway_top_z_mm": motor[1] + 24.25,
            "motor_keyway_corner_radius_mm": 4.3,
            "plate_insertion_clock_deg": -135.0,
            "servo_front_cover_width_measured_max_mm": 14.75,
            "servo_front_cover_relief_width_mm": 15.4,
            "servo_cover_side_clearance_at_measured_max_mm": 0.325,
            "servo_front_cover_axial_depth_inherited_not_measured_mm": 1.9,
            "servo_front_cover_end_y_inherited_mm": -2.2,
            "servo_cover_relief_forward_plane_y_mm": -2.0,
            "servo_cover_nominal_axial_clearance_mm": 0.2,
            "servo_upper_lower_ear_centres_xz_mm": [[10.5, CENTRE[1] + 8.35],
                                                   [10.5, CENTRE[1] - 19.45]],
            "upper_right_case_axis_xz_mm": [-16.0, 41.72],
            "left_case_axis_xz_mm": [18.1, 41.72],
            "upper_right_rear_M3_insert_y_mm": [-6.5, -2.5],
            "upper_right_case_screw": "M3x35 button head, under-head plane Y29.5",
            "upper_right_case_screw_tip_y_mm": -5.5,
            "upper_right_case_nominal_insert_engagement_mm": 3.0,
            "upper_left_case_screw": "M3x30 button head, under-head plane Y30.5",
            "upper_left_case_screw_tip_y_mm": 0.5,
            "upper_left_case_nominal_insert_engagement_mm": 3.8,
            "stepper_ear_screws": "2 x M3x10 button head; inherited flange thread depth unqualified",
            "lower_plate_screw": "M3x10 button head",
            "lower_shared_case_screw": "M3x35 button head in existing lower plate heatset",
            "M2_insert_OD_length_mm": [3.2, 3.0],
            "M2_insert_y_mm": [-2.9, 0.1],
            "MR128ZZ_and_MF85ZZ_positions_unchanged": True,
            "fit_and_loaded_strength_not_qualified": True,
        }
        write("design_parameters.json", STATE["parameters"])
    return STATE["parameters"]


def edit(plan, shape, tool, operation, label):
    s, _ = geometry()
    if not tool.lumps.count:
        raise RuntimeError("Empty bounded geometry tool: " + label)
    if operation == "cut":
        overlap, _ = s.common_volume(shape, tool)
        if overlap == 0:
            return
    start = shape.volume * 1000
    s.op(shape, s.tbm().copy(tool), operation)
    if not shape.isSolid or shape.lumps.count != 1 or shape.volume <= 0:
        write("failed_edit.json", {"label": label, "shape": stats(shape),
                                  "pieces": [{"volume_mm3": l.volume * 1000,
                                              "bounds_mm": bounds(l)} for l in shape.lumps]})
        raise RuntimeError("The bounded edit disconnects the print: " + label)
    plan.append({"tool": s.tbm().copy(tool), "operation": operation,
                 "label": label, "expected": s.tbm().copy(shape)})
    STATE.setdefault("build_journal", []).append(
        {"label": label, "operation": operation, "before_mm3": start,
         "after_mm3": shape.volume * 1000})
    write("candidate_build_journal.json", STATE["build_journal"])


def complete(name, shape, plan):
    one_solid(shape, name)
    STATE["candidate"][name] = shape
    STATE["plans"][name] = plan
    write("candidate_parts.json", {name: stats(shape) for name, shape in STATE["candidate"].items()})
    return {"part": name, "steps": len(plan), **stats(shape)}


def capsule(first, second, y0, y1, radius):
    s, m = geometry()
    dx, dz = second[0] - first[0], second[1] - first[1]
    length = math.hypot(dx, dz)
    result = s.cyl(*first, y0, y1, radius)
    s.op(result, s.cyl(*second, y0, y1, radius), "join")
    obb = m.load("ahg_placement").obb(
        (first[0] + second[0]) / 2, (y0 + y1) / 2, (first[1] + second[1]) / 2,
        (dx / length, dz / length), length, y1 - y0, 2 * radius)
    s.op(result, obb, "join")
    return result


def prepare_plate(app):
    require(app)
    if PLATE in STATE["candidate"]:
        raise RuntimeError("The 7mm plate candidate already exists")
    s, m = geometry()
    p = parameters()
    old = STATE["before"][PLATE]
    shape, plan = s.tbm().copy(old), []
    edit(plan, shape, s.box(-30, 30, -20, PLATE_REAR, -30, 80), "cut",
         "V19 seven millimetre plate - fixed motor-facing datum")
    edit(plan, shape, s.cyl(-16, 41.72, PLATE_REAR, 0.3, 2.6), "join",
         "V19 close retired deeper shared insert pocket")
    edit(plan, shape, s.cyl(-16, 41.72, -6.5, -2.5, 2.1), "cut",
         "V19 rear-loaded shared M3 insert in 7mm plate")
    edit(plan, shape, m.cone_y(-16, 41.72, -6.75, 2.35, -6.45, 2.1), "cut",
         "V19 rear heatset insertion lead")
    edit(plan, shape, s.cyl(-16, 41.72, -2.5, 0.4, 1.7), "cut",
         "V19 front thread-clearance and backed insert shoulder")
    cx, cz = CENTRE
    edit(plan, shape, s.box(cx - 7.7, cx + 7.7, -6.8, -4.1,
                           cz - 21.95, cz + 10.85), "cut",
         "V19 servo insertion throat for measured 14p75 cover")
    edit(plan, shape, s.box(cx - 7.7, cx + 7.7, -4.2, -2.0,
                           cz - 17.25, cz + 6.15), "cut",
         "V19 measured wider servo gearbox cover relief")
    lead = s.box(cx - 8.0, cx + 8.0, -6.8, -6.35, cz - 17.25, cz + 6.15)
    edit(plan, shape, lead, "cut", "V19 relieved rear servo entry mouth")
    mx, mz = p["motor_axis_xz_mm"]
    half = p["motor_keyway_width_mm"] / 2
    top = p["motor_keyway_top_z_mm"]
    bottom = mz + 14.0
    radius = p["motor_keyway_corner_radius_mm"]
    corners = [(mx - half + radius, top - radius, radius),
               (mx + half - radius, top - radius, radius)]
    keyway = m.rounded_box(mx - half, mx + half, -6.8, 0.4, bottom, top, corners)
    s.op(keyway, s.cyl(mx, mz, -6.9, 0.5, p["motor_keyway_outer_radius_mm"]), "common")
    edit(plan, shape, keyway, "cut", "V19 rounded top keyway for XH connector and lead passage")
    STATE["motor_keyway_tool"] = keyway
    mask = s.box(-30, 30, -7, 1, -30, HEAD_Z)
    s.op(mask, s.box(0.0, 22.6, -7, 1, HEAD_Z - 0.1, 63), "join")
    trim = s.box(-30, 30, -7, 1, HEAD_Z, 80)
    s.op(trim, mask, "cut")
    edit(plan, shape, trim, "cut", "V19 remove tall unused left plate enclosure")
    obsolete_tail = s.cyl(18.1, 41.72, -4.0, 0.3, 1.85)
    s.op(obsolete_tail, s.box(cx - 7.7, cx + 7.7, -6.8, -2.0,
                              cz - 17.25, cz + 6.15), "cut")
    edit(plan, shape, obsolete_tail, "join",
         "V19 close obsolete long left-screw tail notch beside servo")
    return complete(PLATE, shape, plan)


def prepare_servo(app):
    require(app)
    s, m = geometry()
    before = STATE["before"][SERVO]
    cx, cz = CENTRE
    cover = m.rounded_box(cx - 7.375, cx + 7.375, -4.1, -2.2,
                          cz - 16.95, cz + 5.85, [
                              (cx - 6.375, cz - 15.95, 1.0),
                              (cx + 6.375, cz - 15.95, 1.0),
                              (cx - 6.375, cz + 4.85, 1.0),
                              (cx + 6.375, cz + 4.85, 1.0)])
    shape = s.tbm().copy(before)
    s.op(shape, cover, "join")
    one_solid(shape, "measured servo front-cover envelope")
    STATE["hardware"][SERVO] = shape
    write("measured_servo_envelope.json", {
        "body": stats(shape), "measured_front_cover_width_max_mm": 14.75,
        "rounded_rectangular_conservative_front_cover_not_exact_maker_CAD": True,
        "axial_depth_and_longitudinal_dimensions_inherited_fit_pending": True,
        "shaft_axis_ear_hole_positions_and_servo_clock_unchanged": True,
    })
    return stats(shape)


def prepare_back(app):
    require(app)
    s, _ = geometry()
    old = STATE["before"][BACK]
    shape, plan = s.tbm().copy(old), []
    mask = s.box(-30, 30, 0.2, 25, -70, HEAD_Z)
    s.op(mask, s.cyl(*CENTRE, 0.2, 4.15, 8.25), "join")
    s.op(mask, s.cyl(10.5, CENTRE[1] + 8.35, 0.2, 3.0, 3.2), "join")
    s.op(mask, capsule((10.5, CENTRE[1] + 8.35), CENTRE, 0.2, 3.0, 2.4), "join")
    s.op(mask, capsule(CENTRE, (18.1, 41.72), 0.2, 4.15, 3.1), "join")
    trim = s.box(-30, 30, 0.2, 25, HEAD_Z, 80)
    s.op(trim, mask, "cut")
    edit(plan, shape, trim, "cut",
         "V19 open upper back frame - rear bearing ring and servo ear brace retained")
    return complete(BACK, shape, plan)


def prepare_front(app):
    require(app)
    s, m = geometry()
    old = STATE["before"][FRONT]
    shape, plan = s.tbm().copy(old), []
    crossbeam = m.rounded_box(-16.0, 19.0, 13.7, 16.7, 44.5, 47.5, [
        (-15.0, 45.5, 1.0), (-15.0, 46.5, 1.0),
        (18.0, 45.5, 1.0), (18.0, 46.5, 1.0)])
    edit(plan, shape, crossbeam, "join",
         "V19 compact receiver cross-tie below cam retainer and behind filament")
    STATE["receiver_crossbeam"] = crossbeam
    support = s.box(-30, 30, 10.5, 34, -30, HEAD_Z)
    s.op(support, s.cyl(*CENTRE, 10.5, 14.5, 6.3), "join")
    s.op(support, capsule(CENTRE, (18.1, 41.72), 10.5, 14.5, 3.1), "join")
    trim = s.box(-30, 30, 2.9, 34, -30, 80)
    s.op(trim, support, "cut")
    edit(plan, shape, trim, "cut",
         "V19 open receiver crown with independent opposite-side MF85 support")
    edit(plan, shape, s.cyl(-16.0, 41.72, 29.5, 33.5, 3.05), "cut",
         "V19 deeper single upper-right M3x35 head seat")
    edit(plan, shape, s.cyl(18.1, 41.72, 30.5, 33.5, 3.05), "cut",
         "V19 shorter upper-left clamp - no screw tail in wider servo cover")
    return complete(FRONT, shape, plan)


def prepare_hardware(app):
    require(app)
    s, m = geometry()
    before = STATE["before"]
    replacements = {}
    for index in (0, 1):
        old_name = "M3x18 ISO7380 motor ear " + str(index) + " (rear entry)"
        x, z = s.centre(before[old_name])
        replacements[old_name] = m.screw_shape(x, z, PLATE_REAR, 2.85, 1.65,
                                               PLATE_REAR + 10.0)
    x, z = s.centre(before["SPACER_M3x14_SHCS_0"])
    replacements["SPACER_M3x14_SHCS_0"] = m.screw_shape(
        x, z, PLATE_REAR, 2.85, 1.65, PLATE_REAR + 10.0)
    replacements["UPPER_RIGHT_SHARED_M3x40_FRAME"] = m.screw_shape(
        -16.0, 41.72, 29.5, 2.85, 1.65, -5.5)
    old_insert = before["UPPER_RIGHT_REAR_M3_HEATSET_4p6x4"]
    ix, iz = s.centre(old_insert)
    replacements["UPPER_RIGHT_REAR_M3_HEATSET_4p6x4"] = m.translated(
        old_insert, dx=-16.0 - ix, dy=2.0, dz=41.72 - iz)
    replacements["CLAM_M3x40_FRAME_3"] = m.screw_shape(
        -16.0, -13.0, 31.5, 2.85, 1.65, -3.5)
    replacements["FRAME_M3x35_into_P01_insert"] = m.screw_shape(
        18.1, 41.72, 30.5, 2.85, 1.65, 0.5)
    for name, shape in replacements.items():
        one_solid(shape, name)
    STATE["hardware"].update(replacements)
    write("hardware_candidates.json", {name: stats(shape) for name, shape in STATE["hardware"].items()})
    return {"changed_hardware_references": len(STATE["hardware"]),
            "same_threads_no_extra_nuts": True}


def inspect_candidates(app):
    require(app)
    s, _ = geometry()
    shapes = dict(STATE["before_world"])
    shapes.update(STATE["candidate"])
    shapes.update(STATE["hardware"])
    rows = []
    for name, shape in STATE["candidate"].items():
        gain = s.tbm().copy(shape)
        s.op(gain, STATE["before"][name], "cut")
        if not gain.lumps.count:
            continue
        for other, fixed in shapes.items():
            if other == name:
                continue
            volume, overlap = s.common_volume(gain, fixed)
            if volume > 1e-5:
                rows.append({"changed": name, "against": other,
                             "new_material_overlap_mm3": volume,
                             "bounds_mm": bounds(overlap)})
    for name, shape in STATE["hardware"].items():
        for other, fixed in shapes.items():
            if other == name or (other in STATE["hardware"] and other < name):
                continue
            volume, overlap = s.common_volume(shape, fixed)
            if volume > 1e-5:
                rows.append({"changed_reference": name, "against": other,
                             "whole_part_overlap_mm3": volume, "bounds_mm": bounds(overlap)})
    write("candidate_contacts.json", {"contacts": rows, "insert_press_fits_not_filtered": True})
    return rows


def check_motor_insertion(app):
    require_review_input(app)
    s, m = geometry()
    axis = parameters()["motor_axis_xz_mm"]
    fixed = {name: shape for name, shape in STATE["before_world"].items()
             if name.startswith("AHG ") and not name.startswith(
                 ("AHG lead red", "AHG lead green", "AHG lead yellow", "AHG lead blue"))}
    if len(fixed) != 5:
        raise RuntimeError("Check the LDO motor body, flange, pinion and rigid XH connector")
    stages = [
        ("rotate loose plate clear of motor", [(angle, -40.0) for angle in range(0, -136, -5)]),
        ("slide keyed plate over rigid connector after feeding flexible leads",
         [(-135.0, -40.0 + i * 0.5) for i in range(81)]),
        ("rotate seated 7mm plate back onto motor ear datum",
         [(angle, 0.0) for angle in range(-135, 1, 5)]),
    ]
    rows = []
    for stage, poses in stages:
        for angle, dy in poses:
            moved = m.translated(m.rotated(STATE["candidate"][PLATE], axis, angle), dy=dy)
            collisions = []
            for name, shape in fixed.items():
                volume, _ = s.common_volume(moved, shape)
                if volume > 1e-5:
                    collisions.append({"motor_part": name, "overlap_mm3": volume})
            row = {"stage": stage, "plate_clock_deg": angle, "plate_offset_y_mm": dy,
                   "unexpected_interferences": collisions}
            rows.append(row)
            write("motor_rotate_slide_rotate_path.json", {
                "poses": rows, "motor_reference_count": len(fixed),
                "plate_is_loose_before_frame_servo_and_screws_installation": True,
                "flexible_leads_fed_separately_not_treated_as_rigid_straight_tails": True,
                "wire_bending_and_connector_variant_fit_not_qualified": True,
            })
            if collisions:
                raise RuntimeError("The motor insertion path is blocked: " + json.dumps(row))
    plate_box = STATE["candidate"][PLATE].preciseBoundingBox
    thickness = (plate_box.maxPoint.y - plate_box.minPoint.y) * 10
    if abs(thickness - 7.0) > 1e-7:
        raise RuntimeError("The complete plate is not 7 mm thick")
    report = {
        "path_poses": len(rows), "plate_thickness_mm": thickness,
        "all_five_rigid_motor_parts_clear": True,
        "insertion_plate_clock_deg": -135.0,
        "free_plate_installation_required_before_attaching_frame_and_servo": True,
        "nominal_motor_radial_clearance_mm": 0.30,
        "nominal_keyway_connector_side_clearance_mm": (10.4 - 8.5) / 2,
        "nominal_keyway_top_clearance_to_rigid_connector_mm":
            parameters()["motor_keyway_top_z_mm"] - 25.6006030014535,
        "flexible_wire_tails_must_be_fed_through_separately": True,
        "straight_rigid_wire_tail_passage_not_claimed": True,
        "physical_hardware_tolerances_and_flexible_wire_path_not_qualified": True,
    }
    STATE["motor_path_verified"] = True
    write("motor_insertion_summary.json", report)
    return report


def verify_protected_geometry(app):
    require_review_input(app)
    s, _ = geometry()
    before, candidate = STATE["before"], STATE["candidate"]
    guards = [
        (BACK, "rear gear bearings, motor face and pilot",
         s.box(-22.4, 22.4, 0.3, 5.3, -18, 27)),
        (BACK, "belt clamps and MGN carriage interfaces",
         s.box(-30, 30, 0.2, 25, -60, -18)),
        (BACK, "MR128 rear cam bearing bore and fore shoulder",
         s.cyl(*CENTRE, 0.3, 4.05, 7.65)),
        (FRONT, "MF85 front race seat, flange shoulder and immediate wall",
         s.cyl(*CENTRE, 10.7, 13.2, 4.8)),
        (FRONT, "fixed compound fore bearing support",
         s.cyl(-9.5, 13.099982, 22.3, 27.0, 5.0)),
        (FRONT, "moving compound fore bearing support",
         s.cyl(9.5, 13.099982, 25.6, 30.0, 5.0)),
        (FRONT, "fixed HGX fore bearing support",
         s.cyl(-10.0502, 0.011542, 24.2, 28.0, 4.6)),
        (PLATE, "upper M2 ear shoulder and insert backing",
         s.cyl(10.5, CENTRE[1] + 8.35, -4.1, 0.3, 2.7)),
        (PLATE, "lower M2 ear shoulder and insert backing",
         s.cyl(10.5, CENTRE[1] - 19.45, -4.1, 0.3, 2.7)),
        (PLATE, "rear cam bearing bore and keeper race-contact profile",
         s.cyl(*CENTRE, -2.0, 0.3, 6.05)),
    ]
    for name, hardware in STATE["before_world"].items():
        if not name.startswith(("OCT_RECEIVER_MAGNET_", "OCT_LOCATOR_PIN_")):
            continue
        box = hardware.preciseBoundingBox
        magnet = name.startswith("OCT_RECEIVER_MAGNET_")
        margin = .6 if magnet else .45
        region = s.box(
            box.minPoint.x * 10 - margin, box.maxPoint.x * 10 + margin,
            27.0 if magnet else box.minPoint.y * 10 - .6,
            32.0 if magnet else box.maxPoint.y * 10 + .6,
            box.minPoint.z * 10 - margin, box.maxPoint.z * 10 + margin)
        guards.append((FRONT, name + (" pocket and backing" if magnet else " seat and retention"), region))
    rows = []
    for name, label, region in guards:
        old, new = s.tbm().copy(before[name]), s.tbm().copy(candidate[name])
        s.op(old, region, "common")
        s.op(new, region, "common")
        delta = difference(old, new, "functional " + label)
        rows.append({"part": name, "functional_region": label,
                     "exact_definition_difference_mm3": delta})
        write("protected_geometry.json", {"regions": rows, "complete": False})
        if delta:
            raise RuntimeError("A protected interface changed: " + label)
    report = {"regions": rows, "complete": True,
              "unchanged_CAM_spline_profile_and_all_metal_HGX_definitions": True,
              "structural_rib_geometry_is_not_loaded_strength_certification": True}
    write("protected_geometry.json", report)
    STATE["protected_verified"] = True
    return report


def pose_shapes(app, angle, actual=False):
    s, _ = geometry()
    if STATE.get("frozen_review"):
        if actual:
            raise RuntimeError("Use the read-only native BRep review while the user edits the live model")
        frozen = STATE["frozen_review"]
        player = STATE["controller"]
        data = player.load_data()[0]
        arm = player.arm_angle(data, angle)
        carrier = player.rotation(arm, data["arm_pivot_mm"])
        relative = -data["moving_hob_ratio"] * (data["held_left_compound_deg"] - arm)
        poses = {"10": player.rotation(angle, data["cam_pivot_mm"]), "05": carrier,
                 "07": player.compose(carrier, player.rotation(relative, data["moving_hob_axis_mm"])),
                 "09": carrier, "11": carrier}
        result = {}
        for name, shape in frozen["world"].items():
            if name.startswith("REFERENCE_"):
                continue
            prefix = frozen["paths"][name][:2]
            if prefix in poses:
                moved = s.tbm().copy(shape)
                inverse = frozen["root_transforms"][prefix].copy()
                inverse.invert()
                delta = player.compose(poses[prefix], inverse)
                if not s.tbm().transform(moved, delta):
                    raise RuntimeError("The frozen native BRep pose transform failed")
                result[name] = moved
            else:
                result[name] = shape
        return result
    STATE["controller"].drive(app, angle)
    result = {name: s.tbm().copy(body) for name, body in logical_bodies(app).items()
              if not name.startswith("REFERENCE_")}
    if not actual:
        result.update(STATE["candidate"])
        result.update(STATE["hardware"])
    return result


def logical_bodies(app):
    aliases = {new: old for old, new in STATE.get("aliases", {}).items()}
    return {aliases.get(name, name): body for name, body in bodies(app).items()}


def check_motion(app, angles, actual=False):
    require_review_input(app)
    if not STATE.get("protected_verified"):
        raise RuntimeError("Check the retained functional interfaces before motion")
    s, _ = geometry()
    key = "native_motion" if actual else "candidate_motion"
    rows = STATE.setdefault(key, [])
    if STATE.get("frozen_review"):
        moving = {name for name, path in STATE["frozen_review"]["paths"].items()
                  if path[:2] in {"05", "07", "09", "10", "11"}}
    else:
        by = logical_bodies(app)
        moving = {name for name, body in by.items()
                  if body.assemblyContext.fullPathName[:2] in {"05", "07", "09", "10", "11"}}
    press_pair = frozenset((PLATE, "UPPER_RIGHT_REAR_M3_HEATSET_4p6x4"))
    nominal_thread_pairs = {
        frozenset(("SPACER_M3x14_SHCS_0", "SPACER_M3_HEATSET_0")): (20.0, 22.0),
        frozenset(("FRAME_M3x35_into_P01_insert", "FRAME_M3_HEATSET_in_P01")): (26.0, 27.5),
    }
    try:
        for angle in angles:
            shapes = pose_shapes(app, float(angle), actual)
            static = not STATE.get(key + "_static")
            tests, unexpected, nominal_engagements = 0, [], []
            pairs = []
            if static:
                names = tuple(STATE["candidate"])
                for index, name in enumerate(names):
                    for other in names[index + 1:]:
                        pairs.append((name, shapes[name], other, shapes[other], "whole revised fixed prints"))
            for name in STATE["candidate"]:
                for other, shape in shapes.items():
                    if other == name or other in STATE["candidate"] or other in STATE["hardware"]:
                        continue
                    if other in moving or static:
                        pairs.append((name, shapes[name], other, shape, "whole fixed print versus inherited reference"))
            for name in STATE["hardware"]:
                for other, shape in shapes.items():
                    if other == name:
                        continue
                    if static or other in moving:
                        if other in STATE["hardware"] and other < name:
                            continue
                        pairs.append((name, shapes[name], other, shape, "whole replaced reference"))
            for first, shape, second, fixed, scope in pairs:
                tests += 1
                overlap, _ = s.common_volume(shape, fixed)
                if frozenset((first, second)) == press_pair:
                    if not 10.0 <= overlap <= 12.0:
                        unexpected.append({"first": first, "second": second,
                                           "overlap_mm3": overlap, "scope": "bad insert seating"})
                elif frozenset((first, second)) in nominal_thread_pairs:
                    lo, hi = nominal_thread_pairs[frozenset((first, second))]
                    nominal_engagements.append({"first": first, "second": second,
                                                "shank_inside_solid_insert_reference_mm3": overlap})
                    if not lo <= overlap <= hi:
                        unexpected.append({"first": first, "second": second,
                                           "overlap_mm3": overlap, "scope": "nominal thread engagement"})
                elif overlap > 1e-5:
                    if scope == "whole fixed print versus inherited reference":
                        inherited, _ = s.common_volume(STATE["before"][first], fixed)
                        if overlap <= inherited + 1e-5:
                            continue
                    else:
                        inherited = 0.0
                    unexpected.append({"first": first, "second": second,
                                       "overlap_mm3": overlap, "baseline_reference_overlap_mm3": inherited,
                                       "scope": scope})
            bearing_drift = 0.0
            if actual:
                for name in (REAR_BEARING, FORE_BEARING):
                    bearing_drift = max(
                        bearing_drift,
                        max(abs(a - b) for a, b in zip(
                            STATE["baseline_transforms"][name],
                            logical_bodies(app)[name].assemblyContext.transform2.asArray())))
                if bearing_drift > 1e-10:
                    raise RuntimeError("A carriage-mounted cam bearing moved with the cam")
            row = {"cam_deg": float(angle), "pair_tests": tests,
                   "static_pairs": static, "unexpected_interferences": unexpected,
                   "solid_insert_reference_thread_engagements": nominal_engagements,
                   "bearing_frame_drift": bearing_drift if actual else None}
            rows.append(row)
            write(key + ".json", {
                "poses": rows, "baseline_cam_and_gearing_unchanged": True,
                "scope": "Whole revised fixed prints, every replaced reference and every moving assembly. "
                         "For inherited nominal installation contacts, no increase over the intact "
                         "v18 interface is permitted. Revised fixed-print pairs must remain disjoint.",
                "not_continuous_contact_or_force_simulation": True,
                "isolated_native_BRep_snapshot": bool(STATE.get("frozen_review")),
            })
            if unexpected:
                raise RuntimeError("New interference: " + json.dumps(row))
            STATE[key + "_static"] = True
    finally:
        if not STATE.get("frozen_review"):
            STATE["tools"].normalize_edit_pose(app)
    return {"recorded_poses": len(rows), "unexpected_interferences": 0}


def require_reviewed(app):
    require(app)
    if not STATE.get("protected_verified") or not STATE.get("motor_path_verified"):
        raise RuntimeError("The interface and complete motor-insertion reviews are required")
    rows = STATE.get("candidate_motion", [])
    if ({row["cam_deg"] for row in rows} != {i * 2.5 for i in range(71)}
            or any(row["unexpected_interferences"] for row in rows)):
        raise RuntimeError("The complete candidate motion sweep has not passed")
    if STATE.get("inflight"):
        raise RuntimeError("Inspect the unresolved native edit: " + json.dumps(STATE["inflight"]))
    STATE["tools"].normalize_edit_pose(app)


def progress():
    write("native_edit_progress.json", {
        "document": STATE["document"], "print_steps": STATE.get("apply_indices", {}),
        "print_step_counts": {name: len(plan) for name, plan in STATE["plans"].items()},
        "hardware": STATE.get("hardware_applied", []), "inflight": STATE.get("inflight")})


def apply_print(app, name, count=8):
    require_reviewed(app)
    s, _ = geometry()
    indices = STATE.setdefault("apply_indices", {})
    start = indices.get(name, 0)
    plan = STATE["plans"][name]
    expected = STATE["before"][name] if start == 0 else plan[start - 1]["expected"]
    by = logical_bodies(app)
    if STATE["native"].exact_difference(expected, s.tbm().copy(by[name].nativeObject)):
        raise RuntimeError("The owned print changed before its native edit: " + name)
    for index in range(start, min(start + count, len(plan))):
        STATE["inflight"] = {"part": name, "step": index, "label": plan[index]["label"]}
        progress()
        check = STATE["tools"].append_step(app, name, plan[index])
        STATE.setdefault("native_feature_checks", []).append(check)
        indices[name] = index + 1
        STATE.pop("inflight")
        progress()
    if indices.get(name) == len(plan):
        one_solid(logical_bodies(app)[name].nativeObject, name)
    write("native_feature_checks.json", STATE.get("native_feature_checks", []))
    return {"part": name, "completed_steps": indices.get(name), "total_steps": len(plan)}


def apply_hardware(app, count=4):
    require_reviewed(app)
    if any(STATE.get("apply_indices", {}).get(name, 0) != len(plan)
           for name, plan in STATE["plans"].items()):
        raise RuntimeError("Complete all revised prints before replacing metal references")
    s, _ = geometry()
    applied = STATE.setdefault("hardware_applied", [])
    pending = [name for name in STATE["hardware"] if name not in applied]
    for name in pending[:count]:
        STATE["tools"].normalize_edit_pose(app)
        proxy = logical_bodies(app)[name]
        STATE["tools"].require_identity_context(proxy)
        body = proxy.nativeObject
        if STATE["native"].exact_difference(STATE["before"][name], s.tbm().copy(body)):
            raise RuntimeError("The reference changed before replacement: " + name)
        component = body.parentComponent
        component_count = component.bRepBodies.count
        if component.bRepBodies.itemByName(name) is None:
            raise RuntimeError("The reference is missing from its original component: " + name)
        STATE["inflight"] = {"hardware": name}
        progress()
        remove = component.features.removeFeatures.add(body)
        remove.name = "V19 retire prior reference " + name
        feature = component.features.baseFeatures.add()
        feature.name = "V19 updated reference " + name
        if not feature.startEdit():
            raise RuntimeError("Could not start the updated hardware reference")
        try:
            replacement = component.bRepBodies.add(s.tbm().copy(STATE["hardware"][name]), feature)
            replacement.name = name
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish the updated hardware reference")
        if feature.bodies.count != 1 or component.bRepBodies.count != component_count:
            raise RuntimeError("Replacing one reference changed the component's body inventory")
        replacement = feature.bodies.item(0)
        replacement.name = name
        if STATE["appearances"][name] is not None:
            replacement.appearance = STATE["appearances"][name]
        one_solid(replacement, name)
        difference = STATE["native"].exact_difference(
            STATE["hardware"][name], s.tbm().copy(replacement))
        if difference:
            raise RuntimeError("The updated reference differs from its reviewed shape: " + name)
        applied.append(name)
        STATE.pop("inflight")
        progress()
    return {"updated_references": len(applied), "total": len(STATE["hardware"])}


def finalize_labels(app):
    require_reviewed(app)
    if len(STATE.get("hardware_applied", [])) != len(STATE["hardware"]):
        raise RuntimeError("The shortened hardware inventory is incomplete")
    aliases = STATE.setdefault("aliases", {})
    mapping = {
        "M3x18 ISO7380 motor ear 0 (rear entry)": "MOTOR_EAR_M3x10_BUTTON_0",
        "M3x18 ISO7380 motor ear 1 (rear entry)": "MOTOR_EAR_M3x10_BUTTON_1",
        "SPACER_M3x14_SHCS_0": "PLATE_M3x10_BUTTON",
        "UPPER_RIGHT_SHARED_M3x40_FRAME": "UPPER_RIGHT_SHARED_M3x35_FRAME",
        "CLAM_M3x40_FRAME_3": "LOWER_CASE_M3x35_BUTTON",
        "FRAME_M3x35_into_P01_insert": "UPPER_LEFT_CASE_M3x30_BUTTON",
    }
    for old, new in mapping.items():
        if old in aliases:
            continue
        body = logical_bodies(app)[old].nativeObject
        body.name = new
        if body.parentComponent.bRepBodies.count == 1:
            body.parentComponent.name = new.replace("_", " ")
        aliases[old] = new
        write("hardware_labels.json", aliases)
    for name, label in (
            (BACK, "P01 v19 open upper frame - MR128 rear support"),
            (PLATE, "P02 v19 7mm plate - keyed motor entry and measured servo relief"),
            (FRONT, "P03 v19 open receiver - independent MF85 tower and cross-tie")):
        body = logical_bodies(app)[name].nativeObject
        body.parentComponent.name = label
        body.attributes.add("OpenFrameV19", "qualification",
                            "Printed fit,load stiffness and endurance require actual qualification")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    root.attributes.add("OpenFrameV19", "source_archive_sha256", SEED_SHA)
    root.attributes.add("OpenFrameV19", "plate_thickness_mm", "7.0")
    root.attributes.add("OpenFrameV19", "servo_cover_measured_max_mm", "14.75")
    root.attributes.add("OpenFrameV19", "servo_cover_relief_mm", "15.4 / axial depth inherited 1.9 FIT PENDING")
    root.attributes.add("OpenFrameV19", "motor_assembly",
                        "Loose plate:clock-135deg,slide over rear connector/leads,rotate back;"
                        "fit frame,servo and shortened mounting screws afterward")
    root.attributes.add("SparkShiftMotion", "revision",
                        "v19 open frame;v15 progressive lobe and v18 minus90 direct spline retained;FIT PENDING")
    STATE["labels_finalized"] = True
    return {"aliases": aliases, "physical_bodies": len(bodies(app)),
            "both_external_cam_bearings_retained": True}


def expected_shapes():
    expected = dict(STATE.get("accepted_user_shapes", STATE["before"]))
    expected.update(STATE["candidate"])
    expected.update(STATE["hardware"])
    return expected


def physical_inventory(by):
    physical, empty = {}, {}
    for name, body in by.items():
        if body.lumps.count:
            physical[name] = body
            continue
        if body.faces.count or body.edges.count or body.vertices.count or body.volume or body.area:
            raise RuntimeError("A nonphysical body still contains unresolved geometry: " + name)
        empty[name] = {"faces": 0, "edges": 0, "vertices": 0, "lumps": 0,
                       "volume_cm3": 0.0, "area_cm2": 0.0}
    return physical, empty


def verify_model(app, count=200):
    require(app)
    if not STATE.get("labels_finalized"):
        raise RuntimeError("Finish native labels before verifying the physical inventory")
    STATE["tools"].normalize_edit_pose(app)
    s, _ = geometry()
    by, expected = logical_bodies(app), expected_shapes()
    if set(by) != set(expected):
        raise RuntimeError("The final physical-body inventory changed unexpectedly")
    changed = set(STATE["candidate"]) | set(STATE["hardware"])
    rows = STATE.setdefault("model_checks", [])
    if any(row["definition_difference_mm3"] or row["world_frame_max_delta"] > 1e-8 for row in rows):
        raise RuntimeError("Reset the failed model review before resuming; a failed row cannot be skipped")
    names = sorted(expected)
    for name in names[len(rows):len(rows) + count]:
        body = by[name]
        shape = s.tbm().copy(body.nativeObject)
        one_solid(shape, name)
        delta = difference(expected[name], shape, "model " + name)
        matrix_error = max(abs(a - b) for a, b in zip(
            STATE["baseline_transforms"][name], body.assemblyContext.transform2.asArray()))
        rows.append({"body": name, "intended_change": name in changed,
                     "definition_difference_mm3": delta, "world_frame_max_delta": matrix_error})
        write("native_model_guard.json", {"bodies": rows, "expected_count": len(expected)})
        if delta or matrix_error > 1e-8:
            raise RuntimeError("The native solid or datum differs: " + name)
    complete = (len(rows) == len(expected) and all(
        not row["definition_difference_mm3"] and row["world_frame_max_delta"] <= 1e-8 for row in rows))
    STATE["native_model_verified"] = complete
    return {"bodies_verified": len(rows), "expected_count": len(expected), "complete": complete,
            "unchanged_definitions": sum(not row["intended_change"] for row in rows),
            "all_checked_definition_and_frame_differences_zero": True}


def native_assembly_paths(app):
    require_review_input(app)
    if not STATE.get("native_model_verified"):
        raise RuntimeError("Review actual assembly paths only after the native model guard")
    s, m = geometry()
    if STATE.get("frozen_review"):
        shapes = STATE["frozen_review"]["world"]
    else:
        STATE["tools"].normalize_edit_pose(app)
        by = logical_bodies(app)
        shapes = {name: s.tbm().copy(body) for name, body in by.items()}
    stages = [
        ("wider servo enters P02 from rear", SERVO, (-15, -10, -7, -4, -2, -1, -.5, 0), (PLATE,)),
        ("rear bearing enters P01 before actuator plate", REAR_BEARING,
         (-12, -6, -3, -1, -.5, 0), (BACK, CAM)),
        ("7mm P02 closes rear bearing seat", PLATE,
         (-8, -4, -2, -1, -.5, 0), (BACK, CAM, REAR_BEARING)),
        ("servo output engages unchanged direct spline", SPLINE,
         (-8, -4, -2, -1, -.5, 0), (CAM, BACK)),
        ("single upper-right M3x35 enters from front", "UPPER_RIGHT_SHARED_M3x40_FRAME",
         (30, 15, 5, 2, 1, 0), (BACK, PLATE, FRONT, "PRINT_RedLizard_HF_tool_carrier")),
        ("shorter upper-left M3x30 enters from front", "FRAME_M3x35_into_P01_insert",
         (30, 15, 5, 2, 1, 0), (BACK, PLATE, FRONT, SERVO)),
    ]
    rows = []
    for stage, moving, offsets, targets in stages:
        for offset in offsets:
            shape = m.translated(shapes[moving], dy=offset)
            for other in targets:
                volume, _ = s.common_volume(shape, shapes[other])
                row = {"stage": stage, "offset_y_mm": offset, "against": other, "overlap_mm3": volume}
                rows.append(row)
                write("native_assembly_paths.json", {"samples": rows})
                if volume > 1e-5:
                    raise RuntimeError("A stated assembly path is blocked: " + json.dumps(row))
    report = {"sampled_new_interface_pairs": len(rows), "all_clear": True,
              "servo_front_cover_max_width_mm": 14.75, "cover_depth_assumed_mm": 1.9,
              "not_wire_bending_or_physical_press_fit_qualification": True}
    STATE["assembly_verified"] = True
    write("native_assembly_paths_summary.json", report)
    return report


def close_remaining_tail_crease(app):
    require_reviewed(app)
    s, _ = geometry()
    by = logical_bodies(app)
    actual = s.tbm().copy(by[PLATE].nativeObject)
    target = s.tbm().copy(actual)
    s.op(target, s.cyl(18.1, 41.72, -2.0, -1.95, 1.85), "join")
    one_solid(target, "obsolete screw-tail crease closure")
    addition = s.tbm().copy(target)
    s.op(addition, actual, "cut")
    if not addition.lumps.count:
        return {"already_closed": True}
    fixed_tests = []
    moving_tests = []
    added_box = addition.preciseBoundingBox
    for name, body in by.items():
        if name == PLATE:
            continue
        prefix = body.assemblyContext.fullPathName[:2]
        if prefix not in {"05", "07", "09", "10", "11"}:
            overlap, _ = s.common_volume(addition, body)
            if overlap > 1e-7:
                raise RuntimeError("The retired-tail closure interferes with " + name)
            fixed_tests.append(name)
            continue
        box = body.preciseBoundingBox
        if box.minPoint.y >= added_box.maxPoint.y or box.maxPoint.y <= added_box.minPoint.y:
            moving_tests.append({"body": name, "proof": "Y-separation invariant under release rotations"})
            continue
        if prefix != "10":
            raise RuntimeError("A moving non-cam part enters the cleanup axial band")
        band = s.tbm().copy(body)
        s.op(band, s.box(-100, 100, -2.1, -1.8, -100, 100), "common")
        envelope = s.cyl(*CENTRE, -2.1, -1.8, 5.5)
        outside = s.tbm().copy(band)
        s.op(outside, envelope, "cut")
        if outside.lumps.count and outside.volume * 1000 > 1e-7:
            raise RuntimeError("The cam-band full-rotation envelope is incomplete")
        overlap, _ = s.common_volume(addition, envelope)
        if overlap > 1e-7:
            raise RuntimeError("The cleanup enters the complete cam-band rotation envelope")
        moving_tests.append({"body": name, "proof": "exact containment in a disjoint full-rotation cylinder"})
    step = {"operation": "join", "label": "V19 remove final50micron retired screw-tail crescent",
            "tool": addition, "expected": target}
    STATE["inflight"] = {"last_tail_crease": True}
    progress()
    check = STATE["tools"].append_step(app, PLATE, step)
    STATE["candidate"][PLATE] = target
    STATE.pop("inflight")
    progress()
    STATE["native_model_verified"] = False
    STATE["model_checks"] = []
    STATE["native_motion"] = []
    STATE.pop("native_motion_static", None)
    report = {"added_mm3": addition.volume * 1000, "exact_native_difference_mm3": check[
        "exact_candidate_difference_mm3"], "fixed_part_tests": len(fixed_tests),
        "all_moving_parts_continuously_clear_for_this_addition": moving_tests,
        "base_candidate_71_pose_sweep_retained_and_augmented": True,
        "not_a_force_simulation": True}
    write("final_legacy_crease_closure.json", report)
    write("candidate_parts.json", {name: stats(shape) for name, shape in STATE["candidate"].items()})
    return report


def final_metrics(app):
    require_review_input(app)
    s, _ = geometry()
    by = (STATE["frozen_review"]["definitions"] if STATE.get("frozen_review")
          else {name: body.nativeObject for name, body in logical_bodies(app).items()})
    before = sum(STATE["before"][name].volume * 1000 for name in (BACK, PLATE, FRONT))
    after = sum(by[name].volume * 1000 for name in (BACK, PLATE, FRONT))
    p = parameters()
    mx, mz = p["motor_axis_xz_mm"]
    outside_cap = s.tbm().copy(STATE["motor_keyway_tool"])
    s.op(outside_cap, s.cyl(mx, mz, -7, 1, 18.25 + 6.0), "cut")
    cap_error = outside_cap.volume * 1000 if outside_cap.lumps.count else 0.0
    if cap_error > 1e-7:
        raise RuntimeError("The motor notch exceeds the requested six-millimetre maximum")
    plate_box = by[PLATE].preciseBoundingBox
    thickness = (plate_box.maxPoint.y - plate_box.minPoint.y) * 10
    if abs(thickness - 7.0) > 1e-7:
        raise RuntimeError("The motor plate is not seven millimetres overall")
    for name in ("HOBBY_SERVO_ENVELOPE", PLATE, BACK, FRONT):
        one_solid(by[name], name)
    report = {
        "physical_bodies": len(by), "overall_plate_thickness_mm": thickness,
        "notch_max_extension_from_motor_OD_mm": 6.0,
        "notch_max_extension_from_bore_mm": 5.7, "notch_width_mm": 10.4,
        "notch_corner_radius_mm": 4.3, "notch_excess_outside_requested_cap_mm3": cap_error,
        "servo_front_cover_max_measured_width_mm": 14.75, "servo_cover_relief_width_mm": 15.4,
        "servo_cover_nominal_side_clearance_mm": 0.325,
        "servo_cover_axial_depth_1p9mm_is_not_measured": True,
        "receiver_main_front_height_reduction_mm": 62.22059521522819 - HEAD_Z,
        "receiver_main_top_z_mm": HEAD_Z,
        "case_CAD_volume_before_v18_mm3": before, "case_CAD_volume_after_mm3": after,
        "case_CAD_volume_reduction_percent": (before - after) / before * 100,
        "not_a_printed_mass_or_measured_strength_result": True,
        "overall_lever_height_and_gear_tool_datums_not_shortened": True,
        "upper_case_clamps_level_z_mm": 41.72, "one_upper_right_bolt": True,
        "upper_right_heatset_loaded_from_rear": True,
        "both_external_cam_bearings_retained": ["MR128ZZ 8x12x3.5", "MF85ZZ 5x8x2.5"],
        "total_modeled_inserts": 14, "insert_families": {"M3": 12, "M2": 2},
        "printed_roles_changed_from_v18": ["P01", "P02", "P03"],
        "P05_matches_reclocked_v18_and_is_included_for_older_builds": True,
        "fit_loaded_stiffness_and_endurance_require_physical_qualification": True,
    }
    write("revision_measurements.json", report)
    return report


def require_verified(app):
    require_review_input(app)
    if not STATE.get("native_model_verified") or not STATE.get("assembly_verified"):
        raise RuntimeError("Finish the exact model and assembly-path checks")
    if not STATE.get("motor_path_verified") or not STATE.get("protected_verified"):
        raise RuntimeError("The keyed motor path or functional-interface review is incomplete")
    rows = STATE.get("candidate_motion" if STATE.get("frozen_review") else "native_motion", [])
    if ({row["cam_deg"] for row in rows} != {i * 2.5 for i in range(71)}
            or any(row["unexpected_interferences"] for row in rows)):
        raise RuntimeError("The complete actual native small-notch motion sweep is incomplete")


def export_archive(app):
    require_verified(app)
    STATE["tools"].normalize_edit_pose(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    root.attributes.add("OpenFrameV19", "keyway_max_extension_from_motor_OD_mm", "6.0")
    root.attributes.add("OpenFrameV19", "keyway_max_extension_from_bore_mm", "5.7")
    root.attributes.add("OpenFrameV19", "keyway_width_mm", "10.4")
    root.attributes.add("OpenFrameV19", "wire_assembly",
                        "Feed flexible leads separately;straight rigid wire-tail passage not claimed")
    keep = {name for name in bodies(app) if not name.startswith("REFERENCE_")}
    STATE["tools"].show(app, keep)
    (PAYLOAD / "cad").mkdir(parents=True, exist_ok=True)
    path = PAYLOAD / "cad" / "SparkShift_v19_OpenFrame_7mmPlate_SmallNotch_WIP.f3d"
    if path.exists():
        raise RuntimeError("The final native archive already exists")
    app.activeDocument.name = "SparkShift v19 - open frame,7mm plate,small notch - WIP"
    if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("The complete native assembly export failed")
    by = logical_bodies(app)
    report = {
        "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size, "physical_bodies": len(by),
        "source_v18_sha256": SEED_SHA,
        "live_cleanup_input_sha256": json.loads((OUT / "final_live_cleanup_capture.json").read_text())["sha256"],
        "authoring_document": STATE["document"],
        "closed_context_matrices": {name: list(body.assemblyContext.transform2.asArray())
                                    for name, body in by.items()},
        "native_geometry_definitions_expected": True, "physical_strength_fit_not_certified": True,
        "no_GitHub_publication": True,
    }
    STATE["archive"] = report
    write("native_archive_receipt.json", report)
    return {key: value for key, value in report.items() if key != "closed_context_matrices"}


def create_mesh_export(app):
    require_verified(app)
    if not STATE.get("archive") or STATE.get("mesh_document"):
        raise RuntimeError("Export the checked native archive before creating the print-export document")
    s, _ = geometry()
    support = load_file("sparkshift_v19_print_bed", BASE / "sparkshift_surface_cleanup.py")
    shapes = []
    by = logical_bodies(app)
    for part, (name, filename, direction) in CHANGED_PRINTS.items():
        body = by[name].nativeObject
        orientation = support.bed_face(body, direction)
        shape = s.tbm().copy(body)
        build = adsk.core.Vector3D.create(*orientation["build_direction"])
        target = adsk.core.Vector3D.create(0, 0, 1)
        rotation = adsk.core.Matrix3D.create()
        angle = build.angleTo(target)
        if angle > 1e-10:
            axis = build.crossProduct(target)
            if axis.length < 1e-10:
                axis = adsk.core.Vector3D.create(1, 0, 0)
            axis.normalize()
            rotation.setToRotation(angle, axis, adsk.core.Point3D.create(0, 0, 0))
            if not s.tbm().transform(shape, rotation):
                raise RuntimeError("The print-bed rotation failed")
        box = shape.preciseBoundingBox
        translation = adsk.core.Matrix3D.create()
        translation.translation = adsk.core.Vector3D.create(
            -box.minPoint.x, -box.minPoint.y, -box.minPoint.z)
        if not s.tbm().transform(shape, translation):
            raise RuntimeError("The print-bed translation failed")
        one_solid(shape, part)
        shapes.append((part, name, filename, shape, orientation,
                       list(rotation.asArray()), list(translation.asArray()), body.volume * 1000))
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.activate()
    document.name = "EXPORT ONLY - v19 four small-notch print meshes"
    design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
    STATE["mesh_document"] = document.creationId
    STATE["mesh_source_document"] = source.creationId
    STATE["mesh_shapes"] = shapes
    STATE["mesh_exports"] = {}
    for part, name, filename, shape, orientation, rotation, translation, volume in shapes:
        feature = design.rootComponent.features.baseFeatures.add()
        feature.name = "V19 raw mesh source " + part
        if not feature.startEdit():
            raise RuntimeError("Could not start the export-only print solid")
        try:
            body = design.rootComponent.bRepBodies.add(shape, feature)
            body.name = part
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish the export-only print solid")
        feature.bodies.item(0).name = part
    (PAYLOAD / "stl").mkdir(parents=True, exist_ok=True)
    return {"export_document": document.creationId, "print_roles": list(CHANGED_PRINTS)}


def export_mesh_batch(app, count=4):
    if app.activeDocument.creationId != STATE.get("mesh_document"):
        raise RuntimeError("Activate only the owned raw print-export document")
    design = adsk.fusion.Design.cast(app.activeProduct)
    start = len(STATE["mesh_exports"])
    for part, name, filename, shape, orientation, rotation, translation, volume in (
            STATE["mesh_shapes"][start:start + count]):
        path = PAYLOAD / "stl" / (filename + ".stl")
        if path.exists():
            raise RuntimeError("A raw native print mesh would be overwritten")
        body = design.rootComponent.bRepBodies.itemByName(part)
        options = design.exportManager.createSTLExportOptions(body, str(path))
        options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        options.isBinaryFormat = True
        if part == "P05":
            options.surfaceDeviation = .0003
            options.normalDeviation = 4.
        if not design.exportManager.execute(options) or path.stat().st_size <= 84:
            raise RuntimeError("The raw native mesh export failed: " + part)
        STATE["mesh_exports"][part] = {
            "body": name, "path": str(path), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "native_volume_mm3": volume, "bed_face": orientation,
            "rotation": rotation, "translation": translation,
            "native_archive_sha256": STATE["archive"]["sha256"], "raw_native_no_mesh_repair": True,
        }
        write("mesh_export_receipt.json", STATE["mesh_exports"])
    return {"exported": len(STATE["mesh_exports"]), "total": 4}


def close_mesh_export(app):
    if len(STATE.get("mesh_exports", {})) != 4:
        raise RuntimeError("The four revised print roles have not all been exported")
    source = next(doc for doc in app.documents if doc.creationId == STATE["mesh_source_document"])
    owned = next(doc for doc in app.documents if doc.creationId == STATE["mesh_document"])
    source.activate()
    if not owned.close(False):
        raise RuntimeError("Could not close the owned export-only document")
    STATE["closed_mesh_document"] = STATE.pop("mesh_document")
    return {"temporary_export_document_closed": True}


def begin_archive_readback(app):
    require_verified(app)
    if STATE.get("readback_document"):
        raise RuntimeError("The independent native archive readback already exists")
    path = Path(STATE["archive"]["path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != STATE["archive"]["sha256"]:
        raise RuntimeError("The native archive hash changed before readback")
    doc = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(str(path)))
    if doc is None:
        raise RuntimeError("Could not independently reopen the final native archive")
    doc.activate()
    doc.name = "SparkShift v19 - verified small-notch WIP"
    STATE["readback_document"] = doc.creationId
    STATE["readback_checks"] = []
    return {"readback_document": doc.creationId, "archive_sha256": STATE["archive"]["sha256"]}


def verify_archive_readback(app, count=200):
    if app.activeDocument.creationId != STATE.get("readback_document"):
        raise RuntimeError("Activate only the independent archive readback")
    by, expected = logical_bodies(app), expected_shapes()
    if set(by) != set(expected) or len(by) != 139:
        raise RuntimeError("The saved physical-body inventory differs")
    rows = STATE["readback_checks"]
    if any(row["exact_definition_difference_mm3"] or row["closed_world_matrix_max_delta"] > 1e-8
           for row in rows):
        raise RuntimeError("Reset the failed archive review before resuming; a failed row cannot be skipped")
    names = sorted(expected)
    for name in names[len(rows):len(rows) + count]:
        body = by[name].nativeObject
        one_solid(body, name)
        delta = difference(expected[name], body, "archive " + name)
        pose_error = max(abs(a - b) for a, b in zip(
            STATE["archive"]["closed_context_matrices"][name],
            by[name].assemblyContext.transform2.asArray()))
        rows.append({"body": name, "exact_definition_difference_mm3": delta,
                     "closed_world_matrix_max_delta": pose_error})
        write("native_archive_readback.json", {
            "archive_sha256": STATE["archive"]["sha256"], "bodies": rows,
            "expected_count": 139, "all_recorded_definitions_equal": not any(
                row["exact_definition_difference_mm3"] for row in rows)})
        if delta or pose_error > 1e-8:
            raise RuntimeError("The saved native geometry or pose differs: " + name)
    STATE["readback_verified"] = len(rows) == 139 and all(
        not row["exact_definition_difference_mm3"] and row["closed_world_matrix_max_delta"] <= 1e-8
        for row in rows)
    return {"verified_bodies": len(rows), "complete": STATE["readback_verified"]}


def finish_receiver_arc_cleanup(app):
    require(app)
    helper = STATE["arc_helper"]
    body = logical_bodies(app)[FRONT].nativeObject
    component = body.parentComponent
    roots = adsk.core.ObjectCollection.create()
    for edge in body.edges:
        box = edge.boundingBox
        if (abs(box.minPoint.z * 10 - HEAD_Z) > 1e-5
                or abs(box.maxPoint.z * 10 - HEAD_Z) > 1e-5):
            continue
        cylinders = [face.geometry for face in edge.faces
                     if isinstance(face.geometry, adsk.core.Cylinder)
                     and abs(face.geometry.radius * 10 - 6.3) < 1e-6
                     and math.hypot(face.geometry.origin.x * 10 - CENTRE[0],
                                    face.geometry.origin.z * 10 - CENTRE[1]) < 1e-6]
        if not cylinders:
            continue
        x = (box.minPoint.x + box.maxPoint.x) * 5
        if ((x < CENTRE[0] and box.minPoint.y * 10 >= 13.4)
                or (x > CENTRE[0] and box.minPoint.y * 10 >= 11.39)):
            roots.add(edge)
    if roots.count != 2:
        raise RuntimeError("Could not uniquely identify the two outer support root edges")
    inp = component.features.filletFeatures.createInput()
    inp.edgeSetInputs.addConstantRadiusEdgeSet(
        roots, adsk.core.ValueInput.createByReal(.2), False)
    fillet = component.features.filletFeatures.add(inp)
    if fillet.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        message = fillet.errorOrWarningMessage
        if fillet.isValid:
            fillet.deleteMe()
        raise RuntimeError("The analytic support-root fillet failed: " + message)
    fillet.name = "V19 two true tangent2mm cam-support roots"
    rows = [{"operation": fillet.name, "roots": 2, "radius_mm": 2.0,
             "left_root_fore_only_to_preserve_follower_clearance": True}]
    for x, old_radius, label in (
            (2.5, 3.201026193374863, "V19 right throat tangent analytic3p2 arc"),
            (-2.5, 3.201020292652993, "V19 left throat tangent analytic3p2 arc")):
        result = helper.replace_cylinder_patch(
            app, FRONT, (x, 44.67), 3.2, [old_radius], 17.68, 31.5, label)
        rows.append(result)
        write("receiver_arc_cleanup_results.json", {"operations": rows})
        if result["status"] != "replaced-pending-clearance-review":
            raise RuntimeError("The throat arc replacement failed: " + json.dumps(result))
    s, _ = geometry()
    for name in (BACK, PLATE, FRONT):
        STATE["candidate"][name] = s.tbm().copy(logical_bodies(app)[name].nativeObject)
        one_solid(STATE["candidate"][name], name)
    return rows


def capture_frozen_packet(app, ui):
    require(app)
    if STATE.get("frozen_review"):
        raise RuntimeError("The immutable review packet already exists")
    if ui.activeCommand == "FreeOrbitCommand":
        ui.terminateActiveCommand()
    if ui.activeCommand != "SelectCommand":
        raise RuntimeError("Finish the active native edit before capturing the review snapshot")
    STATE["tools"].normalize_edit_pose(app)
    source = app.activeDocument
    design = adsk.fusion.Design.cast(app.activeProduct)
    by, empty = physical_inventory(logical_bodies(app))
    if len(by) != 139 or set(by) != set(expected_shapes()):
        raise RuntimeError("The frozen source has an unexpected physical-body inventory")
    body_names = {body.name for name, body in by.items() if not name.startswith("REFERENCE_")}
    STATE["tools"].show(app, body_names)
    root = design.rootComponent
    root.attributes.add("OpenFrameV19", "keyway_max_extension_from_motor_OD_mm", "6.0")
    root.attributes.add("OpenFrameV19", "keyway_max_extension_from_bore_mm", "5.7")
    root.attributes.add("OpenFrameV19", "keyway_width_mm", "10.4")
    root.attributes.add("OpenFrameV19", "wire_assembly",
                        "Feed flexible leads separately;straight rigid wire-tail passage not claimed")
    path = OUT / "cad" / ("Arc_cleaned_frozen_input_" + time.strftime("%Y%m%d_%H%M%S") + ".f3d")
    if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("Could not capture the complete current native revision")
    s, _ = geometry()
    frozen = {
        "definitions": {name: s.tbm().copy(body.nativeObject) for name, body in by.items()},
        "world": {name: s.tbm().copy(body) for name, body in by.items()},
        "paths": {name: body.assemblyContext.fullPathName for name, body in by.items()},
        "matrices": {name: list(body.assemblyContext.transform2.asArray()) for name, body in by.items()},
        "root_transforms": {o.name[:2]: o.transform2.copy()
                            for o in design.rootComponent.occurrences if o.name[:2].isdigit()},
        "archive_path": str(path), "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "retained_empty_history_records": empty,
    }
    STATE["capture_inflight"] = {"frozen": frozen, "source_document": source.creationId,
                                 "stage": "native archive and immutable shapes captured"}
    STATE["controller"].validate(design)
    for name in (BACK, PLATE, FRONT):
        STATE["candidate"][name] = s.tbm().copy(frozen["definitions"][name])
    support = load_file("sparkshift_v19_frozen_bed", BASE / "sparkshift_surface_cleanup.py")
    print_shapes = []
    for part, (name, filename, direction) in CHANGED_PRINTS.items():
        native_body = by[name].nativeObject
        orientation = support.bed_face(native_body, direction)
        shape = s.tbm().copy(frozen["definitions"][name])
        build = adsk.core.Vector3D.create(*orientation["build_direction"])
        target = adsk.core.Vector3D.create(0, 0, 1)
        rotation = adsk.core.Matrix3D.create()
        angle = build.angleTo(target)
        if angle > 1e-10:
            axis = build.crossProduct(target)
            if axis.length < 1e-10:
                axis = adsk.core.Vector3D.create(1, 0, 0)
            axis.normalize()
            rotation.setToRotation(angle, axis, adsk.core.Point3D.create(0, 0, 0))
            if not s.tbm().transform(shape, rotation):
                raise RuntimeError("The immutable print rotation failed")
        box = shape.preciseBoundingBox
        translation = adsk.core.Matrix3D.create()
        translation.translation = adsk.core.Vector3D.create(-box.minPoint.x, -box.minPoint.y, -box.minPoint.z)
        if not s.tbm().transform(shape, translation):
            raise RuntimeError("The immutable print translation failed")
        one_solid(shape, part)
        print_shapes.append((part, name, filename, shape, orientation,
                             list(rotation.asArray()), list(translation.asArray()),
                             frozen["definitions"][name].volume * 1000))
    STATE["capture_inflight"]["print_shapes"] = print_shapes
    exposed = {body.name for name, body in by.items()
               if not body.assemblyContext.fullPathName.startswith("12 ")
               and not name.startswith("REFERENCE_")}
    images = [
        STATE["tools"].image(app, "Final_v19_receiver_arcs", exposed, (0, 210, 46), (0, 10, 46), 56),
        STATE["tools"].image(app, "Final_v19_small_keyway", {PLATE}, (0, -210, 24), (0, -3, 24), 90),
        STATE["tools"].image(app, "Final_v19_assembled", body_names, (85, 180, 25), (0, 12, -4), 175),
        STATE["tools"].image(app, "Final_v19_opposite_bearing_support",
                             {FRONT, CAM, FORE_BEARING, REAR_BEARING, BACK},
                             (-65, 150, 82), (8, 12, 48), 42),
    ]
    STATE["tools"].show(app, body_names)
    STATE["capture_inflight"].update(images=images, stage="immutable print shapes and images captured")
    export_doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    export_doc.activate()
    export_doc.name = "TEMP EXPORT - immutable v19 print bodies"
    exporter = adsk.fusion.Design.cast(export_doc.products.itemByProductType("DesignProductType"))
    for part, name, filename, shape, orientation, rotation, translation, volume in print_shapes:
        feature = exporter.rootComponent.features.baseFeatures.add()
        if not feature.startEdit():
            raise RuntimeError("Could not create the immutable print-export body")
        try:
            body = exporter.rootComponent.bRepBodies.add(shape, feature)
            body.name = part
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish the immutable print-export body")
        feature.bodies.item(0).name = part
    source.activate()
    (PAYLOAD / "stl").mkdir(parents=True, exist_ok=True)
    exports = {}
    STATE["capture_inflight"]["exports"] = exports
    try:
        for part, name, filename, shape, orientation, rotation, translation, volume in print_shapes:
            mesh_path = PAYLOAD / "stl" / (filename + ".stl")
            if mesh_path.exists():
                raise RuntimeError("An existing immutable raw mesh would be overwritten")
            options = exporter.exportManager.createSTLExportOptions(
                exporter.rootComponent.bRepBodies.itemByName(part), str(mesh_path))
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            options.isBinaryFormat = True
            if part == "P05":
                options.surfaceDeviation = .0003
                options.normalDeviation = 4.
            if not exporter.exportManager.execute(options) or mesh_path.stat().st_size <= 84:
                raise RuntimeError("The immutable native print export failed: " + part)
            exports[part] = {
                "body": name, "path": str(mesh_path), "bytes": mesh_path.stat().st_size,
                "sha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
                "native_volume_mm3": volume, "bed_face": orientation,
                "rotation": rotation, "translation": translation,
                "native_archive_sha256": frozen["archive_sha256"], "raw_native_no_mesh_repair": True}
            write("mesh_export_receipt.json", exports)
    finally:
        source.activate()
        if not export_doc.close(False):
            raise RuntimeError("Could not close the owned immutable print-export document")
    readback = app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(path)))
    if readback is None:
        raise RuntimeError("Could not independently read the immutable native archive")
    readback.activate()
    read_design = adsk.fusion.Design.cast(readback.products.itemByProductType("DesignProductType"))
    read_by = {body.name: body for occurrence in read_design.rootComponent.allOccurrences
               for body in occurrence.bRepBodies}
    aliases = {new: old for old, new in STATE.get("aliases", {}).items()}
    read_by = {aliases.get(name, name): body for name, body in read_by.items()}
    read_by, read_empty = physical_inventory(read_by)
    if empty != read_empty:
        raise RuntimeError("The preserved empty history records differ after archive readback")
    STATE["controller"].validate(read_design)
    read_definitions = {name: s.tbm().copy(body.nativeObject) for name, body in read_by.items()}
    read_matrices = {name: list(body.assemblyContext.transform2.asArray()) for name, body in read_by.items()}
    source.activate()
    if not readback.close(False):
        raise RuntimeError("Could not close the owned independent readback document")
    frozen.update(readback_definitions=read_definitions, readback_matrices=read_matrices)
    STATE["frozen_review"] = frozen
    STATE["mesh_exports"] = exports
    STATE["candidate_motion"] = []
    STATE.pop("candidate_motion_static", None)
    STATE["native_model_verified"] = False
    STATE["protected_verified"] = False
    STATE["assembly_verified"] = False
    STATE["model_checks"] = []
    STATE["readback_checks"] = []
    STATE.pop("capture_inflight")
    report = {
        "native_input": str(path), "native_input_sha256": frozen["archive_sha256"],
        "body_count": len(frozen["definitions"]), "independent_readback_count": len(read_definitions),
        "preserved_empty_nonphysical_history_records": empty,
        "raw_mesh_count": len(exports), "images": images, "source_document_left_open": source.creationId,
        "temporary_export_and_readback_documents_closed": True,
        "subsequent_review_uses_immutable_BRep_copies_not_live_user_geometry": True,
        "review_complete": False,
    }
    write("frozen_packet_receipt.json", report)
    return report


def verify_frozen_model():
    frozen = STATE["frozen_review"]
    expected = expected_shapes()
    if set(frozen["definitions"]) != set(expected) or set(frozen["readback_definitions"]) != set(expected):
        raise RuntimeError("The native snapshot or readback inventory differs")
    rows = []
    for name in sorted(expected):
        shape = frozen["definitions"][name]
        one_solid(shape, name)
        delta = difference(expected[name], shape, "frozen model " + name)
        reopened_delta = difference(shape, frozen["readback_definitions"][name], "frozen archive " + name)
        pose_error = max(abs(a - b) for a, b in zip(
            frozen["matrices"][name], frozen["readback_matrices"][name]))
        baseline_pose_error = max(abs(a - b) for a, b in zip(
            STATE["baseline_transforms"][name], frozen["matrices"][name]))
        row = {"body": name, "intended_definition_difference_mm3": delta,
               "independent_readback_difference_mm3": reopened_delta,
               "readback_pose_error": pose_error, "baseline_pose_error": baseline_pose_error}
        rows.append(row)
        write("frozen_native_model_guard.json", {
            "input_sha256": frozen["archive_sha256"], "bodies": rows, "complete": False})
        if delta or reopened_delta or pose_error > 1e-8 or baseline_pose_error > 1e-8:
            raise RuntimeError("The immutable native shape or pose differs: " + name)
    STATE["native_model_verified"] = True
    STATE["readback_verified"] = True
    write("frozen_native_model_guard.json", {
        "input_sha256": frozen["archive_sha256"], "bodies": rows, "complete": True})
    return {"native_bodies": len(rows), "independent_readback_bodies": len(rows),
            "all_exact_definition_differences_zero": True, "all_frames_unchanged": True}


def verify_receiver_arc_joins():
    body = STATE["frozen_review"]["definitions"][FRONT]
    boss = []
    retired = []
    roots = []
    throat = {}
    leftover_steps = []
    for face in body.faces:
        g = face.geometry
        box = face.boundingBox
        if isinstance(g, adsk.core.Cylinder) and abs(g.axis.y) > .999999:
            x, z, radius = g.origin.x * 10, g.origin.z * 10, g.radius * 10
            if math.hypot(x - CENTRE[0], z - CENTRE[1]) < 1e-6:
                if abs(radius - 6.3) < 1e-6:
                    boss.append(face)
                if abs(radius - 6.2) < 1e-6:
                    retired.append(face)
            if abs(radius - 2.0) < 1e-6 and abs(z - 50.7) < 1e-6:
                error = abs(math.hypot(x - CENTRE[0], z - CENTRE[1]) - 8.3)
                roots.append({"centre_xz_mm": [x, z], "circle_tangency_error_mm": error,
                              "flat_root_tangency_error_mm": abs(z - radius - HEAD_Z)})
            for sign in (-1, 1):
                if math.hypot(x - sign * 2.5, z - 44.67) < 1e-6 and abs(radius - 3.2) < 1e-6:
                    throat[sign] = {"centre_xz_mm": [x, z], "radius_mm": radius,
                                    "sidewall_tangency_error_mm": abs(abs(x) + radius - 5.7)}
        if isinstance(g, adsk.core.Plane) and abs(g.normal.z) > .9:
            if (box.minPoint.z * 10 > 44.60 and box.maxPoint.z * 10 < 44.75
                    and 5.55 < abs((box.minPoint.x + box.maxPoint.x) * 5) < 5.80):
                leftover_steps.append({"area_mm2": face.area * 100, "bounds_mm": bounds(face)})
    if len(boss) != 1 or retired or len(roots) != 2 or set(throat) != {-1, 1} or leftover_steps:
        write("receiver_arc_join_validation.json", {
            "outer_R6p3_faces": len(boss), "retired_R6p2_faces": len(retired),
            "roots": roots, "throat": throat, "leftover_step_faces": leftover_steps, "passed": False})
        raise RuntimeError("The four marked receiver arc joins are not fully normalized")
    if any(row["circle_tangency_error_mm"] > 1e-6 or row["flat_root_tangency_error_mm"] > 1e-6
           for row in roots) or any(row["sidewall_tangency_error_mm"] > 1e-6
                                    for row in throat.values()):
        raise RuntimeError("The repaired circle joins are not tangent to their adjoining surfaces")
    report = {"outer_support_radius_mm": 6.3, "single_coaxial_outer_cylinder": True,
              "retired_6p2mm_step_removed": True, "two_2mm_tangent_roots": roots,
              "throat_tangent_arcs": throat, "tiny_upper_throat_step_faces": 0,
              "bearing_seat_and_cam_profile_reviewed_separately": True, "passed": True}
    write("receiver_arc_join_validation.json", report)
    return report
