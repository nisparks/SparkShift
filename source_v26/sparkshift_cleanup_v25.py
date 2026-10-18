"""v25: deliberate cleanup of holes, slivers and broken geometry left by earlier passes.

Principles: no unintended through-holes (genus checked), no slivers or micro-steps, and
every clearance is a simple analytic shape (plane or pivot/cam-centred cylinder) with a
uniform gap.  Preserve the user's live edits and apply only with exact-match guards.
"""

import hashlib
import json
import math
import sys
from contextlib import contextmanager
from pathlib import Path

import adsk.core
import adsk.fusion


OUT = Path(__file__).resolve().parent / "sparkshift_cleanup_v25"
P01 = "PRINT_motor_mount"
P02 = "PRINT_REAR_MOTOR_SERVO_SPACER"
P03 = "PRINT_000_outer_shell_of_extruder_1"
P04R = "PRINT_carrier_box_left"
P04F = "PRINT_arm_front_half"
STATE = {}


def g22():
    return sys.modules["sparkshift_blue_half_v22"]


def v24():
    return sys.modules["sparkshift_coupling_v24"]


def front():
    return sys.modules["sparkshift_front_half_only_v21"]


def tools():
    return sys.modules["sparkshift_open_frame_v19"]


def geometry():
    return tools().geometry()


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


@contextmanager
def bound(placement=False):
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
    with bound() as module:
        report = module.capture(app, ui, "USER_live_input_v25")
    STATE["candidates"] = {}
    return report


def world_of(name):
    s, _ = geometry()
    if name in STATE.get("candidates", {}):
        shape = s.tbm().copy(STATE["candidates"][name])
        if not s.tbm().transform(shape, STATE["matrices"][name]):
            raise RuntimeError("Candidate placement failed: " + name)
        return shape
    return STATE["world"][name]


def render_close(app, items, views, label, size=(1600, 1200)):
    """Orthographic close-ups with explicit target and extents in an owned temporary document."""
    s, _ = geometry()
    source = app.activeDocument
    design_source = adsk.fusion.Design.cast(source.products.itemByProductType("DesignProductType"))
    looks = {}
    for body in front().inventory(design_source)[0].values():
        looks.setdefault(body.appearance.name, body.appearance)
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.activate()
    document.name = "TEMP - v25 close-up render"
    files = []
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent
        feature = root.features.baseFeatures.add()
        if not feature.startEdit():
            raise RuntimeError("Could not start render bodies")
        try:
            for shape, _ in items:
                root.bRepBodies.add(s.tbm().copy(shape), feature)
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish render bodies")
        for body, (_, look) in zip(feature.bodies, items):
            if look in looks:
                existing = design.appearances.itemByName(look)
                body.appearance = existing or design.appearances.addByCopy(looks[look], look)
        viewport = app.activeViewport
        for name, target, direction, up, extent in views:
            camera = viewport.camera
            camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
            camera.isFitView = False
            camera.isSmoothTransition = False
            eye = [target[i] - direction[i] * 200 for i in range(3)]
            camera.target = adsk.core.Point3D.create(*(v / 10 for v in target))
            camera.eye = adsk.core.Point3D.create(*(v / 10 for v in eye))
            camera.upVector = adsk.core.Vector3D.create(*up)
            camera.viewExtents = extent / 10
            viewport.camera = camera
            viewport.refresh()
            adsk.doEvents()
            path = OUT / "images" / (label + "_" + name + ".png")
            path.parent.mkdir(parents=True, exist_ok=True)
            if not viewport.saveAsImageFile(str(path), *size):
                raise RuntimeError("Could not save " + path.name)
            files.append(str(path))
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the render document")
        source.activate()
    return files


def genus(body):
    v, e, f = body.vertices.count, body.edges.count, body.faces.count
    loops = sum(face.loops.count for face in body.faces)
    shells = sum(lump.shells.count for lump in body.lumps)
    return shells - (v - e + 2 * f - loops) / 2


