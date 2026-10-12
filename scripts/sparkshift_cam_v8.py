"""Short, horn-keyed cam with an accessible servo-matched centre retainer.

The retained horn/spline are fit envelopes. The M2x16 retainer is a dimensional
reference derived from the existing OEM-screw model, not a verified MG90S thread.
"""

import hashlib
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
CAM = "PRINT_DIRECT_CAM"
CASE = "PRINT_000_outer_shell_of_extruder_1"
FRONT_ARM = "PRINT_arm_front_half"
REAR_ARM = "PRINT_carrier_box_left"
BACK_CASE = "PRINT_motor_mount"
BEARING = "CAM_OUTBOARD_MF85ZZ_5x8x2p5"
SCREW = "CAM_CENTRE_RETAINER_M2x16_REFERENCE_VERIFY_THREAD"
WASHER = "CAM_CENTRE_WASHER_2p2x5x0p3"
LOWER_BOLT = "ARM_LOWER_M3x16_BUTTON_HEAD"
LOWER_NUT = "ARM_LOWER_M3_HEX_NUT"
ARM_ADDED = {LOWER_BOLT, LOWER_NUT}
REPLACEMENTS = {CAM: CAM, CASE: CASE, BACK_CASE: BACK_CASE, FRONT_ARM: FRONT_ARM, REAR_ARM: REAR_ARM,
                "CAM_OUTBOARD_MF63": BEARING, "OEM_HORN_SCREW": SCREW}
REMOVED = ("CAM_JOURNAL_PIN_3x10", "CAM_HORN_SELF_TAP_-5.5", "CAM_HORN_SELF_TAP_5.5")
CAM_ROTATES = {CAM, "OEM_SERVO_HORN", "OEM_SERVO_SPLINE", SCREW, WASHER}
POSES = ((0, 0), (30, -.02), (60, -1.55), (90, -4.453), (120, -5.98),
         (150, -6.053), (180, -5.58), (0, .3), (0, -7))


