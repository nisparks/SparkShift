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
  - the bell-mouth round on the wall's duct-side bottom edge grows from r 1.4 to r 2.4, from the heel (Y16.7) to Y24.6,
    on a foot 1 mm proud of the wall's duct face with a 45 degree chamfer back up to it; over the last 3 mm the round
    and its foot ease out together into the wall's corner as the duct's front roof comes down to meet them. Behind
    the heel the round runs into the heel's ramp and the foot runs on, rounded, until the ramp and the wall's
    thickening duct face take it in, so it ends nowhere square and prints without support with P22 on its back face.
The lower floor lets the blower move more air, but on its own the jets leave steeper and more of the air splashes up
behind the hotend; the larger round turns the air into the jets more gently, and they leave as flat as revision 41's.
The jets' top, the hotend slot (|X| 10.2), the duct upstream and every interface stay as they were, apart from the
printing changes and the review's rib in the plenum (below, printable()). The CFD (cfd_cpap_r43.py,
verification_cfd_cpap_r43.json) has the numbers; the studies below are the variants it compared.
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
    """The round as first adopted and as the studies simulated it: Y17.6 (or BELL_HEEL with the taper) to Y26.2."""
    body = fuse(body, *[bell_fill(s, taper) for s in (-1, 1)])
    return cut(body, [bell_cut(s, taper) for s in (-1, 1)])


# The round over the jet's full length. From the review in Fusion: the round stopped at Y26.2, short of the front
# wall (Y27.4-27.9 here, slanting back outboard), and behind Y17.6 the tapered foot left a V-shaped notch against the
# wall's duct face, which thickens outboard behind Y17.5. Now the round and its foot run from the heel to the front
# wall (with_runout_bell, below, eases them out over the last 3 mm), and behind the heel the foot carries on, in the
# duct's air only, until the heel's ramp and the thickening wall take it in: nothing ends square, and no part of the
# foot faces down with P22 on its back face.
BELL_BACK = 13.0      # where the foot's extension behind the heel starts; the duct's air ends it before here
BELL_FRONT = 29.5     # past the front wall; the duct's plan outline ends the round on the wall
HEEL_CUT_Y = 15.5     # the round's cut starts here, behind the heel: the heel's ramp (horn_in) ends it, so it leaves no
                      # end face (started at the heel, it left a 0.5 mm2 step where the island's corner stood behind).
                      # The CFD: that opens the jets' back corner, and 4 % less air reaches the print within 5 mm of
                      # the nozzle (r43np46_bambu_bed against r43revrunout_bambu_bed, both on 46 cores; README)


def bell_foot(side, y0, y1):
    """The foot under the wall (bell_fill's profile): from the slot face out to |X| WALL_X[0] + BELL_R, BELL_R up from
    ROOF, then a 45 degree chamfer back to the wall's duct face."""
    x0, x1 = WALL_X[0], WALL_X[0] + BELL_R
    top = ROOF + BELL_R + (x1 - WALL_X[1])
    pts = [(x0, ROOF), (x1, ROOF), (x1, ROOF + BELL_R), (WALL_X[1], top), (x0, top)]
    return shape(a.prism_xz_r(mirror(pts, side), [0] * 5, y0, y1))


def bell_outside(side, y0, y1):
    """Outside the round (bell_cut's): the corner under ROOF + BELL_R, out to |X| 12.9, less the r BELL_R cylinder."""
    x = side * WALL_X[0]
    lo, hi = sorted((x, side * (WALL_X[0] + BELL_R + 0.3)))
    corner = shape(a.box(lo, hi, y0, y1, ROOF - 0.01, ROOF + BELL_R))
    return corner.cut(shape(a.cyl_y(x, ROOF + BELL_R, y0 - 0.1, y1 + 0.1, BELL_R)))


