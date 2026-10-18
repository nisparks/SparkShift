"""v24: secure, printable pin seats for the October-YUDX Maxwell coupling in yellow P03.

The pin axes, ball centres and magnets are unchanged; they already match YUDX 9b0f1b3 to
within 0.006 mm.  The previous seats were 90-degree V grooves with two short end bands.
Each ball pushes its pin 4.3x harder sideways than into the seat (13-16 degrees below the
face), so a pin in a 90-degree V needs friction mu >= 0.62 to stay put.  YUDX holds the
pins in a square CNC slot whose vertical wall takes that load.  Here every groove becomes a
full-length conformal C-seat (pin radius, 223-degree wrap, 45-degree teardrop roof that prints
face-down without support).  The outboard wall reacts the docking load in compression,
and the ball sockets are opened toward YUDX's generous pockets.
"""

import hashlib
import json
import math
import sys
from contextlib import contextmanager
from pathlib import Path

import adsk.core
import adsk.fusion


OUT = Path(__file__).resolve().parent / "sparkshift_coupling_v24"
P03 = "PRINT_000_outer_shell_of_extruder_1"
PINS = ["OCT_LOCATOR_PIN_%d" % k for k in range(6)]
MAGNETS = ["OCT_RECEIVER_MAGNET_%d" % k for k in range(4)]
BALLS = ["OCT_TOOL_05_4mm_ball:1", "OCT_TOOL_11_4mm_ball:2",
         "OCT_TOOL_12_4mm_ball:3", "OCT_TOOL_13_4mm_ball:4"]
FACE_Y = 31.5
SEAT_R = 0.75
SEAT_T = (-0.1, 5.0)
SOCKET_R = 2.4
SOCKET_FLOOR_CLEAR = 0.6
POCKET_MARGIN = 0.1
STATE = {}


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
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


@contextmanager
def bound(placement=False):
    """Run the proven v22 capture/audit helpers against this module's state and folder."""
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
        report = module.capture(app, ui, "USER_live_input_v24")
    STATE["candidates"] = {}
    for name in [P03] + PINS + MAGNETS + BALLS:
        if name not in STATE["definitions"]:
            raise RuntimeError("Expected body missing: " + name)
    identity = adsk.core.Matrix3D.create().asArray()
    if max(abs(a - b) for a, b in zip(STATE["matrices"][P03].asArray(), identity)) > 1e-9:
        raise RuntimeError("P03 must keep its identity assembly context")
    return report


def vec(*c):
    return adsk.core.Vector3D.create(*c)


def pt(*c):
    return adsk.core.Point3D.create(*(v / 10 for v in c))


def pins():
    """Exact pin end point, unit axis, length and radius read from the steel pin bodies."""
    rows = {}
    for name in PINS:
        body = STATE["world"][name]
        cyl = [f.geometry for f in body.faces if isinstance(f.geometry, adsk.core.Cylinder)]
        ends = [f for f in body.faces if isinstance(f.geometry, adsk.core.Plane)]
        if len(cyl) != 1 or len(ends) != 2:
            raise RuntimeError("Unexpected locator pin body: " + name)
        g = cyl[0]
        d = [g.axis.x, g.axis.y, g.axis.z]
        o = [g.origin.x * 10, g.origin.y * 10, g.origin.z * 10]
        ts = []
        for face in ends:
            p = face.pointOnFace
            ts.append(sum((c * 10 - o[i]) * d[i] for i, c in enumerate((p.x, p.y, p.z))))
        t0, t1 = min(ts), max(ts)
        rows[name] = {"origin": [o[i] + d[i] * t0 for i in range(3)], "axis": d,
                      "length": t1 - t0, "radius": g.radius * 10}
    return rows


def balls():
    rows = {}
    for name in BALLS:
        spheres = [f.geometry for f in STATE["world"][name].faces if isinstance(f.geometry, adsk.core.Sphere)]
        if len(spheres) != 1:
            raise RuntimeError("Unexpected ball body: " + name)
        g = spheres[0]
        rows[name] = {"centre": [g.origin.x * 10, g.origin.y * 10, g.origin.z * 10], "radius": g.radius * 10}
    return rows


