"""Standalone Fusion script for the saved SparkShift preview's native joints."""

import bisect
import json
import math

import adsk.core
import adsk.fusion


TAG = "COMPACT_CAM_MOTION"
JOINTS = {"E", "S_R", "S_L", "C", "SC", "H_R", "H_L", "CAM", "ROLLER",
          "A_R", "A_L", "TOOL_Y"}
LINKS = {"INPUT_38T", "PRIMARY_PAIR", "FIXED_HOB_14_37", "CLAMPED_HOB_14_37"}
REFERENCE_CACHE = {}


def rotation(joint):
    value = math.degrees(joint.jointMotion.rotationValue)
    if not math.isfinite(value):
        raise RuntimeError("Fusion reported a non-finite joint angle")
    return value if joint.name == "J_E" else math.remainder(value, 360)


def settle(design):
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    if not design.computeAll():
        raise RuntimeError("Fusion could not compute the SparkShift assembly")
    adsk.doEvents()


def drive(design, joint, degrees):
    locked = joint.isLocked
    preferences = adsk.core.Application.get().preferences.unitAndValuePreferences
    precision = preferences.angularPrecision
    start = rotation(joint)
    if joint.name != "J_E":
        degrees = start+math.remainder(degrees-start, 360)
    steps = max(1, math.ceil(abs(degrees-start)/90))
    joint.isLocked = False
    try:
        preferences.angularPrecision = 6
        for index in range(1, steps+1):
            target = start+(degrees-start)*index/steps
            joint.jointMotion.rotationValue = math.radians(target)
            settle(design)
            error = rotation(joint)-target
            if joint.name != "J_E":
                error = math.remainder(error, 360)
            if abs(error) > .005:
                raise RuntimeError(joint.name+" did not reach the requested angle")
    finally:
        joint.isLocked = locked
        preferences.angularPrecision = precision


def lookup(table, angle):
    rows = table["rows"]
    if not math.isfinite(angle) or not rows[0][0] <= angle <= rows[-1][0]:
        raise ValueError("Cam command is outside the saved contact table")
    index = bisect.bisect_left([row[0] for row in rows], angle)
    if index == 0 or rows[index][0] == angle:
        return rows[index][1:]
    left, right = rows[index-1], rows[index]
    fraction = (angle-left[0])/(right[0]-left[0])
    return [left[i]+fraction*(right[i]-left[i]) for i in (1, 2)]


def rotate_xz(point, pivot, degrees):
    angle = math.radians(degrees)
    x, z = point[0]-pivot[0], point[1]-pivot[1]
    return [pivot[0]+x*math.cos(angle)+z*math.sin(angle),
            pivot[1]-x*math.sin(angle)+z*math.cos(angle)]


def filament_fraction(config, q, tool_mm):
    if tool_mm > .001:
        return 0.0
    data = config["reference_geometry"]
    closed = data["closed_left_hob_xz_mm"]
    moved = rotate_xz(closed, data["pivot_authoring_xz_mm"], -(q-config["closed_arm_deg"]))
    return max(0.0, min(1.0, 1+(moved[0]-closed[0])/data["filament_nip_xz_mm"][0]))


def filament_x(data, z, fraction):
    if z <= -34 or z >= 32:
        return 0.0
    nip_x, nip_z = data["filament_nip_xz_mm"]
    t = (z+34)/(nip_z+34) if z <= nip_z else (32-z)/(32-nip_z)
    return nip_x*fraction*t*t*(3-2*t)


def installed_point(data, x, y, z):
    return adsk.core.Point3D.create(-x/10, y/10, (data["installed_hob_z_mm"]-z)/10)


