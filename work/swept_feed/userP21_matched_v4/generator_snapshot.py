"""Use the user's sloping P21 support as the input for a separate matched-joint study."""
from pathlib import Path
import math

import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections

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
