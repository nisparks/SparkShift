"""v23: make the purple P02 servo plate fit both the MG90S and MG90D STEP servos.

Both STEP servos put the ear face 8.5 mm below the gear-cover top, not the inherited 1.9 mm,
so the ears sit 4.5 mm behind the 7 mm plate.  Two bosses carry flat ear seats and
self-tapping pilots on the shared 27.5 mm MG90S/TowerPro pattern.  M2 heat-set inserts cannot
fit: both ear holes are only 2.25-2.32 mm from the case end and gear tower.
"""

import hashlib
import json
import math
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import adsk.core
import adsk.fusion


OUT = Path(__file__).resolve().parent / "sparkshift_servo_plate_v23"
PLATE = "PRINT_REAR_MOTOR_SERVO_SPACER"
ENVELOPE = "HOBBY_SERVO_ENVELOPE"
NEAR_SCREW = "MG90_M2x8_SELF_TAPPING_near"
FAR_SCREW = "MG90_M2x8_SELF_TAPPING_far"
REPLACED = {"MG90S_M2x6_SERVO_left": NEAR_SCREW, "MG90S_M2x6_SERVO_right": FAR_SCREW}
RETIRED = ("MG90S_UPPER_M2_HEATSET_3p2x3", "MG90S_LOWER_M2_HEATSET_3p2x3",
           "MG90S_M2_WASHER_left", "MG90S_M2_WASHER_right")
STATE = {}

AXIS_X, SHAFT_Z = 10.5, 50.7206
SEAT_Y, REAR_Y, FLOOR_Y, FRONT_Y = -11.2, -6.7, -2.0, 0.3
WIN_X = (2.8, 18.2)
POCKET_BOTTOM, POCKET_TOP_OLD, POCKET_TOP = 33.47, 56.87, 57.12
UPPER_BOSS_Z = (57.12, 62.22)
LOWER_BOSS_Z = (28.37, 33.47)
NEAR_Z, FAR_Z = 59.04, 31.54
PILOT_R, CSK, SEAT_FILLET = 0.85, 0.3, 0.5
SOCKET_FLOOR_Y = 1.16
SCREW_HEAD_R, SCREW_HEAD_H, SCREW_R, SCREW_L = 1.75, 1.3, 1.0, 8.0


def g22():
    return sys.modules["sparkshift_blue_half_v22"]


def front():
    return sys.modules["sparkshift_front_half_only_v21"]


def tools():
    return sys.modules["sparkshift_open_frame_v19"]


def geometry():
    return tools().geometry()


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


@contextmanager
def bound(placement=False):
    """Run proven v22 capture/audit helpers against this module's own state and folder."""
    module = g22()
    saved = (module.STATE, module.OUT, module.world_of)
    module.STATE, module.OUT = STATE, OUT
    if placement:
        module.world_of = world_of
    try:
        yield module
    finally:
        module.STATE, module.OUT, module.world_of = saved


def capture(app, ui):
    raw = {k: [(p, geometry()[0].tbm().copy(sh)) for p, sh in v]
           for k, v in g22().STATE["servo_step_shells"].items()}
    with bound() as module:
        report = module.capture(app, ui, "USER_live_input_v23")
    STATE["servo_raw"] = raw
    STATE["candidates"] = {}
    for name in (PLATE, ENVELOPE) + tuple(REPLACED) + RETIRED:
        if name not in STATE["definitions"]:
            raise RuntimeError("Expected body missing from the live assembly: " + name)
    return report


def identity(matrix, label):
    reference = adsk.core.Matrix3D.create().asArray()
    if max(abs(a - b) for a, b in zip(matrix.asArray(), reference)) > 1e-9:
        raise RuntimeError("Expected an identity assembly context: " + label)


