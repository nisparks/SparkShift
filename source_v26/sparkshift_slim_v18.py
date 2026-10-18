"""Source-preserving print-feedback study; fit and loaded strength remain WIP."""

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
OUT = BASE / "sparkshift_slim_v18"
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
RETIRED = (
    "CLAM_M3x25_FRAME_0", "CLAM_M3_FRAME_INSERT_0",
    "SPACER_M3x14_SHCS_1", "SPACER_M3_HEATSET_1",
)
CHANGED_PRINTS = {
    "P01": (BACK, "P01_Back_case_slim_v18", (0, 1, 0)),
    "P02": (PLATE, "P02_Motor_servo_plate_slim_v18", (0, -1, 0)),
    "P03": (FRONT, "P03_Front_case_slim_v18", (0, -1, 0)),
    "P05": (CAM, "P05_Reclocked_cam_v18", (0, 1, 0)),
}


def load_file(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def write(name, report):
    (OUT / name).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def bodies(app):
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    rows = [body for occurrence in root.allOccurrences for body in occurrence.bRepBodies]
    if len(rows) != len({body.name for body in rows}):
        raise RuntimeError("Body names are not unique in the active assembly")
    return {body.name: body for body in rows}


def require(app):
    if not STATE or app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate only the owned v18 print-feedback study")


def native():
    return STATE["native"]


def geometry():
    return native().load("pancake_paths_study"), native().load("sparkshift_ahg_min")


def bounds(shape):
    box = (shape.preciseBoundingBox if isinstance(shape, adsk.fusion.BRepBody)
           else shape.boundingBox)
    return [[round(value * 10, 6) for value in point.asArray()]
            for point in (box.minPoint, box.maxPoint)]


def stats(shape):
    return {"volume_mm3": shape.volume * 1000, "bounds_mm": bounds(shape),
            "solid": shape.isSolid, "lumps": shape.lumps.count,
            "faces": shape.faces.count}


def assert_solid(shape, label):
    if (not shape.isSolid or shape.lumps.count != 1
            or not math.isfinite(shape.volume) or shape.volume <= 0):
        report = {"label": label, "solid": shape.isSolid,
                  "lumps": [{"volume_mm3": lump.volume * 1000,
                             "bounds_mm": bounds(lump)} for lump in shape.lumps]}
        STATE["failed_candidate"] = adsk.fusion.TemporaryBRepManager.get().copy(shape)
        write("candidate_failure.json", report)
        raise RuntimeError("The candidate is not one positive solid: "
                           + label + " / " + json.dumps(report["lumps"]))


def capture(app, ui, expected_source):
    if STATE:
        raise RuntimeError("The v18 source has already been captured")
    if app.activeDocument.creationId != expected_source:
        raise RuntimeError("The user source document changed before capture")
    if ui.activeCommand != "SelectCommand":
        raise RuntimeError("Finish the active CAD command before creating the study")
    source = app.activeDocument
    design = adsk.fusion.Design.cast(app.activeProduct)
    source_bodies = bodies(app)
    required = (BACK, PLATE, FRONT, CAM, SERVO, SPLINE, REAR_BEARING, FORE_BEARING)
    if len(source_bodies) != 143 or not all(name in source_bodies for name in required):
        raise RuntimeError("The expected dual-bearing source inventory changed")
    prior = sys.modules.get("sparkshift_direct_mount_v16")
    exact_helper = prior.STATE.get("exact_readback_helper") if prior else None
    if exact_helper is None:
        raise RuntimeError("The existing native geometry comparison helper is unavailable")
    manager = adsk.fusion.TemporaryBRepManager.get()
    source_shapes = {name: manager.copy(body.nativeObject or body)
                     for name, body in source_bodies.items()}
    OUT.mkdir(exist_ok=True)
    (OUT / "cad").mkdir(exist_ok=True)
    (OUT / "images").mkdir(exist_ok=True)
    archive = OUT / "cad" / ("Input_before_slimming_" + time.strftime("%Y%m%d_%H%M%S") + ".f3d")
    if not design.exportManager.execute(
            design.exportManager.createFusionArchiveExportOptions(str(archive))):
        raise RuntimeError("Could not preserve the current user assembly")
    receipt = {
        "source_document": source.creationId, "source_name": source.name,
        "source_archive": str(archive), "source_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "source_bytes": archive.stat().st_size, "source_body_count": len(source_bodies),
        "source_geometry_and_visibility_not_modified": True,
        "source_transforms": {name: list(body.assemblyContext.transform2.asArray())
                              for name, body in source_bodies.items()},
    }
    write("source_capture.json", receipt)
    document = app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(archive)))
    if document is None or document == source:
        raise RuntimeError("Could not create an isolated print-feedback revision")
    document.activate()
    document.name = "SparkShift v18 - slim servo and captured inserts - WIP"
    adapter = load_file("sparkshift_v18_native", BASE / "sparkshift_opening_v14.py")
    player = load_file(
        "sparkshift_v18_playback",
        BASE / "sparkshift_dual_cam_bearings_v17" / "playback"
        / "SparkShiftCamPlayback" / "SparkShiftCamPlayback.py")
    STATE.update(document=document.creationId, source_document=source.creationId,
                 source_shapes=source_shapes, exact_readback_helper=exact_helper,
                 native=adapter, controller=player, applied=[])
    adapter.STATE = STATE
    adapter.OUT = OUT
    player.drive(app, 0.0)
    current = bodies(app)
    STATE["before"] = {name: manager.copy(body.nativeObject or body)
                       for name, body in current.items()}
    STATE["before_world"] = {name: manager.copy(body) for name, body in current.items()}
    STATE["appearances"] = {name: body.appearance for name, body in current.items()}
    STATE["source_lights"] = {name: body.isLightBulbOn for name, body in current.items()}
    receipt["owned_document"] = document.creationId
    receipt["owned_baseline_closed_pose_only"] = True
    receipt["baseline_parts"] = {name: stats(shape) for name, shape in STATE["before"].items()
                                 if name.startswith("PRINT_")}
    write("source_capture.json", receipt)
    return {key: value for key, value in receipt.items()
            if key not in ("source_transforms", "baseline_parts")}


def inspect_loadpaths(app):
    require(app)
    current = bodies(app)
    result = {"parts": {}, "sidewall_material_y_intervals_mm": [],
              "note": "Geometry/location evidence, not FEA or loaded-strength qualification."}
    inside = (adsk.fusion.PointContainment.PointInsidePointContainment,
              adsk.fusion.PointContainment.PointOnPointContainment)
    for name in (BACK, FRONT, PLATE):
        shape = current[name].nativeObject
        planes = []
        for index, face in enumerate(shape.faces):
            if not isinstance(face.geometry, adsk.core.Plane):
                continue
            box = face.boundingBox
            if box.maxPoint.z * 10 < 49:
                continue
            if min(abs(box.minPoint.x * 10), abs(box.maxPoint.x * 10)) < 18:
                continue
            planes.append({"face": index, "area_mm2": face.area * 100,
                           "bounds_mm": bounds(face),
                           "normal": list(face.geometry.normal.asArray())})
        result["parts"][name] = {"stats": stats(shape), "upper_outer_planes": planes}
        if name == PLATE:
            continue
        for x in (-21.5, 21.5):
            for z in (-12.0, 0.0, 20.0, 35.0, 46.0, 54.0, 58.0, 61.0):
                intervals = []
                start = None
                previous = None
                for step in range(140):
                    y = -1.25 + step * 0.25
                    point = adsk.core.Point3D.create(x / 10, y / 10, z / 10)
                    material = shape.pointContainment(point) in inside
                    if material and start is None:
                        start = y
                    elif not material and start is not None:
                        intervals.append([start, previous])
                        start = None
                    previous = y
                if start is not None:
                    intervals.append([start, previous])
                result["sidewall_material_y_intervals_mm"].append(
                    {"body": name, "x_mm": x, "z_mm": z, "intervals_mm": intervals,
                     "sample_step_mm": 0.25})
    s, m = geometry()
    servo = m.rotated(STATE["before_world"][SERVO], CENTRE, -90.0)
    contacts = []
    excluded = {SERVO, SPLINE, CAM}
    for name, shape in STATE["before_world"].items():
        if name in excluded or name.startswith("MG90S_M2"):
            continue
        overlap, _ = s.common_volume(servo, shape)
        if overlap > 1e-5:
            contacts.append({"body": name, "overlap_mm3": overlap})
    result["servo_minus_90_trial"] = {"bounds_mm": bounds(servo), "existing_geometry_hits": contacts,
                                      "working_cam_axis_not_moved": True}
    write("loadpath_inspection.json", result)
    return {"parts": {name: row["stats"] for name, row in result["parts"].items()},
            "servo_minus_90_trial": result["servo_minus_90_trial"],
            "full_report": str(OUT / "loadpath_inspection.json")}


