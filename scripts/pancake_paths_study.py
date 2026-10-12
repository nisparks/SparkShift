"""Original SparkShift with two pancake placements; study geometry only.

Coordinates are the published F3D world frame in mm: +Y toward the tool, +Z up.
"""

import json
import math
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "pancake_paths_study"
R_BODY, D_EAR, R_EAR = 18.25, 43.84 / 2, (51.0 - 43.84) / 2
CUT_X = -2.0
MOTOR_GROUP = ("MOTOR_14HS13_case", "MOTOR_factory_shaft", "M3x6_motor_0", "M3x6_motor_1",
               "M3x6_motor_2", "M3x6_motor_3")
PINION = ("PINION_motor_20T_m0p5", "M3x3_motor_grub")
P01, P02 = "PRINT_motor_mount", "PRINT_REAR_MOTOR_SERVO_SPACER"
STATE = {}


def tbm():
    return adsk.fusion.TemporaryBRepManager.get()


def P(x, y, z):
    return adsk.core.Point3D.create(x / 10, y / 10, z / 10)


def cyl(x, z, y0, y1, r):
    return tbm().createCylinderOrCone(P(x, y0, z), r / 10, P(x, y1, z), r / 10)


def box(x0, x1, y0, y1, z0, z1):
    return tbm().createBox(adsk.core.OrientedBoundingBox3D.create(
        P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
        adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
        (x1 - x0) / 10, (y1 - y0) / 10, (z1 - z0) / 10))


def op(a, b, kind):
    kinds = {"join": adsk.fusion.BooleanTypes.UnionBooleanType,
             "cut": adsk.fusion.BooleanTypes.DifferenceBooleanType,
             "common": adsk.fusion.BooleanTypes.IntersectionBooleanType}
    if not tbm().booleanOperation(a, b, kinds[kind]):
        raise RuntimeError("Boolean failed: " + kind)
    return a


def common_volume(a, b):
    ab, bb = a.boundingBox, b.boundingBox
    if any(getattr(ab.maxPoint, axis) <= getattr(bb.minPoint, axis) or
           getattr(bb.maxPoint, axis) <= getattr(ab.minPoint, axis) for axis in ("x", "y", "z")):
        return 0.0, None
    target = tbm().copy(a)
    if not tbm().booleanOperation(target, tbm().copy(b), adsk.fusion.BooleanTypes.IntersectionBooleanType):
        raise RuntimeError("Intersection calculation failed; overlap is unknown")
    volume = target.volume * 1000 if target.lumps.count else 0.0
    return volume, target


def pancake(ax, az, face, theta, c=0.0):
    """Drawing envelope: 20 mm body, 3 mm eared flange, 16 mm x 1.5 mm pilot."""
    t = math.radians(theta)
    ux, uz = math.sin(t), math.cos(t)
    solid = cyl(ax, az, face - 20 - c, face - 3, R_BODY + c)
    flange = cyl(ax, az, face - 3 - c, face + c, R_BODY + c)
    ears = [(ax + s * D_EAR * ux, az + s * D_EAR * uz) for s in (1, -1)]
    for ex, ez in ears:
        op(flange, cyl(ex, ez, face - 3 - c, face + c, R_EAR + c), "join")
    web = tbm().createBox(adsk.core.OrientedBoundingBox3D.create(
        P(ax, face - 1.5, az), adsk.core.Vector3D.create(ux, 0, uz), adsk.core.Vector3D.create(0, 1, 0),
        2 * D_EAR / 10, (3 + 2 * c) / 10, (2 * R_EAR + 2 * c) / 10))
    op(flange, web, "join")
    op(solid, flange, "join")
    op(solid, cyl(ax, az, face, face + 1.5 + c, 8 + c), "join")
    return solid, ears


def proxies(root):
    rows = []

    def walk(occs):
        for occ in occs:
            for body in occ.bRepBodies:
                rows.append(body)
            walk(occ.childOccurrences)
    walk(root.occurrences)
    return rows