def step_data():
    """Ear-top plane, ear-hole centres and output-shaft tips read from both STEP servos."""
    s, _ = geometry()
    rows = {}
    for servo, parts in STATE["servo_raw"].items():
        holes = []
        for part, shape in parts:
            for face in shape.faces:
                g = face.geometry
                if isinstance(g, adsk.core.Cylinder) and abs(abs(g.axis.y) - 1) < 1e-6:
                    r = g.radius * 10
                    b = tools().bounds(face)
                    if 1.2 < r < 1.3 and abs(g.origin.x * 10 - AXIS_X) < .01 \
                            and abs(g.origin.z * 10 - SHAFT_Z) > 3:
                        holes.append({"z": g.origin.z * 10, "r": r, "y": [b[0][1], b[1][1]]})
        tip = max(tools().bounds(shape)[1][1] for _, shape in parts)
        ear_top = max(h["y"][1] for h in holes)
        rows[servo] = {"ear_top_y": ear_top, "ear_back_y": min(h["y"][0] for h in holes),
                       "holes": sorted(holes, key=lambda h: h["z"]), "shaft_tip_y": tip,
                       "seat_shift_mm": SEAT_Y - ear_top}
    STATE["step_data"] = rows
    return rows


def servo_shells():
    s, m = geometry()
    data = STATE.get("step_data") or step_data()
    return {servo: [(p, m.translated(s.tbm().copy(sh), dy=data[servo]["seat_shift_mm"])) for p, sh in parts]
            for servo, parts in STATE["servo_raw"].items()}


def plate_tools():
    s, m = geometry()
    x0, x1 = WIN_X
    joins = s.box(x0, x1, REAR_Y, -4.1, 28.77, POCKET_BOTTOM)
    for tool in (
            s.box(x0, x1, REAR_Y, -4.1, POCKET_TOP, 61.57),
            s.cyl(AXIS_X, 31.27, -4.1, FRONT_Y, 1.75),
            s.cyl(AXIS_X, 59.07, -4.1, FRONT_Y, 1.75),
            m.rounded_box(x0, x1, SEAT_Y, REAR_Y, *UPPER_BOSS_Z,
                          [(x0 + 1, UPPER_BOSS_Z[1] - 1, 1.0), (x1 - 1, UPPER_BOSS_Z[1] - 1, 1.0)]),
            m.rounded_box(x0, x1, SEAT_Y, REAR_Y, *LOWER_BOSS_Z,
                          [(x0 + 1, LOWER_BOSS_Z[0] + 1, 1.0), (x1 - 1, LOWER_BOSS_Z[0] + 1, 1.0)])):
        s.op(joins, tool, "join")
    cuts = s.box(x0, x1, REAR_Y - 0.1, FLOOR_Y, POCKET_TOP_OLD, POCKET_TOP)
    for z in (NEAR_Z, FAR_Z):
        s.op(cuts, s.cyl(AXIS_X, z, SEAT_Y - 0.2, FLOOR_Y, PILOT_R), "join")
        s.op(cuts, m.cone_y(AXIS_X, z, SEAT_Y - 0.1, PILOT_R + CSK + 0.1, SEAT_Y + CSK, PILOT_R), "join")
    return joins, cuts


def seat_edges(body):
    edges = adsk.core.ObjectCollection.create()
    rows = []
    for edge in body.edges:
        b = tools().bounds(edge)
        if abs(b[0][1] - SEAT_Y) > 1e-6 or abs(b[1][1] - SEAT_Y) > 1e-6:
            continue
        kinds = []
        for face in edge.faces:
            g = face.geometry
            fb = tools().bounds(face)
            if isinstance(g, adsk.core.Plane) and abs(abs(g.normal.y) - 1) < 1e-9 \
                    and abs(fb[0][1] - SEAT_Y) < 1e-6 and abs(fb[1][1] - SEAT_Y) < 1e-6:
                kinds.append("seat")
            elif isinstance(g, adsk.core.Cone):
                kinds.append("countersink")
            elif isinstance(g, adsk.core.Plane) and abs(abs(g.normal.z) - 1) < 1e-9 and \
                    min(abs(fb[0][2] - POCKET_TOP), abs(fb[0][2] - POCKET_BOTTOM)) < 1e-6 and \
                    abs(fb[0][2] - fb[1][2]) < 1e-9:
                kinds.append("inner")
            else:
                kinds.append("outer")
        rows.append(kinds)
        if sorted(kinds) == ["outer", "seat"]:
            edges.add(edge)
    if edges.count != 10:
        STATE["seat_edge_debug"] = rows
        raise RuntimeError("Expected ten outer seat edges, found %d" % edges.count)
    return edges


