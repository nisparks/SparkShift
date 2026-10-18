"""Review and reinforce only the current user-cleaned yellow receiver half."""

import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

import adsk.core
import adsk.fusion


OUT = Path(__file__).resolve().parent / "sparkshift_front_half_only_v21"
TARGET = "PRINT_000_outer_shell_of_extruder_1"
STATE = {}
MOVING = {"05", "07", "09", "10", "11"}


def tools():
    return sys.modules["sparkshift_open_frame_v19"]


def geometry():
    return tools().geometry()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def inventory(design):
    rows = [body for occurrence in design.rootComponent.allOccurrences
            for body in occurrence.bRepBodies]
    if len(rows) != len({body.name for body in rows}):
        raise RuntimeError("The current physical body names are not unique")
    by = {}
    empty = {}
    for body in rows:
        if body.lumps.count:
            by[body.name] = body
        elif body.faces.count or body.edges.count or body.volume:
            raise RuntimeError("Unresolved nonphysical geometry: " + body.name)
        else:
            empty[body.name] = "empty nonphysical history record retained"
    return by, empty


def exact(first, second, label):
    s, _ = geometry()
    errors = []
    for angle in (0.0, 7.0, 90.0):
        a, b = s.tbm().copy(first), s.tbm().copy(second)
        if angle:
            axis = adsk.core.Vector3D.create(1, 2, 3)
            axis.normalize()
            matrix = adsk.core.Matrix3D.create()
            matrix.setToRotation(math.radians(angle), axis, adsk.core.Point3D.create())
            if not s.tbm().transform(a, matrix) or not s.tbm().transform(b, matrix):
                raise RuntimeError("The common geometry-comparison frame failed")
        try:
            delta = tools().STATE["native"].exact_difference(a, b)
        except RuntimeError as error:
            if not any(code in str(error) for code in
                       ("ASM_BODY_VERTEX_CRUMBLE", "ASM_INCONS_FACE", "ASM_NOT_HANDLED")):
                raise
            errors.append({"angle_deg": angle, "kernel_error": str(error)})
            write("comparison_diagnostics.json", {"label": label, "errors": errors})
            continue
        if errors or angle:
            STATE.setdefault("comparison_frames", []).append({
                "label": label, "common_frame_deg": angle, "exact_difference_mm3": delta,
                "errors_before_success": errors, "healing_not_called": True})
            write("comparison_frames.json", STATE["comparison_frames"])
        return delta
    raise RuntimeError("Native comparison is inconclusive, not equality: " + label)


def capture(app, ui):
    if STATE:
        raise RuntimeError("The front-half input was already preserved")
    if ui.activeCommand != "SelectCommand":
        raise RuntimeError("Finish the current native command before preserving the cleaned front half")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by, empty = inventory(design)
    if TARGET not in by:
        raise RuntimeError("The yellow receiver front half is not in the current design")
    source = app.activeDocument
    for directory in (OUT, OUT / "cad", OUT / "images"):
        directory.mkdir(exist_ok=True)
    path = OUT / "cad" / ("USER_cleaned_front_input_" + time.strftime("%Y%m%d_%H%M%S") + ".f3d")
    if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("Could not preserve the complete current user-cleaned input")
    by, empty = inventory(design)
    s, _ = geometry()
    player = tools().STATE["controller"]
    player.validate(design)
    root_frames = {o.name[:2]: o.transform2.copy()
                   for o in design.rootComponent.occurrences if o.name[:2].isdigit()}
    slider = design.rootComponent.joints.itemByName("J_TOOL_Y")
    if slider is None or not hasattr(slider.jointMotion, "slideValue"):
        raise RuntimeError("The existing tool-withdrawal slider is unavailable")
    STATE.update(
        document=source.creationId, source_native=str(path),
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        definitions={name: s.tbm().copy(body.nativeObject) for name, body in by.items()},
        world={name: s.tbm().copy(body) for name, body in by.items()},
        paths={name: body.assemblyContext.fullPathName for name, body in by.items()},
        matrices={name: body.assemblyContext.transform2.copy() for name, body in by.items()},
        root_frames=root_frames, player=player, tool_slide_mm=slider.jointMotion.slideValue * 10,
        empty_history=empty, source_lights={name: body.isLightBulbOn for name, body in by.items()},
        source_camera=app.activeViewport.camera,
    )
    STATE["target_world"] = s.tbm().copy(STATE["world"][TARGET])
    report = {
        "source_document": source.creationId, "source_name": source.name, "input": str(path),
        "input_sha256": STATE["source_sha256"], "physical_bodies": len(by),
        "empty_history": empty, "target": TARGET, "target_stats": tools().stats(
            STATE["definitions"][TARGET]),
        "tool_source_slide_mm": STATE["tool_slide_mm"],
        "only_P03_may_change": True, "other_piece_redesign_explicitly_paused": True,
        "source_pose_not_commanded_or_changed_for_this_capture": True,
        "playback_data_sha256": player.load_data()[1],
    }
    write("input_capture.json", report)
    return report


def pose(angle):
    s, _ = geometry()
    player = STATE["player"]
    data = player.load_data()[0]
    arm = player.arm_angle(data, angle)
    carrier = player.rotation(arm, data["arm_pivot_mm"])
    relative = -data["moving_hob_ratio"] * (data["held_left_compound_deg"] - arm)
    frames = {"10": player.rotation(angle, data["cam_pivot_mm"]), "05": carrier,
              "07": player.compose(carrier, player.rotation(relative, data["moving_hob_axis_mm"])),
              "09": carrier, "11": carrier}
    result = {}
    for name, shape in STATE["world"].items():
        prefix = STATE["paths"][name][:2]
        if prefix in frames:
            transformed = s.tbm().copy(shape)
            inverse = STATE["root_frames"][prefix].copy()
            inverse.invert()
            if not s.tbm().transform(transformed, player.compose(frames[prefix], inverse)):
                raise RuntimeError("A read-only native motion transform failed")
            result[name] = transformed
        else:
            result[name] = shape
    return result