def full_bell(side, front=BELL_FRONT, heel_cut=HEEL_CUT_Y):
    """(fill, cut, extension) for one jet. From the heel forward the foot and the round are bounded by the duct's side
    profile and plan outline, so they end on the front wall. Behind the heel the rounded foot is added only where the
    duct's air is (p22_air_xy leaves out the centre island, so the hotend slot, which widens behind Y16.5, is never
    touched), and the round's cut runs on from `heel_cut` until the heel's ramp ends it (the studies started it at
    BELL_HEEL). `front` < the front wall ends them square there instead (the review's front-end study)."""
    lo, hi = sorted((side * (WALL_X[0] - 1.0), side * (WALL_X[0] + BELL_R + 1.5)))
    horn = R41.horn_in(lo, hi)
    z0, z1 = ROOF - 1.0, ROOF + BELL_R + 2.0
    duct, air = inside(z0, z1), R41.p22_air_xy(z0, z1)
    fill = common(bell_foot(side, BELL_HEEL, front), [horn, duct])
    rnd = common(bell_outside(side, heel_cut, front), [horn, duct])
    ext = common(cut(bell_foot(side, BELL_BACK, BELL_HEEL), [bell_outside(side, BELL_BACK, BELL_HEEL)]), [horn, air])
    return fill, rnd, ext


def with_full_bell(body, front=BELL_FRONT, heel_cut=HEEL_CUT_Y):
    rows = [full_bell(s, front, heel_cut) for s in (-1, 1)]
    body = cut(fuse(body, *[r[0] for r in rows]), [r[1] for r in rows])
    return fuse(body, *[r[2] for r in rows])


# The round running out with the duct's front roof (adopted; the study r43revrunout_*). The CFD's finding: at full
# size over the jet's last 1.7 mm, where revision 41's sloping front roof leads the air in, the round let more air
# through but sent less of it over the print at the nozzle. So the round is full from the heel to RUNOUT_Y[0]; then,
# along a cosine, the round and its foot shrink together to a sharp corner by RUNOUT_Y[1], just short of the front
# wall, while the roof (HORN_IN) comes down over the same 3 mm. No step anywhere, and the surface only rises.
RUNOUT_Y, RUNOUT_H, RUNOUT_N = (24.6, 27.3), 3.6, 14


def runout_section(y, s):
    """The wall's bottom in the plane Y=y (right side), with s from 1 (the full round and foot) to 0 (a sharp corner):
    a round of r BELL_R*s tangent to the jet's roof at |X| WALL_X[0] + (1-s)*wall, its foot s mm proud of the wall's
    duct face with the 45 degree chamfer above. As s falls the round's tangent point slides from the slot face to
    the duct-side corner, so the surface only moves one way."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
    from OCP.gp import gp_Pnt
    x0, x1, z0, top = WALL_X[0], WALL_X[1], ROOF, ROOF + RUNOUT_H
    P = lambda x, z: gp_Pnt(x, y, z)  # noqa: E731
    seg = lambda a, b: BRepBuilderAPI_MakeEdge(GC_MakeSegment(a, b).Value()).Edge()  # noqa: E731
    s = min(max(s, 0.02), 0.995)
    r, xt = BELL_R * s, x0 + (1.0 - s) * (x1 - x0)
    mid = P(xt + r * math.sqrt(0.5), z0 + r - r * math.sqrt(0.5))
    arc = BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(P(xt, z0), mid, P(xt + r, z0 + r)).Value()).Edge()
    w = BRepBuilderAPI_MakeWire()
    for e in (seg(P(x0, top), P(x0, z0)), seg(P(x0, z0), P(xt, z0)), arc, seg(P(xt + r, z0 + r), P(x1, z0 + r + s)),
              seg(P(x1, z0 + r + s), P(x1, top)), seg(P(x1, top), P(x0, top))):
        w.Add(e)
    return w.Wire()


def runout_s(y):
    """The run-out's scale at Y: 1 (the full round and foot) at RUNOUT_Y[0] down to 0 (a sharp corner) at [1]."""
    t = min(max((y - RUNOUT_Y[0]) / (RUNOUT_Y[1] - RUNOUT_Y[0]), 0.0), 1.0)
    return 0.5 * (1.0 + math.cos(math.pi * t))


