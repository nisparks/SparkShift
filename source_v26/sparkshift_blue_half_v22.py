"""Repair and refine the user-selected blue rear case and red arm without moving datums."""

import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

import adsk.core
import adsk.fusion


OUT = Path(__file__).resolve().parent / "sparkshift_blue_half_only_v22"
BLUE = "PRINT_motor_mount"
ARM_REAR = "PRINT_carrier_box_left"
ARM_FRONT = "PRINT_arm_front_half"
MOVING = {"05", "07", "09", "10", "11"}
STATE = {}


def front():
    return sys.modules["sparkshift_front_half_only_v21"]


def tools():
    return sys.modules["sparkshift_open_frame_v19"]


def geometry():
    return tools().geometry()


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def appearance(design, source, name):
    existing = design.appearances.itemByName(name)
    if existing:
        return existing
    return design.appearances.addByCopy(source, name)


def circle_fit(points):
    """Algebraic least-squares circle through XZ points; returns centre, radius, residual."""
    n = len(points)
    sx = sum(p[0] for p in points) / n
    sz = sum(p[1] for p in points) / n
    u = [(p[0] - sx, p[1] - sz) for p in points]
    suu = sum(a * a for a, _ in u)
    svv = sum(b * b for _, b in u)
    suv = sum(a * b for a, b in u)
    suuu = sum(a ** 3 for a, _ in u)
    svvv = sum(b ** 3 for _, b in u)
    suvv = sum(a * b * b for a, b in u)
    svuu = sum(b * a * a for a, b in u)
    det = suu * svv - suv * suv
    if abs(det) < 1e-12:
        return None
    rhs1 = .5 * (suuu + suvv)
    rhs2 = .5 * (svvv + svuu)
    uc = (rhs1 * svv - rhs2 * suv) / det
    vc = (suu * rhs2 - suv * rhs1) / det
    centre = (uc + sx, vc + sz)
    radius = math.sqrt(uc * uc + vc * vc + (suu + svv) / n)
    residual = max(abs(math.dist(p, centre) - radius) for p in points)
    return centre, radius, residual


def facet_bands(body, minimum=4, tolerance=.06):
    """Find sampled rotational facet bands: planar faces parallel to Y forming an arc."""
    faces = {}
    for face in body.faces:
        g = face.geometry
        if not isinstance(g, adsk.core.Plane) or abs(g.normal.y) > 1e-6:
            continue
        lines = []
        for edge in face.edges:
            e = edge.geometry
            if isinstance(e, adsk.core.Line3D):
                v = e.startPoint.vectorTo(e.endPoint)
                if v.length > 1e-6 and abs(abs(v.y) / v.length - 1) < 1e-7:
                    lines.append((round(e.startPoint.x * 10, 5), round(e.startPoint.z * 10, 5)))
        if len(lines) < 2:
            continue
        b = front().tools().bounds(face)
        width = max(math.dist(a, c) for a in lines for c in lines)
        faces[face.tempId] = {"face": face, "y": (round(b[0][1], 4), round(b[1][1], 4)),
                              "points": sorted(set(lines)), "width": width}
    graph = {key: set() for key in faces}
    by_point = {}
    for key, row in faces.items():
        for p in row["points"]:
            by_point.setdefault((row["y"], p), set()).add(key)
    for keys in by_point.values():
        for a in keys:
            graph[a] |= keys - {a}
    seen, bands = set(), []
    for key in faces:
        if key in seen:
            continue
        stack, group = [key], set()
        while stack:
            k = stack.pop()
            if k in group:
                continue
            group.add(k)
            stack.extend(graph[k] - group)
        seen |= group
        if len(group) < minimum:
            continue
        points = sorted({p for k in group for p in faces[k]["points"]})
        fit = circle_fit(points)
        if fit is None:
            continue
        centre, radius, residual = fit
        if residual > tolerance or radius > 80:
            continue
        angles = sorted(math.degrees(math.atan2(p[1] - centre[1], p[0] - centre[0])) for p in points)
        b = [[min(front().tools().bounds(faces[k]["face"])[0][i] for k in group) for i in range(3)],
             [max(front().tools().bounds(faces[k]["face"])[1][i] for k in group) for i in range(3)]]
        bands.append({"faces": len(group), "face_ids": [faces[k]["face"].tempId for k in group],
                      "y_mm": list(faces[next(iter(group))]["y"]), "centre_xz_mm": list(centre),
                      "radius_mm": radius, "residual_mm": residual,
                      "max_width_mm": max(faces[k]["width"] for k in group),
                      "angle_span_deg": [angles[0], angles[-1]], "bounds_mm": b})
    return sorted(bands, key=lambda r: -r["faces"])


def render(app, items, views, label, size=(1400, 1100)):
    """Render immutable shapes in an owned temporary document, then close it."""
    s, _ = geometry()
    source = app.activeDocument
    design_source = adsk.fusion.Design.cast(source.products.itemByProductType("DesignProductType"))
    looks = {}
    for body in front().inventory(design_source)[0].values():
        looks.setdefault(body.appearance.name, body.appearance)
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.activate()
    document.name = "TEMP - v22 inspection render"
    files = []
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent
        feature = root.features.baseFeatures.add()
        if not feature.startEdit():
            raise RuntimeError("Could not start the inspection render bodies")
        try:
            for index, (shape, _) in enumerate(items):
                root.bRepBodies.add(s.tbm().copy(shape), feature)
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish the inspection render bodies")
        for body, (_, look) in zip(feature.bodies, items):
            if look in looks:
                body.appearance = appearance(design, looks[look], look)
        viewport = app.activeViewport
        for view_name, eye, target, up in views:
            camera = viewport.camera
            camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
            camera.eye = adsk.core.Point3D.create(*(v / 10 for v in eye))
            camera.target = adsk.core.Point3D.create(*(v / 10 for v in target))
            camera.upVector = adsk.core.Vector3D.create(*up)
            camera.isSmoothTransition = False
            camera.isFitView = True
            viewport.camera = camera
            viewport.refresh()
            adsk.doEvents()
            path = OUT / "images" / (label + "_" + view_name + ".png")
            path.parent.mkdir(parents=True, exist_ok=True)
            if not viewport.saveAsImageFile(str(path), *size):
                raise RuntimeError("Could not save inspection image " + path.name)
            files.append(str(path))
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the owned inspection render document")
        source.activate()
    return files


def require_idle(ui, allow_view=True):
    benign = {"SelectCommand"} | ({"FreeOrbitCommand", "MeasureCommand"} if allow_view else set())
    if ui.activeCommand not in benign:
        raise RuntimeError("The user has an active modeling command: " + str(ui.activeCommand))