def native_plate(component, joins, cuts):
    s, _ = geometry()
    names = []

    def tool_body(shape, label):
        feature = component.features.baseFeatures.add()
        feature.name = label
        if not feature.startEdit():
            raise RuntimeError("Could not start " + label)
        try:
            component.bRepBodies.add(s.tbm().copy(shape), feature)
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish " + label)
        return feature.bodies.item(0)

    def combine(tool, operation, label):
        collection = adsk.core.ObjectCollection.create()
        collection.add(tool)
        options = component.features.combineFeatures.createInput(
            component.bRepBodies.itemByName(PLATE), collection)
        options.operation = operation
        options.isKeepToolBodies = False
        feature = component.features.combineFeatures.add(options)
        front().healthy(feature, label)
        feature.name = label
        names.append(label)

    combine(tool_body(joins, "V23 TOOL MG90 ear-seat bosses and retired insert fills"),
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "P02 MG90S-MG90D ear-seat bosses at Y-11.2")
    combine(tool_body(cuts, "V23 TOOL MG90 tower clearance and self-tapping pilots"),
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            "P02 tower relief to Z57.12 and M2 self-tapping pilots")
    body = component.bRepBodies.itemByName(PLATE)
    fillets = component.features.filletFeatures
    options = fillets.createInput()
    options.edgeSetInputs.addConstantRadiusEdgeSet(
        seat_edges(body), adsk.core.ValueInput.createByReal(SEAT_FILLET / 10), True)
    blend = fillets.add(options)
    front().healthy(blend, "Seat edge fillet")
    blend.name = "P02 ear-seat outer edges R%.1f" % SEAT_FILLET
    names.append(blend.name)
    body = component.bRepBodies.itemByName(PLATE)
    tools().one_solid(body, "Revised P02")
    return body, names


def prototype_plate(app):
    s, _ = geometry()
    identity(STATE["matrices"][PLATE], PLATE)
    joins, cuts = plate_tools()
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "TEMP - P02 v23 prototype"
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        component = design.rootComponent
        base = component.features.baseFeatures.add()
        if not base.startEdit():
            raise RuntimeError("Could not start the P02 prototype input")
        try:
            component.bRepBodies.add(s.tbm().copy(STATE["definitions"][PLATE]), base)
        finally:
            if not base.finishEdit():
                raise RuntimeError("Could not finish the P02 prototype input")
        base.bodies.item(0).name = PLATE
        body, names = native_plate(component, joins, cuts)
        STATE["candidates"][PLATE] = s.tbm().copy(body)
        STATE["plate_tools"] = (s.tbm().copy(joins), s.tbm().copy(cuts))
        added = s.tbm().copy(body)
        s.op(added, s.tbm().copy(STATE["definitions"][PLATE]), "cut")
        removed = s.tbm().copy(STATE["definitions"][PLATE])
        s.op(removed, s.tbm().copy(body), "cut")
        report = {"features": names, "before": tools().stats(STATE["definitions"][PLATE]),
                  "candidate": tools().stats(body),
                  "added_mm3": added.volume * 1000, "removed_mm3": removed.volume * 1000}
        write("P02_candidate.json", report)
        return report
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the P02 prototype document")
        source.activate()


