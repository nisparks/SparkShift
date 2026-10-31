"""Use the user's sloping P21 support as the input for a separate matched-joint study."""
from pathlib import Path
import math

import cadquery as cq
import numpy as np
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset, BRepOffsetAPI_ThruSections
from OCP.GeomAbs import GeomAbs_Arc

import r43_c28_mechanical as M

SOCKET_CLEARANCE = .25
RECEIVER_WALL = 1.25
RELIEF_TOP = -58.5
RELIEF_BOTTOM = -65.0
RELIEF_BACK_Y = -34.0
RELIEF_HALF_X = 3.6
FRONT_OPEN_Y = -19.0
SCREW_BOSS_R = 4.8
# Original P21 sleeve: bottom plane and front wall faces; P22 leaves a 0.18 mm slot in front of it.
SEAL_Z = -51.4
SLEEVE_BACK_FACE_Y = -35.88
SLEEVE_FRONT_FACE_Y = -34.63
P22_BAND_Y = -34.45
SKIRT = SOCKET_CLEARANCE + RECEIVER_WALL
DAM_HALF_X = 6.25


def load_user_p21(path):
    """Remove only the two collapsed planar inner wires in the captured Fusion STEP.

    The native STL is closed. These two backtracking line loops have zero area
    and no manufactured surface; retaining them prevents OCC from importing the
    declared closed shell as a solid. All outer wires and real inner holes stay.
    """
    path = Path(path)
    raw = cq.importers.importStep(str(path)).val()
    if raw.isValid() and len(raw.Solids()) == len(raw.Shells()) == 1:
        return raw.Solids()[0], {"repaired_exchange_wires": [], "already_valid_solid": True}
    repaired, faces = [], []
    for face in raw.Faces():
        kept, dropped = [], []
        for wire in face.innerWires():
            edges, bb = wire.Edges(), wire.BoundingBox()
            candidate = (
                face.geomType() == "PLANE" and len(edges) == 2
                and all(e.geomType() == "LINE" for e in edges)
                and bb.xlen < 1e-7 and bb.ylen < 1e-7
                and abs(bb.zlen - 6.5) < 1e-7
                and abs(abs(wire.Center().x) - 4.0) < 1e-7
                and abs(wire.Center().y + 33.2) < 1e-7
                and abs(wire.Center().z + 45.25) < 1e-7
                and abs(edges[0].Length() - edges[1].Length()) < 1e-7
                and (edges[0].Center() - edges[1].Center()).Length < 1e-7
            )
            (dropped if candidate else kept).append(wire)
        if not dropped:
            faces.append(face)
            continue
        replacement = cq.Face.makeFromWires(face.outerWire(), kept)
        if replacement.normalAt().dot(face.normalAt()) < 0:
            replacement.wrapped.Reverse()
        if abs(replacement.Area() - face.Area()) > 1e-7:
            raise ValueError("Removing a collapsed wire changed a real surface area")
        repaired += [{"centre_mm": list(w.Center().toTuple()), "length_mm": w.Length(),
                      "face_area_before_mm2": face.Area(), "face_area_after_mm2": replacement.Area()}
                     for w in dropped]
        faces.append(replacement)
    if len(repaired) != 2:
        raise ValueError(f"Unexpected user STEP topology: found {len(repaired)} known collapsed wires")
    sewing = BRepBuilderAPI_Sewing(1e-7)
    for face in faces:
        sewing.Add(face.wrapped)
    sewing.Perform()
    shell = cq.Shape.cast(sewing.SewedShape())
    if sewing.NbFreeEdges() or sewing.NbMultipleEdges() or len(shell.Shells()) != 1:
        raise ValueError("The exchange-only wire cleanup did not produce one closed manifold shell")
    solid = cq.Solid.makeSolid(shell.Shells()[0]).fix()
    if not solid.isValid() or len(solid.Solids()) != 1 or len(solid.Shells()) != 1 or solid.Volume() <= 0:
        raise ValueError("The cleaned user STEP is not one positively oriented valid solid")
    return solid, {
        "repaired_exchange_wires": repaired, "sewing_tolerance_mm": 1e-7,
        "surfaces_preserved": "Two zero-area inner line loops removed; all real boundaries and surfaces retained.",
        "faces_before": len(raw.Faces()), "faces_after": len(solid.Faces()),
    }