def audit_static(label):
    s, _ = geometry()
    case = STATE["target_world"]
    allowed = {"SPRING_PRELOAD_M3_HEATSET": 1.44}
    contacts, clashes = [], []
    for name, shape in STATE["world"].items():
        if name == TARGET or STATE["paths"][name][:2] in MOVING or name.startswith("REFERENCE_"):
            continue
        volume, common = s.common_volume(case, shape)
        if volume <= 1e-5:
            continue
        row = {"other": name, "overlap_mm3": volume, "bounds_mm": tools().bounds(common)}
        if name in allowed and volume <= allowed[name]:
            row["declared_nominal_insert_installation_contact"] = True
            contacts.append(row)
        else:
            clashes.append(row)
    report = {"input_sha256": STATE["source_sha256"], "target": TARGET,
              "declared_installation_contacts": contacts, "unexpected_clashes": clashes,
              "all_physical_fixed_parts_and_docked_tool_considered": True}
    STATE[label + "_static"] = report
    write(label + "_static_audit.json", report)
    return report


def audit_motion(angles, label):
    s, _ = geometry()
    rows = STATE.setdefault(label + "_motion", [])
    cache = STATE.setdefault(label + "_identical_carrier_contacts", {})
    data = STATE["player"].load_data()[0]
    for angle in angles:
        posed = pose(float(angle))
        arm = STATE["player"].arm_angle(data, float(angle))
        clashes = []
        for name, path in STATE["paths"].items():
            if path[:2] not in MOVING:
                continue
            key = (name, arm) if path[:2] != "10" else (name, float(angle))
            if key not in cache:
                volume, common = s.common_volume(STATE["target_world"], posed[name])
                cache[key] = ({"other": name, "overlap_mm3": volume,
                               "bounds_mm": tools().bounds(common)} if volume > 1e-5 else None)
            if cache[key] is not None:
                clashes.append(cache[key])
        rows.append({"cam_deg": float(angle), "unexpected_clashes": clashes})
        write(label + "_motion_audit.json", {
            "input_sha256": STATE["source_sha256"], "poses": rows,
            "native_BRep_read_only_existing_nominal_FK_path": True,
            "identical_rigid_carrier_poses_reuse_exact_contact_results": True,
            "actual_cam_following_spring_force_and_hardware_endpoints_not_qualified": True})
    return {"recorded_poses": len(rows), "poses_with_clashes":
            sum(bool(row["unexpected_clashes"]) for row in rows)}


def audit_tool_withdrawal(label):
    s, m = geometry()
    tool = {name: m.translated(shape, dy=-STATE["tool_slide_mm"])
            for name, shape in STATE["world"].items() if STATE["paths"][name].startswith("12 ")}
    if not tool:
        raise RuntimeError("The removable tool group is unavailable")
    rows = []
    for offset in range(36):
        clashes = []
        for name, shape in tool.items():
            if name.startswith("REFERENCE_"):
                continue
            volume, common = s.common_volume(STATE["target_world"], m.translated(shape, dy=offset))
            if volume > 1e-5:
                clashes.append({"tool_part": name, "overlap_mm3": volume,
                                "bounds_mm": tools().bounds(common)})
        rows.append({"withdrawal_mm": offset, "unexpected_clashes": clashes})
        write(label + "_tool_audit.json", {"poses": rows, "source_slide_removed_mm":
                                         STATE["tool_slide_mm"], "maximum_withdrawal_mm": 35})
    report = {"sampled_tool_offsets": len(rows),
              "offsets_with_clashes": sum(bool(row["unexpected_clashes"]) for row in rows)}
    STATE[label + "_tool_summary"] = report
    return report


def ray_material(body, world_start, world_direction, nominal_face_distance):
    transform = STATE["matrices"][TARGET]
    inverse = transform.copy()
    inverse.invert()
    start = adsk.core.Point3D.create(*(v / 10 for v in world_start))
    local_start = start.copy()
    local_start.transformBy(inverse)
    direction = adsk.core.Vector3D.create(*world_direction)
    local_direction = direction.copy()
    local_direction.transformBy(inverse)
    hits = adsk.core.ObjectCollection.create()
    body.parentComponent.findBRepUsingRay(
        local_start, local_direction, adsk.fusion.BRepEntityTypes.BRepFaceEntityType,
        -1.0, False, hits)
    distances = [0.0]
    for i in range(hits.count):
        point = hits.item(i).copy()
        point.transformBy(transform)
        distance = start.vectorTo(point).dotProduct(direction) * 10
        if distance > 1e-6 and all(abs(distance - old) > 1e-5 for old in distances):
            distances.append(distance)
    distances.append(100.0)
    distances.sort()
    intervals = []
    inside = {adsk.fusion.PointContainment.PointInsidePointContainment,
              adsk.fusion.PointContainment.PointOnPointContainment}
    for first, last in zip(distances, distances[1:]):
        mid = adsk.core.Point3D.create(*((world_start[i] + world_direction[i] *
                                         (first + last) / 2) / 10 for i in range(3)))
        mid.transformBy(inverse)
        if body.pointContainment(mid) in inside:
            intervals.append([first, last])
    nearby = next((row for row in intervals if row[0] <= nominal_face_distance + .35), None)
    if nearby is None:
        return {"wall_mm": 0.0, "exposed": True, "first_material_intervals_mm": intervals[:3]}
    return {"wall_mm": nearby[1] - nearby[0], "exposed": False,
            "pocket_entry_distance_mm": nearby[0], "first_material_intervals_mm": intervals[:3]}