def hardware_world():
    s, _ = geometry()

    def screw(z):
        head = s.cyl(AXIS_X, z, -13.7 - SCREW_HEAD_H, -13.7, SCREW_HEAD_R)
        s.op(head, s.cyl(AXIS_X, z, -13.7, -13.7 + SCREW_L, SCREW_R), "join")
        return head

    envelope = s.box(4.4, 16.6, -30.9, -6.76, 33.86, 56.82)
    s.op(envelope, s.box(4.4, 16.6, -13.7, SEAT_Y, 29.26, 61.57), "join")
    s.op(envelope, s.cyl(AXIS_X, SHAFT_Z, -7.0, -2.66, 6.1), "join")
    s.op(envelope, s.cyl(10.55, 44.62, -7.0, -2.7, 3.0), "join")
    for z in (NEAR_Z, FAR_Z):
        s.op(envelope, s.cyl(AXIS_X, z, -13.8, SEAT_Y + 0.1, 1.25), "cut")
    return {NEAR_SCREW: screw(NEAR_Z), FAR_SCREW: screw(FAR_Z), ENVELOPE: envelope}


def hardware_candidates():
    """Native-frame shapes for the replaced references, placed with their original contexts."""
    s, _ = geometry()
    world = hardware_world()
    for old, new in REPLACED.items():
        STATE["matrices"][new] = STATE["matrices"][old].copy()
        STATE["paths"][new] = STATE["paths"][old]
    for name, shape in world.items():
        native = s.tbm().copy(shape)
        inverse = STATE["matrices"][name].copy()
        inverse.invert()
        if not s.tbm().transform(native, inverse):
            raise RuntimeError("Could not move a reference into its component frame: " + name)
        tools().one_solid(native, name)
        STATE["candidates"][name] = native
    contained = {}
    for servo, parts in servo_shells().items():
        rows = {}
        for part, shape in parts:
            outside = s.tbm().copy(shape)
            s.op(outside, s.tbm().copy(world[ENVELOPE]), "cut")
            rows[part] = {"part_mm3": shape.volume * 1000,
                          "outside_envelope_mm3": outside.volume * 1000 if outside.lumps.count else 0.0,
                          "outside_bounds_mm": tools().bounds(outside) if outside.lumps.count else None}
        contained[servo] = rows
    report = {n: tools().stats(world[n]) for n in world}
    report["servo_parts_outside_union_envelope"] = contained
    write("hardware_candidates.json", report)
    return report


def world_of(name):
    s, _ = geometry()
    if name in STATE["candidates"]:
        shape = s.tbm().copy(STATE["candidates"][name])
        if not s.tbm().transform(shape, STATE["matrices"][name]):
            raise RuntimeError("Candidate placement failed: " + name)
        return shape
    return STATE["world"][name]


def after_world():
    world = {n: sh for n, sh in STATE["world"].items() if n not in RETIRED and n not in REPLACED}
    for name in STATE["candidates"]:
        world[name] = world_of(name)
    return world


def group(name):
    return STATE["paths"][name][:2]


def overlaps(shape, others):
    s, _ = geometry()
    rows = {}
    for name, other in others.items():
        volume, common = s.common_volume(shape, other)
        if volume > 1e-5:
            rows[name] = {"overlap_mm3": volume, "bounds_mm": tools().bounds(common)}
    return rows


def thread_engagement_ok(row, z):
    lo, hi = row["bounds_mm"]
    return (row["overlap_mm3"] <= 8.0 and abs((lo[0] + hi[0]) / 2 - AXIS_X) < .05
            and abs((lo[2] + hi[2]) / 2 - z) < .05 and hi[0] - lo[0] <= 2 * SCREW_R + 1e-6)