def receiver_profile(offset, z0, z1):
    half = M.R.BOSS_HALF + offset
    front, back = -25 + offset, M.R.BOSS_Y - offset
    rear = M.R.shape(M.R.a.prism_xy_r(
        [(-half, front), (-half, back), (half, back), (half, front)],
        3 + offset, z0, z1))
    nose = M.cylinder(0, M.RETAINER_Y, z0, z1, M.TONGUE_R + offset)
    return M.checked(rear.fuse(nose), "Analytic vertical receiver profile")


def lower_relief_keep(offset=0):
    back_slope = (RELIEF_BACK_Y - M.R.BOSS_Y) / (RELIEF_TOP - RELIEF_BOTTOM)
    side_slope = (M.R.BOSS_HALF - RELIEF_HALF_X) / (RELIEF_TOP - RELIEF_BOTTOM)
    z0, z1 = -75.0, -45.0

    def back(z):
        return M.R.BOSS_Y + back_slope * (RELIEF_TOP - z) - offset * math.hypot(1, back_slope)

    def half(z):
        return M.R.BOSS_HALF + side_slope * (z - RELIEF_TOP) + offset * math.hypot(1, side_slope)

    rear = M.yz_prism([(back(z0), z0), (-15, z0), (-15, z1), (back(z1), z1)], -12, 12)
    wire = cq.Wire.makePolygon([
        cq.Vector(-half(z0), -55, z0), cq.Vector(half(z0), -55, z0),
        cq.Vector(half(z1), -55, z1), cq.Vector(-half(z1), -55, z1),
    ], close=True)
    sides = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 40, 0))
    return rear.intersect(sides)


def refine_lower_support(p21):
    low = M.box(-7, 7, -44, -20, -66, RELIEF_TOP)
    body = p21.cut(low.cut(lower_relief_keep()))
    return M.checked(body, "User sloped support with confined lower rear/side relief")


def receiver_base(angled_p22):
    """Angled-mount C28 P22 plus only the underside screw boss; none of the fork's slots or ribs."""
    boss = M.cylinder(0, M.RETAINER_Y, M.SEAT_Z, M.TONGUE_BOTTOM - SOCKET_CLEARANCE, SCREW_BOSS_R)
    return M.checked(angled_p22.fuse(boss, tol=.005), "C28 angled P22 with underside screw boss")


def front_opening(offset=SOCKET_CLEARANCE, front=FRONT_OPEN_Y):
    """The socket's relieved X-Z section, extruded forward into the open hotend/cable bay.

    With P22 printed back-down, +Y is up; a closed socket front is a flat ceiling that
    needs support. Opening it leaves vertical side walls and removes only dry material.
    """
    side_slope = (M.R.BOSS_HALF - RELIEF_HALF_X) / (RELIEF_TOP - RELIEF_BOTTOM)
    grow = offset * math.hypot(1, side_slope)
    top_half = M.R.BOSS_HALF + offset
    bottom = M.TONGUE_BOTTOM - offset
    bottom_half = M.R.BOSS_HALF + side_slope * (bottom - RELIEF_TOP) + grow
    knee = RELIEF_TOP + (top_half - M.R.BOSS_HALF - grow) / side_slope
    points = [(-top_half, -48), (top_half, -48), (top_half, knee),
              (bottom_half, bottom), (-bottom_half, bottom), (-top_half, knee)]
    wire = cq.Wire.makePolygon([cq.Vector(x, M.RETAINER_Y, z) for x, z in points], close=True)
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(0, front - M.RETAINER_Y, 0))


def profile_wire(offset, z):
    half = M.R.BOSS_HALF + offset
    front, back = -25 + offset, M.R.BOSS_Y - offset
    return M.R.a.rounded_polygon_wire_xy(
        [(-half, front), (-half, back), (half, back), (half, front)], 3 + offset, z)