def runout_material(side):
    """The wall's bottom over the run-out, lofted through runout_section, and its last section on to the front wall."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec
    y0, y1 = RUNOUT_Y
    loft = BRepOffsetAPI_ThruSections(True, False)
    for k in range(RUNOUT_N + 1):
        y = y0 + (y1 - y0) * k / RUNOUT_N
        loft.AddWire(runout_section(y, runout_s(y)))
    loft.Build()
    face = BRepBuilderAPI_MakeFace(runout_section(y1, 0.0), True).Face()
    tail = shape(BRepPrimAPI_MakePrism(face, gp_Vec(0, BELL_FRONT - y1, 0)).Shape())
    solid = fuse(shape(loft.Shape()), tail)
    return solid if side > 0 else solid.mirror("YZ")


def with_runout_bell(body, heel_cut=HEEL_CUT_Y):
    """The full round and foot (full_bell) up to RUNOUT_Y[0]; from there to the front wall the wall's bottom is
    replaced by runout_material, inside the duct's side profile and plan outline."""
    body = with_full_bell(body, front=RUNOUT_Y[0], heel_cut=heel_cut)
    for side in (-1, 1):
        lo, hi = sorted((side * WALL_X[0], side * (WALL_X[0] + BELL_R + 0.3)))
        horn, duct = R41.horn_in(lo - 1.0, hi + 1.0), inside(ROOF - 1.0, ROOF + RUNOUT_H + 1.0)
        zone = common(shape(a.box(lo, hi, RUNOUT_Y[0], BELL_FRONT, ROOF - 0.01, ROOF + RUNOUT_H)), [horn, duct])
        body = fuse(cut(body, [zone]), common(runout_material(side), [horn, duct]))
    return body


# Study, not adopted (r43revfocus_*): the round only where the jets face the nozzle. The CFD after the review: the more
# of the jets' air leaves through their back 2 mm, behind the nozzle, the less reaches the print near it (the first
# version, its foot tapered at the heel: 3.5 % of it, +9 % within 5 mm; the round cut from the heel: 4.5 %, +4 %; run
# into the heel's ramp: 5.7 %, 0 %). Here the round and its foot grow from nothing at FOCUS_Y[0], where the island's
# duct face has turned straight (Y18.11), so they can't leave a valley against it, to full at FOCUS_Y[1], along the
# front run-out's cosine; behind FOCUS_Y[0] the wall's bottom edge is sharp, to throttle the jet's back end. It did:
# 1.7 % of the air left there, but the duct became 34 % more restrictive and the faster jets splashed up past the
# hotend (28 % of their air), so 15 % less air reached the print within 10 and 14 mm of the nozzle (2 % more within 5).
FOCUS_Y = (18.2, 18.2 + RUNOUT_Y[1] - RUNOUT_Y[0])


def focus_s(y):
    """The ease-in's scale at Y: 0 (a sharp edge) at FOCUS_Y[0] up to 1 (the full round and foot) at FOCUS_Y[1]."""
    t = min(max((y - FOCUS_Y[0]) / (FOCUS_Y[1] - FOCUS_Y[0]), 0.0), 1.0)
    return 0.5 * (1.0 - math.cos(math.pi * t))


def focus_corner_fill(side):
    """From the heel to FOCUS_Y[0]: revision 41's r1.4 round (r41_parts.jet_lip_cut) filled back to a sharp edge, out to
    the island's duct face, which still slants out there (its thickening, which that cut squared off, comes back too)."""
    lo, hi = sorted((side * WALL_X[0], side * (R41.JET_LIP_X_OUT + 0.1)))
    zone = shape(a.box(lo, hi, R41.HEEL_Y - 0.01, FOCUS_Y[0] + 0.01, ROOF, ROOF + R41.JET_LIP_R + 0.01))
    return common(zone, [a.prism_xy_r(R41.XY_ISLAND, R41.XY_ISLAND_R, ROOF - 1.0, ROOF + 2.0),
                         R41.horn_in(lo - 1.0, hi + 1.0)])