def audit_static():
    """Every changed fixed reference against every other fixed body after the change."""
    world = after_world()
    before = STATE["world"]
    fixed = {n for n in world if group(n) not in g22().MOVING}
    report = {}
    for name in STATE["candidates"]:
        others = {n: world[n] for n in fixed if n != name and not n.startswith("REFERENCE_")}
        rows = overlaps(world[name], others)
        baseline = overlaps(before[name], {n: before[n] for n in before
                                           if n != name and group(n) not in g22().MOVING}) \
            if name in before else {}
        accepted, new = {}, {}
        for other, row in rows.items():
            pair = {name, other}
            if pair == {PLATE, NEAR_SCREW} and thread_engagement_ok(row, NEAR_Z) or \
                    pair == {PLATE, FAR_SCREW} and thread_engagement_ok(row, FAR_Z):
                accepted[other] = dict(row, reason="M2 self-tapping thread engagement in the 1.7 mm pilot")
            elif any(k in other.upper() for k in ("HEATSET", "INSERT")) and row["overlap_mm3"] <= 16.25 \
                    and other in baseline:
                accepted[other] = dict(row, reason="unchanged pre-existing heat-set install")
            elif other in baseline and row["overlap_mm3"] <= baseline[other]["overlap_mm3"] + 1e-4:
                accepted[other] = dict(row, reason="unchanged pre-existing contact",
                                       baseline_mm3=baseline[other]["overlap_mm3"])
            else:
                new[other] = row
        report[name] = {"accepted": accepted, "new_clashes": new, "baseline": baseline}
    write("static_audit.json", report)
    STATE["static"] = report
    return {n: {"new": list(r["new_clashes"]), "accepted": list(r["accepted"])} for n, r in report.items()}


def audit_servos():
    """Both real STEP servos, seated at Y-11.2, against every fixed body and the cam socket."""
    s, _ = geometry()
    world = after_world()
    fixed = {n: world[n] for n in world if group(n) not in g22().MOVING
             and n not in (ENVELOPE, NEAR_SCREW, FAR_SCREW) and not n.startswith("REFERENCE_")}
    cam = {n: world[n] for n in world if group(n) == "10"}
    data = STATE.get("step_data") or step_data()
    report = {}
    for servo, parts in servo_shells().items():
        rows = {}
        for part, shape in parts:
            rows[part] = {"fixed": overlaps(shape, fixed), "cam_group": overlaps(shape, cam)}
        tip = data[servo]["shaft_tip_y"] + data[servo]["seat_shift_mm"]
        report[servo] = {"parts": rows, "seated_shaft_tip_y": tip,
                         "spline_tip_to_cam_socket_floor_mm": SOCKET_FLOOR_Y - tip,
                         "seated_ear_top_y": SEAT_Y, "seat_shift_mm": data[servo]["seat_shift_mm"]}
    write("servo_step_fit.json", report)
    STATE["servo_fit"] = report
    return {servo: {"fixed_overlaps": sorted({o for r in v["parts"].values() for o in r["fixed"]}),
                    "cam_overlaps": sorted({o for r in v["parts"].values() for o in r["cam_group"]}),
                    "tip_clearance_mm": v["spline_tip_to_cam_socket_floor_mm"]}
            for servo, v in report.items()}


def clearances(app):
    """Minimum servo-to-plate distances with the intended ear-seat face contact removed.

    The top 0.6 mm of each ear (outside the case footprint) is clipped away, so a reported
    0.6 mm is that artefact; anything smaller is a real clearance elsewhere.
    """
    s, _ = geometry()
    measure = app.measureManager
    plate = world_of(PLATE)
    rows = {}
    for servo, parts in servo_shells().items():
        for part, shape in parts:
            clipped = s.tbm().copy(shape)
            for z0, z1 in ((28.0, 33.86), (56.72, 62.6)):
                s.op(clipped, s.box(4.0, 17.0, SEAT_Y - 0.6, SEAT_Y + 0.001, z0, z1), "cut")
            if not clipped.lumps.count:
                continue
            result = measure.measureMinimumDistance(clipped, plate)
            rows[servo + "|" + part] = result.value * 10
    write("servo_plate_min_distance.json", rows)
    return rows


