"""Analytic structural revisions of the saved AHG-min v6 assembly. Dimensions are mm."""

import importlib.util
import json
import math
import sys
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "sparkshift_ahg_min"
STATE = {}
PARTS = {
    "P01": "PRINT_motor_mount",
    "P02": "PRINT_REAR_MOTOR_SERVO_SPACER",
    "P03": "PRINT_000_outer_shell_of_extruder_1",
    "P04R": "PRINT_carrier_box_left",
    "P04F": "PRINT_arm_front_half",
}


def load(name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def stats(body):
    return {"faces": body.faces.count, "lumps": body.lumps.count,
            "volume_mm3": round(body.volume * 1000, 3),
            "bounds_mm": [round(x, 4) for x in load("sparkshift_ahg_min").bb_of(body)]}


def initialize(app, output=None):
    global OUT
    if "before" in STATE:
        raise RuntimeError("v7 baseline already captured")
    if output is not None:
        OUT = Path(output)
    OUT.mkdir(parents=True, exist_ok=True)
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    m.OUT = OUT
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    by = {b.name: b for b in s.proxies(root)}
    expected = {"P01": 983, "P02": 100, "P03": 521, "P04R": 443, "P04F": 321}
    for key, faces in expected.items():
        if PARTS[key] not in by or by[PARTS[key]].faces.count != faces:
            raise RuntimeError("Not the saved v6 intent-pass baseline: " + key)
    m.PARTS.update(P04F=PARTS["P04F"], P05="PRINT_DIRECT_CAM",
                   P06="PRINT_compound_left", P07="PRINT_compound_right")
    m.STATE.update(Mv=s.centre(by["AXLE_4x24_moving"]),
                   F=s.centre(by["AXLE_4x25_fixed"]),
                   C=s.centre(by["CAM_OUTBOARD_MF63"]),
                   Fo=s.centre(by["CAM_FOLLOWER_623"]),
                   leftovers=[n for n in by if n in (
                       "M3x3_motor_grub", "MOTOR_factory_shaft", "PINION_motor_20T_m0p5",
                       "MOTOR_14HS13_case", "FOLLOWER_M3_INSERT")])
    m.IMAGES_V4 = OUT / "images_v7"
    STATE["before"] = {key: s.tbm().copy(by[name]) for key, name in PARTS.items()}
    STATE["before_all"] = {n: s.tbm().copy(b) for n, b in by.items()}
    STATE["candidate"] = {key: s.tbm().copy(b) for key, b in STATE["before"].items()}
    report = {key: stats(b) for key, b in STATE["before"].items()}
    (OUT / "v7_baseline.json").write_text(json.dumps(report, indent=2))
    return report


def op(a, b, kind):
    s = load("pancake_paths_study")
    out = s.tbm().copy(a)
    s.op(out, b, kind)
    if not math.isfinite(out.volume):
        raise RuntimeError("Invalid volume after " + kind)
    return out


def polygon(points, y0, y1):
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    if area < 0:
        points = list(reversed(points))
    shape = s.box(min(p[0] for p in points), max(p[0] for p in points), y0, y1,
                  min(p[1] for p in points), max(p[1] for p in points))
    for a, b in zip(points, points[1:] + points[:1]):
        angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        shape = op(shape, m.half_xz(a, angle, y0 - .1, y1 + .1), "common")
    return shape


def tapered_capsule(p, rp, q, rq, y0, y1):
    s = load("pancake_paths_study")
    dx, dz = q[0] - p[0], q[1] - p[1]
    length = math.hypot(dx, dz)
    if length <= abs(rp - rq):
        c, r = (p, rp) if rp >= rq else (q, rq)
        return s.cyl(*c, y0, y1, r)
    ux, uz = dx / length, dz / length
    c = (rp - rq) / length
    h = math.sqrt(1 - c * c)
    n0, n1 = (ux * c - uz * h, uz * c + ux * h), (ux * c + uz * h, uz * c - ux * h)
    points = [(p[0] + rp * n0[0], p[1] + rp * n0[1]),
              (q[0] + rq * n0[0], q[1] + rq * n0[1]),
              (q[0] + rq * n1[0], q[1] + rq * n1[1]),
              (p[0] + rp * n1[0], p[1] + rp * n1[1])]
    shape = polygon(points, y0, y1)
    shape = op(shape, s.cyl(*p, y0, y1, rp), "join")
    return op(shape, s.cyl(*q, y0, y1, rq), "join")


def swept_capsule(q, rp, rq, y0, y1, angles=(-7.0, .3)):
    m = load("sparkshift_ahg_min")
    p = m.STATE["Mv"]
    a, b = sorted(angles)
    shape = op(tapered_capsule(p, rp, m.rot_pt(q, p, a), rq, y0, y1),
               tapered_capsule(p, rp, m.rot_pt(q, p, b), rq, y0, y1), "join")
    distance, phi = m.polar(p, q)
    return op(shape, m.sector(p, 0, distance + rq, phi - b, phi - a, y0, y1), "join")


def foot_envelope(y0, y1):
    m = load("sparkshift_ahg_min")
    points = [m.rot_pt(p, m.STATE["Mv"], a) for p in ((15.4, -9.6), (15.7, -5.1))
              for a in (-7, .3)]
    points.sort()

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    lower, upper = [], []
    for point in points:
        while len(lower) > 1 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper) > 1 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    shape = polygon(hull, y0, y1)
    # The 0.38 mm enlargement includes the <0.051 mm orbital sagitta between end poses.
    for a, b in zip(hull, hull[1:] + hull[:1]):
        shape = op(shape, tapered_capsule(a, 2.33, b, 2.33, y0, y1), "join")
    return shape


