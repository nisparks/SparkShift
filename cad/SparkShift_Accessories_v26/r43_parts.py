"""Revision 43: P22's jets, after printing revision 41.

With revision 41's CPAP set printed, P20 and P21 fit well, but P22 still restricts the blower and its output at the
nozzle could be better. Revision 41's CFD (cfd_cpap_r41.py) says why: the jets carry 85 % of the duct's pressure,
because the air has to leave through about 60 mm2 at 51 m/s (180 L/min). Each jet is the slot under the wall between
its side channel and the hotend slot, as tall as the space allows: the floor (Z-76.65) is 1.2 mm over P22's underside
(1 mm above the nozzle tip) and the wall's flat bottom (Z-73.6) is 0.32 mm under the Red Lizard's heater block. Each
already runs the length of the hotend (Y16.7-28.2, against the nozzle at Y22.7).

Revision 43 changes two things under the duct-to-slot wall on each side, and nothing else:
  - the jet's floor drops 0.4 mm, following revision 41's floor: flat at Z-77.05 from Y22.4 to the front wall, and
    0.4 mm lower along the heel's curve back to Y19. That leaves 0.8 mm (two perimeters) over P22's underside, which
    doesn't move, and makes each jet 13 % taller where it faces the nozzle;
  - the bell-mouth round on the wall's duct-side bottom edge grows from r 1.4 to r 2.4, from the jet's heel (Y16.7)
    to Y26.2, on a foot 1 mm proud of the wall's duct face with a 45 degree chamfer back up to it. Behind Y17.6 the
    foot narrows at 45 degrees in plan, so with P22 on its back face it prints without support.
The lower floor lets the blower move more air, but on its own the jets leave steeper and more of the air splashes up
behind the hotend; the larger round turns the air into the jets more gently, and they leave as flat as revision 41's.
The jets' top, the hotend slot (|X| 10.2), the duct upstream and every interface stay as they were. The CFD
(cfd_cpap_r43.py, verification_cfd_cpap_r43.json) has the numbers; the studies below are the variants it compared.
"""
import math

import cadquery as cq

import r41_parts as R41
from build_bambu_clean_r29 import single

a = R41.a
shape, fuse, cut, common, unify = R41.shape, R41.fuse, R41.cut, R41.common, R41.unify

NAMES = {
    "p22": "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW",
    "assembly": "43_CPAP_Outlet_Complete_REVIEW",
    "review": "43_CPAP_Outlet_REVIEW",
}

ROOF, WALL_X = R41.ROOF, R41.WALL_X   # the jets' top (Z-73.6) and the duct-to-slot wall (|X| 10.2-11.6)
FLOOR, UNDER = -76.65, -77.85         # revision 41's jet floor where it is flat (Y22.38 on) and P22's underside
DROP = 0.4                            # revision 43 moves the jets' floor down this much: 0.8 mm left over the underside
LOW_FLOOR = FLOOR - DROP
LOW_X = (WALL_X[0] - 0.05, 12.85)     # |X|: from inside the hotend slot out to before the front wall's r3 corner (12.89)
LOW_Y0 = 19.0                         # from here forward; behind it the floor climbs the heel as in revision 41
FRONT_WALL = (R41.XY_INNER[8], R41.XY_INNER[9])   # the duct's front inner wall, slanting back outboard of |X| 8.5
BELL_R = 2.4                          # the bell-mouth's radius (revision 41: 1.4, the wall's thickness)
BELL_Y = (17.6, R41.JET_LIP_Y[1])     # the full round: where the wall's duct face is straight, to Y26.2 as revision 41's
BELL_HEEL = R41.HEEL_Y                # with the taper the round starts here, where the jet does (Y16.69), as revision
                                      # 41's; behind it the hotend slot widens (|X| 11.65 behind Y16.5) and nothing changes


def inside(z0, z1):
    """Inside the duct's outer wall in plan (build_p22_lower_plenum's xy_inner_full)."""
    return a.prism_xy_r(R41.XY_INNER, R41.XY_INNER_R, z0, z1)