def centre(entity):
    b = entity.boundingBox
    return [(b.minPoint.x + b.maxPoint.x) * 5, (b.minPoint.y + b.maxPoint.y) * 5,
            (b.minPoint.z + b.maxPoint.z) * 5]


def artifacts(body, tiny_area=0.05, thin=0.08, short=0.03, tilt=(1e-3, 3.0)):
    """Faces and edges that are almost always unintended: micro faces, thin bands, near-axis tilts."""
    rows = []
    for i, face in enumerate(body.faces):
        g = face.geometry
        area = face.area * 100
        b = face.boundingBox
        dims = sorted([(b.maxPoint.x - b.minPoint.x) * 10, (b.maxPoint.y - b.minPoint.y) * 10,
                       (b.maxPoint.z - b.minPoint.z) * 10])
        kind = None
        if area < tiny_area:
            kind = "micro_face"
        elif isinstance(g, (adsk.core.Cylinder, adsk.core.Cone)):
            a = g.axis
            ext = (abs(a.x) * (b.maxPoint.x - b.minPoint.x) + abs(a.y) * (b.maxPoint.y - b.minPoint.y)
                   + abs(a.z) * (b.maxPoint.z - b.minPoint.z)) * 10
            if ext < thin and abs(abs(a.x) + abs(a.y) + abs(a.z) - 1) < 1e-6:
                kind = "thin_band"
        elif isinstance(g, adsk.core.Plane):
            n = g.normal
            dev = math.degrees(math.acos(min(1.0, max(abs(n.x), abs(n.y), abs(n.z)))))
            if tilt[0] < dev < tilt[1]:
                kind = "near_axis_tilt_%.3fdeg" % dev
            elif dims[1] < thin:
                kind = "sliver_plane"
        if kind:
            rows.append({"face": i, "kind": kind, "type": type(g).__name__, "area_mm2": area,
                         "centre_mm": centre(face), "dims_mm": dims})
    edges = [{"edge": j, "length_mm": e.length * 10, "centre_mm": centre(e)}
             for j, e in enumerate(body.edges) if e.length * 10 < short]
    return {"faces": rows, "short_edges": edges, "genus": genus(body), "face_count": body.faces.count}


CAM_X, CAM_Z = 10.5, 50.72059521522819
PIVOT_X, PIVOT_Z = 9.5, 13.099982791045502
SLOT_N = (-0.9942782700235946, -0.10682097995659799)
SLOT_R = 33.90199763725427
HS_X, HS_Z = 18.1, 41.72
RELIEF_A = (-0.622256706275615, 42.20333922703023, 9.0)
CORNER_O = (9.538816329595848, 48.80515856399153)
CORNER_N = (0.7622513650115522, 0.6472811263570301)
Y_BACK, Y_SLOT, Y_SHOULDER, Y_CROWN, Y_BOSS, Y_BUMP, Y_FRONT = 0.3, 2.2, 2.45, 3.0, 4.05, 4.55, 11.4
R_ROI, R_HOUSING, R_BOSS, R_SEAT, R_BORE = 9.62, 8.5, 7.1, 6.025, 5.5
R_BUMP, R_POCKET, R_HOLE = 3.3, 2.0, 1.7
X_BLOCK, Z_CROWN = 13.5, 53.5


def slab(origin, normal, y0, y1, depth=200.0, span=400.0):
    """Half-space {n.(p - o) in [0, depth]} between two Y planes (XZ origin and normal, mm)."""
    s, _ = geometry()
    nx, nz = normal
    centre = adsk.core.Point3D.create((origin[0] + nx * depth / 2) / 10, (y0 + y1) / 20,
                                      (origin[1] + nz * depth / 2) / 10)
    return s.tbm().createBox(adsk.core.OrientedBoundingBox3D.create(
        centre, adsk.core.Vector3D.create(nx, 0, nz), adsk.core.Vector3D.create(0, 1, 0),
        depth / 10, (y1 - y0) / 10, span / 10))