def backbone():
    """Broader ring and tangent webs; the old bearing seats remain geometrically untouched."""
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    before = STATE["before"]
    pivot, hob, joint = m.STATE["Mv"], m.HOB_MOVING, m.JOINT_AXES[0]
    ring_r, hob_r, joint_r, gap = 10.25, 6.0, 4.8, .4
    y0, y1 = 11.0, m.ARM_SPLIT_V6
    upper = tapered_capsule(pivot, ring_r, joint, joint_r, y0, y1)
    lower = tapered_capsule(pivot, ring_r, hob, hob_r, y0, y1)
    fill = op(upper, lower, "join")
    for centre, radius in ((pivot, 7.8), (hob, 3.9)):
        fill = op(fill, s.cyl(*centre, y0 - .1, y1 + .1, radius), "cut")
    fill = op(fill, s.cyl(*joint, y0 - .1, y1 + .1, 1.7), "cut")
    spring_void = s.box(-20, 11.85, 10.3, 19.0, 27.95, 36.45)
    fill = op(fill, spring_void, "cut")
    rear = op(before["P04R"], fill, "join")
    stub = s.box(13.3, 17.6, 6.7, 12.0, -12.0, -7.8)
    rear = op(rear, stub, "cut")

    relief = op(swept_capsule(joint, ring_r + gap, joint_r + gap, y0 - gap, y1 + gap),
                swept_capsule(hob, ring_r + gap, hob_r + gap, y0 - gap, y1 + gap), "join")
    front = op(before["P03"], relief, "cut")
    gear_relief = m.arc_slot(hob, 10.1, -7, .3, 15.65, 20.35)
    front = op(front, gear_relief, "cut")

    back = op(before["P01"], s.box(-4.85, 2.5, 6.4, 11.4, -7.7, .2), "join")
    back = op(back, s.box(13.5, 18.0, 6.8, 11.4, -11.6, -8.1), "join")
    back = op(back, m.arc_slot(hob, 6.0, -7, .3, 6.35, 11.4), "cut")
    back = op(back, relief, "cut")
    candidates = {"P01": back, "P03": front, "P04R": rear}
    for key, body in candidates.items():
        if body.lumps.count != 1:
            raise RuntimeError("Disconnected candidate: " + key)
    STATE["candidate"].update(candidates)
    STATE["backbone_fill"] = fill
    STATE["backbone_relief"] = relief
    report = {key: {**stats(body), "delta_mm3": round((body.volume - before[key].volume) * 1000, 3)}
              for key, body in candidates.items()}
    (OUT / "v7_backbone.json").write_text(json.dumps(report, indent=2))
    return report


