"""Separate routing study: upstream Y-feeds over the probe and a nose-following angled outlet.

The released R43 and the earlier centre-feed study are unchanged. Unlike the latter, this has
an enclosed floor above the PCB, no transverse plenum, and no manifold below the probe. The
outlet follows the board's nose and points down toward the nozzle. This is geometry, not a
claim of improved cooling; CFD and print qualification are still required.
"""
import math

import cadquery as cq
from OCP.BRepOffset import BRepOffset_Mode
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape
from OCP.GeomAbs import GeomAbs_JoinType

import r37_parts as P37
import r41_parts as R41
import r42_parts as R42
import r43_centre_feed as CF
import r43_parts as R43
import r43_rear_jet as RJ
from build_bambu_clean_r29 import single

WALL = 0.8
HALF_WIDTH = 9.0
ANGLE = math.radians(32.0)
DIRECTION = cq.Vector(0, math.cos(ANGLE), -math.sin(ANGLE))
UP = cq.Vector(0, math.sin(ANGLE), math.cos(ANGLE))
MOUTH_Z = -73.25
MOUTH_HEIGHT = 1.3
NOSE_STANDOFF = 1.2
START_Y = 4.0
FLOOR_Z = -72.5
NOSE = (11.700, 11.654, 11.483, 11.174, 10.733, 10.265, 9.797, 9.329, 8.862, 8.394, 7.926)
# y, |x| centre, z centre, width, height; take air through the existing island's
# inner walls, ahead of the cable, clearing the Cartographer header at Y-6.04.
FEED = (
    (-10.0, 16.0, -65.0, 4.2, 5.0),
    (-6.0, 14.4, -65.7, 3.8, 4.8),
    (-2.0, 10.7, -67.3, 4.0, 4.2),
    (1.0, 7.3, -69.4, 7.0, 3.2),
    (4.5, 4.3, -71.5, 9.0, 2.0),
)


def nose_y(x):
    x = abs(x)
    if x > len(NOSE) - 1:
        raise ValueError(f"Nose profile outside measured span: {x}")
    i = min(int(x), len(NOSE) - 2)
    return NOSE[i] + (x - i) * (NOSE[i + 1] - NOSE[i])


def mouth(x):
    # More setback outboard clears the PCB under the normal-offset, swept floor.
    setback = NOSE_STANDOFF + 0.8 * (x / HALF_WIDTH) ** 2
    return cq.Vector(x, nose_y(x) + setback, MOUTH_Z)


def outlet_axes(angle_deg=32.0):
    angle = math.radians(angle_deg)
    return (cq.Vector(0, math.cos(angle), -math.sin(angle)),
            cq.Vector(0, math.sin(angle), math.cos(angle)))


def profile(x, extension=0.0, roof_raise=0.0, mouth_height=MOUTH_HEIGHT, angle_deg=32.0,
            floor_reference_height=None):
    """A YZ passage section; only the air extends beyond the intended outlet."""
    front = nose_y(x)
    end = mouth(x)
    direction, up = outlet_axes(angle_deg)
    high, low = end + up * (mouth_height / 2), end - up * (mouth_height / 2)
    if floor_reference_height is not None:
        low = end - up * (floor_reference_height / 2)
        high = end + up * (mouth_height - floor_reference_height / 2)
    roof_start = cq.Vector(x, START_Y, -70.5 + roof_raise)
    floor_start = cq.Vector(x, START_Y, FLOOR_Z)
    # Bezier control points bound the floor instead of letting an interpolating spline
    # dip into the higher Cartographer PCB between otherwise-clear sections.
    roof = cq.Edge.makeBezier([roof_start, cq.Vector(x, front - 2.2, -70.5 + roof_raise),
                               high - direction * 1.2, high])
    floor = cq.Edge.makeBezier([low, low - direction * 0.8,
                                cq.Vector(x, front + 0.4, FLOOR_Z),
                                cq.Vector(x, front + 0.3, FLOOR_Z),
                                cq.Vector(x, front - 2.0, FLOOR_Z), floor_start])
    rear = cq.Edge.makeLine(floor_start, roof_start)
    edges = [roof, cq.Edge.makeLine(high, low), floor, rear]
    if extension:
        # Extend only the outlet, keeping all other vertices and their topology unchanged.
        e_high, e_low = high + direction * extension, low + direction * extension
        edges = [roof, cq.Edge.makeLine(high, e_high),
                 cq.Edge.makeLine(e_high, e_low), cq.Edge.makeLine(e_low, low),
                 floor, rear]
    return cq.Wire.assembleEdges(edges)


def offset(solid):
    """A true normal offset; padding loft sections in X/Z makes the diagonal walls thinner."""
    builder = BRepOffsetAPI_MakeOffsetShape()
    builder.PerformByJoin(solid.wrapped, WALL, 1e-4, BRepOffset_Mode.BRepOffset_Skin,
                          False, False, GeomAbs_JoinType.GeomAbs_Arc, True)
    if not builder.IsDone():
        raise ValueError("Swept passage wall offset failed")
    result = cq.Shape.cast(builder.Shape())
    if len(result.Solids()) != 1 or not result.isValid():
        raise ValueError("Swept passage wall offset is not one valid solid")
    return result


def mouth_keep(angle_deg=32.0):
    """Upstream side of the curved outlet, extended beyond the nozzle's side walls."""
    wires = []
    direction, up = outlet_axes(angle_deg)
    for x in (-9.9, -9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0, 9.9):
        end = mouth(x)
        points = [end + up * 30, end - up * 30,
                  end - up * 30 - direction * 60, end + up * 30 - direction * 60]
        wires.append(cq.Wire.makePolygon(points + [points[0]]))
    return cq.Solid.makeLoft(wires)


