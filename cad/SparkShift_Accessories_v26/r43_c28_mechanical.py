"""Separate Bambu C28 study: paired inclined mounts and a bottom-screwed forked retainer.

The callers supply the frozen current P01/P21/C28 solids. This does not alter R43 or
promote this mechanical study to the CFD-qualified cooling baseline.
"""
import math

import cadquery as cq

import r41_parts as R
import r43_swept_feed as F
from build_bambu_clean_r29 import single

MOUNT_X = (-18.0, 18.0)
MOUNT_Y, MOUNT_Z = 17.0, -55.5
MOUNT_HALF = 4.0
MOUNT_GAP = .05
MOUNT_GRIP = 3.5
MOUNT_NORMAL = cq.Vector(0, math.sqrt(.5), -math.sqrt(.5))
MOUNT_TANGENT = cq.Vector(0, math.sqrt(.5), math.sqrt(.5))
INSERT_R = 2.27
HOLE_R = 1.65
BUTTON_R, BUTTON_H = 2.85, 1.65

RETAINER_Y = -28.2
TONGUE_R = 3.5
TONGUE_BOTTOM, TONGUE_TOP = -65.0, -58.5
SOCKET_CLEARANCE = .25
SEAT_Z = -70.8
FORK_INNER_X = 2.0
ROOT_OUTER_X = 4.0
ROOT_BACK_Y = -33.6
ROOT_BOTTOM = -51.2
ROOT_YZ = [
    (ROOT_BACK_Y, -42.0), (-33.2, -42.0), (-33.2, -49.0),
    (RETAINER_Y, -49.0), (RETAINER_Y, ROOT_BOTTOM), (ROOT_BACK_Y, ROOT_BOTTOM),
]


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def cylinder(x, y, z0, z1, radius):
    return cq.Solid.makeCylinder(radius, z1 - z0, cq.Vector(x, y, z0))


def yz_prism(points, x0, x1):
    wire = cq.Wire.makePolygon([cq.Vector(x0, y, z) for y, z in points], close=True)
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(x1 - x0, 0, 0))


def checked(body, label):
    if not body.isValid() or len(body.Solids()) != 1 or len(body.Shells()) != 1:
        raise ValueError(f"{label}: valid={body.isValid()}, solids={len(body.Solids())}, "
                         f"shells={len(body.Shells())}, volumes={[s.Volume() for s in body.Solids()]}")
    return single(body, label)


def mount_point(x, normal=0, tangent=0):
    return cq.Vector(x, MOUNT_Y, MOUNT_Z) + MOUNT_NORMAL * normal + MOUNT_TANGENT * tangent


def mount_cylinder(x, start, end, radius):
    return cq.Solid.makeCylinder(radius, end - start, mount_point(x, start), MOUNT_NORMAL)


def mount_pad(x, start, end):
    points = [mount_point(x + dx, start, tangent) for dx, tangent in
              ((-MOUNT_HALF, -MOUNT_HALF), (MOUNT_HALF, -MOUNT_HALF),
               (MOUNT_HALF, MOUNT_HALF), (-MOUNT_HALF, MOUNT_HALF))]
    return cq.Solid.extrudeLinear(cq.Wire.makePolygon(points, close=True), [],
                                  MOUNT_NORMAL * (end - start))


def p01(base):
    body = base
    for x in MOUNT_X:
        body = body.cut(box(x - 4.1, x + 4.1, 11.4, 16.0, -58.4, -50.1))
        low, high = mount_point(x, tangent=-MOUNT_HALF), mount_point(x, tangent=MOUNT_HALF)
        rear_high = mount_point(x, -5.0, MOUNT_HALF)
        root = yz_prism([(11.2, -57.2), (low.y, low.z), (high.y, high.z),
                         (rear_high.y, rear_high.z), (11.2, rear_high.z)],
                        x - MOUNT_HALF, x + MOUNT_HALF)
        body = body.fuse(root)
        body = body.cut(mount_cylinder(x, -4.25, .1, INSERT_R))
        body = body.cut(mount_cylinder(x, -5.0, .1, HOLE_R))
    return checked(body, "C28 paired inclined P01 mounts")


def angled_p22(base):
    horn = R.shape(R.a.prism_yz_r(R.HORN_OUT, R.HORN_OUT_R, -23, 23))
    air = F.main_channel_air()
    body = base
    for x in MOUNT_X:
        old_cheek = box(x - 4.5, x + 4.5, 11.35, 21.3, -65.7, -49.0).cut(horn)
        body = body.cut(old_cheek)
        pad = mount_pad(x, MOUNT_GAP, MOUNT_GAP + MOUNT_GRIP)
        low = mount_point(x, MOUNT_GAP, -MOUNT_HALF)
        far = mount_point(x, MOUNT_GAP + MOUNT_GRIP, -MOUNT_HALF)
        root = yz_prism([(low.y, low.z), (far.y, far.z),
                         (far.y + 1.0, far.z - 2.0), (low.y, low.z - 2.0)],
                        x - MOUNT_HALF, x + MOUNT_HALF)
        addition = pad.fuse(root, tol=.005).cut(air)
        body = body.fuse(addition, tol=.005)
        body = body.cut(mount_cylinder(x, -.1, MOUNT_GAP + MOUNT_GRIP + .1, HOLE_R))
    return checked(body, "C28 paired inclined P22 mounts")


