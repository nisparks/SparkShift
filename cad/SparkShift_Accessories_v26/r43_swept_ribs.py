"""Separate curved-rib print study on cleaned C28; existing mounting datums are unchanged."""
import cadquery as cq

import r41_parts as R41
import r43_parts as R43
import r43_swept_feed as R
from build_bambu_clean_r29 import single

THICKNESS = .8
INLET_PATH = ((6.5, -46.0), (8.2, -41.0), (11.0, -35.0), (12.8, -29.0),
              (15.5, -23.0), (16.8, -18.0), (16.9, -12.0))
SLEEVE_CLEARANCE = .2


def rib_prism(edge):
    outline = cq.Wire.assembleEdges([edge]).offset2D(THICKNESS / 2, "arc")
    if len(outline) != 1 or not outline[0].IsClosed():
        raise ValueError("Rib offset did not form one closed outline")
    return cq.Solid.extrudeLinear(outline[0], [], cq.Vector(0, 0, 40)).translate((0, 0, -80))


def inlet_ribs():
    curve = cq.Edge.makeSpline([cq.Vector(x, y, 0) for x, y in INLET_PATH])
    envelope = R41.common(
        R41.a.prism_yz_r(R41.HORN_OUT, R41.HORN_OUT_R, -23, 23),
        [R41.a.prism_xy_r(R43.XY_OUTER, R43.XY_OUTER_SHARP_R, -90, -40)])
    right = rib_prism(curve).intersect(envelope)
    z0 = R41.P21_SLEEVE_BOT - SLEEVE_CLEARANCE
    sleeve_zone = R41.shape(R41.a.box(-24, 24, -48, -28, z0, R41.P21_BOT + .1))
    bore = R41.corridor((R41.BORE[0] + SLEEVE_CLEARANCE,
                        R41.BORE[1] - SLEEVE_CLEARANCE), z0 - .01, R41.P21_BOT + .2)
    right = right.cut(sleeve_zone.cut(bore))
    return [right, right.mirror("YZ")]


def rear_spine():
    radius = THICKNESS / 2
    prism = R41.fuse(
        cq.Solid.makeBox(THICKNESS, 11.8, 40, cq.Vector(-radius, 4.2, -80)),
        *[cq.Solid.makeCylinder(radius, 40, cq.Vector(0, y, -80)) for y in (4.2, 16)])
    return prism.intersect(R.nozzle(True, 3, .9, 28, conformal_outlet=True))


def p22(base, include_rear_spine=False):
    body = base.fuse(*inlet_ribs(), tol=.005)
    if include_rear_spine:
        body = body.fuse(rear_spine(), tol=.005)
    if not body.isValid():
        body = R41.unify(body)
    if not body.isValid() or len(body.Solids()) != 1 or len(body.Shells()) != 1:
        raise ValueError("Curved-rib study is not a valid single solid/shell")
    return single(body, "Cleaned C28 with flow-aligned printing ribs")