def motor_path():
    """Repeat the v19 rotate-slide-rotate loose-plate installation with the bosses."""
    s, m = geometry()
    axis = tools().parameters()["motor_axis_xz_mm"]
    fixed = {n: sh for n, sh in STATE["world"].items() if n.startswith("AHG ") and not n.startswith(
        ("AHG lead red", "AHG lead green", "AHG lead yellow", "AHG lead blue"))}
    if len(fixed) != 5:
        raise RuntimeError("Expected five rigid motor parts, found %d" % len(fixed))
    plate = world_of(PLATE)
    stages = [("rotate loose plate clear of motor", [(a, -40.0) for a in range(0, -136, -5)]),
              ("slide keyed plate over rigid connector", [(-135.0, -40.0 + i * .5) for i in range(81)]),
              ("rotate seated plate back onto motor ear datum", [(a, 0.0) for a in range(-135, 1, 5)])]
    rows = []
    for stage, poses in stages:
        for angle, dy in poses:
            moved = m.translated(m.rotated(s.tbm().copy(plate), axis, angle), dy=dy)
            hits = [{"motor_part": n, "overlap_mm3": v} for n, sh in fixed.items()
                    for v in [s.common_volume(moved, sh)[0]] if v > 1e-5]
            rows.append({"stage": stage, "plate_clock_deg": angle, "plate_offset_y_mm": dy, "hits": hits})
    write("motor_insertion_path.json", {"poses": rows, "rigid_motor_parts": sorted(fixed)})
    return {"poses": len(rows), "poses_with_hits": sum(bool(r["hits"]) for r in rows)}


def audit_motion(angles):
    with bound(placement=True) as module:
        plate = module.audit_motion_fast(PLATE, angles, "v23_P02")
        envelope = module.audit_motion_fast(ENVELOPE, angles, "v23_envelope")
    return {"P02": plate, "envelope": envelope}


def audit_tool():
    with bound(placement=True) as module:
        return module.audit_tool([PLATE, ENVELOPE, NEAR_SCREW, FAR_SCREW], "v23")


def replace_reference(component, old_body, name, shape, label):
    s, _ = geometry()
    count = component.bRepBodies.count
    look = old_body.appearance
    remove = component.features.removeFeatures.add(old_body)
    remove.name = "V23 retire " + old_body.name
    feature = component.features.baseFeatures.add()
    feature.name = "V23 reference " + name
    if not feature.startEdit():
        raise RuntimeError("Could not start the updated reference " + name)
    try:
        component.bRepBodies.add(s.tbm().copy(shape), feature)
    finally:
        if not feature.finishEdit():
            raise RuntimeError("Could not finish the updated reference " + name)
    body = feature.bodies.item(0)
    body.name = name
    if look is not None:
        body.appearance = look
    if component.bRepBodies.count != count:
        raise RuntimeError("Replacing a reference changed the component inventory: " + name)
    delta = front().exact(shape, body, "v23 reference " + name)
    if delta:
        raise RuntimeError("The live reference differs from review: " + name)
    component.name = label
    return body


def apply_live(app, ui):
    """Apply the reviewed P02 and hardware references once over the exact captured inputs."""
    if STATE.get("applied"):
        raise RuntimeError("v23 was already applied")
    g22().require_idle(ui, allow_view=False)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the captured live assembly")
    if design.timeline.count != STATE["timeline_count"]:
        raise RuntimeError("The user changed the live timeline after capture; recapture first")
    by, _ = front().inventory(design)
    for name in (PLATE, ENVELOPE) + tuple(REPLACED) + RETIRED:
        if front().exact(STATE["definitions"][name], by[name].nativeObject, "live " + name):
            raise RuntimeError("A live body changed after capture: " + name)
    identity(by[PLATE].assemblyContext.transform2, PLATE)
    plate = by[PLATE].nativeObject
    plate_component = plate.parentComponent
    joins, cuts = STATE["plate_tools"]
    result, names = native_plate(plate_component, joins, cuts)
    delta = front().exact(STATE["candidates"][PLATE], result, "applied P02 v23")
    if delta:
        raise RuntimeError("The live P02 differs from the reviewed candidate: %.6f mm3" % delta)
    plate_component.name = "P02 v23 7mm plate - MG90S-MG90D ear-seat bosses"
    report = {"P02_features": names, "P02_exact_difference_mm3": delta}
    env = by[ENVELOPE].nativeObject
    replace_reference(env.parentComponent, env, ENVELOPE, STATE["candidates"][ENVELOPE],
                      "MG90S + MG90D STEP envelope - ear seat Y-11.2")
    for old, new in REPLACED.items():
        body = by[old].nativeObject
        replace_reference(body.parentComponent, body, new, STATE["candidates"][new],
                          "MG90 M2x8 self-tapping - %s ear" % ("near" if new == NEAR_SCREW else "far"))
    for old in RETIRED:
        body = by[old].nativeObject
        owner = body.parentComponent
        remove = owner.features.removeFeatures.add(body)
        remove.name = "V23 retire " + old
        owner.name = "RETIRED v23 - " + owner.name
    by_after, _ = front().inventory(design)
    expected = set(STATE["definitions"]) - set(RETIRED) - set(REPLACED) | set(REPLACED.values())
    if set(by_after) != expected:
        raise RuntimeError("Unexpected body inventory after v23: %s" % sorted(set(by_after) ^ expected))
    STATE["applied"] = True
    STATE["timeline_after"] = design.timeline.count
    report.update(timeline_after=design.timeline.count, bodies_after=len(by_after),
                  plate=tools().stats(result))
    write("live_application.json", report)
    return report