def crown_tools():
    """One analytic rebuild of the MR128 housing, cam boss, crown face and cam bore.

    Inside one R9.62 cylinder about the cam axis everything is replaced by: the R6.025
    bearing seat to the Y2.45 shoulder, an R5.5 bore, an R7.1 boss to Y4.05, an R8.5
    housing ring to Y2.2 (0.3 mm behind the swing arm), the crown front face at Y3.0
    and one R9.62 cam bore from Y3.0 to the front face.  The M3 heat-set gets an R3.3
    boss ending 0.3 mm behind the cam lobes.  Two tangent-circle slivers are absorbed.
    """
    s, _ = geometry()

    def c(x, z, y0, y1, r):
        return s.cyl(x, z, y0, y1, r)

    roi = c(CAM_X, CAM_Z, Y_BACK - 0.1, Y_FRONT + 0.1, R_ROI)
    plate = c(CAM_X, CAM_Z, Y_BACK, Y_CROWN, R_ROI)
    s.op(plate, s.box(-100, X_BLOCK, -1, 20, -100, Z_CROWN), "cut")
    slot = slab((PIVOT_X, PIVOT_Z), SLOT_N, Y_SLOT, Y_CROWN + 0.5)
    s.op(slot, c(PIVOT_X, PIVOT_Z, Y_SLOT - 0.1, Y_CROWN + 0.6, SLOT_R), "cut")
    s.op(plate, slot, "cut")
    fill = s.op(plate, c(CAM_X, CAM_Z, Y_BACK, Y_SLOT, R_HOUSING), "join")
    s.op(fill, c(CAM_X, CAM_Z, Y_SLOT, Y_BOSS, R_BOSS), "join")
    s.op(fill, c(HS_X, HS_Z, Y_BACK, Y_BUMP, R_BUMP), "join")
    counterbore = c(HS_X, HS_Z, 4.4, 4.7, 2.8)
    s.op(counterbore, c(CAM_X, CAM_Z, 4.3, 4.8, R_ROI), "cut")
    s.op(fill, counterbore, "join")
    ax, az, ar = RELIEF_A
    relief = s.box(-9.9, -8.9, 7.45, Y_FRONT, 39.0, 40.8)
    s.op(relief, c(ax, az, 7.0, 12.0, ar), "cut")
    s.op(fill, relief, "join")
    corner = s.box(14.9, 15.7, 6.0, Y_FRONT, 42.0, 42.9)
    s.op(corner, slab(CORNER_O, CORNER_N, 5.9, Y_FRONT + 0.1), "common")
    s.op(corner, c(CAM_X, CAM_Z, 5.9, Y_FRONT + 0.1, R_ROI), "cut")
    s.op(corner, c(17.2, 40.0, 5.9, Y_FRONT + 0.1, 2.75), "cut")
    s.op(fill, corner, "join")
    cut = c(CAM_X, CAM_Z, Y_BACK - 0.1, Y_SHOULDER, R_SEAT)
    s.op(cut, c(CAM_X, CAM_Z, Y_SHOULDER - 0.05, Y_BOSS + 0.1, R_BORE), "join")
    s.op(cut, c(HS_X, HS_Z, Y_BACK - 0.1, Y_BUMP, R_POCKET), "join")
    s.op(cut, c(HS_X, HS_Z, Y_BUMP - 0.05, Y_FRONT + 0.1, R_HOLE), "join")
    return {"roi": roi, "fill": fill, "cut": cut}


def build_p01(source=None):
    s, _ = geometry()
    t = crown_tools()
    body = s.tbm().copy(source or STATE["definitions"][P01])
    s.op(body, s.tbm().copy(t["roi"]), "cut")
    s.op(body, s.tbm().copy(t["fill"]), "join")
    s.op(body, s.tbm().copy(t["cut"]), "cut")
    STATE["p01_tools"] = t
    return body


def delta_lumps(before, after):
    """Material added and removed, as separate lumps with volume and bounds."""
    s, _ = geometry()
    out = {}
    for label, a, b in (("added", after, before), ("removed", before, after)):
        d = s.tbm().copy(a)
        s.op(d, s.tbm().copy(b), "cut")
        out[label] = sorted(({"volume_mm3": l.volume * 1000, "bounds_mm": tools().bounds(l)}
                             for l in d.lumps), key=lambda r: -r["volume_mm3"])
    return out


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