def focus_material(side):
    """The wall's bottom from FOCUS_Y[0] to FOCUS_Y[1], lofted through runout_section as the round and its foot grow."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    y0, y1 = FOCUS_Y
    loft = BRepOffsetAPI_ThruSections(True, False)
    for k in range(RUNOUT_N + 1):
        y = y0 + (y1 - y0) * k / RUNOUT_N
        loft.AddWire(runout_section(y, focus_s(y)))
    loft.Build()
    solid = shape(loft.Shape())
    return solid if side > 0 else solid.mirror("YZ")


def with_focused_bell(body):
    """A sharp edge from the heel to FOCUS_Y[0], the round and foot growing to full by FOCUS_Y[1], full to RUNOUT_Y[0],
    and easing out into the front wall as in with_runout_bell. Nothing is added behind the heel."""
    body = fuse(body, *[focus_corner_fill(s) for s in (-1, 1)])
    rows = []
    for side in (-1, 1):
        lo, hi = sorted((side * (WALL_X[0] - 1.0), side * (WALL_X[0] + BELL_R + 1.5)))
        horn, duct = R41.horn_in(lo, hi), inside(ROOF - 1.0, ROOF + BELL_R + 2.0)
        rows.append((common(bell_foot(side, FOCUS_Y[1], RUNOUT_Y[0]), [horn, duct]),
                     common(bell_outside(side, FOCUS_Y[1], RUNOUT_Y[0]), [horn, duct])))
    body = cut(fuse(body, *[r[0] for r in rows]), [r[1] for r in rows])
    for side in (-1, 1):
        lo, hi = sorted((side * WALL_X[0], side * (WALL_X[0] + BELL_R + 0.3)))
        horn, duct = R41.horn_in(lo - 1.0, hi + 1.0), inside(ROOF - 1.0, ROOF + RUNOUT_H + 1.0)
        for (y0, y1), material in ((FOCUS_Y, focus_material(side)), ((RUNOUT_Y[0], BELL_FRONT), runout_material(side))):
            zone = common(shape(a.box(lo, hi, y0, y1, ROOF - 0.01, ROOF + RUNOUT_H)), [horn, duct])
            body = fuse(cut(body, [zone]), common(material, [horn, duct]))
    return body


# Study, not adopted (r43revfade_*): the round over the whole length, its foot fading in and out, in case the full
# foot fed the jet's two ends at the nozzle's expense. The foot grows from nothing at FOOT_FADE_BACK[0] (where the
# wall's duct face turns straight, so no notch can form) to full at [1], and back to nothing over FOOT_FADE_FRONT, along
# cosine curves (their steepest point leans 41 degrees, so they print without support). It did worse at the nozzle.
FOOT_FADE_BACK, FOOT_FADE_FRONT = (18.2, 20.0), (24.8, 26.6)


def foot_clip(side, n=12):
    """In plan: up to the foot's outer face as it fades, |X| WALL_X[1] to WALL_X[0] + BELL_R and back."""
    x_in, x_out = WALL_X[1], WALL_X[0] + BELL_R

    def ramp(y0, y1, xa, xb):
        return [(xa + (xb - xa) * 0.5 * (1 - math.cos(math.pi * k / n)), y0 + (y1 - y0) * k / n) for k in range(n + 1)]
    back, front = ramp(*FOOT_FADE_BACK, x_in, x_out), ramp(*FOOT_FADE_FRONT, x_out, x_in)
    wp = (cq.Workplane("XY").workplane(offset=ROOF - 1.0).moveTo(8.0, 12.0).lineTo(x_in, 12.0).lineTo(*back[0])
          .spline(back[1:], tangents=[(0, 1), (0, 1)], includeCurrent=True).lineTo(*front[0])
          .spline(front[1:], tangents=[(0, 1), (0, 1)], includeCurrent=True).lineTo(x_in, 30.0).lineTo(8.0, 30.0).close())
    solid = wp.extrude(BELL_R + 6.0).val()
    return solid if side > 0 else solid.mirror("YZ")