def spring_shape(manager, config, q):
    data, spring = config["reference_geometry"], config["spring_layout"]
    pivot = data["pivot_authoring_xz_mm"]
    left = rotate_xz(data["closed_left_spring_xz_mm"], pivot, -(q-config["closed_arm_deg"]))
    right = [spring["nominal_right_seat_x_mm"]-spring["nominal_adjustment_mm"],
             spring["axis_z_mm"]]
    length = math.dist(left, right)
    ux, uz = [(right[i]-left[i])/length for i in range(2)]
    y = spring["axis_y_mm"]

    def point(x, yy, z):
        return adsk.core.Point3D.create(x/10, yy/10, z/10)

    first = point(left[0]-2*ux, y, left[1]-2*uz)
    last = point(right[0]+2*ux, y, right[1]+2*uz)
    shape = manager.createCylinderOrCone(
        first, spring["spring_outer_radius_mm"]/10, last, spring["spring_outer_radius_mm"]/10)
    inner = manager.createCylinderOrCone(
        first, spring["spring_inner_radius_mm"]/10, last, spring["spring_inner_radius_mm"]/10)
    if not manager.booleanOperation(shape, inner, adsk.fusion.BooleanTypes.DifferenceBooleanType):
        raise RuntimeError("Cannot make the hollow spring display envelope")

    def box(x0, x1):
        return manager.createBox(adsk.core.OrientedBoundingBox3D.create(
            point((x0+x1)/2, y, spring["axis_z_mm"]),
            adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
            (x1-x0)/10, 4.0, 6.0))

    left_half = box(data["closed_left_spring_xz_mm"][0], 80)
    transform = adsk.core.Matrix3D.create()
    transform.setToRotation(math.radians(-(q-config["closed_arm_deg"])),
                            adsk.core.Vector3D.create(0, 1, 0), point(pivot[0], 0, pivot[1]))
    if not manager.transform(left_half, transform):
        raise RuntimeError("Cannot align the moving spring end plane")
    for limiter in (left_half, box(-80, right[0])):
        if not manager.booleanOperation(shape, limiter, adsk.fusion.BooleanTypes.IntersectionBooleanType):
            raise RuntimeError("Cannot terminate the spring at its actual seats")
    transform.setToRotation(math.pi, adsk.core.Vector3D.create(0, 1, 0), point(0, 0, 0))
    transform.translation = adsk.core.Vector3D.create(0, 0, data["installed_hob_z_mm"]/10)
    if not manager.transform(shape, transform) or not shape.isSolid or shape.lumps.count != 1:
        raise RuntimeError("Cannot install the seated spring display envelope")
    return shape


def replace_reference(occurrence, shape):
    component = occurrence.component
    feature = component.features.baseFeatures.item(0)
    body = component.bRepBodies.item(0)
    name, appearance = body.name, body.appearance
    if not feature.startEdit():
        raise RuntimeError("Could not edit the deforming display reference")
    try:
        source = feature.bodies.item(0)
        if not feature.updateBody(source, shape):
            raise RuntimeError("Could not update the deforming display reference")
        source.name, source.appearance, source.opacity = name, appearance, .4
    finally:
        feature.finishEdit()


def update_references(design, config, parts, q, tool_mm):
    root = design.rootComponent
    data = config["reference_geometry"]
    previous_q = float(root.attributes.itemByName(TAG, "reference_arm_deg").value)
    previous_fraction = float(root.attributes.itemByName(TAG, "reference_filament_fraction").value)
    fraction = filament_fraction(config, q, tool_mm)
    if abs(previous_q-q) <= 1e-9 and abs(previous_fraction-fraction) <= 1e-9:
        return
    manager = adsk.fusion.TemporaryBRepManager.get()
    cache = REFERENCE_CACHE.setdefault(root.entityToken, {})
    current_key, key = round(previous_fraction, 8), round(fraction, 8)
    if current_key not in cache:
        cache[current_key] = manager.copy(parts["REFERENCE_loaded_filament"].component.bRepBodies.item(0))
    replace_reference(parts["CLOSING_SPRING_ENVELOPE"], spring_shape(manager, config, q))
    if key != current_key:
        if key not in cache:
            body = None
            heights = [-55.0, *[-34+66*i/96 for i in range(97)], 38.0]
            for z0, z1 in zip(heights, heights[1:]):
                a = installed_point(data, filament_x(data, z0, fraction), data["filament_axis_y_mm"], z0)
                b = installed_point(data, filament_x(data, z1, fraction), data["filament_axis_y_mm"], z1)
                segment = manager.createCylinderOrCone(a, .0875, b, .0875)
                if z1 != heights[-1] and not manager.booleanOperation(
                        segment, manager.createSphere(b, .0875), adsk.fusion.BooleanTypes.UnionBooleanType):
                    raise RuntimeError("Cannot join the curved filament reference")
                if body is None:
                    body = segment
                elif not manager.booleanOperation(body, segment, adsk.fusion.BooleanTypes.UnionBooleanType):
                    raise RuntimeError("Cannot complete the filament reference")
            cache[key] = body
        replace_reference(parts["REFERENCE_loaded_filament"], cache[key])
    root.attributes.add(TAG, "reference_arm_deg", repr(q))
    root.attributes.add(TAG, "reference_filament_fraction", repr(fraction))
    settle(design)