def seal_skirt():
    """P21 addition: a 45 deg skirt that caps the socket gap where the post passes the inflow.

    The service drop forces the socket through the original P21-flange/P22-top seal. The
    skirt's underside lands on the receiver top in the existing sleeve-bottom plane, so the
    clearance gap around the rear of the post is closed without any sliding interference.
    It prints unsupported with P21 top-face down.
    """
    loft = BRepOffsetAPI_ThruSections(True, True)
    loft.AddWire(profile_wire(SKIRT, SEAL_Z))
    loft.AddWire(profile_wire(0, SEAL_Z + SKIRT))
    loft.Build()
    frustum = cq.Shape.cast(loft.Shape())
    post = M.R.shape(M.R.a.prism_xy_r(
        [(-M.R.BOSS_HALF + .05, -25), (-M.R.BOSS_HALF + .05, M.R.BOSS_Y + .05),
         (M.R.BOSS_HALF - .05, M.R.BOSS_Y + .05), (M.R.BOSS_HALF - .05, -25)],
        2.95, SEAL_Z - 1, SEAL_Z + SKIRT + 1))
    rear = M.box(-10, 10, -45, SLEEVE_BACK_FACE_Y + .6, SEAL_Z, SEAL_Z + SKIRT)
    return M.checked(frustum.cut(post).intersect(rear), "P21 rear seal skirt")


def sealed_p21(p21):
    return M.checked(p21.fuse(seal_skirt(), tol=1e-4), "User P21 with rear seal skirt")


def sleeve_dam():
    """P22 addition closing the original 0.18 mm sleeve slot beside the opened socket."""
    return M.box(-DAM_HALF_X, DAM_HALF_X, SLEEVE_FRONT_FACE_Y, P22_BAND_Y + .05, SEAL_Z, -49.0)


def rear_keel(offset=SKIRT):
    """45 deg keel under the receiver back, so the back-down P22 print needs no trapped support."""
    half, radius = M.R.BOSS_HALF + offset, 3 + offset
    x_t = half - radius * (1 - math.sqrt(.5))
    y_t = M.R.BOSS_Y - offset + radius * (1 - math.sqrt(.5))
    wire = cq.Wire.makePolygon([cq.Vector(x, y, -66.5) for x, y in (
        (x_t, y_t), (0, y_t - x_t), (-x_t, y_t), (-x_t, y_t + 3), (x_t, y_t + 3))], close=True)
    prism = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, SEAL_Z + 66.5))
    return M.checked(prism.intersect(lower_relief_keep(offset)), "Receiver rear keel")


def matched_receiver(p21, original_p21, previous_p22, cable, lower_relief=False, open_front=False,
                     sealed=False):
    extension = p21.cut(original_p21, tol=1e-5)
    extension = M.checked(extension, "User P21 extension beyond original mid duct")
    reference = receiver_profile(0, -66, -48)
    if lower_relief:
        reference = reference.intersect(lower_relief_keep())
    outside = extension.cut(reference)
    if not outside.isValid() or abs(outside.Volume()) > 1e-4:
        raise ValueError(f"The receiver profile does not enclose the user support: {outside.Volume()} mm3")
    socket = receiver_profile(SOCKET_CLEARANCE, -65.25, -48.9)
    # The sealed receiver rises to the sleeve-bottom plane, where the P21 skirt lands on it.
    envelope = receiver_profile(SOCKET_CLEARANCE + RECEIVER_WALL, -66.5, SEAL_Z if sealed else -51.65)
    if lower_relief:
        socket = socket.intersect(lower_relief_keep(SOCKET_CLEARANCE))
        envelope = envelope.intersect(lower_relief_keep(SOCKET_CLEARANCE + RECEIVER_WALL))
    construction = {"extension": extension, "socket": socket}
    if sealed:
        if not (lower_relief and open_front):
            raise ValueError("The sealed receiver is defined for the relieved, open-front variant")
        construction["keel"], construction["dam"] = rear_keel(), sleeve_dam()
        envelope = envelope.fuse(construction["keel"], construction["dam"], tol=.005)
    # Open at the top so P22 can drop off the fixed cable, rather than trapping it
    # in a closed port. This applies only to the new receiver material.
    cable_slot = M.box(-1.95, 1.95, -36.85, -20, -57.15, -48)
    reinforcement = envelope.cut(cable_slot)
    if not reinforcement.isValid() or reinforcement.distance(cable) < .45 - 1e-6:
        raise ValueError("New receiver material violates the cable clearance")
    construction["reinforcement"] = reinforcement
    body = previous_p22.fuse(reinforcement, tol=.005)
    cutters = [
        socket,
        M.cylinder(0, M.RETAINER_Y, M.TONGUE_BOTTOM - M.SOCKET_CLEARANCE, -48,
                   M.TONGUE_R + M.SOCKET_CLEARANCE),
        M.cylinder(0, M.RETAINER_Y, M.SEAT_Z - .1, -64, M.HOLE_R),
    ]
    if open_front:
        if not lower_relief:
            raise ValueError("The front opening follows the relieved socket section")
        construction["front_opening"] = front_opening()
        cutters.append(construction["front_opening"])
    for cutter in cutters:
        body = body.cut(cutter)
    return M.checked(body, "Matched receiver for user P21 support"), construction