def heel_fill(side):
    """Revision 41's round squared the wall's thickening off flat at |X| 11.6, below ROOF + 1.4, from the heel forward
    (r41_parts.jet_lip_cut); with no foot over it now, that left a 0.15 mm jog at the heel. Put the thickening back,
    so the island's duct face runs on past the heel and the round alone shapes it."""
    lo, hi = sorted((side * (WALL_X[1] - 0.05), side * (R41.JET_LIP_X_OUT + 0.05)))
    zone = shape(a.box(lo, hi, BELL_HEEL - 0.01, FOOT_FADE_BACK[0] + 0.1, ROOF - 0.01, ROOF + R41.JET_LIP_R + 0.01))
    return common(zone, [a.prism_xy_r(R41.XY_ISLAND, R41.XY_ISLAND_R, ROOF - 1.0, ROOF + 2.0)])


def with_faded_bell(body, heel=True):
    """The round (r BELL_R on the slot face) from the heel to the front wall; its foot only inside foot_clip. With
    `heel` the round runs back into the heel's ramp and the wall's thickening is put back in front of the heel
    (heel=False is the study as simulated, r43revfade_*; the difference is under 0.5 mm3 at each heel)."""
    fills, rounds = [], []
    for side in (-1, 1):
        lo, hi = sorted((side * (WALL_X[0] - 1.0), side * (WALL_X[0] + BELL_R + 1.5)))
        horn, duct = R41.horn_in(lo, hi), inside(ROOF - 1.0, ROOF + BELL_R + 2.0)
        fills.append(common(bell_foot(side, BELL_HEEL, BELL_FRONT), [horn, duct, foot_clip(side)]))
        if heel:
            fills.append(heel_fill(side))
        rounds.append(common(bell_outside(side, HEEL_CUT_Y if heel else BELL_HEEL, BELL_FRONT), [horn, duct]))
    return cut(fuse(body, *fills), rounds)


# --------------------------------------------------------------------------------------------
# Printing. P22 prints on its back face (the duct then runs up the build, and the jets' layer lines run along the
# flow); no other side has less overhang, and every orientation that needs no support rests on an edge. On its back
# face revision 41 needed support in three places, and revision 43 removes two of them:
#   - the window between the side channels (the probe's connector and cable come up through it) ends in front at a
#     flat face, Y-5.4, which printed as a 22.9 mm ceiling. Revision 43 cuts a 45 degree notch into the solid block
#     in front of it, to an apex at Y6.05, 2.25 mm behind the hotend slot, right through to the underside, with its
#     three vertical edges rounded r 5 (the apex, and where it leaves the window's sides). A first version left the
#     block's bottom 1.8 mm for P23 to bear on, which printed as a 22.9 mm bridge one strip wide; Bambu Studio sliced
#     it as walls and gap fill across thin air. P23 still bears on 85 % of its old area, and its four screws clamp it
#     at the bosses, at least 9 mm from the notch;
#   - the round on the bottom-back edge (r16) faced the plate where it met the back face: its first half becomes a
#     45 degree chamfer, tangent to the rest of the round, which also lengthens the flat back face on the plate from
#     5.8 to 12.4 mm. Nothing else is within 1.44 mm of the corner. The back face's two corners in plan (r3.5, which
#     faced the plate for their first half millimetre) become sharp.
# From the review in Fusion, inside the duct: a rib in the plane of symmetry from the plenum's back wall to the cable
# boss's nose, which otherwise printed as a 7 mm arch, flaring into the nose at 45 degrees so the nose's r3 rounds
# don't overhang; and the centre island's square back corners, which stood 0.32 mm proud of the nose's rounds, are
# cut back so each round runs on to its tangent with the island's side.
# The cheeks' bearing faces (on P01's bosses, with P01 behind them) still need support: in print they are ceilings
# 8.5 mm wide, cantilevered 10 mm from the duct. Everything else bridges at most 15.4 mm.
# --------------------------------------------------------------------------------------------
WINDOW_FRONT, WINDOW_HALF = -5.40, 11.45  # the window's front face and half-width (build_p22_lower_plenum's valleys)
NOTCH_R = 5.0                             # the notch's three vertical edges (the review's fillet)
NOTCH_STRIP = 3.0                         # the notch's plan reaches this far back into the window's own air, so the
                                          # rounds where it leaves the window's sides (2.07 mm along them) fit
