"""Separate Bambu-focused printability variant of cleaned C28, not a released R43 edit.

The 0.9 mm, 28-degree airway is protected while the direct-mount seat's
down-facing steps are ramped or notched for the established back-face-down
orientation. Manufacturing and external-flow qualification are separate.
"""
import cadquery as cq

import r37_parts as P37
import r41_parts as R41
import r42_parts as R42
import r43_swept_feed as R
from build_bambu_clean_r29 import single

LEG_X = (11.5, 20.4)
LEG_REAR_Y = -14.2
RELIEF_FRONT_Y = -7.95
SEAT_WINDOW_Y = -5.8
SEAT_WINDOW_HALF = 11.5
SEAT_NOTCH_FRONT_Y = 2.3


def yz_prism(points, x0, x1):
    wire = cq.Wire.makePolygon([cq.Vector(x0, y, z) for y, z in points]
                              + [cq.Vector(x0, *points[0])])
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(x1 - x0, 0, 0))


def rear_leg_ramps():
    top, bottom = P37.Z_TOP, P37.RELIEF_TOP
    front = LEG_REAR_Y
    back = front - (top - bottom)
    points = [(back, top), (back, top + .02), (front + .02, top + .02),
              (front + .02, bottom), (front, bottom)]
    return [yz_prism(points, *sorted((side * LEG_X[0], side * LEG_X[1])))
            for side in (-1, 1)]


def relief_step_chamfers(probe):
    floor = P37.Z_SEAT if probe == "Beacon" else R42.SEAT
    height = P37.RELIEF_TOP - floor
    y = RELIEF_FRONT_Y
    points = [(y - .01, floor - .01), (y - .01, P37.RELIEF_TOP + .01),
              (y + height + .01, floor - .01)]
    return [yz_prism(points, *sorted((side * LEG_X[0], side * LEG_X[1])))
            for side in (-1, 1)]


def protected_passage():
    return R41.fuse(R.nozzle(True, 3.0, .9, 28.0, conformal_outlet=True),
                    R.feed(-1, True, 3.0), R.feed(1, True, 3.0))


def seat_notch(probe):
    half, rear, front = SEAT_WINDOW_HALF, SEAT_WINDOW_Y, SEAT_NOTCH_FRONT_Y
    tip_half = half - (front - rear)
    points = [(-half, rear - 2), (half, rear - 2), (half, rear),
              (tip_half, front), (-tip_half, front), (-half, rear)]
    floor = P37.Z_SEAT if probe == "Beacon" else R42.SEAT
    return R41.shape(R41.a.prism_xy_r(points, [0.] * len(points), floor - .05, P37.Z_TOP + .05))


def p22(base, probe="Beacon"):
    """Apply only to the frozen cleaned C28 base; preserve its airway and live mounts."""
    if probe not in ("Beacon", "Cartographer"):
        raise ValueError(f"Unknown probe: {probe}")
    guard = protected_passage()
    cutters = [R41.cut(seat_notch(probe), [guard])]
    cutters += relief_step_chamfers(probe)
    body = base.fuse(*rear_leg_ramps(), tol=.005)
    body = R41.cut(body, cutters)
    for candidate in (body, R41.unify(body), R.RJ.fixed(body)):
        if candidate.isValid() and len(candidate.Solids()) == len(candidate.Shells()) == 1:
            return single(candidate, f"Cleaned C28 printability study, {probe}")
    raise ValueError(f"C28 printability study, {probe}: no valid single solid/shell")