def identified(collection, attribute):
    result = {}
    for entity in collection:
        owner = entity.component if attribute == "part_id" else entity
        identity = owner.attributes.itemByName(TAG, attribute)
        if identity:
            if identity.value in result:
                raise ValueError("Duplicate native motion identity: "+identity.value)
            result[identity.value] = entity
    return result


def checked_state(root, config, table, joints, links):
    angles = {name: rotation(joint) for name, joint in joints.items() if name != "TOOL_Y"}
    carrier, motor = angles["C"], angles["E"]
    right = -motor*config["motor_teeth"]/38
    expected = {"S_R": right, "S_L": -right, "SC": -right-carrier,
                "H_R": -14/37*right, "H_L": -14/37*(-right-carrier)}
    if any(abs(math.remainder(angles[name]-value, 360)) > .005 for name, value in expected.items()):
        raise RuntimeError("The native gear relationships are inconsistent")
    for name, link in links.items():
        suppressed = name == "CLAMPED_HOB_14_37" and abs(carrier) >= 1e-6
        if link.isSuppressed != suppressed:
            raise RuntimeError("A native gear link has the wrong suppression state")
    q = config["closed_arm_deg"]-carrier
    manual = root.attributes.itemByName(TAG, "manual_release_active")
    if not manual or manual.value != "true":
        expected_q, roller = lookup(table, angles["CAM"])
        if abs(q-expected_q) > .005 or abs(math.remainder(angles["ROLLER"]-roller, 360)) > .005:
            raise ValueError("The carrier/follower is not coordinated with the cam")
    return {"motor_deg": motor, "cam_deg": angles["CAM"], "arm_deg": q,
            "tool_mm": joints["TOOL_Y"].jointMotion.slideValue*10, "angles_deg": angles}