def capture(app, ui, label="USER_live_input"):
    """Preserve the live assembly and immutable native/world snapshots of every physical body."""
    require_idle(ui)
    design = adsk.fusion.Design.cast(app.activeProduct)
    by, empty = front().inventory(design)
    for folder in (OUT, OUT / "cad", OUT / "images"):
        folder.mkdir(parents=True, exist_ok=True)
    path = OUT / "cad" / (label + "_" + time.strftime("%Y%m%d_%H%M%S") + ".f3d")
    if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("Could not preserve the live user assembly")
    by, empty = front().inventory(design)
    s, _ = geometry()
    player = tools().STATE["controller"]
    player.validate(design)
    slider = design.rootComponent.joints.itemByName("J_TOOL_Y")
    snapshot = dict(
        document=app.activeDocument.creationId, source_native=str(path),
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        definitions={n: s.tbm().copy(b.nativeObject) for n, b in by.items()},
        world={n: s.tbm().copy(b) for n, b in by.items()},
        paths={n: b.assemblyContext.fullPathName for n, b in by.items()},
        matrices={n: b.assemblyContext.transform2.copy() for n, b in by.items()},
        root_frames={o.name[:2]: o.transform2.copy() for o in design.rootComponent.occurrences
                     if o.name[:2].isdigit()},
        player=player, tool_slide_mm=slider.jointMotion.slideValue * 10, empty_history=empty,
        timeline_count=design.timeline.count)
    keep = {k: v for k, v in STATE.items() if k in ("candidates", "plans", "history")}
    STATE.clear()
    STATE.update(snapshot)
    STATE.update(keep)
    report = {"document": snapshot["document"], "input": str(path),
              "input_sha256": snapshot["source_sha256"], "physical_bodies": len(by),
              "timeline_count": snapshot["timeline_count"], "tool_slide_mm": snapshot["tool_slide_mm"],
              "playback_data_sha256": player.load_data()[1]}
    write("input_capture.json", report)
    return report


def frames(angle):
    player = STATE["player"]
    data = player.load_data()[0]
    arm = player.arm_angle(data, angle)
    carrier = player.rotation(arm, data["arm_pivot_mm"])
    relative = -data["moving_hob_ratio"] * (data["held_left_compound_deg"] - arm)
    return arm, {"10": player.rotation(angle, data["cam_pivot_mm"]), "05": carrier,
                 "07": player.compose(carrier, player.rotation(relative, data["moving_hob_axis_mm"])),
                 "09": carrier, "11": carrier}


def place(name, shape, frame_map):
    """Move a captured world-pose shape to a commanded pose without touching the live model."""
    s, _ = geometry()
    prefix = STATE["paths"][name][:2]
    if prefix not in frame_map:
        return shape
    moved = s.tbm().copy(shape)
    inverse = STATE["root_frames"][prefix].copy()
    inverse.invert()
    if not s.tbm().transform(moved, STATE["player"].compose(frame_map[prefix], inverse)):
        raise RuntimeError("A read-only pose transform failed")
    return moved


def world_of(name):
    s, _ = geometry()
    if name in STATE.get("candidates", {}):
        shape = s.tbm().copy(STATE["candidates"][name])
        if not s.tbm().transform(shape, STATE["matrices"][name]):
            raise RuntimeError("Candidate placement failed")
        return shape
    return STATE["world"][name]


def overlaps(shape, others, exclude=()):
    s, _ = geometry()
    rows = {}
    for name, other in others.items():
        if name in exclude or name.startswith("REFERENCE_"):
            continue
        volume, common = s.common_volume(shape, other)
        if volume > 1e-5:
            rows[name] = {"overlap_mm3": volume, "bounds_mm": front().tools().bounds(common)}
    return rows


def classify(rows, baseline):
    """Separate unchanged pre-existing contacts and declared heat-set installs from new clashes."""
    accepted, new = {}, {}
    for name, row in rows.items():
        insert = any(k in name.upper() for k in ("HEATSET", "INSERT")) and row["overlap_mm3"] <= 16.25
        old = baseline.get(name)
        if insert or (old is not None and row["overlap_mm3"] <= old["overlap_mm3"] + 1e-4
                      and name.startswith("STOCK_")):
            accepted[name] = row
        else:
            new[name] = row
    return accepted, new


def audit_static(names, label):
    report = {}
    for name in names:
        group = STATE["paths"][name][:2]
        others = {n: STATE["world"][n] for n in STATE["world"] if n != name and n not in names}
        others.update({n: world_of(n) for n in names if n != name})
        movers = {n for n in others if STATE["paths"][n][:2] in MOVING}
        if group in MOVING:
            exclude = {n for n in movers if STATE["paths"][n][:2] in ("10",)}
            exclude |= {n for n in others if STATE["paths"][n][:2] not in MOVING}
        else:
            exclude = movers
        base = overlaps(STATE["world"][name], others, exclude)
        rows = overlaps(world_of(name), others, exclude)
        accepted, new = classify(rows, base)
        report[name] = {"baseline": base, "accepted": accepted, "new_clashes": new}
    write(label + "_static.json", report)
    STATE[label + "_static"] = report
    return {n: {"new_clashes": list(r["new_clashes"]), "accepted": list(r["accepted"])}
            for n, r in report.items()}


def audit_motion(names, angles, label):
    """Changed fixed parts against moving parts, and changed moving parts against everything else."""
    s, _ = geometry()
    rows = STATE.setdefault(label + "_motion", [])
    cache = STATE.setdefault(label + "_motion_cache", {})
    fixed_names = [n for n in STATE["world"] if STATE["paths"][n][:2] not in MOVING]
    shapes = {n: world_of(n) for n in names}
    for angle in angles:
        arm, frame_map = frames(float(angle))
        clashes = []
        for name in names:
            group = STATE["paths"][name][:2]
            if group not in MOVING:
                for other, path in STATE["paths"].items():
                    if path[:2] not in MOVING or other.startswith("REFERENCE_"):
                        continue
                    key = (name, other, round(float(angle), 4) if path[:2] == "10" else round(arm, 6))
                    if key not in cache:
                        volume, common = s.common_volume(shapes[name], place(other, world_of(other), frame_map))
                        cache[key] = (volume, front().tools().bounds(common) if volume > 1e-5 else None)
                    if cache[key][0] > 1e-5:
                        clashes.append({"part": name, "other": other, "overlap_mm3": cache[key][0],
                                        "bounds_mm": cache[key][1]})
            else:
                moved = place(name, shapes[name], frame_map)
                for other in STATE["world"]:
                    if other == name or other.startswith("REFERENCE_"):
                        continue
                    path = STATE["paths"][other][:2]
                    if path in ("05", "09", "11") or (path == "07"):
                        continue
                    key = (name, other, round(float(angle), 4) if path == "10" else round(arm, 6))
                    if key not in cache:
                        target = place(other, world_of(other), frame_map) if path in MOVING else world_of(other)
                        volume, common = s.common_volume(moved, target)
                        cache[key] = (volume, front().tools().bounds(common) if volume > 1e-5 else None)
                    if cache[key][0] > 1e-5:
                        clashes.append({"part": name, "other": other, "overlap_mm3": cache[key][0],
                                        "bounds_mm": cache[key][1]})
        rows.append({"cam_deg": float(angle), "arm_deg": arm, "clashes": clashes})
    write(label + "_motion.json", {"source_sha256": STATE["source_sha256"], "poses": rows,
                                    "existing_nominal_forward_kinematics_not_force_simulation": True})
    return {"poses": len(rows), "poses_with_clashes": sum(bool(r["clashes"]) for r in rows),
            "clashes_last": rows[-1]["clashes"] if rows else []}