def oriented_box(centre, length_dir, width_dir, length, width, height):
    s, _ = geometry()
    box = adsk.core.OrientedBoundingBox3D.create(pt(*centre), vec(*length_dir), vec(*width_dir),
                                                length / 10, width / 10, height / 10)
    shape = s.tbm().createBox(box)
    if shape is None:
        raise RuntimeError("Oriented box creation failed")
    return shape


def seat_profile(pin, radius=SEAT_R, t_range=SEAT_T, face_y=FACE_Y):
    """Fill between the old 90-degree V and a conformal teardrop C-seat for one pin."""
    s, _ = geometry()
    o, d = pin["origin"], pin["axis"]
    if abs(d[1]) > 1e-9:
        raise RuntimeError("Locator pins must lie parallel to the coupling face")
    w = [-d[2], 0.0, d[0]]
    t0, t1 = t_range
    length = t1 - t0
    mid = [o[i] + d[i] * (t0 + t1) / 2 for i in range(3)]
    axis_y = o[1]
    apex_y = axis_y - radius * math.sqrt(2.0)
    side = 3.0
    e1 = [0.7071067811865476 * w[0], 0.7071067811865476, 0.7071067811865476 * w[2]]
    centre = [mid[0], apex_y + side / math.sqrt(2.0), mid[2]]
    wedge = oriented_box(centre, d, e1, length, side, side)
    tangent_y = axis_y - radius / math.sqrt(2.0)
    band = oriented_box([mid[0], (tangent_y + face_y) / 2, mid[2]], d, w, length, 6.0, face_y - tangent_y)
    s.op(wedge, band, "common")
    a = [o[i] + d[i] * (t0 - 0.2) for i in range(3)]
    b = [o[i] + d[i] * (t1 + 0.2) for i in range(3)]
    seat = s.tbm().createCylinderOrCone(pt(*a), radius / 10, pt(*b), radius / 10)
    roof = oriented_box(centre, d, e1, length, side, side)
    s.op(roof, oriented_box([mid[0], (apex_y - 0.2 + tangent_y) / 2, mid[2]], d, w, length, 6.0,
                            tangent_y - apex_y + 0.2), "common")
    teardrop = s.tbm().copy(seat)
    s.op(teardrop, roof, "join")
    s.op(wedge, seat, "cut")
    return wedge, teardrop, {"axis_y": axis_y, "apex_y": apex_y, "tangent_y": tangent_y,
                             "wrap_deg": 360 - 2 * math.degrees(math.acos((face_y - axis_y) / radius)),
                             "mouth_mm": 2 * math.sqrt(radius ** 2 - (face_y - axis_y) ** 2)}


def socket_tool(radius=SOCKET_R, clear=SOCKET_FLOOR_CLEAR):
    s, _ = geometry()
    tool, rows = None, {}
    for name, ball in balls().items():
        cx, cy, cz = ball["centre"]
        floor = cy - ball["radius"] - clear
        cyl = s.cyl(cx, cz, floor, FACE_Y + 0.3, radius)
        rows[name] = {"centre_xz": [cx, cz], "floor_y": floor, "radius": radius}
        if tool is None:
            tool = cyl
        else:
            s.op(tool, cyl, "join")
    return tool, rows


def pocket_tool():
    s, _ = geometry()
    tool = None
    for name in MAGNETS:
        b = tools().bounds(STATE["world"][name])
        box = s.box(b[0][0] - POCKET_MARGIN, b[1][0] + POCKET_MARGIN, 27.5, FACE_Y + 0.3,
                    b[0][2] - POCKET_MARGIN, b[1][2] + POCKET_MARGIN)
        if tool is None:
            tool = box
        else:
            s.op(tool, box, "join")
    return tool