# Flow-neutral receiver: the post and its socket stay inside the clean C28 spine between the air lobes.
SKIN = .84                      # two 0.42 mm P22 perimeters between the socket and the duct air
SLIP = .18                      # the existing P21/P22 sleeve slip
SPINE_BOX = (-9.0, 9.0, -42.0, -20.0)
SPINE_SECTION_Z = -58.0
SPINE_Z0 = -67.0


def recess_outline():
    r = M.R
    return [(-r.RECESS_HALF, -25.0), (-r.RECESS_HALF, r.RECESS_Y), (r.RECESS_HALF, r.RECESS_Y), (r.RECESS_HALF, -25.0)]


def spine_air_prism(air, section_z=SPINE_SECTION_Z, z0=SPINE_Z0, z1=SEAL_Z):
    """Clean duct air beside the spine, sectioned in plan and extruded over the post's height.

    Beside the spine the lobe walls are vertical (boss nose, island fillet and rear keel), so this prism and
    its plan offset bound the post exactly; at the floor elbow and under the roof it is conservative."""
    x0, x1, y0, y1 = SPINE_BOX
    plane = cq.Face.makePlane(200, 200, cq.Vector(0, 0, section_z), cq.Vector(0, 0, 1))
    section = air.intersect(plane).intersect(M.box(x0, x1, y0, y1, section_z - 1, section_z + 1))
    prisms = []
    for face in section.Faces():
        face = face.translate((0, 0, z0 - section_z))
        prisms.append(cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(), cq.Vector(0, 0, z1 - z0)))
    return prisms[0].fuse(*prisms[1:]).clean() if len(prisms) > 1 else prisms[0]


def plan_offset(prism, distance):
    """Exact plan offset of a vertical prism: offset its bottom face with arc joins, then re-extrude."""
    solids = []
    for solid in prism.Solids():
        faces = sorted(solid.Faces(), key=lambda f: f.Center().z)
        bottom, height = faces[0], faces[-1].Center().z - faces[0].Center().z
        maker = BRepOffsetAPI_MakeOffset(bottom.wrapped, GeomAbs_Arc)
        maker.Perform(distance)
        wires = sorted(cq.Shape.cast(maker.Shape()).Wires(), key=lambda w: -w.BoundingBox().DiagonalLength)
        face = cq.Face.makeFromWires(wires[0], wires[1:])
        solids.append(cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(), cq.Vector(0, 0, height)))
    body = solids[0].fuse(*solids[1:]).clean() if len(solids) > 1 else solids[0]
    if not body.isValid() or body.Volume() <= prism.Volume():
        raise ValueError("Plan offset failed")
    return body