def mirror(pts, side):
    return pts if side > 0 else [(-x, z) for x, z in pts][::-1]


def duct_air(dz, x0, x1):
    """The duct's air in side view (revision 41's horn_in), moved dz in Z."""
    return a.prism_yz_r([(y, z + dz) for y, z in R41.HORN_IN], R41.HORN_IN_R, x0, x1)


def front_chamfer(side):
    """The floor under a 45 degree slope over the lowered floor's last DROP before the front wall, so with P22 on its
    back face that end of the jet is a 45 degree overhang, not a ceiling. Built along the wall's slanted face."""
    (x0, y0), (x1, y1) = FRONT_WALL
    d = DROP + 0.2
    pts = [(-d, LOW_FLOOR - 0.3), (d, LOW_FLOOR - 0.3), (d, FLOOR + d), (-d, FLOOR - d)]   # local Y: 0 on the face
    w = shape(a.prism_yz_r(pts, [0] * 4, 0.0, math.hypot(x1 - x0, y1 - y0)))
    w = w.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), math.degrees(math.atan2(y1 - y0, x1 - x0)))
    w = w.translate(cq.Vector(x0, y0, 0.0))
    return w if side > 0 else w.mirror("YZ")


def pocket(side):
    """Under one jet: the band between revision 41's floor and that floor moved DROP down, so the floor stays at
    least 0.8 mm thick where it climbs the heel (P22's underside curves up from Y21.99), from LOW_Y0 to the front wall
    and across LOW_X, less the front chamfer. Its back and outboard ends are plain steps DROP high."""
    lo, hi = sorted((side * LOW_X[0], side * LOW_X[1]))
    band = cut(common(a.box(lo, hi, LOW_Y0, 29.0, UNDER, ROOF), [duct_air(-DROP, lo - 1.0, hi + 1.0)]),
               [duct_air(0.01, lo - 1.0, hi + 1.0)])
    return cut(common(band, [inside(UNDER - 1.0, ROOF + 1.0)]), [front_chamfer(side)])


def bell_fill(side, taper=True):
    """The corner under the wall, from its slot face out to |X| WALL_X[0] + BELL_R and BELL_R up from ROOF, with a
    45 degree chamfer back to the wall's duct face above, only where the duct's air is. With the taper it starts at
    BELL_HEEL, and the foot outside the wall's duct face is cut by a vertical plane at 45 degrees in plan that reaches
    its full width at BELL_Y[0]: |X| <= WALL_X[1] + (Y - BELL_Y[0]) + (BELL_R - wall)."""
    x0, x1 = WALL_X[0], WALL_X[0] + BELL_R
    top = ROOF + BELL_R + (x1 - WALL_X[1])
    pts = [(x0, ROOF), (x1, ROOF), (x1, ROOF + BELL_R), (WALL_X[1], top), (x0, top)]
    y0 = BELL_HEEL if taper else BELL_Y[0]
    fill = common(shape(a.prism_xz_r(mirror(pts, side), [0] * 5, y0, BELL_Y[1])), [R41.horn_in(-23.0, 23.0)])
    if not taper:
        return fill
    ys = BELL_Y[0] - (x1 - WALL_X[1])            # where the plane crosses the wall's duct face
    plan = mirror([(x0 - 1.0, ys - 3.0), (WALL_X[1], ys - 3.0), (WALL_X[1], ys), (x1 + 1.0, BELL_Y[0] + 1.0),
                   (x1 + 1.0, BELL_Y[1] + 1.0), (x0 - 1.0, BELL_Y[1] + 1.0)], side)
    return common(fill, [a.prism_xy_r(plan, [0] * 6, ROOF - 1.0, top + 1.0)])


def bell_cut(side, taper=True):
    """The round: revision 41's on the larger radius, centred on the slot face BELL_R above ROOF."""
    y0 = BELL_HEEL if taper else BELL_Y[0]
    x = side * WALL_X[0]
    lo, hi = sorted((x, side * (WALL_X[0] + BELL_R + 0.3)))
    corner = shape(a.box(lo, hi, y0, BELL_Y[1], ROOF - 0.01, ROOF + BELL_R))
    corner = corner.cut(shape(a.cyl_y(x, ROOF + BELL_R, y0 - 0.1, BELL_Y[1] + 0.1, BELL_R)))
    return common(corner, [R41.horn_in(lo - 1.0, hi + 1.0)])