ISLAND_TOP = -57.36                       # the block's top around the window (HORN_OUT's flat), where those edges end
BACK_Y, BOTTOM_Z, BACK_R = -45.40, -70.80, 16.0   # the back face, the underside behind the heel, the round between
XY_OUTER = [(-13.00, -45.40), (-20.60, -38.20), (-20.60, -25.30), (-22.42, -19.50), (-22.42, 15.00), (-20.40, 22.50),
            (-14.80, 28.40), (-8.50, 29.60), (-8.50, 11.20), (8.50, 11.20), (8.50, 29.60), (14.80, 28.40),
            (20.40, 22.50), (22.42, 15.00), (22.42, -19.50), (20.60, -25.30), (20.60, -38.20), (13.00, -45.40)]
XY_OUTER_R = [3.5, 3.5, 16.0, 16.0, 12.0, 10.0, 4.0, 0.8, 0.0, 0.0, 0.8, 4.0, 10.0, 12.0, 16.0, 16.0, 3.5, 3.5]
XY_OUTER_SHARP_R = [0.0] + XY_OUTER_R[1:-1] + [0.0]   # the back face's two corners in plan, sharp (were r3.5)


def notch_plan(radius):
    w, y0 = WINDOW_HALF, WINDOW_FRONT
    return [(-w, y0 - NOTCH_STRIP), (w, y0 - NOTCH_STRIP), (w, y0), (0.0, y0 + w), (-w, y0)], [0.0, 0.0] + [radius] * 3


def window_notch():
    """The 45 degree notch in plan at the window's front, through the block from the underside up, its vertical edges
    rounded r NOTCH_R. Behind Y-5.4 it only overlaps the window's own air."""
    pts, radii = notch_plan(NOTCH_R)
    return shape(a.prism_xy_r(pts, radii, BOTTOM_Z - 0.5, -50.0))


def window_corner_fills():
    """Where the notch leaves the window's sides, its rounds reach 2.07 mm back into the window's own air: fill them,
    from the underside to the block's top."""
    pts, radii = notch_plan(NOTCH_R)
    sharp = shape(a.prism_xy_r(pts, [0.0] * 5, BOTTOM_Z, ISLAND_TOP))
    rounded = shape(a.prism_xy_r(pts, radii, BOTTOM_Z - 1.0, ISLAND_TOP + 1.0))
    w, y0 = WINDOW_HALF, WINDOW_FRONT
    return common(cut(sharp, [rounded]), [a.box(-w - 1.0, w + 1.0, y0 - NOTCH_STRIP - 1.0, y0, BOTTOM_Z, ISLAND_TOP)])


# The cable boss's nose (r41_parts.XY_BOSS_NOSE: |X| 3.65 to Y-38.15, corners r 3) and the rib behind it, the width of
# the nose's flat tip, from the plenum's back wall (HORN_IN, Y-43.56) up to the socket's floor (Z-51.4). Each side of
# the rib flares into the nose along the 45 degree tangent to the nose's round, blended into the rib r RIB_BLEND_R.
NOSE_HALF, NOSE_TIP, NOSE_R = 3.65, -38.15, 3.0
NOSE_C = (NOSE_HALF - NOSE_R, NOSE_TIP + NOSE_R)          # the rounds' centres, |X| 0.65, Y-35.15
RIB_HALF = NOSE_C[0]
RIB_BACK, RIB_TOP = R41.HORN_IN[0][0], R41.HORN_IN[3][1]  # Y-43.56, Z-51.4
RIB_BLEND_R = 1.5
NOSE_45 = (NOSE_C[0] + NOSE_R * math.sqrt(0.5), NOSE_C[1] - NOSE_R * math.sqrt(0.5))   # where the round is at 45 degrees
ISLAND_BACK = R41.XY_ISLAND[0][1]                         # Y-36.5: the centre island's square back corners