def plan(radius=SEAT_R):
    """Reviewed TBM fill and cut tools for P03."""
    s, _ = geometry()
    fill, rows, seats = None, {}, None
    for name, pin in pins().items():
        part, teardrop, info = seat_profile(pin, radius)
        rows[name] = dict(info, pin=pin)
        if fill is None:
            fill, seats = part, teardrop
        else:
            s.op(fill, part, "join")
            s.op(seats, teardrop, "join")
    cut, sockets = socket_tool()
    s.op(fill, s.tbm().copy(cut), "cut")
    s.op(fill, pocket_tool(), "cut")
    for name in PINS:
        s.op(fill, s.tbm().copy(STATE["world"][name]), "cut")
    s.op(fill, s.box(-12.5, 12.5, 29.0, FACE_Y, -25.0, 50.0), "common")
    sealed = seal_cavities(fill, cut, seats)
    new = s.tbm().copy(fill)
    s.op(new, s.tbm().copy(STATE["definitions"][P03]), "cut")
    lumps = [{"volume_mm3": l.volume * 1000, "bounds_mm": tools().bounds(l)} for l in new.lumps] \
        if new.lumps.count else []
    report = {"seats": rows, "sockets": sockets, "fill_mm3": fill.volume * 1000,
              "fill_lumps": fill.lumps.count, "new_material_mm3": new.volume * 1000 if lumps else 0.0,
              "new_material_lumps": lumps, "cut_mm3": cut.volume * 1000,
              "sealed_notches_filled": sealed,
              "seat_radius_mm": radius, "socket_radius_mm": SOCKET_R,
              "socket_floor_clearance_mm": SOCKET_FLOOR_CLEAR}
    STATE["tools"] = (s.tbm().copy(fill), s.tbm().copy(cut))
    write("plan.json", report)
    return report