def audit_motion_fast(name, angles, label, margin=1.0):
    """All moving bodies against one changed fixed part, using conservative swept-region clips."""
    s, _ = geometry()
    part = world_of(name)
    player = STATE["player"]
    data = player.load_data()[0]
    cam = data["cam_pivot_mm"]
    arm_angles = sorted({round(player.arm_angle(data, a), 9) for a in angles})
    clips = STATE.setdefault(label + "_clips", {})
    if not clips:
        for other, path in STATE["paths"].items():
            group = path[:2]
            if group not in MOVING or other.startswith("REFERENCE_"):
                continue
            shape = world_of(other)
            if group == "10":
                reach = max(math.hypot(v.geometry.x * 10 - cam[0], v.geometry.z * 10 - cam[2])
                            for v in shape.vertices) if shape.vertices.count else 0
                for face in shape.faces:
                    g = face.geometry
                    if isinstance(g, adsk.core.Cylinder):
                        reach = max(reach, math.hypot(g.origin.x * 10 - cam[0], g.origin.z * 10 - cam[2])
                                    + g.radius * 10)
                    elif not isinstance(g, adsk.core.Plane):
                        b = front().tools().bounds(face)
                        reach = max(reach, max(math.hypot(x - cam[0], z - cam[2])
                                               for x in (b[0][0], b[1][0]) for z in (b[0][2], b[1][2])))
                b = front().tools().bounds(shape)
                lo = [cam[0] - reach - margin, b[0][1] - margin, cam[2] - reach - margin]
                hi = [cam[0] + reach + margin, b[1][1] + margin, cam[2] + reach + margin]
            else:
                boxes = []
                for a in (arm_angles[0], arm_angles[len(arm_angles) // 2], arm_angles[-1]):
                    _, frame_map = frames_for_arm(a)
                    boxes.append(front().tools().bounds(place(other, shape, frame_map)))
                lo = [min(b[0][i] for b in boxes) - margin for i in range(3)]
                hi = [max(b[1][i] for b in boxes) + margin for i in range(3)]
            clip = s.tbm().copy(part)
            if not s.tbm().booleanOperation(clip, s.box(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]),
                                            adsk.fusion.BooleanTypes.IntersectionBooleanType):
                raise RuntimeError("Conservative motion clip failed")
            clips[other] = clip if clip.lumps.count else None
    rows = STATE.setdefault(label + "_motion", [])
    cache = STATE.setdefault(label + "_motion_cache", {})
    for angle in angles:
        arm, frame_map = frames(float(angle))
        clashes = []
        for other, clip in clips.items():
            if clip is None:
                continue
            group = STATE["paths"][other][:2]
            key = (other, round(float(angle), 4) if group == "10" else round(arm, 9))
            if key not in cache:
                volume, common = s.common_volume(clip, place(other, world_of(other), frame_map))
                cache[key] = (volume, front().tools().bounds(common) if volume > 1e-5 else None)
            if cache[key][0] > 1e-5:
                clashes.append({"part": name, "other": other, "overlap_mm3": cache[key][0],
                                "bounds_mm": cache[key][1]})
        rows.append({"cam_deg": float(angle), "arm_deg": arm, "clashes": clashes})
    write(label + "_motion.json", {"source_sha256": STATE["source_sha256"], "poses": rows,
                                    "conservative_region_clips_margin_mm": margin,
                                    "existing_nominal_forward_kinematics_not_force_simulation": True})
    return {"poses": len(rows), "poses_with_clashes": sum(bool(r["clashes"]) for r in rows),
            "active_clipped_bodies": sum(c is not None for c in clips.values())}


def frames_for_arm(arm):
    player = STATE["player"]
    data = player.load_data()[0]
    carrier = player.rotation(arm, data["arm_pivot_mm"])
    relative = -data["moving_hob_ratio"] * (data["held_left_compound_deg"] - arm)
    return arm, {"05": carrier, "09": carrier, "11": carrier,
                 "07": player.compose(carrier, player.rotation(relative, data["moving_hob_axis_mm"]))}


def audit_tool(names, label):
    s, m = geometry()
    tool = {n: m.translated(shape, dy=-STATE["tool_slide_mm"]) for n, shape in STATE["world"].items()
            if STATE["paths"][n].startswith("12 ") and not n.startswith("REFERENCE_")}
    rows = []
    for offset in range(36):
        clashes = []
        for name in names:
            if STATE["paths"][name][:2] in MOVING:
                continue
            for n, shape in tool.items():
                volume, common = s.common_volume(world_of(name), m.translated(shape, dy=offset))
                if volume > 1e-5:
                    clashes.append({"part": name, "tool_part": n, "overlap_mm3": volume})
        rows.append({"withdrawal_mm": offset, "clashes": clashes})
    write(label + "_tool.json", {"poses": rows, "source_slide_removed_mm": STATE["tool_slide_mm"]})
    report = {"offsets": len(rows), "offsets_with_clashes": sum(bool(r["clashes"]) for r in rows)}
    STATE[label + "_tool"] = report
    return report


def audit_feed(names, phases, label):
    """Independent rotor-phase clearance at closed and fully open release poses."""
    s, _ = geometry()
    data = STATE["player"].load_data()[0]
    axes = {}
    for group, axle in (("03", "AXLE_4x25_fixed"), ("04", "AXLE_4x24_moving"),
                        ("06", "STOCK_003_extrude_wheel_1")):
        b = front().tools().bounds(STATE["world"][axle])
        axes[group] = [(b[0][0] + b[1][0]) / 2, 0, (b[0][2] + b[1][2]) / 2]
    rows = STATE.setdefault(label + "_feed", [])
    for cam in (0.0, 175.0):
        arm, frame_map = frames(cam)
        moving_axis = adsk.core.Point3D.create(*(v / 10 for v in data["moving_hob_axis_mm"]))
        moving_axis.transformBy(STATE["player"].rotation(arm, data["arm_pivot_mm"]))
        for phase in phases:
            clashes = []
            for name in names:
                part = world_of(name)
                if STATE["paths"][name][:2] in MOVING:
                    part = place(name, part, frame_map)
                for other, path in STATE["paths"].items():
                    group = path[:2]
                    if group not in ("03", "04", "06", "07") or other in names:
                        continue
                    body = place(other, world_of(other), frame_map) if group in MOVING else s.tbm().copy(world_of(other))
                    axis = [v * 10 for v in moving_axis.asArray()] if group == "07" else axes[group]
                    if not s.tbm().transform(body, STATE["player"].rotation(float(phase), axis)):
                        raise RuntimeError("Rotor phase transform failed")
                    volume, _ = s.common_volume(part, body)
                    if volume > 1e-5:
                        clashes.append({"part": name, "rotor": other, "overlap_mm3": volume})
            rows.append({"cam_deg": cam, "phase_deg": float(phase), "clashes": clashes})
    write(label + "_feed.json", {"poses": rows})
    return {"pairs": len(rows), "pairs_with_clashes": sum(bool(r["clashes"]) for r in rows)}


CAM_CLEAR_R = 9.62
SLOT_R = 3.2
SLOT_FLOOR_Y = 9.85
SLOT_FRONT_Y = 11.4
EAR_POCKET_END_Y = 4.1
EAR_SCREW_AXIS = (14.252, -11.249)
LOWER_BOLT_AXIS = (18.2, -13.7)


def halfspace(cx, cz, angle, y0, y1, left=True):
    s, _ = geometry()
    a = math.radians(angle)
    u = (math.cos(a), math.sin(a))
    n = (-u[1], u[0]) if left else (u[1], -u[0])
    width = 120.0
    centre = adsk.core.Point3D.create((cx + n[0] * width / 2) / 10, (y0 + y1) / 20,
                                      (cz + n[1] * width / 2) / 10)
    box = adsk.core.OrientedBoundingBox3D.create(
        centre, adsk.core.Vector3D.create(u[0], 0, u[1]), adsk.core.Vector3D.create(n[0], 0, n[1]),
        24.0, width / 10, (y1 - y0) / 10)
    shape = s.tbm().createBox(box)
    if shape is None:
        raise RuntimeError("Half-space construction failed")
    return shape


def sector(cx, cz, r_in, r_out, a0, a1, y0, y1):
    """Annular sector about a Y-parallel axis, angles in degrees measured atan2(z, x)."""
    s, _ = geometry()
    if not 0 < a1 - a0 < 180:
        raise RuntimeError("Sector span must be between 0 and 180 degrees")
    shape = s.cyl(cx, cz, y0, y1, r_out)
    if r_in > 0:
        s.op(shape, s.cyl(cx, cz, y0 - .1, y1 + .1, r_in), "cut")
    s.op(shape, halfspace(cx, cz, a0, y0, y1, True), "common")
    s.op(shape, halfspace(cx, cz, a1, y0, y1, False), "common")
    return shape


def arc_slot(radius, y0, y1):
    """Clean swept clearance for the arm's lower screw head between closed and full-open poses."""
    s, _ = geometry()
    player = STATE["player"]
    data = player.load_data()[0]
    pivot = data["arm_pivot_mm"]
    full = min(player.arm_angle(data, i / 4) for i in range(701))
    head = STATE["world"]["ARM_LOWER_M3x14_BUTTON_HEAD"]
    axis = next(f.geometry.origin for f in head.faces if isinstance(f.geometry, adsk.core.Cylinder))
    inverse = STATE["root_frames"]["05"].copy()
    inverse.invert()
    ends = []
    for angle in (0.0, full):
        point = axis.copy()
        point.transformBy(player.compose(player.rotation(angle, pivot), inverse))
        ends.append((point.x * 10, point.z * 10))
    rho = math.dist(ends[0], (pivot[0], pivot[2]))
    angles = sorted(math.degrees(math.atan2(e[1] - pivot[2], e[0] - pivot[0])) for e in ends)
    shape = sector(pivot[0], pivot[2], rho - radius, rho + radius, angles[0], angles[1], y0, y1)
    for e in ends:
        s.op(shape, s.cyl(e[0], e[1], y0, y1, radius), "join")
    return shape, {"pivot_xz_mm": [pivot[0], pivot[2]], "head_axis_closed_open_xz_mm": ends,
                   "pitch_radius_mm": rho, "sweep_angles_deg": angles, "slot_radius_mm": radius,
                   "y_mm": [y0, y1]}


def lever_rear_slot(margin_deg=.6, y0=2.2, y1=6.7):
    """Clean pivot-centred clearance for the user's rearward lever extension through the crown."""
    s, _ = geometry()
    player = STATE["player"]
    data = player.load_data()[0]
    pivot = data["arm_pivot_mm"]
    full = min(player.arm_angle(data, i / 4) for i in range(701))
    rear = s.tbm().copy(STATE["definitions"][ARM_REAR])
    s.op(rear, s.box(-40, 40, y0 + .2, y1 - .25, 47, 90), "common")
    points = []
    for edge in rear.edges:
        ok, t0, t1 = edge.evaluator.getParameterExtents()
        ok, strokes = edge.evaluator.getStrokes(t0, t1, .0005)
        points += [(p.x * 10, p.z * 10) for p in strokes]
    if not points:
        raise RuntimeError("The rear lever extension was not found")
    angles = [math.degrees(math.atan2(z - pivot[2], x - pivot[0])) for x, z in points]
    radii = [math.hypot(x - pivot[0], z - pivot[2]) for x, z in points]
    # Native arm geometry is the closed pose; full opening rotates it by -full degrees in atan2(z, x).
    a0, a1 = min(angles) - margin_deg, max(angles) - full + margin_deg
    r0 = min(radii) - .5
    shape = sector(pivot[0], pivot[2], r0, 75.0, a0, a1, y0, y1)
    return shape, {"pivot_xz_mm": [pivot[0], pivot[2]], "angles_deg": [a0, a1],
                   "inner_radius_mm": r0, "y_mm": [y0, y1], "margin_deg": margin_deg,
                   "closed_to_open_rotation_deg": -full}


def blue_tools():
    """Restored v18 rear crown, lower-screw slot and ear-pocket refills, and the clean slot cuts."""
    s, _ = geometry()
    current = STATE["definitions"][BLUE]
    v18 = tools().STATE["before"][BLUE]
    crown = s.tbm().copy(v18)
    s.op(crown, s.box(-30, 30, 0.2, 25, 48.7, 80), "common")
    s.op(crown, s.tbm().copy(current), "cut")
    envelope, _ = arc_slot(3.6, 9.4, SLOT_FLOOR_Y)
    slot_fill = s.tbm().copy(envelope)
    s.op(slot_fill, s.tbm().copy(current), "cut")
    pocket_fill = s.cyl(*EAR_SCREW_AXIS, EAR_POCKET_END_Y, 5.45, 1.75)
    s.op(pocket_fill, s.tbm().copy(current), "cut")
    slot, slot_report = arc_slot(SLOT_R, SLOT_FLOOR_Y, SLOT_FRONT_Y)
    lever, lever_report = lever_rear_slot()
    joins = s.tbm().copy(crown)
    for extra in (slot_fill, pocket_fill):
        if extra.lumps.count:
            s.op(joins, extra, "join")
    report = {"crown": front().tools().stats(crown), "slot_fill_mm3": slot_fill.volume * 1000,
              "ear_pocket_fill_mm3": pocket_fill.volume * 1000, "slot": slot_report,
              "slot_cut_mm3": slot.volume * 1000, "lever_slot": lever_report}
    return joins, (lever, slot), report


def native_blue(component, joins, slot):
    """Downstream P01 features; identical sequence for the invisible prototype and live part."""
    s, _ = geometry()
    names = []

    def add_tool(shape, label):
        feature = component.features.baseFeatures.add()
        feature.name = label
        if not feature.startEdit():
            raise RuntimeError("Could not start " + label)
        try:
            body = component.bRepBodies.add(s.tbm().copy(shape), feature)
            if body is None:
                raise RuntimeError("Could not add " + label)
        finally:
            if not feature.finishEdit():
                raise RuntimeError("Could not finish " + label)
        tool = feature.bodies.item(0)
        tool.name = label
        return tool

    def combine(tool, operation, label):
        target = component.bRepBodies.itemByName(BLUE)
        collection = adsk.core.ObjectCollection.create()
        collection.add(tool)
        options = component.features.combineFeatures.createInput(target, collection)
        options.operation = operation
        options.isKeepToolBodies = False
        feature = component.features.combineFeatures.add(options)
        front().healthy(feature, label)
        feature.name = label
        names.append(label)

    combine(add_tool(joins, "V22 TOOL restored rear crown and refills"),
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "P01 restored rear crown - lower slot floor and ear pocket refills")
    lever, slot = slot
    combine(add_tool(lever, "V22 TOOL lever extension slot"),
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            "P01 crown slot for rear lever extension - pivot-centred sector")
    combine(add_tool(slot, "V22 TOOL clean lower screw-head arc slot"),
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            "P01 clean lower screw-head arc slot")
    body = component.bRepBodies.itemByName(BLUE)
    data = STATE["player"].load_data()[0]
    cam = data["cam_pivot_mm"]
    ids = {i for b in facet_bands(body, minimum=3)
           if math.dist(b["centre_xz_mm"], (cam[0], cam[2])) < 1.6 for i in b["face_ids"]}
    band = [face for face in body.faces if face.tempId in ids]
    if len(band) < 100:
        raise RuntimeError("The sampled cam clearance band was not found")
    radii = [math.hypot(v.geometry.x * 10 - cam[0], v.geometry.z * 10 - cam[2])
             for face in band for v in face.vertices]
    if max(radii) >= CAM_CLEAR_R:
        raise RuntimeError("The clean cam cylinder would add material")
    cylinder = s.cyl(cam[0], cam[2], 2.0, 12.0, CAM_CLEAR_R)
    sheet = s.tbm().copy(next(f for f in cylinder.faces if isinstance(f.geometry, adsk.core.Cylinder)))
    guide = component.features.baseFeatures.add()
    guide.name = "V22 GUIDE cam clearance R9.62"
    if not guide.startEdit():
        raise RuntimeError("Could not start the cam guide")
    try:
        component.bRepBodies.add(sheet, guide)
    finally:
        if not guide.finishEdit():
            raise RuntimeError("Could not finish the cam guide")
    guide_body = next(b for b in component.bRepBodies if not b.isSolid)
    sources = adsk.core.ObjectCollection.create()
    for face in band:
        sources.add(face)
    targets = adsk.core.ObjectCollection.create()
    targets.add(guide_body)
    replace = component.features.replaceFaceFeatures.add(
        component.features.replaceFaceFeatures.createInput(sources, False, targets))
    front().healthy(replace, "Cam clearance replacement")
    replace.name = "P01 cam clearance - one R9.62 cylinder about the cam axis"
    names.append(replace.name)
    removal = component.features.removeFeatures.add(next(b for b in component.bRepBodies if not b.isSolid))
    removal.name = "Remove V22 cam guide"
    body = component.bRepBodies.itemByName(BLUE)
    ring = [face for face in body.faces if isinstance(face.geometry, adsk.core.Cylinder)
            and abs(face.geometry.radius * 10 - 3.6) < 1e-6
            and math.dist((face.geometry.origin.x * 10, face.geometry.origin.z * 10), LOWER_BOLT_AXIS) < 1e-5
            and front().tools().bounds(face)[0][1] > 11.39 and front().tools().bounds(face)[1][1] < 11.61]
    if len(ring) != 2:
        raise RuntimeError("The lower bolt R3.6 contact ring faces were not uniquely found")
    ring_guide = s.cyl(*LOWER_BOLT_AXIS, 9.0, 14.0, 3.15)
    ring_sheet = s.tbm().copy(next(f for f in ring_guide.faces if isinstance(f.geometry, adsk.core.Cylinder)))
    guide = component.features.baseFeatures.add()
    guide.name = "V22 GUIDE lower bolt ring R3.15"
    if not guide.startEdit():
        raise RuntimeError("Could not start the lower ring guide")
    try:
        component.bRepBodies.add(ring_sheet, guide)
    finally:
        if not guide.finishEdit():
            raise RuntimeError("Could not finish the lower ring guide")
    sources = adsk.core.ObjectCollection.create()
    for face in ring:
        sources.add(face)
    targets = adsk.core.ObjectCollection.create()
    targets.add(next(b for b in component.bRepBodies if not b.isSolid))
    offset = component.features.replaceFaceFeatures.add(
        component.features.replaceFaceFeatures.createInput(sources, False, targets))
    front().healthy(offset, "Lower bolt ring clearance")
    offset.name = "P01 lower bolt ring R3.6 to R3.15 - rear arm clearance"
    names.append(offset.name)
    removal = component.features.removeFeatures.add(next(b for b in component.bRepBodies if not b.isSolid))
    removal.name = "Remove V22 lower ring guide"
    body = component.bRepBodies.itemByName(BLUE)
    front().tools().one_solid(body, "Revised P01")
    if sum(b.lumps.count > 0 for b in component.bRepBodies) != 1:
        raise RuntimeError("Unconsumed tool bodies remain in P01")
    return body, names


def plane_halfspace(point, normal, y0, y1, along_normal):
    """Half-space bounded by a Y-parallel plane through point (mm XZ) with unit normal (XZ)."""
    angle = math.degrees(math.atan2(-normal[0], normal[1]))
    return halfspace(point[0], point[1], angle, y0, y1, along_normal)


def arm_world_faces():
    """Locate the user-marked arm profile faces in the captured world pose."""
    s, _ = geometry()
    arm = STATE["world"][ARM_REAR]
    found = {}
    for face in arm.faces:
        g = face.geometry
        b = front().tools().bounds(face)
        if isinstance(g, adsk.core.Cylinder) and abs(g.axis.y) > .999:
            key = (round(g.radius * 10, 3), round(g.origin.x * 10, 2), round(g.origin.z * 10, 2))
            found.setdefault(("cyl",) + key, []).append(face)
        elif isinstance(g, adsk.core.Plane) and abs(g.normal.y) < 1e-6 and face.area * 100 > 1.0:
            found.setdefault(("plane", round(g.normal.x, 3), round(g.normal.z, 3)), []).append(face)
    return found


def arm_tools():
    """Profile fills for the rear arm: remove the right-side hook and the left-side notch."""
    s, _ = geometry()
    arm = STATE["world"][ARM_REAR]
    faces = arm_world_faces()

    def one(key):
        rows = faces.get(key, [])
        if len(rows) != 1:
            raise RuntimeError("Arm reference face is not unique: " + str(key))
        return rows[0]

    def plane_data(face):
        g = face.geometry
        return (g.origin.x * 10, g.origin.z * 10), (g.normal.x, g.normal.z)

    r91 = [f for f in arm.faces if isinstance(f.geometry, adsk.core.Cylinder)
           and abs(f.geometry.radius * 10 - 9.1) < 1e-3 and abs(f.geometry.axis.y) > .999
           and front().tools().bounds(f)[1][0] < 0 and front().tools().bounds(f)[1][2] > 54]
    if len(r91) != 1:
        raise RuntimeError("The lobe-layer cam clearance arc beside the lever was not unique")
    centre = (r91[0].geometry.origin.x * 10, r91[0].geometry.origin.z * 10)
    ledge = [f for k, rows in faces.items() if k[0] == "plane" for f in rows
             if abs(f.geometry.normal.z) > .98 and front().tools().bounds(f)[0][1] > 2.49
             and front().tools().bounds(f)[1][1] < 4.41 and abs(front().tools().bounds(f)[0][2] - 51.6) < .3]
    if len(ledge) != 1:
        ledge = [f for f in arm.faces if isinstance(f.geometry, adsk.core.Plane)
                 and abs(f.geometry.normal.z) > .98 and abs(front().tools().bounds(f)[0][2] - 51.6) < .3
                 and front().tools().bounds(f)[1][1] < 4.41]
    if len(ledge) != 1:
        raise RuntimeError("The right-side hook ledge was not uniquely found")
    lever_right = [f for f in arm.faces if isinstance(f.geometry, adsk.core.Plane)
                   and f.geometry.normal.x > .97 and front().tools().bounds(f)[1][2] > 70]
    lever_left = [f for f in arm.faces if isinstance(f.geometry, adsk.core.Plane)
                  and f.geometry.normal.x < -.97 and front().tools().bounds(f)[1][2] > 69]
    boss = [f for f in arm.faces if isinstance(f.geometry, adsk.core.Cylinder)
            and abs(f.geometry.radius * 10 - 8.3) < 1e-3]
    notch = [f for f in arm.faces if isinstance(f.geometry, adsk.core.Cylinder)
             and abs(f.geometry.radius * 10 - 4.2) < 1e-3]
    if not (len(lever_right) == len(lever_left) == len(boss) == len(notch) == 1):
        raise RuntimeError("Arm lever/boss/notch references are not unique")
    lp, ln = plane_data(ledge[0])
    rp, rn = plane_data(lever_right[0])
    right = s.cyl(centre[0], centre[1], 2.5, 4.4, 9.15)
    s.op(right, s.cyl(centre[0], centre[1], 2.4, 4.5, 7.8), "cut")
    s.op(right, plane_halfspace(lp, ln, 2.5, 4.4, True), "common")
    s.op(right, plane_halfspace(rp, rn, 2.5, 4.4, False), "common")
    s.op(right, s.tbm().copy(arm), "cut")
    bg = boss[0].geometry
    ng = notch[0].geometry
    qp, qn = plane_data(lever_left[0])
    zone = s.box(-10.6, -6.8, 2.4, 13.1, 43.0, 49.6)
    bump = s.tbm().copy(arm)
    s.op(bump, s.tbm().copy(zone), "common")
    s.op(bump, plane_halfspace(qp, qn, 2.4, 13.1, True), "common")
    s.op(bump, s.cyl(bg.origin.x * 10, bg.origin.z * 10, 2.3, 13.2, bg.radius * 10), "cut")
    left = s.tbm().copy(zone)
    s.op(left, s.box(-30, 30, 2.5, 13.0, 0, 90), "common")
    s.op(left, plane_halfspace(qp, qn, 2.5, 13.0, False), "common")
    s.op(left, s.tbm().copy(arm), "cut")
    fills = s.tbm().copy(right)
    if left.lumps.count:
        s.op(fills, left, "join")
    cuts = bump
    inverse = STATE["matrices"][ARM_REAR].copy()
    inverse.invert()
    native = s.tbm().copy(fills)
    native_cuts = s.tbm().copy(cuts) if cuts.lumps.count else None
    for shape in (native, native_cuts):
        if shape is not None and not s.tbm().transform(shape, inverse):
            raise RuntimeError("Arm tool transform failed")
    notch_native = adsk.core.Point3D.create(ng.origin.x, 0, ng.origin.z)
    notch_native.transformBy(inverse)
    STATE["arm_notch_native_xz_mm"] = (notch_native.x * 10, notch_native.z * 10)
    report = {"right_hook_fill_mm3": right.volume * 1000, "left_kink_fill_mm3": left.volume * 1000,
              "left_bump_trim_mm3": cuts.volume * 1000 if cuts.lumps.count else 0.0,
              "cam_clearance_centre_open_pose_xz_mm": list(centre),
              "rear_layer_arc_radius_mm": 7.8, "lobe_layer_arc_radius_mm_unchanged": 9.1,
              "boss_radius_mm": bg.radius * 10, "replaced_bump_radius_mm": ng.radius * 10}
    return (native, native_cuts), report


def native_arm(component, arm_shapes, fillet_mm=2.0):
    s, _ = geometry()
    fills, cuts = arm_shapes
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
        target = component.bRepBodies.itemByName(ARM_REAR)
        collection = adsk.core.ObjectCollection.create()
        collection.add(tool)
        options = component.features.combineFeatures.createInput(target, collection)
        options.operation = operation
        options.isKeepToolBodies = False
        feature = component.features.combineFeatures.add(options)
        front().healthy(feature, label)
        feature.name = label
        names.append(label)

    combine(tool_body(fills, "V22 TOOL arm profile fills"), adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "P04R right hook removed and left kink filled")
    if cuts is not None:
        combine(tool_body(cuts, "V22 TOOL arm left bump trim"), adsk.fusion.FeatureOperations.CutFeatureOperation,
                "P04R left bump trimmed to lever line")
    body = component.bRepBodies.itemByName(ARM_REAR)
    edges = adsk.core.ObjectCollection.create()
    notch = STATE["arm_notch_native_xz_mm"]
    for edge in body.edges:
        cylinders = [f for f in edge.faces if isinstance(f.geometry, adsk.core.Cylinder)
                     and abs(f.geometry.radius * 10 - 8.3) < 1e-3]
        planes = [f for f in edge.faces if isinstance(f.geometry, adsk.core.Plane)
                  and f.geometry.normal.x < -.97]
        b = front().tools().bounds(edge)
        middle = ((b[0][0] + b[1][0]) / 2, (b[0][2] + b[1][2]) / 2)
        if len(cylinders) == 1 and len(planes) == 1 and math.dist(middle, notch) < 6:
            edges.add(edge)
    if edges.count < 1:
        rows = []
        for edge in body.edges:
            b = front().tools().bounds(edge)
            middle = ((b[0][0] + b[1][0]) / 2, (b[0][2] + b[1][2]) / 2)
            if math.dist(middle, notch) < 6:
                rows.append([f.geometry.objectType.split("::")[-1] +
                             (":%.3f" % (f.geometry.radius * 10) if hasattr(f.geometry, "radius") else
                              ":%.3f,%.3f" % (f.geometry.normal.x, f.geometry.normal.z)) for f in edge.faces])
        STATE["arm_edge_debug"] = rows
        raise RuntimeError("The left boss-to-lever edge was not found")
    fillets = component.features.filletFeatures
    options = fillets.createInput()
    options.edgeSetInputs.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByReal(fillet_mm / 10), True)
    blend = fillets.add(options)
    front().healthy(blend, "Left tangent boss blend")
    blend.name = "P04R left boss-to-lever tangent blend R%.1f" % fillet_mm
    names.append(blend.name)
    body = component.bRepBodies.itemByName(ARM_REAR)
    front().tools().one_solid(body, "Revised P04R")
    return body, names