def freeze(app, label="SparkShift_v23_P02_MG90S_MG90D_ear_seats_WIP"):
    with bound() as module:
        return module.freeze(app, label)


def readback(app, count=200):
    """Reopen the frozen archive; compare every body and placement with the reviewed state."""
    if not STATE.get("archive"):
        raise RuntimeError("Freeze the archive first")
    source = next(d for d in app.documents if d.creationId == STATE["document"])
    if not STATE.get("readback_document"):
        path = Path(STATE["archive"]["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != STATE["archive"]["sha256"]:
            raise RuntimeError("The frozen archive changed")
        document = app.importManager.importToNewDocument(
            app.importManager.createFusionArchiveImportOptions(str(path)))
        if document is None:
            raise RuntimeError("Could not reopen the frozen archive")
        STATE["readback_document"] = document.creationId
        STATE["readback_rows"] = []
    document = next(d for d in app.documents if d.creationId == STATE["readback_document"])
    document.activate()
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        by, _ = front().inventory(design)
        expected = set(STATE["definitions"]) - set(RETIRED) - set(REPLACED) | set(REPLACED.values())
        if set(by) != expected:
            raise RuntimeError("The reopened physical inventory differs")
        rows = STATE["readback_rows"]
        if any(r["difference_mm3"] or r["placement_max_delta"] > 1e-8 for r in rows):
            raise RuntimeError("A failed readback row cannot be skipped")
        names = sorted(by)
        for name in names[len(rows):len(rows) + count]:
            shape = STATE["candidates"].get(name, STATE["definitions"].get(name))
            body = by[name].nativeObject
            tools().one_solid(body, "Reopened " + name)
            delta = front().exact(shape, body, "v23 readback " + name)
            placement = max(abs(a - b) for a, b in zip(STATE["matrices"][name].asArray(),
                                                      by[name].assemblyContext.transform2.asArray()))
            rows.append({"body": name, "difference_mm3": delta, "placement_max_delta": placement,
                         "changed_in_v23": name in STATE["candidates"]})
            write("native_archive_readback.json", {"archive_sha256": STATE["archive"]["sha256"],
                                                   "checked": rows, "complete": len(rows) == len(names)})
            if delta or placement > 1e-8:
                raise RuntimeError("Reopened geometry or placement differs: " + name)
        complete = len(rows) == len(names)
        STATE["readback_complete"] = complete
        return {"checked": len(rows), "total": len(names), "complete": complete}
    finally:
        source.activate()


def close_readback(app):
    with bound() as module:
        return module.close_readback(app)


def export_plate(app):
    with bound() as module:
        saved = module.PRINTS
        module.PRINTS = {PLATE: ("P02_servo_plate_MG90S_MG90D_ear_seats_v23", (0, -1, 0))}
        try:
            return module.export_meshes(app)
        finally:
            module.PRINTS = saved