def measure_top_magnets(app, label, body=None):
    if body is None:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if app.activeDocument.creationId != STATE["document"]:
            raise RuntimeError("Activate the preserved front-half document for local wall measurement")
        by, _ = inventory(design)
        body = by[TARGET].nativeObject
    rows = []
    for name in ("OCT_RECEIVER_MAGNET_0", "OCT_RECEIVER_MAGNET_2"):
        box = STATE["world"][name].preciseBoundingBox
        lo, hi = [v * 10 for v in box.minPoint.asArray()], [v * 10 for v in box.maxPoint.asArray()]
        middle = [(a + b) / 2 for a, b in zip(lo, hi)]
        inner_sign = 1.0 if middle[0] < 0 else -1.0
        for fx in (.2, .5, .8):
            for fz in (.05, .2, .5, .8, .95):
                start = [lo[0] + fx * (hi[0] - lo[0]), middle[1],
                         lo[2] + fz * (hi[2] - lo[2])]
                row = ray_material(body, start, (0, -1, 0), middle[1] - lo[1])
                rows.append({"magnet": name, "wall": "backing", "point_mm": start, **row})
        for fy in (.1, .5, .8):
            for fz in (.05, .2, .5, .8, .95):
                start = [middle[0], lo[1] + fy * (hi[1] - lo[1]), lo[2] + fz * (hi[2] - lo[2])]
                row = ray_material(body, start, (inner_sign, 0, 0), (hi[0] - lo[0]) / 2)
                rows.append({"magnet": name, "wall": "inner side", "point_mm": start, **row})
        for fx in (.2, .5, .8):
            for fy in (.1, .5, .8):
                start = [lo[0] + fx * (hi[0] - lo[0]), lo[1] + fy * (hi[1] - lo[1]), middle[2]]
                row = ray_material(body, start, (0, 0, 1), hi[2] - middle[2])
                rows.append({"magnet": name, "wall": "top cap", "point_mm": start, **row})
    summary = []
    for name in ("OCT_RECEIVER_MAGNET_0", "OCT_RECEIVER_MAGNET_2"):
        for wall in ("backing", "inner side", "top cap"):
            selected = [row for row in rows if row["magnet"] == name and row["wall"] == wall]
            values = [row["wall_mm"] for row in selected]
            summary.append({"magnet": name, "wall": wall, "samples": len(values),
                            "minimum_wall_mm": min(values), "median_wall_mm": statistics.median(values),
                            "exposed_samples": sum(row["exposed"] for row in selected)})
    report = {"target": TARGET, "sample_count": len(rows), "summary": summary, "samples": rows,
              "working_magnetic_front_faces_intentionally_not_capped_or_counted_as_walls": True}
    write(label + "_magnet_walls.json", report)
    return report


def measure_outer_magnets(app, label, body=None):
    if body is None:
        if app.activeDocument.creationId != STATE["document"]:
            raise RuntimeError("Activate the preserved assembly for outer-wall measurement")
        by, _ = inventory(adsk.fusion.Design.cast(app.activeProduct))
        body = by[TARGET].nativeObject
    rows = []
    summary = []
    for name in ("OCT_RECEIVER_MAGNET_0", "OCT_RECEIVER_MAGNET_2"):
        lo, hi = tools().bounds(STATE["world"][name])
        middle = [(a + b) / 2 for a, b in zip(lo, hi)]
        sign = -1 if middle[0] < 0 else 1
        samples = []
        support_y = [lo[1] + fraction * (hi[1] - lo[1]) for fraction in (.1, .5, .8)]
        support_y.append(31.45)
        for y in support_y:
            for fz in (.05, .2, .5, .8, .95, .999):
                point = [middle[0], y, lo[2] + fz * (hi[2] - lo[2])]
                samples.append({"point_mm": point, **ray_material(
                    body, point, (sign, 0, 0), (hi[0] - lo[0]) / 2)})
        rows.append({"magnet": name, "samples": samples})
        summary.append({"magnet": name, "sample_count": len(samples),
                        "minimum_outer_wall_mm": min(row["wall_mm"] for row in samples),
                        "median_outer_wall_mm": statistics.median(row["wall_mm"] for row in samples),
                        "exposed_samples": sum(row["exposed"] for row in samples)})
    report = {"summary": summary, "magnets": rows,
              "case_front_y_mm": 31.5, "intentionally_proud_magnetic_faces_excluded": True}
    STATE[label + "_outer_walls"] = report
    write(label + "_outer_magnet_walls.json", report)
    return report


def healthy(feature, label):
    if feature is None or feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        message = feature.errorOrWarningMessage if feature is not None else "No parametric feature"
        raise RuntimeError(label + ": " + message)


def select_clearance_face(body, kind):
    reference = STATE["definitions"][TARGET]
    index = 381 if kind == "rear" else 15
    original = reference.faces.item(index).geometry
    matches = []
    for face in body.faces:
        g = face.geometry
        if kind == "rear":
            if not isinstance(g, adsk.core.Plane):
                continue
            if abs(g.normal.dotProduct(original.normal)) < 1 - 1e-9:
                continue
            if abs(original.origin.vectorTo(g.origin).dotProduct(original.normal)) > 1e-7:
                continue
            b = tools().bounds(face)
            if b[0][1] < 11.39 or b[1][1] > 13.51 or b[0][2] < 35 or b[1][2] < 47:
                continue
        else:
            if not isinstance(g, adsk.core.Cylinder) or abs(g.axis.y) < .999999:
                continue
            if abs(g.radius - original.radius) > 1e-8:
                continue
            if math.hypot(g.origin.x - original.origin.x, g.origin.z - original.origin.z) > 1e-8:
                continue
        matches.append(face)
    if len(matches) != 1:
        raise RuntimeError("The preserved " + kind + " clearance face is not uniquely identifiable")
    return matches[0]


