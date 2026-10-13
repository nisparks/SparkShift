"""SparkShift AHG-min: the published original with only the parts the LDO 10T pancake forces changed.

Macro concept geometry (not qualified). Published F3D world frame, mm: +Y toward the tool, +Z up.
Changes: AHG motor in P01, flat pin plate on the motor face, fixed compound on a stationary pin with
two internal MR74ZZ, moving compound keeps its rotating axle (rear MR74 in the pin plate), swing arm's
lower rear plate replaced by a 6700ZZ hinge ring on the moving compound hub. P03, cam/servo, hotend,
tool, belts and carriage are untouched.
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "sparkshift_ahg_min"
PHI, FACE, THETA = -47.0, 4.3, -45.0
PLATE_Y = (4.3, 6.3)
GEAR_REAR_Y = 6.6
ARM_RING_Y = (11.0, 15.0)
OPEN_DEG = -6.899
STATE = {}


def load(name):
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
    return module


def replace(proxy, temp, body_name=None, component_name=None):
    s = load("pancake_paths_study")
    native = proxy.nativeObject or proxy
    component = native.parentComponent
    geometry = s.tbm().copy(temp)
    if proxy.assemblyContext:
        inverse = proxy.assemblyContext.transform2.copy()
        inverse.invert()
        s.tbm().transform(geometry, inverse)
    feature = component.features.baseFeatures.item(0)
    feature.startEdit()
    try:
        source = next(feature.bodies.item(i) for i in range(feature.bodies.count)
                      if feature.bodies.item(i).name == native.name)
        if not feature.updateBody(source, geometry):
            raise RuntimeError("Could not update " + native.name)
        if body_name and source.isValid:
            source.name = body_name          # stored in the base feature, survives recompute
    finally:
        feature.finishEdit()
    single = component.bRepBodies.count == 1
    if body_name:
        if native.isValid:
            native.name = body_name
        elif single:
            component.bRepBodies.item(0).name = body_name
    if component_name and single:
        component.name = component_name


def ring(cx, cz, y0, y1, r_out, r_in):
    s = load("pancake_paths_study")
    shape = s.cyl(cx, cz, y0, y1, r_out)
    s.op(shape, s.cyl(cx, cz, y0 - .1, y1 + .1, r_in), "cut")
    return shape


def rotated(shape, centre, degrees):
    s = load("pancake_paths_study")
    copy = s.tbm().copy(shape)
    matrix = adsk.core.Matrix3D.create()
    matrix.setToRotation(math.radians(degrees), adsk.core.Vector3D.create(0, 1, 0),
                         adsk.core.Point3D.create(centre[0] / 10, 0, centre[1] / 10))
    s.tbm().transform(copy, matrix)
    return copy


def plate_shape(M, F, Mv, ears):
    """Flat printed plate on the motor face: rear bearings for both rotating compound axles.

    The fixed-compound seat sits 12.1 mm from the motor axis, so it opens into the pilot clearance
    (a C-seat); every major mesh separating force pushes that axle away from the opening.
    """
    s, a = load("pancake_paths_study"), load("ahg_placement")
    plate = a.flange(M[0], M[1], PLATE_Y[0], PLATE_Y[1], THETA)
    y0, y1 = PLATE_Y[0] - .1, PLATE_Y[1] + .1
    s.op(plate, s.cyl(M[0], M[1], y0, y1, 8.25), "cut")
    s.op(plate, s.cyl(F[0], F[1], y0, y1, 3.5), "cut")
    dx, dz = M[0] - F[0], M[1] - F[1]
    length = math.hypot(dx, dz)
    s.op(plate, load("ahg_placement").obb(F[0] + dx / length * 3.0, (y0 + y1) / 2, F[1] + dz / length * 3.0,
                                          (dx / length, dz / length), 6.0, y1 - y0, 3.0), "cut")
    s.op(plate, s.cyl(Mv[0], Mv[1], y0, y1, 3.5), "cut")
    for ex, ez in ears:
        s.op(plate, s.cyl(ex, ez, y0, y1, 1.7), "cut")
    return plate


def arm_ring_solids(Mv, H):
    """6700ZZ hinge ring around the moving compound hub plus webs to the hob boss and upper arm."""
    s = load("pancake_paths_study")
    y0, y1 = ARM_RING_Y
    solid = s.cyl(Mv[0], Mv[1], y0, y1, 9.5)
    dx, dz = H[0] - Mv[0], H[1] - Mv[1]
    length = math.hypot(dx, dz)
    direction = (dx / length, dz / length)
    web = load("ahg_placement").obb((Mv[0] + H[0]) / 2, (y0 + y1) / 2, (Mv[1] + H[1]) / 2, direction,
                                    length, y1 - y0, 9.0)
    s.op(solid, web, "join")
    s.op(solid, s.box(Mv[0] - 5.5, Mv[0] + 5.5, y0, y1, Mv[1], 26.0), "join")
    s.op(solid, s.cyl(H[0], H[1], y0, y1, 5.6), "join")
    return solid


def build(app):
    s, a = load("pancake_paths_study"), load("ahg_placement")
    if not app.activeDocument.name.startswith("SparkShift AHG-min"):
        raise RuntimeError("Run in the fresh AHG-min copy of the original")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    bodies = s.proxies(root)
    by = {body.name: body for body in bodies}
    F = s.centre(by["STOCK_013_4mm_axle_1"])
    Mv = s.centre(by["STOCK_048_4mm_axle_1_1"])
    H = s.centre(by["SHAFT_hob_left"])
    M = (F[0] + 12.1 * math.cos(math.radians(PHI)), F[1] + 12.1 * math.sin(math.radians(PHI)))
    t = math.radians(THETA)
    ears = [(M[0] + sign * a.D_EAR * math.sin(t), M[1] + sign * a.D_EAR * math.cos(t)) for sign in (1, -1)]
    motor_env = a.envelope(M[0], M[1], FACE, THETA)
    motor_cut = a.envelope(M[0], M[1], FACE, THETA, .3)
    plate = plate_shape(M, F, Mv, ears)
    plate_pocket = a.flange(M[0], M[1], PLATE_Y[0] - .05, PLATE_Y[1] + .1, THETA, .2)
    ring_solids = arm_ring_solids(Mv, H)

    # Swing arm: drop the lower rear plate, add the hinge ring, keep the follower/upper/front arm.
    arm = s.tbm().copy(by["PRINT_carrier_box_left"])
    s.op(arm, s.box(-7, 22, -6, GEAR_REAR_Y, -13, 24.5), "cut")
    s.op(arm, a.envelope(M[0], M[1], FACE, THETA, 1.0), "cut")
    s.op(arm, ring_solids, "join")
    for shape in (s.cyl(Mv[0], Mv[1], ARM_RING_Y[0] - .1, ARM_RING_Y[1] + .1, 7.5),
                  s.cyl(H[0], H[1], 13.4, 16.2, 3.65),
                  s.cyl(H[0], H[1], ARM_RING_Y[0] - .1, 13.4, 1.8)):
        s.op(arm, shape, "cut")

    # Compounds keep the original rotating-axle architecture; 38T bands start at Y 6.6 to clear the plate.
    fixed = s.tbm().copy(by["PRINT_compound_right"])
    s.op(fixed, s.cyl(F[0], F[1], 5.0, GEAR_REAR_Y, 11.0), "cut")
    moving = s.tbm().copy(by["PRINT_compound_left"])
    s.op(moving, s.cyl(Mv[0], Mv[1], 5.0, GEAR_REAR_Y, 11.0), "cut")
    s.op(moving, ring(Mv[0], Mv[1], 10.7, 16.1, 5.0, 2.0), "join")

    # Backplate: motor pocket, pin-plate pocket, pinion relief, arm-ring sweep, rear-entry ear screws.
    p01 = s.tbm().copy(by["PRINT_motor_mount"])
    s.op(p01, motor_cut, "cut")
    s.op(p01, plate_pocket, "cut")
    s.op(p01, s.cyl(M[0], M[1], 5.5, 10.8, 3.6), "cut")
    sweep = s.tbm().copy(ring_solids)
    for degrees in (-2.3, -4.6, OPEN_DEG):
        s.op(sweep, rotated(ring_solids, Mv, degrees), "join")
    sweep_clear = s.tbm().copy(sweep)
    for dx, dz in ((.5, 0), (-.5, 0), (0, .5), (0, -.5)):
        shifted = s.tbm().copy(sweep)
        move = adsk.core.Matrix3D.create()
        move.translation = adsk.core.Vector3D.create(dx / 10, 0, dz / 10)
        s.tbm().transform(shifted, move)
        s.op(sweep_clear, shifted, "join")
    s.op(sweep_clear, s.cyl(Mv[0], Mv[1], 10.6, 16.3, 5.4), "join")
    s.op(p01, sweep_clear, "cut")
    screws = []
    for ex, ez in ears:
        s.op(p01, s.cyl(ex, ez, -8.1, FACE, 1.7), "cut")
        s.op(p01, s.cyl(ex, ez, -8.1, -5.0, 3.0), "cut")
        screw = s.cyl(ex, ez, -8.0, -5.0, 2.75)
        s.op(screw, s.cyl(ex, ez, -5.0, 5.0, 1.5), "join")
        screws.append(screw)

    # Front clamshell: one internal relief for the arm hinge ring and the moving hub; exterior unchanged.
    p03 = s.tbm().copy(by["PRINT_000_outer_shell_of_extruder_1"])
    p03_before = p03.volume * 1000
    s.op(p03, sweep_clear, "cut")
    p03_removed = p03_before - p03.volume * 1000

    # Spacer: fill the old NEMA14 seat, pass the motor body, ear-screw access, lead-exit slot.
    p02 = s.tbm().copy(by["PRINT_REAR_MOTOR_SERVO_SPACER"])
    bottom = by["PRINT_REAR_MOTOR_SERVO_SPACER"].boundingBox.minPoint.z * 10
    s.op(p02, s.box(-22.5, 22.5, -13.7, -8.0, bottom, 21.0), "join")
    s.op(p02, s.cyl(M[0], M[1], -14.0, -7.9, 18.6), "cut")
    for ex, ez in ears:
        s.op(p02, s.cyl(ex, ez, -14.0, -7.9, 3.2), "cut")
    t = math.radians(THETA)
    lead = (-math.cos(t), math.sin(t))
    lx, lz = M[0] + lead[0] * 23.0, M[1] + lead[1] * 23.0
    s.op(p02, load("ahg_placement").obb(lx, -10.85, lz, lead, 14.0, 6.4, 10.0), "cut")

    # Stock parts: both axles shortened at the rear to start on the motor-face plane.
    pin = s.cyl(F[0], F[1], FACE + .1, 29.7, 2.0)
    axle = s.cyl(Mv[0], Mv[1], FACE + .1, 28.3, 2.0)
    hardware = [
        (ring(F[0], F[1], PLATE_Y[0], PLATE_Y[1], 3.5, 2.0), "MR74 4x7x2 fixed axle rear (pin plate C-seat)"),
        (ring(Mv[0], Mv[1], PLATE_Y[0], PLATE_Y[1], 3.5, 2.0), "MR74 4x7x2 moving axle rear (pin plate)"),
        (ring(Mv[0], Mv[1], ARM_RING_Y[0], ARM_RING_Y[1], 7.5, 5.0), "6700ZZ arm rear hinge (on moving hub)"),
    ] + [(screw, "M3x10 SHCS motor ear %d (rear entry)" % i) for i, screw in enumerate(screws)]

    replace(by["PRINT_carrier_box_left"], arm, None, "P04 Swing arm - AHG hinge ring")
    replace(by["PRINT_compound_right"], fixed, None, "P07 Right compound - 38T from Y6.6")
    replace(by["PRINT_compound_left"], moving, None, "P06 Left compound - 6700 hub")
    replace(by["PRINT_motor_mount"], p01, None, "P01 Flat backplate - AHG pocket")
    replace(by["PRINT_REAR_MOTOR_SERVO_SPACER"], p02, None, "P02 Spacer - AHG pass-through")
    replace(by["PRINT_000_outer_shell_of_extruder_1"], p03, None, "P03 Front clamshell - hinge-ring relief")
    replace(by["STOCK_013_4mm_axle_1"], pin, "AXLE_4x25_fixed", "AXLE 4x25 fixed (rotating)")
    replace(by["STOCK_048_4mm_axle_1_1"], axle, "AXLE_4x24_moving", "AXLE 4x24 moving (rotating)")
    removed = []
    for name in ("MOTOR_14HS13_case", "MOTOR_factory_shaft", "PINION_motor_20T_m0p5", "M3x3_motor_grub",
                 "M3x6_motor_0", "M3x6_motor_1", "M3x6_motor_2", "M3x6_motor_3",
                 "STOCK_011_4mm_flange_bearing_1", "STOCK_061_4mm_flange_bearing_3",
                 "STOCK_046_4mm_flange_bearing_1_1"):
        removed.append([name, bool(by[name].assemblyContext.deleteMe())])
    leftovers = [b.name for b in s.proxies(root) if b.name in ("M3x3_motor_grub", "MOTOR_factory_shaft",
                                                                  "PINION_motor_20T_m0p5", "MOTOR_14HS13_case")]
    for body in s.proxies(root):
        if body.name in leftovers:
            body.assemblyContext.isLightBulbOn = False
    motor_parts = a.ahg(M[0], M[1], FACE, THETA, lead_sign=1)
    groups = {
        "motor": s.add_group(root, "LDO-36STH20-1004AHG(XH)", [(p, n, None) for p, n, _ in motor_parts]),
        "plate": s.add_group(root, "P19 AHG pin plate (flat print)", [(plate, "PRINT_AHG_PIN_PLATE", None)]),
        "hardware": s.add_group(root, "AHG-min new hardware", [(h, n, None) for h, n in hardware]),
    }
    keys = {n: k for _, n, k in motor_parts}
    for body in groups["motor"].component.bRepBodies:
        body.appearance = a.colour(design, keys[body.name])
    STATE.update(M=M, F=F, Mv=Mv, H=H, ears=ears, groups=groups, leftovers=leftovers)
    report = {"motor_axis": M, "fixed_compound": F, "moving_compound": Mv, "moving_hob": H,
              "ears": ears, "removed": removed, "hidden_leftovers": leftovers,
              "p03_internal_relief_mm3": round(p03_removed, 1)}
    OUT.mkdir(exist_ok=True)
    (OUT / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


ARM_GROUPS = ("05 Swinging arm", "07 Moving-side driven", "09 Moving-side free", "11 Follower")
EXPECTED = {
    frozenset(("AXLE_4x25_fixed", "STOCK_015_4mm_flange_bearing_2")),
    frozenset(("AXLE_4x25_fixed", "PRINT_compound_right")),
    frozenset(("AXLE_4x24_moving", "STOCK_063_4mm_flange_bearing_front_frame_left")),
    frozenset(("AXLE_4x24_moving", "STOCK_050_4mm_flange_bearing_1_2")),
    frozenset(("AXLE_4x24_moving", "PRINT_compound_left")),
    frozenset(("AHG factory 10T m0.5 pinion", "PRINT_compound_right")),
}
ORIGINAL_PRESS_FITS = ("INSERT", "HEATSET")
RIGID_SUBASSEMBLY = {"HOBBY_SERVO_ENVELOPE", "MG90S_M2_NUT_left", "MG90S_M2_NUT_right", "MG90S_M2x6_SERVO_left",
                     "MG90S_M2x6_SERVO_right", "MG90S_M2_WASHER_left", "MG90S_M2_WASHER_right", "OEM_SERVO_SPLINE",
                     "OEM_SERVO_HORN", "OEM_HORN_SCREW", "CAM_HORN_SELF_TAP_-5.5", "CAM_HORN_SELF_TAP_5.5",
                     "PRINT_DIRECT_CAM", "CAM_JOURNAL_PIN_3x10", "CAM_OUTBOARD_MF63"}
FOLLOWER_STACK = {"FOLLOWER_M3x8_SHCS_single_shear", "FOLLOWER_INNER_RING_WASHER_rear",
                  "FOLLOWER_INNER_RING_WASHER_front", "CAM_FOLLOWER_623", "FOLLOWER_M3_INSERT"}
MOTOR_INTERNAL = ("AHG ",)
DEFORMING = ("CLOSING_SPRING_ENVELOPE",)


def check(app, extra=(), out_name="check.json"):
    """Static interference of every changed/new body, closed and at full open (arm group rotated)."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    bodies = s.proxies(design.rootComponent)
    changed = {"PRINT_carrier_box_left", "PRINT_compound_right", "PRINT_compound_left", "PRINT_motor_mount",
               "PRINT_REAR_MOTOR_SERVO_SPACER", "PRINT_000_outer_shell_of_extruder_1", "AXLE_4x25_fixed",
               "AXLE_4x24_moving", "PRINT_AHG_PIN_PLATE", "PRINT_DIRECT_CAM", "CAM_JOURNAL_PIN_3x10",
               "FOLLOWER_M3x8_SHCS_single_shear", "SPACER_M3x8_SHCS_rear_entry"} | set(SERVO_MOVES)
    changed |= {b.name for b in bodies if b.assemblyContext and b.assemblyContext.component.name in
                ("LDO-36STH20-1004AHG(XH)", "AHG-min new hardware")}
    changed |= set(extra)
    leftovers = set(STATE.get("leftovers", ()))
    bodies = [b for b in bodies if b.name not in leftovers]
    ignore_pairs = {frozenset(pair) for pair in EXPECTED}
    Mv = STATE["Mv"]
    results = {}
    for pose, degrees in (("closed", 0.0), ("open", OPEN_DEG)):
        shapes = []
        for body in bodies:
            shape = s.tbm().copy(body)
            path = body.assemblyContext.fullPathName if body.assemblyContext else ""
            moving_arm = any(group in path for group in ARM_GROUPS) or body.name in (
                "6700ZZ arm rear hinge (on moving hub)",)
            if degrees and moving_arm:
                shape = rotated(shape, Mv, degrees)
            shapes.append((body.name, shape, path))
        hits = []
        for i, (name, shape, path) in enumerate(shapes):
            if name not in changed:
                continue
            for j, (other, other_shape, other_path) in enumerate(shapes):
                if i == j or (other in changed and j < i) or frozenset((name, other)) in ignore_pairs:
                    continue
                if any(tag in other or tag in name for tag in ORIGINAL_PRESS_FITS):
                    continue
                if name in RIGID_SUBASSEMBLY and other in RIGID_SUBASSEMBLY:
                    continue  # spline, horn screw, self-taps, ear screws/nuts and cam pin: modeled engagements
                if {name, other} & FOLLOWER_STACK == {name, other}:
                    continue
                if name.startswith(MOTOR_INTERNAL) and other.startswith(MOTOR_INTERNAL):
                    continue
                if name.startswith(CART_CONTEXT_PREFIXES) and other.startswith(CART_CONTEXT_PREFIXES):
                    continue  # cart, belts, cartridges and their screws moved rigidly together
                if name.startswith("HF_") and other.startswith("HF_"):
                    continue  # hotend reference internals (threaded nozzle/heatbreak engagements)
                if degrees and (name in DEFORMING or other in DEFORMING):
                    continue
                if degrees and frozenset((name, other)) == frozenset(("PRINT_compound_left", "PRINT_feed_left")):
                    continue  # 14T/37T tooth phase: a pure rotation of the arm does not roll the 37T
                if not shape.boundingBox.intersects(other_shape.boundingBox):
                    continue
                volume, _ = s.common_volume(shape, other_shape)
                if volume > .05:
                    hits.append([name, other, round(volume, 2)])
        results[pose] = hits
    (OUT / out_name).write_text(json.dumps(results, indent=2) + "\n")
    return results

# ---------------------------------------------------------------------------------------------
# v3 (user direction): servo forward toward the stepper plane, cam neck removed, single-shear
# follower, arm's upper-rear block removed, freed backplate volume filled solid, strong servo seat.
# ---------------------------------------------------------------------------------------------
SERVO_SHIFT = 9.6
CAM_REAR_Y = 2.0
SERVO_MOVES = ("HOBBY_SERVO_ENVELOPE", "MG90S_M2_NUT_left", "MG90S_M2_NUT_right", "MG90S_M2x6_SERVO_left",
               "MG90S_M2x6_SERVO_right", "MG90S_M2_WASHER_left", "MG90S_M2_WASHER_right", "OEM_SERVO_SPLINE",
               "OEM_SERVO_HORN", "OEM_HORN_SCREW", "CAM_HORN_SELF_TAP_-5.5", "CAM_HORN_SELF_TAP_5.5")
RELOCATED_FASTENER = (-15.0, 52.0)


def translated(shape, dx=0.0, dy=0.0, dz=0.0):
    s = load("pancake_paths_study")
    copy = s.tbm().copy(shape)
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = adsk.core.Vector3D.create(dx / 10, dy / 10, dz / 10)
    s.tbm().transform(copy, matrix)
    return copy


def union_all(shapes):
    s = load("pancake_paths_study")
    result = s.tbm().copy(shapes[0])
    for shape in shapes[1:]:
        s.op(result, s.tbm().copy(shape), "join")
    return result