def audit_static(part):
    """Candidate against every fixed body, versus the captured baseline overlaps."""
    moving = g22().MOVING
    others = {n: STATE["world"][n] for n in STATE["world"]
              if n != part and group(n) not in moving and not n.startswith("REFERENCE_")}
    base = overlaps(STATE["world"][part], others)
    rows = overlaps(world_of(part), others)
    accepted, new = {}, {}
    for name, row in rows.items():
        old = base.get(name)
        if old is not None and row["overlap_mm3"] <= old["overlap_mm3"] + 1e-4:
            accepted[name] = dict(row, baseline_mm3=old["overlap_mm3"])
        else:
            new[name] = dict(row, baseline_mm3=old["overlap_mm3"] if old else 0.0)
    report = {"accepted_unchanged": accepted, "new_clashes": new, "baseline": base,
              "checked_bodies": len(others)}
    STATE.setdefault("static", {})[part] = report
    write("static_audit_%s.json" % part, report)
    return {"new": {n: r["overlap_mm3"] for n, r in new.items()},
            "accepted": {n: r["overlap_mm3"] for n, r in accepted.items()}, "checked": len(others)}


def audit_motion(part, angles, label):
    with bound(placement=True) as module:
        return module.audit_motion_fast(part, angles, label)


def audit_tool(parts, label):
    with bound(placement=True) as module:
        return module.audit_tool(parts, label)


def audit_feed(parts, label):
    with bound(placement=True) as module:
        return module.audit_feed(parts, range(0, 360, 15), label)


def added_clearance(part, label, arm_samples=33, cam_samples=73):
    """Minimum distance from the material added to `part` to every moving body over the motion."""
    s, _ = geometry()
    module = g22()
    measure = adsk.core.Application.get().measureManager
    before, after = STATE["definitions"][part], STATE["candidates"][part]
    added = s.tbm().copy(after)
    s.op(added, s.tbm().copy(before), "cut")
    lumps = [l for l in added.lumps if l.volume * 1000 > 1e-3]
    pieces = []
    for lump in lumps:
        piece = s.tbm().copy(added)
        b = lump.boundingBox
        clip = s.box(b.minPoint.x * 10 - 0.01, b.maxPoint.x * 10 + 0.01, b.minPoint.y * 10 - 0.01,
                     b.maxPoint.y * 10 + 0.01, b.minPoint.z * 10 - 0.01, b.maxPoint.z * 10 + 0.01)
        s.op(piece, clip, "common")
        if not s.tbm().transform(piece, STATE["matrices"][part]):
            raise RuntimeError("Placement failed")
        pieces.append((piece, tools().bounds(piece), lump.volume * 1000))
    player = STATE["player"]
    data = player.load_data()[0]
    angles = [i * 175.0 / (cam_samples - 1) for i in range(cam_samples)]
    arm_angles = sorted({round(player.arm_angle(data, a), 6) for a in angles})
    if len(arm_angles) > arm_samples:
        step = (len(arm_angles) - 1) / (arm_samples - 1)
        arm_angles = sorted({arm_angles[round(i * step)] for i in range(arm_samples)})
    rows = {}
    with bound(placement=True):
        for angle in angles:
            arm, frame_map = module.frames(float(angle))
            for other, path in STATE["paths"].items():
                group_id = path[:2]
                if group_id not in module.MOVING or other.startswith("REFERENCE_"):
                    continue
                if group_id != "10" and round(arm, 6) not in arm_angles:
                    continue
                shape = module.place(other, module.world_of(other), frame_map)
                for index, (piece, box, volume) in enumerate(pieces):
                    distance = measure.measureMinimumDistance(piece, shape).value * 10
                    key = (index, other)
                    if key not in rows or distance < rows[key]["min_mm"]:
                        rows[key] = {"lump": index, "lump_mm3": volume, "lump_bounds": box, "other": other,
                                     "min_mm": distance, "cam_deg": angle, "arm_deg": arm}
    report = sorted(rows.values(), key=lambda r: r["min_mm"])
    write(label + "_added_clearance.json", report)
    return [{"lump": r["lump"], "other": r["other"], "min_mm": round(r["min_mm"], 4),
             "cam": round(r["cam_deg"], 2), "arm": round(r["arm_deg"], 3)} for r in report[:12]]


