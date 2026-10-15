"""Physical 2.5 mm hob-rim opening study, isolated from the user's live model."""

import datetime
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "sparkshift_opening_v14"
STATE = {}
CAM = "PRINT_DIRECT_CAM"
BACK = "PRINT_motor_mount"
FRONT = "PRINT_000_outer_shell_of_extruder_1"
REAR_ARM = "PRINT_carrier_box_left"
FRONT_ARM = "PRINT_arm_front_half"


def load(name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def require_owned(app):
    if not STATE or app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate only the owned larger-opening study")


def bodies(app):
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    return {b.name: b for b in load("pancake_paths_study").proxies(root)}


def capture(app):
    if STATE:
        raise RuntimeError("The larger-opening study is already initialized")
    OUT.mkdir(exist_ok=True)
    (OUT / "cad").mkdir(exist_ok=True)
    source_document = app.activeDocument
    source = adsk.fusion.Design.cast(app.activeProduct)
    if source is None:
        raise RuntimeError("The current user document is not a Fusion design")
    by = bodies(app)
    physical = {name: body for name, body in by.items()
                if not name.startswith("MOTION_ONLY_")}
    if len(physical) != 143:
        raise RuntimeError("The expected current physical body inventory has changed")
    manager = adsk.fusion.TemporaryBRepManager.get()
    before = {name: manager.copy(body.nativeObject or body)
              for name, body in physical.items()}
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUT / "cad" / ("Input_before_2p5mm_opening_" + stamp + ".f3d")
    if not source.exportManager.execute(
            source.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("The user's current native model could not be preserved")
    receipt = {
        "input_path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size, "source_document": source_document.name,
        "source_creation_id": source_document.creationId,
        "target_minimum_rim_gap_mm": 2.5,
        "user_current_pose_preserved_in_input": True,
        "physical_body_count": len(before), "all_body_count": len(by),
    }
    write("opening_input_capture.json", receipt)
    options = app.importManager.createFusionArchiveImportOptions(str(path))
    document = app.importManager.importToNewDocument(options)
    if document is None or document == source_document:
        raise RuntimeError("The separate larger-opening document was not created")
    document.name = "SparkShift v14 - 2.5 mm opening WIP"
    STATE.update(document=document.creationId, before=before,
                 source_document=source_document.creationId,
                 input_path=str(path), input_sha256=receipt["sha256"],
                 target_gap_mm=2.5)
    receipt["owned_document"] = document.creationId
    write("opening_input_capture.json", receipt)
    return receipt


def close_owned_pose(app):
    require_owned(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    for name in ("J_C", "J_CAM"):
        root.joints.itemByName(name).isLocked = False
        root.joints.itemByName(name).jointMotion.rotationLimits.isRestValueEnabled = False
    root.joints.itemByName("J_SC").isSuppressed = True
    root.motionLinks.itemByName("CLAMPED_HOB_14_37").isSuppressed = True
    current = math.degrees(root.joints.itemByName("J_CAM").jointMotion.rotationValue)
    targets = [float(math.floor(current)), *range(math.floor(current)-1, -1, -1)]
    for target in targets:
        root.joints.itemByName("J_CAM").jointMotion.rotationValue = math.radians(target)
        if abs(math.degrees(root.joints.itemByName("J_CAM").jointMotion.rotationValue)
               - target) > 1e-6:
            raise RuntimeError("The copied model did not return through its existing cam path")
    return {"cam_degrees": math.degrees(root.joints.itemByName("J_CAM").jointMotion.rotationValue)}


def outer_profile(body, top=.92):
    faces = [f for f in body.faces
             if abs(f.boundingBox.minPoint.y-top) < 1e-6
             and abs(f.boundingBox.maxPoint.y-top) < 1e-6]
    if not faces:
        raise RuntimeError("No physical cam working-land top face was found")
    face = max(faces, key=lambda f: f.area)
    loop = next(loop for loop in face.loops if loop.isOuter)
    points = []
    for coedge in loop.coEdges:
        edge = coedge.edge
        ok, start, end = edge.evaluator.getParameterExtents()
        if not ok:
            raise RuntimeError("Cam profile edge parameters are unavailable")
        ok, strokes = edge.evaluator.getStrokes(start, end, 1e-5)
        if not ok or len(strokes) < 2:
            raise RuntimeError("The cam profile could not be sampled")
        if points:
            if strokes[-1].distanceTo(points[-1]) < strokes[0].distanceTo(points[-1]):
                strokes.reverse()
            if strokes[0].distanceTo(points[-1]) > 1e-6:
                raise RuntimeError("The cam working contour is not connected")
            points.extend(strokes[1:])
        else:
            vertex = edge.endVertex if coedge.isOpposedToEdge else edge.startVertex
            if strokes[-1].distanceTo(vertex.geometry) < strokes[0].distanceTo(vertex.geometry):
                strokes.reverse()
            points.extend(strokes)
    if points[-1].distanceTo(points[0]) > 1e-6:
        raise RuntimeError("The cam working contour is not closed")
    return [[p.x*10, p.z*10] for p in points]


def extract_design_input(app):
    require_owned(app)
    before = STATE["before"]
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    pivot = root.joints.itemByName("J_C").geometryOrOriginTwo.origin
    cam_centre = root.joints.itemByName("J_CAM").geometryOrOriginTwo.origin
    centres = {}
    for name in ("STOCK_003_extrude_wheel_1", "STOCK_038_extrude_wheel_1"):
        torus = next(adsk.core.Torus.cast(f.geometry) for f in before[name].faces
                     if adsk.core.Torus.cast(f.geometry))
        centres[name] = [torus.origin.x*10, torus.origin.z*10]
    follower = next(adsk.core.Cylinder.cast(f.geometry)
                    for f in before["CAM_FOLLOWER_623"].faces
                    if adsk.core.Cylinder.cast(f.geometry)
                    and abs(adsk.core.Cylinder.cast(f.geometry).radius-.5) < 1e-7)
    result = {
        "source_sha256": STATE["input_sha256"], "target_rim_gap_mm": 2.5,
        "outline_xz_mm": outer_profile(before[CAM]),
        "cam_centre_xz_mm": [cam_centre.x*10, cam_centre.z*10],
        "pivot_xz_mm": [pivot.x*10, pivot.z*10],
        "follower_xz_mm": [follower.origin.x*10, follower.origin.z*10],
        "follower_radius_mm": follower.radius*10,
        "fixed_hob_xz_mm": centres["STOCK_003_extrude_wheel_1"],
        "moving_hob_xz_mm": centres["STOCK_038_extrude_wheel_1"],
        "hob_rim_radius_mm": 9.,
        "cam_range_degrees": [0, 155],
        "cam_added_material_y_mm": [4.85, 9.2],
        "profile_stroke_tolerance_mm": .0001,
    }
    write("physical_opening_design_input.json", result)
    return {k: v for k, v in result.items() if k != "outline_xz_mm"}


def prism(app, points, y0, y1):
    require_owned(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    if math.dist(points[0], points[-1]) < 1e-7:
        points = points[:-1]
    occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occurrence.component.name = "TEMP_V14_PROFILE_PRISM"
    sketch = occurrence.component.sketches.add(occurrence.component.xZConstructionPlane)
    sketch.isComputeDeferred = True
    try:
        first = previous = None
        for index in range(len(points)):
            a = sketch.modelToSketchSpace(
                adsk.core.Point3D.create(points[index][0]/10, 0, points[index][1]/10))
            b = sketch.modelToSketchSpace(adsk.core.Point3D.create(
                points[(index+1) % len(points)][0]/10, 0,
                points[(index+1) % len(points)][1]/10))
            line = sketch.sketchCurves.sketchLines.addByTwoPoints(
                previous or a, first if index == len(points)-1 else b)
            if first is None:
                first = line.startSketchPoint
            previous = line.endSketchPoint
    finally:
        sketch.isComputeDeferred = False
    if sketch.profiles.count != 1:
        raise RuntimeError("The physical cam polygon did not form one native profile")
    extrude = occurrence.component.features.extrudeFeatures.addSimple(
        sketch.profiles.item(0), adsk.core.ValueInput.createByReal((y1-y0)/10),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    if extrude.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError("Physical cam prism extrusion failed: "
                           + extrude.errorOrWarningMessage)
    manager = adsk.fusion.TemporaryBRepManager.get()
    shape = manager.copy(extrude.bodies.item(0))
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = adsk.core.Vector3D.create(
        0, (y0+y1)/20-(shape.boundingBox.minPoint.y+shape.boundingBox.maxPoint.y)/2, 0)
    if not manager.transform(shape, matrix):
        raise RuntimeError("The physical cam prism placement failed")
    design.activateRootComponent()
    if not occurrence.deleteMe():
        raise RuntimeError("The owned temporary prism component was not removed")
    return shape


def prepare_cam(app):
    require_owned(app)
    if "candidate_cam" in STATE:
        raise RuntimeError("The physical cam candidate is already prepared")
    spec = json.loads((OUT / "physical_cam_candidate.json").read_text())
    if spec["source_sha256"] != STATE["input_sha256"]:
        raise RuntimeError("The new physical cam profile is not bound to this input")
    s = load("pancake_paths_study")
    manager = s.tbm()
    y0, y1 = spec["added_material_y_mm"]
    cx, cz = spec["cam_centre_xz_mm"]
    outer = prism(app, spec["new_outer_prism_xz_mm"], y0, y1)
    annulus = manager.copy(outer)
    s.op(annulus, s.cyl(cx, cz, y0-.1, y1+.1,
                      spec["unchanged_inner_radius_mm"]), "cut")
    cam = manager.copy(STATE["before"][CAM])
    s.op(cam, annulus, "join")
    if not cam.isSolid or cam.lumps.count != 1 or not math.isfinite(cam.volume):
        raise RuntimeError("The enlarged physical cam is not one valid solid")
    delta = manager.copy(cam)
    s.op(delta, STATE["before"][CAM], "cut")
    removed = manager.copy(STATE["before"][CAM])
    s.op(removed, cam, "cut")
    if removed.lumps.count and removed.volume*1000 > 1e-7:
        raise RuntimeError("The physical cam enlargement removed original geometry")
    protected = s.cyl(cx, cz, -.1, 20, spec["unchanged_inner_radius_mm"]-.0001)
    changed_core, _ = s.common_volume(delta, protected)
    if changed_core > 1e-7:
        raise RuntimeError("The horn/journal/retainer core changed")
    STATE["candidate_cam"] = cam
    STATE["cam_addition"] = annulus
    write("native_physical_cam_candidate.json", {
        "native_volume_mm3": cam.volume*1000,
        "added_volume_mm3": delta.volume*1000,
        "original_removed_mm3": removed.volume*1000 if removed.lumps.count else 0.,
        "protected_core_change_mm3": changed_core,
        "added_material_bounds_mm": [
            [v*10 for v in delta.boundingBox.minPoint.asArray()],
            [v*10 for v in delta.boundingBox.maxPoint.asArray()]],
        "physical_cam_not_yet_applied": True,
        "one_valid_native_solid": True,
    })
    return {"added_volume_mm3": delta.volume*1000,
            "native_cam_faces": cam.faces.count,
            "new_outer_profile_points": len(outer_profile(cam))}


def prepare_clearance(app):
    require_owned(app)
    if "case_candidates" in STATE:
        raise RuntimeError("The larger-swing clearance candidates are already prepared")
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    manager = s.tbm()
    before = STATE["before"]
    pivot = tuple(json.loads((OUT / "physical_opening_design_input.json").read_text())
                  ["pivot_xz_mm"])
    rear = manager.copy(before[REAR_ARM])
    s.op(rear, s.cyl(8, -13.3, 9.5, 11.8, 3.45), "cut")
    bolt_name = "ARM_LOWER_M3x14_BUTTON_HEAD"
    bolt = m.translated(before[bolt_name], dy=.4)

    protected = s.cyl(18.2, -13.7, 6., 10., 4.)
    cap = s.cyl(18.2, -13.7, 10., 31.5, 3.25)
    s.op(protected, cap, "join")
    s.op(protected, before[BACK], "common")
    expanded = m.grown(protected, .17)
    for dy in (-.15, .15):
        s.op(expanded, m.translated(protected, dy=dy), "join")
    lower_only = s.cyl(8, -13.3, 9.5, 11.75, 4.1)
    for angle in (-7.5, -7.75, -8.):
        tool = m.rotated(expanded, pivot, -angle)
        s.op(tool, lower_only, "common")
        if tool.lumps.count:
            s.op(rear, tool, "cut")
    if not rear.isSolid or rear.lumps.count != 1:
        raise RuntimeError("The local lower-seat relief disconnected the rear arm")

    tools = []
    for angle in (-7.5, -7.75, -8.):
        for name, shape in ((REAR_ARM, rear), (FRONT_ARM, before[FRONT_ARM]),
                            (bolt_name, bolt)):
            posed = m.rotated(shape, pivot, angle)
            tools.append((name, angle, m.grown(posed, .17)))
    cases = {}
    report = {"lower_arm_head_seat_y_mm": 11.8,
              "lower_arm_screw_unchanged": "M3x14 button head",
              "lower_arm_head_top_y_mm": 10.15,
              "lower_arm_screw_tip_y_mm": 25.8,
              "lower_arm_insert_y_mm": [20.5, 24.5],
              "lower_arm_nominal_thread_engagement_mm": 4.,
              "rear_arm_axial_stock_under_head_mm": 15.6-11.8,
              "case_changes": [], "protected_insert_losses": [],
              "remaining_intersections": []}
    for name in (BACK, FRONT):
        case = manager.copy(before[name])
        for _, _, tool in tools:
            s.op(case, tool, "cut")
        if not case.isSolid or case.lumps.count != 1:
            raise RuntimeError("A locally relieved housing is not one solid: " + name)
        removed = manager.copy(before[name])
        s.op(removed, case, "cut")
        report["case_changes"].append(
            {"part": name, "removed_mm3": removed.volume*1000 if removed.lumps.count else 0.})
        for insert_name in ("CLAM_M3_FRAME_INSERT_0", "CLAM_M3_FRAME_INSERT_1",
                            "CLAM_M3_FRAME_INSERT_2", "CLAM_M3_FRAME_INSERT_3"):
            box = before[insert_name].boundingBox
            cx = (box.minPoint.x+box.maxPoint.x)*5
            cz = (box.minPoint.z+box.maxPoint.z)*5
            y0, y1 = box.minPoint.y*10, box.maxPoint.y*10
            region = s.cyl(cx, cz, y0, y1, 4.)
            loss, _ = s.common_volume(removed, region)
            report["protected_insert_losses"].append(
                {"part": name, "insert": insert_name, "removed_mm3": loss})
            if loss > 1e-6:
                write("larger_swing_clearance_candidates.json", report)
                raise RuntimeError("The proposed relief removes required case-insert stock")
        if name == BACK:
            region = s.cyl(18.2, -13.7, 10., 11.6, 3.25)
            loss, _ = s.common_volume(removed, region)
            if loss > 1e-6:
                raise RuntimeError("The lower case-insert backing/shank land changed")
        cases[name] = case
    for angle in (-7., -7.5, -7.85, -8.):
        for name, shape in ((REAR_ARM, rear), (FRONT_ARM, before[FRONT_ARM]),
                            (bolt_name, bolt)):
            posed = m.rotated(shape, pivot, angle)
            for case_name, case in cases.items():
                volume, _ = s.common_volume(posed, case)
                if volume > 1e-5:
                    report["remaining_intersections"].append(
                        {"angle": angle, "moving": name, "case": case_name,
                         "overlap_mm3": volume})
    for name, shape in ((REAR_ARM, rear), (FRONT_ARM, before[FRONT_ARM])):
        value, _ = s.common_volume(bolt, shape)
        if value > 1e-5:
            report["remaining_intersections"].append(
                {"moving": bolt_name, "part": name, "overlap_mm3": value})
    write("larger_swing_clearance_candidates.json", report)
    if report["remaining_intersections"]:
        raise RuntimeError("The bounded larger-swing clearance candidate still interferes")
    STATE.update(case_candidates=cases, rear_arm_candidate=rear,
                 lower_bolt_candidate=bolt, clearance_tools=tools)
    return report


def protect_front_interfaces(app):
    require_owned(app)
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    manager = s.tbm()
    before = STATE["before"]
    pivot = (9.5, 13.0999827910455)
    local_case = manager.copy(before[FRONT])
    s.op(local_case, s.box(5, 16, 26.5, 30.2, 32, 40), "common")
    if not local_case.lumps.count:
        raise RuntimeError("The reviewed upper-arm case corner is missing")
    local_case = m.grown(local_case, .17)
    front = manager.copy(before[FRONT_ARM])
    limit = s.box(7, 20, 26.5, 30.1, 33, 40)
    for angle in (-7.5, -7.75, -8.):
        tool = m.rotated(local_case, pivot, -angle)
        s.op(tool, limit, "common")
        if tool.lumps.count:
            s.op(front, tool, "cut")
    if not front.isSolid or front.lumps.count != 1:
        raise RuntimeError("The local upper-corner clearance disconnected the front arm")
    removed_front = manager.copy(before[FRONT_ARM])
    s.op(removed_front, front, "cut")
    protected_upper = s.cyl(14.95, 31.4, 15.6, 21.2, 4.)
    upper_loss, _ = s.common_volume(removed_front, protected_upper)
    if upper_loss > 1e-7:
        raise RuntimeError("The upper arm clamp insert/backing stock changed")
    tools = []
    for name, angle, tool in STATE["clearance_tools"]:
        if name == FRONT_ARM:
            tool = m.grown(m.rotated(front, pivot, angle), .17)
        tools.append((name, angle, tool))
    cases = {}
    for name in (BACK, FRONT):
        case = manager.copy(before[name])
        for _, _, tool in tools:
            s.op(case, tool, "cut")
        cases[name] = case

    delta_cam = manager.copy(STATE["candidate_cam"])
    s.op(delta_cam, before[CAM], "cut")
    cam_tools = []
    for angle in range(0, 156, 5):
        posed = m.rotated(delta_cam, (10.5, 50.72059521522819), angle)
        for name, case in cases.items():
            overlap, _ = s.common_volume(posed, case)
            near = (overlap > 0 or
                    app.measureManager.measureMinimumDistance(posed, case).value*10 < .18)
            if near:
                tool = m.grown(posed, .17)
                s.op(case, tool, "cut")
                cam_tools.append({"case": name, "cam_deg": angle,
                                  "physical_overlap_before_mm3": overlap})
    losses = []
    for name, body in before.items():
        box = body.boundingBox
        if name.startswith("OCT_RECEIVER_MAGNET"):
            low, high = box.minPoint, box.maxPoint
            region = s.box(low.x*10, high.x*10, low.y*10-1.6, low.y*10,
                           low.z*10, high.z*10)
        elif name.startswith("OCT_LOCATOR_PIN"):
            low, high = box.minPoint, box.maxPoint
            region = s.box(low.x*10-1.6, high.x*10+1.6,
                           low.y*10-1.6, high.y*10+1.6,
                           low.z*10-1.6, high.z*10+1.6)
        else:
            continue
        for case_name, after in cases.items():
            removed = manager.copy(before[case_name])
            s.op(removed, after, "cut")
            loss, _ = s.common_volume(removed, region)
            if loss > 1e-6:
                losses.append({"case": case_name, "interface": name,
                               "support_removed_mm3": loss})
    report = {"front_arm_corner_removed_mm3": removed_front.volume*1000,
              "upper_arm_insert_backing_loss_mm3": upper_loss,
              "cam_clearance_tools": cam_tools, "interface_support_losses": losses,
              "case_removed_mm3": {name: (before[name].volume-case.volume)*1000
                                   for name, case in cases.items()}}
    write("protected_interface_clearance_candidates.json", report)
    if losses:
        raise RuntimeError("The bounded clearance changes still alter interface support")
    if any(not case.isSolid or case.lumps.count != 1 for case in cases.values()):
        raise RuntimeError("A protected housing clearance candidate is not one solid")
    STATE.update(case_candidates=cases, front_arm_candidate=front, clearance_tools=tools)
    return report


def clear_cam_from_rear_arm(app):
    require_owned(app)
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    before = STATE["before"]
    rear = s.tbm().copy(STATE["rear_arm_candidate"])
    cam_delta = s.tbm().copy(STATE["candidate_cam"])
    s.op(cam_delta, before[CAM], "cut")
    profile = json.loads((OUT / "physical_cam_candidate.json").read_text())
    angles = {p["cam_deg"]: p["arm_deg"] for p in profile["physical_motion"]}
    region = s.box(7, 22, 4.7, 9.35, 37, 48)
    changed = []
    for phi in range(0, 156, 5):
        world = m.rotated(cam_delta, (10.5, 50.72059521522819), phi)
        local = m.rotated(world, (9.5, 13.0999827910455), -angles[float(phi)])
        overlap, _ = s.common_volume(local, rear)
        near = (overlap > 0 or
                app.measureManager.measureMinimumDistance(local, rear).value*10 < .18)
        if not near:
            continue
        tool = m.grown(local, .17)
        for dy in (-.15, .15):
            s.op(tool, m.translated(local, dy=dy), "join")
        s.op(tool, region, "common")
        if tool.lumps.count:
            volume = rear.volume
            s.op(rear, tool, "cut")
            if volume-rear.volume > 1e-10:
                changed.append({"cam_deg": phi, "removed_mm3": (volume-rear.volume)*1000})
    if not rear.isSolid or rear.lumps.count != 1:
        raise RuntimeError("The cam-window clearance disconnected the rear arm")
    delta = s.tbm().copy(STATE["rear_arm_candidate"])
    s.op(delta, rear, "cut")
    follower_stock = s.cyl(3, 43.22059521522819, 2.5, 15.6, 5.5)
    follower_loss, _ = s.common_volume(delta, follower_stock)
    if follower_loss > 1e-6:
        raise RuntimeError("The cam-window clearance changes the bearing/fork support")
    upper_stock = s.cyl(14.95, 31.4, 7., 21.2, 4.)
    upper_loss, _ = s.common_volume(delta, upper_stock)
    if upper_loss > 1e-6:
        raise RuntimeError("The cam-window clearance changes the upper clamp support")
    STATE["rear_arm_candidate"] = rear
    report = {"local_cam_window_cuts": changed,
              "bearing_and_fork_support_removed_mm3": follower_loss,
              "upper_clamp_support_removed_mm3": upper_loss,
              "one_connected_rear_arm": True}
    write("rear_arm_cam_window_clearance.json", report)
    return report


def exact_difference(first, second):
    manager = adsk.fusion.TemporaryBRepManager.get()
    helper = STATE.get("exact_readback_helper")
    if helper is None:
        helper = sys.modules["sparkshift_corruption_v11"].STATE["exact_readback_helper"]
    diagnostics = []

    def volume(body):
        value = body.volume*1000
        if not math.isfinite(value) or value < 0:
            raise RuntimeError("Invalid native geometry-comparison volume")
        return value

    return (helper.exact_native_difference(manager, first, second, volume, diagnostics)
            + helper.exact_native_difference(manager, second, first, volume, diagnostics))


def append_boolean(app, name, tool, operation, label, expected):
    require_owned(app)
    manager = adsk.fusion.TemporaryBRepManager.get()
    proxy = bodies(app)[name]
    native = proxy.nativeObject or proxy
    component = native.parentComponent
    if component.bRepBodies.count != 1:
        raise RuntimeError("Unrelated construction bodies are present in " + name)
    feature = component.features.baseFeatures.add()
    feature.name = label + " tools"
    if not feature.startEdit():
        raise RuntimeError("Could not edit the bounded geometry tools")
    try:
        for lump in tool.lumps:
            component.bRepBodies.add(manager.copy(lump), feature)
    finally:
        if not feature.finishEdit():
            raise RuntimeError("Could not finish the bounded geometry tools")
    adsk.doEvents()
    tools = adsk.core.ObjectCollection.create()
    for index, body in enumerate(feature.bodies):
        body.name = label + " tool " + str(index)
        tools.add(body)
    if tools.count != tool.lumps.count:
        raise RuntimeError("The native geometry tool inventory is incomplete")
    target = component.bRepBodies.itemByName(name)
    inp = component.features.combineFeatures.createInput(target, tools)
    inp.operation = (adsk.fusion.FeatureOperations.JoinFeatureOperation
                     if operation == "join" else adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.isKeepToolBodies = False
    result = component.features.combineFeatures.add(inp)
    result.name = label
    if result.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError("Native geometry edit failed: " + result.errorOrWarningMessage)
    actual = bodies(app)[name].nativeObject
    if not actual.isSolid or actual.lumps.count != 1 or actual.volume <= 0:
        raise RuntimeError("The changed native physical part is invalid: " + name)
    difference = exact_difference(expected, manager.copy(actual))
    if difference:
        raise RuntimeError("The appended native edit differs from its reviewed candidate: "
                           + name + " / " + str(difference))
    STATE.setdefault("applied", []).append(name)
    write("native_applied_parts.json", {"parts": STATE["applied"]})
    return {"part": name, "volume_mm3": actual.volume*1000,
            "exact_candidate_difference_mm3": difference}


def apply_physical_parts(app):
    require_owned(app)
    if STATE.get("applied"):
        raise RuntimeError("Physical edits have already started; inspect their progress")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    relation = root.tangentRelationships.itemByName("SWING_ARM_CAM_ANIMATION_GUIDE")
    if relation:
        relation.isSuppressed = True
    before = STATE["before"]
    manager = adsk.fusion.TemporaryBRepManager.get()
    s = load("pancake_paths_study")
    result = [append_boolean(app, CAM, STATE["cam_addition"], "join",
                             "V14 physical 2.5 mm release lobe", STATE["candidate_cam"])]
    expected_parts = {
        BACK: STATE["case_candidates"][BACK],
        FRONT: STATE["case_candidates"][FRONT],
        REAR_ARM: STATE["rear_arm_candidate"],
        FRONT_ARM: STATE["front_arm_candidate"],
    }
    for name, expected in expected_parts.items():
        tool = manager.copy(before[name])
        s.op(tool, expected, "cut")
        if tool.lumps.count:
            result.append(append_boolean(app, name, tool, "cut",
                                         "V14 bounded larger-swing clearance", expected))
    name = "ARM_LOWER_M3x14_BUTTON_HEAD"
    body = bodies(app)[name].nativeObject
    collection = adsk.core.ObjectCollection.create()
    collection.add(body)
    inp = body.parentComponent.features.moveFeatures.createInput2(collection)
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = adsk.core.Vector3D.create(0, .04, 0)
    if not inp.defineAsFreeMove(matrix):
        raise RuntimeError("The lower clamp-head reference move could not be defined")
    move = body.parentComponent.features.moveFeatures.add(inp)
    move.name = "V14 lower M3x14 head seat forward 0.40 mm"
    if move.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError("The lower clamp-head move failed: " + move.errorOrWarningMessage)
    difference = exact_difference(STATE["lower_bolt_candidate"],
                                  manager.copy(bodies(app)[name].nativeObject))
    if difference:
        raise RuntimeError("The existing M3x14 screw was not moved rigidly to its new seat")
    STATE["applied"].append(name)
    root.joints.itemByName("J_C").jointMotion.rotationLimits.minimumValue = math.radians(-8)
    root.joints.itemByName("J_C").jointMotion.rotationLimits.isMinimumValueEnabled = True
    physical = json.loads((OUT / "physical_opening_design_input.json").read_text())
    physical["outline_xz_mm"] = outer_profile(bodies(app)[CAM].nativeObject)
    physical["arm_range_deg"] = [-8., 1.]
    physical["cam_range_deg"] = [0., 155.]
    physical["follower_radius_mm"] = 5.
    write("frozen_cam_profile.json", physical)
    write("native_applied_parts.json",
          {"parts": STATE["applied"], "hardware_lengths_changed": False,
           "original_history_retained_and_only_downstream_features_appended": True})
    return result


def verify_parts(app):
    require_owned(app)
    by = bodies(app)
    expected = {
        CAM: STATE["candidate_cam"], BACK: STATE["case_candidates"][BACK],
        FRONT: STATE["case_candidates"][FRONT], REAR_ARM: STATE["rear_arm_candidate"],
        FRONT_ARM: STATE["front_arm_candidate"],
        "ARM_LOWER_M3x14_BUTTON_HEAD": STATE["lower_bolt_candidate"],
    }
    rows = []
    manager = adsk.fusion.TemporaryBRepManager.get()
    for name, before in STATE["before"].items():
        actual = manager.copy(by[name].nativeObject or by[name])
        if not actual.isSolid or actual.lumps.count != 1 or actual.volume <= 0:
            raise RuntimeError("An original physical part is no longer one solid: " + name)
        difference = exact_difference(expected.get(name, before), actual)
        rows.append({"part": name, "intended_change": name in expected,
                     "exact_expected_difference_mm3": difference})
        write("native_part_verification.json", {"parts": rows})
        if difference:
            raise RuntimeError("A physical part differs from the bounded revision: " + name)
    extras = set(by)-set(STATE["before"])
    if extras != {"MOTION_ONLY_CAM_GUIDE", "MOTION_ONLY_FOLLOWER_REFERENCE"}:
        raise RuntimeError("Unexpected construction or duplicate bodies remain")
    return {"physical_parts": len(rows), "untouched_definitions_exact_unchanged": 137,
            "intentionally_updated_parts": list(expected), "non_printing_references": 2}


def export_changed_parts(app, names=None):
    require_owned(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    folder = OUT / "validation"
    folder.mkdir(exist_ok=True)
    by = bodies(app)
    rows = []
    for name in names or (CAM, BACK, FRONT, REAR_ARM, FRONT_ARM):
        body = by[name]
        states = []
        occurrence = body.assemblyContext
        while occurrence:
            states.append((occurrence, occurrence.isLightBulbOn))
            occurrence.isLightBulbOn = True
            occurrence = occurrence.assemblyContext
        old_light = body.isLightBulbOn
        body.isLightBulbOn = True
        try:
            step = folder / (name + ".step")
            if not design.exportManager.execute(
                    design.exportManager.createSTEPExportOptions(str(step),
                                                                 (body.nativeObject or body)
                                                                 .parentComponent)):
                raise RuntimeError("Native changed-part STEP export failed: " + name)
            stl = folder / (name + ".stl")
            options = design.exportManager.createSTLExportOptions(
                body.nativeObject or body, str(stl))
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementCustom
            options.surfaceDeviation = .0003
            options.normalDeviation = 4.
            options.maximumEdgeLength = .5
            options.aspectRatio = 21.5
            options.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
            options.isBinaryFormat = True
            options.sendToPrintUtility = False
            if not design.exportManager.execute(options) or stl.stat().st_size <= 84:
                raise RuntimeError("Native changed-part STL export failed: " + name)
            rows.append({"part": name, "step": str(step), "stl": str(stl),
                         "native_volume_mm3": (body.nativeObject or body).volume*1000})
        finally:
            body.isLightBulbOn = old_light
            for occurrence, light in reversed(states):
                occurrence.isLightBulbOn = light
    write("changed_part_exports.json",
          {"parts": rows, "orientation": "As-designed; geometry validation, not print-bed setup",
           "mesh_repair_or_face_deletion": False})
    return rows
