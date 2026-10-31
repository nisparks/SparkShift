"""Variant of revision 43 (not a revision): P23 folded into P22, the probe screwed straight to P22, and the layer P23
filled used as a duct that feeds a rear jet down the centre, blowing at the nozzle from behind (270 degrees).
Revision 43's P22 (r43_parts.p22) is the base and is not changed; r43_rear_jet.py is the first rear-jet variant, fed
from the side channels through the heel's ramp (a manifold 2.6 x 2.5 mm inside, so its jet drew only 7 % of the air).

Here the air leaves each side channel through an opening in its floor (|X|13.4-18.4, in front of the probe screws'
bosses), runs inward through P23's old layer (Z-73.87..-70.8, on a 0.8 mm floor) and spreads over the probe's coil,
where the board itself is the floor (|X| <= 9.4; plastic only over the coil, as Beacon and Cartographer ask). It drops
past the probe's nose, between the nose and the Red Lizard's block (Y14.2): 1.2 mm deep on the centre line, opening up
to 4.7 mm at |X|9.4 as the nose's edges run back, and beside the Red Lizard's neck (|X| > 6.3) on forward to the
manifold's front. Under the neck a manifold (0.5 mm under the block, its air Y12.5-15.7, Z-77.05..-74.58) leads to the
rear jet (|X| <= 6, Z-77.05..-75.3, under the Bambu's sock as before). Below the probe a 0.8 mm wall stands in front of
its edge, so the probe still goes in from below.

The seat is the Beacon's (Z-74.67); the Cartographer's board top is 0.2 mm higher, so it needs a matching P22 seat;
a shim must not be assumed to preserve the probe/nozzle datum. A study (cfd_cpap_r43.py, case r43centre_bambu_bed,
and with jet=False the duct's body
alone, r43centrebody_bambu_bed; domains built with P23 and its rear screws left out), not adopted. The rear jet drew
17.7 L/min of 180 (10 %; the first variant 7 %): it blows into the space where the side jets meet. The body alone
doubled the air leaving up the hotend slot (28 %, against 16 %), by filling the space where the side jets' air ran
back along the print under the probe. With the jet open, 11 % less air reached the print within 5 mm than with
revision 43 (at each design's own blower flow).
These airflow results apply to this routing, not all rear jets, and are not a thermal cooling prediction.
"""
import cadquery as cq

import r37_parts as P37
import r41_parts as R41
import r43_parts as R43
import r43_rear_jet as RJ
from build_bambu_clean_r29 import single

a = R41.a
shape, fuse, cut, unify = R41.shape, R41.fuse, R41.cut, R41.unify

NAMES = {"p22": "P22_CPAP_Lower_Plenum_Centre_Feed_VARIANT"}

WALL = 0.8
SEAT, TOP = P37.Z_SEAT, P37.Z_TOP       # -74.67 (the Beacon's board top) and -70.8 (P23's top, P22's underside)
FLOOR = SEAT + WALL                    # the duct's floor where the board isn't under it
ARM_X = (13.4, 18.4)                   # the openings in each side channel's floor (its air spans |X|12.75-21.6 here)
FEED_Y = (3.8, 10.4)                   # in front of the probe screws' bosses (screws at Y-0.3), behind P23's front (Y11.55)
CENTRE_X = 11.0                        # the plenum over the coil, inside the hotend slot's walls
CENTRE_Y = (-4.4, 12.9)                # behind: the Cartographer's header (Y-6.04) clear by 0.84 mm through the wall;
                                       # in front: a 0.8 mm wall 0.5 mm behind the Red Lizard's block (Y14.2)
DROP_X = 9.4                           # the drop past the probe's nose, 0.8 mm inside the slot's wall line (|X|10.2)
MAN_Y = (12.5, 15.7)                   # the manifold's air under the Red Lizard's neck
MAN_TOP = -74.58                       # 0.8 mm roof, 0.5 mm under the Red Lizard's block (Z-73.28)
LEG_X = (7.1, DROP_X)                  # beside the neck (|X|5.75) the drop runs on forward to the manifold's front wall
JET = RJ.JET                           # (half-width 6.0, floor -77.05, top -75.3)
JET_Y = (MAN_Y[1] - 0.1, MAN_Y[1] + WALL + 0.1)


def probe_footprint(z0, z1, grow=0.0):
    """The probe board's plan outline (Beacon; the Cartographer's nose is within 0.02 mm of it), as a prism."""
    board = P37.beacon()[3]
    slab = board.intersect(shape(a.box(-30.0, 30.0, -30.0, 30.0, -75.6, -75.4)))
    face = [f for f in slab.Faces() if f.normalAt().z < -0.99][0]
    wire = face.outerWire()
    if grow:
        wire = wire.offset2D(grow, "arc")[0]
    wire = wire.translate(cq.Vector(0, 0, z0 - face.Center().z))
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, z1 - z0))