def offset_clearances(component):
    rows = []
    for kind, distance, label in (
        ("rear", -.6, "P03 rear arm clearance - 0.6 mm parallel relief"),
        ("front", -.5, "P03 front arm clearance - coaxial R7.0"),
    ):
        body = component.bRepBodies.itemByName(TARGET)
        before = body.volume * 1000
        face = select_clearance_face(body, kind)
        features = component.features.offsetFacesFeatures
        feature = features.add(features.createInput(
            [face], adsk.core.ValueInput.createByReal(distance / 10)))
        healthy(feature, label)
        feature.name = label
        after = component.bRepBodies.itemByName(TARGET).volume * 1000
        if after >= before:
            raise RuntimeError("The clearance offset did not remove material: " + kind)
        rows.append({"kind": kind, "offset_mm": distance, "removed_mm3": before - after,
                     "feature": feature.name})
    return rows


def pin_clearance(name, radius_growth_mm):
    s, _ = geometry()
    pin = STATE["world"][name]
    cylinders = [face.geometry for face in pin.faces
                 if isinstance(face.geometry, adsk.core.Cylinder)]
    planes = [face.geometry for face in pin.faces if isinstance(face.geometry, adsk.core.Plane)]
    if len(cylinders) != 1 or len(planes) != 2 or pin.faces.count != 3:
        raise RuntimeError("The locating-pin reference is not a simple capped cylinder: " + name)
    cylinder = cylinders[0]
    axis = cylinder.axis.copy()
    axis.normalize()
    parameters = []
    for plane in planes:
        denominator = plane.normal.dotProduct(axis)
        if abs(denominator) < .999999:
            raise RuntimeError("The locating-pin end cap is not perpendicular to its axis")
        parameters.append(cylinder.origin.vectorTo(plane.origin).dotProduct(plane.normal) /
                          denominator)
    endpoints = []
    for parameter in (min(parameters) - .02, max(parameters) + .02):
        vector = axis.copy()
        vector.scaleBy(parameter)
        point = cylinder.origin.copy()
        point.translateBy(vector)
        endpoints.append(point)
    radius = cylinder.radius + radius_growth_mm / 10
    result = s.tbm().createCylinderOrCone(endpoints[0], radius, endpoints[1], radius)
    if result is None:
        raise RuntimeError("The analytic locating-pin keepout failed")
    return result


def prepare_supports():
    if STATE.get("support_tools"):
        raise RuntimeError("The front-only magnet ribs were already prepared")
    s, m = geometry()
    magnets = [name for name in STATE["world"] if name.startswith("OCT_RECEIVER_MAGNET_")]
    pins = [name for name in STATE["world"]
            if name.startswith("OCT_") and "PIN" in name.upper()]
    if len(magnets) != 4 or len(pins) != 6:
        raise RuntimeError("The four receiver magnets and six locating pins must be identified explicitly")
    box = tools().bounds(STATE["world"]["OCT_RECEIVER_MAGNET_2"])
    radius = 1.0
    x0, x1, y0, y1 = 4.45, 8.65, 24.0, box[0][1]
    z0, z1 = 26.0, 35.0
    positive = m.rounded_box(x0, x1, y0, y1, z0, z1, [
        (x0 + radius, z0 + radius, radius), (x1 - radius, z0 + radius, radius),
        (x0 + radius, z1 - radius, radius), (x1 - radius, z1 - radius, radius)])
    guards = []
    for name in magnets:
        lo, hi = tools().bounds(STATE["world"][name])
        guards.append((name, s.box(lo[0] - .1, hi[0] + .1, lo[1], hi[1] + 1,
                                   lo[2] - .1, hi[2] + .1)))
    for name in pins:
        guards.append((name, pin_clearance(name, .2)))
        shoulder = pin_clearance(name, .55)
        s.op(shoulder, s.box(-25, 25, 25, 35, box[1][2] + .1, 60), "common")
        if shoulder.lumps.count:
            guards.append((name + " upper access", shoulder))
    for _, guard in guards:
        s.op(positive, s.tbm().copy(guard), "cut")
    tools().one_solid(positive, "Protected positive upper-magnet backing")
    STATE["support_tools"] = [positive]
    STATE["pocket_guards"] = guards
    report = {
        "reinforced_magnet": "OCT_RECEIVER_MAGNET_2",
        "reason": "The exposed side is an arm-clearance opening; reinforce rearward instead",
        "measured_full_open_magnet_to_arm_clearance_mm": .1087287864104336,
        "no_permission_to_change_arm_or_tool": True,
        "inner_tool_gallery_abs_x_mm_unchanged": 3.2, "outer_wall_x_mm": x1,
        "outline_corner_radius_mm": radius, "rear_rim_radius_mm": .6,
        "x_mm": [x0, x1], "y_mm": [y0, y1], "z_mm": [z0, z1],
        "receiver_magnet_and_locator_pocket_guards": [name for name, _ in guards],
        "magnet_working_front_faces_not_capped": True,
        "existing_locator_access_openings_intentionally_retained": True,
    }
    write("magnet_support_design.json", report)
    return report