def with_bell(body, taper=True):
    body = fuse(body, *[bell_fill(s, taper) for s in (-1, 1)])
    return cut(body, [bell_cut(s, taper) for s in (-1, 1)])


# --------------------------------------------------------------------------------------------
# Printing. P22 prints on its back face (the duct then runs up the build, and the jets' layer lines run along the
# flow); no other side has less overhang, and every orientation that needs no support rests on an edge. On its back
# face revision 41 needed support in three places, and revision 43 removes two of them:
#   - the window between the side channels (the probe's connector and cable come up through it) ends in front at a
#     flat face, Y-5.4, which printed as a 22.9 mm ceiling. Revision 43 cuts a 45 degree notch into the solid block
#     in front of it, to an apex at Y6.05, 2.25 mm behind the hotend slot. The block's bottom WINDOW_SKIN stays, so
#     P23 still bears on all of P22's underside; it prints as a 1.8 mm-wide bridge;
#   - the round on the bottom-back edge (r16) faced the plate where it met the back face: its first half becomes a
#     45 degree chamfer, tangent to the rest of the round, which also lengthens the flat back face on the plate from
#     5.8 to 12.4 mm. Nothing else is within 1.44 mm of the corner. The back face's two corners in plan (r3.5, which
#     faced the plate for their first half millimetre) become sharp.
# The cheeks' bearing faces (on P01's bosses, with P01 behind them) still need support: in print they are ceilings
# 8.5 mm wide, cantilevered 10 mm from the duct. Everything else bridges at most 15.4 mm.
# --------------------------------------------------------------------------------------------
WINDOW_FRONT, WINDOW_HALF = -5.40, 11.45  # the window's front face and half-width (build_p22_lower_plenum's valleys)
WINDOW_SKIN = (-70.80, -69.00)            # the block's underside, left under the notch for P23 to bear on
BACK_Y, BOTTOM_Z, BACK_R = -45.40, -70.80, 16.0   # the back face, the underside behind the heel, the round between
XY_OUTER = [(-13.00, -45.40), (-20.60, -38.20), (-20.60, -25.30), (-22.42, -19.50), (-22.42, 15.00), (-20.40, 22.50),
            (-14.80, 28.40), (-8.50, 29.60), (-8.50, 11.20), (8.50, 11.20), (8.50, 29.60), (14.80, 28.40),
            (20.40, 22.50), (22.42, 15.00), (22.42, -19.50), (20.60, -25.30), (20.60, -38.20), (13.00, -45.40)]
XY_OUTER_R = [3.5, 3.5, 16.0, 16.0, 12.0, 10.0, 4.0, 0.8, 0.0, 0.0, 0.8, 4.0, 10.0, 12.0, 16.0, 16.0, 3.5, 3.5]
XY_OUTER_SHARP_R = [0.0] + XY_OUTER_R[1:-1] + [0.0]   # the back face's two corners in plan, sharp (were r3.5)


def window_notch():
    """The 45 degree notch in plan at the window's front, through the block above WINDOW_SKIN. Its faces start at
    the window's front corners; behind Y-5.4 it only overlaps the window's own air."""
    w, y0 = WINDOW_HALF, WINDOW_FRONT
    plan = [(-w, y0 - 0.5), (w, y0 - 0.5), (w, y0), (0.0, y0 + w), (-w, y0)]
    return shape(a.prism_xy_r(plan, [0] * 5, WINDOW_SKIN[1], -50.0))