def seal_cavities(fill, cut, seats):
    """Fill any pre-existing notch whose only opening the new seat wall closes (no sealed voids)."""
    s, _ = geometry()
    shape = s.tbm().copy(STATE["definitions"][P03])
    s.op(shape, s.tbm().copy(fill), "join")
    s.op(shape, s.tbm().copy(cut), "cut")
    rows = []
    for lump in shape.lumps:
        for shell in list(lump.shells)[1:]:
            b = shell.boundingBox
            lo = [b.minPoint.x * 10, b.minPoint.y * 10, b.minPoint.z * 10]
            hi = [b.maxPoint.x * 10, b.maxPoint.y * 10, b.maxPoint.z * 10]
            void = s.box(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
            s.op(void, s.tbm().copy(shape), "cut")
            s.op(void, s.tbm().copy(seats), "cut")
            enclosed = sum(f.area for f in shell.faces) * 100
            for name in PINS + MAGNETS + BALLS:
                volume, _ = s.common_volume(void, STATE["world"][name])
                if volume > 1e-6:
                    raise RuntimeError("A sealed notch is occupied by " + name)
            s.op(fill, void, "join")
            rows.append({"bounds_mm": [lo, hi], "void_mm3": void.volume * 1000,
                         "shell_area_mm2": enclosed})
    check = s.tbm().copy(STATE["definitions"][P03])
    s.op(check, s.tbm().copy(fill), "join")
    s.op(check, s.tbm().copy(cut), "cut")
    tools().one_solid(check, "P03 v24 plan")
    return rows


def native_p03(component, fill, cut):
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
        options = component.features.combineFeatures.createInput(component.bRepBodies.itemByName(P03), collection)
        options.operation = operation
        options.isKeepToolBodies = False
        feature = component.features.combineFeatures.add(options)
        front().healthy(feature, label)
        feature.name = label
        names.append(label)

    combine(tool_body(fill, "V24 TOOL conformal pin seat fills"),
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "P03 full-length conformal C-seats for six Maxwell pins")
    combine(tool_body(cut, "V24 TOOL ball socket clearance"),
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            "P03 ball sockets R%.2f with %.1f mm floor clearance" % (SOCKET_R, SOCKET_FLOOR_CLEAR))
    body = component.bRepBodies.itemByName(P03)
    tools().one_solid(body, "Revised P03")
    return body, names


def prototype(app):
    s, _ = geometry()
    fill, cut = STATE["tools"]
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "TEMP - P03 v24 pin seat prototype"
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        component = design.rootComponent
        base = component.features.baseFeatures.add()
        if not base.startEdit():
            raise RuntimeError("Could not start the P03 prototype input")
        try:
            component.bRepBodies.add(s.tbm().copy(STATE["definitions"][P03]), base)
        finally:
            if not base.finishEdit():
                raise RuntimeError("Could not finish the P03 prototype input")
        base.bodies.item(0).name = P03
        body, names = native_p03(component, fill, cut)
        STATE["candidates"][P03] = s.tbm().copy(body)
        added = s.tbm().copy(body)
        s.op(added, s.tbm().copy(STATE["definitions"][P03]), "cut")
        removed = s.tbm().copy(STATE["definitions"][P03])
        s.op(removed, s.tbm().copy(body), "cut")
        report = {"features": names, "before": tools().stats(STATE["definitions"][P03]),
                  "candidate": tools().stats(body),
                  "added_mm3": added.volume * 1000 if added.lumps.count else 0.0,
                  "removed_mm3": removed.volume * 1000 if removed.lumps.count else 0.0}
        write("P03_candidate.json", report)
        return report
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the P03 prototype document")
        source.activate()


def world_of(name):
    s, _ = geometry()
    if name in STATE.get("candidates", {}):
        shape = s.tbm().copy(STATE["candidates"][name])
        if not s.tbm().transform(shape, STATE["matrices"][name]):
            raise RuntimeError("Candidate placement failed: " + name)
        return shape
    return STATE["world"][name]


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


def audit_static():
    """New P03 against every fixed body and the docked tool, versus the captured baseline."""
    moving = g22().MOVING
    others = {n: STATE["world"][n] for n in STATE["world"]
              if n != P03 and group(n) not in moving and not n.startswith("REFERENCE_")}
    base = overlaps(STATE["world"][P03], others)
    rows = overlaps(world_of(P03), others)
    accepted, new = {}, {}
    for name, row in rows.items():
        old = base.get(name)
        if old is not None and row["overlap_mm3"] <= old["overlap_mm3"] + 1e-4:
            accepted[name] = dict(row, baseline_mm3=old["overlap_mm3"])
        else:
            new[name] = row
    report = {"accepted_unchanged": accepted, "new_clashes": new, "baseline": base,
              "checked_bodies": len(others)}
    STATE["static"] = report
    write("static_audit.json", report)
    return {"new": {n: r["overlap_mm3"] for n, r in new.items()},
            "accepted": {n: r["overlap_mm3"] for n, r in accepted.items()}, "checked": len(others)}


def clearances(app):
    """Minimum distances from pins, balls and magnets to the revised P03."""
    measure = app.measureManager
    part = world_of(P03)
    rows = {}
    for name in PINS + BALLS + MAGNETS:
        result = measure.measureMinimumDistance(STATE["world"][name], part)
        rows[name] = result.value * 10
    write("coupling_clearances.json", rows)
    return rows


def audit_motion(angles):
    with bound(placement=True) as module:
        return module.audit_motion_fast(P03, angles, "v24_P03")


def audit_tool():
    with bound(placement=True) as module:
        return module.audit_tool([P03], "v24")


def audit_feed():
    with bound(placement=True) as module:
        return module.audit_feed([P03], range(0, 360, 15), "v24")


def apply_live(app, ui):
    if STATE.get("applied"):
        raise RuntimeError("v24 was already applied")
    g22().require_idle(ui, allow_view=False)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the captured live assembly")
    if design.timeline.count != STATE["timeline_count"]:
        raise RuntimeError("The user changed the live timeline after capture; recapture first")
    by, _ = front().inventory(design)
    body = by[P03].nativeObject
    if front().exact(STATE["definitions"][P03], body, "live P03 before v24"):
        raise RuntimeError("The live P03 changed after capture")
    fill, cut = STATE["tools"]
    result, names = native_p03(body.parentComponent, fill, cut)
    delta = front().exact(STATE["candidates"][P03], result, "applied P03 v24")
    if delta:
        raise RuntimeError("The live P03 differs from the reviewed candidate: %.6f mm3" % delta)
    STATE["applied"] = True
    STATE["timeline_after"] = design.timeline.count
    report = {"features": names, "exact_difference_mm3": delta, "timeline_after": design.timeline.count,
              "stats": tools().stats(result)}
    write("live_application.json", report)
    return report


def freeze(app, label="SparkShift_v24_P03_conformal_Maxwell_pin_seats_WIP"):
    with bound() as module:
        return module.freeze(app, label)


def readback(app, count=200):
    with bound() as module:
        return module.readback(app, count)


def close_readback(app):
    with bound() as module:
        return module.close_readback(app)


def export_p03(app):
    with bound() as module:
        saved = module.PRINTS
        module.PRINTS = {P03: ("P03_conformal_Maxwell_pin_seats_v24", (0, -1, 0))}
        try:
            return module.export_meshes(app)
        finally:
            module.PRINTS = saved


def export_coupon(app, radii=(0.70, 0.725, 0.75, 0.775, 0.80)):
    """Export the print-orientation pin seat fit coupon as a raw binary STL."""
    s, _ = geometry()
    shape, rows = coupon(radii)
    folder = OUT / "release" / "stl"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "P03_pin_seat_fit_coupon_v24.stl"
    if path.exists():
        raise RuntimeError("Refusing to overwrite " + path.name)
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "EXPORT ONLY - v24 pin seat coupon"
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        feature = design.rootComponent.features.baseFeatures.add()
        if not feature.startEdit():
            raise RuntimeError("Could not start the coupon body")
        try:
            design.rootComponent.bRepBodies.add(s.tbm().copy(shape), feature)
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish the coupon body")
        body = feature.bodies.item(0)
        options = design.exportManager.createSTLExportOptions(body, str(path))
        options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        options.surfaceDeviation = .0003
        options.normalDeviation = 4.
        options.isBinaryFormat = True
        if not design.exportManager.execute(options) or path.stat().st_size <= 84:
            raise RuntimeError("Coupon export failed")
        receipt = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "native_volume_mm3": shape.volume * 1000, "seats": rows,
                   "print_orientation": "as exported: legs on the bed, seat ceiling 1.65 mm above it, "
                                        "same support settings as P03"}
        STATE["coupon"] = receipt
        write("coupon_receipt.json", receipt)
        return receipt
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the coupon export document")
        source.activate()