def centre(body):
    box3 = body.boundingBox
    return ((box3.minPoint.x + box3.maxPoint.x) * 5, (box3.minPoint.z + box3.maxPoint.z) * 5)


def interference(solid, bodies, exclude):
    found = []
    for body in bodies:
        if body.name in exclude or not solid.boundingBox.intersects(body.boundingBox):
            continue
        volume, shape = common_volume(tbm().copy(body), solid)
        if volume > 0.05:
            found.append((body.name, round(volume, 2), shape))
    return found


def add_group(root, name, items):
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    feature = occ.component.features.baseFeatures.add()
    feature.startEdit()
    for shape, _, _ in items:
        occ.component.bRepBodies.add(shape, feature)
    feature.finishEdit()
    for body, (_, body_name, appearance) in zip(occ.component.bRepBodies, items):
        body.name = body_name
        if appearance:
            body.appearance = appearance
    return occ


def section(items):
    keep = []
    for shape, name, appearance in items:
        bb = shape.boundingBox
        if bb.minPoint.x * 10 >= CUT_X:
            continue
        copy = tbm().copy(shape)
        if bb.maxPoint.x * 10 > CUT_X:
            try:
                op(copy, box(CUT_X, 200, -200, 200, -200, 200), "cut")
            except RuntimeError:
                continue
            if not copy.lumps.count:
                continue
        keep.append((copy, name, appearance))
    return keep