def load(name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def op(a, b, kind):
    s = load("pancake_paths_study")
    shape = s.tbm().copy(a)
    s.op(shape, b, kind)
    if not math.isfinite(shape.volume):
        raise RuntimeError("Invalid " + kind + " result")
    return shape


def stats(body):
    m = load("sparkshift_ahg_min")
    return {"faces": body.faces.count, "lumps": body.lumps.count,
            "volume_mm3": round(body.volume * 1000, 4),
            "bounds_mm": [round(x, 4) for x in m.bb_of(body)]}


def initialize(app, output=None, back_case_input=None):
    global OUT
    if STATE:
        raise RuntimeError("Cam baseline already captured")
    if output is not None:
        OUT = Path(output)
    OUT.mkdir(parents=True, exist_ok=True)
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    by = {b.name: b for b in s.proxies(root)}
    if BEARING in by or by[CASE].faces.count != 516 or "CAM_JOURNAL_PIN_3x10" not in by:
        raise RuntimeError("Open the saved AHG-min v7 baseline")
    STATE["before"] = {n: s.tbm().copy(b) for n, b in by.items()}
    STATE["native_start"] = dict(STATE["before"])
    STATE["paths"] = {n: b.assemblyContext.fullPathName for n, b in by.items()}
    STATE["C"] = s.centre(by["CAM_OUTBOARD_MF63"])
    STATE["Mv"] = s.centre(by["AXLE_4x24_moving"])
    m.STATE.update(C=STATE["C"], Mv=STATE["Mv"])
    if back_case_input is not None:
        source = Path(back_case_input)
        original = app.activeDocument
        document = app.importManager.importToNewDocument(
            app.importManager.createFusionArchiveImportOptions(str(source)))
        try:
            imported = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
            if imported.rootComponent.bRepBodies.count != 1 or imported.rootComponent.occurrences.count:
                raise RuntimeError("Expected the captured, one-body P01 input")
            body = s.tbm().copy(imported.rootComponent.bRepBodies.item(0))
            if body.lumps.count != 1 or stats(body)["bounds_mm"] != stats(STATE["before"][BACK_CASE])["bounds_mm"]:
                raise RuntimeError("Captured P01 has an unexpected coordinate frame")
            STATE["original_back_case"] = STATE["before"][BACK_CASE]
            STATE["before"][BACK_CASE] = body
            STATE["back_case_input_path"] = str(source)
            STATE["back_case_input_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        finally:
            document.close(False)
            original.activate()
    report = {n: stats(by[n]) for n in (*REPLACEMENTS, *REMOVED, "OEM_SERVO_HORN")}
    (OUT / "v8_baseline.json").write_text(json.dumps(report, indent=2))
    return report


def correct_marked_regions():
    s, m, v = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_strength_v7")
    before = STATE["before"]
    case = before[CASE]
    case = op(case, s.box(-3.5, 5.15, 11.35, 15.65, 48.8, 51.05), "cut")
    case = op(case, s.cyl(*m.HOB_FIXED, 11.39, 20.26, 10.15), "cut")
    case = op(case, s.box(18.0, 20.45, 11.39, 30.31, 4.0, 18.5), "cut")

    magnet = before["OCT_RECEIVER_MAGNET_3"]
    mb = m.bb_of(magnet)
    backing = s.box(3.2, 9.65, 27.2, mb[2], mb[4] - .25, mb[5] + .25)
    case = op(case, backing, "join")
    # The old fore cup continues 1.7 mm beyond its bearing. Remove that unused
    # extension, not the bearing seat, to make room for a complete magnet backing.
    relief = v.tapered_capsule(m.HOB_MOVING, 7.1, (m.HOB_MOVING[0], 6.8), 6.3, 26.85, 31.0)
    front_arm = op(before[FRONT_ARM], relief, "cut")
    footprint = s.box(mb[0], mb[1], mb[2] - 1.5, mb[2], mb[4], mb[5])
    missing = op(footprint, case, "cut")
    if missing.volume > 1e-8:
        raise RuntimeError("The magnet footprint is not completely backed")
    STATE["magnet_backing_probe"] = footprint
    STATE["magnet_backing"] = backing
    STATE["marked_parts"] = {CASE: case, FRONT_ARM: front_arm}
    report = {"magnet_backing_thickness_mm": mb[2] - 27.2,
              "magnet_footprint_mm": [mb[1] - mb[0], mb[5] - mb[4]],
              "unbacked_volume_mm3": missing.volume * 1000,
              "fore_bearing_end_y_mm": m.bb_of(before["STOCK_049_3mm_flange_bearing_1_2"])[3],
              "fore_arm_trim_plane_y_mm": 26.85,
              "parts": {n: stats(b) for n, b in STATE["marked_parts"].items()}}
    (OUT / "v8_marked_regions.json").write_text(json.dumps(report, indent=2))
    return STATE["marked_parts"]


def clean_spring_pocket(case):
    s, m, v = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_strength_v7")
    spring_z = STATE["C"][1] - 18.5
    case = op(case, s.box(-10.295, -3.25, 11.4, 19.1, 25.4, 30.5), "join")
    channel = m.axis_cyl((0, 14.6, spring_z), (1, 0, 0), 4.6, -10.295, -3.20)
    case = op(case, channel, "cut")
    case = op(case, s.box(-3.25, 2.0, 11.39, 19.21, 22.3, 30.5), "cut")
    case = op(case, s.box(3.1, 11.85, 11.39, 16.01, 24.8, 28.25), "cut")

    rear = STATE["before"][REAR_ARM]
    ramp = v.polygon([(4.0, 24.5), (12.0, 24.5), (12.0, 27.4),
                      (11.82, 27.4), (4.0, 26.0)], 11.0, 15.6)
    rear = op(rear, ramp, "join")
    angle = math.degrees(math.atan2(1.4, 7.82))
    trim = op(m.half_xz((4.0, 26.0), angle, 10.7, 15.7),
              s.box(3.9, 11.82, 10.7, 15.7, 25.0, 30.8), "common")
    rear = op(rear, trim, "cut")
    STATE["spring_channel"] = channel
    return case, rear


def circle_hull(circles, y0, y1):
    v = load("sparkshift_strength_v7")
    points = sorted(set(p for p, _ in circles))

    def turn(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    lower, upper = [], []
    for point in points:
        while len(lower) > 1 and turn(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper) > 1 and turn(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    shape = v.polygon(hull, y0, y1)
    for i, (p, rp) in enumerate(circles):
        for q, rq in circles[i + 1:]:
            shape = op(shape, v.tapered_capsule(p, rp, q, rq, y0, y1), "join")
    return shape


def tie_sweep(a, ra, b, rb, y0, y1):
    m = load("sparkshift_ahg_min")
    # 0.4 mm includes 0.35 mm clearance and the <=0.055 mm endpoint-chord sagitta.
    circles = [(m.rot_pt(p, STATE["Mv"], angle), radius + .405)
               for p, radius in ((a, ra), (b, rb)) for angle in (-7, .3)]
    return circle_hull(circles, y0 - .35, y1 + .35)


def add_arm_connections(case, rear, front):
    s, m, v = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_strength_v7")
    lower, hob, old_foot = (8.0, -13.3), m.HOB_MOVING, (15.4, -9.6)
    radius = 3.3
    rear_leg = v.tapered_capsule(hob, 6.0, lower, radius, 11.4, 15.6)
    for centre, r in ((hob, 3.9), (STATE["Mv"], 7.8)):
        rear_leg = op(rear_leg, s.cyl(*centre, 10.9, 15.7, r), "cut")
    rear = op(rear, rear_leg, "join")
    front_bar = v.tapered_capsule(lower, radius, old_foot, 2.0, 15.6, 24.5)
    front_bar = op(front_bar, s.cyl(*hob, 15.5, 20.4, 10.1), "cut")
    front_bar = op(front_bar, s.cyl(*hob, 20.3, 24.6, 9.4), "cut")
    frame_keepout = m.arc_slot((18.75, -14.73), 3.85, -.3, 7, 14.0, 30.0)
    front_bar = op(front_bar, frame_keepout, "cut")
    front = op(front, front_bar, "join")
    bore = s.cyl(*lower, 11.3, 24.6, 1.7)
    rear, front = op(rear, bore, "cut"), op(front, bore, "cut")

    front = op(front, s.cyl(15.55, 24.5, 15.6, 19.8, 4.0), "join")
    key_a, key_b = (15.55, 23.95), (15.55, 25.05)
    key = v.tapered_capsule(key_a, 1.75, key_b, 1.75, 13.25, 15.7)
    pocket = v.tapered_capsule(key_a, 1.9, key_b, 1.9, 13.1, 15.7)
    front, rear = op(front, key, "join"), op(rear, pocket, "cut")

    screw = m.screw_shape(*lower, 11.4, 2.85, 1.65, 27.4, r=1.5)
    socket_radius = 2.0 / math.sqrt(3)
    socket = [(lower[0] + socket_radius * math.cos(i * math.pi / 3),
               lower[1] + socket_radius * math.sin(i * math.pi / 3)) for i in range(6)]
    screw = op(screw, v.polygon(socket, 9.65, 10.7), "cut")
    nut_radius = 5.5 / math.sqrt(3)
    hexagon = [(lower[0] + nut_radius * math.cos(i * math.pi / 3),
                lower[1] + nut_radius * math.sin(i * math.pi / 3)) for i in range(6)]
    nut = op(v.polygon(hexagon, 24.5, 26.9), s.cyl(*lower, 24.4, 27.0, 1.5), "cut")

    rear_clearance = tie_sweep(hob, 6.0, lower, radius, 11.4, 15.6)
    front_clearance = tie_sweep(lower, radius, old_foot, 2.0, 15.6, 24.5)
    nut_clearance = m.arc_slot(lower, nut_radius + .35, -7, .3, 24.15, 27.25)
    head_clearance = m.arc_slot(lower, 3.2, -7, .3, 9.4, 11.75)
    tip_clearance = m.arc_slot(lower, 1.85, -7, .3, 26.8, 27.75)
    STATE["back_clearance_tools"] = [
        ("root", rear_clearance), ("front", front_clearance), ("nut", nut_clearance),
        ("head", head_clearance), ("tip", tip_clearance)]
    back = STATE["before"][BACK_CASE]
    for tool in (rear_clearance, front_clearance, nut_clearance, head_clearance, tip_clearance):
        case = op(case, tool, "cut")
        back = op(back, tool, "cut")
    case = op(case, m.arc_slot((15.55, 24.5), 4.35, -7, .3, 15.25, 20.15), "cut")
    keeper = op(STATE["before"][CASE], s.cyl(18.75, -14.73, 9.7, 29.8, 3.5), "common")
    case = op(case, keeper, "join")
    STATE["lower_axis"] = lower
    STATE["central_key"] = key
    STATE["central_key_pocket"] = pocket
    report = {"lower_bolt": "M3x16 ISO7380 button head + ordinary M3 hex nut",
              "lower_axis_xz_mm": lower, "head_seat_y_mm": 11.4, "nut_y_mm": [24.5, 26.9],
              "screw_tip_y_mm": 27.4, "through_bore_diameter_mm": 3.4,
              "lower_boss_diameter_mm": 6.6, "nominal_boss_radial_wall_mm": 1.6,
              "central_land_mm": [8.0, 4.2, 8.0],
              "key_width_height_mm": [3.5, 4.6], "key_engagement_mm": 2.35,
              "key_side_clearance_mm": .15, "key_tip_clearance_mm": .15,
              "nut_access": "Tighten on the bench before fitting the arm into the cases",
              "print_note": "Key projects rearward from the front half; rear split-plane print face is retained"}
    (OUT / "v8_arm_connections.json").write_text(json.dumps(report, indent=2))
    return case, back, rear, front, screw, nut


def build():
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    C = STATE["C"]
    before = STATE["before"]
    cam = op(before[CAM], s.box(-30, 40, 9.2, 40, 20, 80), "cut")
    cam = op(cam, s.cyl(*C, .3, 4.85, 7.3), "join")
    for dx in (-5.5, 5.5):
        cam = op(cam, s.cyl(C[0] + dx, C[1], .3, 9.2, 1.6), "join")
    cam = op(cam, s.cyl(*C, .3, 9.2, 2.0), "join")
    cam = op(cam, m.cone_y(*C, 9.2, 3.6, 10.5, 2.475), "join")
    cam = op(cam, s.cyl(*C, 10.4, 13.7, 2.475), "join")
    pocket = s.box(C[0] - 7.1, C[0] + 7.1, .2, 2.0, C[1] - 2.6, C[1] + 2.6)
    pocket = op(pocket, s.cyl(*C, .2, 2.0, 3.3), "join")
    cam = op(cam, pocket, "cut")
    cam = op(cam, s.cyl(*C, .2, 13.8, 1.1), "cut")

    # Catalogue MF85ZZ: 5x8x2.5, 9.2 mm flange, 0.6 mm flange thickness.
    bearing = s.cyl(*C, 10.7, 13.2, 4.0)
    bearing = op(bearing, s.cyl(*C, 10.7, 11.3, 4.6), "join")
    bearing = op(bearing, s.cyl(*C, 10.6, 13.3, 2.5), "cut")
    screw = m.screw_shape(*C, 14.0, 1.9, 2.0, -2.0, r=1.0)
    radius = 1.5 / math.sqrt(3)
    hexagon = [(C[0] + radius * math.cos(i * math.pi / 3),
                C[1] + radius * math.sin(i * math.pi / 3)) for i in range(6)]
    screw = op(screw, load("sparkshift_strength_v7").polygon(hexagon, 14.7, 16.1), "cut")
    washer = op(s.cyl(*C, 13.7, 14.0, 2.5), s.cyl(*C, 13.6, 14.1, 1.1), "cut")

    marked = correct_marked_regions()
    case, rear = clean_spring_pocket(marked[CASE])
    case = op(case, s.cyl(*C, 10.5, 15.5, 6.2), "join")
    for y0, y1, radius in ((10.4, 11.3, 4.65), (11.25, 13.2, 4.02), (13.15, 39, 3.2)):
        case = op(case, s.cyl(*C, y0, y1, radius), "cut")
    case, back, rear, front, lower_screw, lower_nut = add_arm_connections(case, rear, marked[FRONT_ARM])
    shapes = {CAM: cam, CASE: case, BACK_CASE: back, FRONT_ARM: front, REAR_ARM: rear,
              BEARING: bearing, SCREW: screw, WASHER: washer, LOWER_BOLT: lower_screw, LOWER_NUT: lower_nut}
    for name, shape in shapes.items():
        if shape.lumps.count != 1:
            raise RuntimeError("Disconnected cam-stack part: " + name)
    STATE["shapes"] = shapes
    report = {n: stats(b) for n, b in shapes.items()}
    report["dimensions"] = {
        "journal_diameter_mm": 4.95, "journal_root_y_mm": 9.2, "journal_end_y_mm": 13.7,
        "journal_total_length_mm": 4.5, "straight_journal_y_mm": [10.5, 13.7],
        "journal_min_radial_wall_mm": 1.375, "old_pin_length_mm": 10.0,
        "bearing_y_mm": [10.7, 13.2], "washer_y_mm": [13.7, 14.0],
        "bearing_to_washer_axial_gap_mm": .5, "screw_y_mm": [-2.0, 16.0],
        "case_driver_access_diameter_mm": 6.4,
    }
    (OUT / "v8_build.json").write_text(json.dumps(report, indent=2))
    return report


def geometry():
    shapes = {n: b for n, b in STATE["before"].items() if n not in (*REPLACEMENTS, *REMOVED)}
    shapes.update(STATE["shapes"])
    return shapes


def contact_check(app, poses=POSES):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    report = {"poses": list(poses), "overlaps": [], "near": [], "errors": []}
    for phi, arm in poses:
        shapes = {}
        for name, body in geometry().items():
            if name in CAM_ROTATES:
                shapes[name] = m.rotated(body, STATE["C"], phi)
            elif name in ARM_ADDED or any(k in STATE["paths"].get(name, "") for k in m.ARM_GROUPS):
                shapes[name] = m.rotated(body, STATE["Mv"], arm)
            else:
                shapes[name] = body
        names = list(shapes)
        for i, n in enumerate(names):
            if n not in STATE["shapes"]:
                continue
            a = shapes[n]
            for j, o in enumerate(names):
                if n == o or (o in STATE["shapes"] and j < i):
                    continue
                if o in m.STATE.get("leftovers", ()) or o == "CLOSING_SPRING_ENVELOPE":
                    continue
                b = shapes[o]
                if m.bb_gap_l(m.bb_of(a), m.bb_of(b)) > .7:
                    continue
                try:
                    distance = app.measureManager.measureMinimumDistance(a, b).value * 10
                    volume = s.common_volume(a, b)[0] if distance < 1e-5 else 0.0
                    if volume > .001:
                        report["overlaps"].append([phi, arm, n, o, round(volume, 4)])
                    elif distance < .4:
                        report["near"].append([phi, arm, n, o, round(distance, 4)])
                except RuntimeError as error:
                    report["errors"].append([phi, n, o, str(error)])
        (OUT / "v8_contacts.json").write_text(json.dumps(report, indent=2))
    return report


def detail_shots(app, prefix="v8_cam"):
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    shapes = geometry()
    palette = {CAM: (215, 110, 55), BEARING: (155, 180, 205), SCREW: (60, 80, 100),
               WASHER: (150, 160, 170), "OEM_SERVO_HORN": (65, 175, 215),
               "OEM_SERVO_SPLINE": (200, 180, 90), "HOBBY_SERVO_ENVELOPE": (90, 95, 110)}
    items = [(s.tbm().copy(shapes[n]), n, m.rgb_appearance(adsk.fusion.Design.cast(app.activeProduct),
                                                       "v8 " + n, colour))
             for n, colour in palette.items()]
    states = [(o, o.isLightBulbOn) for o in root.occurrences]
    old_images = m.IMAGES_V4
    group = s.add_group(root, "TEMP compact cam", items)
    m.IMAGES_V4 = OUT / "images_v8"
    try:
        for occ, _ in states:
            occ.isLightBulbOn = False
        C = STATE["C"]
        for suffix, eye, target, up, ext in m.std_views((C[0], 2, C[1]), 5.2,
                                                      ("front_iso", "rear_iso", "right")):
            m.camera_shot(app, prefix + suffix + ".png", eye, target, up, ext)
    finally:
        group.deleteMe()
        for occ, state in states:
            if occ.isValid:
                occ.isLightBulbOn = state
        m.IMAGES_V4 = old_images
    return prefix


def proof(app):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    before, shapes = STATE["before"], STATE["shapes"]
    def changed_in(name, regions):
        total = 0.0
        for region in regions:
            a, b = op(before[name], region, "common"), op(shapes[name], region, "common")
            total += op(a, b, "cut").volume + op(b, a, "cut").volume
        return total
    changed_seat = changed_in(FRONT_ARM, [
        s.cyl(*m.HOB_MOVING, 24.15, 26.75, 3.67),
        s.cyl(*STATE["Mv"], 20.1, 25.15, 4.4)])
    rear_change = changed_in(REAR_ARM, [
        s.cyl(*m.HOB_MOVING, 12.5, 16.05, 3.7),
        s.cyl(*STATE["Mv"], 10.95, 15.65, 7.55)])
    belt_change = changed_in(BACK_CASE, [s.box(-30, 30, -20, 40, -70, -18)])
    backing_missing = op(STATE["magnet_backing_probe"], shapes[CASE], "cut").volume * 1000
    report = {"bearing_seat_change_mm3": changed_seat * 1000,
              "rear_bearing_region_change_mm3": rear_change * 1000,
              "belt_mount_change_mm3": belt_change * 1000,
              "missing_magnet_backing_mm3": backing_missing,
              "arm_backing_clearance": [], "driver_access": [], "tool_withdrawal": [], "errors": []}
    if max(changed_seat, rear_change, belt_change) > 1e-8 or backing_missing > 1e-5:
        raise RuntimeError("Bearing engagement or complete magnet backing was not preserved")
    keeper = s.cyl(18.75, -14.73, 9.7, 29.8, 3.5)
    report["frame_keeper_removed_mm3"] = {}
    for name in (CASE, BACK_CASE):
        old_keeper = op(before[name], keeper, "common")
        new_keeper = op(shapes[name], keeper, "common")
        removed = op(old_keeper, new_keeper, "cut").volume * 1000
        report["frame_keeper_removed_mm3"][name] = removed
        if removed > 1e-5:
            raise RuntimeError("Lower frame-fastener support was reduced")
    for angle in (.3, 0, -2, -4, -6.053, -7):
        arm = m.rotated(shapes[FRONT_ARM], STATE["Mv"], angle)
        distance = app.measureManager.measureMinimumDistance(arm, STATE["magnet_backing"]).value * 10
        report["arm_backing_clearance"].append([angle, round(distance, 4)])
        if distance < .3:
            raise RuntimeError("Insufficient clearance behind the magnet")
    driver = s.cyl(*STATE["C"], 16.01, 60, 1.4)
    for n in (CASE, CAM, BEARING, WASHER):
        volume, _ = s.common_volume(driver, shapes[n])
        report["driver_access"].append([n, round(volume, 6)])
        if volume > 1e-5:
            raise RuntimeError("Blocked centre-screw driver: " + n)
    for distance in (0, 5, 10, 15, 20, 25, 30, 35):
        for name, body in before.items():
            if not STATE["paths"][name].startswith("12 "):
                continue
            tool = m.translated(body, dy=distance)
            for n in (CASE, BACK_CASE, FRONT_ARM, REAR_ARM, CAM, BEARING, SCREW, WASHER, LOWER_BOLT, LOWER_NUT):
                target = shapes[n]
                if n in (FRONT_ARM, REAR_ARM) or n in ARM_ADDED:
                    target = m.rotated(target, STATE["Mv"], -6.053)
                elif n in CAM_ROTATES:
                    target = m.rotated(target, STATE["C"], 150)
                if m.bb_gap_l(m.bb_of(tool), m.bb_of(target)) > 0:
                    continue
                volume, _ = s.common_volume(tool, target)
                if volume > .001:
                    report["tool_withdrawal"].append([distance, name, n, volume])
    (OUT / "v8_proof.json").write_text(json.dumps(report, indent=2))
    if report["tool_withdrawal"]:
        raise RuntimeError("Tool withdrawal obstructed")
    return report


def review_summary(report):
    expected = {
        frozenset((CASE, "SPRING_PRELOAD_M3_HEATSET")): 1.44,
        frozenset((REAR_ARM, "STOCK_047_3mm_flange_bearing_1_1")): .051,
        frozenset((BACK_CASE, "FRAME_M3_HEATSET_in_P01")): 15.5,
        frozenset((BACK_CASE, "SPACER_M3_HEATSET_0")): 16.22,
        frozenset((BACK_CASE, "SPACER_M3_HEATSET_1")): 16.22,
    }
    expected.update({frozenset((BACK_CASE, "CLAM_M3_FRAME_INSERT_" + str(i))): 1.44 for i in range(4)})
    unexpected = [p for p in report["overlaps"] if
                  p[4] > expected.get(frozenset((p[2], p[3])), 0)]
    return {"poses": report["poses"], "errors": report["errors"], "unexpected_overlaps": unexpected,
            "expected_press_fits": len(report["overlaps"]) - len(unexpected)}


def spring_views(app):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    colours = {CASE: (225, 160, 65), REAR_ARM: (190, 65, 75),
               "PRINT_SINGLE_SPRING_PRESSURE_CUP": (200, 205, 145),
               "6700ZZ arm rear hinge (on moving hub)": (165, 180, 195),
               "CAM_FOLLOWER_623": (165, 180, 195)}
    old_images = m.IMAGES_V4
    m.IMAGES_V4 = OUT / "images_v8"
    try:
        for stage in ("before", "after"):
            overrides = STATE.get("pre_spring_shapes", {}) if stage == "before" else STATE["shapes"]
            items = [(s.tbm().copy(overrides.get(n, STATE["before"].get(n))), n,
                      m.rgb_appearance(design, "v8 spring " + n, colour)) for n, colour in colours.items()]
            states = [(o, o.isLightBulbOn) for o in root.occurrences]
            group = s.add_group(root, "TEMP spring interface", items)
            try:
                for occ, _ in states:
                    occ.isLightBulbOn = False
                for suffix, eye, target, up, ext in m.std_views((1, 14, 28), 3.6, ("rear_iso", "rear")):
                    m.camera_shot(app, "v8_spring_" + stage + suffix + ".png", eye, target, up, ext)
            finally:
                group.deleteMe()
                for occ, light in states:
                    if occ.isValid:
                        occ.isLightBulbOn = light
    finally:
        m.IMAGES_V4 = old_images
    return "v8_spring"


def assembled_arm_views(app):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    names = [n for n, path in STATE["paths"].items() if any(g in path for g in m.ARM_GROUPS)]
    names += ["6700ZZ arm rear hinge (on moving hub)", "AXLE_4x24_moving", "PRINT_compound_left",
              LOWER_BOLT, LOWER_NUT]
    names = list(dict.fromkeys(names))
    shapes = geometry()
    colours = {REAR_ARM: (205, 65, 80), FRONT_ARM: (55, 145, 220),
               "ARM_SPLIT_M3x10_SHCS_0": (235, 190, 50), "ARM_SPLIT_M3_INSERT_0": (210, 150, 50),
               LOWER_BOLT: (235, 190, 50), LOWER_NUT: (210, 150, 50),
               "PRINT_feed_left": (100, 175, 95), "PRINT_compound_left": (150, 100, 190)}
    old_images = m.IMAGES_V4
    m.IMAGES_V4 = OUT / "images_v8"
    files = []
    try:
        for mode in ("complete", "structure"):
            chosen = names if mode == "complete" else [
                REAR_ARM, FRONT_ARM, "ARM_SPLIT_M3x10_SHCS_0", "ARM_SPLIT_M3_INSERT_0", LOWER_BOLT, LOWER_NUT]
            items = [(s.tbm().copy(shapes[n]), n,
                      m.rgb_appearance(design, "v8 assembled arm " + n,
                                       colours.get(n, (170, 185, 200)))) for n in chosen]
            states = [(o, o.isLightBulbOn) for o in root.occurrences]
            group = s.add_group(root, "TEMP assembled arm review", items)
            try:
                for occ, _ in states:
                    occ.isLightBulbOn = False
                views = ("front_iso", "rear_iso", "right") if mode == "complete" else ("right", "rear_iso")
                for suffix, eye, target, up, ext in m.std_views((8, 15, 32), 10.0, views):
                    name = "v8_arm_" + mode + suffix + ".png"
                    m.camera_shot(app, name, eye, target, up, ext)
                    files.append(name)
                if mode == "structure":
                    for suffix, eye, target, up, ext in m.std_views((10, 17, 8), 5.5, ("front_iso",)):
                        name = "v8_arm_lower_connection.png"
                        m.camera_shot(app, name, eye, target, up, ext)
                        files.append(name)
            finally:
                group.deleteMe()
                for occ, light in states:
                    if occ.isValid:
                        occ.isLightBulbOn = light
    finally:
        m.IMAGES_V4 = old_images
    rear, front = STATE["shapes"][REAR_ARM], STATE["shapes"][FRONT_ARM]
    volume, overlap = s.common_volume(rear, m.translated(front, dy=-.01))
    patches = []
    if overlap and overlap.lumps.count:
        for lump in overlap.lumps:
            patches.append({"area_estimate_mm2": round(lump.volume * 1000 / .01, 2),
                            "bounds_mm": [round(x, 3) for x in m.bb_of(lump)]})
    report = {"views": files, "complete_view_bodies": names,
              "split_y_mm": 15.6, "upper_clamp_axis_xz_mm": [14.95, 31.4],
              "hob_axis_xz_mm": list(m.HOB_MOVING), "lower_tie_fastener": "M3x16 button head and M3 nut",
              "lower_tie_axis_xz_mm": STATE["lower_axis"],
              "central_key": "3.5 x 4.6 mm rounded key, 2.35 mm engagement, broad mating land",
              "contact_patch_method": "0.01 mm axial overlap; geometric contact-area estimate only",
              "contact_patches": patches,
              "status": "User-directed two-piece arm with a lower bolt and central key; loaded stiffness not qualified"}
    (OUT / "v8_arm_assembly_review.json").write_text(json.dumps(report, indent=2))
    STATE["arm_review_names"] = names
    return report


def axial_section(app):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    C = STATE["C"]
    clip = s.box(C[0] - 10, C[0], -5, 20, C[1] - 10, C[1] + 10)
    colours = {CASE: (185, 190, 200), CAM: (220, 125, 60), BEARING: (130, 155, 180),
               SCREW: (65, 80, 100), WASHER: (145, 155, 170), "OEM_SERVO_HORN": (60, 180, 215),
               "OEM_SERVO_SPLINE": (200, 175, 80), "HOBBY_SERVO_ENVELOPE": (80, 90, 105)}
    items = []
    for name, colour in colours.items():
        body = op(geometry()[name], clip, "common")
        if body.lumps.count:
            items.append((body, name, m.rgb_appearance(adsk.fusion.Design.cast(app.activeProduct),
                                                      "v8 section " + name, colour)))
    states = [(o, o.isLightBulbOn) for o in root.occurrences]
    group = s.add_group(root, "TEMP compact cam section", items)
    old_images = m.IMAGES_V4
    m.IMAGES_V4 = OUT / "images_v8"
    try:
        for occ, _ in states:
            occ.isLightBulbOn = False
        cc = (C[0] / 10, .7, C[1] / 10)
        m.camera_shot(app, "v8_cam_axial_section.png", (cc[0] + 60, cc[1], cc[2]), cc,
                      (0, 0, 1), 3.1)
    finally:
        group.deleteMe()
        for occ, light in states:
            if occ.isValid:
                occ.isLightBulbOn = light
        m.IMAGES_V4 = old_images
    return "v8_cam_axial_section.png"


def apply(app):
    if STATE.get("applied"):
        raise RuntimeError("Compact cam revision is already applied")
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    by = {b.name: b for b in s.proxies(root)}
    for old in (*REPLACEMENTS, *REMOVED):
        initial = STATE.get("native_start", STATE["before"])
        if old not in by or stats(by[old]) != stats(initial[old]):
            raise RuntimeError("Live model changed since capture: " + old)
    status = []
    for old, new in REPLACEMENTS.items():
        by = {b.name: b for b in s.proxies(root)}
        label = {CAM: "P05 Compact cam - recessed OEM horn and centre retainer",
                 CASE: "P03 Front case - full magnet backing and MF85 support",
                 BACK_CASE: "P01 Back case - lower arm-bolt clearance",
                 FRONT_ARM: "P04F Front arm - full bearing engagement and magnet clearance",
                 REAR_ARM: "P04R Rear arm - smooth spring-pocket shoulder"}.get(new, new)
        m.replace(by[old], STATE["shapes"][new], new, label)
        status.append([old, new])
        (OUT / "v8_apply_status.json").write_text(json.dumps(status))
    add_hardware(app, WASHER, SCREW)
    add_hardware(app, LOWER_BOLT, REAR_ARM)
    add_hardware(app, LOWER_NUT, FRONT_ARM)
    for name in REMOVED:
        by = {b.name: b for b in s.proxies(root)}
        occurrence = by[name].assemblyContext
        if occurrence.component.bRepBodies.count != 1:
            raise RuntimeError("Removal would affect another body: " + name)
        occurrence.deleteMe()
    STATE["applied"] = True
    STATE["applied_shapes"] = dict(STATE["shapes"])
    app.activeDocument.name = "SparkShift AHG-min v8 - backed magnets and compact cam"
    return status


def refine_applied(app):
    if not STATE.get("applied"):
        raise RuntimeError("Use apply() for the first revision")
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    previous = STATE.get("applied_shapes", dict(STATE["shapes"]))
    STATE["pre_spring_shapes"] = previous
    build()
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    by = {b.name: b for b in s.proxies(root)}
    for name, new in STATE["shapes"].items():
        expected = previous.get(name, STATE["before"].get(name))
        if name in ARM_ADDED and name not in by and expected is None:
            continue
        if expected is None or (stats(by[name]) != stats(expected) and stats(by[name]) != stats(new)):
            raise RuntimeError("Live geometry changed before refinement: " + name)
    changed = []
    for name, new in STATE["shapes"].items():
        if name not in by and name in ARM_ADDED:
            add_hardware(app, name, REAR_ARM if name == LOWER_BOLT else FRONT_ARM)
            changed.append(name)
        elif stats(by[name]) != stats(new):
            if name == BACK_CASE and (by[name].nativeObject or by[name]).parentComponent.features.count > 1:
                append_back_clearance(app)
            else:
                m.replace(by[name], new)
            changed.append(name)
        current = {b.name: b for b in s.proxies(root)}
        if name in current:
            STATE.setdefault("applied_shapes", {})[name] = s.tbm().copy(current[name])
        (OUT / "v8_refinement_status.json").write_text(json.dumps(changed))
    STATE["applied_shapes"] = dict(STATE["shapes"])
    return changed


def append_back_clearance(app):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    proxy = by[BACK_CASE]
    component = (proxy.nativeObject or proxy).parentComponent
    tools = [(tag, tool) for tag, tool in STATE["back_clearance_tools"]
             if s.common_volume(proxy, tool)[0] > 1e-5]
    if not tools:
        return
    transform = proxy.assemblyContext.transform2.copy()
    transform.invert()
    names = ["V8_arm_clearance_" + tag for tag, _ in tools]
    missing = [(tag, tool) for tag, tool in tools
               if component.bRepBodies.itemByName("V8_arm_clearance_" + tag) is None]
    if missing:
        feature = component.features.baseFeatures.add()
        feature.name = "V8 lower-arm clearance tools"
        if feature.startEdit() is False:
            raise RuntimeError("Cannot create downstream clearance tools")
        try:
            for tag, tool in missing:
                shape = s.tbm().copy(tool)
                s.tbm().transform(shape, transform)
                body = component.bRepBodies.add(shape, feature)
                body.name = "V8_arm_clearance_" + tag
        finally:
            feature.finishEdit()
    for name in names:
        target = component.bRepBodies.itemByName(BACK_CASE)
        tool = component.bRepBodies.itemByName(name)
        if target is None or tool is None:
            raise RuntimeError("Missing downstream clearance body: " + name)
        collection = adsk.core.ObjectCollection.create()
        collection.add(tool)
        inp = component.features.combineFeatures.createInput(target, collection)
        inp.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        inp.isKeepToolBodies = False
        feature = component.features.combineFeatures.add(inp)
        feature.name = "V8 lower-arm clearance - " + name.rsplit("_", 1)[-1]
        if feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            raise RuntimeError("Downstream clearance failed: " + feature.errorOrWarningMessage)
        current = next(b for b in s.proxies(design.rootComponent) if b.name == BACK_CASE)
        STATE.setdefault("applied_shapes", {})[BACK_CASE] = s.tbm().copy(current)
    current = next(b for b in s.proxies(design.rootComponent) if b.name == BACK_CASE)
    wanted = STATE["shapes"][BACK_CASE]
    if stats(current) != stats(wanted):
        difference = op(current, wanted, "cut").volume + op(wanted, current, "cut").volume
        if difference > 1e-7:
            raise RuntimeError("Downstream clearance does not match its reviewed geometry")
        STATE["shapes"][BACK_CASE] = s.tbm().copy(current)
    (OUT / "v8_downstream_back_clearance.json").write_text(json.dumps(
        {"preserved_upstream_features": True, "cuts": names, "result": stats(current)}, indent=2))


def add_hardware(app, name, sibling):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    by = {b.name: b for b in s.proxies(root)}
    if name in by:
        raise RuntimeError("Hardware already exists: " + name)
    occ = m.add_body(by[sibling], STATE["shapes"][name], name, name)
    feat = occ.component.features.baseFeatures.item(0)
    feat.startEdit()
    try:
        feat.bodies.item(0).name = name
    finally:
        feat.finishEdit()
    by = {b.name: b for b in s.proxies(root)}
    STATE["paths"][name] = by[name].assemblyContext.fullPathName


def export_meshes(app):
    if not STATE.get("applied"):
        raise RuntimeError("Apply the reviewed revision before exporting")
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    parts = {
        "P01": ("PRINT_motor_mount", "P01_Back_case"),
        "P02": ("PRINT_REAR_MOTOR_SERVO_SPACER", "P02_Motor_servo_plate"),
        "P03": (CASE, "P03_Front_case"),
        "P04R": ("PRINT_carrier_box_left", "P04R_Swing_arm_rear_half"),
        "P04F": (FRONT_ARM, "P04F_Swing_arm_front_half"),
        "P05": (CAM, "P05_Servo_cam"),
        "P06": ("PRINT_compound_left", "P06_Left_compound_38T_14T"),
        "P07": ("PRINT_compound_right", "P07_Right_compound_38T_14T"),
    }
    folder = OUT / "stl_v8_assembly"
    folder.mkdir(parents=True, exist_ok=True)
    states = [(o, o.isLightBulbOn) for o in root.allOccurrences]
    bodies = [(b, b.isLightBulbOn) for b in by.values()]
    report = {}
    try:
        for occ, _ in states:
            occ.isLightBulbOn = True
        for key, (name, filename) in parts.items():
            body = by[name]
            body.isLightBulbOn = True
            path = folder / (filename + ".stl")
            options = design.exportManager.createSTLExportOptions(body, str(path))
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            options.isBinaryFormat = True
            if not design.exportManager.execute(options) or not path.exists() or path.stat().st_size <= 84:
                raise RuntimeError("STL export missing: " + key)
            report[key] = {"path": str(path), "native": stats(body),
                           "build_direction": [0, 1, 0] if key in ("P01", "P05", "P06", "P07") else [0, -1, 0]}
            (OUT / "v8_mesh_export.json").write_text(json.dumps(report, indent=2))
    finally:
        for body, light in bodies:
            if body.isValid:
                body.isLightBulbOn = light
        for occ, light in states:
            if occ.isValid:
                occ.isLightBulbOn = light
    return report