def join_supports(component):
    s, _ = geometry()
    feature = component.features.baseFeatures.add()
    feature.name = "P03 upper-magnet rear backing - R1.0 rounded support"
    if not feature.startEdit():
        raise RuntimeError("Could not start the P03 reinforcement tool")
    try:
        for index, shape in enumerate(STATE["support_tools"]):
            added = component.bRepBodies.add(s.tbm().copy(shape), feature)
            if added is None:
                raise RuntimeError("Could not add an upper-magnet rib")
            added.name = "V21_MAGNET_WALL_TOOL_" + str(index)
    finally:
        if not feature.finishEdit():
            raise RuntimeError("Could not finish the P03 reinforcement tools")
    collection = adsk.core.ObjectCollection.create()
    for body in feature.bodies:
        collection.add(body)
    target = component.bRepBodies.itemByName(TARGET)
    features = component.features.combineFeatures
    options = features.createInput(target, collection)
    options.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    options.isKeepToolBodies = False
    joined = features.add(options)
    healthy(joined, "Joining the upper-magnet rear backing")
    joined.name = "P03 joined upper-magnet support only"
    body = component.bRepBodies.itemByName(TARGET)
    tools().one_solid(body, "Reinforced P03")
    if sum(b.lumps.count > 0 for b in component.bRepBodies) != 1:
        raise RuntimeError("The P03 reinforcement left unconsumed physical tool bodies")
    return finish_rear_rim(component)


def finish_rear_rim(component):
    body = component.bRepBodies.itemByName(TARGET)
    collection = adsk.core.ObjectCollection.create()
    for edge in body.edges:
        b = tools().bounds(edge)
        if (abs(b[0][0] - 8.65) < 1e-5 and abs(b[1][0] - 8.65) < 1e-5 and
                abs(b[0][1] - 24.0) < 1e-5 and abs(b[1][1] - 24.0) < 1e-5 and
                b[1][2] - b[0][2] > 5):
            collection.add(edge)
    if collection.count != 1:
        raise RuntimeError("The new upper-magnet backing rim is not uniquely identifiable")
    features = component.features.filletFeatures
    options = features.createInput()
    options.edgeSetInputs.addConstantRadiusEdgeSet(
        collection, adsk.core.ValueInput.createByReal(.06), True)
    feature = features.add(options)
    healthy(feature, "The rounded upper-magnet rear rim")
    feature.name = "P03 upper-magnet smooth R0.6 rear rim"
    return component.bRepBodies.itemByName(TARGET)


def prototype(app, ui):
    if STATE.get("candidate_native") or not STATE.get("support_tools"):
        raise RuntimeError("Prepare the P03 outer-wall support once before prototyping")
    if ui.activeCommand == "FreeOrbitCommand":
        ui.terminateActiveCommand()
    if app.activeDocument.creationId != STATE["document"] or ui.activeCommand != "SelectCommand":
        raise RuntimeError("Finish the current command in the preserved front-half document")
    s, _ = geometry()
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.activate()
    document.name = "TEMP - P03 only magnet and clearance review"
    STATE["prototype_document"] = document.creationId
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        component = design.rootComponent
        feature = component.features.baseFeatures.add()
        feature.name = "Unmodified user-cleaned P03 input"
        if not feature.startEdit():
            raise RuntimeError("Could not start the isolated P03 review body")
        try:
            body = component.bRepBodies.add(s.tbm().copy(STATE["definitions"][TARGET]), feature)
            body.name = TARGET
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish the isolated P03 review body")
        feature.bodies.item(0).name = TARGET
        offsets = offset_clearances(component)
        body = join_supports(component)
        STATE["candidate_native"] = s.tbm().copy(body)
        STATE["target_world"] = s.tbm().copy(body)
        if not s.tbm().transform(STATE["target_world"], STATE["matrices"][TARGET]):
            raise RuntimeError("The candidate front-half placement failed")
        if not s.tbm().exportToFile([STATE["candidate_native"]], str(OUT / "P03_reviewed_candidate.smt")):
            raise RuntimeError("The isolated native P03 checkpoint could not be preserved")
        report = {"source_sha256": STATE["source_sha256"], "only_P03": True,
                  "offset_features": offsets, "candidate_stats": tools().stats(body)}
        STATE["candidate_report"] = report
        write("candidate_native_geometry.json", report)
        walls = measure_top_magnets(app, "candidate", body)
        outer = measure_outer_magnets(app, "candidate", body)
        return {"geometry": report, "magnet_walls": walls["summary"],
                "outer_magnet_walls": outer["summary"]}
    finally:
        source.activate()


def verify_inventory(app, label, expected_target=None, count=50):
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the preserved assembly for the front-only scope check")
    by, empty = inventory(adsk.fusion.Design.cast(app.activeProduct))
    if set(by) != set(STATE["definitions"]) or empty != STATE["empty_history"]:
        raise RuntimeError("The preserved physical inventory or empty history changed")
    rows = STATE.setdefault(label + "_inventory", [])
    if any(row["definition_difference_mm3"] or row["placement_max_delta"] > 1e-8 for row in rows):
        raise RuntimeError("A failed scope check must be reset, not skipped")
    names = sorted(by)
    for name in names[len(rows):len(rows) + count]:
        expected = expected_target if name == TARGET and expected_target is not None else STATE["definitions"][name]
        delta = exact(expected, by[name].nativeObject, label + " " + name)
        placement = max(abs(a - b) for a, b in zip(
            STATE["matrices"][name].asArray(), by[name].assemblyContext.transform2.asArray()))
        rows.append({"body": name, "definition_difference_mm3": delta,
                     "placement_max_delta": placement})
        write(label + "_inventory.json", {
            "source_sha256": STATE["source_sha256"], "expected_physical_count": len(names),
            "checked": rows, "complete": len(rows) == len(names)})
        if delta or placement > 1e-8:
            raise RuntimeError("The live geometry or placement changed: " + name)
    return {"checked": len(rows), "total": len(names), "complete": len(rows) == len(names)}