def prototype_arm(app):
    s, _ = geometry()
    fills, report = arm_tools()
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "TEMP - P04R v22 prototype"
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        component = design.rootComponent
        base = component.features.baseFeatures.add()
        if not base.startEdit():
            raise RuntimeError("Could not start the arm prototype input")
        try:
            component.bRepBodies.add(s.tbm().copy(STATE["definitions"][ARM_REAR]), base)
        finally:
            if not base.finishEdit():
                raise RuntimeError("Could not finish the arm prototype input")
        base.bodies.item(0).name = ARM_REAR
        body, names = native_arm(component, fills)
        STATE.setdefault("candidates", {})[ARM_REAR] = s.tbm().copy(body)
        STATE["arm_tools"] = tuple(s.tbm().copy(t) if t is not None else None for t in fills)
        report.update(features=names, candidate=front().tools().stats(body))
        write("P04R_candidate.json", report)
        return report
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the arm prototype document")
        source.activate()


def blue_lever_relief(p01):
    """Extend P01's existing full-open lever clearance plane through the obsolete bump pocket."""
    s, _ = geometry()
    planes = [f for f in p01.faces if isinstance(f.geometry, adsk.core.Plane)
              and abs(abs(f.geometry.normal.x) - .991) < .003 and abs(abs(f.geometry.normal.z) - .131) < .003
              and abs(front().tools().bounds(f)[0][1] - 6.7) < 1e-3 and abs(front().tools().bounds(f)[1][1] - 11.4) < 1e-3]
    if len(planes) != 1:
        raise RuntimeError("The P01 full-open lever clearance plane was not unique")
    g = planes[0].geometry
    point = (g.origin.x * 10, g.origin.z * 10)
    normal = (g.normal.x, g.normal.z)
    cavity = (-9.0, 46.0)
    along = (cavity[0] - point[0]) * normal[0] + (cavity[1] - point[1]) * normal[1] > 0
    tool = plane_halfspace(point, normal, 7.45, 11.4, along)
    s.op(tool, s.box(-10.6, -8.6, 7.45, 11.4, 44.0, 47.2), "common")
    removed = s.tbm().copy(p01)
    s.op(removed, s.tbm().copy(tool), "common")
    return tool, {"plane_point_xz_mm": point, "plane_normal_xz": normal,
                  "removed_mm3": removed.volume * 1000}