def coupon(radii=(0.70, 0.725, 0.75, 0.775, 0.80), pitch=5.0):
    """Fit coupon in print coordinates (Z up, bed at Z0) reproducing the P03 seat section.

    Each seat axis runs along Y, 0.273 mm above a ceiling face at Z1.65, exactly as P03 prints
    rails-down; seat ends are closed like P03.  Dots on the top surface count the seat index.
    """
    s, _ = geometry()
    axis_z = 1.65 + (FACE_Y - 31.226568159)
    length = SEAT_T[1] - SEAT_T[0]
    width = len(radii) * pitch + 4.0
    slab = s.box(0.0, width, 0.0, 9.0, 1.65, 4.65)
    for x0 in (0.0, width - 2.0):
        s.op(slab, s.box(x0, x0 + 2.0, 0.0, 9.0, 0.0, 1.65), "join")
    rows = []
    y0, y1 = 1.9, 1.9 + length
    for k, r in enumerate(radii):
        cx = 2.0 + pitch * (k + 0.5)
        apex = axis_z + r * math.sqrt(2.0)
        tangent = axis_z + r / math.sqrt(2.0)
        groove = s.cyl(cx, axis_z, y0, y1, r)
        side = 3.0
        wedge = oriented_box([cx, (y0 + y1) / 2, apex - side / math.sqrt(2.0)], [0, 1, 0],
                             [0.7071067811865476, 0.0, 0.7071067811865476], length, side, side)
        s.op(wedge, s.box(cx - 3, cx + 3, y0, y1, tangent, apex + 0.01), "common")
        s.op(groove, wedge, "join")
        s.op(slab, groove, "cut")
        for j in range(k + 1):
            x = cx - 0.45 * k + 0.9 * j
            dot = s.tbm().createCylinderOrCone(pt(x, 8.0, 4.25), 0.03, pt(x, 8.0, 4.75), 0.03)
            s.op(slab, dot, "cut")
        rows.append({"index_dots": k + 1, "seat_radius_mm": r,
                     "mouth_mm": 2 * math.sqrt(r * r - (axis_z - 1.65) ** 2),
                     "seat_centre_x_mm": cx})
    tools().one_solid(slab, "Pin seat fit coupon")
    return slab, rows