def apply_front_only(app, ui):
    if STATE.get("applied") or not STATE.get("candidate_native"):
        raise RuntimeError("The reviewed P03 candidate must be applied exactly once")
    if len(STATE.get("before_apply_inventory", [])) != len(STATE["definitions"]):
        raise RuntimeError("Verify every preserved body before applying the P03-only features")
    if ui.activeCommand == "FreeOrbitCommand":
        ui.terminateActiveCommand()
    if app.activeDocument.creationId != STATE["document"] or ui.activeCommand != "SelectCommand":
        raise RuntimeError("Finish the active native command before changing P03")
    if len(STATE.get("candidate_motion", [])) < 5 or any(
            row["unexpected_clashes"] for row in STATE["candidate_motion"]):
        raise RuntimeError("The candidate still interferes with the opening path")
    if ("candidate_static" not in STATE or STATE["candidate_static"]["unexpected_clashes"] or
            STATE.get("candidate_tool_summary") !=
            {"sampled_tool_offsets": 36, "offsets_with_clashes": 0}):
        raise RuntimeError("The candidate fixed-part and tool-withdrawal checks have not passed")
    by, _ = inventory(adsk.fusion.Design.cast(app.activeProduct))
    body = by[TARGET].nativeObject
    if exact(STATE["definitions"][TARGET], body, "immediate P03 application guard"):
        raise RuntimeError("The user changed P03 after the reviewed input; preserve the new edit")
    component = body.parentComponent
    offsets = offset_clearances(component)
    body = join_supports(component)
    delta = exact(STATE["candidate_native"], body, "applied P03 candidate")
    if delta:
        raise RuntimeError("The native P03 result differs from the reviewed candidate")
    s, _ = geometry()
    STATE["target_world"] = s.tbm().copy(body)
    if not s.tbm().transform(STATE["target_world"], STATE["matrices"][TARGET]):
        raise RuntimeError("The applied P03 world-frame audit copy could not be created")
    STATE["applied"] = True
    report = {"only_modified_body": TARGET, "offset_features": offsets,
              "exact_candidate_difference_mm3": delta, "stats": tools().stats(body),
              "other_piece_redesigns_not_applied": True}
    write("front_only_application.json", report)
    return report


def audit_feed(phases, label):
    s, _ = geometry()
    data = STATE["player"].load_data()[0]
    fixed_box = tools().bounds(STATE["world"]["STOCK_003_extrude_wheel_1"])
    fixed_axis = [(fixed_box[0][0] + fixed_box[1][0]) / 2, 0,
                  (fixed_box[0][2] + fixed_box[1][2]) / 2]
    axes = {"06": fixed_axis}
    for group, name in (("03", "AXLE_4x25_fixed"), ("04", "AXLE_4x24_moving")):
        box = tools().bounds(STATE["world"][name])
        axes[group] = [(box[0][0] + box[1][0]) / 2, 0,
                       (box[0][2] + box[1][2]) / 2]
    endpoints = []
    for cam in (0, 175):
        posed = pose(cam)
        carrier = STATE["player"].rotation(
            STATE["player"].arm_angle(data, cam), data["arm_pivot_mm"])
        moving_axis = adsk.core.Point3D.create(*(v / 10 for v in data["moving_hob_axis_mm"]))
        moving_axis.transformBy(carrier)
        endpoints.append((cam, posed, [v * 10 for v in moving_axis.asArray()]))
    rows = STATE.setdefault(label + "_feed", [])
    for phase in phases:
        for cam, posed, moving_axis in endpoints:
            clashes = []
            for name, path in STATE["paths"].items():
                group = path[:2]
                if group not in ("03", "04", "06", "07") or group != "07" and cam:
                    continue
                body = s.tbm().copy(posed[name])
                transform = STATE["player"].rotation(
                    float(phase), moving_axis if group == "07" else axes[group])
                if not s.tbm().transform(body, transform):
                    raise RuntimeError("A read-only feed-rotation sample failed")
                volume, common = s.common_volume(STATE["target_world"], body)
                if volume > 1e-5:
                    clashes.append({"body": name, "overlap_mm3": volume,
                                    "bounds_mm": tools().bounds(common)})
            rows.append({"independent_rotor_phase_deg": float(phase), "cam_deg": cam,
                         "unexpected_clashes": clashes})
            write(label + "_feed_audit.json", {
                "poses": rows, "independent_rotor_clearance_not_a_gear_meshing_simulation": True})
    return {"sampled_endpoint_phase_pairs": len(rows),
            "pairs_with_clashes": sum(bool(row["unexpected_clashes"]) for row in rows)}