def recess_fill(full=False):
    """Fill P21's sleeve recess (behind the sleeve front face, or all of it); the probe-cable passage stays open.

    The passage keeps 0.45 mm around the cable reference, whose vertical run sits 0.4 mm behind the
    released bore axis (Y-34.5), so it is cut around both axes."""
    r = M.R
    prism = r.shape(r.a.prism_xy_r(recess_outline(), r.RECESS_HALF - .41, SEAL_Z, r.P21_BOT))
    body = prism.intersect(M.box(-5, 5, -40, -24.0 if full else SLEEVE_FRONT_FACE_Y, SEAL_Z, r.P21_BOT))
    return M.checked(body.cut(cable_channel(SEAL_Z - 1, r.P21_BOT + 1)), "P21 recess fill")


CABLE_AXIS_Y = -34.9            # vertical run of the probe-cable reference (r1.5) through the joint
TOP_ZONE_Z = -57.2              # cable zone: P21's boss outline may continue down to here
BACK_MARGIN = .5                # socket stays this far inside the boss's back face, under its bottom


def cable_channel(z0, z1):
    """0.45 mm around the cable's vertical run (both axes) and a 4 mm slot forward along its bend."""
    return M.cylinder(0, CABLE_AXIS_Y, z0, z1, 1.95).fuse(
        M.cylinder(0, -34.5, z0, z1, 1.95), M.box(-1.95, 1.95, CABLE_AXIS_Y, -20, z0, z1))


def boss_shadow(z0, z1):
    """P21's cable-boss outline below its own bottom face, behind the sleeve front face."""
    return M.R.cable_boss(M.R.BOSS_Y, z0, z1).intersect(M.box(-6, 6, -40, SLEEVE_FRONT_FACE_Y, z0, z1))


KEEL_FAIRING = 3.0              # the skin keel fairs out of P21's boss outline at 45 deg over this height


def boss_outline_wire(grow, z):
    """P21's cable-boss plan outline grown by `grow` (an exact offset), as a wire at height z."""
    r, half, back = M.R, M.R.BOSS_HALF + grow, M.R.BOSS_Y - grow
    wire = r.a.rounded_polygon_wire_2d(
        [(-half, -25.0 + grow), (-half, back), (half, back), (half, -25.0 + grow)], [3.0 + grow] * 4)
    return cq.Wire(wire).translate((0, 0, z))


def shadow_keel(z0, z1):
    """45 deg keel under the boss-shadow skin's back, tangent to P21's boss arcs as the clean spine's own keel is
    tangent to its arcs, so the back-down P22 print needs no support in the plenum. Its top fairs out of the
    boss outline at 45 deg, so the descending air meets no ledge below the boss."""
    r, s = M.R, 3 * (1 - math.sqrt(.5))
    x_t, y_t = r.BOSS_HALF - s, r.BOSS_Y + s
    wire = cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in (
        (x_t, y_t), (0, y_t - x_t), (-x_t, y_t), (-x_t, y_t + 3), (x_t, y_t + 3))], close=True)
    keel = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, z1 - z0))
    h = min(KEEL_FAIRING, z1 - z0)
    fairing = cq.Solid.makeLoft([boss_outline_wire(0, z1), boss_outline_wire(h, z1 - h)], True)
    below = cq.Solid.extrudeLinear(boss_outline_wire(h, z0), [], cq.Vector(0, 0, z1 - h - z0))
    return M.checked(keel.intersect(fairing.fuse(below)), "Boss-shadow skin keel")


def front_corner_bevels(lobes_top, offset):
    """45 deg bevels where the boss-shadow socket meets the narrower spine at the sleeve face. Each is tangent to
    the `offset` round about the lobe corner, so the clearance to the air is kept and the back-down P22 print has
    no flat ceiling there."""
    cuts, y_c, d = [], SLEEVE_FRONT_FACE_Y, offset / math.sqrt(2)
    for side in (1, -1):
        probe = lobes_top.intersect(M.box(0 if side > 0 else -9, 9 if side > 0 else 0,
                                          y_c, y_c + .02, SEAL_Z - 1, SEAL_Z)).BoundingBox()
        tx, ty = (probe.xmin if side > 0 else probe.xmax) - side * d, y_c - d
        wire = cq.Wire.makePolygon([cq.Vector(x, y, SPINE_Z0) for x, y in (
            (tx, ty), (tx + side * 1.5, ty - 1.5), (tx + side * 1.5, ty))], close=True)
        cuts.append(cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, SEAL_Z - SPINE_Z0)))
    return cuts