def smooth_details():
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    c = STATE["candidate"]
    pivot, hob, joint = m.STATE["Mv"], m.HOB_MOVING, m.JOINT_AXES[0]
    seat = s.box(11.82, 19.7, 7.0, 15.6, 27.95, 36.35)
    seat = op(seat, s.cyl(*joint, 6.9, 10.1, 3.0), "cut")
    seat = op(seat, s.cyl(*joint, 10.0, 15.7, 1.7), "cut")
    rear = op(c["P04R"], seat, "join")
    rear = op(rear, s.box(8.4, 11.82, 10.7, 15.7, 27.4, 30.85), "cut")
    rear = op(rear, s.box(8.4, 11.82, 10.7, 15.7, 33.65, 36.6), "cut")

    front = c["P03"]
    # Existing relief scallops are wholly within this deliberately circular clearance.
    front = op(front, m.arc_slot(hob, 6.4, -7, .3, 10.6, 16.01), "cut")

    p02 = c["P02"]
    motor = m.motor_axis({n: b for n, b in STATE["before_all"].items()})
    p02 = op(p02, s.cyl(*motor, -13.7, -10.05, 19.3), "join")
    p02 = op(p02, s.cyl(*motor, -13.8, .4, 18.55), "cut")
    a = load("ahg_placement")
    angle = math.radians(m.THETA)
    lead = (-math.cos(angle), math.sin(angle))
    p02 = op(p02, a.obb(motor[0] + lead[0] * 26, (-14.7 + m.LEAD_DEPTH_Y) / 2,
                        motor[1] + lead[1] * 26, lead, 20, m.LEAD_DEPTH_Y + 14.7, 12), "cut")
    STATE["candidate"].update(P02=p02, P03=front, P04R=rear)
    return {key: stats(c[key]) for key in ("P02", "P03", "P04R")}


def refine_print_faces():
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    c = STATE["candidate"]
    front = c["P03"]
    # Magnet position is fixed. Remove the perforated 0.07 mm backing skin, not the magnet pocket.
    opening = s.box(3.19, 9.60, 28.55, 28.90, -6.2, 7.90)
    front = op(front, opening, "cut")
    magnet_stop = s.box(3.2, 9.7, 26.8, 28.60, 7.9, 9.38)
    front = op(front, magnet_stop, "join")
    p04f = c["P04F"]
    # Merge the split arm's lower contact foot into a simple rounded support.
    foot = tapered_capsule((15.4, -9.6), 1.95, (15.7, -5.1), 1.95, 15.6, 29.4)
    foot = op(foot, s.cyl(*m.HOB_MOVING, 15.5, 20.4, 10.25), "cut")
    foot = op(foot, s.cyl(*m.HOB_MOVING, 20.3, 24.35, 9.65), "cut")
    p04f = op(p04f, foot, "join")
    p04f = op(p04f, s.cyl(*m.HOB_MOVING, 20.3, 24.25, 9.4), "cut")
    # Recut concentric seat surfaces instead of retaining offset copies of the same bore.
    cup = s.cyl(*m.STATE["Mv"], 20.15, 24.2, 6.15)
    p04f = op(p04f, cup, "join")
    for a, b, radius in ((20.1, 22.0, 2.35), (22.0, 22.3, 2.8),
                         (22.3, 24.15, 3.52), (24.15, 25.1, 4.35)):
        p04f = op(p04f, s.cyl(*m.STATE["Mv"], a, b, radius), "cut")
    p04f = op(p04f, s.cyl(*m.HOB_MOVING, 20.05, 24.25, 9.4), "cut")
    front = op(front, foot_envelope(15.2, 29.8), "cut")

    lever = tapered_capsule((-.6, 54.2), 4.1, (-.9, 72.2), 3.5, 12.95, 15.6)
    rear = op(c["P04R"], lever, "join")
    lever_relief = m.sector(m.STATE["Mv"], 37.8, 64.0, 96.3, 116.6, 12.55, 16.0)
    front = op(front, lever_relief, "cut")
    front = op(front, s.box(-10, 8, 16.0, 19.2, 57.8, 62.22059521522817), "join")
    STATE["candidate"].update(P03=front, P04F=p04f, P04R=rear)
    return {key: stats(c[key]) for key in ("P03", "P04F", "P04R")}