def refresh_user_references(app, ui):
    if STATE.get("applied") or app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Only refresh unmodified, still-live user input")
    if ui.activeCommand not in ("SelectCommand", "FreeOrbitCommand"):
        raise RuntimeError("Finish the active modeling command before preserving fresh references")
    by, empty = inventory(adsk.fusion.Design.cast(app.activeProduct))
    if set(by) != set(STATE["definitions"]) or empty != STATE["empty_history"]:
        raise RuntimeError("The user changed the assembly inventory; review that change explicitly")
    changes = []
    for name in sorted(by):
        delta = exact(STATE["definitions"][name], by[name].nativeObject, "user reference " + name)
        placement = max(abs(a - b) for a, b in zip(
            STATE["matrices"][name].asArray(), by[name].assemblyContext.transform2.asArray()))
        if delta or placement > 1e-8:
            changes.append({"body": name, "definition_difference_mm3": delta,
                            "placement_max_delta": placement, "path": STATE["paths"][name]})
    if any(row["body"] == TARGET for row in changes):
        write("new_user_P03_requires_review.json", changes)
        raise RuntimeError("The user changed P03; do not apply an older candidate over that edit")
    if any(row["path"][:2] in MOVING or row["path"].startswith("12 ") for row in changes):
        raise RuntimeError("Moving or tool references changed; rerun their candidate checks before application")
    if ui.activeCommand == "FreeOrbitCommand":
        ui.terminateActiveCommand()
    previous = STATE.copy()
    previous_sha = STATE["source_sha256"]
    s, _ = geometry()
    previous["blue_before_reference_refresh"] = s.tbm().copy(STATE["definitions"]["PRINT_motor_mount"])
    reference = OUT / "P01_before_reported_loss_REFERENCE_ONLY.smt"
    if not reference.exists() and not s.tbm().exportToFile(
            [previous["blue_before_reference_refresh"]], str(reference)):
        raise RuntimeError("Could not preserve the earlier blue-half reference for the queued repair")
    STATE.clear()
    report = capture(app, ui)
    latest = STATE.copy()
    STATE.update(previous)
    STATE.update(latest)
    STATE.pop("before_apply_inventory", None)
    s, _ = geometry()
    STATE["target_world"] = s.tbm().copy(STATE["candidate_native"])
    if not s.tbm().transform(STATE["target_world"], STATE["matrices"][TARGET]):
        raise RuntimeError("The refreshed candidate placement failed")
    receipt = {"previous_input_sha256": previous_sha, "latest_input_sha256": STATE["source_sha256"],
               "user_reference_changes_preserved": changes,
               "P03_and_all_moving_tool_references_exactly_unchanged": True,
               "candidate_motion_and_tool_checks_still_applicable": True}
    write("user_reference_refresh.json", receipt)
    return {"refresh": receipt, "latest_input": report, "static_recheck": audit_static("candidate")}


def freeze_archive(app):
    if not STATE.get("applied") or app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Apply the reviewed front half before freezing its native assembly")
    rows = STATE.get("after_apply_inventory", [])
    if len(rows) != len(STATE["definitions"]) or any(
            row["definition_difference_mm3"] or row["placement_max_delta"] > 1e-8 for row in rows):
        raise RuntimeError("Complete the exact 139-body post-application scope check")
    path = OUT / "release" / "cad" / "SparkShift_P03_magnet_support_clearance_v21_WIP.f3d"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError("The frozen P03 assembly must not be overwritten")
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("Could not save the matched native P03 revision")
    report = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "bytes": path.stat().st_size, "source_input_sha256": STATE["source_sha256"],
              "physical_bodies": len(STATE["definitions"]), "only_modified_body": TARGET,
              "other_138_definitions_and_all_139_placements_exactly_unchanged": True,
              "source_inspection_pose_retained_not_commanded_closed": True,
              "geometric_verification_complete": False, "qualified_hardware_release": False}
    STATE["archive"] = report
    write("native_archive_receipt.json", report)
    return report


def export_mesh(app, body, label):
    s, _ = geometry()
    helper = tools().load_file("sparkshift_v21_print_bed",
                               Path(__file__).resolve().parent / "sparkshift_surface_cleanup.py")
    orientation = helper.bed_face(body, (0, -1, 0))
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
        rotation.setToRotation(angle, axis, adsk.core.Point3D.create())
        if not s.tbm().transform(shape, rotation):
            raise RuntimeError("The P03 print-bed rotation failed")
    box = shape.preciseBoundingBox
    translation = adsk.core.Matrix3D.create()
    translation.translation = adsk.core.Vector3D.create(
        -box.minPoint.x, -box.minPoint.y, -box.minPoint.z)
    if not s.tbm().transform(shape, translation):
        raise RuntimeError("The P03 print-bed translation failed")
    tools().one_solid(shape, "Bed-oriented P03")
    folder = OUT / ("release" if label == "final" else "trial") / "stl"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("P03_reinforced_backing_clearance_v21_" + label + ".stl")
    if path.exists():
        raise RuntimeError("A raw P03 mesh would be overwritten")
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.activate()
    document.name = "EXPORT ONLY - P03 native raw mesh"
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        feature = design.rootComponent.features.baseFeatures.add()
        if not feature.startEdit():
            raise RuntimeError("Could not start the P03 print-export solid")
        try:
            exported = design.rootComponent.bRepBodies.add(shape, feature)
            exported.name = "P03"
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish the P03 print-export solid")
        feature.bodies.item(0).name = "P03"
        options = design.exportManager.createSTLExportOptions(
            design.rootComponent.bRepBodies.itemByName("P03"), str(path))
        options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        options.surfaceDeviation = .0003
        options.normalDeviation = 4.
        options.isBinaryFormat = True
        if not design.exportManager.execute(options) or path.stat().st_size <= 84:
            raise RuntimeError("The raw native P03 mesh export failed")
        report = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "native_volume_mm3": body.volume * 1000, "bed_face": orientation,
                  "rotation": list(rotation.asArray()), "translation": list(translation.asArray()),
                  "native_archive_sha256": STATE.get("archive", {}).get("sha256"),
                  "raw_native_mesh_without_repair": True}
        STATE[label + "_mesh"] = report
        write(label + "_mesh_export.json", report)
        return report
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the owned P03 print-export document")
        source.activate()


def begin_readback(app):
    if not STATE.get("archive") or STATE.get("readback_document"):
        raise RuntimeError("Freeze the assembly once before independent native readback")
    path = Path(STATE["archive"]["path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != STATE["archive"]["sha256"]:
        raise RuntimeError("The frozen native archive changed")
    document = app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(path)))
    if document is None:
        raise RuntimeError("The frozen front-half archive could not be independently reopened")
    document.activate()
    document.name = "SparkShift v21 - P03-only magnet backing and clearances - WIP"
    STATE["readback_document"] = document.creationId
    STATE["readback_rows"] = []
    return {"readback_document": document.creationId, "archive_sha256": STATE["archive"]["sha256"]}