def release_shadow(p22_body):
    """Plan shadow, grown by SLIP, of P22 material above the joint plane near the post, extended down over the
    post's height. The post stays outside it, so P22 drops clear of the fixed post along Z (and assembles)."""
    x0, x1, y0, y1 = SPINE_BOX
    above = p22_body.intersect(M.box(x0, x1, y0, y1, SEAL_Z + .005, M.R.P21_BOT + .5))
    prisms = []
    for z in np.linspace(SEAL_Z + .05, M.R.P21_BOT - .05, 7):
        for face in above.intersect(M.box(x0, x1, y0, y1, z - .005, z + .005)).Faces():
            if face.normalAt().z > .99 and face.Center().z > z:
                face = face.translate((0, 0, SPINE_Z0 - face.Center().z))
                prisms.append(cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(),
                                                     cq.Vector(0, 0, SEAL_Z - SPINE_Z0)))
    if not prisms:
        return None
    return plan_offset(prisms[0].fuse(*prisms[1:]).clean() if len(prisms) > 1 else prisms[0], SLIP)


def duct_air(p20, p21, p22):
    """Inlet-connected duct air of an assembly, with the CFD outlet box removed; also the leak test."""
    cap = cq.Solid.makeCylinder(8.2 + 2.5, 2.0, cq.Vector(0, -48.5, 29.0))
    space = M.box(-40, 40, -70, 60, -110, 45).cut(p20.fuse(p21).fuse(p22)).cut(cap).cut(
        M.box(-30, 30, -20, 50, -79.08, -45))
    return next(s for s in space.Solids() if s.isInside(cq.Vector(0, -48.5, 20.0)))


def clean_duct_air(p20, original_p21, angled_p22):
    """The clean C28 duct itself. Unlike the analytic channel corridor it includes the slivers beside the
    spine's rear corners, which a socket must not reach."""
    air = duct_air(p20, original_p21, angled_p22)
    b = air.BoundingBox()
    if b.xmin < -39 or b.xmax > 39 or b.ymin < -69 or b.zmax > 44:
        raise ValueError("The clean reference duct is not sealed")
    return air


def notch_removal(full=False):
    """P22's notch boss inside P21's recess: behind the sleeve face (its bridge in front stays), or all of it,
    so that nothing of P22 lies above the post's footprint when P22 drops off for service."""
    r = M.R
    prism = r.shape(r.a.prism_xy_r(recess_outline(), r.RECESS_HALF - .41, SEAL_Z - .01, r.P21_BOT + .1))
    return prism.intersect(M.box(-5, 5, -40, -24.0 if full else SLEEVE_FRONT_FACE_Y, SEAL_Z - .01, r.P21_BOT + .1))