def back_chamfer():
    """Material between the r16 round's first half and its tangent at 45 degrees, inside P22's plan outline."""
    c = BACK_R / math.sqrt(2.0)
    ty, tz = BACK_Y + BACK_R - c, BOTTOM_Z + BACK_R - c        # where the chamfer meets the round
    z_back = tz + (ty - BACK_Y)                                  # and the back face
    region = [(BACK_Y, z_back), (ty, tz), (ty, -45.0), (BACK_Y, -45.0)]
    fill = common(shape(a.prism_yz_r(region, [0] * 4, -23.0, 23.0)),
                  [a.prism_xy_r(XY_OUTER, XY_OUTER_SHARP_R, -78.0, -49.0)])
    return cut(fill, [a.prism_yz_r(R41.HORN_OUT, R41.HORN_OUT_R, -23.0, 23.0)])


def back_corners():
    """The back face's corners in plan made sharp: their r3.5 rounds faced the plate for the first half millimetre."""
    sharp = cut(a.prism_xy_r(XY_OUTER, XY_OUTER_SHARP_R, -78.0, -49.0), [a.prism_xy_r(XY_OUTER, XY_OUTER_R, -79.0, -48.0)])
    return common(sharp, [a.prism_yz_r(R41.HORN_OUT, R41.HORN_OUT_R, -23.0, 23.0)])


def printable(body):
    return cut(fuse(body, back_chamfer(), back_corners()), [window_notch()])


def p22():
    body = with_bell(printable(R41.p22()))
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 P22")


# --------------------------------------------------------------------------------------------
# Studies, not adopted, as simulated (cfd_cpap_r43.py; the bell-mouth in them stops square at Y17.6, no taper):
#   pocket_study()            the lower floor alone (cases r43pocket_*)
#   front_study(bell)         the floor lowered only where revision 41's is flat, Y22.38 on (r43front_*, r43frontbell_*)
#   bell_study(low)           the larger bell-mouth alone (r43bell_*), and with low_study's pocket (r43combo_*)
#   low_study()               the first, flat pocket at LOW_FLOOR from Y19 (r43low_*). Behind Y22.4 it ran under the
#                             heel's curve: a ledge thinning to nothing over a slot with 0.18 mm of floor under it.
#                             Not printable; pocket() follows the floor instead
#   long_jets_study()         below (r43long_*; r43rear_* closed its front 4 mm)
# --------------------------------------------------------------------------------------------
STUDY_LOW_X, STUDY_LOW_RAMP, STUDY_LOW_Y = 13.0, 0.4, (19.0, 28.2)
FRONT_Y0 = 22.38                      # revision 41's floor is flat from here forward (the heel's r6.5 round ends here)


def pocket_study():
    return single(unify(cut(R41.p22(), [pocket(s) for s in (-1, 1)])), "revision-43 lower-floor study")


def front_pocket(side):
    """The floor DROP lower only where revision 41's is flat, with a 45 degree ramp down to it from FRONT_Y0 - DROP."""
    lo, hi = sorted((side * LOW_X[0], side * LOW_X[1]))
    top = FLOOR + 0.03
    band = shape(a.prism_yz_r([(FRONT_Y0 - DROP, top), (FRONT_Y0, LOW_FLOOR), (29.0, LOW_FLOOR), (29.0, top)], [0] * 4, lo, hi))
    return cut(common(band, [inside(UNDER - 1.0, ROOF + 1.0)]), [front_chamfer(side)])


def front_study(bell=False):
    body = with_bell(R41.p22(), taper=False) if bell else R41.p22()
    return single(unify(cut(body, [front_pocket(s) for s in (-1, 1)])), "revision-43 front-floor study")


def low_study_cut(side):
    pts = [(WALL_X[0] - 0.05, LOW_FLOOR), (STUDY_LOW_X, LOW_FLOOR), (STUDY_LOW_X + STUDY_LOW_RAMP, FLOOR + 0.01),
           (WALL_X[0] - 0.05, FLOOR + 0.01)]
    return common(shape(a.prism_xz_r(mirror(pts, side), [0] * 4, *STUDY_LOW_Y)), [inside(LOW_FLOOR - 1.0, FLOOR + 1.0)])


def low_study():
    return single(unify(cut(R41.p22(), [low_study_cut(s) for s in (-1, 1)])), "revision-43 flat-pocket study")