PRINTS = {BLUE: ("P01_rear_case_restored_crown_v22", (0, 1, 0)),
          ARM_REAR: ("P04R_swing_arm_rear_tangent_profile_v22", (0, -1, 0))}


def freeze(app, label="SparkShift_v22_blue_crown_and_arm_profile_WIP"):
    design = adsk.fusion.Design.cast(app.activeProduct)
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the live revised assembly")
    path = OUT / "release" / "cad" / (label + ".f3d")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError("Refusing to overwrite an existing frozen archive")
    if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("Could not save the revised native assembly")
    STATE["archive"] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "bytes": path.stat().st_size, "timeline_count": design.timeline.count}
    write("native_archive_receipt.json", STATE["archive"])
    return STATE["archive"]


def readback(app, count=200):
    """Independently reopen the frozen archive and compare every physical body and placement."""
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
        by, empty = front().inventory(design)
        if set(by) != set(STATE["definitions"]):
            raise RuntimeError("The reopened physical inventory differs")
        rows = STATE["readback_rows"]
        if any(r["difference_mm3"] or r["placement_max_delta"] > 1e-8 for r in rows):
            raise RuntimeError("A failed readback row cannot be skipped")
        names = sorted(by)
        for name in names[len(rows):len(rows) + count]:
            expected = STATE["candidates"].get(name, STATE["definitions"][name])
            body = by[name].nativeObject
            front().tools().one_solid(body, "Reopened " + name)
            delta = front().exact(expected, body, "v22 readback " + name)
            placement = max(abs(a - b) for a, b in zip(STATE["matrices"][name].asArray(),
                                                      by[name].assemblyContext.transform2.asArray()))
            rows.append({"body": name, "difference_mm3": delta, "placement_max_delta": placement,
                         "changed_in_v22": name in STATE["candidates"]})
            write("native_archive_readback.json", {"archive_sha256": STATE["archive"]["sha256"],
                                                   "checked": rows, "complete": len(rows) == len(names)})
            if delta or placement > 1e-8:
                raise RuntimeError("Reopened geometry or placement differs: " + name)
        complete = len(rows) == len(names)
        if complete:
            STATE["readback_complete"] = True
        return {"checked": len(rows), "total": len(names), "complete": complete}
    finally:
        source.activate()