def refine_case_pockets():
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    front = STATE["candidate"]["P03"]
    rim = s.cyl(*m.STATE["Mv"], 11.4, 15.99, 11.2)
    rim = op(rim, s.box(10.0, 22.5, 11.3, 16.1, -10, 40), "common")
    front = op(front, rim, "join")
    front = op(front, STATE["backbone_relief"], "cut")
    front = op(front, m.arc_slot(m.HOB_MOVING, 7.5, -7, .3, 24.24, 28.61), "cut")
    front = op(front, foot_envelope(15.2, 29.8), "cut")
    STATE["candidate"]["P03"] = front
    return stats(front)


def candidate_shots(app, keys, tag, views=("front", "front_iso", "rear_iso")):
    m = load("sparkshift_ahg_min")
    out = []
    for key in keys:
        body = STATE["candidate"][key]
        bb = m.bb_of(body)
        centre = tuple((bb[2 * i] + bb[2 * i + 1]) / 2 for i in range(3))
        extents = max(bb[1] - bb[0], bb[5] - bb[4]) * .11
        out.extend(m.solo_shots(app, [body], m.std_views(centre, extents, views), tag + "_" + key,
                               colours={"shape": (185, 190, 200)}))
    return out


def candidate_contacts(app, key, angles=(0.3, 0, -3.5, -6.05, -7.0), near=.41):
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    by = {b.name: b for b in s.proxies(root)}
    changed = {PARTS[k]: b for k, b in STATE["candidate"].items()}
    arm_names = {b.name for b in m.arm_split(app)[0]}
    target_name = PARTS[key]
    report = {"key": key, "pairs": [], "errors": []}
    for angle in angles:
        target = changed[target_name]
        if target_name in arm_names:
            target = m.rotated(target, m.STATE["Mv"], angle)
        for name, proxy in by.items():
            if name == target_name or name in m.STATE["leftovers"] or name == "CLOSING_SPRING_ENVELOPE":
                continue
            if "TEMP" in proxy.assemblyContext.fullPathName:
                continue
            other = changed.get(name, proxy)
            if name in arm_names:
                other = m.rotated(other, m.STATE["Mv"], angle)
            if m.bb_gap_l(m.bb_of(target), m.bb_of(other)) > near:
                continue
            try:
                distance = app.measureManager.measureMinimumDistance(target, other).value * 10
                volume = s.common_volume(target, other)[0] if distance < 1e-5 else 0.0
                if distance < near or volume > .001:
                    report["pairs"].append([angle, name, round(distance, 4), round(volume, 4)])
            except RuntimeError as error:
                report["errors"].append([angle, name, str(error)])
    (OUT / ("v7_contacts_" + key + ".json")).write_text(json.dumps(report, indent=2))
    return report


def structural_report(app):
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    report = {}
    for key, body in STATE["candidate"].items():
        before = STATE["before"][key]
        direction = (0, 1, 0) if key == "P01" else (0, -1, 0)
        if body.lumps.count != 1:
            raise RuntimeError("Disconnected print: " + key)
        report[key] = {"before": stats(before), "after": stats(body),
                       "overhang_before_mm2": m.overhang(before, direction)["total_mm2"],
                       "overhang_after_mm2": m.overhang(body, direction)["total_mm2"]}
    clip = s.box(-30, 30, -20, 40, -70, -18)
    before = op(STATE["before"]["P01"], clip, "common")
    after = op(STATE["candidate"]["P01"], clip, "common")
    added, removed = op(after, before, "cut"), op(before, after, "cut")
    report["frozen_belt_mount"] = {"added_mm3": added.volume * 1000,
                                 "removed_mm3": removed.volume * 1000}
    if max(added.volume, removed.volume) > 1e-7:
        raise RuntimeError("Frozen belt mounting changed")
    report["upper_neck_at_z24_y13"] = {}
    for label, body in (("before", STATE["before"]["P04R"]), ("after", STATE["candidate"]["P04R"])):
        section = op(body, s.box(-25, 25, 12.99, 13.01, 23.99, 24.01), "common")
        bb = m.bb_of(section)
        report["upper_neck_at_z24_y13"][label] = {"width_mm": round(bb[1] - bb[0], 3),
                                                "lumps": section.lumps.count}
    report["hinge_ring_radial_wall_mm"] = {"before": 2.0, "after": 2.75}
    report["front_cross_bridge_mm"] = {"depth_y": 3.2, "height_z": 4.4206,
                                      "lever_clearance_y": .4}
    (OUT / "v7_structure.json").write_text(json.dumps(report, indent=2))
    return report