def native_build(component, part, steps):
    """Apply (label, shape, operation) tool steps to `part` with base features and combines."""
    s, _ = geometry()
    names = []
    for label, shape, operation in steps:
        feature = component.features.baseFeatures.add()
        feature.name = "V25 TOOL " + label
        if not feature.startEdit():
            raise RuntimeError("Could not start " + label)
        try:
            component.bRepBodies.add(s.tbm().copy(shape), feature)
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish " + label)
        collection = adsk.core.ObjectCollection.create()
        collection.add(feature.bodies.item(0))
        options = component.features.combineFeatures.createInput(component.bRepBodies.itemByName(part),
                                                                 collection)
        options.operation = operation
        options.isKeepToolBodies = False
        combine = component.features.combineFeatures.add(options)
        front().healthy(combine, label)
        combine.name = label
        names.append(label)
    body = component.bRepBodies.itemByName(part)
    tools().one_solid(body, "Revised " + part)
    return body, names


def p01_steps():
    t = STATE["p01_tools"]
    cut, join = (adsk.fusion.FeatureOperations.CutFeatureOperation,
                 adsk.fusion.FeatureOperations.JoinFeatureOperation)
    return [("P01 clear cam housing region R9.62", t["roi"], cut),
            ("P01 analytic housing, boss, crown face and insert boss", t["fill"], join),
            ("P01 MR128 seat, R5.5 bore and M3 insert pocket", t["cut"], cut)]


def prototype(app, part, steps):
    """Run the native features in a temporary document; the native result becomes the candidate."""
    s, _ = geometry()
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "TEMP - v25 %s prototype" % part
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        component = design.rootComponent
        base = component.features.baseFeatures.add()
        if not base.startEdit():
            raise RuntimeError("Could not start the prototype input")
        try:
            component.bRepBodies.add(s.tbm().copy(STATE["definitions"][part]), base)
        finally:
            if not base.finishEdit():
                raise RuntimeError("Could not finish the prototype input")
        base.bodies.item(0).name = part
        body, names = native_build(component, part, steps)
        native = s.tbm().copy(body)
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the prototype document")
        source.activate()
    reference = STATE["candidates"].get(part)
    delta = front().exact(reference, native, "native vs TBM " + part) if reference is not None else None
    STATE["candidates"][part] = native
    report = {"features": names, "native_vs_reviewed_mm3": delta, "before": tools().stats(STATE["definitions"][part]),
              "candidate": tools().stats(native), "genus": [genus(STATE["definitions"][part]), genus(native)]}
    write("%s_native_candidate.json" % part, report)
    return report


def apply_live(app, ui, part, steps):
    applied = STATE.setdefault("applied", [])
    g22().require_idle(ui, allow_view=False)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the captured live assembly")
    if design.timeline.count != STATE["timeline_count"]:
        raise RuntimeError("The live timeline changed since capture/last apply; recapture first")
    by, _ = front().inventory(design)
    body = by[part].nativeObject
    if front().exact(STATE["definitions"][part], body, "live %s before v25" % part):
        raise RuntimeError("The live %s changed after capture" % part)
    result, names = native_build(body.parentComponent, part, steps)
    delta = front().exact(STATE["candidates"][part], result, "applied %s v25" % part)
    if delta:
        raise RuntimeError("The live %s differs from the reviewed candidate: %.6f mm3" % (part, delta))
    s, _ = geometry()
    STATE["timeline_count"] = design.timeline.count
    STATE["definitions"][part] = s.tbm().copy(STATE["candidates"][part])
    STATE["world"][part] = world_of(part)
    applied.append({"part": part, "features": names, "timeline_after": design.timeline.count})
    write("live_application.json", applied)
    return applied[-1]