def close_readback(app):
    document = next((d for d in app.documents if d.creationId == STATE.get("readback_document")), None)
    if document is not None and not document.close(False):
        raise RuntimeError("Could not close the owned readback document")
    return {"closed": document is not None}


def export_meshes(app):
    s, _ = geometry()
    helper = tools().load_file("sparkshift_v22_print_bed",
                               Path(__file__).resolve().parent / "sparkshift_surface_cleanup.py")
    folder = OUT / "release" / "stl"
    folder.mkdir(parents=True, exist_ok=True)
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "EXPORT ONLY - v22 raw print meshes"
    receipts = {}
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        for name, (filename, direction) in PRINTS.items():
            native = STATE["candidates"][name]
            feature = design.rootComponent.features.baseFeatures.add()
            if not feature.startEdit():
                raise RuntimeError("Could not start the print body " + name)
            try:
                body = design.rootComponent.bRepBodies.add(s.tbm().copy(native), feature)
            finally:
                if not feature.finishEdit():
                    raise RuntimeError("Could not finish the print body " + name)
            body = feature.bodies.item(0)
            orientation = helper.bed_face(body, direction)
            shape = s.tbm().copy(native)
            build = adsk.core.Vector3D.create(*orientation["build_direction"])
            rotation = adsk.core.Matrix3D.create()
            angle = build.angleTo(adsk.core.Vector3D.create(0, 0, 1))
            if angle > 1e-10:
                axis = build.crossProduct(adsk.core.Vector3D.create(0, 0, 1))
                if axis.length < 1e-10:
                    axis = adsk.core.Vector3D.create(1, 0, 0)
                axis.normalize()
                rotation.setToRotation(angle, axis, adsk.core.Point3D.create())
                s.tbm().transform(shape, rotation)
            box = shape.preciseBoundingBox
            translation = adsk.core.Matrix3D.create()
            translation.translation = adsk.core.Vector3D.create(-box.minPoint.x, -box.minPoint.y, -box.minPoint.z)
            s.tbm().transform(shape, translation)
            front().tools().one_solid(shape, "Bed-oriented " + name)
            feature2 = design.rootComponent.features.baseFeatures.add()
            if not feature2.startEdit():
                raise RuntimeError("Could not start the oriented body " + name)
            try:
                design.rootComponent.bRepBodies.add(shape, feature2)
            finally:
                if not feature2.finishEdit():
                    raise RuntimeError("Could not finish the oriented body " + name)
            oriented = feature2.bodies.item(0)
            path = folder / (filename + ".stl")
            if path.exists():
                raise RuntimeError("Refusing to overwrite " + path.name)
            options = design.exportManager.createSTLExportOptions(oriented, str(path))
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            options.surfaceDeviation = .0003
            options.normalDeviation = 4.
            options.isBinaryFormat = True
            if not design.exportManager.execute(options) or path.stat().st_size <= 84:
                raise RuntimeError("Raw mesh export failed: " + name)
            receipts[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "native_volume_mm3": native.volume * 1000, "bed_face": orientation,
                              "native_archive_sha256": STATE.get("archive", {}).get("sha256"),
                              "raw_native_mesh_without_repair": True}
        STATE["meshes"] = receipts
        write("mesh_export_receipt.json", receipts)
        return receipts
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the export-only document")
        source.activate()