def flow_neutral_parts(user_p21, original_p21, angled_p22, air, print_bevels=True, full_recess=True):
    """User post kept SKIN + SLIP inside the clean lobe walls, and its matched P22.

    In the cable zone behind the sleeve face the boundary is P21's own boss outline (its wake), so the
    post keeps a usable section around the cable; P22 adds only that thin skin there. Elsewhere the
    socket keeps SKIN of existing P22 between itself and the duct air. P21's filled recess seats on the
    remaining notch-boss bridge, closing the sleeve slip at the cable boss without a dam or skirt.
    print_bevels (v5c) adds the skin's faired 45 deg keel and the socket's 45 deg sleeve-face bevels;
    without them (v5b) the back-down P22 print needs support under those faces. full_recess (v5d) fills all
    of P21's recess, removes all of P22's notch boss and keeps the post out of the plan shadow of P22 above
    the joint, so P22 drops clear of the post; without it P22's notch boss sits over the post's arms."""
    x0, x1, y0, y1 = SPINE_BOX
    shadow = {k: boss_shadow(TOP_ZONE_Z - d, SEAL_Z) for k, d in (("post", 0), ("socket", SLIP), ("skin", SLIP + SKIN))}
    lobes = {k: (spine_air_prism(air, z0=TOP_ZONE_Z - d, z1=SEAL_Z).cut(shadow[k]),
                 spine_air_prism(air, z0=SPINE_Z0, z1=TOP_ZONE_Z - d)) for k, d in (("post", 0), ("socket", SLIP))}
    post_room = M.box(x0, x1, M.R.BOSS_Y + BACK_MARGIN + SLIP, y1, SPINE_Z0, SEAL_Z)
    socket_room = M.box(x0, x1, M.R.BOSS_Y + BACK_MARGIN, y1, SPINE_Z0, SEAL_Z)
    keep_post = post_room.cut(plan_offset(lobes["post"][0], SKIN + SLIP)).cut(plan_offset(lobes["post"][1], SKIN + SLIP))
    keep_socket = socket_room.cut(plan_offset(lobes["socket"][0], SKIN)).cut(plan_offset(lobes["socket"][1], SKIN))
    if print_bevels:
        keep_post = keep_post.cut(*front_corner_bevels(lobes["post"][0], SKIN + SLIP))
        keep_socket = keep_socket.cut(*front_corner_bevels(lobes["socket"][0], SKIN))
    added = user_p21.cut(original_p21, tol=1e-5)
    back_fill = M.box(-2.05, 2.05, -38.7, -34.0, -58.6, SEAL_Z).cut(cable_channel(-59, SEAL_Z + 1))
    notch = notch_removal(full_recess)
    release = release_shadow(receiver_base(angled_p22).cut(notch)) if full_recess else None
    if release is not None:
        keep_post = keep_post.cut(release)
    post = added.fuse(back_fill.intersect(M.box(-6, 6, -40, -34.0, -58.6, SEAL_Z)), tol=1e-4)
    post = post.intersect(M.box(-12, 12, -45, -15, -70, SEAL_Z)).intersect(keep_post)
    pieces = sorted(post.Solids(), key=lambda s: -s.Volume())
    fill = recess_fill(full_recess)
    upper = added.intersect(M.box(-12, 12, -45, SLEEVE_FRONT_FACE_Y, SEAL_Z, -40))
    p21 = original_p21.fuse(fill, pieces[0], *upper.Solids(), tol=1e-4)
    p21 = M.checked(p21, "Flow-neutral user P21")
    skin_zone = shadow["skin"]
    if print_bevels:
        skin_zone = skin_zone.fuse(shadow_keel(TOP_ZONE_Z - SLIP - SKIN, SEAL_Z))
    skin = skin_zone.intersect(air)
    socket = receiver_profile(SLIP, M.TONGUE_BOTTOM - SOCKET_CLEARANCE, SEAL_Z).intersect(keep_socket)
    hole = M.cylinder(0, M.RETAINER_Y, M.SEAT_Z - .1, -64, M.HOLE_R)
    p22 = receiver_base(angled_p22).fuse(skin, tol=1e-4).cut(socket).cut(notch).cut(hole)
    p22 = M.checked(p22, "Flow-neutral receiver")
    return p21, p22, {
        "lobes_top": lobes["socket"][0], "lobes_low": lobes["socket"][1], "keep_post": keep_post,
        "keep_socket": keep_socket,
        "post": pieces[0], "discarded_post_fragments_mm3": [s.Volume() for s in pieces[1:]],
        "user_upper_kept": upper, "recess_fill": fill, "boss_shadow_skin": skin, "socket": socket,
        "notch_removal": notch, "back_fill": back_fill, "print_bevels": print_bevels, "full_recess": full_recess,
        "release_shadow": release,
        "skin_keel_beyond_boss_wake": skin.cut(shadow["skin"]) if print_bevels else None,
    }