def build(app):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    if not app.activeDocument.name.startswith("OWNED original SparkShift 7ca126e"):
        raise RuntimeError("Run only in the owned original study copy")
    bodies = proxies(root)
    by = {body.name: body for body in bodies}
    metal, red = by["MOTOR_14HS13_case"].appearance, by["PRINT_carrier_box_left"].appearance
    hardware = by["M3x6_motor_0"].appearance
    mx, mz = centre(by["MOTOR_factory_shaft"])
    cx, cz = centre(by["STOCK_013_4mm_axle_1"])
    distance = math.hypot(mx - cx, mz - cz)
    bx, bz = cx + (mx - cx) * 12.1 / distance, cz + (mz - cz) * 12.1 / distance
    p01_back = by[P01].boundingBox.minPoint.y * 10
    report = {"original_motor_axis_xz": [mx, mz], "original_input_centre_mm": distance,
              "fixed_compound_axis_xz": [cx, cz], "p01_rear_face_y": p01_back,
              "original_motor_rear_y": by["MOTOR_14HS13_case"].boundingBox.minPoint.y * 10}

    # A: plain 5 mm shaft, original 20T pinion unchanged, face against P01's rear face.
    face_a = p01_back
    excluded_a = set(MOTOR_GROUP + PINION + (P01, P02))
    trials = []
    for theta in (30, -30, 20, -20, 40, -40, 50, -50, 0, 90):
        cutter, _ = pancake(mx, mz, face_a, theta, .3)
        hits = interference(cutter, bodies, excluded_a)
        trials.append({"theta": theta, "hits": [[name, volume] for name, volume, _ in hits]})
        if not hits:
            theta_a = theta
            break
    else:
        raise RuntimeError("No tested ear clocking clears plain-shaft placement A")
    motor_a, ears_a = pancake(mx, mz, face_a, theta_a)
    shaft_a = cyl(mx, mz, face_a + 1.5, face_a + 19.0, 2.5)
    cutter_a, _ = pancake(mx, mz, face_a, theta_a, .3)
    p02a = tbm().copy(by[P02])
    op(p02a, box(-22.5, 22.5, -13.7, -8.0, by[P02].boundingBox.minPoint.z * 10, 20.5), "join")
    op(p02a, cutter_a, "cut")
    screws = []
    for ex, ez in ears_a:
        op(p02a, cyl(ex, ez, -14.0, face_a, 1.7), "cut")
        screw = cyl(ex, ez, -16.7, -13.7, 2.75)
        op(screw, cyl(ex, ez, -13.7, -8.7, 1.5), "join")
        screws.append(screw)
    p01a = tbm().copy(by[P01])
    p01_pilot_cut = cyl(mx, mz, face_a - .1, face_a + 1.8, 8.4)
    p01_removed, _ = common_volume(tbm().copy(by[P01]), p01_pilot_cut)
    op(p01a, p01_pilot_cut, "cut")
    check_a = [[name, volume] for name, volume, _ in interference(
        motor_a, [body for body in bodies if body.name not in excluded_a], set())]
    for shape, name in ((p02a, "P02A"), (p01a, "P01A")):
        volume, _ = common_volume(shape, motor_a)
        check_a.append([name, round(volume, 3)])
    report["A_plain_shaft"] = {
        "motor": "LDO-36STH20-1004AH class: 36.5 mm round, 20 mm body, plain 5 mm D shaft",
        "axis_xz": [mx, mz], "face_y": face_a, "ear_clock_deg": theta_a, "ear_axes_xz": ears_a,
        "shaft_projection_assumed_mm": 19.0,
        "original_pinion_y": [by["PINION_motor_20T_m0p5"].boundingBox.minPoint.y * 10,
                              by["PINION_motor_20T_m0p5"].boundingBox.maxPoint.y * 10],
        "rear_y": face_a - 20, "ear_trials": trials,
        "p01_pilot_recess_removed_mm3": round(p01_removed, 2),
        "post_change_interference_mm3": check_a,
    }

    # B: factory 10T integral pinion, centre distance 12.1 mm, pinion centred in the original 38T band.
    face_b = 8.3 - 4.0
    excluded_b = set(MOTOR_GROUP + PINION)
    options = []
    for theta in (45, -45, 30, -30, 60, -60, 0, 90):
        envelope, _ = pancake(bx, bz, face_b, theta)
        hits = interference(envelope, bodies, excluded_b)
        other = sum(volume for name, volume, _ in hits if name not in (P01, P02))
        options.append((other, theta, hits))
    options.sort(key=lambda row: row[0])
    other_b, theta_b, hits_b = options[0]
    motor_b, ears_b = pancake(bx, bz, face_b, theta_b)
    pinion_b = cyl(bx, bz, face_b + 1.5, face_b + 2.0, 1.5)
    op(pinion_b, cyl(bx, bz, face_b + 2.0, face_b + 6.0, 3.0), "join")
    report["B_factory_10T"] = {
        "motor": "LDO-36STH20-1004AHG(XH): factory 10T pinion 2..6 mm in front of face",
        "axis_xz": [bx, bz], "face_y": face_b, "pinion_y": [face_b + 2, face_b + 6],
        "ear_clock_deg": theta_b, "rear_y": face_b - 20,
        "collisions_mm3": [[name, volume] for name, volume, _ in hits_b],
        "non_housing_collision_mm3": round(other_b, 2),
    }

    # Native study groups.
    original_items = [(tbm().copy(body), body.name, body.appearance) for body in bodies]
    a_items = [(motor_a, "PANCAKE A plain-shaft envelope", metal), (shaft_a, "PANCAKE A 5mm shaft", metal),
               (p02a, "P02A pancake spacer", by[P02].appearance), (p01a, "P01A with pilot recess", by[P01].appearance)]
    a_items += [(screw, "M3 ear screw %d" % i, hardware) for i, screw in enumerate(screws)]
    b_items = [(motor_b, "PANCAKE B factory-10T envelope", metal), (pinion_b, "PANCAKE B 10T pinion", metal)]
    b_items += [(shape, "COLLISION " + name, red) for name, _, shape in hits_b]
    groups = {
        "A": add_group(root, "STUDY A - plain-shaft pancake, original 20T", a_items),
        "B": add_group(root, "STUDY B - factory 10T pancake collisions", b_items),
        "S0": add_group(root, "SECTION 0 - original", section(original_items)),
        "SA": add_group(root, "SECTION A - plain-shaft pancake", section(
            [row for row in original_items if row[1] not in excluded_a or row[1] in PINION] + a_items)),
        "SB": add_group(root, "SECTION B - factory 10T pancake", section(
            [row for row in original_items if row[1] not in excluded_b] + b_items)),
    }
    STATE.update(groups=groups, hide_a=set(MOTOR_GROUP + (P01, P02)), hide_b=set(MOTOR_GROUP + PINION))
    OUT.mkdir(exist_ok=True)
    (OUT / "study.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


COLOURS = {"P01": (51, 116, 214), "P02": (159, 87, 214), "P03": (238, 170, 71), "P04": (255, 54, 76),
           "P05": (255, 130, 35), "P06": (255, 191, 48), "P07": (255, 191, 48), "P08": (248, 223, 124),
           "P09": (248, 223, 124), "P12": (228, 237, 171), "P13": (227, 86, 160), "P14": (227, 86, 160),
           "P15": (96, 207, 235), "P16": (96, 207, 235), "P17": (28, 200, 143), "P18": (174, 213, 72),
           "collision": (255, 0, 255), "motor": (150, 160, 172)}


def refine(app):
    """Show B as remaining structure, magenta overlap and the free motor envelope; apply the poster key."""
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    report = json.loads((OUT / "study.json").read_text())["B_factory_10T"]
    (bx, bz), face_b, theta_b = report["axis_xz"], report["face_y"], report["ear_clock_deg"]
    envelope, _ = pancake(bx, bz, face_b, theta_b)
    pinion = cyl(bx, bz, face_b + 1.5, face_b + 2.0, 1.5)
    op(pinion, cyl(bx, bz, face_b + 2.0, face_b + 6.0, 3.0), "join")
    for key in ("B", "SB"):
        STATE["groups"][key].deleteMe()
    originals = [body for body in proxies(root) if body.assemblyContext and not
                 body.assemblyContext.component.name.startswith(("STUDY", "SECTION"))]
    whole, overlap, hit_names = [], [], []
    for body in originals:
        if body.name in MOTOR_GROUP + PINION:
            continue
        copy = tbm().copy(body)
        if envelope.boundingBox.intersects(body.boundingBox):
            volume, inter = common_volume(copy, envelope)
            if volume > .05:
                rest = tbm().copy(body)
                op(rest, tbm().copy(envelope), "cut")
                if rest.lumps.count:
                    whole.append((rest, body.name, body.appearance))
                overlap.append((inter, "COLLISION " + body.name, None))
                hit_names.append(body.name)
                continue
        whole.append((copy, body.name, body.appearance))
    free = tbm().copy(envelope)
    for body in originals:
        if body.name in hit_names:
            op(free, tbm().copy(body), "cut")
    motor_full = (tbm().copy(envelope), "PANCAKE B factory-10T envelope", None)
    pinion_row = (pinion, "PANCAKE B 10T pinion", None)
    rest_rows = [row for row in whole if row[1] in hit_names]
    STATE["groups"]["B"] = add_group(root, "STUDY B - factory 10T pancake in cut original", rest_rows + [motor_full, pinion_row])
    STATE["groups"]["SB"] = add_group(root, "SECTION B - factory 10T overlap", section(
        whole + overlap + [(free, "PANCAKE B free envelope", None), pinion_row]))
    STATE["hide_b"] = set(MOTOR_GROUP + PINION) | set(hit_names)

    base = design.appearances.itemByName("SparkShift arm")

    def colour(key):
        name = "STUDY colour " + key
        found = design.appearances.itemByName(name)
        if not found:
            found = design.appearances.addByCopy(base, name)
            prop = adsk.core.ColorProperty.cast(found.appearanceProperties.itemById("opaque_albedo"))
            prop.value = adsk.core.Color.create(*COLOURS[key], 255)
        return found
    ids = {"P02A pancake spacer": "P02", "P01A with pilot recess": "P01"}
    for body in originals:
        prefix = body.assemblyContext.name[:3]
        if prefix in COLOURS:
            ids[body.name] = prefix
    painted = 0
    for body in proxies(root):
        key = ids.get(body.name)
        if body.name.startswith("COLLISION"):
            key = "collision"
        elif body.name.startswith(("PANCAKE", "MOTOR_14HS13")):
            key = "motor"
        if key:
            body.appearance = colour(key)
            painted += 1
    return {"collided": hit_names, "painted": painted}


def fix_a(app, theta=-40.0):
    """Rebuild placement A so both factory ears are clamped by P02 material."""
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    for key in ("A", "SA"):
        STATE["groups"][key].deleteMe()
    originals = [body for body in proxies(root) if body.assemblyContext and not
                 body.assemblyContext.component.name.startswith(("STUDY", "SECTION"))]
    by = {body.name: body for body in originals}
    mx, mz = centre(by["MOTOR_factory_shaft"])
    face = by[P01].boundingBox.minPoint.y * 10
    bottom = by[P02].boundingBox.minPoint.z * 10
    excluded = set(MOTOR_GROUP + PINION + (P01, P02))
    motor, ears = pancake(mx, mz, face, theta)
    cutter, _ = pancake(mx, mz, face, theta, .3)
    p02a = tbm().copy(by[P02])
    op(p02a, box(-22.5, 22.5, -13.7, -8.0, bottom, 20.5), "join")
    tabs = []
    for ex, ez in ears:
        if ez - R_EAR - 1.5 < bottom:
            tab = box(ex - R_EAR - 1.5, ex + R_EAR + 1.5, -13.7, -8.0, ez - R_EAR - 1.5, bottom + 1.0)
            tabs.append(tbm().copy(tab))
            op(p02a, tab, "join")
    op(p02a, cutter, "cut")
    screws = []
    for ex, ez in ears:
        op(p02a, cyl(ex, ez, -14.0, face, 1.7), "cut")
        screw = cyl(ex, ez, -16.7, -13.7, 2.75)
        op(screw, cyl(ex, ez, -13.7, -8.7, 1.5), "join")
        screws.append(screw)
    p01a = tbm().copy(by[P01])
    op(p01a, cyl(mx, mz, face - .1, face + 1.8, 8.4), "cut")
    check = {}
    for label, shape in [("motor", cutter)] + [("tab%d" % i, tab) for i, tab in enumerate(tabs)] + \
            [("screw%d" % i, screw) for i, screw in enumerate(screws)]:
        check[label] = [[name, volume] for name, volume, _ in interference(shape, originals, excluded)]
    for shape, label in ((p02a, "P02A"), (p01a, "P01A")):
        volume, _ = common_volume(shape, motor)
        check[label] = round(volume, 3)
    shaft = cyl(mx, mz, face + 1.5, face + 19.0, 2.5)
    hardware = by["M3x6_motor_0"].appearance
    a_items = [(motor, "PANCAKE A plain-shaft envelope", None), (shaft, "PANCAKE A 5mm shaft", None),
               (p02a, "P02A pancake spacer", None), (p01a, "P01A with pilot recess", None)]
    a_items += [(screw, "M3 ear screw %d" % i, hardware) for i, screw in enumerate(screws)]
    original_items = [(tbm().copy(body), body.name, body.appearance) for body in originals
                      if body.name not in excluded or body.name in PINION]
    STATE["groups"]["A"] = add_group(root, "STUDY A - plain-shaft pancake, original 20T", a_items)
    STATE["groups"]["SA"] = add_group(root, "SECTION A - plain-shaft pancake", section(original_items + a_items))
    report = json.loads((OUT / "study.json").read_text())
    report["A_plain_shaft"].update(
        ear_clock_deg=theta, ear_axes_xz=ears, p02_lower_ear_tabs=len(tabs),
        post_change_interference_mm3=check,
        note="Both threaded ears are backed by P02; rear-entry M3x5 screws.")
    (OUT / "study.json").write_text(json.dumps(report, indent=2) + "\n")
    return check


def paint(app):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    base = design.appearances.itemByName("SparkShift arm")
    extra = {"gear": (255, 191, 48), "servo": (107, 129, 153), "hardware": (204, 221, 236)}

    def colour(key):
        name = "STUDY colour " + key
        found = design.appearances.itemByName(name)
        if not found:
            found = design.appearances.addByCopy(base, name)
            prop = adsk.core.ColorProperty.cast(found.appearanceProperties.itemById("opaque_albedo"))
            prop.value = adsk.core.Color.create(*(COLOURS.get(key) or extra[key]), 255)
        return found
    ids = {"P02A pancake spacer": "P02", "P01A with pilot recess": "P01"}
    for body in proxies(root):
        context = body.assemblyContext
        if context and context.name[:3] in COLOURS and not context.component.name.startswith(("STUDY", "SECTION")):
            ids[body.name] = context.name[:3]
    for body in proxies(root):
        name = body.name
        if name in ids:
            key = ids[name]
        elif name.startswith("COLLISION"):
            key = "collision"
        elif name.startswith(("PINION", "PANCAKE B 10T pinion")):
            key = "gear"
        elif name.startswith(("PANCAKE", "MOTOR_14HS13")):
            key = "motor"
        elif name == "HOBBY_SERVO_ENVELOPE":
            key = "servo"
        else:
            key = "hardware"
        body.appearance = colour(key)


def capture(app):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    groups = STATE["groups"]
    originals = [occ for occ in root.occurrences if not occ.component.name.startswith(("STUDY", "SECTION"))]
    bodies = proxies(adsk.fusion.Design.cast(app.activeProduct).rootComponent)
    view = app.activeViewport

    def shot(name, eye, target=(0, 0, 0), extents=None):
        camera = view.camera
        camera.isSmoothTransition = False
        camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        camera.isFitView = extents is None
        camera.target = adsk.core.Point3D.create(*target)
        camera.eye = adsk.core.Point3D.create(*eye)
        camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
        if extents:
            camera.viewExtents = extents
        view.camera = camera
        adsk.doEvents()
        view.refresh()
        if not view.saveAsImageFile(str(OUT / name), 1800, 1400):
            raise RuntimeError("Image capture failed: " + name)

    def scene(original=True, hidden=(), show=()):
        for occ in originals:
            occ.isLightBulbOn = original
        for body in bodies:
            if body.assemblyContext and body.assemblyContext.component.name not in [
                    occ.component.name for occ in groups.values()]:
                body.assemblyContext.isLightBulbOn = body.name not in hidden
        for key, occ in groups.items():
            occ.isLightBulbOn = key in show

    iso, side = (-30, -38, 22), (40, -1.2, .2)
    zoom = dict(target=(0, -1.2, .2), extents=9.5)
    scene()
    shot("0_original_iso.png", iso)
    scene(hidden=STATE["hide_a"], show=("A",))
    shot("A_plain_shaft_iso.png", iso)
    scene(hidden=STATE["hide_b"], show=("B",))
    shot("B_factory10T_iso.png", iso)
    for key, name in (("S0", "0_original_section.png"), ("SA", "A_plain_shaft_section.png"),
                      ("SB", "B_factory10T_section.png")):
        scene(original=False, show=(key,))
        shot(name, side, **zoom)
    scene()
    archive = OUT / "pancake_paths_study.f3d"
    design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
    return sorted(path.name for path in OUT.iterdir())