def bell_study(low=False):
    body = with_bell(R41.p22(), taper=False)
    if low:
        body = cut(body, [low_study_cut(s) for s in (-1, 1)])
    return single(unify(body), "revision-43 bell-mouth study")


def low_bell_study():
    """The lower floor with the bell-mouth as simulated (r43lowbell_*): revision 43 without the taper."""
    body = with_bell(R41.p22(), taper=False)
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 lower-floor bell-mouth study")

# --------------------------------------------------------------------------------------------
# Study, not adopted: the jets run back to Y13.05 (cfd_cpap_r43.py, cases r43long_*). P22's heel drops straight
# down 0.3 mm in front of P23's front face, so the channel floor stays at Z-76.65 back to Y13.05; the wall over
# the jets is a plain 1.4 mm slab for 2.2 mm over ROOF, rounded r 1.4 as revision 41's. The extra air blows into
# the gap behind the hotend and up; the new heel would print as a flat overhang at 57 mm.
# --------------------------------------------------------------------------------------------
LONG_P23_FRONT = 11.55                     # both P23s' front face (Z-74.6..-70.8, |X| 11.5-20.4)
LONG_HEEL_GAP = 0.30
LONG_HEEL_OUT = LONG_P23_FRONT + LONG_HEEL_GAP       # the heel's outer face
LONG_WALL = 1.2                            # P22's floor and heel wall
LONG_HEEL_IN = LONG_HEEL_OUT + LONG_WALL             # the heel's inner face: the jets start here
LONG_WINDOW_FRONT = 28.2                   # the front wall's inner face (revision 41's jets run to it too)
LONG_TRIM_H = 2.2                          # the wall's bottom this far above ROOF is a plain 1.4 mm slab
LONG_SLAB_Y = 17.6                         # in front of this the wall is already that slab (revision 41's round runs here)
LONG_JET_LIP_Y = (LONG_HEEL_IN, R41.JET_LIP_Y[1])

# The duct's YZ profiles with the new heel (build_p22_lower_plenum's horn_yz_in and horn_yz_out up to the front wall,
# then straight down at LONG_HEEL_IN / LONG_HEEL_OUT in place of the 45 degree heel arcs).
LONG_HORN_IN = R41.HORN_IN[:11] + [(LONG_HEEL_IN, FLOOR), (LONG_HEEL_IN, -68.90)]
LONG_HORN_IN_R = R41.HORN_IN_R[:11] + [0.5, 0.5]
LONG_HORN_OUT = R41.HORN_OUT[:11] + [(LONG_HEEL_OUT, UNDER), (LONG_HEEL_OUT, -70.80)]
LONG_HORN_OUT_R = R41.HORN_OUT_R[:11] + [0.5, 0.0]
# build_p22_lower_plenum's outer plan (xy_outer_full): 1.4 mm side walls, the hotend slot notched out in front of Y11.2
LONG_XY_OUTER = [(-13.00, -45.40), (-20.60, -38.20), (-20.60, -25.30), (-22.42, -19.50), (-22.42, 15.00), (-20.40, 22.50),
            (-14.80, 28.40), (-8.50, 29.60), (-8.50, 11.20), (8.50, 11.20), (8.50, 29.60), (14.80, 28.40),
            (20.40, 22.50), (22.42, 15.00), (22.42, -19.50), (20.60, -25.30), (20.60, -38.20), (13.00, -45.40)]
LONG_XY_OUTER_R = [3.5, 3.5, 16.0, 16.0, 12.0, 10.0, 4.0, 0.8, 0.0, 0.0, 0.8, 4.0, 10.0, 12.0, 16.0, 16.0, 3.5, 3.5]


def long_horn_in(x0, x1):
    return a.prism_yz_r(LONG_HORN_IN, LONG_HORN_IN_R, x0, x1)


def long_inside(z0, z1):
    """Inside the duct's outer wall in plan (build_p22_lower_plenum's xy_inner_full)."""
    return a.prism_xy_r(R41.XY_INNER, R41.XY_INNER_R, z0, z1)