def apply_v3(app):
    s, a = load("pancake_paths_study"), load("ahg_placement")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    bodies = s.proxies(root)
    by = {body.name: body for body in bodies}
    if "FOLLOWER_M3x8_SHCS_single_shear" in by:
        raise RuntimeError("v3 already applied")
    C = s.centre(by["OEM_SERVO_SPLINE"])
    Fo = s.centre(by["CAM_FOLLOWER_623"])
    F = s.centre(by["AXLE_4x25_fixed"])
    Mv = s.centre(by["AXLE_4x24_moving"])
    M = (F[0] + 12.1 * math.cos(math.radians(PHI)), F[1] + 12.1 * math.sin(math.radians(PHI)))
    servo_bb = by["HOBBY_SERVO_ENVELOPE"].boundingBox
    case_front = servo_bb.maxPoint.y * 10 + SERVO_SHIFT
    case_x = (C[0] - 16.95 - .3, C[0] + 5.85 + .3)
    case_z = (servo_bb.minPoint.z * 10 - .3, servo_bb.maxPoint.z * 10 + .3)
    ear_x = (servo_bb.minPoint.x * 10 - .3, servo_bb.maxPoint.x * 10 + .3)
    ear_front = case_front - 1.9

    # Moved stock: servo, its ear hardware, spline, horn and horn screws.
    moved = {name: translated(by[name], dy=SERVO_SHIFT) for name in SERVO_MOVES}
    screw_axes = [s.centre(by[name]) for name in ("MG90S_M2x6_SERVO_left", "MG90S_M2x6_SERVO_right")]

    # Cam: drop the 9.6 mm neck/flange; the lobe and front collar stay at their original Y.
    cam = s.tbm().copy(by["PRINT_DIRECT_CAM"])
    s.op(cam, s.box(-10, 40, -20, CAM_REAR_Y, 30, 70), "cut")
    s.op(cam, s.cyl(C[0], C[1], CAM_REAR_Y - .1, case_front + 4.2 + 1.7, 1.95), "cut")
    for dx in (-5.5, 5.5):
        s.op(cam, s.cyl(C[0] + dx, C[1], CAM_REAR_Y - .1, 5.4, .9), "cut")
    pin = s.cyl(C[0], C[1], 4.8, 14.8, 1.5)

    # Follower: unchanged XZ and Y; single shear from the arm's front cheek, head at the rear.
    follower_screw = s.cyl(Fo[0], Fo[1], -1.2, 1.8, 2.75)
    s.op(follower_screw, s.cyl(Fo[0], Fo[1], 1.8, 9.8, 1.5), "join")

    # Arm: remove the upper-rear block (rear follower cheek and plate behind the front cheek).
    arm = s.tbm().copy(by["PRINT_carrier_box_left"])
    s.op(arm, s.box(-7, 22, -6, 6.8, 24.0, 52.0), "cut")

    # Clearance solids for everything that moves near the backplate.
    horn_sweep = s.cyl(C[0], C[1], case_front - .3, case_front + 4.5, 7.6)
    lobe_sweep = s.cyl(C[0], C[1], CAM_REAR_Y - .3, 6.6, 9.0)
    collar = s.cyl(C[0], C[1], 6.0, 7.9, 4.0)
    pin_hole = s.cyl(C[0], C[1], 4.6, 15.0, 1.7)
    follower_parts = s.cyl(Fo[0], Fo[1], 1.5, 7.0, 5.6)
    s.op(follower_parts, s.cyl(Fo[0], Fo[1], -1.6, 2.0, 3.2), "join")
    follower_sweep = union_all([rotated(follower_parts, Mv, d) for d in (0.0, -2.3, -4.6, OPEN_DEG)])
    case_pocket = s.box(case_x[0], case_x[1], -8.2, case_front + .3, case_z[0], case_z[1])
    ear_pocket = s.box(ear_x[0], ear_x[1], -8.2, ear_front, case_z[0], case_z[1])
    frame_hole = s.cyl(*s.centre(by["FRAME_REAR_LOADED_M3x40"]), -12.5, 29.6, 1.7)
    screw_holes, nut_pockets = [], []
    for (sx, sz) in screw_axes:
        screw_holes.append(s.cyl(sx, sz, -8.6, case_front + 2.0, 1.2))
        nut = s.cyl(sx, sz, ear_front + 1.5, ear_front + 3.3, 2.4)
        toward = case_x[0] if sx < C[0] else case_x[1]
        s.op(nut, s.box(min(sx, toward), max(sx, toward), ear_front + 1.5, ear_front + 3.3, sz - 2.1, sz + 2.1), "join")
        nut_pockets.append(nut)
    insert_hole = s.cyl(*RELOCATED_FASTENER, -8.1, -3.9, 2.0)
    servo_features = [case_pocket, ear_pocket, horn_sweep, lobe_sweep, collar, pin_hole, follower_sweep,
                      frame_hole, insert_hole] + screw_holes + nut_pockets

    # Backplate: fill the old arm cavity solid, then cut only what moves or mounts there.
    fill = s.box(-5.6, 20.3, -4.6, 6.6, 22.5, 52.0)
    for shape in (a.envelope(M[0], M[1], FACE, THETA, .3),
                  a.flange(M[0], M[1], PLATE_Y[0] - .05, PLATE_Y[1] + .1, THETA, .2),
                  s.cyl(F[0], F[1], 6.2, 11.2, 10.7), s.cyl(Mv[0], Mv[1], 6.2, 11.2, 10.7)):
        s.op(fill, shape, "cut")
    for shape in servo_features:
        s.op(fill, s.tbm().copy(shape), "cut")
    p01 = s.tbm().copy(by["PRINT_motor_mount"])
    p01_before = p01.volume * 1000
    s.op(p01, fill, "join")
    for shape in servo_features:
        s.op(p01, s.tbm().copy(shape), "cut")
    p01_delta = p01.volume * 1000 - p01_before

    # Spacer: fill the retired servo-ear seats, pass the servo through, rear-entry access and fastener.
    p02 = s.tbm().copy(by["PRINT_REAR_MOTOR_SERVO_SPACER"])
    s.op(p02, s.box(-12, 22, -13.7, -8.0, 44.4, 59.6), "join")
    s.op(p02, s.box(case_x[0], case_x[1], -14.0, -7.9, case_z[0], case_z[1]), "cut")
    for (sx, sz) in screw_axes:
        s.op(p02, s.cyl(sx, sz, -14.0, -7.9, 2.6), "cut")
    s.op(p02, s.cyl(*RELOCATED_FASTENER, -14.0, -7.9, 1.7), "cut")
    t = math.radians(THETA)
    lead = (-math.cos(t), math.sin(t))
    lx, lz = M[0] + lead[0] * 23.0, M[1] + lead[1] * 23.0
    s.op(p02, a.obb(lx, -10.85, lz, lead, 14.0, 6.4, 12.0), "cut")

    # Relocated P02-to-P01 fastener: rear-entry M3x8 SHCS into a P01 heat-set insert.
    fastener = s.cyl(*RELOCATED_FASTENER, -16.7, -13.7, 2.75)
    s.op(fastener, s.cyl(*RELOCATED_FASTENER, -13.7, -5.7, 1.5), "join")
    insert = s.cyl(*RELOCATED_FASTENER, -8.0, -4.0, 2.3)

    for name, shape in moved.items():
        replace(by[name], shape)
    replace(by["PRINT_DIRECT_CAM"], cam, None, "P05 Servo cam - compact, no neck")
    replace(by["CAM_JOURNAL_PIN_3x12"], pin, "CAM_JOURNAL_PIN_3x10", "CAM_JOURNAL_PIN_3x10")
    replace(by["FOLLOWER_M3x12"], follower_screw, "FOLLOWER_M3x8_SHCS_single_shear", "FOLLOWER_M3x8_SHCS")
    replace(by["PRINT_carrier_box_left"], arm)
    replace(by["PRINT_motor_mount"], p01, None, "P01 Flat backplate - AHG + forward servo")
    replace(by["PRINT_REAR_MOTOR_SERVO_SPACER"], p02, None, "P02 Spacer - motor and servo pass-through")
    replace(by["INTEGRATED_SPACER_M3x6_1"], fastener, "SPACER_M3x8_SHCS_rear_entry", "SPACER_M3x8_SHCS_rear_entry")
    replace(by["INTEGRATED_SPACER_INSERT_1"], insert, "SPACER_M3_HEATSET_in_P01", "SPACER_M3_HEATSET_in_P01")
    report = {
        "servo_shift_y_mm": SERVO_SHIFT, "servo_case_y_mm": [servo_bb.minPoint.y * 10 + SERVO_SHIFT, case_front],
        "servo_ear_front_y_mm": ear_front, "cam_axis_xz_mm": C, "follower_axis_xz_mm": Fo,
        "cam_y_mm": [CAM_REAR_Y, 7.6], "journal_pin": "3x10 at Y 4.8..14.8",
        "follower": "623 unchanged at Y 2.3..6.3; M3x8 SHCS single shear into the front-cheek insert",
        "p01_net_added_mm3": round(p01_delta, 1),
        "relocated_p02_p01_fastener_xz_mm": RELOCATED_FASTENER,
    }
    STATE.update(C=C, Fo=Fo, v3=report)
    (OUT / "v3.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def capture_v3(app):
    """Inspection-coloured views of the AHG-min v3 model, including the user's side-view framing."""
    s, a = load("pancake_paths_study"), load("ahg_placement")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    view = app.activeViewport
    images = OUT / "images_v3"
    images.mkdir(parents=True, exist_ok=True)
    base = design.appearances.itemByName("SparkShift arm")
    palette = dict(s.COLOURS)
    palette.update({"P19": (0, 170, 170), "gear": (255, 191, 48), "servo": (107, 129, 153),
                    "hardware": (204, 221, 236), "new": (255, 120, 0)})

    def colour(key):
        name = "AHGmin colour " + key
        found = design.appearances.itemByName(name)
        if not found:
            found = design.appearances.addByCopy(base, name)
            prop = adsk.core.ColorProperty.cast(found.appearanceProperties.itemById("opaque_albedo"))
            prop.value = adsk.core.Color.create(*palette[key], 255)
        return found
    for body in s.proxies(root):
        context = body.assemblyContext
        group = context.component.name if context else ""
        prefix = context.name[:3] if context else ""
        if group == "LDO-36STH20-1004AHG(XH)":
            continue
        if prefix in palette:
            key = prefix
        elif group == "AHG-min new hardware":
            key = "new"
        elif body.name.startswith(("PRINT_compound", "OEM_SERVO_SPLINE")):
            key = "gear"
        elif body.name == "HOBBY_SERVO_ENVELOPE":
            key = "servo"
        else:
            key = "hardware"
        body.appearance = colour(key)

    def contexts(names):
        return [b.assemblyContext for b in s.proxies(root) if b.name in names and b.assemblyContext]
    leftovers = set(STATE.get("leftovers", ()))
    for occ in contexts(leftovers):
        occ.isLightBulbOn = False

    def show(hidden=()):
        for b in s.proxies(root):
            if b.assemblyContext and b.name not in leftovers:
                b.assemblyContext.isLightBulbOn = b.name not in hidden

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

    housings = {"PRINT_motor_mount", "PRINT_000_outer_shell_of_extruder_1"}
    side_target = (0, .3, 2.6)
    show(hidden=housings)
    shot("side_like_screenshot.png", (40, .3, 2.6), side_target, 11.5)
    shot("rear_iso_internals.png", (-30, -38, 22), (0, 0, 2.0))
    show(hidden={"PRINT_000_outer_shell_of_extruder_1"})
    shot("side_with_backplate.png", (40, .3, 2.6), side_target, 11.5)
    show(hidden={"PRINT_REAR_MOTOR_SERVO_SPACER"})
    shot("rear_iso_no_spacer.png", (-30, -38, 22))
    show()
    shot("rear_iso.png", (-30, -38, 22))
    shot("rear_right_iso.png", (30, -38, 18))
    shot("front_iso.png", (30, 38, 18))

    # Section through the cam axis (X = cam axis): temporary display group, removed afterwards.
    cut_x = STATE["C"][0]
    items = [(s.tbm().copy(b), b.name, b.appearance) for b in s.proxies(root)
             if b.assemblyContext and b.isVisible and b.name not in leftovers]
    group = s.add_group(root, "TEMP section through cam axis", a.section_at(items, cut_x))
    try:
        for occ in root.occurrences:
            occ.isLightBulbOn = occ.component.name == "TEMP section through cam axis"
        target = (cut_x / 10, 0, 3.6)
        shot("section_cam_axis.png", (40, 0, 3.6), target, 9.0)
    finally:
        group.deleteMe()
        for occ in root.occurrences:
            occ.isLightBulbOn = True
        show()
    return sorted(path.name for path in images.iterdir())


# ---------------------------------------------------------------------------------------------
# v4 (user direction): heater block flipped 180 deg, extruder pushed rearward toward the cart.
# The model keeps the extruder datums fixed and moves the cart/belt context forward by DELTA.
# ---------------------------------------------------------------------------------------------
NOZZLE_AXIS = (0.0, 22.7)
HEATER_BLOCK = ("HF_04_Creality_Ender_3_Volcano_Hotend_v14", "HF_05_HF03_NOMINAL_VOLCANO_NOZZLE_NOT_VENDOR_CAD",
                "HF_06_HF04_HEATER_6x20_NOMINAL_REFERENCE", "HF_07_HF05_THERMISTOR_3x15_NOMINAL_REFERENCE")
CART_CONTEXT_PREFIXES = ("MONO_CART", "PRINT_MONOLITH", "MONOC_", "REFINED_M3x10_CART")
LOWER_SPLIT_Z = -18.0
CART_FEATURE_END_Y = 1.5


def turned_about_z(shape, centre, degrees):
    s = load("pancake_paths_study")
    copy = s.tbm().copy(shape)
    matrix = adsk.core.Matrix3D.create()
    matrix.setToRotation(math.radians(degrees), adsk.core.Vector3D.create(0, 0, 1),
                         adsk.core.Point3D.create(centre[0] / 10, centre[1] / 10, 0))
    s.tbm().transform(copy, matrix)
    return copy


def flip_heater(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    nozzle = s.centre(by["HF_05_HF03_NOMINAL_VOLCANO_NOZZLE_NOT_VENDOR_CAD"])
    before = {name: [round(by[name].boundingBox.minPoint.y * 10, 2), round(by[name].boundingBox.maxPoint.y * 10, 2)]
              for name in HEATER_BLOCK}
    axis = (0.0, (by["HF_05_HF03_NOMINAL_VOLCANO_NOZZLE_NOT_VENDOR_CAD"].boundingBox.minPoint.y +
                  by["HF_05_HF03_NOMINAL_VOLCANO_NOZZLE_NOT_VENDOR_CAD"].boundingBox.maxPoint.y) * 5)
    axis = (nozzle[0], axis[1])
    for name in HEATER_BLOCK:
        replace(by[name], turned_about_z(by[name], axis, 180.0))
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    after = {name: [round(by[name].boundingBox.minPoint.y * 10, 2), round(by[name].boundingBox.maxPoint.y * 10, 2)]
             for name in HEATER_BLOCK}
    STATE["nozzle_axis"] = axis
    return {"nozzle_axis_xy": axis, "before_y": before, "after_y": after}


def scan_shift(app, deltas=(8.0, 9.0, 9.5, 10.0, 11.0, 12.0)):
    """Move the cart/belt context forward by each delta; list clashes with everything except P01."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    bodies = [b for b in s.proxies(design.rootComponent) if b.name not in set(STATE.get("leftovers", ()))]
    context = [b for b in bodies if b.name.startswith(CART_CONTEXT_PREFIXES)]
    others = [b for b in bodies if not b.name.startswith(CART_CONTEXT_PREFIXES) and b.name != "PRINT_motor_mount"]
    results = {}
    for delta in deltas:
        hits = []
        for body in context:
            shape = translated(body, dy=delta)
            for other in others:
                if not shape.boundingBox.intersects(other.boundingBox):
                    continue
                volume, _ = s.common_volume(shape, s.tbm().copy(other))
                if volume > .05:
                    hits.append([body.name, other.name, round(volume, 2)])
        results[str(delta)] = hits
    return results

# ---- v4 inspection helpers -----------------------------------------------------------------
IMAGES_V4 = OUT / "images_v4"


def camera_shot(app, name, eye, target, up=(0, 0, 1), extents=None, size=(1600, 1200)):
    view = app.activeViewport
    camera = view.camera
    camera.isSmoothTransition = False
    camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    camera.isFitView = extents is None
    camera.target = adsk.core.Point3D.create(*target)
    camera.eye = adsk.core.Point3D.create(*eye)
    camera.upVector = adsk.core.Vector3D.create(*up)
    if extents:
        camera.viewExtents = extents
    view.camera = camera
    adsk.doEvents()
    view.refresh()
    IMAGES_V4.mkdir(parents=True, exist_ok=True)
    if not view.saveAsImageFile(str(IMAGES_V4 / name), size[0], size[1]):
        raise RuntimeError("Image capture failed: " + name)
    return name


AUDIT_COLOURS = {"PRINT_motor_mount": (70, 130, 220), "PRINT_REAR_MOTOR_SERVO_SPACER": (90, 190, 110),
                 "PRINT_000_outer_shell_of_extruder_1": (235, 150, 60), "PRINT_carrier_box_left": (210, 60, 70),
                 "PRINT_AHG_PIN_PLATE": (160, 90, 200)}


def rgb_appearance(design, key, rgb):
    name = "AUDIT colour " + key
    found = design.appearances.itemByName(name)
    if not found:
        found = design.appearances.addByCopy(design.appearances.itemByName("SparkShift arm"), name)
        prop = adsk.core.ColorProperty.cast(found.appearanceProperties.itemById("opaque_albedo"))
        prop.value = adsk.core.Color.create(*rgb, 255)
    return found


def section_shot(app, name, axis, value, keep_below, eye, target, up, extents, hide=(), only=None, depth=None,
                 include_hidden=True, colours=None):
    """Temporary sectioned copy of the visible model (keep the side below/above value), one image."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    leftovers = set(STATE.get("leftovers", ()))
    big = 400.0
    lo, hi = (value, big) if keep_below else (-big, value)
    bounds = {"x": (lo, hi, -big, big, -big, big), "y": (-big, big, lo, hi, -big, big),
              "z": (-big, big, -big, big, lo, hi)}[axis]
    items = []
    for body in s.proxies(root):
        if not body.assemblyContext or body.name in leftovers or body.name in hide:
            continue
        if not include_hidden and not body.isVisible:
            continue
        if body.assemblyContext.component.name.startswith("TEMP"):
            continue
        if only is not None and not any(body.name.startswith(p) for p in only):
            continue
        bb = body.boundingBox
        low, high = getattr(bb.minPoint, axis) * 10, getattr(bb.maxPoint, axis) * 10
        if (keep_below and low >= value) or (not keep_below and high <= value):
            continue
        copy = s.tbm().copy(body)
        if low < value < high:
            try:
                s.op(copy, s.box(*bounds), "cut")
            except RuntimeError:
                continue
            if not copy.lumps.count:
                continue
        if depth:
            far = value - depth if keep_below else value + depth
            if (keep_below and high <= far) or (not keep_below and low >= far):
                continue
            slab = (-big, far) if keep_below else (far, big)
            cut = {"x": (slab[0], slab[1], -big, big, -big, big), "y": (-big, big, slab[0], slab[1], -big, big),
                   "z": (-big, big, -big, big, slab[0], slab[1])}[axis]
            if (keep_below and low < far) or (not keep_below and high > far):
                try:
                    s.op(copy, s.box(*cut), "cut")
                except RuntimeError:
                    continue
                if not copy.lumps.count:
                    continue
        look = rgb_appearance(design, body.name, colours[body.name]) if colours and body.name in colours else body.appearance
        items.append((copy, body.name, look))
    states = [(occ, occ.isLightBulbOn) for occ in root.occurrences]
    group = s.add_group(root, "TEMP v4 section", items)
    try:
        for occ, _ in states:
            occ.isLightBulbOn = False
        return camera_shot(app, name, eye, target, up, extents)
    finally:
        group.deleteMe()
        for occ, state in states:
            occ.isLightBulbOn = state


# ---- v4 shift: extruder 8.3 mm closer to the cart ----------------------------------------------
SHIFT = 8.3                      # cart face moves from Y -8.0 to Y 0.3 in the extruder frame
SPLIT_Y = -8.0 + SHIFT           # new P01/P02 interface = cart face plane (one flat P01 print face)
BAND_FRONT_Y = 11.4              # original band front face, kept
SPACER_SCREWS = {                # P02 -> P01 fasteners moved to the new interface (rear-entry, counterbored)
    "INTEGRATED_SPACER_M3x6_0": ("INTEGRATED_SPACER_INSERT_0", (17.25, 23.72), "SPACER_M3x10_SHCS_0"),
    "SPACER_M3x8_SHCS_rear_entry": ("SPACER_M3_HEATSET_in_P01", (-15.0, 52.0), "SPACER_M3x10_SHCS_1"),
}


def apply_v4_shift(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    if "SPACER_M3x10_SHCS_0" in by:
        raise RuntimeError("v4 shift already applied")
    context = [b for n, b in by.items() if n.startswith(CART_CONTEXT_PREFIXES)]
    moved = {b.name: translated(b, dy=SHIFT) for b in context}

    p01_old = by["PRINT_motor_mount"]
    upper = s.tbm().copy(p01_old)
    s.op(upper, s.box(-40, 40, SPLIT_Y, 40, LOWER_SPLIT_Z, 90), "common")
    band = s.tbm().copy(p01_old)
    s.op(band, s.box(-40, 40, -20, BAND_FRONT_Y - SHIFT, -70, LOWER_SPLIT_Z), "common")
    band = translated(band, dy=SHIFT)
    s.op(band, s.box(-14.5, 14.5, 10.9, 12.0, -24.6, LOWER_SPLIT_Z + .2), "cut")  # original tool-carrier recess
    p01 = union_all([upper, band])

    slice_ = s.tbm().copy(p01_old)
    s.op(slice_, s.box(-40, 40, -8.05, SPLIT_Y, -17.78, 90), "common")
    p02 = s.tbm().copy(by["PRINT_REAR_MOTOR_SERVO_SPACER"])
    s.op(p02, slice_, "join")

    fasteners = {}
    for screw_name, (insert_name, (fx, fz), new_name) in SPACER_SCREWS.items():
        s.op(p02, s.cyl(fx, fz, -13.0, SPLIT_Y - .05, 3.2), "join")      # close the retired holes
        s.op(p02, s.cyl(fx, fz, -14.0, -6.0, 3.2), "cut")                 # head counterbore from the rear
        s.op(p02, s.cyl(fx, fz, -6.1, SPLIT_Y + .1, 1.7), "cut")
        s.op(p01, s.cyl(fx, fz, SPLIT_Y - .1, SPLIT_Y + 4.3, 2.0), "cut")  # heat-set insert in P01
        screw = s.cyl(fx, fz, -9.0, -6.0, 2.75)
        s.op(screw, s.cyl(fx, fz, -6.0, 4.0, 1.5), "join")
        fasteners[screw_name] = (screw, new_name)
        fasteners[insert_name] = (s.cyl(fx, fz, SPLIT_Y, SPLIT_Y + 4.0, 2.3), new_name.replace("SHCS", "HEATSET"))

    for name, shape in moved.items():
        replace(by[name], shape)
    replace(p01_old, p01, None, "P01 Backplate - cart face is the print face")
    replace(by["PRINT_REAR_MOTOR_SERVO_SPACER"], p02, None, "P02 Motor and servo plate - 14 mm")
    for name, (shape, new_name) in fasteners.items():
        replace(by[name], shape, new_name, new_name)
    by = {b.name: b for b in s.proxies(root)}
    def bb(n):
        b = by[n].boundingBox
        return [round(v * 10, 2) for v in (b.minPoint.x, b.maxPoint.x, b.minPoint.y, b.maxPoint.y,
                                           b.minPoint.z, b.maxPoint.z)]
    report = {"shift_mm": SHIFT, "split_y": SPLIT_Y, "p01_bb": bb("PRINT_motor_mount"),
              "p02_bb": bb("PRINT_REAR_MOTOR_SERVO_SPACER"), "cart_bb": bb("MONO_CART_MGN12H"),
              "p01_lumps": by["PRINT_motor_mount"].lumps.count,
              "p02_lumps": by["PRINT_REAR_MOTOR_SERVO_SPACER"].lumps.count,
              "p01_volume_mm3": round(by["PRINT_motor_mount"].volume * 1000, 1),
              "p02_volume_mm3": round(by["PRINT_REAR_MOTOR_SERVO_SPACER"].volume * 1000, 1),
              "moved_context": sorted(moved)}
    STATE["v4_shift"] = report
    (OUT / "v4_shift.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


# ---- v4 arm (user sketch): follower bearing inside the arm, arm filled behind / in front / below ----
FOLLOWER_DY = 2.7                       # 623 from Y 2.3..6.3 to 5.0..9.0, double shear on a pressed pin
REAR_CHEEK = (2.5, 4.5)
FRONT_FACE = 13.0
LOBE = (4.8, 9.2)
NECK = (2.0, 4.8)
COLLAR = (9.2, 10.5)
NECK_R, COLLAR_R, LOBE_SWEEP_R = 7.3, 3.6, 9.0
ARM_POSES = (0.0, OPEN_DEG / 3, 2 * OPEN_DEG / 3, OPEN_DEG)
FOLLOWER_PIN = "FOLLOWER_PIN_3x10_double_shear"
FOLLOWER_STACK.add(FOLLOWER_PIN)
FOLLOWER_MOVES = ("CAM_FOLLOWER_623", "FOLLOWER_INNER_RING_WASHER_rear", "FOLLOWER_INNER_RING_WASHER_front")


def arm_frame(shapes):
    """Static shapes as the arm sees them over its stroke (subtract from new arm material)."""
    Mv = STATE["Mv"]
    return union_all([rotated(sh, Mv, -d) for sh in shapes for d in ARM_POSES])


def stroke_pocket(shape, grow=0.4):
    """Housing pocket for new arm material: swept through the stroke and grown in X/Z."""
    Mv = STATE["Mv"]
    copies = []
    for d in ARM_POSES:
        r = rotated(shape, Mv, d)
        copies.append(r)
        for dx, dz in ((grow, 0), (-grow, 0), (0, grow), (0, -grow)):
            copies.append(translated(r, dx=dx, dz=dz))
    return union_all(copies)


def extrude_slice(body, y0, y1, window, to_y0, to_y1):
    """Repeat the body's [y0, y1] slice (inside the XZ window) to fill [to_y0, to_y1]."""
    s = load("pancake_paths_study")
    x0, x1, z0, z1 = window
    piece = s.tbm().copy(body)
    s.op(piece, s.box(x0, x1, y0, y1, z0, z1), "common")
    step = (y1 - y0) - .05
    shapes, y = [], to_y0
    while y < to_y1:
        shapes.append(translated(piece, dy=y - y0))
        y += step
    out = union_all(shapes)
    s.op(out, s.box(x0 - 1, x1 + 1, to_y0, to_y1, z0 - 1, z1 + 1), "common")
    return out


def apply_v4_arm(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    if FOLLOWER_PIN in by:
        raise RuntimeError("v4 arm already applied")
    C, Fo, Mv = STATE["C"], STATE["Fo"], STATE["Mv"]
    F = s.centre(by["AXLE_4x25_fixed"])
    M = (F[0] + 12.1 * math.cos(math.radians(PHI)), F[1] + 12.1 * math.sin(math.radians(PHI)))
    arm_old = by["PRINT_carrier_box_left"]
    report = {}

    # New arm material: behind the bearing, ahead of the cheek/lever, and under the hinge web.
    rear = extrude_slice(arm_old, 6.9, 7.25, (-6, 14.5, 26, 53), REAR_CHEEK[0], 7.0)
    s.op(rear, s.cyl(Fo[0], Fo[1], REAR_CHEEK[0], 7.0, 2.6), "join")
    front = extrude_slice(arm_old, 10.45, 10.95, (-6, 11, 37.5, 76), 10.9, FRONT_FACE)
    bottom = extrude_slice(arm_old, 11.05, 11.5, (2, 19, -13, 4), 6.8, 11.1)
    s.op(bottom, s.cyl(Mv[0], Mv[1], 6.2, 10.95, 10.3), "cut")                 # moving 38T band
    statics = [s.cyl(M[0], M[1], 5.5, 10.6, 3.5), s.cyl(F[0], F[1], 6.2, 11.4, 10.3)]
    statics += [s.tbm().copy(by[n]) for n in ("CLAM_M3x20_FRAME_2", "STOCK_059_A1104_hall_effect_sensor_1")]
    s.op(bottom, arm_frame(statics), "cut")

    cam_clear = arm_frame([s.cyl(C[0], C[1], 1.9, LOBE[0] + .15, NECK_R + .4),
                           s.cyl(C[0], C[1], LOBE[0] - .4, LOBE[1] + .4, LOBE_SWEEP_R),
                           s.cyl(C[0], C[1], COLLAR[0] - .2, 10.8, COLLAR_R + .8),
                           s.cyl(C[0], C[1], 10.5, 14.0, 6.5)])
    for shape in (rear, front):
        s.op(shape, s.tbm().copy(cam_clear), "cut")
    arm = union_all([arm_old, rear, front, bottom])
    s.op(arm, cam_clear, "cut")                                                # lobe now runs forward
    s.op(arm, s.cyl(Fo[0], Fo[1], REAR_CHEEK[1] - .1, 9.6, 5.6), "cut")         # bearing + washers slot
    s.op(arm, s.cyl(Fo[0], Fo[1], REAR_CHEEK[0] - .1, FRONT_FACE + .1, 1.5), "cut")  # pressed pin
    report["arm_added_mm3"] = round((arm.volume - arm_old.volume) * 1000, 1)
    report["arm_lumps"] = arm.lumps.count

    # Cam: same profile, full-width lobe at the bearing, round hub to the horn, thrust collar.
    cam_old = by["PRINT_DIRECT_CAM"]
    lobe_slice = s.tbm().copy(cam_old)
    s.op(lobe_slice, s.box(-10, 40, 4.0, 5.0, 30, 70), "common")
    for dx in (-5.5, 5.5):
        s.op(lobe_slice, s.cyl(C[0] + dx, C[1], 3.9, 5.1, 1.0), "join")
    lobe = extrude_slice(lobe_slice, 4.0, 5.0, (-10, 40, 30, 70), LOBE[0], LOBE[1])
    cam = union_all([lobe, s.cyl(C[0], C[1], NECK[0], NECK[1] + .05, NECK_R),
                     s.cyl(C[0], C[1], COLLAR[0] - .05, COLLAR[1], COLLAR_R)])
    s.op(cam, s.cyl(C[0], C[1], 3.7, COLLAR[1] + .1, 1.49), "cut")
    s.op(cam, s.cyl(C[0], C[1], NECK[0] - .1, 3.7, 1.95), "cut")
    for dx in (-5.5, 5.5):
        s.op(cam, s.cyl(C[0] + dx, C[1], NECK[0] - .1, 5.4, .9), "cut")
    report["cam_lumps"] = cam.lumps.count

    # Housings: pockets for the new arm material through the stroke, and the forward cam sweep.
    rear_pocket = union_all([rear, translated(rear, dy=-.4)])
    front_pocket = union_all([front, translated(front, dy=.4)])
    bottom_pocket = union_all([bottom, translated(bottom, dy=-.4)])
    pockets = stroke_pocket(union_all([rear_pocket, front_pocket, bottom_pocket]))
    cam_sweep = union_all([s.cyl(C[0], C[1], 1.6, LOBE[0] + .2, NECK_R + .4),
                           s.cyl(C[0], C[1], LOBE[0] - .4, LOBE[1] + .4, LOBE_SWEEP_R),
                           s.cyl(C[0], C[1], COLLAR[0] - .2, 10.8, COLLAR_R + .8)])
    housings = {}
    for name in ("PRINT_motor_mount", "PRINT_000_outer_shell_of_extruder_1"):
        h = s.tbm().copy(by[name])
        before = h.volume
        s.op(h, s.tbm().copy(pockets), "cut")
        s.op(h, s.tbm().copy(cam_sweep), "cut")
        housings[name] = h
        report[name + "_removed_mm3"] = round((before - h.volume) * 1000, 1)
        report[name + "_lumps"] = h.lumps.count

    # Follower stack forward; pin replaces the single-shear screw; the old insert is retired.
    moved = {n: translated(by[n], dy=FOLLOWER_DY) for n in FOLLOWER_MOVES}
    pin = s.cyl(Fo[0], Fo[1], REAR_CHEEK[0] + .1, REAR_CHEEK[0] + 10.1, 1.5)

    replace(arm_old, arm)
    replace(cam_old, cam, None, "P05 Servo cam - full-width lobe at the arm plane")
    for name, h in housings.items():
        replace(by[name], h)
    for name, shape in moved.items():
        replace(by[name], shape)
    replace(by["FOLLOWER_M3x8_SHCS_single_shear"], pin, FOLLOWER_PIN, FOLLOWER_PIN)
    insert = by["FOLLOWER_M3_INSERT"]
    (insert.nativeObject or insert).isLightBulbOn = False
    STATE.setdefault("leftovers", [])
    if isinstance(STATE["leftovers"], set):
        STATE["leftovers"].add("FOLLOWER_M3_INSERT")
    else:
        STATE["leftovers"] = list(STATE["leftovers"]) + ["FOLLOWER_M3_INSERT"]
    STATE["v4_arm"] = report
    (OUT / "v4_arm.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def ghost_shot(app, name, eye, target, up, extents, hide=(), ghost_dy=-SHIFT, size=(1800, 1400)):
    """All bodies plus a translucent copy of the cart context at its v3 position relative to the extruder."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    leftovers = set(STATE.get("leftovers", ()))
    items, ghosts = [], []
    for body in s.proxies(root):
        if not body.assemblyContext or body.name in leftovers or body.name in hide:
            continue
        if body.assemblyContext.component.name.startswith("TEMP"):
            continue
        items.append((s.tbm().copy(body), body.name, body.appearance))
        if body.name.startswith(CART_CONTEXT_PREFIXES) and ghost_dy:
            ghosts.append((translated(body, dy=ghost_dy), "GHOST " + body.name, body.appearance))
    states = [(occ, occ.isLightBulbOn) for occ in root.occurrences]
    group = s.add_group(root, "TEMP v4 view", items)
    ghost = s.add_group(root, "TEMP v4 ghost", ghosts) if ghosts else None
    try:
        if ghost:
            for body in ghost.component.bRepBodies:
                body.opacity = .28
        for occ, _ in states:
            occ.isLightBulbOn = False
        return camera_shot(app, name, eye, target, up, extents, size)
    finally:
        group.deleteMe()
        if ghost:
            ghost.deleteMe()
        for occ, state in states:
            occ.isLightBulbOn = state


def marker_appearance(design, name="AHGmin colour marker", rgb=(40, 230, 70)):
    found = design.appearances.itemByName(name)
    if not found:
        base = design.appearances.itemByName("SparkShift arm")
        found = design.appearances.addByCopy(base, name)
        prop = adsk.core.ColorProperty.cast(found.appearanceProperties.itemById("opaque_albedo"))
        prop.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
    return found


def relative_shot(app, name, cart_dy, target_y, markers_y, extents=16.0, target_z=-0.9, hide=()):
    """Exterior side view with the cart context relocated by cart_dy (cart-aligned camera) and
    green vertical reference lines at the given Y positions (extruder frame)."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    leftovers = set(STATE.get("leftovers", ()))
    marker = marker_appearance(design)
    items = []
    for body in s.proxies(root):
        if not body.assemblyContext or body.name in leftovers or body.name in hide:
            continue
        if body.assemblyContext.component.name.startswith("TEMP"):
            continue
        shape = s.tbm().copy(body)
        if body.name.startswith(CART_CONTEXT_PREFIXES) and cart_dy:
            shape = translated(body, dy=cart_dy)
        items.append((shape, body.name, body.appearance))
    for y in markers_y:
        items.append((s.box(30.0, 30.6, y - .25, y + .25, -95, 90), "MARKER %.1f" % y, marker))
    states = [(occ, occ.isLightBulbOn) for occ in root.occurrences]
    group = s.add_group(root, "TEMP v4 relative", items)
    try:
        for occ, _ in states:
            occ.isLightBulbOn = False
        return camera_shot(app, name, (40, target_y / 10, target_z), (0, target_y / 10, target_z), (0, 0, 1),
                           extents, (1800, 1400))
    finally:
        group.deleteMe()
        for occ, state in states:
            occ.isLightBulbOn = state


# ---- v5 cleanup inspection: hole inventory and 1D-opening thin-wall scan ------------------------
PARTS = {"P01": "PRINT_motor_mount", "P02": "PRINT_REAR_MOTOR_SERVO_SPACER",
         "P03": "PRINT_000_outer_shell_of_extruder_1", "P04": "PRINT_carrier_box_left"}


def axis_cyl(origin, axis, r, a0, a1):
    s = load("pancake_paths_study")
    p0 = adsk.core.Point3D.create(origin[0] / 10 + axis[0] * a0 / 10, origin[1] / 10 + axis[1] * a0 / 10,
                                  origin[2] / 10 + axis[2] * a0 / 10)
    p1 = adsk.core.Point3D.create(origin[0] / 10 + axis[0] * a1 / 10, origin[1] / 10 + axis[1] * a1 / 10,
                                  origin[2] / 10 + axis[2] * a1 / 10)
    return s.tbm().createCylinderOrCone(p0, r / 10, p1, r / 10)


def hole_inventory(app, key):
    """Every concave cylindrical face of a printed part, grouped, with the bodies that use it."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    bodies = [b for b in s.proxies(design.rootComponent) if b.name not in set(STATE.get("leftovers", ()))]
    part = next(b for b in bodies if b.name == PARTS[key])
    groups = {}
    for face in part.faces:
        g = face.geometry
        if not isinstance(g, adsk.core.Cylinder):
            continue
        ax = g.axis
        axis = tuple(round(v, 3) for v in (ax.x, ax.y, ax.z))
        if max(abs(v) for v in axis) < .999:
            continue
        axis = tuple(float(round(v)) for v in axis)
        if sum(axis) < 0:
            axis = tuple(-v for v in axis)
        o = g.origin
        pt = face.pointOnFace
        ok, normal = face.evaluator.getNormalAtPoint(pt)
        radial = adsk.core.Vector3D.create(pt.x - o.x, pt.y - o.y, pt.z - o.z)
        along = radial.dotProduct(adsk.core.Vector3D.create(*axis))
        radial = adsk.core.Vector3D.create(radial.x - along * axis[0], radial.y - along * axis[1],
                                           radial.z - along * axis[2])
        concave = normal.dotProduct(radial) < 0
        if not concave:
            continue
        idx = [i for i in range(3) if axis[i]][0]
        centre = [round(v * 10, 2) for v in (o.x, o.y, o.z)]
        centre[idx] = 0.0
        k = (axis, tuple(centre), round(g.radius * 10, 2))
        fb = face.boundingBox
        lo, hi = [fb.minPoint.x, fb.minPoint.y, fb.minPoint.z][idx] * 10, [fb.maxPoint.x, fb.maxPoint.y, fb.maxPoint.z][idx] * 10
        if k in groups:
            groups[k][0] = min(groups[k][0], lo)
            groups[k][1] = max(groups[k][1], hi)
        else:
            groups[k] = [lo, hi]
    rows = []
    others = [b for b in bodies if b.name != part.name]
    for (axis, centre, r), (lo, hi) in sorted(groups.items(), key=lambda kv: (-kv[0][2], kv[0][1])):
        probe = None
        if hi - lo > .1 and r > .4:
            try:
                probe = axis_cyl(centre, axis, r * .85, lo + .05, hi - .05)
            except RuntimeError:
                _flush()
        users = []
        if probe:
            for b in others:
                if not probe.boundingBox.intersects(b.boundingBox):
                    continue
                v, _ = s.common_volume(probe, s.tbm().copy(b))
                if v > .02:
                    users.append(b.name)
        rows.append({"axis": "XYZ"[[i for i in range(3) if axis[i]][0]], "at": [c for c in centre],
                     "r": r, "span": [round(lo, 2), round(hi, 2)], "users": users})
    return rows


def _robust(a, make_b, kind, factors=(1.0, 1.0113, .9871, 1.0231, .9769)):
    """Boolean on a copy of a, retrying with slightly perturbed operands (coincident-face failures)."""
    s = load("pancake_paths_study")
    kinds = {"join": adsk.fusion.BooleanTypes.UnionBooleanType,
             "cut": adsk.fusion.BooleanTypes.DifferenceBooleanType,
             "common": adsk.fusion.BooleanTypes.IntersectionBooleanType}
    for f in factors:
        try:
            c = s.tbm().copy(a)
            ok = s.tbm().booleanOperation(c, make_b(f), kinds[kind])
            adsk.fusion.TemporaryBRepManager.get()  # deferred kernel errors surface here
            c.lumps.count
            if ok:
                return c
        except RuntimeError:
            _flush()
            continue
    return None


def _flush():
    for _ in range(200):
        try:
            adsk.fusion.TemporaryBRepManager.get()
            return True
        except RuntimeError:
            continue
    return False


def opening_thin(shape, r, axes="xyz", steps=(-1.0, -.5, .5, 1.0)):
    """Material whose chord along X, Y or Z is shorter than ~2r (1D morphological opening per axis)."""
    s = load("pancake_paths_study")
    r = r * 1.00373
    thin_parts, failed = [], []
    _flush()
    for axis in axes:
        def shift(sh, t):
            return translated(sh, **{"d" + axis: t})
        eroded, empty = s.tbm().copy(shape), False
        for t in steps:
            nxt = _robust(eroded, lambda f, t=t: shift(shape, t * r * f), "common")
            if nxt is None:
                failed.append(axis + " erode %.2f" % t)
                continue
            eroded = nxt
            if not eroded.lumps.count:
                empty = True
                break
        if empty:
            thin = s.tbm().copy(shape)
        else:
            dilated, broken = s.tbm().copy(eroded), False
            for t in steps:
                nxt = _robust(dilated, lambda f, t=t: shift(eroded, t * r * f), "join")
                if nxt is None:
                    failed.append(axis + " dilate %.2f" % t)
                    broken = True  # an incomplete dilation would over-report thin material: skip this axis
                    break
                dilated = nxt
            if broken:
                continue
            thin = _robust(shape, lambda f: dilated, "cut", factors=(1.0,))
            if thin is None:
                failed.append(axis + " diff")
                continue
        if thin.lumps.count:
            thin_parts.append(thin)
    STATE["thin_failed"] = failed
    if not thin_parts:
        return None
    out = thin_parts[0]
    for part in thin_parts[1:]:
        nxt = _robust(out, lambda f, part=part: part, "join", factors=(1.0,))
        if nxt is not None:
            out = nxt
    return out


def thin_report(shape, r, min_volume=.3):
    thin = opening_thin(shape, r)
    rows = []
    if thin is None:
        return thin, rows
    for i in range(thin.lumps.count):
        lump = thin.lumps.item(i)
        v = lump.volume * 1000
        if v < min_volume:
            continue
        b = lump.boundingBox
        rows.append([round(v, 1), round(2 * lump.volume / lump.area * 10, 2)] +
                    [round(x * 10, 1) for x in (b.minPoint.x, b.maxPoint.x, b.minPoint.y, b.maxPoint.y,
                                                b.minPoint.z, b.maxPoint.z)])
    rows.sort(key=lambda row: -row[0])
    return thin, rows


def ray_thin(app, key, h=.5, t_flag=1.2, t_review=1.6, max_markers=1500, body=None):
    """Wall thickness by ray casting along X, Y and Z (no booleans). Returns clusters of thin samples."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    if body is None:
        by = {b.name: b for b in s.proxies(root)}
        body = by[PARTS[key]] if key in PARTS else by[key]
    group = s.add_group(root, "TEMP ray " + key, [(s.tbm().copy(body), "ray target", None)])
    comp = group.component
    samples = []
    try:
        bb = body.boundingBox
        lo = [bb.minPoint.x * 10, bb.minPoint.y * 10, bb.minPoint.z * 10]
        hi = [bb.maxPoint.x * 10, bb.maxPoint.y * 10, bb.maxPoint.z * 10]
        for a in range(3):
            u, v = [i for i in range(3) if i != a]
            d = [0.0, 0.0, 0.0]
            d[a] = 1.0
            direction = adsk.core.Vector3D.create(*d)
            cu = lo[u] + .0137
            while cu < hi[u]:
                cv = lo[v] + .0291
                while cv < hi[v]:
                    o = [0.0, 0.0, 0.0]
                    o[a], o[u], o[v] = lo[a] - 1.0, cu, cv
                    hits = adsk.core.ObjectCollection.create()
                    faces = comp.findBRepUsingRay(adsk.core.Point3D.create(o[0] / 10, o[1] / 10, o[2] / 10),
                                                  direction, adsk.fusion.BRepEntityTypes.BRepFaceEntityType,
                                                  -1.0, False, hits)
                    if hits.count >= 2:
                        pts = []
                        for i in range(hits.count):
                            p = hits.item(i)
                            pts.append(([p.x, p.y, p.z][a] * 10, faces.item(i) if faces and i < faces.count else None, p))
                        pts.sort(key=lambda q: q[0])
                        merged = []
                        for q in pts:
                            if merged and abs(q[0] - merged[-1][0]) < 1e-3:
                                continue
                            merged.append(q)
                        if len(merged) % 2 == 0:
                            for i in range(0, len(merged), 2):
                                length = merged[i + 1][0] - merged[i][0]
                                if length >= t_review / .35 or length <= 1e-3:
                                    continue
                                cosines = []
                                for q in (merged[i], merged[i + 1]):
                                    if q[1] is None:
                                        continue
                                    ok, n = q[1].evaluator.getNormalAtPoint(q[2])
                                    if ok:
                                        cosines.append(abs(n.x * d[0] + n.y * d[1] + n.z * d[2]))
                                if not cosines or min(cosines) < .35:
                                    continue
                                t = length * min(cosines)
                                if t < t_review:
                                    mid = list(o)
                                    mid[a] = (merged[i][0] + merged[i + 1][0]) / 2
                                    samples.append(("XYZ"[a], round(mid[0], 2), round(mid[1], 2), round(mid[2], 2),
                                                    round(t, 2)))
                    cv += h
                cu += h
    finally:
        group.deleteMe()
    # cluster samples within 1.2 mm of each other
    parent = list(range(len(samples)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    cells = {}
    for i, smp in enumerate(samples):
        key3 = (int(smp[1] // 1.2), int(smp[2] // 1.2), int(smp[3] // 1.2))
        cells.setdefault(key3, []).append(i)
    for (cx, cy, cz), members in cells.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in cells.get((cx + dx, cy + dy, cz + dz), ()):
                        for i in members:
                            if abs(samples[i][1] - samples[j][1]) <= 1.2 and abs(samples[i][2] - samples[j][2]) <= 1.2 \
                                    and abs(samples[i][3] - samples[j][3]) <= 1.2:
                                ri, rj = find(i), find(j)
                                if ri != rj:
                                    parent[ri] = rj
    clusters = {}
    for i in range(len(samples)):
        clusters.setdefault(find(i), []).append(samples[i])
    rows = []
    for members in clusters.values():
        ts = sorted(m_[4] for m_ in members)
        xs, ys, zs = [m_[1] for m_ in members], [m_[2] for m_ in members], [m_[3] for m_ in members]
        rows.append({"n": len(members), "t_min": ts[0], "t_med": ts[len(ts) // 2],
                     "flag": ts[len(ts) // 2] < t_flag, "axes": "".join(sorted(set(m_[0] for m_ in members))),
                     "bbox": [round(min(xs), 1), round(max(xs), 1), round(min(ys), 1), round(max(ys), 1),
                              round(min(zs), 1), round(max(zs), 1)]})
    rows.sort(key=lambda r_: (not r_["flag"], -r_["n"]))
    STATE.setdefault("thin_samples", {})[key] = samples[:max_markers * 4]
    return rows


def marker_shot(app, name, key, samples, eye, target, extents, t_flag=1.2, others=(), opacity=.35):
    """The part (translucent) with thin samples as small spheres: magenta < t_flag, amber up to review."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    body = by[PARTS[key]] if key in PARTS else by[key]
    hot = marker_appearance(design, "AHGmin colour thin", (255, 40, 200))
    warm = marker_appearance(design, "AHGmin colour review", (255, 170, 0))
    items = [(s.tbm().copy(body), body.name, body.appearance)]
    for n in others:
        items.append((s.tbm().copy(by[n]), n, by[n].appearance))
    step = max(1, -(-len(samples) // 350))
    for smp in samples[::step]:
        sphere = s.tbm().createSphere(adsk.core.Point3D.create(smp[1] / 10, smp[2] / 10, smp[3] / 10), .035)
        items.append((sphere, "thin %.2f" % smp[4], hot if smp[4] < t_flag else warm))
    states = [(occ, occ.isLightBulbOn) for occ in root.occurrences]
    group = s.add_group(root, "TEMP thin markers", items)
    try:
        group.component.bRepBodies.item(0).opacity = opacity
        for occ, _ in states:
            occ.isLightBulbOn = False
        return camera_shot(app, name, eye, target, (0, 0, 1), extents, (1600, 1200))
    finally:
        group.deleteMe()
        for occ, state in states:
            occ.isLightBulbOn = state


# =============================================================================================
# v5 cleanup (user: clean the four printed parts - thin walls, useless geometry)
# =============================================================================================
P02_Y = (-13.7, 0.3)
EAR_SEAT_Y = -4.1               # MG90S ear front face (clamped against the P02 shoulder)
CASE_FRONT_Y = -2.2
NUT_POCKET_Y = (-2.1, 0.4)      # M2 nut pockets open to the P02 front face (nuts trapped by P01)
NUT_SHIFT = 0.5
LEAD_DEPTH_Y = -10.1            # XH plug notch depth from the P02 rear face
SHCS_AXES = {"0": (17.25, 23.72), "1": (-17.0, 40.0)}
HEAD_SEAT_Y = -10.5             # M3x16 SHCS: 3.2 mm counterbore in P02, tip at Y 5.5 in a P01 insert
FRAME_AXIS = (18.1, 41.72)
REAR_FILL_LIMITS = {"x_max": 13.0, "z_min": 28.0}
SWEEP_POSES = tuple(OPEN_DEG * i / 8 for i in range(9))


def corner_fillets(body, x0, x1, z0, z1, rmax=5.0):
    """Convex Y-axis fillets at the outline corners of a plate-like printed part."""
    out = set()
    for f in body.faces:
        g = f.geometry
        if not isinstance(g, adsk.core.Cylinder) or abs(abs(g.axis.y) - 1) > 1e-3 or g.radius * 10 > rmax:
            continue
        cx, cz, r = g.origin.x * 10, g.origin.z * 10, g.radius * 10
        if min(abs(cx - r - x0), abs(cx + r - x1)) < .05 and min(abs(cz - r - z0), abs(cz + r - z1)) < .05:
            out.add((round(cx, 3), round(cz, 3), round(r, 3)))
    return sorted(out)


def rounded_box(x0, x1, y0, y1, z0, z1, corners):
    s = load("pancake_paths_study")
    shape = s.box(x0, x1, y0, y1, z0, z1)
    for cx, cz, r in corners:
        kx = x0 if cx < (x0 + x1) / 2 else x1
        kz = z0 if cz < (z0 + z1) / 2 else z1
        bounds = (min(kx, cx), max(kx, cx), y0 - .1, y1 + .1, min(kz, cz), max(kz, cz))
        s.op(shape, s.box(*bounds), "cut")
        quarter = s.cyl(cx, cz, y0, y1, r)
        s.op(quarter, s.box(*bounds), "common")
        s.op(shape, quarter, "join")
    return shape


def grown(shape, g, diagonal=True):
    dirs = [(g, 0), (-g, 0), (0, g), (0, -g)]
    if diagonal:
        h = g * .7071
        dirs += [(h, h), (h, -h), (-h, h), (-h, -h)]
    return union_all([shape] + [translated(shape, dx=dx, dz=dz) for dx, dz in dirs])


def arm_sweep(shape, grow=.45):
    """Region a piece of the arm occupies over its stroke (9 poses), grown in X/Z for clearance."""
    Mv = STATE["Mv"]
    return grown(union_all([rotated(shape, Mv, d) for d in SWEEP_POSES]), grow)


def cam_axis_in_arm(d):
    Mv, C = STATE["Mv"], STATE["C"]
    mtx = adsk.core.Matrix3D.create()
    mtx.setToRotation(math.radians(-d), adsk.core.Vector3D.create(0, 1, 0),
                      adsk.core.Point3D.create(Mv[0] / 10, 0, Mv[1] / 10))
    p = adsk.core.Point3D.create(C[0] / 10, 0, C[1] / 10)
    p.transformBy(mtx)
    return p.x * 10, p.z * 10


def cam_obround(y0, y1, r):
    """Cam clearance in the arm frame: the hull of the cam cylinder over the arm stroke."""
    s, a = load("pancake_paths_study"), load("ahg_placement")
    p0, p1 = cam_axis_in_arm(0.0), cam_axis_in_arm(OPEN_DEG)
    shape = union_all([s.cyl(p0[0], p0[1], y0, y1, r), s.cyl(p1[0], p1[1], y0, y1, r)])
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dz)
    s.op(shape, a.obb((p0[0] + p1[0]) / 2, (y0 + y1) / 2, (p0[1] + p1[1]) / 2, (dx / length, dz / length),
                      length, y1 - y0, 2 * r), "join")
    return shape


def v5_arm(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    if STATE.get("v5_arm"):
        raise RuntimeError("v5 arm already applied")
    Fo = STATE["Fo"]
    proxy = by[PARTS["P04"]]
    arm = s.tbm().copy(proxy)
    v0 = arm.volume
    lim = REAR_FILL_LIMITS
    # Rear plate behind the follower (all arm material behind Y 6.0, plus 6.0-6.8 inside the v3 cut box).
    for box in ((lim["x_max"], 40, 1.0, 5.99, 15.0, 60.0), (lim["x_max"], 22.0, 5.95, 6.79, 24.0, 52.0),
                (-30, 40, 1.0, 5.99, 15.0, lim["z_min"]), (-7.0, 22.0, 5.95, 6.79, 24.0, lim["z_min"])):
        s.op(arm, s.box(*box), "cut")
    trimmed = (v0 - arm.volume) * 1000
    clear = union_all([cam_obround(1.9, 4.95, NECK_R + .5), cam_obround(4.4, 9.6, LOBE_SWEEP_R + .1),
                       cam_obround(9.55, 14.0, 6.6)])
    v1 = arm.volume
    s.op(arm, s.tbm().copy(clear), "cut")
    smoothed = (v1 - arm.volume) * 1000
    plug = s.cyl(Fo[0], Fo[1], 9.6, 10.4, 2.45)
    s.op(plug, s.cyl(Fo[0], Fo[1], 9.0, 11.0, 1.5), "cut")
    s.op(plug, s.tbm().copy(clear), "cut")
    v2 = arm.volume
    s.op(arm, plug, "join")
    report = {"rear_fill_trim_mm3": round(trimmed, 1), "cam_slot_extra_cut_mm3": round(smoothed, 1),
              "insert_pocket_fill_mm3": round((arm.volume - v2) * 1000, 1), "lumps": arm.lumps.count,
              "volume_cm3": round(arm.volume, 3), "cam_axis_in_arm": [cam_axis_in_arm(0.0), cam_axis_in_arm(OPEN_DEG)]}
    replace(proxy, arm)
    STATE["v5_arm"] = report
    (OUT / "v5_arm.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def arm_regions(arm):
    """Pieces of the (cleaned) arm that the housings must pocket: rear plate, front column, lower web."""
    s = load("pancake_paths_study")
    rear = s.tbm().copy(arm)
    s.op(rear, s.box(-30, 40, 0.0, 5.99, 20.0, 60.0), "common")  # rear plate only (lever starts at Y 6.0)
    front = s.tbm().copy(arm)
    s.op(front, s.box(-30, 40, 10.95, 14.0, 37.0, 80.0), "common")
    bottom = s.tbm().copy(arm)
    s.op(bottom, s.box(1.5, 20.0, 6.75, 11.15, -14.0, 4.5), "common")
    return rear, front, bottom


def rear_zone(rear):
    """One clean box pocket covering the rear plate over the full stroke (no stepped sweep faces)."""
    s = load("pancake_paths_study")
    Mv = STATE["Mv"]
    lo, hi = [1e9, 1e9], [-1e9, -1e9]
    for d in SWEEP_POSES:
        b = rotated(rear, Mv, d).boundingBox
        lo = [min(lo[0], b.minPoint.x * 10), min(lo[1], b.minPoint.z * 10)]
        hi = [max(hi[0], b.maxPoint.x * 10), max(hi[1], b.maxPoint.z * 10)]
    rb = rear.boundingBox
    box = (lo[0] - .5, hi[0] + .5, rb.minPoint.y * 10 - .45, 7.45, lo[1] - .5, hi[1] + .5)  # plate reaches Y 7.0
    return s.box(*box), [round(v, 2) for v in box]


def servo_frame(by):
    s = load("pancake_paths_study")
    C = STATE["C"]
    sb = by["HOBBY_SERVO_ENVELOPE"].boundingBox
    case_x = (C[0] - 16.95 - .3, C[0] + 5.85 + .3)
    case_z = (sb.minPoint.z * 10 - .3, sb.maxPoint.z * 10 + .3)
    ear_x = (sb.minPoint.x * 10 - .3, sb.maxPoint.x * 10 + .3)
    screws = [s.centre(by[n]) for n in ("MG90S_M2x6_SERVO_left", "MG90S_M2x6_SERVO_right")]
    return case_x, case_z, ear_x, screws


def motor_axis(by):
    s = load("pancake_paths_study")
    F = s.centre(by["AXLE_4x25_fixed"])
    return (F[0] + 12.1 * math.cos(math.radians(PHI)), F[1] + 12.1 * math.sin(math.radians(PHI)))


def screw_shape(x, z, head_y, head_r, head_h, tip_y, r=1.5):
    """Y-axis screw: head from head_y away from the tip, shank to tip_y."""
    s = load("pancake_paths_study")
    sign = 1 if tip_y > head_y else -1
    head = s.cyl(x, z, min(head_y, head_y - sign * head_h), max(head_y, head_y - sign * head_h), head_r)
    s.op(head, s.cyl(x, z, min(head_y, tip_y), max(head_y, tip_y), r), "join")
    return head


def v5_p02(app):
    """Motor/servo plate rebuilt from intent: one clean 14 mm plate, rear-loaded servo, no leftovers."""
    s, a = load("pancake_paths_study"), load("ahg_placement")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    if "SPACER_M3x16_SHCS_0" in by:
        raise RuntimeError("v5 P02 already applied")
    C = STATE["C"]
    M = motor_axis(by)
    ears = STATE["ears"]
    case_x, case_z, ear_x, screws = servo_frame(by)
    y0, y1 = P02_Y
    old = by[PARTS["P02"]]
    corners = corner_fillets(old, -22.5, 22.5, -17.78, 62.22)
    p02 = rounded_box(-22.5, 22.5, y0, y1, -17.78, 62.22, corners)
    t = math.radians(THETA)
    lead = (-math.cos(t), math.sin(t))
    cuts = [s.cyl(M[0], M[1], y0 - 1, y1 + 1, 18.55),
            a.obb(M[0] + lead[0] * 26, (y0 - 1 + LEAD_DEPTH_Y) / 2, M[1] + lead[1] * 26, lead, 20.0,
                  LEAD_DEPTH_Y - (y0 - 1), 12.0)]  # XH plug and leads
    cuts += [s.cyl(ex, ez, y0 - 1, y1 + 1, 1.7) for ex, ez in ears]
    # Servo: ears drop in from the rear onto a 2 mm shoulder; right ear well opens through the side.
    cuts.append(s.box(ear_x[0], 23.5, y0 - 1, EAR_SEAT_Y, case_z[0], case_z[1]))
    cuts.append(s.box(case_x[0], case_x[1], EAR_SEAT_Y - .1, CASE_FRONT_Y + .3, case_z[0], case_z[1]))
    cuts.append(s.cyl(C[0], C[1], CASE_FRONT_Y - .3, y1 + 1, 7.6))
    for sx, sz in screws:
        cuts.append(s.cyl(sx, sz, EAR_SEAT_Y - .1, y1 + 1, 1.2))
        cuts.append(s.box(sx - 2.25, sx + 2.25, NUT_POCKET_Y[0], NUT_POCKET_Y[1], sz - 2.45, sz + 2.45))
    for fx, fz in SHCS_AXES.values():
        cuts.append(s.cyl(fx, fz, y0 - 1, HEAD_SEAT_Y, 3.2))
        cuts.append(s.cyl(fx, fz, HEAD_SEAT_Y - .1, y1 + 1, 1.7))
    cuts.append(s.cyl(FRAME_AXIS[0], FRAME_AXIS[1], -2.5, y1 + 1, 1.75))
    cuts.append(s.box(-2.35, 2.35, -0.9, y1 + 1, -16.1, -10.45))
    for c in cuts:
        s.op(p02, c, "cut")

    hw = {}
    for n in ("MG90S_M2_NUT_left", "MG90S_M2_NUT_right"):
        hw[n] = (translated(by[n], dy=NUT_SHIFT), None)
    for k, (fx, fz) in SHCS_AXES.items():
        hw["SPACER_M3x10_SHCS_" + k] = (screw_shape(fx, fz, HEAD_SEAT_Y, 2.75, 3.0, HEAD_SEAT_Y + 16.0),
                                       "SPACER_M3x16_SHCS_" + k)
        hw["SPACER_M3x10_HEATSET_" + k] = (s.cyl(fx, fz, .3, 4.3, 2.3), "SPACER_M3_HEATSET_" + k)
    for i in range(2):
        name = "M3x10 SHCS motor ear %d (rear entry)" % i
        cx, cz = s.centre(by[name])
        ex, ez = min(ears, key=lambda e: math.hypot(e[0] - cx, e[1] - cz))
        hw[name] = (screw_shape(ex, ez, y0, 2.85, 1.65, y0 + 18.0), "M3x18 ISO7380 motor ear %d (rear entry)" % i)
    fb = by["FRAME_REAR_LOADED_M3x40"].boundingBox
    head_front = fb.maxPoint.y * 10
    hw["FRAME_REAR_LOADED_M3x40"] = (screw_shape(FRAME_AXIS[0], FRAME_AXIS[1], head_front - 1.65, 2.85, 1.65,
                                                 head_front - 1.65 - 30.0), "FRAME_M3x30_into_P01_insert")
    hw["FRAME_REAR_LOADED_M3_HEATSET"] = (s.cyl(FRAME_AXIS[0], FRAME_AXIS[1], .3, 4.3, 2.3), "FRAME_M3_HEATSET_in_P01")

    v_old = old.volume
    replace(old, p02, None, "P02 Motor and servo plate - v5 clean")
    for n, (shape, new) in hw.items():
        replace(by[n], shape, new, new)
    report = {"corners": corners, "lumps": p02.lumps.count, "faces": p02.faces.count,
              "volume_cm3": [round(v_old, 2), round(p02.volume, 2)], "case_x": case_x, "case_z": case_z,
              "ear_x": ear_x, "servo_screws": screws, "hardware": {n: v[1] for n, v in hw.items()}}
    STATE["v5_p02"] = report
    (OUT / "v5_p02.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def p01_keepouts(by, arm):
    """Everything that must stay open in P01's rear 6 mm (Y 0.3..6.0) - re-cut after the refill."""
    s, a = load("pancake_paths_study"), load("ahg_placement")
    C, M = STATE["C"], motor_axis(by)
    keep = {"stator": s.cyl(M[0], M[1], .2, 1.3, 18.55),
            "flange": a.flange(M[0], M[1], 1.3, 4.35, THETA, .2),
            "plate": a.flange(M[0], M[1], 4.25, 6.4, THETA, .2),
            "pilot": s.cyl(M[0], M[1], 4.2, 6.4, 8.55),
            "pinion": s.cyl(M[0], M[1], 5.7, 6.4, 3.5),
            "horn_neck": s.cyl(C[0], C[1], .2, 5.0, 7.7),
            "lobe": s.cyl(C[0], C[1], 4.4, 6.4, 9.0),
            "frame_insert": s.cyl(FRAME_AXIS[0], FRAME_AXIS[1], .2, 4.6, 2.0),
            "frame_clear": s.cyl(FRAME_AXIS[0], FRAME_AXIS[1], 4.5, 6.4, 1.7),
            "hall": s.box(-2.35, 2.35, .2, 6.4, -16.1, -10.45)}
    for i, (ex, ez) in enumerate(STATE["ears"]):
        keep["ear_screw_%d" % i] = s.cyl(ex, ez, .2, 1.4, 1.7)
    for k, (fx, fz) in SHCS_AXES.items():
        keep["shcs_insert_" + k] = s.cyl(fx, fz, .2, 6.1, 2.0)
    p03 = s.tbm().copy(by[PARTS["P03"]])
    s.op(p03, s.box(-30, 30, 0.0, 6.6, -30, 70), "common")      # P03 tongues that reach into P01's top
    keep["p03_tongues"] = union_all([grown(p03, .23), translated(p03, dy=-.23)])
    rear, front, bottom = arm_regions(arm)
    zone, zone_box = rear_zone(rear)
    keep["arm_rear_zone"] = zone
    STATE["v5_zone_box"] = zone_box
    return keep, (rear, front, bottom)


def cut_each(target, shapes, log):
    """Cut shapes one at a time; nudge a failing tool by <0.01 mm (coincident-face kernel failures)."""
    for name, shape in shapes:
        nxt = _robust(target, lambda f, sh=shape: translated(sh, dx=(f - 1) * .5, dz=(f - 1) * .3), "cut")
        if nxt is None:
            log.append(name)
            continue
        target = nxt
    return target


def v5_p01(app, dry=True):
    """Refill P01's rear 6 mm from a clean block minus keep-outs; re-cut the arm zone, sweeps and new holes."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    old = by[PARTS["P01"]]
    arm = s.tbm().copy(by[PARTS["P04"]])
    corners = [c for c in corner_fillets(old, -22.5, 22.5, -57.28, 62.22) if c[1] > 0]
    slab = rounded_box(-22.5, 22.5, .3, 6.0, -18.0, 62.22, corners)
    keep, pieces = p01_keepouts(by, arm)
    failed = []
    fill = cut_each(slab, list(keep.items()), failed)
    rear, front, bottom = pieces
    new_holes = [(k, keep[k]) for k in ("shcs_insert_0", "shcs_insert_1", "frame_insert", "frame_clear")]
    sweeps = [("front_sweep", arm_sweep(union_all([front, translated(front, dy=.4)]))),
              ("bottom_sweep", arm_sweep(union_all([bottom, translated(bottom, dy=-.4)])))]
    STATE["v5_sweeps"] = sweeps
    if dry:
        u = _robust(fill, lambda f: translated(old, dx=(f - 1) * .5), "cut") or fill
        rows = []
        for i in range(u.lumps.count):
            lump = u.lumps.item(i)
            v = lump.volume * 1000
            if v < .5:
                continue
            b = lump.boundingBox
            rows.append([round(v, 1)] + [round(x * 10, 1) for x in (b.minPoint.x, b.maxPoint.x, b.minPoint.y,
                                                                   b.maxPoint.y, b.minPoint.z, b.maxPoint.z)])
        rows.sort(key=lambda r: -r[0])
        STATE["v5_p01_fill_preview"] = u
        return {"corners": corners, "zone_box": STATE["v5_zone_box"], "fill_lumps": rows, "failed": failed,
                "fill_total_mm3": round(sum(r[0] for r in rows), 1)}
    p01 = _robust(old, lambda f: translated(fill, dx=(f - 1) * .5), "join")
    if p01 is None:
        raise RuntimeError("join of the refill failed")
    p01 = cut_each(p01, new_holes + [("arm_rear_zone", keep["arm_rear_zone"])] + sweeps, failed)
    big = max((p01.lumps.item(i) for i in range(p01.lumps.count)), key=lambda l: l.volume)
    dropped = sum(p01.lumps.item(i).volume for i in range(p01.lumps.count)) - big.volume
    clean = s.tbm().copy(big)
    report = {"volume_cm3": [round(old.volume, 2), round(clean.volume, 2)], "lumps_before_drop": p01.lumps.count,
              "dropped_mm3": round(dropped * 1000, 2), "faces": [old.faces.count, clean.faces.count],
              "zone_box": STATE["v5_zone_box"], "failed": failed}
    replace(old, clean, None, "P01 Backplate - v5 clean")
    STATE["v5_p01"] = report
    (OUT / "v5_p01.json").write_text(json.dumps(report, indent=2) + "\n")
    return report

def v5_fix2(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    if STATE.get("v5_fix2"):
        raise RuntimeError("v5 fix2 already applied")
    C, Fo, Mv = STATE["C"], STATE["Fo"], STATE["Mv"]
    F, M = s.centre(by["AXLE_4x25_fixed"]), motor_axis(by)
    rep, failed = {}, []
    # Arm: the follower pin gets full support through the front cheek (old r2.25 insert hole ran to Y 13).
    arm_p = by[PARTS["P04"]]
    arm = s.tbm().copy(arm_p)
    plug = s.cyl(Fo[0], Fo[1], 10.3, 13.0, 2.45)
    s.op(plug, s.cyl(Fo[0], Fo[1], 9.0, 14.0, 1.5), "cut")
    s.op(plug, cam_obround(9.55, 14.0, 6.6), "cut")
    v = arm.volume
    s.op(arm, plug, "join")
    rep["arm_pin_plug_mm3"] = round((arm.volume - v) * 1000, 1)
    rep["arm_lumps"] = arm.lumps.count
    # P01: refill the original NEMA14 20T pinion relief, clean step at the horn, shallower insert holes,
    # absorb the slot left by P03's 0.6 mm fin.
    p01_p = by[PARTS["P01"]]
    p01 = s.tbm().copy(p01_p)
    v = p01.volume
    low = s.tbm().copy(arm)
    s.op(low, s.box(-10, 15, 6.0, 11.6, -8.0, 8.0), "common")
    old20 = s.cyl(-1.5, .887, 6.35, 10.7, 5.95)
    old20 = cut_each(old20, [("band_F", s.cyl(F[0], F[1], 6.0, 11.6, 10.4)),
                             ("band_Mv", s.cyl(Mv[0], Mv[1], 6.0, 11.6, 10.4)),
                             ("pinion", s.cyl(M[0], M[1], 6.0, 11.6, 3.65)),
                             ("arm_low_sweep", arm_sweep(low))], failed)
    joins = [("old20_fill", old20)]
    for k, (fx, fz) in SHCS_AXES.items():
        joins.append(("insert_floor_" + k, s.cyl(fx, fz, 4.55, 6.15, 2.05)))
    joins.append(("fin_slot", s.box(-11.25, -9.9, .3, 5.95, 53.1, 58.55)))
    for name, shape in joins:
        nxt = _robust(p01, lambda f, sh=shape: translated(sh, dx=(f - 1) * .5), "join")
        if nxt is None:
            failed.append(name)
        else:
            p01 = nxt
    p01 = cut_each(p01, [("horn_step", s.cyl(C[0], C[1], 2.7, 4.5, 9.45))], failed)
    rep["p01_delta_mm3"] = round((p01.volume - v) * 1000, 1)
    rep["p01_lumps"] = p01.lumps.count
    # P03: restore the top wall I thinned (0.95 -> 2.2 mm), drop the 0.6 mm fin, smooth arm pockets.
    p03_p = by[PARTS["P03"]]
    p03 = s.tbm().copy(p03_p)
    v = p03.volume
    nxt = _robust(p03, lambda f: translated(s.box(-6.5, 6.5, 14.3, 15.6, 49.0, 62.22), dx=(f - 1) * .5), "join")
    if nxt is None:
        failed.append("p03_top_wall")
    else:
        p03 = nxt
    p03 = cut_each(p03, [("p03_fin", s.box(-11.05, -10.15, 2.9, 6.6, 53.1, 58.5))] + list(STATE["v5_sweeps"]), failed)
    rep["p03_delta_mm3"] = round((p03.volume - v) * 1000, 1)
    rep["p03_lumps"] = p03.lumps.count
    for name, shape in (("arm", arm), ("p01", p01), ("p03", p03)):
        if shape.lumps.count > 1:
            big = max((shape.lumps.item(i) for i in range(shape.lumps.count)), key=lambda l: l.volume)
            rep[name + "_dropped_mm3"] = round((shape.volume - big.volume) * 1000, 2)
    def biggest(shape):
        return s.tbm().copy(max((shape.lumps.item(i) for i in range(shape.lumps.count)), key=lambda l: l.volume))
    replace(arm_p, biggest(arm))
    replace(p01_p, biggest(p01))
    replace(p03_p, biggest(p03), None, "P03 Front case - v5 clean")
    for k, (fx, fz) in SHCS_AXES.items():
        replace(by["SPACER_M3x16_SHCS_" + k], screw_shape(fx, fz, HEAD_SEAT_Y, 2.75, 3.0, HEAD_SEAT_Y + 14.0),
                "SPACER_M3x14_SHCS_" + k, "SPACER_M3x14_SHCS_" + k)
    rep["failed"] = failed
    STATE["v5_fix2"] = rep
    (OUT / "v5_fix2.json").write_text(json.dumps(rep, indent=2) + "\n")
    return rep



def v5_desliver(app, keys=("P01", "P02", "P04", "P03"), r=.3):
    """Remove only features thinner than ~2r (slivers, knife-edge cusps, sub-layer skins) from each part."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    rep = {}
    if "P01" in keys and not STATE.get("v5_neck"):
        M = motor_axis(by)
        Mv = STATE["Mv"]
        p01 = s.tbm().copy(by[PARTS["P01"]])
        neck = cut_each(p01, [("pinion_band_neck", s.box(-1.5, 2.5, 6.45, 11.45, 6.0, 9.6))], [])
        replace(by[PARTS["P01"]], neck)
        STATE["v5_neck"] = True
        by = {b.name: b for b in s.proxies(design.rootComponent)}
    for key in keys:
        _flush()
        body = by[PARTS[key]]
        shape = s.tbm().copy(body)
        thin = opening_thin(shape, r)
        failed = list(STATE.get("thin_failed", []))
        if thin is None or not thin.lumps.count:
            rep[key] = {"removed_mm3": 0.0, "failed": failed}
            continue
        out = _robust(shape, lambda f: thin, "cut", factors=(1.0,))
        if out is None:
            rep[key] = {"removed_mm3": None, "failed": failed + ["final cut"]}
            continue
        big = max((out.lumps.item(i) for i in range(out.lumps.count)), key=lambda l: l.volume)
        removed = (shape.volume - big.volume) * 1000
        rep[key] = {"removed_mm3": round(removed, 2), "lumps": out.lumps.count, "failed": failed}
        replace(body, s.tbm().copy(big))
    STATE["v5_desliver"] = rep
    (OUT / "v5_desliver.json").write_text(json.dumps(rep, indent=2) + "\n")
    return rep


# =============================================================================================
# v6 audit: bearing seats, contacts, range of motion, assembly paths, unneeded voids
# =============================================================================================
PRINTED = {"P01": "PRINT_motor_mount", "P02": "PRINT_REAR_MOTOR_SERVO_SPACER",
           "P03": "PRINT_000_outer_shell_of_extruder_1", "P04": "PRINT_carrier_box_left",
           "P05": "PRINT_DIRECT_CAM", "P19": "PRINT_AHG_PIN_PLATE"}
SUPPORTED = ("bearing", "MR74", "6700", "MF63", "623", "needle", "AXLE", "SHAFT", "PIN", "INSERT", "HEATSET",
             "SPRING_PRELOAD", "pinion", "OEM_SERVO", "HOBBY_SERVO", "AHG ")


def mind(a, b):
    """Minimum distance in mm between two bodies (0 when touching or overlapping)."""
    return app_ref().measureManager.measureMinimumDistance(a, b).value * 10


def app_ref():
    return adsk.core.Application.get()


def bb_gap(a, b):
    """Lower bound of the distance between two bounding boxes (mm)."""
    pa, pb = a.boundingBox, b.boundingBox
    gaps = []
    for lo1, hi1, lo2, hi2 in ((pa.minPoint.x, pa.maxPoint.x, pb.minPoint.x, pb.maxPoint.x),
                               (pa.minPoint.y, pa.maxPoint.y, pb.minPoint.y, pb.maxPoint.y),
                               (pa.minPoint.z, pa.maxPoint.z, pb.minPoint.z, pb.maxPoint.z)):
        gaps.append(max(0.0, lo2 - hi1, lo1 - hi2) * 10)
    return math.sqrt(sum(g * g for g in gaps))


def audit_contacts(app, tol=.05):
    """For every supported/hardware body: which printed parts touch it (gap <= tol)."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    leftovers = set(STATE.get("leftovers", ()))
    bodies = [b for b in s.proxies(design.rootComponent) if b.name not in leftovers
              and not b.name.startswith(CART_CONTEXT_PREFIXES)]
    by = {b.name: b for b in bodies}
    parts = {k: by[v] for k, v in PRINTED.items() if v in by}
    rows = []
    for b in bodies:
        if b.name in PRINTED.values() or not any(t.lower() in b.name.lower() for t in SUPPORTED):
            continue
        touch = []
        for k, p in parts.items():
            if bb_gap(b, p) > 1.0:
                continue
            d = mind(b, p)
            if d <= 1.0:
                touch.append([k, round(d, 3)])
        bb = b.boundingBox
        rows.append({"name": b.name, "touch": sorted(touch, key=lambda t: t[1]),
                     "bb": [round(v * 10, 2) for v in (bb.minPoint.x, bb.maxPoint.x, bb.minPoint.y, bb.maxPoint.y,
                                                       bb.minPoint.z, bb.maxPoint.z)]})
    pairs = []
    keys = sorted(parts)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if bb_gap(parts[a], parts[b]) > 1.0:
                continue
            r = app.measureManager.measureMinimumDistance(parts[a], parts[b])
            pairs.append([a, b, round(r.value * 10, 3),
                          [round(v * 10, 2) for v in (r.positionOne.x, r.positionOne.y, r.positionOne.z)]])
    out = {"supported": rows, "part_pairs": pairs}
    (OUT / "v6_contacts.json").write_text(json.dumps(out, indent=1))
    return out


def seat_walls(app, body_name, part_key, n=24, y=None):
    """Radial wall around a Y-axis bearing/pin seat: distance from the body OD to the part's outer surface."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    b = by[body_name]
    part = by[PRINTED[part_key]]
    bb = b.boundingBox
    cx, cz = (bb.minPoint.x + bb.maxPoint.x) * 5, (bb.minPoint.z + bb.maxPoint.z) * 5
    r_od = (bb.maxPoint.x - bb.minPoint.x) * 5
    ys = [y] if y is not None else [bb.minPoint.y * 10 + .3, (bb.minPoint.y + bb.maxPoint.y) * 5, bb.maxPoint.y * 10 - .3]
    group = s.add_group(root, "TEMP seat ray", [(s.tbm().copy(part), "ray", None)])
    comp = group.component
    res = {}
    try:
        for yy in ys:
            walls = []
            for k in range(n):
                a = 2 * math.pi * k / n
                d = (math.cos(a), math.sin(a))
                start = adsk.core.Point3D.create((cx + d[0] * (r_od + .05)) / 10, yy / 10, (cz + d[1] * (r_od + .05)) / 10)
                hits = adsk.core.ObjectCollection.create()
                comp.findBRepUsingRay(start, adsk.core.Vector3D.create(d[0], 0, d[1]),
                                      adsk.fusion.BRepEntityTypes.BRepFaceEntityType, -1.0, False, hits)
                ds = sorted(math.hypot(hits.item(i).x * 10 - start.x * 10, hits.item(i).z * 10 - start.z * 10)
                            for i in range(hits.count))
                # wall = distance to the first exit; if the start is in a void, 0
                inside = part_contains(comp, start)
                walls.append(round(ds[0], 2) if (ds and inside) else 0.0)
            res["y%.1f" % yy] = {"min": min(walls), "median": sorted(walls)[n // 2], "walls": walls}
    finally:
        group.deleteMe()
    return {"body": body_name, "part": part_key, "centre_xz": [round(cx, 2), round(cz, 2)], "r_od": round(r_od, 2),
            "by_y": res}


def part_contains(comp, p):
    body = comp.bRepBodies.item(0)
    c = body.pointContainment(p)
    return c in (adsk.fusion.PointContainment.PointInsidePointContainment,
                 adsk.fusion.PointContainment.PointOnPointContainment)


# ---- v6 range of motion ---------------------------------------------------------------------------
ROM_EXPECTED = {
    frozenset(("PRINT_carrier_box_left", "6700ZZ arm rear hinge (on moving hub)")),
    frozenset(("STOCK_050_4mm_flange_bearing_1_2", "AXLE_4x24_moving")),
    frozenset(("STOCK_050_4mm_flange_bearing_1_2", "PRINT_compound_left")),
    frozenset(("PRINT_feed_left", "PRINT_compound_left")),
    frozenset(("PRINT_feed_left", "PRINT_feed_right")),
    frozenset(("STOCK_038_extrude_wheel_1", "STOCK_003_extrude_wheel_1")),
}


def arm_split(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    leftovers = set(STATE.get("leftovers", ()))
    moving, static = [], []
    for b in s.proxies(design.rootComponent):
        if b.name in leftovers or not b.assemblyContext:
            continue
        path = b.assemblyContext.fullPathName
        if path.startswith("TEMP") or "TEMP " in path:
            continue
        (moving if any(g in path for g in ARM_GROUPS) else static).append(b)
    return moving, static


def bb_of(body):
    bb = body.boundingBox
    return [v * 10 for v in (bb.minPoint.x, bb.maxPoint.x, bb.minPoint.y, bb.maxPoint.y, bb.minPoint.z, bb.maxPoint.z)]


def bb_gap_l(a, b):
    g = [max(0.0, b[2 * i] - a[2 * i + 1], a[2 * i] - b[2 * i + 1]) for i in range(3)]
    return math.sqrt(sum(x * x for x in g))


def rom_arm(app, angles, out_name, near=1.5, skip=("CLOSING_SPRING_ENVELOPE",)):
    """Min distance from every arm-group body (rotated about Mv) to every static body, per angle."""
    s = load("pancake_paths_study")
    mm = app.measureManager
    moving, static = arm_split(app)
    Mv = STATE["Mv"]
    sbb = [(b, bb_of(b)) for b in static if b.name not in skip]
    res = {}
    for deg in angles:
        rows = []
        for mb in moving:
            if mb.name in skip:
                continue
            shape = rotated(s.tbm().copy(mb), Mv, deg) if deg else s.tbm().copy(mb)
            mbb = bb_of(shape)
            for sb, bbs in sbb:
                if bb_gap_l(mbb, bbs) > near:
                    continue
                r = mm.measureMinimumDistance(shape, sb)
                d = r.value * 10
                if d > near:
                    continue
                p = r.positionOne
                rows.append([mb.name, sb.name, round(d, 3), [round(p.x * 10, 2), round(p.y * 10, 2), round(p.z * 10, 2)],
                             frozenset((mb.name, sb.name)) in ROM_EXPECTED or "FIL" in sb.name.upper()])
        res["%.3f" % deg] = sorted(rows, key=lambda r: r[2])
    (OUT / out_name).write_text(json.dumps(res, indent=1))
    return {k: [r for r in v if not r[4] and r[2] < .3] for k, v in res.items()}


def solo_shots(app, names, views, prefix, colours=None, size=(1600, 1200)):
    """Copies of the named bodies alone in a TEMP group; one image per (suffix, eye, target, up, extents)."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    items = []
    for n in names:
        shape = n if not isinstance(n, str) else s.tbm().copy(by[n])
        key = n if isinstance(n, str) else "shape"
        look = rgb_appearance(design, key, colours[key]) if colours and key in colours else (
            by[n].appearance if isinstance(n, str) else None)
        items.append((shape, key, look))
    states = [(occ, occ.isLightBulbOn) for occ in root.occurrences]
    group = s.add_group(root, "TEMP solo", items)
    out = []
    try:
        for occ, _ in states:
            occ.isLightBulbOn = False
        for suffix, eye, target, up, ext in views:
            out.append(camera_shot(app, prefix + suffix + ".png", eye, target, up, ext, size))
    finally:
        group.deleteMe()
        for occ, state in states:
            occ.isLightBulbOn = state
    return out


CAM_GROUP = "10 Servo output"
CAM_EXPECTED = {
    frozenset(("CAM_JOURNAL_PIN_3x10", "CAM_OUTBOARD_MF63")),
    frozenset(("OEM_SERVO_SPLINE", "HOBBY_SERVO_ENVELOPE")),
}


def rom_cam(app, phis, out_name, near=1.0):
    """Servo-cam sweep: arm angle needed at each cam angle (follower contact) and cam/horn clearances."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    mm = app.measureManager
    C, Mv = STATE["C"], STATE["Mv"]
    leftovers = set(STATE.get("leftovers", ()))
    cam, arm, static = [], [], []
    for b in s.proxies(design.rootComponent):
        if b.name in leftovers or not b.assemblyContext:
            continue
        path = b.assemblyContext.fullPathName
        if path.startswith("TEMP") or b.name.startswith("CLOSING_SPRING"):
            continue
        if CAM_GROUP in path:
            cam.append(b)
        elif any(g in path for g in ARM_GROUPS):
            arm.append(b)
        else:
            static.append(b)
    by_cam = {b.name: b for b in cam}
    follower = next(b for b in arm if b.name == "CAM_FOLLOWER_623")
    sbb = [(b, bb_of(b)) for b in static]
    res = []
    for phi in phis:
        lobe = rotated(s.tbm().copy(by_cam["PRINT_DIRECT_CAM"]), C, phi)

        def dist(theta):
            f = rotated(s.tbm().copy(follower), Mv, theta)
            return mm.measureMinimumDistance(f, lobe).value * 10

        d0 = dist(0.0)
        if d0 > 1e-3:
            theta = 0.0
        else:
            lo, hi = -12.0, 0.0
            if dist(lo) <= 1e-3:
                theta = None
            else:
                for _ in range(13):
                    mid = (lo + hi) / 2
                    if dist(mid) > 1e-3:
                        lo = mid
                    else:
                        hi = mid
                theta = lo
        near_rows = []
        shapes = [(b.name, rotated(s.tbm().copy(b), C, phi)) for b in cam]
        arm_shapes = [(b.name, rotated(s.tbm().copy(b), Mv, theta or 0.0)) for b in arm if b.name != "CAM_FOLLOWER_623"]
        for name, shape in shapes:
            cbb = bb_of(shape)
            others = [(b.name, b, bbs) for b, bbs in sbb] + [(n, a, bb_of(a)) for n, a in arm_shapes]
            for oname, other, obb in others:
                if frozenset((name, oname)) in CAM_EXPECTED or bb_gap_l(cbb, obb) > near:
                    continue
                r = mm.measureMinimumDistance(shape, other)
                d = r.value * 10
                if d <= near:
                    p = r.positionOne
                    near_rows.append([name, oname, round(d, 3), [round(p.x * 10, 1), round(p.y * 10, 1), round(p.z * 10, 1)]])
        res.append({"phi": phi, "arm_deg": None if theta is None else round(theta, 3), "follower_gap_closed": round(d0, 3),
                    "near": sorted(near_rows, key=lambda r: r[2])})
    (OUT / out_name).write_text(json.dumps(res, indent=1))
    return res


# =============================================================================================
# v6: P19 merged into P01, motor 1 mm rearward (flange clamped on P02's flat face), sandwich rules
# =============================================================================================
V6_DY = -1.0
FACE_V6 = FACE + V6_DY                     # 3.3 motor face
CEIL_V6 = (FACE_V6, FACE_V6 + 2.0)         # merged pin plate = P01 ceiling over the flange pocket
GEAR_REAR_V6 = GEAR_REAR_Y + V6_DY         # 5.6: 38T bands widened 1 mm rearward (pinion keeps 3.7 mm mesh)
MOTOR_COMPONENT = "LDO-36STH20-1004AHG(XH)"
MR74_NAMES = ("MR74 4x7x2 fixed axle rear (pin plate C-seat)", "MR74 4x7x2 moving axle rear (pin plate)")


def v6_motor(app):
    s, a = load("pancake_paths_study"), load("ahg_placement")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    if STATE.get("v6_motor") or "PRINT_AHG_PIN_PLATE" not in by:
        raise RuntimeError("v6 motor already applied")
    M = motor_axis(by)
    F, Mv, ears = STATE["F"], STATE["Mv"], STATE["ears"]
    log = []

    comp = {}
    for n in ("PRINT_compound_right", "PRINT_compound_left"):
        g = s.tbm().copy(by[n])
        sl = s.tbm().copy(by[n])
        s.op(sl, s.box(-40, 40, GEAR_REAR_Y, GEAR_REAR_Y + 1.0, -40, 90), "common")
        g = _robust(g, lambda f, sl=sl: translated(sl, dy=V6_DY if f == 1.0 else V6_DY + .01), "join")
        if g is None or g.lumps.count != 1:
            raise RuntimeError("compound widen failed " + n)
        comp[n] = g

    p01 = _robust(by["PRINT_motor_mount"], lambda f: a.flange(M[0], M[1], P02_Y[1], PLATE_Y[1] + .1 * f, THETA, .8), "join")
    if p01 is None:
        raise RuntimeError("P01 refill failed")
    d = (M[0] - F[0], M[1] - F[1])
    L = math.hypot(*d)
    u = (d[0] / L, d[1] / L)
    cuts = [("flange pocket open to rear", a.flange(M[0], M[1], P02_Y[1] - .8, FACE_V6, THETA, .2)),
            ("pilot", s.cyl(M[0], M[1], FACE_V6 - .1, FACE_V6 + 1.7, 8.25)),
            ("pinion", s.cyl(M[0], M[1], FACE_V6 + 1.4, 9.8, 3.6)),
            ("MR74 fixed", s.cyl(F[0], F[1], FACE_V6 - .1, CEIL_V6[1] + .05, 3.5)),
            ("MR74 moving", s.cyl(Mv[0], Mv[1], FACE_V6 - .1, CEIL_V6[1] + .05, 3.5)),
            ("C-seat slot", a.obb(F[0] + u[0] * L / 2, (FACE_V6 + CEIL_V6[1]) / 2, F[1] + u[1] * L / 2, u, L,
                                  CEIL_V6[1] - FACE_V6 + .2, 4.0)),
            ("38T fixed", s.cyl(F[0], F[1], CEIL_V6[1], GEAR_REAR_V6 + 1.5, 10.4)),
            ("38T moving", s.cyl(Mv[0], Mv[1], CEIL_V6[1], GEAR_REAR_V6 + 1.5, 10.4))]
    for i, (ex, ez) in enumerate(ears):
        cuts.append(("ear screw tip %d" % i, s.cyl(ex, ez, FACE_V6 - .1, FACE + .6, 1.7)))
    p01 = cut_each(p01, cuts, log)
    if p01.lumps.count != 1 or log:
        raise RuntimeError("P01 cuts: lumps %d failed %s" % (p01.lumps.count, log))

    motor = [b for b in s.proxies(root) if b.assemblyContext and b.assemblyContext.component.name == MOTOR_COMPONENT]
    for b in motor:
        replace(b, translated(b, dy=V6_DY))
    for n in MR74_NAMES:
        replace(by[n], translated(by[n], dy=V6_DY))
    for n, g in comp.items():
        replace(by[n], g)
    replace(by["AXLE_4x25_fixed"], s.cyl(F[0], F[1], FACE_V6 + .1, 29.7, 2.0))
    replace(by["AXLE_4x24_moving"], s.cyl(Mv[0], Mv[1], FACE_V6 + .1, 28.3, 2.0))
    v_old = by["PRINT_motor_mount"].volume * 1000
    replace(by["PRINT_motor_mount"], p01, None, "P01 Back case - v6 merged pin plate")
    p19 = by["PRINT_AHG_PIN_PLATE"].assemblyContext
    p19_volume = by["PRINT_AHG_PIN_PLATE"].volume * 1000
    p19.deleteMe()
    report = {"motor_dy": V6_DY, "face": FACE_V6, "ceiling": CEIL_V6, "gear_rear": GEAR_REAR_V6,
              "p01_mm3": [round(v_old, 1), round(p01.volume * 1000, 1)], "p01_faces": p01.faces.count,
              "p19_removed_mm3": round(p19_volume, 1), "motor_bodies": len(motor),
              "axles": {"fixed": [FACE_V6 + .1, 29.7], "moving": [FACE_V6 + .1, 28.3]}}
    STATE["v6_motor"] = report
    (OUT / "v6_motor.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


MESH_PAIRS = {frozenset(("AHG factory 10T m0.5 pinion", "PRINT_compound_right")),
              frozenset(("PRINT_compound_right", "PRINT_compound_left")),
              frozenset(("PRINT_feed_left", "PRINT_feed_right")),
              frozenset(("PRINT_feed_left", "PRINT_compound_left")),
              frozenset(("PRINT_feed_right", "PRINT_compound_right")),
              frozenset(("STOCK_038_extrude_wheel_1", "STOCK_003_extrude_wheel_1"))}


def interfere(app, names, tol=1e-3, arm_deg=0.0):
    """Volumetric overlaps of the named bodies with every other body (arm group rotated by arm_deg)."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    leftovers = set(STATE.get("leftovers", ()))
    Mv = STATE["Mv"]
    shapes = []
    for b in s.proxies(design.rootComponent):
        if b.name in leftovers or not b.assemblyContext or b.assemblyContext.fullPathName.startswith("TEMP"):
            continue
        g = s.tbm().copy(b)
        if arm_deg and any(k in b.assemblyContext.fullPathName for k in ARM_GROUPS):
            g = rotated(g, Mv, arm_deg)
        shapes.append((b.name, g, bb_of(g), b.assemblyContext.component.name))
    ignore = {frozenset(p) for p in EXPECTED} | MESH_PAIRS
    hits = []
    for i, (n, g, bb, comp) in enumerate(shapes):
        if n not in names:
            continue
        for j, (o, h, obb, ocomp) in enumerate(shapes):
            if i == j or (o in names and j < i) or frozenset((n, o)) in ignore:
                continue
            if comp == ocomp == MOTOR_COMPONENT:
                continue
            if bb_gap_l(bb, obb) > 0:
                continue
            v, c = s.common_volume(g, h)
            if v > tol:
                hits.append([n, o, round(v, 4), [round(x, 1) for x in bb_of(c)]])
    return hits


HOB_FIXED = (-10.0502, 0.0115)


def cone_y(cx, cz, y0, r0, y1, r1):
    p0 = adsk.core.Point3D.create(cx / 10, y0 / 10, cz / 10)
    p1 = adsk.core.Point3D.create(cx / 10, y1 / 10, cz / 10)
    return adsk.fusion.TemporaryBRepManager.get().createCylinderOrCone(p0, r0 / 10, p1, r1 / 10)


def v6_fixed_hob(app):
    """Fixed hob sandwiched front/rear: STOCK_012 moves from P03's cantilever tongue to a P01 boss."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    if STATE.get("v6_fixed_hob"):
        raise RuntimeError("already applied")
    F = STATE["F"]
    hx, hz = HOB_FIXED
    p03 = by["PRINT_000_outer_shell_of_extruder_1"]
    # P03 left-wall inner face next to the tongue
    comp = s.add_group(design.rootComponent, "TEMP ray", [(s.tbm().copy(p03), "ray", None)]).component
    try:
        hits = adsk.core.ObjectCollection.create()
        comp.findBRepUsingRay(adsk.core.Point3D.create(-3.0, 1.4, .58), adsk.core.Vector3D.create(1, 0, 0),
                              adsk.fusion.BRepEntityTypes.BRepFaceEntityType, -1.0, False, hits)
        xs = sorted(hits.item(i).x * 10 for i in range(hits.count))
    finally:
        comp.parentDesign.rootComponent.allOccurrencesByComponent(comp).item(0).deleteMe()
    wall_x = xs[1]
    tongue = s.box(wall_x - .02, -3.0, 11.9, 16.05, -5.6, 5.6)
    new03 = _robust(p03, lambda f: translated(tongue, dx=(f - 1) * .2), "cut")
    if new03 is None or new03.lumps.count != 1:
        raise RuntimeError("tongue cut failed")
    removed = p03.volume * 1000 - new03.volume * 1000

    boss = s.cyl(hx, hz, 11.0, 15.4, 5.5)
    s.op(boss, cone_y(F[0], F[1], 10.5, 10.9, 21.4, 0.0), "cut")          # 45 deg underside over the 38T pocket
    p01 = _robust(by["PRINT_motor_mount"], lambda f: translated(boss, dx=(f - 1) * .1), "join")
    log = []
    p01 = cut_each(p01, [("MF63 seat", s.cyl(hx, hz, 13.45, 15.5, 3.0)),
                         ("hob shaft end", s.cyl(hx, hz, 12.6, 13.5, 2.0))], log)
    if p01.lumps.count != 1 or log:
        raise RuntimeError("P01 boss failed %s" % log)
    added = p01.volume * 1000 - by["PRINT_motor_mount"].volume * 1000
    replace(p03, new03, None, "P03 Front case - v6")
    replace(by["PRINT_motor_mount"], p01, None, "P01 Back case - v6")
    report = {"wall_x": round(wall_x, 3), "ray_x": [round(x, 2) for x in xs], "p03_removed_mm3": round(removed, 1),
              "p01_added_mm3": round(added, 1)}
    STATE["v6_fixed_hob"] = report
    (OUT / "v6_fixed_hob.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def overhang(body, d, crit=45.0, bed_tol=.3, cell=6.0):
    """Downward-facing area (> crit deg from vertical) above the bed for build direction d; clustered."""
    calc = body.meshManager.createMeshCalculator()
    calc.setQuality(adsk.fusion.TriangleMeshQualityOptions.NormalQualityTriangleMesh)
    mesh = calc.calculate()
    c = mesh.nodeCoordinatesAsDouble
    idx = mesh.nodeIndices
    dn = math.sqrt(sum(x * x for x in d))
    d = [x / dn for x in d]
    hs = [(c[3 * i] * d[0] + c[3 * i + 1] * d[1] + c[3 * i + 2] * d[2]) * 10 for i in range(len(c) // 3)]
    bed = min(hs)
    lim = -math.cos(math.radians(90 - crit))
    total, clusters = 0.0, {}
    for t in range(0, len(idx), 3):
        a, b, e = idx[t], idx[t + 1], idx[t + 2]
        p = [(c[3 * a + k] * 10, c[3 * b + k] * 10, c[3 * e + k] * 10) for k in range(3)]
        u = [p[k][1] - p[k][0] for k in range(3)]
        v = [p[k][2] - p[k][0] for k in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.sqrt(sum(x * x for x in n))
        if ln < 1e-9:
            continue
        cos = sum(n[k] * d[k] for k in range(3)) / ln
        if cos > lim:
            continue
        h = (hs[a] + hs[b] + hs[e]) / 3 - bed
        if h < bed_tol:
            continue
        area = ln / 2
        total += area
        cen = [sum(p[k]) / 3 for k in range(3)]
        key = tuple(int(math.floor(x / cell)) for x in cen)
        cl = clusters.setdefault(key, [0.0, [0, 0, 0], 1e9, -1e9])
        cl[0] += area
        cl[1] = [cl[1][k] + cen[k] * area for k in range(3)]
        cl[2], cl[3] = min(cl[2], h), max(cl[3], h)
    rows = sorted(([round(v[0], 1), [round(x / v[0], 1) for x in v[1]], round(v[2], 1), round(v[3], 1)]
                   for v in clusters.values()), key=lambda r: -r[0])
    return {"total_mm2": round(total, 1), "top": rows[:8]}


# ---- v6 arm: front/rear halves split at the gear plane --------------------------------------------
ARM_SPLIT_Y = 16.0
ARM_SWEEP = (0.3, 0.0) + tuple(-0.5 * i for i in range(1, 15))          # +0.3 .. -7.0 deg
CAM_LIFT = ((0, 0.0), (30, -0.02), (60, -1.55), (90, -4.45), (120, -5.98), (150, -6.05), (180, -5.58))
ARM_GROW = .35
JOINT_AXES = ((14.95, 31.4),)               # one M3x10 SHCS + insert through the top bridge (shafts align the halves)
JOINT_HEAD_Y = 10.1                    # M3x10 SHCS head seat in the rear half (head 0.5 mm in front of P01 at Y 6.6)
FOLLOWER_AXIS = (3.0, 43.22)
HOB_MOVING = (8.66, 0.03)


def _safe_join(U, r, log, tag):
    """Union r into U; on a (deferred) kernel failure keep U unchanged."""
    s = load("pancake_paths_study")
    _flush()
    prev = s.tbm().copy(U)
    try:
        ok = s.tbm().booleanOperation(U, r, adsk.fusion.BooleanTypes.UnionBooleanType)
        adsk.fusion.TemporaryBRepManager.get()
        U.lumps.count
        if ok:
            return U
    except RuntimeError:
        pass
    _flush()
    log.append(tag)
    return prev


def _grow(shape, g):
    s = load("pancake_paths_study")
    out = s.tbm().copy(shape)
    log = []
    for dx, dy, dz in ((g, 0, 0), (-g, 0, 0), (0, g, 0), (0, -g, 0), (0, 0, g), (0, 0, -g)):
        out = _safe_join(out, translated(shape, dx, dy, dz), log, "grow")
    return out


def v6_arm_keepout(app):
    """Static bodies seen from the arm frame over the stroke (+0.3..-7 deg), grown 0.35 mm; cached in STATE."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    Mv, C = STATE["Mv"], STATE["C"]
    abb = bb_of(by["PRINT_carrier_box_left"])
    clip = s.box(abb[0] - 2, abb[1] + 2, abb[2] - 2, 31.5, abb[4] - 2, abb[5] + 2)
    names = ["PRINT_motor_mount", "PRINT_000_outer_shell_of_extruder_1", "CAM_OUTBOARD_MF63",
             "STOCK_059_A1104_hall_effect_sensor_1", "PRINT_RedLizard_HF_tool_carrier"] + \
            [n for n in by if n.startswith("OCT_RECEIVER_MAGNET")]
    parts, log = [], []
    status = OUT / "v6_arm_K_progress.json"
    for n in names:
        _flush()
        g = _robust(by[n], lambda f: translated(clip, dx=(f - 1) * .3), "common")
        if g is None or not g.lumps.count:
            log.append("clip " + n)
            continue
        U = None
        for th in ARM_SWEEP:
            r = rotated(g, Mv, -th)
            U = r if U is None else _safe_join(U, r, log, "sweep %s %.1f" % (n, th))
        parts.append((n, _grow(U, ARM_GROW)))
        status.write_text(json.dumps({"done": [p[0] for p in parts], "log": log}))
    cam = None
    for phi, th in CAM_LIFT:
        for b in ("PRINT_DIRECT_CAM", "CAM_JOURNAL_PIN_3x10"):
            r = rotated(rotated(by[b], C, phi), Mv, -th)
            cam = r if cam is None else _safe_join(cam, r, log, "cam %d" % phi)
    parts.append(("cam sweep", _grow(cam, ARM_GROW)))
    hub = s.cyl(Mv[0], Mv[1], 10.6 - ARM_GROW, 20.0 + ARM_GROW, 5.0 + ARM_GROW)
    s.op(hub, s.cyl(Mv[0], Mv[1], 5.6 - ARM_GROW, 10.6, 9.82 + ARM_GROW), "join")
    parts.append(("moving compound envelope", hub))
    parts.append(("spring", _grow(s.tbm().copy(by["CLOSING_SPRING_ENVELOPE"]), .3)))
    STATE["arm_K"] = parts
    return {"parts": [n for n, _ in parts], "log": log}


ARM_SPLIT_V6 = 15.6
ARM_ANGLES9 = (0.3, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0, -6.0, -7.0)
GROW7 = ((0, 0, 0), (0, .4013, 0), (0, -.4013, 0), (.4013, 0, 0), (-.4013, 0, 0), (0, 0, .4013), (0, 0, -.4013))


def _cut_try(target, tool, log, tag):
    s = load("pancake_paths_study")
    _flush()
    c = s.tbm().copy(target)
    try:
        ok = s.tbm().booleanOperation(c, tool, adsk.fusion.BooleanTypes.DifferenceBooleanType)
        adsk.fusion.TemporaryBRepManager.get()
        s.tbm().copy(c).lumps.count
        if ok:
            return c
    except RuntimeError:
        pass
    _flush()
    log.append(tag)
    return target


def sweep_cut(target, static, clip, log, tag, angles=ARM_ANGLES9, grow=None, about=None):
    """target (arm frame) minus every pose of static (world) over the arm stroke, grown by the offsets."""
    s = load("pancake_paths_study")
    Mv = about or STATE["Mv"]
    grow = GROW7 if grow is None else grow
    g = None
    for f in (0.0, .013, -.017, .029):
        _flush()
        try:
            gg = s.tbm().copy(static)
            ok = s.tbm().booleanOperation(gg, translated(clip, dx=f, dz=.7 * f),
                                          adsk.fusion.BooleanTypes.IntersectionBooleanType)
            adsk.fusion.TemporaryBRepManager.get()
            s.tbm().copy(gg).lumps.count
            if ok:
                g = gg
                break
        except RuntimeError:
            _flush()
    if g is None:
        log.append("clip " + tag)
        return target
    if not g.lumps.count:
        return target
    tbb = bb_of(target)
    for th in angles:
        for dx, dy, dz in grow:
            _flush()
            try:
                tool = translated(rotated(g, Mv, -th), dx, dy, dz)
                adsk.fusion.TemporaryBRepManager.get()
            except RuntimeError:
                _flush()
                log.append("tool %s %.1f" % (tag, th))
                continue
            if bb_gap_l(bb_of(tool), tbb) > 0:
                continue
            target = _cut_try(target, tool, log, "%s %.1f (%.2f,%.2f,%.2f)" % (tag, th, dx, dy, dz))
    _flush()
    return target


def v6_arm_stage(app, stage):
    """Staged arm rebuild; intermediate bodies live in STATE['v6arm']."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    Mv, C, F = STATE["Mv"], STATE["C"], STATE["F"]
    st = STATE.setdefault("v6arm", {"log": []})
    log = st["log"]
    Y = ARM_SPLIT_V6
    rear_clip = s.box(-8.13, 23.17, 12.37, Y + .63, -16.31, 80.07)
    front_clip = s.box(-8.13, 24.17, Y - .63, 32.07, -16.31, 42.11)
    if stage == "split":
        arm = by["PRINT_carrier_box_left"]
        R = s.tbm().copy(arm)
        s.op(R, s.box(-30, 30, -10, Y, -30, 90), "common")
        Fr = s.tbm().copy(arm)
        s.op(Fr, s.box(-30, 30, Y, 40, -30, 90), "common")
        R = _robust(R, lambda f: s.box(-5.3, 19.9, 12.9, Y, -11.9, 75.7 * f if f < 1.001 else 75.7), "join")
        st.update(R=R, Fr=Fr)
        return {"R": [R.lumps.count, round(R.volume * 1000, 1)], "Fr": [Fr.lumps.count, round(Fr.volume * 1000, 1)]}
    if stage in ("P03", "P01", "tool"):
        names = {"P03": ["PRINT_000_outer_shell_of_extruder_1"], "P01": ["PRINT_motor_mount"],
                 "tool": ["PRINT_RedLizard_HF_tool_carrier", "STOCK_059_A1104_hall_effect_sensor_1",
                          "CAM_OUTBOARD_MF63"] + [n for n in by if n.startswith("OCT_RECEIVER_MAGNET")]}[stage]
        for n in names:
            st["R"] = sweep_cut(st["R"], by[n], rear_clip, log, "R-" + n[:12])
            st["Fr"] = sweep_cut(st["Fr"], by[n], front_clip, log, "F-" + n[:12])
        return {"R": [st["R"].lumps.count, round(st["R"].volume * 1000, 1)],
                "Fr": [st["Fr"].lumps.count, round(st["Fr"].volume * 1000, 1)], "log": log[-6:]}
    if stage == "cam":
        for phi, th in CAM_LIFT:
            for b in ("PRINT_DIRECT_CAM", "CAM_JOURNAL_PIN_3x10"):
                tool = rotated(rotated(by[b], C, phi), Mv, -th)
                for dx, dy, dz in GROW7:
                    st["R"] = _cut_try(st["R"], translated(tool, dx, dy, dz), log, "cam %d" % phi)
        return {"R": [st["R"].lumps.count, round(st["R"].volume * 1000, 1)], "log": log[-6:]}
    if stage == "recut":
        H, Fo = HOB_MOVING, FOLLOWER_AXIS
        spring = s.tbm().copy(by["CLOSING_SPRING_ENVELOPE"])
        sp = s.tbm().copy(spring)
        for dy, dz in ((.3, 0), (-.3, 0), (0, .3), (0, -.3)):
            s.op(sp, translated(spring, dy=dy, dz=dz), "join")
        env = []
        for cx, cz in (Mv, F):
            e = s.cyl(cx, cz, 10.6 - ARM_GROW, 20.0 + ARM_GROW, 5.0 + ARM_GROW)
            s.op(e, s.cyl(cx, cz, 5.6 - ARM_GROW, 10.6 + ARM_GROW, 9.82 + ARM_GROW), "join")
            env.append(e)
        st["R"] = sweep_cut(st["R"], env[1], rear_clip, log, "R-fixed compound", grow=((0, 0, 0),))
        cuts = [("spring", sp), ("moving compound", env[0]),
                ("6700 seat", s.cyl(Mv[0], Mv[1], 10.9, 15.0, 7.5)),
                ("6700 inner race", s.cyl(Mv[0], Mv[1], 14.9, 15.4, 6.7)),
                ("STOCK_047 seat", s.cyl(H[0], H[1], 13.45, 15.45, 3.05)),
                ("STOCK_047 flange", s.cyl(H[0], H[1], 15.35, Y + .1, 3.65)),
                ("hob shaft end", s.cyl(H[0], H[1], 12.6, 13.6, 2.0)),
                ("follower pin", s.cyl(Fo[0], Fo[1], 2.5, Y + .1, 1.5)),
                ("P01 face 6.0->6.4 above fork", s.box(-8, 23, 5.5, 6.4, 53.05, 80)),
                ("P01 face 6.0->6.4 beside fork", s.box(13.05, 23, 5.5, 6.4, 20, 80))]
        slot = s.box(JOINT_AXES[0][0] - 3.0, JOINT_AXES[0][0] + 3.0, 5.5, JOINT_HEAD_Y, JOINT_AXES[0][1],
                     JOINT_AXES[1][1])
        for jx, jz in JOINT_AXES:
            s.op(slot, s.cyl(jx, jz, 5.5, JOINT_HEAD_Y, 3.0), "join")
            cuts.append(("joint clearance", s.cyl(jx, jz, JOINT_HEAD_Y - .1, Y + .1, 1.7)))
        cuts.append(("joint head slot", slot))
        st["R"] = cut_each(st["R"], cuts, log)
        fr_cuts = [("spring", sp), ("moving compound", env[0])] + [
            ("joint insert", s.cyl(jx, jz, Y - .1, Y + 4.0, 2.3)) for jx, jz in JOINT_AXES]
        st["Fr"] = cut_each(st["Fr"], fr_cuts, log)
        return {"R": [st["R"].lumps.count, round(st["R"].volume * 1000, 1), st["R"].faces.count],
                "Fr": [st["Fr"].lumps.count, round(st["Fr"].volume * 1000, 1), st["Fr"].faces.count],
                "log": log[-8:]}
    raise ValueError(stage)


def v6_arm_simple(app):
    """Arm split at Y 15.6 (moving hob + pivot sandwiched); ring/web filled to the split face; P03 relieved."""
    s, a = load("pancake_paths_study"), load("ahg_placement")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    if "PRINT_arm_front_half" in by:
        raise RuntimeError("arm already split")
    Mv, H, Fo = STATE["Mv"], HOB_MOVING, FOLLOWER_AXIS
    Y = ARM_SPLIT_V6
    log = []
    arm = by["PRINT_carrier_box_left"]
    R = s.tbm().copy(arm)
    s.op(R, s.box(-30, 30, -10, Y, -30, 90), "common")
    Fr = s.tbm().copy(arm)
    s.op(Fr, s.box(-30, 30, Y, 40, -30, 90), "common")

    y0 = 14.95
    fill = s.cyl(Mv[0], Mv[1], y0, Y, 9.5)
    dx, dz = H[0] - Mv[0], H[1] - Mv[1]
    L = math.hypot(dx, dz)
    s.op(fill, a.obb((Mv[0] + H[0]) / 2, (y0 + Y) / 2, (Mv[1] + H[1]) / 2, (dx / L, dz / L), L, Y - y0, 9.0), "join")
    s.op(fill, s.box(Mv[0] - 5.5, Mv[0] + 5.5, y0, Y, Mv[1], 26.0), "join")
    s.op(fill, s.cyl(H[0], H[1], y0, Y, 5.6), "join")
    R = _robust(R, lambda f: translated(fill, dx=(f - 1) * .2), "join")

    cuts = [("6700 seat", s.cyl(Mv[0], Mv[1], 10.9, 15.0, 7.5)),
            ("6700 inner race + hub", s.cyl(Mv[0], Mv[1], 14.9, Y + .1, 6.7)),
            ("STOCK_047 seat", s.cyl(H[0], H[1], 13.45, 15.45, 3.05)),
            ("STOCK_047 flange", s.cyl(H[0], H[1], 15.35, Y + .1, 3.65)),
            ("hob shaft end", s.cyl(H[0], H[1], 12.6, 13.6, 2.0)),
            ("P01 face above fork", s.box(-8, 23, 5.5, 6.4, 53.05, 80)),
            ("P01 face beside fork", s.box(13.05, 23, 5.5, 6.4, 20, 80))]
    slot = s.box(JOINT_AXES[0][0] - 3.0, JOINT_AXES[0][0] + 3.0, 5.5, JOINT_HEAD_Y, JOINT_AXES[0][1], JOINT_AXES[1][1])
    for jx, jz in JOINT_AXES:
        s.op(slot, s.cyl(jx, jz, 5.5, JOINT_HEAD_Y, 3.0), "join")
        cuts.append(("joint clearance", s.cyl(jx, jz, JOINT_HEAD_Y - .1, Y + .1, 1.7)))
    cuts.append(("joint head slot", slot))
    R = cut_each(R, cuts, log)
    Fr = cut_each(Fr, [("joint insert", s.cyl(jx, jz, Y - .1, Y + 4.0, 2.3)) for jx, jz in JOINT_AXES], log)

    def biggest(body):
        if body.lumps.count == 1:
            return body, 0.0
        vols = [body.lumps.item(i).volume for i in range(body.lumps.count)]
        keep = vols.index(max(vols))
        out = None
        dropped = 0.0
        for i in range(body.lumps.count):
            if i == keep:
                continue
            dropped += vols[i] * 1000
        lb = body.lumps.item(keep).boundingBox
        out = s.tbm().copy(body)
        s.op(out, s.box(lb.minPoint.x * 10 - .01, lb.maxPoint.x * 10 + .01, lb.minPoint.y * 10 - .01,
                        lb.maxPoint.y * 10 + .01, lb.minPoint.z * 10 - .01, lb.maxPoint.z * 10 + .01), "common")
        return out, dropped

    R, dropR = biggest(R)
    Fr, dropF = biggest(Fr)
    if R.lumps.count != 1 or Fr.lumps.count != 1:
        raise RuntimeError("lumps R %d Fr %d" % (R.lumps.count, Fr.lumps.count))

    p03 = s.tbm().copy(by["PRINT_000_outer_shell_of_extruder_1"])
    v03 = p03.volume
    for th in ARM_ANGLES9:
        r = rotated(fill, Mv, th)
        for ox, oy, oz in GROW7:
            p03 = _cut_try(p03, translated(r, ox, oy, oz), log, "P03 relief %.1f" % th)
    if p03.lumps.count != 1:
        raise RuntimeError("P03 lumps %d" % p03.lumps.count)
    STATE["v6arm_simple"] = {"R": R, "Fr": Fr, "p03": p03}
    rep = {"R": [round(R.volume * 1000, 1), R.faces.count], "Fr": [round(Fr.volume * 1000, 1), Fr.faces.count],
           "dropped_mm3": [round(dropR, 2), round(dropF, 2)], "p03_relief_mm3": round((v03 - p03.volume) * 1000, 1),
           "log": log}
    (OUT / "v6_arm_simple.json").write_text(json.dumps(rep, indent=2))
    return rep


def add_body(sibling_proxy, shape, name, component_name):
    """New component (one base-feature body) next to sibling_proxy's occurrence, in the same parent group."""
    s = load("pancake_paths_study")
    parent_occ = sibling_proxy.assemblyContext
    path_parent = parent_occ.assemblyContext
    parent_comp = path_parent.component if path_parent else adsk.fusion.Design.cast(
        adsk.core.Application.get().activeProduct).rootComponent
    occ = parent_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = component_name
    geometry = s.tbm().copy(shape)
    proxy_occ = occ.createForAssemblyContext(path_parent) if path_parent else occ
    inverse = proxy_occ.transform2.copy()
    inverse.invert()
    s.tbm().transform(geometry, inverse)
    feature = occ.component.features.baseFeatures.add()
    feature.startEdit()
    occ.component.bRepBodies.add(geometry, feature)
    feature.finishEdit()
    occ.component.bRepBodies.item(0).name = name
    return occ


def web_primitives(y0, y1, g=0.0, ring=True):
    """Arm hinge ring + webs (arm_ring_solids layout) between y0..y1, every dimension grown by g."""
    s, a = load("pancake_paths_study"), load("ahg_placement")
    Mv, H = STATE["Mv"], HOB_MOVING
    dx, dz = H[0] - Mv[0], H[1] - Mv[1]
    L = math.hypot(dx, dz)
    shape = a.obb((Mv[0] + H[0]) / 2, (y0 + y1) / 2, (Mv[1] + H[1]) / 2, (dx / L, dz / L), L + 2 * g, y1 - y0, 9.0 + 2 * g)
    s.op(shape, s.box(Mv[0] - 5.5 - g, Mv[0] + 5.5 + g, y0, y1, Mv[1] - g, 26.0 + g), "join")
    s.op(shape, s.cyl(H[0], H[1], y0, y1, 5.6 + g), "join")
    if ring:
        s.op(shape, s.cyl(Mv[0], Mv[1], y0, y1, 9.5 + g), "join")
    return shape


def v6_arm_fix(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    Mv = STATE["Mv"]
    log = []
    angles = (0.3,) + tuple(-0.5 * i for i in range(0, 15))
    front = web_primitives(15.0 - .45, ARM_SPLIT_V6 + .41, .41)
    rear = web_primitives(11.0 - .45, 11.0 + .05, .41, ring=False)
    p03 = s.tbm().copy(by["PRINT_000_outer_shell_of_extruder_1"])
    p01 = s.tbm().copy(by["PRINT_motor_mount"])
    v03, v01 = p03.volume, p01.volume
    for th in angles:
        p03 = _cut_try(p03, rotated(front, Mv, th), log, "P03 %.1f" % th)
        p01 = _cut_try(p01, rotated(rear, Mv, th), log, "P01 %.1f" % th)
    R = cut_each(by["PRINT_carrier_box_left"], [("rear face beside fork", s.box(13.05, 23, 5.5, 7.0, 20, 80))], log)
    if p03.lumps.count != 1 or p01.lumps.count != 1 or R.lumps.count != 1:
        raise RuntimeError("lumps %d %d %d %s" % (p03.lumps.count, p01.lumps.count, R.lumps.count, log))
    replace(by["PRINT_000_outer_shell_of_extruder_1"], p03)
    replace(by["PRINT_motor_mount"], p01)
    replace(by["PRINT_carrier_box_left"], R)
    return {"p03_mm3": round((v03 - p03.volume) * 1000, 1), "p01_mm3": round((v01 - p01.volume) * 1000, 1), "log": log}



def persist_names(app, mapping=None):
    """Write body names into their base features (names set outside an edit revert on recompute).
    Single-body hardware components take the component name; mapping {body name: new name} wins."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    mapping = mapping or {}
    done = []
    seen = set()
    for proxy in s.proxies(design.rootComponent):
        native = proxy.nativeObject or proxy
        comp = native.parentComponent
        if comp.name in seen or not comp.features.baseFeatures.count:
            continue
        seen.add(comp.name)
        bodies = [comp.bRepBodies.item(i) for i in range(comp.bRepBodies.count)]
        want = [mapping.get(b.name, b.name) for b in bodies]
        if len(bodies) == 1 and " " not in comp.name and not comp.name.startswith(("P0", "P1", "P2")):
            want = [mapping.get(bodies[0].name, comp.name)]
        feature = comp.features.baseFeatures.item(0)
        stored = [feature.bodies.item(i).name for i in range(feature.bodies.count)]
        if stored != want or [b.name for b in bodies] != want:
            feature.startEdit()
            try:
                fb = [feature.bodies.item(i) for i in range(feature.bodies.count)]
                for b, w in zip(fb, want):
                    if b.name != w:
                        b.name = w
            finally:
                feature.finishEdit()
        for b, w in zip([comp.bRepBodies.item(i) for i in range(comp.bRepBodies.count)], want):
            if b.name != w:
                done.append([b.name, w])
                b.name = w
    return done


def thin_summary(app, key):
    """ray_thin + v5-comparable counts (samples < 1.2 mm and < 0.5 mm); written to v6_thin_<key>.json."""
    rows = ray_thin(app, key)
    smp = STATE["thin_samples"][key]
    out = {"key": key, "n_lt_1p2": sum(1 for q in smp if q[4] < 1.2), "n_lt_0p5": sum(1 for q in smp if q[4] < .5),
           "clusters_lt_0p5": [[r["n"], r["t_min"], r["t_med"], r["axes"], r["bbox"]] for r in rows if r["t_min"] < .5]}
    (OUT / ("v6_thin_%s.json" % key)).write_text(json.dumps(out, indent=1))
    return out


# =============================================================================================
# v6 intent audit: every face of each printed part must be explained by a body, a motion or a path
# =============================================================================================
INTENT_CLEAR = 1.0
HW_TOKENS = ("bearing", "MR74", "6700", "MF63", "623", "SHCS", "ISO7380", "M3x", "M2x", "M2_", "NUT", "WASHER",
             "INSERT", "HEATSET", "PIN", "AXLE", "SHAFT", "GRUB", "SCREW", "TAP", "MAGNET")
Y_AXIS_HW = ("bearing", "MR74", "6700", "MF63", "623", "NUT", "WASHER", "INSERT", "HEATSET", "MAGNET")


def lift_at(phi):
    phi = max(0.0, min(180.0, phi))
    for (a, ta), (b, tb) in zip(CAM_LIFT, CAM_LIFT[1:]):
        if a <= phi <= b:
            return ta + (tb - ta) * (phi - a) / (b - a)
    return 0.0


def _hw_axis(body):
    n = body.name
    if "SPRING_PRELOAD" in n:
        return 0
    if any(t.lower() in n.lower() for t in Y_AXIS_HW):
        return 1
    bb = bb_of(body)
    ext = [bb[1] - bb[0], bb[3] - bb[2], bb[5] - bb[4]]
    return ext.index(max(ext))


def intent_explainers(app, key, margin=3.0):
    """(label, shape, bbox) for everything that may explain a face of printed part `key`, in that part's frame."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    leftovers = set(STATE.get("leftovers", ()))
    target = PARTS[key]
    Mv, C = STATE["Mv"], STATE["C"]
    in_arm = key in ("P04", "P04F")
    proxies = [b for b in s.proxies(design.rootComponent) if b.name not in leftovers and b.assemblyContext
               and not b.assemblyContext.fullPathName.startswith("TEMP")]
    pbb = bb_of(next(b for b in proxies if b.name == target))
    zone = [pbb[0] - margin - 30, pbb[1] + margin + 30, pbb[2] - margin - 30, pbb[3] + margin + 30,
            pbb[4] - margin - 30, pbb[5] + margin + 30]
    out = []

    def add(label, shape):
        bb = bb_of(shape)
        if bb_gap_l(bb, pbb) <= margin:
            out.append((label, shape, bb))

    for b in proxies:
        if b.name == target or bb_gap_l(bb_of(b), zone) > 0:
            continue
        path = b.assemblyContext.fullPathName
        is_arm = any(g in path for g in ARM_GROUPS)
        is_cam = CAM_GROUP in path
        is_tool = path.startswith("12 ")
        is_motor = b.assemblyContext.component.name == MOTOR_COMPONENT
        hw = any(t.lower() in b.name.lower() for t in HW_TOKENS)
        if in_arm:
            if is_arm:
                add(b.name, s.tbm().copy(b))
            elif is_cam:
                for phi in range(0, 181, 15):
                    add("%s @cam%d" % (b.name, phi), rotated(rotated(b, C, phi), Mv, -lift_at(phi)))
            else:
                for th in (0.3, 0.0, -2.0, -4.0, -6.05, -7.0):
                    add("%s @arm%.2f" % (b.name, th), rotated(b, Mv, -th))
        else:
            if is_arm:
                for th in (0.3, 0.0, -2.0, -4.0, -6.05, -7.0):
                    add("%s @arm%.2f" % (b.name, th), rotated(b, Mv, th))
            elif is_cam:
                for phi in range(0, 360, 20):
                    add("%s @cam%d" % (b.name, phi), rotated(b, C, phi))
            else:
                add(b.name, s.tbm().copy(b))
        if is_tool and not in_arm:
            for dy in (5, 10, 20, 40):
                add("%s withdraw+%d" % (b.name, dy), translated(b, dy=dy))
        if is_motor or b.name == "HOBBY_SERVO_ENVELOPE":
            for dy in (-3, -6, -12, -20):
                g = translated(b, dy=dy)
                add("%s insert%+d" % (b.name, dy), rotated(g, Mv, 0.0) if in_arm else g)
        elif hw:
            ax = _hw_axis(b)
            for dist in (-6, -3, 3, 6):
                d = [0.0, 0.0, 0.0]
                d[ax] = dist
                g = translated(b, *d)
                add("%s path%s%+d" % (b.name, "XYZ"[ax], dist), g)
    return out


def explain_faces(app, key, clear=INTENT_CLEAR):
    """Each face of the part: nearest explainer within `clear` mm, else unexplained; clusters by adjacency."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    part = by[PARTS[key]]
    native = part.nativeObject or part
    ex = intent_explainers(app, key)
    mm = app.measureManager
    pbb = bb_of(part)
    faces = [part.faces.item(i) for i in range(part.faces.count)]
    nfaces = [native.faces.item(i) for i in range(native.faces.count)]
    idx = {f.tempId: i for i, f in enumerate(nfaces)}
    rows = []
    for i, f in enumerate(faces):
        fb = f.boundingBox
        fbb = [fb.minPoint.x * 10, fb.maxPoint.x * 10, fb.minPoint.y * 10, fb.maxPoint.y * 10,
               fb.minPoint.z * 10, fb.maxPoint.z * 10]
        envelope = any(abs(fbb[2 * a] - fbb[2 * a + 1]) < 1e-3 and
                       (abs(fbb[2 * a] - pbb[2 * a]) < 1e-3 or abs(fbb[2 * a] - pbb[2 * a + 1]) < 1e-3)
                       for a in range(3))
        best = (None, 99.0)
        if not envelope:
            cands = sorted((bb_gap_l(fbb, ebb), n, g) for n, g, ebb in ex if bb_gap_l(fbb, ebb) < clear)
            for gap, n, g in cands:
                if gap >= best[1]:
                    break
                try:
                    d = mm.measureMinimumDistance(f, g).value * 10
                except RuntimeError:
                    _flush()
                    continue
                if d < best[1]:
                    best = (n, d)
                if d < .05:
                    break
        p = f.pointOnFace
        rows.append({"i": i, "type": type(f.geometry).__name__, "area": round(f.area * 100, 3),
                     "pt": [round(p.x * 10, 2), round(p.y * 10, 2), round(p.z * 10, 2)], "bb": [round(v, 2) for v in fbb],
                     "envelope": envelope, "by": best[0], "d": round(best[1], 3),
                     "explained": envelope or best[1] < clear})
    # clusters of unexplained faces by edge adjacency
    un = {r["i"] for r in rows if not r["explained"]}
    parent = {i: i for i in un}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in un:
        for e in nfaces[i].edges:
            for g in e.faces:
                j = idx.get(g.tempId)
                if j in un and find(i) != find(j):
                    parent[find(i)] = find(j)
    groups = {}
    for i in un:
        groups.setdefault(find(i), []).append(i)
    clusters = []
    for members in groups.values():
        rs = [rows[i] for i in members]
        bb = [min(r["bb"][0] for r in rs), max(r["bb"][1] for r in rs), min(r["bb"][2] for r in rs),
              max(r["bb"][3] for r in rs), min(r["bb"][4] for r in rs), max(r["bb"][5] for r in rs)]
        near = sorted(((r["d"], r["by"]) for r in rs if r["by"]), key=lambda t: t[0])[:2]
        clusters.append({"faces": sorted(members), "n": len(members), "area": round(sum(r["area"] for r in rs), 2),
                         "bbox": [round(v, 2) for v in bb], "types": sorted(set(r["type"] for r in rs)), "nearest": near})
    clusters.sort(key=lambda c: -c["area"])
    out = {"key": key, "faces": len(rows), "explainers": len(ex), "unexplained_faces": len(un),
           "unexplained_area": round(sum(rows[i]["area"] for i in un), 1), "clusters": clusters, "rows": rows}
    (OUT / ("v6_intent_%s.json" % key)).write_text(json.dumps(out, indent=1))
    STATE.setdefault("intent", {})[key] = out
    return {k: v for k, v in out.items() if k not in ("rows", "clusters")}


def intent_shot(app, key, name, views, others=(), size=(1600, 1200), red=(225, 40, 40), grey=(185, 190, 200)):
    """Copy of the part with its unexplained faces in red (plus optional context bodies), one image per view."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    part = by[PARTS[key]]
    data = STATE["intent"][key]
    if any("class" in r for r in data["rows"]):
        bad = {r["i"] for r in data["rows"] if r.get("class") == "UNCLASSIFIED"}
        amber_ids = {r["i"] for r in data["rows"] if r.get("class") == "declared"}
    else:
        bad = {r["i"] for r in data["rows"] if not r["explained"]}
        amber_ids = set()

    def fkey(f):
        b = f.boundingBox
        return (round(f.area * 100, 2), round(b.minPoint.x * 10, 2), round(b.maxPoint.x * 10, 2), round(b.minPoint.y * 10, 2),
                round(b.maxPoint.y * 10, 2), round(b.minPoint.z * 10, 2), round(b.maxPoint.z * 10, 2))
    keys = {fkey(part.faces.item(i)) for i in bad}
    amber_keys = {fkey(part.faces.item(i)) for i in amber_ids}
    look = rgb_appearance(design, "intent red", red)
    amber = rgb_appearance(design, "intent amber", (240, 170, 30))
    items = [(s.tbm().copy(part), "part", rgb_appearance(design, "intent grey", grey))]
    for o in others:
        shape = o if not isinstance(o, str) else s.tbm().copy(by[o])
        items.append((shape, "ctx", rgb_appearance(design, "intent ctx", (90, 140, 210))))
    states = [(occ, occ.isLightBulbOn) for occ in root.occurrences]
    # face overrides only persist when made inside the base-feature edit (outside it each one is undone by
    # the next recompute); body appearances are applied after finishEdit
    group = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    group.component.name = "TEMP intent"
    try:
        feat = group.component.features.baseFeatures.add()
        feat.startEdit()
        try:
            for i, (shape, _, _) in enumerate(items):
                body = group.component.bRepBodies.add(shape, feat)
                if i == 0:
                    for f in body.faces:
                        k = fkey(f)
                        if k in keys:
                            f.appearance = look
                        elif k in amber_keys:
                            f.appearance = amber
        finally:
            feat.finishEdit()
        for body, (_, body_name, appearance) in zip(group.component.bRepBodies, items):
            body.name = body_name
            body.appearance = appearance
        STATE["intent_shot_marked"] = sum(1 for f in group.component.bRepBodies.item(0).faces
                                          if f.appearance and f.appearance.name in (look.name, amber.name))
        for occ, _ in states:
            occ.isLightBulbOn = False
        for suffix, eye, target, up, ext in views:
            camera_shot(app, name + suffix + ".png", eye, target, up, ext, size)
    finally:
        group.deleteMe()
        for occ, state in states:
            if occ.isValid:
                occ.isLightBulbOn = state
    return len(bad)


def hole_groups(body):
    """Concave axis-aligned cylindrical faces of a body grouped by (axis, centre, radius) with their axial span."""
    groups = {}
    for face in body.faces:
        g = face.geometry
        if not isinstance(g, adsk.core.Cylinder):
            continue
        ax = g.axis
        axis = tuple(round(v, 3) for v in (ax.x, ax.y, ax.z))
        if max(abs(v) for v in axis) < .999:
            continue
        a = [i for i in range(3) if abs(axis[i]) > .5][0]
        o = g.origin
        pt = face.pointOnFace
        ok, normal = face.evaluator.getNormalAtPoint(pt)
        radial = [pt.x - o.x, pt.y - o.y, pt.z - o.z]
        radial[a] = 0.0
        if normal.x * radial[0] + normal.y * radial[1] + normal.z * radial[2] >= 0:
            continue                                   # convex (boss), not a hole
        c = [o.x * 10, o.y * 10, o.z * 10]
        c[a] = 0.0
        k = (a, round(c[0], 1), round(c[1], 1), round(c[2], 1), round(g.radius * 10, 2))
        fb = face.boundingBox
        lo = [fb.minPoint.x, fb.minPoint.y, fb.minPoint.z][a] * 10
        hi = [fb.maxPoint.x, fb.maxPoint.y, fb.maxPoint.z][a] * 10
        if k in groups:
            groups[k] = [min(groups[k][0], lo), max(groups[k][1], hi)]
        else:
            groups[k] = [lo, hi]
    return groups


def lost_holes(app, orig_bodies, new_bodies, tol=.35, rtol=.06):
    """Original hole groups with no matching hole (same axis, centre within tol, radius within rtol) in the new part(s)."""
    new = {}
    for b in new_bodies:
        for k, span in hole_groups(b).items():
            new.setdefault(k, span)
    out = []
    for b in orig_bodies:
        for (a, x, y, z, r), (lo, hi) in sorted(hole_groups(b).items()):
            match = [k for k in new if k[0] == a and abs(k[4] - r) <= rtol and
                     math.hypot(*[[x, y, z][i] - k[1 + i] for i in range(3) if i != a]) <= tol]
            if not match:
                out.append({"axis": "XYZ"[a], "centre": [x, y, z], "r": r, "span": [round(lo, 2), round(hi, 2)]})
    return out


# ---- v6 intent pass: restore the original probe-adapter pilots ------------------------------------
# The original P01 carried two blind M3x4.6x4 insert pilots (X +/-18, Z -52.78) for a future
# Cartographer/Beacon adapter. The v4 band is only 2.1 mm deep there (the belt cartridges sit behind
# it), so they return on forward bosses: same X/Z pattern, 4.5 mm blind pilot, 0.6 mm lead-in.
PROBE_PILOTS = ((-18.0, -52.78), (18.0, -52.78))
PROBE_BOSS = (11.2, 15.9, 4.0)                                  # Y from, Y to, radius
PROBE_PILOT = ((11.4, 15.3, 2.27), (15.3, 15.95, 2.42))


def v6_probe_pilots(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    if STATE.get("v6_probe_pilots"):
        raise RuntimeError("already applied")
    p01 = by["PRINT_motor_mount"]
    y0, y1, r = PROBE_BOSS
    bosses = None
    for x, z in PROBE_PILOTS:
        c = s.cyl(x, z, y0, y1, r)
        if bosses is None:
            bosses = c
        else:
            s.op(bosses, c, "join")
    new = _robust(p01, lambda f: translated(bosses, dx=(f - 1) * .1), "join")
    if new is None or new.lumps.count != 1:
        raise RuntimeError("probe boss join failed")
    log = []
    new = cut_each(new, [("probe pilot %+.0f r%.2f" % (x, rr), s.cyl(x, z, a, b, rr))
                         for x, z in PROBE_PILOTS for a, b, rr in PROBE_PILOT], log)
    if new.lumps.count != 1 or log:
        raise RuntimeError("probe pilot cut failed %s" % log)
    added = new.volume * 1000 - p01.volume * 1000
    replace(p01, new, None, "P01 Back case - v6")
    report = {"added_mm3": round(added, 1), "pilots_xz": PROBE_PILOTS, "boss_y0_y1_r": PROBE_BOSS,
              "pilot_y0_y1_r": PROBE_PILOT}
    STATE["v6_probe_pilots"] = report
    (OUT / "v6_probe_pilots.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


# ---- declared intent: faces with a documented reason that no body/motion/path explains -----------
INTENT_MICRO = 0.2                                              # mm^2: boolean micro-facets
INTENT_DECLARED = {
    "P01": [
        ("Probe-adapter insert boss + blind M3 pilot, left (original Cartographer/Beacon pattern)",
         [-22.05, -13.95, 11.15, 15.96, -56.85, -48.7]),
        ("Probe-adapter insert boss + blind M3 pilot, right (original Cartographer/Beacon pattern)",
         [13.95, 22.05, 11.15, 15.96, -56.85, -48.7]),
        ("Arm hob-boss swing clearance (r7.3 sweep, ~1.0 mm), pinion-relief front and a 0.75 mm legacy "
         "NEMA14 shaft-end notch that opens into the relief", [-4.9, 7.9, 6.35, 11.45, -7.6, 3.5]),
        ("Arm hob-boss swing clearance at full open (r7.3 sweep)", [17.55, 17.75, 6.35, 11.45, -1.05, 0.0]),
        ("Arm-relief box corner steps (rear zone)", [3.85, 4.4, 6.55, 10.25, 26.7, 28.65]),
    ],
    "P02": [
        ("Motor lead exit notch corner (AHG lead bend room)", [-14.25, -13.95, -13.75, -10.05, -17.85, -17.1]),
        ("Motor lead exit notch corner (AHG lead bend room)", [-22.55, -21.85, -13.75, -10.05, -7.95, -7.7]),
    ],
    "P03": [
        ("Optional CPAP adapter blind M3 pilot (original BOM)", [-20.5, -15.5, 33.4, 38.0, 18.25, 23.2]),
        ("Optional CPAP adapter blind M3 pilot (original BOM)", [-20.5, -15.5, 33.4, 38.0, 30.25, 35.2]),
        ("Optional CPAP adapter blind M3 pilot (original BOM)", [15.5, 20.5, 33.4, 38.0, 18.25, 23.2]),
        ("Optional CPAP adapter blind M3 pilot (original BOM)", [15.5, 20.5, 33.4, 38.0, 30.25, 35.2]),
        ("0.3 mm front-face print chamfer (prints front face down)", [-22.55, 22.55, 37.6, 38.0, -22.85, 62.3]),
        ("r0.5 inside-corner fillet of the open-front tool slot", [11.1, 11.7, 31.45, 38.0, 48.4, 49.0]),
        ("r0.5 inside-corner fillet of the open-front tool slot", [-11.7, -11.1, 31.45, 38.0, 48.4, 49.0]),
    ],
    "P04": [
        ("Manual-release lever tip above the case", [-4.55, 2.55, 6.35, 13.05, 72.2, 75.75]),
        ("Closing-spring centring spigot inside the coil", [8.75, 11.85, 13.4, 15.65, 30.9, 33.65]),
        ("Moving-hob boss outline step", [13.3, 14.3, 11.95, 15.0, -0.3, 4.5]),
        ("Follower 623 pocket (r5.6, ~1.04 mm bearing clearance)", [1.45, 9.05, 4.35, 9.65, 41.65, 49.25]),
    ],
    "P04F": [],
    "P05": [],
}


def classify_intent(key):
    """Label every face of a saved intent audit: geometry | envelope | declared | micro | UNCLASSIFIED."""
    path = OUT / ("v6_intent_%s.json" % key)
    data = json.loads(path.read_text())
    decl = INTENT_DECLARED.get(key, [])
    tally = {"geometry": 0, "envelope": 0, "declared": 0, "micro": 0, "UNCLASSIFIED": 0}
    labels = {}
    for r in data["rows"]:
        if r["envelope"]:
            c = "envelope"
        elif r["explained"]:
            c = "geometry"
        else:
            bb = r["bb"]
            hit = next((lab for lab, d in decl if all(d[2 * a] - .05 <= bb[2 * a] and bb[2 * a + 1] <= d[2 * a + 1] + .05
                                                      for a in range(3))), None)
            if hit:
                c = "declared"
                labels[hit] = labels.get(hit, 0) + 1
            elif r["area"] < INTENT_MICRO:
                c = "micro"
            else:
                c = "UNCLASSIFIED"
        r["class"] = c
        tally[c] += 1
    data["tally"] = tally
    data["declared_labels"] = labels
    data["unclassified"] = [r for r in data["rows"] if r["class"] == "UNCLASSIFIED"]
    path.write_text(json.dumps(data, indent=1))
    STATE.setdefault("intent", {})[key] = data
    return {"key": key, "faces": data["faces"], "tally": tally, "declared": labels,
            "unclassified": [[r["i"], r["type"], r["area"], r["bb"]] for r in data["unclassified"]]}


# ---- v6 intent pass: inner-ring reliefs in blind bearing seats -----------------------------------
# Inherited from the original: each blind seat floor ran from the shaft clearance straight out to the
# seat wall, so the rotating inner ring's face sat on stationary plastic. A 0.3 mm relief out past
# the inner ring (MF63 ~4.0 mm, MF74 ~5.2 mm land) leaves the floor bearing on the outer ring only.
RING_RELIEFS = (
    ("P03", "fixed hob front MF63 (STOCK_014)", HOB_FIXED, 26.7, +1, 2.3),
    ("P03", "fixed compound front MF74 (STOCK_015)", (-9.5, 13.1), 24.8, +1, 2.8),
    ("P03", "moving compound front MF74 (STOCK_063)", (9.5, 13.1), 28.1, +1, 2.8),
    ("P03", "cam outboard MF63", (10.5, 50.721), 13.2, +1, 2.3),
    ("P04F", "arm pivot front MF74 (STOCK_050)", (9.5, 13.1), 22.3, -1, 2.8),
)
RING_RELIEF_DEPTH = 0.3


def v6_ring_reliefs(app):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    if STATE.get("v6_ring_reliefs"):
        raise RuntimeError("already applied")
    report = {}
    for key in ("P03", "P04F"):
        proxy = by[PARTS[key]]
        cuts = []
        for k, label, (x, z), face, sgn, r in RING_RELIEFS:
            if k == key:
                a, b = sorted((face - .05 * sgn, face + RING_RELIEF_DEPTH * sgn))
                cuts.append((label, s.cyl(x, z, a, b, r)))
        log = []
        new = cut_each(s.tbm().copy(proxy), cuts, log)
        if new.lumps.count != 1 or log:
            raise RuntimeError("%s ring relief failed %s" % (key, log))
        report[key] = {"removed_mm3": round(proxy.volume * 1000 - new.volume * 1000, 2), "cuts": [c[0] for c in cuts]}
        replace(proxy, new, None, None)
    STATE["v6_ring_reliefs"] = report
    (OUT / "v6_ring_reliefs.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


# =============================================================================================
# v7 strength pass (user: "smooth bulky pieces"): find stair-step sweep facets, thin necks, stubs
# =============================================================================================
def stair_faces(body, max_tilt=9.0, min_tilt=0.15):
    """Faces produced by discrete arm-sweep poses: planes whose XZ normal is tilted 0.15..9 deg off an
    axis, and Y-axis cylinders/cones that are rotated copies (centre not on a design axis)."""
    out = []
    for i in range(body.faces.count):
        f = body.faces.item(i)
        g = f.geometry
        fb = f.boundingBox
        bb = [round(v * 10, 2) for v in (fb.minPoint.x, fb.maxPoint.x, fb.minPoint.y, fb.maxPoint.y,
                                         fb.minPoint.z, fb.maxPoint.z)]
        if isinstance(g, adsk.core.Plane):
            n = g.normal
            if abs(n.y) > .999:
                continue
            ang = math.degrees(math.atan2(n.z, n.x)) % 90.0
            tilt = min(ang, 90.0 - ang)
            if min_tilt < tilt < max_tilt:
                out.append({"i": i, "type": "plane", "tilt": round(tilt, 2), "area": round(f.area * 100, 3), "bb": bb})
    return out


def stair_report(app, keys=("P01", "P03", "P04", "P04F"), cell=4.0):
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for b in s.proxies(design.rootComponent)}
    rep = {}
    for k in keys:
        fs = stair_faces(by[PARTS[k]])
        groups = {}
        for f in fs:
            c = ((f["bb"][0] + f["bb"][1]) / 2, (f["bb"][2] + f["bb"][3]) / 2, (f["bb"][4] + f["bb"][5]) / 2)
            key = tuple(int(math.floor(v / cell)) for v in c)
            g = groups.setdefault(key, {"n": 0, "area": 0.0, "bb": [1e9, -1e9, 1e9, -1e9, 1e9, -1e9], "tilts": set()})
            g["n"] += 1
            g["area"] += f["area"]
            g["tilts"].add(f["tilt"])
            for a in range(3):
                g["bb"][2 * a] = min(g["bb"][2 * a], f["bb"][2 * a])
                g["bb"][2 * a + 1] = max(g["bb"][2 * a + 1], f["bb"][2 * a + 1])
        rows = sorted(({"n": g["n"], "area": round(g["area"], 2), "bb": [round(v, 1) for v in g["bb"]],
                        "tilts": sorted(g["tilts"])[:6]} for g in groups.values()), key=lambda r: -r["area"])
        rep[k] = {"faces": by[PARTS[k]].faces.count, "stair_faces": len(fs),
                  "stair_area": round(sum(f["area"] for f in fs), 1), "regions": rows}
    (OUT / "v7_stairs.json").write_text(json.dumps(rep, indent=1))
    return rep

def mark_shot(app, key, name, views, red_ids=(), amber_ids=(), others=(), size=(1600, 1200),
              grey=(185, 190, 200)):
    """Copy of a part with chosen face indices in red/amber (plus optional context bodies), one image per view."""
    s = load("pancake_paths_study")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    by = {b.name: b for b in s.proxies(root)}
    part = by[PARTS[key]] if key in PARTS else by[key]

    def fkey(f):
        b = f.boundingBox
        return (round(f.area * 100, 2), round(b.minPoint.x * 10, 2), round(b.maxPoint.x * 10, 2), round(b.minPoint.y * 10, 2),
                round(b.maxPoint.y * 10, 2), round(b.minPoint.z * 10, 2), round(b.maxPoint.z * 10, 2))
    rk = {fkey(part.faces.item(i)) for i in red_ids}
    ak = {fkey(part.faces.item(i)) for i in amber_ids}
    look = rgb_appearance(design, "intent red", (225, 40, 40))
    amber = rgb_appearance(design, "intent amber", (240, 170, 30))
    items = [(s.tbm().copy(part), rgb_appearance(design, "intent grey", grey))]
    for o in others:
        shape = o if not isinstance(o, str) else s.tbm().copy(by[o])
        items.append((shape, rgb_appearance(design, "intent ctx", (90, 140, 210))))
    states = [(occ, occ.isLightBulbOn) for occ in root.occurrences]
    group = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    group.component.name = "TEMP mark"
    try:
        feat = group.component.features.baseFeatures.add()
        feat.startEdit()
        try:
            for i, (shape, _) in enumerate(items):
                body = group.component.bRepBodies.add(shape, feat)
                if i == 0:
                    for f in body.faces:
                        k = fkey(f)
                        if k in rk:
                            f.appearance = look
                        elif k in ak:
                            f.appearance = amber
        finally:
            feat.finishEdit()
        for body, (_, appearance) in zip(group.component.bRepBodies, items):
            body.appearance = appearance
        for occ, _ in states:
            occ.isLightBulbOn = False
        for suffix, eye, target, up, ext in views:
            camera_shot(app, name + suffix + ".png", eye, target, up, ext, size)
    finally:
        group.deleteMe()
        for occ, state in states:
            if occ.isValid:
                occ.isLightBulbOn = state
    return name


def std_views(c, ext, which=("front", "front_iso", "rear_iso")):
    """c in mm; returns camera_shot view tuples (cm)."""
    cc = (c[0] / 10, c[1] / 10, c[2] / 10)
    d = {"front": (0, 60, 0), "front_iso": (35, 45, 30), "rear_iso": (-35, -45, 25),
         "low_front_iso": (-30, 40, -35), "rear": (0, -60, 0), "right": (60, 0, 0), "left": (-60, 0, 0),
         "top": (0, 0, 60), "bottom": (0, 0, -60), "low_rear_iso": (35, -45, -30), "plus_x_iso": (50, 25, 20)}
    out = []
    for w in which:
        e = d[w]
        up = (0, 1, 0) if w in ("top", "bottom") else (0, 0, 1)
        out.append(("_" + w, (cc[0] + e[0], cc[1] + e[1], cc[2] + e[2]), cc, up, ext))
    return out


# ---- v7 smooth primitives: arcs about the arm pivot instead of 9-pose stepped unions --------------
PROBE_ANGLES = (0.3, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0, -6.05, -6.5, -7.0, -7.2)


def half_xz(c, phi, y0, y1, L=200.0):
    """Half-space (Y slab) left of the ray from c at polar angle phi (deg, atan2(z, x)): angles phi..phi+180."""
    s = load("pancake_paths_study")
    return rotated(s.box(c[0] - L, c[0] + L, y0, y1, c[1], c[1] + L), c, -phi)


def sector(c, r_in, r_out, a0, a1, y0, y1):
    """Annular sector about c (XZ), polar angles a0..a1 (deg, a1 > a0), Y slab y0..y1."""
    s = load("pancake_paths_study")
    shape = s.cyl(c[0], c[1], y0, y1, r_out)
    if r_in > 1e-3:
        s.op(shape, s.cyl(c[0], c[1], y0 - .1, y1 + .1, r_in), "cut")
    span = a1 - a0
    if span >= 359.9:
        return shape
    if span <= 180.0:
        s.op(shape, half_xz(c, a0, y0 - .1, y1 + .1), "common")
        s.op(shape, half_xz(c, a1 - 180.0, y0 - .1, y1 + .1), "common")
        return shape
    mid = (a0 + a1) / 2.0
    left = sector(c, r_in, r_out, a0, mid, y0, y1)
    s.op(left, sector(c, r_in, r_out, mid, a1, y0, y1), "join")
    return left


def polar(c, p):
    return math.hypot(p[0] - c[0], p[1] - c[1]), math.degrees(math.atan2(p[1] - c[1], p[0] - c[0]))


def rot_pt(p, c, deg):
    """Point p (x, z) after rotated(..., c, deg)."""
    a = math.radians(deg)
    dx, dz = p[0] - c[0], p[1] - c[1]
    return (c[0] + dx * math.cos(a) + dz * math.sin(a), c[1] - dx * math.sin(a) + dz * math.cos(a))


def arc_slot(p, R, t0, t1, y0, y1, c=None):
    """Circle (centre p, radius R, Y slab) swept by rotated(.., c, t) for t in t0..t1: one smooth arc slot."""
    s = load("pancake_paths_study")
    c = c or STATE["Mv"]
    d, phi = polar(c, p)
    lo, hi = min(t0, t1), max(t0, t1)
    p0, p1 = rot_pt(p, c, lo), rot_pt(p, c, hi)
    shape = s.cyl(p0[0], p0[1], y0, y1, R)
    s.op(shape, s.cyl(p1[0], p1[1], y0, y1, R), "join")
    if hi - lo > 1e-6:
        s.op(shape, sector(c, max(0.0, d - R), d + R, phi - hi, phi - lo, y0, y1), "join")
    return shape


def probe_fill(app, shape, angles=PROBE_ANGLES, skip=("CLOSING_SPRING_ENVELOPE",),
               own=("PRINT_carrier_box_left", "PRINT_arm_front_half"), tol=1e-3):
    """Where would an arm-frame solid hit something? Static bodies at every pose (overlap returned in the
    arm frame) and arm-group bodies (other than `own`) at the closed pose."""
    s = load("pancake_paths_study")
    moving, static = arm_split(app)
    Mv = STATE["Mv"]
    fbb = bb_of(shape)
    out = []
    for b in moving:
        if b.name in own or b.name in skip or bb_gap_l(fbb, bb_of(b)) > 0:
            continue
        v, c = s.common_volume(shape, b)
        if v > tol:
            out.append([b.name, "arm", round(v, 3), [round(x, 2) for x in bb_of(c)]])
    for th in angles:
        g = rotated(shape, Mv, th) if th else s.tbm().copy(shape)
        gbb = bb_of(g)
        for b in static:
            if b.name in skip or bb_gap_l(gbb, bb_of(b)) > 0:
                continue
            v, c = s.common_volume(g, b)
            if v > tol:
                cc = rotated(c, Mv, -th) if th else c
                out.append([b.name, th, round(v, 3), [round(x, 2) for x in bb_of(cc)]])
    return out


def probe_summary(rows):
    """Merge probe rows per body: max volume, union bbox (arm frame), poses hit."""
    agg = {}
    for n, th, v, bb in rows:
        a = agg.setdefault(n, {"v": 0.0, "bb": [1e9, -1e9, 1e9, -1e9, 1e9, -1e9], "poses": []})
        a["v"] = max(a["v"], v)
        a["poses"].append(th)
        for i in range(3):
            a["bb"][2 * i] = min(a["bb"][2 * i], bb[2 * i])
            a["bb"][2 * i + 1] = max(a["bb"][2 * i + 1], bb[2 * i + 1])
    return {n: {"v": round(a["v"], 2), "bb": [round(x, 2) for x in a["bb"]], "poses": a["poses"]} for n, a in agg.items()}