def seat():
    """P23's outline as part of P22, down to the probe's board: its front setback, connector opening and relief over
    the Beacon's top-side components stay; P22's insert holes open down through it to the probe's own screw holes."""
    xi, xo = P37.EAR_X
    outline = [(-19.2, 11.55), (19.2, 11.55), (19.2, 4.6), (xo, 3.4), (xo, P37.EAR_Y_REAR), (xi, P37.EAR_Y_REAR),
               (xi, -14.2), (-xi, -14.2), (-xi, P37.EAR_Y_REAR), (-xo, P37.EAR_Y_REAR), (-xo, 3.4), (-19.2, 4.6)]
    radii = [2.0, 2.0, 0.6, 0.6, 2.0, 2.0, 0.0, 0.0, 2.0, 2.0, 0.6, 0.6]
    body = a.prism_xy_r(outline, radii, SEAT, TOP)
    cutters = [a.rounded_box_xy(-11.65, 11.65, 8.30, 20.00, SEAT - 1.0, TOP + 1.0, 4.65),
               a.box(-11.50, 11.50, -16.00, -5.80, SEAT - 1.0, TOP + 1.0),
               a.box(-xo - 0.5, xo + 0.5, -16.00, -7.95, SEAT - 0.5, P37.RELIEF_TOP)]
    cutters += [a.cyl_z(x, y, SEAT - 1.0, TOP + 0.05, 2.27) for x, y in P37.P22_MOUNTS]   # into P22's insert holes
    return cut(body, cutters)


def walls():
    """New material in the hotend slot: round the plenum's front and over it (the slot is open above), and the drop's
    and manifold's walls in front of the probe's edge."""
    env = shape(a.box(-CENTRE_X - WALL, CENTRE_X + WALL, CENTRE_Y[0] - WALL, CENTRE_Y[1] + WALL, SEAT, TOP + WALL))
    xw = DROP_X + WALL
    man = fuse(shape(a.box(-xw, xw, CENTRE_Y[0], MAN_Y[1] + WALL, R43.UNDER, MAN_TOP + WALL)),
               shape(a.box(-xw, xw, CENTRE_Y[0], CENTRE_Y[1] + WALL, R43.UNDER, TOP)),
               *[shape(a.box(*sorted((s * (LEG_X[0] - WALL), s * xw)), CENTRE_Y[0], MAN_Y[1] + WALL, R43.UNDER,
                             TOP + WALL)) for s in (-1, 1)])
    return env, cut(man, [probe_footprint(-90.0, -60.0)])


def air(jet=True):
    y0, y1 = FEED_Y
    parts = [shape(a.box(*sorted((s * ARM_X[0], s * ARM_X[1])), y0, y1, FLOOR, -68.4)) for s in (-1, 1)]
    parts.append(shape(a.box(-ARM_X[1], ARM_X[1], y0, y1, FLOOR, TOP)))
    parts.append(shape(a.box(-CENTRE_X, CENTRE_X, CENTRE_Y[0], CENTRE_Y[1], FLOOR, TOP)))
    drop = shape(a.box(-DROP_X, DROP_X, CENTRE_Y[0], CENTRE_Y[1], R43.LOW_FLOOR, TOP))
    parts.append(cut(drop, [probe_footprint(-80.0, SEAT), probe_footprint(-80.0, P37.PCB_BOTTOM, grow=WALL)]))
    parts.append(shape(a.box(-DROP_X, DROP_X, MAN_Y[0], MAN_Y[1], R43.LOW_FLOOR, MAN_TOP)))
    parts += [shape(a.box(*sorted((s * LEG_X[0], s * LEG_X[1])), MAN_Y[0], MAN_Y[1], R43.LOW_FLOOR, TOP))
              for s in (-1, 1)]
    hx, z0, z1 = JET
    if jet:
        parts.append(shape(a.box(-hx, hx, JET_Y[0], JET_Y[1], z0, z1)))
    return fuse(*parts)


def p22(base=None, jet=True):
    """Revision 43's P22 with P23 folded in and the centre feed. `base` saves rebuilding revision 43's P22.
    jet=False closes the rear jet (the CFD's check on what the duct's body alone does: r43centrebody_bambu_bed)."""
    body = base if base is not None else R43.p22()
    env, man = walls()
    body = fuse(body, seat(), env, man)
    body = cut(body, [air(jet)])
    ok = lambda s: len(s.Solids()) == 1 and s.Solids()[0].isValid()  # noqa: E731
    for candidate in (unify(body), body, RJ.fixed(body)):
        if ok(candidate):
            return single(candidate, "revision-43 P22, centre-feed variant")
    raise ValueError("revision-43 P22, centre-feed variant: no valid solid")
