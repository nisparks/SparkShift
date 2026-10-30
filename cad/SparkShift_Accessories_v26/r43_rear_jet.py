"""Variant of revision 43 (not a revision): P22 with a rear jet, blowing at the nozzle from behind (270 degrees) as
well as from both sides. Revision 43's P22 (r43_parts.p22) is the base and is not changed.

Behind the nozzle the probe (Beacon or Cartographer, Z-76.3..-74.67) reaches forward to Y11.7 on the centre line,
curving back to Y7.9 at |X| 10, with P23 over it back to Y8.3; the Bambu's sock starts at Y18.4 (bottom Z-75.48) and
the Red Lizard's block at Y14.2 (|X| <= 5, from Z-73.3 up). Between them, from P22's lowest level (Z-77.85) up to just
under the Red Lizard's block, a manifold runs across behind the hotend and out under the heel's ramp on both sides,
where openings through the ramp draw air from the bottom of each side channel. The rear jet leaves the manifold's
front face across the middle, at the side jets' height but stopping just under the Bambu's sock, so it passes under
the sock to the nozzle and the print. Beside the Red Lizard's block (|X| > 6.3) the manifold's legs stand taller.

A study (cfd_cpap_r43.py, cases r43rearjet_bambu_bed and, with wide=True, r43rearjetb_bambu_bed), not adopted: the
side jets' air leaves the nozzle along the print, mostly backward, and the manifold and its jet stand in that path, so
twice as much air turned up the hotend slot (32-33 %, against 16 %) and 9-12 % less reached the print within 5 mm of
the nozzle. The manifold's back face would also print as a ceiling.
"""
import r41_parts as R41
import r43_parts as R43
from build_bambu_clean_r29 import single

a = R41.a
shape, fuse, cut, common, unify = R41.shape, R41.fuse, R41.cut, R41.common, R41.unify

NAMES = {"p22": "P22_CPAP_Lower_Plenum_Rear_Jet_VARIANT"}

WALL = 0.8
MAN_Y = (12.3, 16.5)          # back face (0.6 mm in front of the probe at X0) and front face (1.9 mm behind the sock)
MAN_X = 15.5                  # out under the heel's ramp, short of the side channel's outer wall (|X| 21)
MAN_Z = (R43.UNDER, -73.8)    # P22's lowest level, and 0.5 mm under the Red Lizard's block
LEG_X = 6.3                   # outboard of this the Red Lizard's block (|X| 5.75 at its back) is clear by 0.5 mm: the legs
                              # rise to P22's underside
LEG_TOP = -70.8               # P22's underside behind the heel (and P23's top)
TAP_X = (12.9, 14.7)          # the openings through the ramp: |X|, inside the side channel (island face 12.85..12.2)
JET = (6.0, R43.LOW_FLOOR, -75.3)   # the rear jet: half-width, floor (the side jets' floor) and top (under the sock)
# wide=True: the manifold runs out under the ramp to |X| 19 and its openings into the side channels grow to |X| 18.2
# (the side channel's outer wall is at |X| 20.5-21 here), so they no longer limit the rear jet's flow (r43rearjetb_*)
WIDE_MAN_X, WIDE_TAP_X = 19.0, (12.9, 18.2)


def duct_air():
    """The duct's own air near the heel (horn_in in side view, the duct's plan), which the manifold must not fill."""
    return common(R41.horn_in(-23.0, 23.0), [R41.p22_air_xy(-80.0, -60.0)])


def manifold_outer(man_x=MAN_X):
    y0, y1 = MAN_Y
    z0, z1 = MAN_Z
    low = shape(a.box(-man_x, man_x, y0, y1, z0, z1))
    legs = [shape(a.box(*sorted((s * LEG_X, s * man_x)), y0, y1, z0, LEG_TOP)) for s in (-1, 1)]
    return cut(fuse(low, *legs), [duct_air()])


def manifold_air(man_x=MAN_X):
    """Inside the walls: across the back at the base's height, and up the legs to under P22's underside."""
    y0, y1 = MAN_Y[0] + WALL, MAN_Y[1] - WALL
    z0 = MAN_Z[0] + WALL
    base = shape(a.box(-(man_x - WALL), man_x - WALL, y0, y1, z0, MAN_Z[1] - WALL))
    legs = [shape(a.box(*sorted((s * (LEG_X + WALL), s * (man_x - WALL))), y0, y1, z0, LEG_TOP - WALL)) for s in (-1, 1)]
    return fuse(base, *legs)


def taps(tap_x=TAP_X):
    """Through the heel's ramp into the bottom of each side channel."""
    y0, y1 = MAN_Y[0] + WALL, MAN_Y[1] - WALL
    return [shape(a.box(*sorted((s * tap_x[0], s * tap_x[1])), y0, y1, MAN_Z[0] + WALL, -68.0)) for s in (-1, 1)]


def jet_opening():
    hx, z0, z1 = JET
    return shape(a.box(-hx, hx, MAN_Y[1] - WALL - 0.1, MAN_Y[1] + 0.1, z0, z1))


def fixed(s):
    """ShapeFix, for when OCC's booleans leave the solid flagged invalid."""
    from OCP.ShapeFix import ShapeFix_Shape
    fx = ShapeFix_Shape(s.wrapped)
    fx.Perform()
    return shape(fx.Shape())


def p22(base=None, wide=False):
    """Revision 43's P22 with the rear manifold and jet. `base` saves rebuilding revision 43's P22 (a BREP of it).
    The cuts go in three steps (all at once, OCC's boolean leaves the solid invalid), and merging coplanar faces is
    kept only if the solid stays valid."""
    man_x, tap_x = (WIDE_MAN_X, WIDE_TAP_X) if wide else (MAN_X, TAP_X)
    body = base if base is not None else R43.p22()
    air = cut(manifold_air(man_x), [body])      # the manifold's own air, leaving P22's walls alone
    body = fuse(body, manifold_outer(man_x))
    for cutters in ([air], [jet_opening()], taps(tap_x)):
        body = cut(body, cutters)
    ok = lambda s: len(s.Solids()) == 1 and s.Solids()[0].isValid()  # noqa: E731
    for candidate in (unify(body), body, fixed(body)):
        if ok(candidate):
            return single(candidate, "revision-43 P22, rear-jet variant")
    raise ValueError("revision-43 P22, rear-jet variant: no valid solid")