RAIL_O, RAIL_N = (-9.763750262446338, 46.929005699540426), (-0.991440936995337, -0.1305559973720412)
CROWN45_O, CROWN45_N = (-15.5, 55.11029760761409), (-0.7126123342557662, 0.7015580240197872)
SLOT_STRIPS = ((-19.188508250390942, -19.17940478477181), (-25.779404784771813, -25.77030131915268),
               (-49.78850825039093, -49.779404784771806), (-56.37940478477181, -56.37030131915267))


def p01_pass2_tools(nick_centre):
    """Snap the remaining sub-0.1 mm steps on P01 to the surfaces they belong to."""
    s, _ = geometry()
    neg = lambda n: (-n[0], -n[1])
    rail_x = -9.857481548826328
    fill = s.box(-10.0, rail_x, Y_BACK, 2.08, 47.6, 50.95)
    s.op(fill, s.box(-10.0, rail_x, 2.0, Y_SLOT, 47.6, 48.75), "join")
    rail = s.box(-11.8, -10.0, 6.7, Y_FRONT, 51.6, 59.6)
    s.op(rail, slab(RAIL_O, RAIL_N, 6.6, Y_FRONT + 0.1), "common")
    s.op(rail, slab(CROWN45_O, neg(CROWN45_N), 6.6, Y_FRONT + 0.1), "common")
    s.op(fill, rail, "join")
    nick = s.cyl(nick_centre[0], nick_centre[1], 6.0, Y_FRONT, 3.3)
    s.op(nick, s.box(20.5, 20.7, 5.9, Y_FRONT + 0.1, 20.0, 27.0), "common")
    s.op(fill, nick, "join")
    for sign in (1, -1):
        x0, x1 = sorted((sign * 22.2, sign * 22.5))
        s.op(fill, s.box(x0, x1, Y_BACK, 0.6, -18.37940478477181, -18.27940478477181), "join")
        a0, a1 = sorted((sign * 4.1, sign * 6.7))
        for z0, z1 in SLOT_STRIPS:
            s.op(fill, s.box(a0, a1, Y_BACK, 5.3, z0, z1), "join")
    cut = s.box(-11.8, -10.0, 6.7, Y_FRONT, 55.0, 59.6)
    s.op(cut, slab(RAIL_O, neg(RAIL_N), 6.6, Y_FRONT + 0.1), "common")
    s.op(cut, slab(CROWN45_O, neg(CROWN45_N), 6.6, Y_FRONT + 0.1), "common")
    return {"fill": fill, "cut": cut}


def p01_pass2_steps():
    t = STATE["p01_pass2_tools"]
    return [("P01 snap rail, slot ends and edge stubs to their faces", t["fill"],
             adsk.fusion.FeatureOperations.JoinFeatureOperation),
            ("P01 rail face one plane to the crown chamfer", t["cut"],
             adsk.fusion.FeatureOperations.CutFeatureOperation)]


P03_BEARING_END = (-10.0502, 0.0115, 2.3, 26.7, 27.1)
P03_AXLE_END = (-9.500000000000004, 13.099982791045484, 2.35, 29.8, 29.9)
P03_NOTCHES = ((-4.46, -4.24), (4.23, 4.45))


def seat_teardrop(pin, radius=0.75, t0=-0.1, t1=5.0):
    """Exact v24 C-seat for one pin: R0.75 bore plus a 45-degree roof, over t0..t1 only."""
    s, _ = geometry()
    box = v24().oriented_box
    o, d = pin["origin"], pin["axis"]
    w = [-d[2], 0.0, d[0]]
    apex_y = o[1] - radius * math.sqrt(2.0)
    tangent_y = o[1] - radius / math.sqrt(2.0)
    mid = [o[i] + d[i] * (t0 + t1) / 2 for i in range(3)]
    side = 3.0
    e1 = [math.sqrt(0.5) * w[0], math.sqrt(0.5), math.sqrt(0.5) * w[2]]
    roof = box([mid[0], apex_y + side / math.sqrt(2.0), mid[2]], d, e1, t1 - t0, side, side)
    s.op(roof, box([mid[0], (apex_y - 0.2 + tangent_y) / 2, mid[2]], d, w, t1 - t0, 6.0,
                   tangent_y - apex_y + 0.2), "common")
    a = [o[i] + d[i] * t0 for i in range(3)]
    b = [o[i] + d[i] * t1 for i in range(3)]
    seat = s.tbm().createCylinderOrCone(v24().pt(*a), radius / 10, v24().pt(*b), radius / 10)
    s.op(seat, roof, "join")
    return seat