def show(app, names):
    require(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    components = {root.entityToken: root}
    for occurrence in root.allOccurrences:
        occurrence.isLightBulbOn = bool(
            occurrence.component.bRepBodies.count or occurrence.childOccurrences.count)
        components[occurrence.component.entityToken] = occurrence.component
    for component in components.values():
        for plane in component.constructionPlanes:
            plane.isLightBulbOn = False
        for axis in component.constructionAxes:
            axis.isLightBulbOn = False
        for point in component.constructionPoints:
            point.isLightBulbOn = False
    for name, body in bodies(app).items():
        body.isLightBulbOn = name in names
    root.isJointsFolderLightBulbOn = False
    root.isJointOriginsFolderLightBulbOn = False
    root.isSketchFolderLightBulbOn = False


def image(app, slug, names, eye_mm, target_mm, extent_mm, size=(1500, 1200)):
    show(app, names)
    camera = adsk.core.Camera.create()
    camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    camera.isFitView = False
    camera.isSmoothTransition = False
    camera.eye = adsk.core.Point3D.create(*(v / 10 for v in eye_mm))
    camera.target = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
    camera.viewExtents = extent_mm / 10
    app.activeViewport.camera = camera
    app.activeViewport.refresh()
    path = OUT / "images" / (slug + ".png")
    if not app.activeViewport.saveAsImageFile(str(path), *size):
        raise RuntimeError("The native inspection image was not saved: " + slug)
    return str(path)


def capture_inspection(app):
    require(app)
    top_names = {BACK, FRONT, PLATE, CAM, FORE_BEARING, REAR_BEARING, SERVO, SPLINE,
                 "CLAM_M3x25_FRAME_0", "CLAM_M3x25_FRAME_1", "FRAME_M3x35_into_P01_insert"}
    images = [
        image(app, "Before_upper_case_corner", top_names, (-95, 125, 98), (0, 13, 49), 65),
        image(app, "Before_back_case_sidewall", {BACK}, (100, 150, 70), (0, 11, 27), 85),
        image(app, "Before_front_case_wrap", {FRONT}, (-100, -150, 75), (0, 18, 36), 86),
        image(app, "Before_rear_plate_servo", {PLATE, SERVO}, (0, -200, 35), (0, -5, 23), 90),
    ]
    write("inspection_images.json", {"images": images, "source_document_not_modified": True})
    return images


def parameters():
    if "parameters" not in STATE:
        s, _ = geometry()
        before = STATE["before"]
        left = s.centre(before["FRAME_M3x35_into_P01_insert"])
        old_axes = [s.centre(before["CLAM_M3x25_FRAME_" + str(i)]) for i in (0, 1)]
        servo_axes = []
        for side in ("left", "right"):
            x, z = s.centre(before["MG90S_M2x6_SERVO_" + side])
            servo_axes.append((CENTRE[0] - (z - CENTRE[1]),
                               CENTRE[1] + (x - CENTRE[0])))
        profile = native().outer_profile(before[CAM])
        radius = max(math.hypot(x - CENTRE[0], z - CENTRE[1]) for x, z in profile)
        STATE["parameters"] = {
            "servo_clock_deg": -90.0, "unchanged_cam_axis_xz_mm": list(CENTRE),
            "new_right_case_axis_xz_mm": [old_axes[1][0], left[1]],
            "left_case_axis_xz_mm": list(left), "retired_upper_case_axes_xz_mm": old_axes,
            "servo_mount_axes_xz_mm": servo_axes,
            "new_right_case_screw": "M3x40, existing lower-case screw geometry reused",
            "new_right_case_insert_od_length_mm": [4.6, 4.0],
            "new_right_case_insert_y_mm": [-8.5, -4.5],
            "right_insert_loaded_from": "rear / negative Y",
            "right_case_mating_plane_y_mm": 11.4,
            "upper_plate_rear_face_y_mm": -8.7,
            "servo_insert_thread_od_length_mm": ["M2", 3.2, 3.0],
            "servo_insert_y_mm": [-2.9, 0.1],
            "servo_insert_pilot_diameter_trial_mm": 2.9,
            "servo_insert_installation": "front-loaded into P02 before case closure; 1.2mm rear shoulder and P01 cap",
            "servo_screw": "existing M2x6 with existing 0.3mm washer",
            "servo_nominal_thread_engagement_mm": 2.5,
            "cam_profile_max_radius_sampled_mm": radius,
            "cam_profile_guard_radius_mm": radius + 0.25,
            "rear_bearing_seat_split_y_mm": 0.3,
            "rear_bearing_and_journal_positions_unchanged": True,
            "P01_rear_bearing_nose_transferred_to_P02_for_flat_print_bed": True,
            "hardware_and_loaded_strength_require_physical_qualification": True,
        }
        write("design_parameters.json", STATE["parameters"])
    return STATE["parameters"]


def corner_cut(first, second, side=1):
    s, _ = geometry()
    dx, dz = second[0] - first[0], second[1] - first[1]
    length = math.hypot(dx, dz)
    if length <= 0:
        raise ValueError("A corner cut needs two distinct points")
    tx, tz = side * dx / length, side * dz / length
    nx, nz = -tz, tx
    centre = adsk.core.Point3D.create(
        ((first[0] + second[0]) / 2 + nx * 50) / 10, 1.0,
        ((first[1] + second[1]) / 2 + nz * 50) / 10)
    return s.tbm().createBox(adsk.core.OrientedBoundingBox3D.create(
        centre, adsk.core.Vector3D.create(tx, 0, tz),
        adsk.core.Vector3D.create(0, 1, 0), 15.0, 12.0, 10.0))


def edit(plan, shape, tool, operation, label):
    s, _ = geometry()
    if not tool.lumps.count:
        raise RuntimeError("Empty candidate tool: " + label)
    if operation == "cut":
        overlap, _ = s.common_volume(shape, tool)
        if overlap == 0:
            STATE.setdefault("candidate_noops", []).append(label)
            return
    volume = shape.volume * 1000
    s.op(shape, s.tbm().copy(tool), operation)
    assert_solid(shape, label)
    plan.append({"operation": operation, "label": label,
                 "tool": s.tbm().copy(tool), "expected": s.tbm().copy(shape)})
    row = {"label": label, "operation": operation, "before_mm3": volume,
           "after_mm3": shape.volume * 1000, "faces": shape.faces.count}
    STATE.setdefault("candidate_build_journal", []).append(row)
    write("candidate_build_journal.json", STATE["candidate_build_journal"])


def store_candidate(name, shape, plan):
    assert_solid(shape, name)
    shell_count = sum(lump.shells.count for lump in shape.lumps)
    if shell_count != 1:
        write("candidate_hidden_cavities.json",
              {"part": name, "shells": shell_count, "stats": stats(shape)})
        raise RuntimeError("The revised print still contains a sealed internal cavity: " + name)
    STATE.setdefault("candidate", {})[name] = shape
    STATE.setdefault("plans", {})[name] = plan
    report = {key: stats(value) for key, value in STATE["candidate"].items()}
    write("candidate_parts.json", report)
    return {"part": name, "steps": len(plan), "stats": stats(shape)}


def prepare_plate(app):
    require(app)
    if PLATE in STATE.get("candidate", {}):
        raise RuntimeError("The plate candidate is already prepared")
    s, m = geometry()
    p = parameters()
    before = STATE["before"]
    shape, plan = s.tbm().copy(before[PLATE]), []
    sb = before[SERVO].preciseBoundingBox
    old_z = (sb.minPoint.z * 10 - 0.3, sb.maxPoint.z * 10 + 1.8)
    edit(plan, shape, s.box(sb.minPoint.x * 10 - 0.3, 22.5, -13.7, -1.8, *old_z),
         "join", "V18 fill retired horizontal servo well and forward boss relief")
    for side in ("left", "right"):
        x, z = s.centre(before["MG90S_M2x6_SERVO_" + side])
        edit(plan, shape, s.cyl(x, z, -4.2, 0.3, 2.9), "join",
             "V18 fill retired M2 nut well " + side)
    edit(plan, shape, s.cyl(-17.0, 40.0, -13.7, 0.3, 3.35), "join",
         "V18 close superseded independent upper plate bolt")
    edit(plan, shape, s.box(-30, 30, -14, -8.7, 28.0, 70), "cut",
         "V18 reduce external upper plate depth to shared-clamp requirement")
    edit(plan, shape, corner_cut((-22.5, 48.0), (-8.5, 62.22059521522819)), "cut",
         "V18 taper obsolete tall negative-X corner")
    edit(plan, shape, corner_cut((-22.5, -11.5), (-17.5, -17.78), -1), "cut",
         "V18 open motor lead corner without cutting lower insert stock")
    cx, cz = CENTRE
    edit(plan, shape, s.box(cx - 6.4, cx + 6.4, -14, -4.1,
                           cz - 21.95, cz + 10.85), "cut",
         "V18 vertical servo rear-entry ear well")
    edit(plan, shape, s.box(cx - 6.4, cx + 6.4, -4.2, -1.95,
                           cz - 17.25, cz + 6.15), "cut",
         "V18 vertical servo body clearance")
    seat = s.cyl(cx, cz, -2.0, 0.3, 8.25)
    s.op(seat, s.cyl(cx, cz, -2.1, -1.15, 5.5), "cut")
    s.op(seat, s.cyl(cx, cz, -1.15, 0.4, 6.025), "cut")
    edit(plan, shape, seat, "join", "V18 P02 rear bearing seat and unchanged axial keeper")
    edit(plan, shape, s.cyl(cx, cz, -2.1, -1.15, 5.5), "cut",
         "V18 clear rotating hub through restored rear keeper")
    edit(plan, shape, s.cyl(cx, cz, -1.15, 0.4, 6.025), "cut",
         "V18 recut canonical bearing bore after retired-well fills")
    for index, (x, z) in enumerate(p["servo_mount_axes_xz_mm"]):
        edit(plan, shape, s.cyl(x, z, -4.2, 0.4, 1.1), "cut",
             "V18 M2 servo clearance " + str(index))
        edit(plan, shape, s.cyl(x, z, -2.9, 0.4, 1.45), "cut",
             "V18 front-loaded captured M2 insert pilot " + str(index))
        edit(plan, shape, m.cone_y(x, z, -0.05, 1.45, 0.35, 1.70), "cut",
             "V18 M2 insert installation lead " + str(index))
    x, z = p["new_right_case_axis_xz_mm"]
    edit(plan, shape, s.cyl(x, z, -8.5, -4.5, 2.1), "cut",
         "V18 rear-loaded M3 shared case and plate insert")
    edit(plan, shape, m.cone_y(x, z, -8.75, 2.35, -8.45, 2.1), "cut",
         "V18 rear M3 insert lead")
    edit(plan, shape, s.cyl(x, z, -4.5, 0.4, 1.7), "cut",
         "V18 shared upper-right screw continuation")
    x, z = p["left_case_axis_xz_mm"]
    edit(plan, shape, s.cyl(x, z, -4.0, 0.4, 1.8), "cut",
         "V18 provide positive left screw-tip clearance")
    return store_candidate(PLATE, shape, plan)


def prepare_back(app):
    require(app)
    if BACK in STATE.get("candidate", {}):
        raise RuntimeError("The back-case candidate is already prepared")
    s, m = geometry()
    p = parameters()
    before = STATE["before"]
    shape, plan = s.tbm().copy(before[BACK]), []
    for index, (x, z) in enumerate(p["retired_upper_case_axes_xz_mm"]):
        edit(plan, shape, s.cyl(x, z, 11.4, 21.7, 5.6), "cut",
             "V18 retire protruding upper post at common mating plane " + str(index))
        edit(plan, shape, s.cyl(x, z, 0.3, 11.4, 3.1), "join",
             "V18 close retired upper case insert " + str(index))
    edit(plan, shape, s.cyl(-17, 40, 0.3, 6.0, 2.5), "join",
         "V18 close retired independent plate insert")
    x, z = p["new_right_case_axis_xz_mm"]
    edit(plan, shape, s.cyl(x, z, 0.3, 11.4, 5.5), "join",
         "V18 single upper-right compression post")
    edit(plan, shape, s.cyl(x, z, 0.2, 21.7, 1.7), "cut",
         "V18 single upper-right screw level with left")
    edit(plan, shape, s.box(-30, 30, -5, 0.3, -70, 85), "cut",
         "V18 flat P01 rear face; rear bearing band now belongs to P02")
    edit(plan, shape, corner_cut((-22.5, 48.0), (-8.5, 62.22059521522819)), "cut",
         "V18 remove superseded high corner and unsupported cover return")
    x, z = p["left_case_axis_xz_mm"]
    plug = s.cyl(x, z, 4.5, 11.4, 2.9)
    s.op(plug, s.cyl(17.2, 40.0, 4.5, 11.4, 2.6), "join")
    s.op(plug, s.cyl(CENTRE[0], CENTRE[1], 4.4, 11.5,
                       p["cam_profile_guard_radius_mm"]), "cut")
    plug = clear_left_filler_for_arm(app, plug)
    if plug.lumps.count:
        edit(plan, shape, plug, "join", "V18 restore offset bore outside actual arm sweep")
    else:
        STATE.setdefault("candidate_noops", []).append(
            "The arm sweep consumes the entire proposed left-post filler")
    edit(plan, shape, s.cyl(x, z, 0.2, 4.6, 2.0), "cut",
         "V18 retain original left rear insert pilot")
    edit(plan, shape, s.cyl(x, z, 4.6, 21.7, 1.7), "cut",
         "V18 one coaxial left frame clearance instead of offset slots")
    window = (-9.95, 13.6, 27.3, 53.6)
    free = s.box(window[0], window[1], 3.1, 3.5, window[2], window[3])
    s.op(free, before[BACK], "cut")
    s.op(free, s.cyl(CENTRE[0], CENTRE[1], 3.0, 3.6, 8.5), "cut")
    bed_opening = m.extrude_slice(free, 3.1, 3.5, window, 0.2, 2.08)
    edit(plan, shape, bed_opening, "cut", "V18 open working cam bay backing to print bed")
    corners = [(-3.3, -2.1, 1.2), (6.3, -2.1, 1.2),
               (-3.3, 5.9, 1.2), (6.3, 5.9, 1.2)]
    fin = m.rounded_box(-4.5, 7.5, 5.35, 10.75, -3.3, 7.1, corners)
    edit(plan, shape, fin, "cut", "V18 remove non-bearing retired pinion-fill knife edge")
    STATE["bed_opening_tool"] = bed_opening
    STATE["gear_fin_tool"] = fin
    return store_candidate(BACK, shape, plan)


def clear_left_filler_for_arm(app, plug):
    s, m = geometry()
    _, data = STATE["controller"].validate(adsk.fusion.Design.cast(app.activeProduct))
    _, digest = STATE["controller"].load_data()
    if "left_arm_clearance_tools" not in STATE:
        pivot = (data["arm_pivot_mm"][0], data["arm_pivot_mm"][2])
        minimum = min(row[1] for row in data["samples"])
        maximum = max(row[1] for row in data["samples"])
        initial = STATE["controller"].arm_angle(data, 0.0)
        intervals = max(1, math.ceil((maximum - minimum) / 0.25))
        tools, rows = [], []
        region = s.box(14.0, 21.6, 4.0, 11.9, 36.8, 45.3)
        for index in range(intervals + 1):
            angle = minimum + (maximum - minimum) * index / intervals
            local = m.rotated(STATE["before_world"]["PRINT_carrier_box_left"],
                              pivot, angle - initial)
            s.op(local, region, "common")
            if local.lumps.count:
                grown = m.grown(local, 0.30)
                axial_tools = [grown, m.translated(grown, dy=-0.25),
                               m.translated(grown, dy=0.25)]
                tools.extend(axial_tools)
                rows.append({"arm_deg": angle, "local_faces": local.faces.count,
                             "tool_faces": sum(tool.faces.count for tool in axial_tools)})
        if not tools:
            raise RuntimeError("The known left-post arm crossing was not found")
        STATE["left_arm_clearance_tools"] = tools
        STATE["left_arm_clearance_data_sha256"] = digest
        write("left_post_arm_sweep.json", {
            "arm_degrees": [minimum, maximum], "physical_arm_step_deg":
                (maximum - minimum) / intervals,
            "sampled_poses": rows, "xz_growth_mm": 0.30, "axial_growth_mm": 0.25,
            "playback_data_sha256": digest,
            "sampled_octagonal_growth_not_a_certified_continuous_offset": True,
            "only_new_filler_trimmed_original_case_not_enlarged": True,
        })
    elif STATE["left_arm_clearance_data_sha256"] != digest:
        raise RuntimeError("The arm contact data changed after clearance construction")
    for tool in STATE["left_arm_clearance_tools"]:
        if plug.lumps.count:
            s.op(plug, tool, "cut")
    STATE["left_post_restoration_tool"] = s.tbm().copy(plug)
    return plug


def prepare_front(app):
    require(app)
    if FRONT in STATE.get("candidate", {}):
        raise RuntimeError("The front-case candidate is already prepared")
    s, m = geometry()
    p = parameters()
    before = STATE["before"]
    shape, plan = s.tbm().copy(before[FRONT]), []
    _, data = STATE["controller"].validate(adsk.fusion.Design.cast(app.activeProduct))
    lowest_arm_angle = min(row[1] for row in data["samples"])
    initial_arm_angle = STATE["controller"].arm_angle(data, 0.0)
    pivot = (data["arm_pivot_mm"][0], data["arm_pivot_mm"][2])
    lever = m.rotated(STATE["before_world"]["PRINT_carrier_box_left"], pivot,
                      lowest_arm_angle - initial_arm_angle)
    s.op(lever, s.box(-30, 0, 10.5, 15.9, 47.0, 66.0), "common")
    if not lever.lumps.count:
        raise RuntimeError("The known upper lever crossing was not found")
    lever_limit_x = lever.preciseBoundingBox.minPoint.x * 10 - 0.30
    lever_clearance = s.box(lever_limit_x, 1.0, 11.3, 14.5, 50.8, 62.6)
    write("upper_lever_clearance.json", {
        "extreme_arm_deg": lowest_arm_angle, "extreme_lever_bounds_mm": bounds(lever),
        "new_rear_filler_stops_at_x_mm": lever_limit_x, "horizontal_margin_mm": 0.30,
        "upper_positive_Z_lever_moves_monotonically_left_over_checked_arm_range": True,
    })
    for index, (x, z) in enumerate(p["retired_upper_case_axes_xz_mm"]):
        rear_fill = s.cyl(x, z, 11.4, 14.4, 5.6)
        if index == 0:
            s.op(rear_fill, lever_clearance, "cut")
        edit(plan, shape, rear_fill, "join",
             "V18 fill retired rear post recess " + str(index))
        edit(plan, shape, s.cyl(x, z, 14.0, 33.149863, 3.35), "join",
             "V18 fill redundant upper front screw counterbore " + str(index))
    x, z = p["new_right_case_axis_xz_mm"]
    edit(plan, shape, s.cyl(x, z, 11.4, 28.0, 5.5), "join",
         "V18 continuous single right post below unchanged tool-locating face")
    edit(plan, shape, s.cyl(x, z, 11.3, 33.5, 1.7), "cut",
         "V18 relocated single upper-right through hole")
    edit(plan, shape, s.cyl(x, z, 31.5, 33.5, 3.05), "cut",
         "V18 flush upper-right M3x40 head pocket")
    edit(plan, shape, corner_cut((-22.5, 48.0), (-8.5, 62.22059521522819)), "cut",
         "V18 compact case head without fragile rear corner tongue")
    return store_candidate(FRONT, shape, plan)


def prepare_cam(app):
    require(app)
    if CAM in STATE.get("candidate", {}):
        raise RuntimeError("The clocked cam candidate is already prepared")
    s, m = geometry()
    before = STATE["before"]
    cx, cz = CENTRE
    shape, plan = s.tbm().copy(before[CAM]), []
    void = s.cyl(cx, cz, -2.0, 1.16, 2.7)
    s.op(void, before[CAM], "cut")
    clocked = m.rotated(void, CENTRE, -90.0)
    edit(plan, shape, s.cyl(cx, cz, -2.0, 1.16, 2.65), "join",
         "V18 fill old spline clocking within unchanged rear journal")
    edit(plan, shape, clocked, "cut",
         "V18 re-clock only the measured spline socket by minus 90 degrees")
    protected = s.cyl(cx, cz, -2.1, 1.26, 2.71)
    old, new = s.tbm().copy(before[CAM]), s.tbm().copy(shape)
    s.op(old, protected, "cut")
    s.op(new, protected, "cut")
    difference = native().exact_difference(old, new)
    if difference:
        raise RuntimeError("The cam lobe, journal or retention geometry changed")
    STATE["cam_outside_socket_difference_mm3"] = difference
    return store_candidate(CAM, shape, plan)


def prepare_hardware(app):
    require(app)
    if "hardware" in STATE:
        raise RuntimeError("Hardware candidates are already prepared")
    s, m = geometry()
    p = parameters()
    before = STATE["before"]
    hardware = {name: m.rotated(before[name], CENTRE, -90.0) for name in
                (SERVO, SPLINE, "MG90S_M2x6_SERVO_left", "MG90S_M2x6_SERVO_right",
                 "MG90S_M2_WASHER_left", "MG90S_M2_WASHER_right")}
    for side, (x, z) in zip(("left", "right"), p["servo_mount_axes_xz_mm"]):
        hardware["MG90S_M2_NUT_" + side] = m.ring(x, z, -2.9, 0.1, 1.6, 1.0)
    x, z = p["new_right_case_axis_xz_mm"]
    reference = before["CLAM_M3x40_FRAME_3"]
    rx, rz = s.centre(reference)
    hardware["CLAM_M3x25_FRAME_1"] = m.translated(reference, dx=x - rx, dz=z - rz)
    insert = before["CLAM_M3_FRAME_INSERT_1"]
    ix, iz = s.centre(insert)
    dy = -8.5 - insert.preciseBoundingBox.minPoint.y * 10
    hardware["CLAM_M3_FRAME_INSERT_1"] = m.translated(insert, dx=x - ix, dy=dy, dz=z - iz)
    for name, shape in hardware.items():
        assert_solid(shape, name)
    STATE["hardware"] = hardware
    STATE["retired"] = RETIRED
    write("hardware_candidates.json", {
        "modified": {name: stats(shape) for name, shape in hardware.items()},
        "removed": list(RETIRED), "new_physical_body_count": len(before) - len(RETIRED),
        "source_metal_gears_motor_bearings_and_tool_parts_not_rebuilt": True,
    })
    return {"modified_references": len(hardware), "retired_references": len(RETIRED),
            "expected_physical_bodies": len(before) - len(RETIRED)}


def verify_protected_geometry(app):
    require(app)
    s, m = geometry()
    before, candidate = STATE["before"], STATE["candidate"]
    cx, cz = CENTRE
    guards = [
        (BACK, "rear gear bearings and motor pilot plate",
         s.box(-22.4, 22.4, 0.3, 5.3, -18, 27)),
        (BACK, "fore portion of rear cam bearing cup",
         s.cyl(cx, cz, 0.3, 4.05, 7.65)),
        (BACK, "belt and carriage interfaces",
         s.box(-30, 30, -2, 25, -60, -18)),
        (FRONT, "MF85 front cam bearing seat",
         s.cyl(cx, cz, 9.6, 14.5, 6.0)),
        (FRONT, "tool magnets, balls and locating pins",
         s.box(-12, 12, 28, 33.3, -23, 45)),
        (FRONT, "centred filament guide and inlet",
         s.box(-6.6, 6.6, 14, 33.3, -17, 63)),
    ]
    motor_x, motor_z = s.centre(before["AHG laminated stator"])
    guards.append((PLATE, "motor pass-through and original lead clearance",
                   m.ring(motor_x, motor_z, -13.7, 0.3, 20.0, 18.0)))
    for index in (0, 1):
        x, z = s.centre(before["M3x18 ISO7380 motor ear " + str(index) + " (rear entry)"])
        guards.append((PLATE, "motor clamping land " + str(index),
                       s.cyl(x, z, -13.7, 0.3, 4.0)))
    guards.extend([
        (PLATE, "lower rear-loaded case insert backing",
         s.cyl(-16, -13, -3.7, 0.3, 4.0)),
        (PLATE, "retained independent lower plate fastener",
         s.cyl(17.25, 23.72, -13.7, 0.3, 4.0)),
    ])
    rows = []
    for name, label, region in guards:
        old, new = s.tbm().copy(before[name]), s.tbm().copy(candidate[name])
        s.op(old, region, "common")
        s.op(new, region, "common")
        difference = native().exact_difference(old, new)
        rows.append({"part": name, "region": label, "exact_difference_mm3": difference})
        if difference:
            write("protected_geometry.json", {"regions": rows, "passed": False})
            raise RuntimeError("A protected functional interface changed: " + label)
    wall = s.box(20.5, 22.5, 0.3, 21.6, -17, 47)
    lost = s.tbm().copy(before[BACK])
    s.op(lost, candidate[BACK], "cut")
    wall_loss, _ = s.common_volume(lost, wall)
    if wall_loss > 1e-7:
        raise RuntimeError("The loaded blue case sidewall was thinned")
    tab = s.box(-22.6, -20.0, 2.9, 11.4, 53.2, 62.3)
    tab_remaining, _ = s.common_volume(candidate[FRONT], tab)
    if tab_remaining > 1e-7:
        raise RuntimeError("The fragile rear cover tongue remains")
    bed_remaining, _ = s.common_volume(candidate[BACK], STATE["bed_opening_tool"])
    fin_remaining, _ = s.common_volume(candidate[BACK], STATE["gear_fin_tool"])
    if bed_remaining > 1e-7 or fin_remaining > 1e-7:
        raise RuntimeError("The marked blind backing or thin fin remains")
    if abs(candidate[BACK].preciseBoundingBox.minPoint.y * 10 - 0.3) > 1e-7:
        raise RuntimeError("The back case does not have the intended flat print datum")
    planes = [face for face in candidate[BACK].faces
              if isinstance(face.geometry, adsk.core.Plane)
              and abs(face.geometry.normal.y) > 0.999999
              and abs(face.geometry.origin.y * 10 - 0.3) < 1e-7]
    report = {
        "regions": rows, "passed": True, "loaded_sidewall_removed_mm3": wall_loss,
        "fragile_cover_return_remaining_mm3": tab_remaining,
        "blind_backing_remaining_mm3": bed_remaining,
        "targeted_gear_fin_remaining_mm3": fin_remaining,
        "P01_flat_rear_print_plane_y_mm": 0.3,
        "P01_flat_print_face_area_mm2": sum(face.area * 100 for face in planes),
        "cam_outside_reclocked_socket_difference_mm3":
            STATE["cam_outside_socket_difference_mm3"],
        "not_a_loaded_strength_or_physical_fit_test": True,
    }
    STATE["protected_verified"] = True
    write("protected_geometry.json", report)
    return report


def logical_bodies(app):
    aliases = {new: old for old, new in STATE.get("aliases", {}).items()}
    return {aliases.get(name, name): body for name, body in bodies(app).items()}


def pose_shapes(app, angle, actual=False):
    s, m = geometry()
    STATE["controller"].drive(app, angle)
    by = logical_bodies(app)
    shapes = {name: s.tbm().copy(body) for name, body in by.items()
              if name not in RETIRED and not name.startswith("REFERENCE_")}
    if not actual:
        shapes.update({name: (m.rotated(shape, CENTRE, angle) if name == CAM
                              else s.tbm().copy(shape))
                       for name, shape in STATE["candidate"].items()})
        shapes.update({name: (m.rotated(shape, CENTRE, angle) if name == SPLINE
                              else s.tbm().copy(shape))
                       for name, shape in STATE["hardware"].items()})
    return shapes


def check_motion(app, angles, actual=False):
    require(app)
    if not STATE.get("protected_verified"):
        raise RuntimeError("Verify the protected interfaces before the clearance sweep")
    s, _ = geometry()
    key = "native_motion" if actual else "candidate_motion"
    accumulated = STATE.setdefault(key, [])
    contacts = {
        frozenset((PLATE, "MG90S_M2_NUT_left")): (3.5, 5.5),
        frozenset((PLATE, "MG90S_M2_NUT_right")): (3.5, 5.5),
        frozenset((PLATE, "CLAM_M3_FRAME_INSERT_1")): (10.0, 12.0),
    }
    changed_hardware = set(STATE["hardware"])
    fixed_hardware = changed_hardware - {SPLINE}
    fixed_parts = (BACK, PLATE, FRONT)
    current_bodies = logical_bodies(app)
    moving_names = {name for name, body in current_bodies.items()
                    if body.assemblyContext.fullPathName[:2]
                    in {"05", "07", "09", "10", "11"}}
    cam_group = {name for name, body in current_bodies.items()
                 if body.assemblyContext.fullPathName.startswith("10 ")}
    core_envelope = s.cyl(CENTRE[0], CENTRE[1], -2.2, 1.26, 2.75)
    gains = {}
    for name in fixed_parts:
        gain = s.tbm().copy(STATE["candidate"][name])
        s.op(gain, STATE["before"][name], "cut")
        gains[name] = gain
    try:
        for angle in angles:
            shapes = pose_shapes(app, float(angle), actual)
            bearing_delta = None
            if actual:
                live = logical_bodies(app)
                matrices = {name: list(live[name].assemblyContext.transform2.asArray())
                            for name in (REAR_BEARING, FORE_BEARING)}
                reference = STATE.setdefault("native_bearing_frames", matrices)
                bearing_delta = max(abs(a - b) for name in matrices
                                    for a, b in zip(reference[name], matrices[name]))
                if bearing_delta > 1e-10:
                    raise RuntimeError("An external cam bearing moved with the cam")
            static_needed = not STATE.get(key + "_static_checked", False)
            unexpected, expected = [], []
            checked = set()
            tests = []
            for index, name in enumerate(fixed_parts):
                if static_needed:
                    for other in fixed_parts[index + 1:]:
                        tests.append((name, shapes[name], other, shapes[other], "whole fixed parts"))
                if gains[name].lumps.count:
                    for other, shape in shapes.items():
                        if other in fixed_parts or other in fixed_hardware:
                            continue
                        if other in moving_names or static_needed:
                            tests.append((name, gains[name], other, shape, "new fixed material"))
            for name in (CAM, *sorted(changed_hardware)):
                for other, shape in shapes.items():
                    if name == CAM:
                        needed = other in fixed_hardware or static_needed
                    elif name == SPLINE:
                        needed = static_needed and other in cam_group
                    else:
                        needed = (other in moving_names and other != SPLINE) or static_needed
                    if not needed:
                        continue
                    pair = frozenset((name, other))
                    if name == other or pair in checked:
                        continue
                    checked.add(pair)
                    tests.append((name, shapes[name], other, shape, "whole moved/replaced part"))
            for other, shape in shapes.items():
                if other not in cam_group and (other in moving_names or static_needed):
                    tests.append(("clocked core radial envelope", core_envelope, other, shape,
                                  "bounds every rotation of the edited socket/shaft region"))
            for name, shape, other, second, scope in tests:
                overlap, _ = s.common_volume(shape, second)
                pair = frozenset((name, other))
                if pair in contacts:
                    lo, hi = contacts[pair]
                    expected.append({"first": name, "second": other,
                                     "installation_interference_mm3": overlap})
                    if not lo <= overlap <= hi:
                        unexpected.append({"first": name, "second": other,
                                           "overlap_mm3": overlap, "scope": "incorrect insert seating"})
                elif overlap > 1e-5:
                    unexpected.append({"first": name, "second": other,
                                       "overlap_mm3": overlap, "scope": scope})
            row = {"cam_deg": float(angle), "pair_tests": len(tests),
                   "fixed_pairs_rechecked": static_needed,
                   "expected_insert_press_fits": expected, "unexpected_interferences": unexpected}
            if bearing_delta is not None:
                row["fixed_bearing_frame_max_delta"] = bearing_delta
            accumulated.append(row)
            write(key + ".json", {
                "poses": accumulated, "sampled_not_continuous_force_analysis": True,
                "scope": "New fixed material versus every moving part; relocated hardware; fixed pairs once; "
                         "unchanged cam exterior inherited through exact protected-geometry comparison; "
                         "edited core checked inside a full-rotation radial envelope.",
            })
            if unexpected:
                raise RuntimeError("Unexpected interference at cam " + str(angle)
                                   + ": " + json.dumps(unexpected[:8]))
            STATE[key + "_static_checked"] = True
    finally:
        STATE["controller"].drive(app, 0.0)
    return {"checked_cam_degrees": [float(a) for a in angles],
            "total_recorded_poses": len(accumulated),
            "unexpected_interferences": 0, "insert_interferences_are_intentional": True}


def normalize_edit_pose(app):
    require(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    reset = {}
    # Feature recomputation obeys native joint fields, not the temporary FK poses.
    for name in ("J_CAM", "J_C"):
        joint = root.joints.itemByName(name)
        if joint is None or joint.isLocked:
            raise RuntimeError("The edit-pose joint is unavailable: " + name)
        motion = joint.jointMotion
        motion.rotationLimits.isRestValueEnabled = False
        previous = motion.rotationValue
        if abs(previous) > 1e-12:
            motion.rotationValue = 0.0
            reset[name] = math.degrees(previous)
    STATE["controller"].drive(app, 0.0)
    if reset:
        STATE.setdefault("edit_pose_resets", []).append(reset)
        write("native_edit_pose_resets.json", {"resets_from_degrees": STATE["edit_pose_resets"],
                                              "final_edit_pose_degrees": 0})


def check_pocket_corrections_motion(app, angles):
    require(app)
    if not STATE.get("protected_verified") or not STATE.get("pocket_amendments"):
        raise RuntimeError("Review the add-only cavity corrections first")
    s, _ = geometry()
    baseline = json.loads((OUT / "candidate_motion_before_pocket_fill.json").read_text())["poses"]
    if {row["cam_deg"] for row in baseline} != {i * 2.5 for i in range(71)} or any(
            row["unexpected_interferences"] for row in baseline):
        raise RuntimeError("The pre-correction motion proof is incomplete")
    STATE["candidate_motion"] = baseline
    by = logical_bodies(app)
    moving = {name for name, body in by.items()
              if body.assemblyContext.fullPathName[:2] in {"05", "07", "09", "10", "11"}}
    expected_press = {
        frozenset((PLATE, "MG90S_M2_NUT_left")): (3.5, 5.5),
        frozenset((PLATE, "MG90S_M2_NUT_right")): (3.5, 5.5),
        frozenset((PLATE, "CLAM_M3_FRAME_INSERT_1")): (10.0, 12.0),
    }
    rows = STATE.setdefault("pocket_motion", [])
    try:
        for angle in angles:
            shapes = pose_shapes(app, float(angle), False)
            static_needed = not STATE.get("pocket_static_checked")
            unexpected = []
            tests = 0
            for name, amendment in STATE["pocket_amendments"].items():
                for other, shape in shapes.items():
                    if other == name or (other not in moving and not static_needed):
                        continue
                    tests += 1
                    volume, _ = s.common_volume(amendment["tool"], shape)
                    pair = frozenset((name, other))
                    if volume > 1e-5:
                        if pair in expected_press:
                            complete_fit, _ = s.common_volume(shapes[name], shape)
                            lo, hi = expected_press[pair]
                            if lo <= complete_fit <= hi:
                                continue
                        unexpected.append({"first": name, "second": other,
                                           "new_material_overlap_mm3": volume})
            rows.append({"cam_deg": float(angle), "new_material_pair_tests": tests,
                         "fixed_pairs_rechecked": static_needed,
                         "unexpected_interferences": unexpected})
            write("pocket_correction_motion.json", {
                "baseline_archive_sha256": STATE["initial_archive"]["sha256"],
                "baseline_poses": 71, "add_only_corrections": True, "poses": rows,
                "scope": "Reuses the complete baseline proof and tests every newly added solid "
                         "against all other parts, fixed pairs once and moving parts at every pose.",
            })
            if unexpected:
                raise RuntimeError("The closed-pocket fill blocks motion: " + json.dumps(unexpected))
            STATE["pocket_static_checked"] = True
    finally:
        normalize_edit_pose(app)
    complete = {row["cam_deg"] for row in rows} == {i * 2.5 for i in range(71)}
    STATE["pocket_motion_verified"] = complete
    return {"checked_new_material_poses": len(rows), "complete": complete,
            "unexpected_interferences": 0}


def require_reviewed_candidates(app):
    require(app)
    if not STATE.get("protected_verified"):
        raise RuntimeError("The protected-interface review is incomplete")
    poses = STATE.get("candidate_motion", [])
    checked = {row["cam_deg"] for row in poses if not row["unexpected_interferences"]}
    if checked != {i * 2.5 for i in range(71)} or any(
            row["unexpected_interferences"] for row in poses):
        raise RuntimeError("Complete the source-bound 0..175 degree candidate sweep")
    if STATE.get("pocket_amendments") and not STATE.get("pocket_motion_verified"):
        raise RuntimeError("Finish the add-only closed-pocket correction review")
    if STATE.get("inflight"):
        raise RuntimeError("Inspect the unresolved native edit before resuming: "
                           + json.dumps(STATE["inflight"]))
    normalize_edit_pose(app)


def write_progress():
    write("native_edit_progress.json", {
        "document": STATE["document"], "source_document": STATE["source_document"],
        "print_steps": STATE.get("apply_indices", {}),
        "print_step_counts": {name: len(plan) for name, plan in STATE["plans"].items()},
        "hardware": STATE.get("hardware_applied", []),
        "retired": STATE.get("retired_applied", []),
        "inflight": STATE.get("inflight"),
    })


def require_identity_context(body):
    identity = adsk.core.Matrix3D.create().asArray()
    if max(abs(a - b) for a, b in zip(
            body.assemblyContext.transform2.asArray(), identity)) > 1e-8:
        raise RuntimeError("The closed-pose component frame is not the captured identity: " + body.name)


def append_step(app, name, step):
    require(app)
    normalize_edit_pose(app)
    s, _ = geometry()
    proxy = logical_bodies(app)[name]
    require_identity_context(proxy)
    body = proxy.nativeObject or proxy
    component = body.parentComponent
    if component.bRepBodies.count != 1:
        raise RuntimeError("Unconsumed native construction bodies are present in " + name)
    feature = component.features.baseFeatures.add()
    feature.name = step["label"] + " tools"
    if not feature.startEdit():
        raise RuntimeError("Could not start the bounded native geometry tool")
    try:
        for lump in step["tool"].lumps:
            component.bRepBodies.add(s.tbm().copy(lump), feature)
    finally:
        if not feature.finishEdit():
            raise RuntimeError("Could not finish the bounded native geometry tool")
    collection = adsk.core.ObjectCollection.create()
    for index, tool_body in enumerate(feature.bodies):
        tool_body.name = step["label"] + " tool " + str(index)
        collection.add(tool_body)
    if collection.count != step["tool"].lumps.count:
        raise RuntimeError("The native tool-body inventory is incomplete")
    target = component.bRepBodies.itemByName(name)
    inp = component.features.combineFeatures.createInput(target, collection)
    inp.operation = (adsk.fusion.FeatureOperations.JoinFeatureOperation
                     if step["operation"] == "join"
                     else adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.isKeepToolBodies = False
    combined = component.features.combineFeatures.add(inp)
    combined.name = step["label"]
    if combined.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError("Native case edit failed: " + combined.errorOrWarningMessage)
    actual = component.bRepBodies.itemByName(name)
    assert_solid(actual, name)
    difference = native().exact_difference(step["expected"], s.tbm().copy(actual))
    if difference:
        raise RuntimeError("The native edit differs from its reviewed solid: " + name)
    return {"label": step["label"], "exact_candidate_difference_mm3": difference,
            "native_timeline_index": combined.timelineObject.index}


def apply_print_batch(app, name, count=4):
    require_reviewed_candidates(app)
    if name not in STATE["plans"] or count <= 0:
        raise ValueError("Choose a prepared print and a positive step count")
    s, _ = geometry()
    indices = STATE.setdefault("apply_indices", {})
    start = indices.get(name, 0)
    plan = STATE["plans"][name]
    expected_input = STATE["before"][name] if start == 0 else plan[start - 1]["expected"]
    actual = logical_bodies(app)[name]
    if native().exact_difference(expected_input, s.tbm().copy(actual.nativeObject or actual)):
        raise RuntimeError("The owned print changed between native edit batches: " + name)
    completed = []
    for index in range(start, min(len(plan), start + count)):
        STATE["inflight"] = {"part": name, "step": index, "label": plan[index]["label"]}
        write_progress()
        row = append_step(app, name, plan[index])
        completed.append(row)
        indices[name] = index + 1
        STATE.pop("inflight")
        STATE.setdefault("native_feature_checks", []).append(row)
        write_progress()
    write("native_feature_checks.json", STATE.get("native_feature_checks", []))
    return {"part": name, "completed": indices.get(name, 0), "total": len(plan),
            "batch_steps": completed}


def apply_hardware_batch(app, count=3):
    require_reviewed_candidates(app)
    if any(STATE.get("apply_indices", {}).get(name, 0) != len(plan)
           for name, plan in STATE["plans"].items()):
        raise RuntimeError("Complete all four native printed parts before hardware")
    s, _ = geometry()
    applied = STATE.setdefault("hardware_applied", [])
    pending = [name for name in STATE["hardware"] if name not in applied]
    rotating = {SERVO, SPLINE, "MG90S_M2x6_SERVO_left", "MG90S_M2x6_SERVO_right",
                "MG90S_M2_WASHER_left", "MG90S_M2_WASHER_right"}
    for name in pending[:count]:
        normalize_edit_pose(app)
        proxy = logical_bodies(app)[name]
        require_identity_context(proxy)
        original = proxy.nativeObject or proxy
        component = original.parentComponent
        if native().exact_difference(STATE["before"][name], s.tbm().copy(original)):
            raise RuntimeError("The hardware reference changed before relocation: " + name)
        STATE["inflight"] = {"hardware": name}
        write_progress()
        if name in rotating or name == "CLAM_M3_FRAME_INSERT_1":
            if name in rotating:
                matrix = STATE["controller"].rotation(-90.0, (CENTRE[0], 0, CENTRE[1]))
            else:
                matrix = adsk.core.Matrix3D.create()
                matrix.translation = adsk.core.Vector3D.create(0, -1.85, -0.5)
            collection = adsk.core.ObjectCollection.create()
            collection.add(original)
            inp = component.features.moveFeatures.createInput2(collection)
            if not inp.defineAsFreeMove(matrix):
                raise RuntimeError("The hardware move could not be defined")
            feature = component.features.moveFeatures.add(inp)
            feature.name = "V18 relocate " + name
            if feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
                raise RuntimeError("The hardware move failed: " + feature.errorOrWarningMessage)
        else:
            removed = component.features.removeFeatures.add(original)
            removed.name = "V18 retire old " + name
            feature = component.features.baseFeatures.add()
            feature.name = "V18 replacement " + name
            if not feature.startEdit():
                raise RuntimeError("Could not start the replacement reference")
            try:
                replacement = component.bRepBodies.add(
                    s.tbm().copy(STATE["hardware"][name]), feature)
                replacement.name = name
            finally:
                if not feature.finishEdit():
                    raise RuntimeError("Could not finish the replacement reference")
            if component.bRepBodies.count != 1:
                raise RuntimeError("The replacement reference is not a single body")
            replacement = component.bRepBodies.item(0)
            replacement.name = name
            appearance_name = ("FRAME_M3_HEATSET_in_P01"
                               if name.startswith("MG90S_M2_NUT_") else name)
            appearance = STATE["appearances"][appearance_name]
            if appearance is not None:
                replacement.appearance = appearance
        actual = component.bRepBodies.itemByName(name)
        assert_solid(actual, name)
        difference = native().exact_difference(
            STATE["hardware"][name], s.tbm().copy(actual))
        if difference:
            raise RuntimeError("A hardware reference differs from the reviewed candidate: " + name)
        applied.append(name)
        STATE.pop("inflight")
        write_progress()
    return {"completed_references": len(applied), "total_references": len(STATE["hardware"])}


def retire_obsolete_hardware(app):
    require_reviewed_candidates(app)
    if len(STATE.get("hardware_applied", [])) != len(STATE["hardware"]):
        raise RuntimeError("Complete the retained hardware before removing superseded references")
    retired = STATE.setdefault("retired_applied", [])
    for name in RETIRED:
        if name in retired:
            continue
        proxy = bodies(app)[name]
        component = (proxy.nativeObject or proxy).parentComponent
        occurrence = proxy.assemblyContext
        STATE["inflight"] = {"retiring": name}
        write_progress()
        feature = component.features.removeFeatures.add(proxy.nativeObject or proxy)
        feature.name = "V18 remove superseded " + name
        if component.bRepBodies.count:
            raise RuntimeError("The obsolete physical reference remains: " + name)
        occurrence.isLightBulbOn = False
        retired.append(name)
        STATE.pop("inflight")
        write_progress()
    expected = len(STATE["before"]) - len(RETIRED)
    if len(bodies(app)) != expected:
        raise RuntimeError("The final physical-body count is not the reviewed inventory")
    return {"physical_bodies": expected, "obsolete_bodies_removed": list(retired),
            "empty_historical_occurrences_retained_for_existing_rigid_links": True}


def apply_pocket_corrections(app):
    require_reviewed_candidates(app)
    s, _ = geometry()
    applied = STATE.setdefault("pocket_corrections_applied", [])
    for name, step in STATE["pocket_amendments"].items():
        if name in applied:
            continue
        body = logical_bodies(app)[name].nativeObject
        if native().exact_difference(step["before"], s.tbm().copy(body)):
            raise RuntimeError("The native plate changed before the sealed-pocket correction")
        STATE["inflight"] = {"closed_pocket_correction": name}
        write_progress()
        row = append_step(app, name, step)
        body = logical_bodies(app)[name].nativeObject
        if sum(lump.shells.count for lump in body.lumps) != 1:
            raise RuntimeError("The native pocket correction did not remove the enclosed shell")
        applied.append(name)
        STATE.setdefault("native_feature_checks", []).append(row)
        STATE.pop("inflight")
        write_progress()
    write("native_pocket_corrections.json", {
        "parts": applied, "native_additions_only": True, "mesh_editing_not_called": True})
    return {"corrected_native_parts": applied, "all_four_prints_single_boundary_shell": True}


def finalize_labels(app):
    require_reviewed_candidates(app)
    if len(STATE.get("retired_applied", [])) != len(RETIRED):
        raise RuntimeError("The obsolete hardware has not been removed")
    aliases = STATE.setdefault("aliases", {})
    mapping = {
        "MG90S_M2_NUT_left": "MG90S_UPPER_M2_HEATSET_3p2x3",
        "MG90S_M2_NUT_right": "MG90S_LOWER_M2_HEATSET_3p2x3",
        "CLAM_M3x25_FRAME_1": "UPPER_RIGHT_SHARED_M3x40_FRAME",
        "CLAM_M3_FRAME_INSERT_1": "UPPER_RIGHT_REAR_M3_HEATSET_4p6x4",
    }
    for old, new in mapping.items():
        if old in aliases:
            continue
        body = logical_bodies(app)[old].nativeObject
        body.name = new
        body.parentComponent.name = new.replace("_", " ")
        aliases[old] = new
        write("body_aliases.json", aliases)
    names = {
        BACK: "P01 v18 flat-back case - bed-open working bay",
        PLATE: "P02 v18 vertical servo - captured inserts and rear bearing band",
        FRONT: "P03 v18 single level upper-right clamp",
        CAM: "P05 v18 cam - spline clocked minus90 - FIT PENDING",
    }
    for name, label in names.items():
        body = logical_bodies(app)[name].nativeObject
        body.parentComponent.name = label
        body.attributes.add("SlimV18", "revision", "Print feedback v18 / WIP")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    for occurrence in root.allOccurrences:
        if (not occurrence.childOccurrences.count
                and not occurrence.component.bRepBodies.count
                and occurrence.component.name in RETIRED):
            occurrence.component.name = "HISTORY ONLY retired " + occurrence.component.name
            occurrence.isLightBulbOn = False
    source = json.loads((OUT / "source_capture.json").read_text())
    root.attributes.add("SlimV18", "input_sha256", source["source_sha256"])
    root.attributes.add("SlimV18", "changes",
                        "Vertical MG90S;captured M2 inserts;single level right M3 rear heatset;"
                        "flat P01;bed-open cam bay;obsolete corner/slots/fin removed")
    root.attributes.add("SlimV18", "qualification",
                        "Native geometry and sampled kinematics only;actual inserts,spline,"
                        "tolerances,loaded strength and endurance require bench qualification")
    root.attributes.add("SparkShiftMotion", "revision",
                        "v18 print-feedback slimming;v15 progressive lobe retained;"
                        "direct 21T socket clocked minus90;FIT PENDING")
    by = logical_bodies(app)
    by[SERVO].nativeObject.attributes.add("SlimV18", "body_clock_deg", "-90")
    for old in ("MG90S_M2_NUT_left", "MG90S_M2_NUT_right"):
        body = by[old].nativeObject
        body.attributes.add("SlimV18", "hardware",
                            "M2 brass insert OD3.2 L3.0;nominal cylinder reference")
        body.attributes.add("SlimV18", "installation",
                            "Front-load into P02 before closure;1.2mm rear shoulder;P01 front cap")
    by["CLAM_M3_FRAME_INSERT_1"].nativeObject.attributes.add(
        "SlimV18", "installation", "Rear-loaded M3 OD4.6 L4;P02 shared case clamp")
    STATE["labels_finalized"] = True
    return {"aliases": aliases, "physical_bodies": len(bodies(app)),
            "printed_roles_retained": list(names)}


def expected_definitions():
    expected = {name: shape for name, shape in STATE["before"].items() if name not in RETIRED}
    expected.update(STATE["candidate"])
    expected.update(STATE["hardware"])
    return expected


def verify_model_batch(app, count=35):
    require(app)
    if not STATE.get("labels_finalized"):
        raise RuntimeError("Finalize the physical inventory and labels before the model guard")
    normalize_edit_pose(app)
    s, _ = geometry()
    by, expected = logical_bodies(app), expected_definitions()
    if set(by) != set(expected):
        raise RuntimeError("The live physical inventory differs from the reviewed assembly")
    rows = STATE.setdefault("model_checks", [])
    names = sorted(expected)
    changed = set(STATE["candidate"]) | set(STATE["hardware"])
    for name in names[len(rows):len(rows) + count]:
        proxy = by[name]
        shape = s.tbm().copy(proxy.nativeObject or proxy)
        assert_solid(shape, name)
        difference = native().exact_difference(expected[name], shape)
        if name in changed:
            require_identity_context(proxy)
            world_difference = difference
        else:
            world_difference = native().exact_difference(
                STATE["before_world"][name], s.tbm().copy(proxy))
        row = {"body": name, "intended_change": name in changed,
               "native_definition_difference_mm3": difference,
               "closed_world_difference_mm3": world_difference,
               "single_positive_solid": True}
        rows.append(row)
        write("native_model_guard.json", {"bodies": rows, "expected_total": len(expected)})
        if difference or world_difference:
            raise RuntimeError("Unintended live definition or placement change: " + name)
    complete = len(rows) == len(expected)
    if complete:
        STATE["native_model_verified"] = True
    return {"checked_bodies": len(rows), "total": len(expected), "complete": complete,
            "unchanged_definitions": sum(not row["intended_change"] for row in rows),
            "all_checked_differences_zero": True}


def metrics(app):
    require(app)
    if not STATE.get("native_model_verified"):
        raise RuntimeError("Verify the live native model before computing final measurements")
    s, _ = geometry()
    by = logical_bodies(app)
    parts = (BACK, PLATE, FRONT)
    old_volume = sum(STATE["before"][name].volume * 1000 for name in parts)
    new_volume = sum(by[name].volume * 1000 for name in parts)
    cross_section = s.box(-30, 30, -20, 40, 59.99, 60.01)
    widths = {}
    for label, shapes in (("before", [STATE["before"][name] for name in parts]),
                          ("after", [by[name].nativeObject for name in parts])):
        boxes = []
        for shape in shapes:
            piece = s.tbm().copy(shape)
            s.op(piece, cross_section, "common")
            if piece.lumps.count:
                boxes.append(piece.preciseBoundingBox)
        widths[label] = (max(box.maxPoint.x for box in boxes)
                         - min(box.minPoint.x for box in boxes)) * 10
    left = s.centre(by["FRAME_M3x35_into_P01_insert"])
    right = s.centre(by["CLAM_M3x25_FRAME_1"])
    if abs(left[1] - right[1]) > 1e-8:
        raise RuntimeError("The two upper case screws are not level")
    report = {
        "physical_bodies": len(by), "changed_printed_parts": [BACK, PLATE, FRONT, CAM],
        "case_solid_CAD_volume_before_mm3": old_volume,
        "case_solid_CAD_volume_after_mm3": new_volume,
        "case_solid_CAD_volume_reduction_percent": (old_volume - new_volume) / old_volume * 100,
        "not_a_printed_mass_or_infill_estimate": True,
        "head_cross_section_z_mm": 60.0, "head_width_mm": widths,
        "overall_height_not_reduced": True,
        "gear_bearing_cam_and_tool_location_datums_retained": True,
        "upper_left_case_axis_xz_mm": left, "upper_right_case_axis_xz_mm": right,
        "upper_case_level_error_mm": abs(left[1] - right[1]),
        "upper_right_screw_count": 1, "upper_right_insert_loaded_from": "rear",
        "servo_case_clock_deg": -90.0, "servo_hex_nuts_remaining": 0,
        "new_M2_heatset_count": 2, "all_heatset_references_per_build": 14,
        "heatset_breakdown": {"M3": 12, "M2": 2},
        "both_external_cam_bearings_retained": True,
        "loaded_strength_not_measured_or_FEA_qualified": True,
    }
    write("revision_measurements.json", report)
    return report


def check_assembly_paths(app):
    require(app)
    if not STATE.get("native_model_verified"):
        raise RuntimeError("Use the checked live revision for assembly-path review")
    normalize_edit_pose(app)
    s, m = geometry()
    by = logical_bodies(app)
    shape = {name: s.tbm().copy(body) for name, body in by.items()}
    rows = []
    stages = [
        ("servo drops into P02 from rear", SERVO, (-15, -8, -4, -2, -1, -0.5, 0), (PLATE,)),
        ("rear bearing enters P01 before P02", REAR_BEARING,
         (-12, -6, -3, -1, -0.5, 0), (BACK, CAM)),
        ("P02 closes rear bearing seat", PLATE, (-8, -4, -2, -1, -0.5, 0),
         (BACK, CAM, REAR_BEARING)),
        ("clocked output enters cam with P02", SPLINE, (-8, -4, -2, -1, -0.5, 0), (CAM, BACK)),
        ("shared M3x40 enters from front", "CLAM_M3x25_FRAME_1",
         (30, 15, 5, 2, 1, 0), (BACK, PLATE, FRONT, "PRINT_RedLizard_HF_tool_carrier")),
    ]
    for label, moving, offsets, targets in stages:
        for offset in offsets:
            moved = m.translated(shape[moving], dy=offset)
            for target in targets:
                volume, _ = s.common_volume(moved, shape[target])
                row = {"stage": label, "offset_y_mm": offset, "against": target,
                       "overlap_mm3": volume}
                rows.append(row)
                write("assembly_paths.json", {"samples": rows})
                if volume > 1e-5:
                    raise RuntimeError("The stated new-interface assembly path is blocked: "
                                       + json.dumps(row))
    x, z = parameters()["new_right_case_axis_xz_mm"]
    iron = s.cyl(x, z, -60, -8.75, 2.5)
    s.op(iron, s.cyl(x, z, -8.8, -8.45, 2.0), "join")
    drivers = [
        ("M3 rear heatset iron approach before screw installation", iron,
         ("CLAM_M3_FRAME_INSERT_1", "CLAM_M3x25_FRAME_1")),
        ("M3 upper-right front driver", s.cyl(x, z, 33.2, 80, 1.35),
         ("CLAM_M3x25_FRAME_1",)),
    ]
    for label, driver, excluded in drivers:
        for target, fixed in shape.items():
            if target in excluded or target.startswith("REFERENCE_"):
                continue
            volume, _ = s.common_volume(driver, fixed)
            if volume > 1e-5:
                raise RuntimeError("Required new fastener approach is blocked: "
                                   + label + " / " + target)
    result = {"new_interface_path_samples": len(rows), "all_sampled_paths_clear": True,
              "rear_insert_iron_and_front_driver_approaches_clear": True,
              "M2_inserts_installed_with_P02_off_the_frame": True,
              "not_whole_toolhead_installation_or_physical_press_fit_qualification": True}
    write("assembly_paths_summary.json", result)
    return result


def require_final_model(app):
    require(app)
    if not STATE.get("native_model_verified"):
        raise RuntimeError("The live native model guard is incomplete")
    poses = STATE.get("native_motion", [])
    if {row["cam_deg"] for row in poses} != {0, 30, 60, 90, 120, 150, 170, 175} or any(
            row["unexpected_interferences"] for row in poses):
        raise RuntimeError("The actual edited assembly motion review is incomplete")
    summary = json.loads((OUT / "native_release_summary.json").read_text())
    if summary["full_open_hob_rim_gap_mm"] < 2.5:
        raise RuntimeError("The required live opening is not recorded")
    for name in (BACK, PLATE, FRONT, CAM):
        body = logical_bodies(app)[name].nativeObject
        if sum(lump.shells.count for lump in body.lumps) != 1:
            raise RuntimeError("A sealed internal print cavity remains: " + name)


def export_native(app):
    require_final_model(app)
    normalize_edit_pose(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design.timeline.markerPosition != design.timeline.count:
        raise RuntimeError("The final native history is not fully evaluated")
    (PAYLOAD / "cad").mkdir(parents=True, exist_ok=True)
    path = PAYLOAD / "cad" / "SparkShift_slim_print_feedback_v18_WIP.f3d"
    if path.exists():
        raise RuntimeError("The final native archive already exists; inspect its receipt first")
    by = logical_bodies(app)
    keep = {name for name in bodies(app)
            if not ("FILAMENT" in name.upper() and "REFERENCE" in name.upper())}
    show(app, keep)
    if not design.exportManager.execute(
            design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("The final native assembly export failed")
    report = {
        "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size, "physical_bodies": len(by),
        "authoring_document": STATE["document"], "source_document": STATE["source_document"],
        "input_sha256": json.loads((OUT / "source_capture.json").read_text())["source_sha256"],
        "closed_context_matrices": {
            name: list(body.assemblyContext.transform2.asArray()) for name, body in by.items()},
        "playback_data_sha256": STATE["controller"].load_data()[1],
        "all_source_history_retained_with_downstream_revision_features": True,
        "not_published": True,
    }
    STATE["archive"] = report
    write("native_archive_receipt.json", report)
    return {key: value for key, value in report.items() if key != "closed_context_matrices"}


def begin_print_export(app):
    require_final_model(app)
    if "archive" not in STATE or STATE.get("mesh_document"):
        raise RuntimeError("Save the checked archive before starting one print-export document")
    normalize_edit_pose(app)
    support = load_file("sparkshift_v18_print_helpers", BASE / "sparkshift_surface_cleanup.py")
    s, _ = geometry()
    by = logical_bodies(app)
    shapes = []
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
            if not rotation.setToRotation(angle, axis, adsk.core.Point3D.create(0, 0, 0)):
                raise RuntimeError("Could not form the print-bed rotation")
            if not s.tbm().transform(shape, rotation):
                raise RuntimeError("The print-bed rotation failed")
        box = shape.preciseBoundingBox
        translation = adsk.core.Matrix3D.create()
        translation.translation = adsk.core.Vector3D.create(
            -box.minPoint.x, -box.minPoint.y, -box.minPoint.z)
        if not s.tbm().transform(shape, translation):
            raise RuntimeError("The print-bed translation failed")
        assert_solid(shape, part)
        shapes.append((part, name, filename, shape, orientation,
                       list(rotation.asArray()), list(translation.asArray()),
                       body.volume * 1000))
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.activate()
    document.name = "EXPORT ONLY - v18 four revised print meshes"
    design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
    STATE["mesh_document"] = document.creationId
    STATE["mesh_source_document"] = source.creationId
    STATE["mesh_shapes"] = shapes
    STATE["mesh_exports"] = {}
    for part, name, filename, shape, orientation, rotation, translation, volume in shapes:
        feature = design.rootComponent.features.baseFeatures.add()
        feature.name = "V18 print export " + part
        if not feature.startEdit():
            raise RuntimeError("Could not start the export-only print body")
        try:
            body = design.rootComponent.bRepBodies.add(shape, feature)
            body.name = part
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish the export-only print body")
        body = feature.bodies.item(0)
        body.name = part
        body.isLightBulbOn = True
    (PAYLOAD / "stl").mkdir(parents=True, exist_ok=True)
    return {"export_document": document.creationId, "revised_prints": len(shapes),
            "main_assembly_not_transformed": True}


def export_print_batch(app, count=2):
    if app.activeDocument.creationId != STATE.get("mesh_document"):
        raise RuntimeError("Activate only the owned export-only print document")
    design = adsk.fusion.Design.cast(app.activeProduct)
    start = len(STATE["mesh_exports"])
    for part, name, filename, shape, orientation, rotation, translation, volume in (
            STATE["mesh_shapes"][start:start + count]):
        path = PAYLOAD / "stl" / (filename + ".stl")
        if path.exists():
            raise RuntimeError("A native print mesh would be overwritten: " + part)
        body = design.rootComponent.bRepBodies.itemByName(part)
        if body is None:
            raise RuntimeError("The export-only print body is missing: " + part)
        options = design.exportManager.createSTLExportOptions(body, str(path))
        options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        options.isBinaryFormat = True
        if part == "P05":
            options.surfaceDeviation = 0.0003
            options.normalDeviation = 4.0
        if not design.exportManager.execute(options) or path.stat().st_size <= 84:
            raise RuntimeError("The revised native STL export failed: " + part)
        STATE["mesh_exports"][part] = {
            "body": name, "path": str(path), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "native_volume_mm3": volume, "bed_face": orientation,
            "rotation": rotation, "translation": translation,
            "native_archive_sha256": STATE["archive"]["sha256"],
            "quality": "native fine spline custom" if part == "P05" else "native high",
            "raw_native_no_mesh_repair": True,
        }
        write("mesh_export_receipt.json", STATE["mesh_exports"])
    return {"exported": len(STATE["mesh_exports"]), "total": len(CHANGED_PRINTS)}


def close_print_export(app):
    if len(STATE.get("mesh_exports", {})) != len(CHANGED_PRINTS):
        raise RuntimeError("The four-part mesh export is incomplete")
    document = next(d for d in app.documents if d.creationId == STATE["mesh_document"])
    source = next(d for d in app.documents if d.creationId == STATE["mesh_source_document"])
    source.activate()
    if not document.close(False):
        raise RuntimeError("Could not close the owned export-only document")
    STATE["closed_mesh_document"] = STATE.pop("mesh_document")
    return {"owned_export_document_closed": True, "main_assembly_active": True}


def begin_readback(app):
    require_final_model(app)
    if STATE.get("readback_document"):
        raise RuntimeError("The independent native readback already exists")
    receipt = STATE["archive"]
    path = Path(receipt["path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["sha256"]:
        raise RuntimeError("The saved native archive changed before independent readback")
    document = app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(path)))
    if document is None or document.creationId == STATE["document"]:
        raise RuntimeError("Could not independently reopen the saved native revision")
    document.activate()
    document.name = "SparkShift v18 - slim print-feedback - WIP"
    design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
    STATE["controller"].validate(design)
    STATE["readback_document"] = document.creationId
    STATE["readback_checks"] = []
    return {"readback_document": document.creationId, "saved_archive_sha256": receipt["sha256"]}


def verify_readback_batch(app, count=50):
    if app.activeDocument.creationId != STATE.get("readback_document"):
        raise RuntimeError("Activate only the independent v18 archive readback")
    s, _ = geometry()
    raw = bodies(app)
    if not set(STATE["aliases"].values()).issubset(raw):
        raise RuntimeError("The corrected hardware labels did not persist in the archive")
    by, expected = logical_bodies(app), expected_definitions()
    if set(by) != set(expected):
        raise RuntimeError("The reopened native physical inventory differs")
    names = sorted(expected)
    rows = STATE["readback_checks"]
    for name in names[len(rows):len(rows) + count]:
        body = by[name]
        shape = s.tbm().copy(body.nativeObject or body)
        assert_solid(shape, name)
        difference = native().exact_difference(expected[name], shape)
        matrix_error = max(abs(a - b) for a, b in zip(
            STATE["archive"]["closed_context_matrices"][name],
            body.assemblyContext.transform2.asArray()))
        rows.append({"body": name, "exact_definition_difference_mm3": difference,
                     "closed_context_matrix_max_delta": matrix_error})
        write("native_archive_readback.json", {
            "archive_sha256": STATE["archive"]["sha256"], "bodies": rows,
            "expected_count": len(expected),
        })
        if difference or matrix_error > 1e-8:
            raise RuntimeError("The independent native archive differs: " + name)
    complete = len(rows) == len(expected)
    if complete:
        STATE["readback_verified"] = True
    return {"verified_bodies": len(rows), "total": len(expected), "complete": complete,
            "all_checked_definitions_and_poses_match": True}


def verify_source_preserved(app):
    s, _ = geometry()
    documents = [d for d in app.documents if d.creationId == STATE["source_document"]]
    if not documents:
        report = {"source_document_not_open": True,
                  "original_input_archive_preserved": str(OUT / "source_capture.json"),
                  "no_live_source_equality_assertion": True}
        write("source_preservation.json", report)
        return report
    design = adsk.fusion.Design.cast(documents[0].products.itemByProductType("DesignProductType"))
    by = {body.name: body for occurrence in design.rootComponent.allOccurrences
          for body in occurrence.bRepBodies}
    if set(by) != set(STATE["source_shapes"]):
        raise RuntimeError("The live user source inventory changed during this work")
    rows = []
    for name, expected in STATE["source_shapes"].items():
        difference = native().exact_difference(
            expected, s.tbm().copy(by[name].nativeObject or by[name]))
        rows.append({"body": name, "exact_definition_difference_mm3": difference})
        write("source_preservation.json", {"source_document": STATE["source_document"],
                                          "bodies": rows})
        if difference:
            raise RuntimeError("The user source changed after capture: " + name)
    return {"source_bodies": len(rows), "all_original_definition_differences_zero": True}