def apply_arm_and_relief(app, ui):
    """Apply the P01 lever relief and P04R profile edits once over the exact reviewed inputs."""
    if STATE.get("applied_arm") or not STATE.get("applied_blue"):
        raise RuntimeError("Apply P01 first, then the arm profile exactly once")
    require_idle(ui, allow_view=False)
    s, _ = geometry()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the captured live assembly")
    expected_count = STATE.get("timeline_after_blue")
    if expected_count is not None and design.timeline.count != expected_count:
        raise RuntimeError("The user changed the timeline after the P01 application; recapture first")
    by, _ = front().inventory(design)
    blue = by[BLUE].nativeObject
    arm = by[ARM_REAR].nativeObject
    if front().exact(STATE["candidates"][BLUE], blue, "live P01 before lever relief"):
        raise RuntimeError("The live P01 changed after its reviewed application")
    if front().exact(STATE["definitions"][ARM_REAR], arm, "live P04R before profile edits"):
        raise RuntimeError("The live P04R changed after capture; preserve the new edit")
    tool, relieved = STATE["p01_lever_relief"]
    component = blue.parentComponent
    feature = component.features.baseFeatures.add()
    feature.name = "V22 TOOL P01 lever clearance extension"
    if not feature.startEdit():
        raise RuntimeError("Could not start the P01 relief tool")
    try:
        component.bRepBodies.add(s.tbm().copy(tool), feature)
    finally:
        if not feature.finishEdit():
            raise RuntimeError("Could not finish the P01 relief tool")
    collection = adsk.core.ObjectCollection.create()
    collection.add(feature.bodies.item(0))
    options = component.features.combineFeatures.createInput(component.bRepBodies.itemByName(BLUE), collection)
    options.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    options.isKeepToolBodies = False
    cut = component.features.combineFeatures.add(options)
    front().healthy(cut, "P01 lever clearance extension")
    cut.name = "P01 lever clearance plane extended through obsolete bump pocket"
    blue_result = component.bRepBodies.itemByName(BLUE)
    delta_blue = front().exact(relieved, blue_result, "applied P01 lever relief")
    if delta_blue:
        raise RuntimeError("The live P01 relief differs from review: %.6f mm3" % delta_blue)
    STATE["candidates"][BLUE] = s.tbm().copy(relieved)
    arm_result, names = native_arm(arm.parentComponent, STATE["arm_tools"])
    delta_arm = front().exact(STATE["candidates"][ARM_REAR], arm_result, "applied P04R profile edits")
    if delta_arm:
        raise RuntimeError("The live P04R differs from review: %.6f mm3" % delta_arm)
    STATE["applied_arm"] = True
    STATE["timeline_after_arm"] = design.timeline.count
    report = {"p01_feature": cut.name, "p01_exact_difference_mm3": delta_blue,
              "p01_stats": front().tools().stats(blue_result), "arm_features": names,
              "arm_exact_difference_mm3": delta_arm, "arm_stats": front().tools().stats(arm_result),
              "timeline_after": design.timeline.count}
    write("P04R_and_P01_relief_live_application.json", report)
    return report