def apply_revision(app):
    if STATE.get("applied"):
        raise RuntimeError("v7 is already applied")
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    by = {b.name: b for b in s.proxies(root)}
    for key, baseline in STATE["before"].items():
        current = by[PARTS[key]]
        if current.faces.count != baseline.faces.count or abs(current.volume - baseline.volume) > 1e-7:
            raise RuntimeError("The live model changed since baseline capture: " + key)
    STATE["applied_parts"] = []
    for key, body in STATE["candidate"].items():
        by = {b.name: b for b in s.proxies(root)}
        m.replace(by[PARTS[key]], body)
        STATE["applied_parts"].append(key)
        (OUT / "v7_apply_status.json").write_text(json.dumps(STATE["applied_parts"]))
    STATE["applied"] = True
    app.activeDocument.name = "SparkShift AHG-min v7 - structural cleanup"
    return STATE["applied_parts"]


def build():
    if STATE.get("applied"):
        raise RuntimeError("Start from the preserved v6 archive, not the applied v7 model")
    s = load("pancake_paths_study")
    STATE["candidate"] = {key: s.tbm().copy(b) for key, b in STATE["before"].items()}
    backbone()
    smooth_details()
    refine_print_faces()
    refine_case_pockets()
    return {key: stats(body) for key, body in STATE["candidate"].items()}


def export_meshes(app):
    if not STATE.get("applied"):
        raise RuntimeError("Apply and review the revision before exporting")
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    names = {
        **{key: (name, {"P01": "P01_Back_case", "P02": "P02_Motor_servo_plate",
                       "P03": "P03_Front_case", "P04R": "P04R_Swing_arm_rear_half",
                       "P04F": "P04F_Swing_arm_front_half"}[key])
           for key, name in PARTS.items()},
        "P05": ("PRINT_DIRECT_CAM", "P05_Servo_cam"),
        "P06": ("PRINT_compound_left", "P06_Left_compound_38T_14T"),
        "P07": ("PRINT_compound_right", "P07_Right_compound_38T_14T"),
    }
    folder = OUT / "stl_v7_assembly"
    folder.mkdir(parents=True, exist_ok=True)
    states = [(o, o.isLightBulbOn) for o in root.allOccurrences]
    bodies = [(b, b.isLightBulbOn) for b in by.values()]
    report = {}
    try:
        for occ, _ in states:
            occ.isLightBulbOn = True
        for key, (name, filename) in names.items():
            body = by[name]
            body.isLightBulbOn = True
            path = folder / (filename + ".stl")
            options = design.exportManager.createSTLExportOptions(body, str(path))
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            options.isBinaryFormat = True
            if not design.exportManager.execute(options) or not path.exists() or path.stat().st_size <= 84:
                raise RuntimeError("No STL data exported: " + key)
            report[key] = {"path": str(path), "native": stats(body),
                           "build_direction": [0, 1, 0] if key in ("P01", "P06", "P07") else [0, -1, 0]}
            (OUT / "v7_mesh_export.json").write_text(json.dumps(report, indent=2))
    finally:
        for b, light in bodies:
            if b.isValid:
                b.isLightBulbOn = light
        for o, light in states:
            if o.isValid:
                o.isLightBulbOn = light
    return report