def verify_readback(app, count=50):
    if app.activeDocument.creationId != STATE.get("readback_document"):
        raise RuntimeError("Activate only the independent front-half archive readback")
    by, empty = inventory(adsk.fusion.Design.cast(app.activeProduct))
    if set(by) != set(STATE["definitions"]) or empty != STATE["empty_history"]:
        raise RuntimeError("The saved native physical inventory differs")
    rows = STATE["readback_rows"]
    if any(row["difference_mm3"] or row["placement_max_delta"] > 1e-8 for row in rows):
        raise RuntimeError("A failed readback cannot be resumed past its failed row")
    names = sorted(by)
    for name in names[len(rows):len(rows) + count]:
        expected = STATE["candidate_native"] if name == TARGET else STATE["definitions"][name]
        tools().one_solid(by[name].nativeObject, "Saved " + name)
        delta = exact(expected, by[name].nativeObject, "saved native " + name)
        placement = max(abs(a - b) for a, b in zip(
            STATE["matrices"][name].asArray(), by[name].assemblyContext.transform2.asArray()))
        rows.append({"body": name, "difference_mm3": delta, "placement_max_delta": placement})
        write("native_archive_readback.json", {
            "archive_sha256": STATE["archive"]["sha256"], "checked": rows,
            "expected_physical_count": len(names), "complete": len(rows) == len(names)})
        if delta or placement > 1e-8:
            raise RuntimeError("The saved body or its placement differs: " + name)
    return {"checked": len(rows), "total": len(names), "complete": len(rows) == len(names)}


def seal_front_only():
    expected = [i / 4 for i in range(701)]
    motion = STATE.get("after_motion", [])
    if ([row["cam_deg"] for row in motion] != expected or
            any(row["unexpected_clashes"] for row in motion)):
        raise RuntimeError("All 701 nominal quarter-degree release samples must pass")
    feed = STATE.get("after_feed", [])
    if (len(feed) != 72 or {(row["independent_rotor_phase_deg"], row["cam_deg"]) for row in feed} !=
            {(float(angle), cam) for angle in range(0, 360, 10) for cam in (0, 175)} or
            any(row["unexpected_clashes"] for row in feed)):
        raise RuntimeError("The 36 closed/open rotor-phase checks must pass")
    if (STATE.get("after_static", {}).get("unexpected_clashes") != [] or
            STATE.get("after_tool_summary") != {"sampled_tool_offsets": 36, "offsets_with_clashes": 0}):
        raise RuntimeError("The fixed-reference and tool-withdrawal checks must pass")
    for key, delta_key in (("after_apply_inventory", "definition_difference_mm3"),
                           ("readback_rows", "difference_mm3")):
        rows = STATE.get(key, [])
        if len(rows) != 139 or any(row[delta_key] or row["placement_max_delta"] > 1e-8 for row in rows):
            raise RuntimeError("The exact 139-body native scope/readback check is incomplete")
    mesh = json.loads((OUT / "final_mesh_validation.json").read_text())
    if not mesh["passed"] or mesh["stored_normal_errors"]:
        raise RuntimeError("The saved raw P03 mesh has not passed without warnings")
    filament = json.loads((OUT / "filament_channel_audit.json").read_text())
    if filament["nominal_1p75_filament_reference_overlap_mm3"] > 1e-5:
        raise RuntimeError("The nominal filament reference intersects P03")
    for item in (STATE["archive"], STATE["final_mesh"]):
        if hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError("A checked delivery artifact changed")
    report = {
        "status": "verified_geometry_only_WIP",
        "source_input_sha256": STATE["source_sha256"],
        "only_modified_body": TARGET,
        "native": STATE["archive"], "mesh": STATE["final_mesh"],
        "native_readback_bodies": 139, "other_138_definitions_unchanged": True,
        "all_139_input_placements_retained": True,
        "release_cam_deg": [0, 175], "release_step_deg": .25, "release_samples": len(motion),
        "release_samples_with_interference": 0,
        "independent_rotor_phases": 36, "closed_open_phase_pairs": len(feed),
        "tool_withdrawal_mm": [0, 35], "tool_samples": 36,
        "unexpected_fixed_part_clashes": [],
        "declared_installation_contacts": STATE["after_static"]["declared_installation_contacts"],
        "raw_mesh_validation": mesh,
        "nominal_filament_reference_overlap_mm3": filament[
            "nominal_1p75_filament_reference_overlap_mm3"],
        "retained_magnet_arm_clearance_mm": .1087287864104336,
        "side_opening_required_rearward_magnet_reinforcement_used": True,
        "physical_fit_force_endpoints_and_FDM_strength_not_qualified": True,
        "blue_half_reported_damage_and_cleanup_not_part_of_this_revision": True,
        "no_publication_or_git_commit": True,
    }
    report["native"].pop("verification_pending_not_a_qualified_release", None)
    report["native"]["geometric_verification_complete"] = True
    report["native"]["qualified_hardware_release"] = False
    STATE["sealed"] = True
    STATE["verification"] = report
    (OUT / "release" / "verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write("native_archive_receipt.json", STATE["archive"])
    return {"sealed": True, "native_sha256": STATE["archive"]["sha256"],
            "mesh_sha256": STATE["final_mesh"]["sha256"], "release_samples": len(motion),
            "readback_bodies": 139, "raw_mesh_passed": True}