def nozzle(outer=False, roof_raise=0.0, mouth_height=MOUTH_HEIGHT, angle_deg=32.0,
           conformal_outlet=False, floor_reference_height=None):
    """Optionally offset the exact extended air loft, avoiding topology-dependent surface drift."""
    xs = (-HALF_WIDTH, -6.0, -3.0, 0.0, 3.0, 6.0, HALF_WIDTH)
    inner = cq.Solid.makeLoft([
        profile(x, 0 if outer and not conformal_outlet else 0.7,
                roof_raise, mouth_height, angle_deg, floor_reference_height) for x in xs])
    return offset(inner).intersect(mouth_keep(angle_deg)) if outer else inner


def feed(side, outer=False, roof_raise=0.0):
    wires = []
    for y, x, z, width, height in FEED:
        z += roof_raise / 2
        height += roof_raise
        points = [cq.Vector(x + dx * width / 2, y, z + dz * height / 2)
                  for dx, dz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        wires.append(cq.Wire.makePolygon(points + [points[0]]))
    solid = cq.Solid.makeLoft(wires)
    if outer:
        solid = offset(solid)
    return solid if side == 1 else solid.mirror("YZ")


def air(roof_raise=0.0, mouth_height=MOUTH_HEIGHT, angle_deg=32.0, floor_reference_height=None):
    return R41.fuse(nozzle(roof_raise=roof_raise, mouth_height=mouth_height, angle_deg=angle_deg,
                          floor_reference_height=floor_reference_height),
                    feed(-1, roof_raise=roof_raise), feed(1, roof_raise=roof_raise))


def main_channel_air():
    """Full-height original channel clearance, including the raised feed's upper junction."""
    zs = [z for _, z in R41.HORN_IN]
    return R41.common(R41.horn_in(-23.0, 23.0), [
        R41.p22_air_xy(min(zs) - 1.0, max(zs) + 1.0)])


def clean_direct_mount(part):
    """Remove obsolete P23 rear ears/bosses and close their blind insert bores."""
    plugs = [
        R41.shape(R41.a.cyl_z(x, y, P37.INSERT_HOLE_Z[0], P37.INSERT_HOLE_Z[1], 2.27))
        for x, y in P37.REAR_XY
    ]
    body = part.fuse(*plugs, tol=0.005)
    cutters = [
        R41.shape(R41.a.box(*sorted((side * P37.EAR_X[0], side * P37.EAR_X[1])),
                           P37.EAR_Y_REAR - 0.1, -14.2, P37.Z_SEAT - 1, P37.Z_TOP))
        for side in (-1, 1)
    ]
    return single(R41.unify(R41.cut(body, cutters)), "Direct mount without obsolete P23 rear ears")


def p22(base=None, probe="Beacon", roof_raise=0.0, mouth_height=MOUTH_HEIGHT, angle_deg=32.0,
        remove_rear_mounts=False, conformal_outlet=False, clear_feed_intrusions=False,
        floor_reference_height=None):
    """Opt-in cleanups preserve historical CFD geometry by default."""
    if not math.isfinite(roof_raise) or roof_raise < 0:
        raise ValueError(f"Invalid swept-feed roof raise: {roof_raise}")
    if not math.isfinite(mouth_height) or mouth_height <= 0:
        raise ValueError(f"Invalid swept-feed mouth height: {mouth_height}")
    if not math.isfinite(angle_deg) or not 0 < angle_deg < 90:
        raise ValueError(f"Invalid swept-feed outlet angle: {angle_deg}")
    if floor_reference_height is not None and (
            not math.isfinite(floor_reference_height) or floor_reference_height <= 0):
        raise ValueError(f"Invalid swept-feed floor reference height: {floor_reference_height}")
    if probe not in ("Beacon", "Cartographer"):
        raise ValueError(f"Unknown probe: {probe}")
    seat = CF.seat()
    if probe == "Cartographer":
        seat = seat.cut(R41.shape(R41.a.box(-25, 25, -30, 15, P37.Z_SEAT - 1, R42.SEAT)))
    base = base if base is not None else R43.p22()
    # The inherited heel-only clearance stops at Z-60; raised feeds also enter the channel above it.
    clearance = main_channel_air() if clear_feed_intrusions else RJ.duct_air()
    envelope = R41.cut(R41.fuse(nozzle(True, roof_raise, mouth_height, angle_deg,
                                     conformal_outlet=conformal_outlet,
                                     floor_reference_height=floor_reference_height), feed(-1, True, roof_raise),
                                feed(1, True, roof_raise)), [clearance])
    mounted = R41.fuse(base, seat)
    # Offset/Bezier tangent faces need a 5 micron coincidence tolerance. OCC otherwise
    # reports a valid union containing only the envelope, silently losing the original P22.
    body = mounted.fuse(envelope, tol=0.005)
    if body.Volume() < mounted.Volume() - 0.01:
        raise ValueError("Swept passage union lost the original P22 or probe mount")
    passage = air(roof_raise, mouth_height, angle_deg, floor_reference_height)
    body = R41.cut(body, [passage])
    retained = base.cut(passage)
    for candidate in (body, R41.unify(body), RJ.fixed(body)):
        if (len(candidate.Solids()) == 1 and candidate.Solids()[0].isValid()
                and candidate.Volume() > base.Volume()
                and retained.cut(candidate).Volume() < 0.01):
            result = single(candidate, f"R43 swept-feed routing study, {probe}")
            return clean_direct_mount(result) if remove_rear_mounts else result
    raise ValueError(f"R43 swept-feed routing study, {probe}: no valid single solid")