def apply_blue(app, ui):
    """Apply the reviewed P01 feature sequence once, only over the exact captured user input."""
    if STATE.get("applied_blue") or BLUE not in STATE.get("candidates", {}):
        raise RuntimeError("Apply one reviewed P01 candidate exactly once")
    require_idle(ui, allow_view=False)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the captured live assembly")
    if design.timeline.count != STATE["timeline_count"]:
        raise RuntimeError("The user changed the live timeline after capture; recapture first")
    by, _ = front().inventory(design)
    body = by[BLUE].nativeObject
    if front().exact(STATE["definitions"][BLUE], body, "live P01 before v22"):
        raise RuntimeError("The live P01 changed after capture; preserve the new edit")
    joins, slot = STATE["blue_tools"]
    result, names = native_blue(body.parentComponent, joins, slot)
    delta = front().exact(STATE["candidates"][BLUE], result, "applied P01 v22")
    if delta:
        raise RuntimeError("The live P01 differs from the reviewed candidate: %.6f mm3" % delta)
    STATE["applied_blue"] = True
    report = {"features": names, "exact_candidate_difference_mm3": delta,
              "stats": front().tools().stats(result), "timeline_after": design.timeline.count}
    write("P01_live_application.json", report)
    return report


def prototype_blue(app):
    """Build the reviewed P01 in an invisible owned document without changing the live model."""
    s, _ = geometry()
    joins, slot, report = blue_tools()
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "TEMP - P01 v22 prototype"
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        component = design.rootComponent
        base = component.features.baseFeatures.add()
        if not base.startEdit():
            raise RuntimeError("Could not start the P01 prototype input")
        try:
            component.bRepBodies.add(s.tbm().copy(STATE["definitions"][BLUE]), base)
        finally:
            if not base.finishEdit():
                raise RuntimeError("Could not finish the P01 prototype input")
        base.bodies.item(0).name = BLUE
        body, names = native_blue(component, joins, slot)
        STATE.setdefault("candidates", {})[BLUE] = s.tbm().copy(body)
        STATE["blue_tools"] = (s.tbm().copy(joins), tuple(s.tbm().copy(t) for t in slot))
        report.update(features=names, candidate=front().tools().stats(body),
                      source_sha256=STATE["source_sha256"])
        if not s.tbm().exportToFile([STATE["candidates"][BLUE]], str(OUT / "P01_candidate.smt")):
            raise RuntimeError("Could not checkpoint the P01 candidate")
        write("P01_candidate.json", report)
        return report
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the P01 prototype document")
        source.activate()