def cable_rib():
    """The rib and its flares, in plan, bounded by P22's outer side profile (so where it runs into the back wall and
    the plenum's floor it only meets solid) and stopping at the socket's floor."""
    ys = NOSE_45[1] - (NOSE_45[0] - RIB_HALF)          # the flare meets the rib's side here (Y-39.39)
    pts = [(-RIB_HALF, RIB_BACK - 0.5), (RIB_HALF, RIB_BACK - 0.5), (RIB_HALF, ys), NOSE_45, (0.0, NOSE_TIP + 1.0),
           (-NOSE_45[0], NOSE_45[1]), (-RIB_HALF, ys)]       # (0, Y-37.15): inside the nose, behind the cable's bore
    radii = [0.0, 0.0, RIB_BLEND_R, 0.0, 0.0, 0.0, RIB_BLEND_R]
    rib = shape(a.prism_xy_r(pts, radii, BOTTOM_Z - 2.0, RIB_TOP))
    return common(rib, [a.prism_yz_r(R41.HORN_OUT, R41.HORN_OUT_R, -23.0, 23.0)])


def boss_shoulder_cut(side):
    """The island's back corner, outside the nose's round, from the plenum's floor up to the socket's floor."""
    cx, cy = side * NOSE_C[0], NOSE_C[1]
    lo, hi = sorted((side * 2.0, side * (NOSE_HALF + 0.4)))
    corner = cut(shape(a.box(lo, hi, ISLAND_BACK - 0.3, cy, BOTTOM_Z - 1.0, RIB_TOP)),
                 [shape(a.cyl_z(cx, cy, BOTTOM_Z - 2.0, RIB_TOP + 1.0, NOSE_R))])
    return common(corner, [R41.horn_in(lo - 1.0, hi + 1.0)])


def printable(body):
    body = cut(fuse(body, back_chamfer(), back_corners()), [window_notch()])
    body = fuse(body, window_corner_fills(), cable_rib())
    return cut(body, [boss_shoulder_cut(s) for s in (-1, 1)])


def p22():
    body = with_runout_bell(printable(R41.p22()))
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 P22")


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


def review_rib_study():
    """The review's rib, trimmed island corners and through notch, with the first version's round (to Y26.2, tapered
    foot): the rib's own effect (r43revrib_*)."""
    body = with_bell(printable(R41.p22()))
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 review rib study")


def review_back_study():
    """As revision 43 after the review, but the round and its foot end square at Y26.2 as the first version's did:
    the front end's own effect (r43revback_*)."""
    body = with_full_bell(printable(R41.p22()), front=R41.JET_LIP_Y[1], heel_cut=BELL_HEEL)
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 review back-end study")


def review_full_study():
    """The review's first pass (r43full_*): the round and its foot at full size to the front wall."""
    body = with_full_bell(printable(R41.p22()), heel_cut=BELL_HEEL)
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 review full-round study")


def review_fade_study():
    """The round over the whole length with its foot fading in and out (r43revfade_*), as simulated (heel=False)."""
    body = with_faded_bell(printable(R41.p22()), heel=False)
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 review faded-foot study")


def review_runout_study():
    """The run-out as simulated (r43revrunout_*): revision 43's P22 with the round's cut started at the heel."""
    body = with_runout_bell(printable(R41.p22()), heel_cut=BELL_HEEL)
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 review run-out study")


def review_focus_study():
    """The round only where the jets face the nozzle (r43revfocus_*)."""
    body = with_focused_bell(printable(R41.p22()))
    return single(unify(cut(body, [pocket(s) for s in (-1, 1)])), "revision-43 review focused-round study")

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