def tongue():
    lower = cylinder(0, RETAINER_Y, TONGUE_BOTTOM, TONGUE_TOP, TONGUE_R)
    fork = cylinder(0, RETAINER_Y, TONGUE_TOP - .1, -49.0, TONGUE_R)
    fork = fork.cut(box(-FORK_INNER_X, FORK_INNER_X, -40, -20, TONGUE_TOP, -48.9))
    roots = []
    for x0, x1 in ((FORK_INNER_X, ROOT_OUTER_X), (-ROOT_OUTER_X, -FORK_INNER_X)):
        root = yz_prism(ROOT_YZ, x0, x1)
        corner = [e for e in root.Edges()
                  if abs(e.Center().y + 33.2) < 1e-6 and abs(e.Center().z + 49.0) < 1e-6]
        if len(corner) != 1:
            raise ValueError(f"Tongue root: expected one inside corner, found {len(corner)}")
        roots.append(root.fillet(.5, corner))
    return checked(lower.fuse(fork, *roots), "Forked mid-duct tongue")


def p21(base):
    body = base.fuse(tongue())
    body = body.cut(cylinder(0, RETAINER_Y, TONGUE_BOTTOM - .1, -61.0, INSERT_R))
    body = body.cut(cylinder(0, RETAINER_Y, TONGUE_BOTTOM - .1, -60.5, HOLE_R))
    return checked(body, "C28 P21 with forked bottom-screw tongue")


def root_slots():
    out = []
    for side in (-1, 1):
        x0, x1 = sorted((side * (FORK_INNER_X - SOCKET_CLEARANCE),
                         side * (ROOT_OUTER_X + SOCKET_CLEARANCE)))
        out.append(box(x0, x1, ROOT_BACK_Y - SOCKET_CLEARANCE, RETAINER_Y,
                       ROOT_BOTTOM - SOCKET_CLEARANCE, -48.9))
    return out


def root_reinforcements():
    # Rounded floor extensions keep the root notches from leaving a thin inlet roof.
    # They are a deliberate local air-boundary change, requiring new CFD before adoption.
    wall = 1.25
    floor = ROOT_BOTTOM - SOCKET_CLEARANCE
    x0, x1 = FORK_INNER_X - SOCKET_CLEARANCE, ROOT_OUTER_X + SOCKET_CLEARANCE
    y0 = ROOT_BACK_Y - SOCKET_CLEARANCE
    outer = box(x0 - wall, x1 + wall, y0 - wall, RETAINER_Y + wall,
                floor - wall, -48.9 + wall)
    vertical = [e for e in outer.Edges() if abs(e.tangentAt().z) > .99]
    outer = outer.fillet(wall, vertical)
    bottom = [e for e in outer.Edges()
              if abs(e.BoundingBox().zmin - (floor - wall)) < 1e-6
              and abs(e.BoundingBox().zmax - (floor - wall)) < 1e-6]
    outer = outer.chamfer(.35, .35, bottom)
    outer = outer.intersect(box(FORK_INNER_X, 10, -40, -20, -60, -51.4))
    return [outer, outer.mirror("YZ")]


def retained_p22(base):
    body = base
    for addition in [cylinder(0, RETAINER_Y, SEAT_Z, TONGUE_BOTTOM - SOCKET_CLEARANCE, 4.8),
                     *root_reinforcements()]:
        body = body.fuse(addition, tol=.005)
    socket = cylinder(0, RETAINER_Y, TONGUE_BOTTOM - SOCKET_CLEARANCE, -48,
                      TONGUE_R + SOCKET_CLEARANCE)
    for cutter in [socket, *root_slots()]:
        body = body.cut(cutter)
    body = body.cut(cylinder(0, RETAINER_Y, SEAT_Z - .1, TONGUE_BOTTOM, HOLE_R))
    return checked(body, "C28 P22 bottom-screw receiver")


def hardware():
    out = []
    seat = MOUNT_GAP + MOUNT_GRIP
    for i, x in enumerate(MOUNT_X):
        screw = mount_cylinder(x, seat - 8, seat, 1.5).fuse(
            mount_cylinder(x, seat, seat + BUTTON_H, BUTTON_R))
        insert = mount_cylinder(x, -4, 0, INSERT_R).cut(mount_cylinder(x, -4.1, .1, 1.5))
        out.extend(((f"C28_P22_P01_M3x8_BUTTON_{i}", screw),
                    (f"C28_P22_P01_M3x4_HEATSET_{i}", insert)))
    screw = cylinder(0, RETAINER_Y, SEAT_Z, SEAT_Z + 10, 1.5).fuse(
        cylinder(0, RETAINER_Y, SEAT_Z - BUTTON_H, SEAT_Z, BUTTON_R))
    insert = cylinder(0, RETAINER_Y, TONGUE_BOTTOM, -61.0, INSERT_R).cut(
        cylinder(0, RETAINER_Y, TONGUE_BOTTOM - .1, -60.9, 1.5))
    out.extend((("C28_P21_P22_M3x10_BUTTON", screw), ("C28_P21_P22_M3x4_HEATSET", insert)))
    return out