def p03_tools():
    """Uniform full-length teardrop seats, no end-box remnants, single-radius pocket ends."""
    s, _ = geometry()
    module = v24()
    saved = module.STATE
    module.STATE = STATE
    try:
        pins = module.pins()
    finally:
        module.STATE = saved
    fill = None
    for x0, x1 in P03_NOTCHES:
        b = s.box(x0, x1, 30.22, 30.80, 37.67, 38.04)
        fill = b if fill is None else s.op(fill, b, "join")
    cut = None
    for name, pin in pins.items():
        seat = seat_teardrop(pin)
        cut = seat if cut is None else s.op(cut, seat, "join")
    for x, z, r, y0, y1 in (P03_BEARING_END, P03_AXLE_END):
        s.op(cut, s.cyl(x, z, y0, y1, r), "join")
    return {"fill": fill, "cut": cut, "pins": pins}


def p03_steps():
    t = STATE["p03_tools"]
    return [("P03 close pin-end box remnants", t["fill"], adsk.fusion.FeatureOperations.JoinFeatureOperation),
            ("P03 uniform teardrop seats and single-radius pocket ends", t["cut"],
             adsk.fusion.FeatureOperations.CutFeatureOperation)]


def p02_steps():
    """Close the 0.6 um slit and step left where the v23 ear seats met the 61.5706/33.4706 faces."""
    s, _ = geometry()
    fill = s.box(2.8, 18.2, -6.7, -4.1, 61.565, 61.575)
    cut = s.box(2.8, 18.2, -4.1, -2.0, 33.47, 33.472)
    STATE["p02_tools"] = {"fill": fill, "cut": cut}
    return [("P02 close 0.6 um ear-seat slit", fill, adsk.fusion.FeatureOperations.JoinFeatureOperation),
            ("P02 ear seat one plane at Z33.47", cut, adsk.fusion.FeatureOperations.CutFeatureOperation)]


def tbm_apply(part, steps):
    s, _ = geometry()
    body = s.tbm().copy(STATE["definitions"][part])
    for _, shape, operation in steps:
        kind = "join" if operation == adsk.fusion.FeatureOperations.JoinFeatureOperation else "cut"
        s.op(body, s.tbm().copy(shape), kind)
    return body


def freeze(app, label="SparkShift_v25_P01_P02_P03_deliberate_cleanup_WIP"):
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design.timeline.count != STATE["timeline_count"]:
        raise RuntimeError("The live timeline changed after the last reviewed apply")
    with bound() as module:
        return module.freeze(app, label)


def readback(app, count=200):
    with bound() as module:
        return module.readback(app, count)


def close_readback(app):
    with bound() as module:
        return module.close_readback(app)


def export_prints(app):
    with bound() as module:
        saved = module.PRINTS
        module.PRINTS = {P01: ("P01_motor_mount_clean_housing_v25", (0, 1, 0)),
                         P02: ("P02_servo_plate_ear_seat_snap_v25", (0, -1, 0)),
                         P03: ("P03_uniform_teardrop_seats_v25", (0, -1, 0))}
        try:
            return module.export_meshes(app)
        finally:
            module.PRINTS = saved


def clusters(rows, radius=1.5):
    groups = []
    for row in rows:
        for g in groups:
            if math.dist(row["centre_mm"], g["centre_mm"]) < radius:
                g["members"].append(row)
                n = len(g["members"])
                g["centre_mm"] = [sum(m["centre_mm"][k] for m in g["members"]) / n for k in range(3)]
                break
        else:
            groups.append({"centre_mm": list(row["centre_mm"]), "members": [row]})
    return sorted(groups, key=lambda g: -len(g["members"]))