def long_heel_fill():
    """The new heel and the floor in front of it: everything under revision 41's 45 degree heel, inside P22's outer
    plan and in front of LONG_HEEL_OUT. On the slot side only below ROOF; above it the slot's rounded back corner stays."""
    region = common(a.box(-23.0, 23.0, LONG_HEEL_OUT, 22.6, UNDER, -70.0),
                    [a.prism_yz_r(LONG_HORN_OUT, LONG_HORN_OUT_R, -23.0, 23.0), a.prism_xy_r(LONG_XY_OUTER, LONG_XY_OUTER_R, -79.0, -69.0)])
    return cut(region, [a.box(-WALL_X[0], WALL_X[0], 0.0, 40.0, -90.0, -50.0),
                        a.box(-WALL_X[1], WALL_X[1], 0.0, 40.0, ROOF, -50.0)])


def long_corner_fill(side):
    """The slot's rounded back corner (released: a 4.65 mm round behind Y16.5) squared off for LONG_TRIM_H over the jet,
    so the wall above the jet is the same 1.4 mm slab from LONG_HEEL_IN forward."""
    lo, hi = sorted((side * WALL_X[0], side * WALL_X[1]))
    return a.box(lo, hi, LONG_HEEL_IN, LONG_SLAB_Y, ROOF, ROOF + LONG_TRIM_H)


def long_channel_air():
    """The side channels' air under revision 41's heel, down to the floor and back to LONG_HEEL_IN."""
    return common(a.box(-22.0, 22.0, LONG_HEEL_IN - 0.01, 23.0, FLOOR - 0.01, -66.0),
                  [long_horn_in(-22.0, 22.0), R41.p22_air_xy(-78.0, -60.0)])


def long_window_cut(side):
    """Each jet: the wall below ROOF, from the slot face to the channel, LONG_HEEL_IN to LONG_WINDOW_FRONT."""
    lo, hi = sorted((side * (WALL_X[0] - 0.05), side * 12.9))
    return common(a.box(lo, hi, LONG_HEEL_IN, LONG_WINDOW_FRONT, FLOOR - 0.01, ROOF),
                  [long_horn_in(lo - 1.0, hi + 1.0), long_inside(FLOOR - 1.0, ROOF + 1.0)])


def long_wall_trim(side):
    """Behind LONG_SLAB_Y the wall's duct face runs out to |X| 12.85; its bottom LONG_TRIM_H is cut back to |X| 11.6."""
    lo, hi = sorted((side * WALL_X[1], side * 13.0))
    return common(a.box(lo, hi, LONG_HEEL_IN, LONG_SLAB_Y, ROOF - 0.01, ROOF + LONG_TRIM_H),
                  [long_horn_in(lo - 1.0, hi + 1.0), long_inside(ROOF - 1.0, ROOF + LONG_TRIM_H + 1.0)])


def long_bell_mouth(side):
    """Revision 41's round (r 1.4, the wall's thickness) on the duct side of the wall's bottom edge, now LONG_HEEL_IN to
    Y26.2; the slot side keeps its square edge at ROOF."""
    x = side * WALL_X[1]
    r = R41.JET_LIP_R
    lo, hi = sorted((x - side * r, side * R41.JET_LIP_X_OUT))
    y0, y1 = LONG_JET_LIP_Y
    corner = shape(a.box(lo, hi, y0, y1, ROOF - 0.01, ROOF + r))
    corner = corner.cut(shape(a.cyl_y(x - side * r, ROOF + r, y0 - 0.1, y1 + 0.1, r)))
    return common(corner, [long_horn_in(lo - 1.0, hi + 1.0)])


def long_jets_study():
    """The study's P22: revision 41's with the heel dropped and the jets run back to LONG_HEEL_IN."""
    body = fuse(R41.p22(), long_heel_fill(), *[long_corner_fill(s) for s in (-1, 1)])
    body = cut(body, [long_channel_air()] + [c for s in (-1, 1) for c in (long_window_cut(s), long_wall_trim(s), long_bell_mouth(s))])
    return single(unify(body), "revision-43 long-jets study")