def apply(action, value=0, design=None):
    design = design or adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    if not design:
        raise ValueError("Activate the SparkShift grouped preview")
    root = design.rootComponent
    schema = root.attributes.itemByName(TAG, "schema")
    config_attr = root.attributes.itemByName(TAG, "configuration")
    table_attr = root.attributes.itemByName(TAG, "cam_relation")
    if not schema or schema.value != "1" or not config_attr or not table_attr:
        raise ValueError("This file is not the SparkShift native motion preview")
    config, table = json.loads(config_attr.value), json.loads(table_attr.value)
    if not config.get("reference_geometry") or not config.get("spring_layout"):
        raise ValueError("Use the current SparkShift.f3d with its saved reference datums")
    joints = identified(root.joints, "joint_id")
    links = identified(root.motionLinks, "link_id")
    parts = identified(root.allOccurrences, "part_id")
    if set(joints) != JOINTS or set(links) != LINKS:
        raise ValueError("The saved native joint/gear-link set is incomplete")
    if not {"CLOSING_SPRING_ENVELOPE", "REFERENCE_loaded_filament"} <= set(parts):
        raise ValueError("The saved deforming references are missing")
    aliases = {name.lower(): name for name in ("Feed", "Open", "Close", "Remove tool", "Insert tool")}
    action = aliases.get(action.strip().lower())
    if not action:
        raise ValueError("Unknown SparkShift action")
    state = checked_state(root, config, table, joints, links)
    manual = root.attributes.itemByName(TAG, "manual_release_active")
    pressed = root.attributes.itemByName(TAG, "manual_lever_pressed")
    if action == "Feed":
        latched = root.attributes.itemByName(TAG, "tool_latched")
        if (abs(state["cam_deg"]) > .01 or abs(state["arm_deg"]-config["closed_arm_deg"]) > .005
                or abs(state["tool_mm"]) > .001 or not latched or latched.value != "true"
                or (manual and manual.value == "true") or (pressed and pressed.value == "true")):
            raise ValueError("Park the cam, release the manual lever, and seat/latch the tool before feeding")
        if not math.isfinite(value) or abs(value) > 3600:
            raise ValueError("Feed demonstration supports -3600 to +3600 motor degrees")
        drive(design, joints["E"], value)
    elif action in ("Open", "Close"):
        if pressed and pressed.value == "true":
            raise ValueError("Release the manual lever before driving the cam")
        angle = 135 if action == "Open" else 0
        if action == "Close" and abs(state["tool_mm"]) > .001:
            raise ValueError("Insert the tool before closing")
        held = rotation(joints["E"])
        old_lock = joints["E"].isLocked
        joints["E"].isLocked = True
        try:
            links["CLAMPED_HOB_14_37"].isSuppressed = True
            q, roller = lookup(table, angle)
            carrier = -(q-config["closed_arm_deg"])
            drive(design, joints["CAM"], angle)
            drive(design, joints["C"], carrier)
            drive(design, joints["H_L"], -14/37*(rotation(joints["S_L"])-carrier))
            drive(design, joints["ROLLER"], roller)
            links["CLAMPED_HOB_14_37"].isSuppressed = abs(carrier) >= 1e-6
            root.attributes.add(TAG, "manual_release_active", "false")
            root.attributes.add(TAG, "manual_lever_pressed", "false")
            settle(design)
        finally:
            joints["E"].isLocked = old_lock
        if abs(rotation(joints["E"])-held) > .005:
            raise RuntimeError("Opening moved the held extrusion motor")
    else:
        required_q, _ = lookup(table, 135)
        if state["cam_deg"] < 134.99 or state["arm_deg"] < required_q-.005:
            raise ValueError("Open the cam and carrier fully before moving the tool")
        joint = joints["TOOL_Y"]
        locked = joint.isLocked
        joint.isLocked = False
        target = 35 if action == "Remove tool" else 0
        try:
            joint.jointMotion.slideValue = target/10
            settle(design)
            if abs(joint.jointMotion.slideValue*10-target) > .01:
                raise RuntimeError("The native tool slider did not reach its command")
        finally:
            joint.isLocked = locked
        root.attributes.add(TAG, "tool_latched", "false" if target else "true")
        if any(abs(math.remainder(rotation(joints[name])-before, 360)) > .005
               for name, before in state["angles_deg"].items()):
            raise RuntimeError("Tool withdrawal moved another joint")
    state = checked_state(root, config, table, joints, links)
    update_references(design, config, parts, state["arm_deg"], state["tool_mm"])
    return state


def run(context):
    ui = adsk.core.Application.get().userInterface
    action, cancelled = ui.inputBox(
        "Action: Feed, Open, Close, Remove tool, Insert tool\n"
        "This moves CAD only, not printer hardware.",
        "SparkShift preview motion", "Open")
    if cancelled:
        return
    try:
        value = 0
        if action.strip().lower() == "feed":
            text, cancelled = ui.inputBox("Absolute motor angle in degrees", "SparkShift feed", "90")
            if cancelled:
                return
            value = float(text)
        state = apply(action, value)
    except (ValueError, RuntimeError) as error:
        ui.messageBox(str(error), "SparkShift motion could not proceed")
        return
    ui.messageBox("Motor {motor_deg:.2f} deg; cam {cam_deg:.2f} deg; "
                  "arm {arm_deg:.2f} deg; tool {tool_mm:.2f} mm".format(**state),
                  "SparkShift CAD state")
