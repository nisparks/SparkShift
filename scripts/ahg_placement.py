"""LDO-36STH20-1004AHG(XH) visual model (LDO drawing, 11/30/20) placed in the original SparkShift.

Published F3D world frame, mm: +Y toward the tool, +Z up. Motor axis along +Y, flange face at `face`.
Drawing: 36.5 mm body, 20 mm max depth, 3 mm eared flange (43.84 mm ear pitch, 51 mm span, 2-M3),
16 mm x 1.5 mm pilot, 10T m0.5 pinion (6 mm OD, 4 mm long) 2..6 mm in front of the face,
27 mm end-cap screw pitch, radial XH2.54 lead exit.
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "ahg_placement"
R_BODY, R_EAR, D_EAR = 18.25, (51.0 - 43.84) / 2, 43.84 / 2
FIXED_COMPOUND = (-9.5, 13.1)
MOVING_COMPOUND = (9.5, 13.1)
REDESIGN = ("PRINT_motor_mount", "PRINT_REAR_MOTOR_SERVO_SPACER", "PRINT_carrier_box_left",
            "STOCK_013_4mm_axle_1", "STOCK_048_4mm_axle_1_1", "STOCK_011_4mm_flange_bearing_1",
            "STOCK_061_4mm_flange_bearing_3", "STOCK_046_4mm_flange_bearing_1_1")
MOTOR_GROUP = ("MOTOR_14HS13_case", "MOTOR_factory_shaft", "PINION_motor_20T_m0p5", "M3x3_motor_grub",
               "M3x6_motor_0", "M3x6_motor_1", "M3x6_motor_2", "M3x6_motor_3")
PALETTE = {"alu": (198, 202, 208), "stack": (92, 98, 108), "pinion": (230, 232, 236), "lead": (24, 24, 26),
           "red": (220, 40, 40), "green": (40, 170, 70), "yellow": (235, 200, 40), "blue": (50, 90, 220),
           "collision": (255, 0, 255)}
STATE = {}


def study():
    module = sys.modules.get("pancake_paths_study")
    if module is None:
        spec = importlib.util.spec_from_file_location("pancake_paths_study", BASE / "pancake_paths_study.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["pancake_paths_study"] = module
    return module


def obb(cx, cy, cz, length_dir, length, width, height):
    """Box: `length` along length_dir (in XZ), `width` along Y, `height` along the XZ perpendicular."""
    s = study()
    return s.tbm().createBox(adsk.core.OrientedBoundingBox3D.create(
        s.P(cx, cy, cz), adsk.core.Vector3D.create(length_dir[0], 0, length_dir[1]),
        adsk.core.Vector3D.create(0, 1, 0), length / 10, width / 10, height / 10))


def rod(p0, p1, r):
    s = study()
    return s.tbm().createCylinderOrCone(s.P(*p0), r / 10, s.P(*p1), r / 10)


def flange(ax, az, y0, y1, theta, c=0.0):
    """Body circle plus two ears joined by external tangents (the drawing's lozenge outline)."""
    s = study()
    R, r = R_BODY + c, R_EAR + c
    t = math.radians(theta)
    beta = math.acos((R - r) / D_EAR)
    shape = s.cyl(ax, az, y0, y1, R)
    for sign in (1, -1):
        u = (sign * math.sin(t), sign * math.cos(t))
        v = (-u[1], u[0])

        def world(a, b):
            return ax + a * u[0] + b * v[0], az + a * u[1] + b * v[1]
        u0, u1 = R * math.cos(beta), D_EAR + r * math.cos(beta)
        ex, ez = world(D_EAR, 0)
        s.op(shape, s.cyl(ex, ez, y0, y1, r), "join")
        cx, cz = world((u0 + u1) / 2, 0)
        quad = obb(cx, (y0 + y1) / 2, cz, u, u1 - u0, y1 - y0, 2 * R * math.sin(beta))
        for side in (1, -1):
            a = (u0, side * R * math.sin(beta))
            b = (u1, side * r * math.sin(beta))
            du, dv = b[0] - a[0], b[1] - a[1]
            length = math.hypot(du, dv)
            du, dv = du / length, dv / length
            nu, nv = -dv * side, du * side
            if nv * side < 0:
                nu, nv = -nu, -nv
            mid = ((a[0] + b[0]) / 2 + nu * 25, (a[1] + b[1]) / 2 + nv * 25)
            mx, mz = world(*mid)
            direction = (du * u[0] + dv * v[0], du * u[1] + dv * v[1])
            s.op(quad, obb(mx, (y0 + y1) / 2, mz, direction, 80, y1 - y0 + 2, 50), "cut")
        s.op(shape, quad, "join")
    return shape


def ahg(ax, az, face, theta, lead_sign=-1):
    """Visual parts as (shape, name, colour); ears clocked `theta` degrees from +Z toward +X."""
    s = study()
    t = math.radians(theta)
    ear = (math.sin(t), math.cos(t))
    lead = (-ear[1] * lead_sign, ear[0] * lead_sign)
    parts = []
    plate = flange(ax, az, face - 3, face, theta)
    for sign in (1, -1):
        s.op(plate, s.cyl(ax + sign * D_EAR * ear[0], az + sign * D_EAR * ear[1], face - 3.1, face + .1, 1.5), "cut")
        s.op(plate, s.cyl(ax + sign * 13.5 * ear[0], az + sign * 13.5 * ear[1], face - .4, face + .1, 2.4), "cut")
    s.op(plate, s.cyl(ax, az, face, face + 1.5, 8.0), "join")
    parts.append((plate, "AHG front flange, ears and 16mm pilot", "alu"))
    stack = s.cyl(ax, az, face - 16.2, face - 3, R_BODY)
    for k in range(10):
        y = face - 4.1 - k * 1.2
        groove = s.cyl(ax, az, y - .15, y + .15, R_BODY + .1)
        s.op(groove, s.cyl(ax, az, y - .2, y + .2, R_BODY - .25), "cut")
        s.op(stack, groove, "cut")
    parts.append((stack, "AHG laminated stator", "stack"))
    rear = s.cyl(ax, az, face - 20, face - 16.2, R_BODY - .15)
    s.op(rear, s.cyl(ax, az, face - 20.1, face - 19.7, 12.5), "cut")
    parts.append((rear, "AHG rear end cap", "alu"))
    pinion = s.cyl(ax, az, face + 1.5, face + 6, 1.25)
    s.op(pinion, s.cyl(ax, az, face + 2, face + 6, 1.95), "join")
    for k in range(10):
        a = 2 * math.pi * k / 10
        d = (math.cos(a), math.sin(a))
        s.op(pinion, obb(ax + 2.45 * d[0], face + 4, az + 2.45 * d[1], d, 1.15, 4, .78), "join")
    parts.append((pinion, "AHG factory 10T m0.5 pinion", "pinion"))
    bx, bz = ax + (R_BODY + 1.4) * lead[0], az + (R_BODY + 1.4) * lead[1]
    parts.append((obb(bx, face - 17.5, bz, lead, 3.4, 5.5, 8.5), "AHG lead exit (XH2.54-4P)", "lead"))
    perp = (-lead[1], lead[0])
    for i, colour in enumerate(("red", "green", "yellow", "blue")):
        offset = (i - 1.5) * 1.6
        x0, z0 = bx + perp[0] * offset, bz + perp[1] * offset
        parts.append((rod((x0, face - 17.5, z0), (x0 + lead[0] * 11, face - 17.5, z0 + lead[1] * 11), .55),
                      "AHG lead " + colour, colour))
    return parts


def envelope(ax, az, face, theta, c=0.0):
    s = study()
    shape = flange(ax, az, face - 3 - c, face + c, theta, c)
    s.op(shape, s.cyl(ax, az, face - 20 - c, face - 3, R_BODY + c), "join")
    s.op(shape, s.cyl(ax, az, face, face + 1.5 + c, 8 + c), "join")
    return shape


def axis(phi):
    return (FIXED_COMPOUND[0] + 12.1 * math.cos(math.radians(phi)),
            FIXED_COMPOUND[1] + 12.1 * math.sin(math.radians(phi)))


def colour(design, key):
    name = "AHG colour " + key
    found = design.appearances.itemByName(name)
    if not found:
        base = design.appearances.itemByName("SparkShift arm")
        found = design.appearances.addByCopy(base, name)
        prop = adsk.core.ColorProperty.cast(found.appearanceProperties.itemById("opaque_albedo"))
        prop.value = adsk.core.Color.create(*PALETTE[key], 255)
    return found


def build(app, phi=-47.0, face=4.3):
    s = study()
    if not app.activeDocument.name.startswith("SparkShift original + AHG"):
        raise RuntimeError("Run in the fresh AHG placement copy of the original")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    bodies = s.proxies(root)
    ax, az = axis(phi)
    gap = math.hypot(ax - MOVING_COMPOUND[0], az - MOVING_COMPOUND[1]) - 3.0 - 10.0
    options = []
    for theta in range(-90, 91, 15):
        hits = s.interference(envelope(ax, az, face, theta), bodies, set(MOTOR_GROUP))
        other = sum(volume for name, volume, _ in hits if name not in REDESIGN)
        ear_out = max(abs(ax + sign * D_EAR * math.sin(math.radians(theta))) + R_EAR for sign in (1, -1)) - 22.5
        options.append((round(other, 2), round(max(ear_out, 0), 2), theta, hits))
    options.sort(key=lambda row: (row[0], row[1]))
    other, ear_out, theta, hits = options[0]
    shape = envelope(ax, az, face, theta)
    rows, hit_names = [], set()
    for name, volume, inter in hits:
        rows.append([name, volume, name in REDESIGN])
        hit_names.add(name)
    motor = ahg(ax, az, face, theta)
    STATE.update(ax=ax, az=az, face=face, theta=theta, hit_names=hit_names)
    # Groups: the motor, and remaining/overlap/free display bodies for clean views.
    originals = [b for b in bodies if b.name not in MOTOR_GROUP]
    rest, overlap = [], []
    for body in originals:
        if body.name in hit_names:
            remaining = s.tbm().copy(body)
            s.op(remaining, s.tbm().copy(shape), "cut")
            if remaining.lumps.count:
                rest.append((remaining, body.name, body.appearance))
            _, inter = s.common_volume(s.tbm().copy(body), shape)
            overlap.append((inter, "CLASH " + body.name, None))
    free = s.tbm().copy(shape)
    for body in originals:
        if body.name in hit_names:
            s.op(free, s.tbm().copy(body), "cut")
    groups = {}
    groups["motor"] = s.add_group(root, "LDO-36STH20-1004AHG(XH) visual model", [(p, n, None) for p, n, _ in motor])
    groups["rest"] = s.add_group(root, "VIEW original parts minus motor", rest)
    groups["clash"] = s.add_group(root, "VIEW clash volumes", overlap)
    whole = [(s.tbm().copy(b), b.name, b.appearance) for b in originals if b.name not in hit_names] + rest + overlap
    whole += [(free, "AHG free envelope", None)] + [(p, n, None) for p, n, k in motor if k in ("pinion", "lead", "red", "green", "yellow", "blue")]
    groups["section"] = s.add_group(root, "VIEW section through motor axis", section_at(whole, ax))
    STATE["groups"] = groups
    keys = {n: k for _, n, k in motor}
    for occ in groups.values():
        for body in occ.component.bRepBodies:
            if body.name in keys:
                body.appearance = colour(design, keys[body.name])
            elif body.name.startswith("CLASH"):
                body.appearance = colour(design, "collision")
            elif body.name == "AHG free envelope":
                body.appearance = colour(design, "alu")
    report = {
        "motor": "LDO-36STH20-1004AHG(XH), drawing 11/30/20",
        "axis_xz_mm": [ax, az], "phi_deg_from_fixed_compound": phi, "input_centre_mm": 12.1,
        "pinion_tip_gap_to_moving_38T_mm": round(gap, 2),
        "face_y_mm": face, "pinion_y_mm": [face + 2, face + 6], "original_38T_band_y_mm": [5.9, 10.7],
        "ear_clock_deg": theta, "ear_projection_beyond_45mm_mm": ear_out,
        "body_x_range_mm": [round(ax - R_BODY, 2), round(ax + R_BODY, 2)],
        "rear_y_mm": face - 20,
        "clashes_mm3": sorted(rows, key=lambda row: -row[1]),
        "clash_outside_redesign_set_mm3": other,
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "placement.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def section_at(items, cut_x):
    s = study()
    keep = []
    for shape, name, appearance in items:
        bb = shape.boundingBox
        if bb.minPoint.x * 10 >= cut_x:
            continue
        copy = s.tbm().copy(shape)
        if bb.maxPoint.x * 10 > cut_x:
            try:
                s.op(copy, s.box(cut_x, 200, -200, 200, -200, 200), "cut")
            except RuntimeError:
                continue
            if not copy.lumps.count:
                continue
        keep.append((copy, name, appearance))
    return keep


def capture(app):
    s = study()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    groups = STATE["groups"]
    group_names = {occ.component.name for occ in groups.values()}
    originals = [occ for occ in root.occurrences if occ.component.name not in group_names]
    view = app.activeViewport
    images = OUT / "images"
    images.mkdir(parents=True, exist_ok=True)
    hidden_housing = {"PRINT_motor_mount", "PRINT_REAR_MOTOR_SERVO_SPACER", "PRINT_000_outer_shell_of_extruder_1"}

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
        if not view.saveAsImageFile(str(images / name), 1800, 1400):
            raise RuntimeError("Image capture failed: " + name)

    def scene(show_originals, hide=(), show=()):
        for occ in originals:
            occ.isLightBulbOn = show_originals
        for body in s.proxies(root):
            context = body.assemblyContext
            if context and context.component.name not in group_names:
                context.isLightBulbOn = body.name not in hide
        for key, occ in groups.items():
            occ.isLightBulbOn = key in show

    ax, az, face = STATE["ax"], STATE["az"], STATE["face"]
    centre = (ax / 10, (face - 8) / 10, az / 10)
    scene(False, show=("motor",))
    shot("ahg_front.png", (centre[0] + 6, centre[1] + 9, centre[2] + 5), centre)
    shot("ahg_rear.png", (centre[0] - 6, centre[1] - 9, centre[2] + 4), centre)
    tool = {b.name for b in s.proxies(root) if b.assemblyContext and "12 Removable tool" in b.assemblyContext.fullPathName}
    hide = set(MOTOR_GROUP) | STATE["hit_names"] | hidden_housing | tool
    scene(True, hide=hide, show=("motor", "rest", "clash"))
    for body in groups["rest"].component.bRepBodies:
        body.isLightBulbOn = body.name not in hidden_housing
    shot("internals_rear.png", (-30, -38, 22), (0, 0, .5))
    shot("internals_rear_right.png", (30, -38, 18), (0, 0, .5))
    scene(False, show=("section",))
    shot("section.png", (40, centre[1], centre[2]), centre, 9.5)
    for body in groups["rest"].component.bRepBodies:
        body.isLightBulbOn = True
    scene(True, hide=set(MOTOR_GROUP) | STATE["hit_names"], show=("motor", "rest"))
    shot("assembled_rear.png", (-30, -38, 22))
    return sorted(path.name for path in images.iterdir())
