"""Revision 41: fixes from the first physical build.

Printing and assembling the carriage showed these problems:
  1. P24 (EBB42 mount) was too complicated and had thin areas;
  2. the CPAP outlet was too small and restricted the blower;
  3. the CPAP joints went together well but had thin walls;
  4. P03 should come in one variant per magnet instead of one universal pocket;
  5. the MG90D servo had a little slack in P02's recess;
  6. P22's cheeks wrapped P01's front bosses with walls down to 0.05 mm;
  7. P21's top, its print face, was on two levels: the saddle under P24 sat 0.62 mm below the trunk rim;
  8. the hall sensor's leads had no way through P02, and P24's groove for them stopped 8.2 mm short of the EBB42;
  9. P01 kept a tab under its +X front frame screw, in a matching slot in P03.

Revision 41 changes P20, P21 and P22 (joints, horizontal bell-mouth jets, face mounts on P01, one flat top on
P21), replaces P24 with a plain frame, tightens P02's servo recess, opens a groove for the hall sensor's leads
through P02 and P24, cuts P01's tab off and splits P03 into four magnet variants. Every
interface (fastener positions, the EBB42 and probe positions, the outer shape of the CPAP parts) stays where it
was, except that P24 now sits 0.62 mm higher on P21's raised saddle.
"""
import json

import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Trsf, gp_Vec
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopoDS import TopoDS

import build_and_verify_accessories_v26 as acc
import r37_parts as P37
import r40_parts as P40
from build_bambu_clean_r29 import single
from build_carriage_lowered_mounts_r31 import BOSS_X as P01_BOSS_X, BOSS_Y as P01_BOSS_Y, NEW_Z as P01_BOSS_Z
from build_carriage_lowered_mounts_r31 import NAMES as R31_NAMES
from build_modular_toolhead import load

a = acc
NAMES = {
    "p01": "P01_Back_case_COTS_MR74_Lowered_Bosses_No_Tab_R41_REVIEW",
    "p20": "P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW",
    "p21": "P21_CPAP_Gantry_Bridge_Thick_Joints_R41_REVIEW",
    "p22": "P22_CPAP_Lower_Plenum_Wide_Jets_Face_Mounts_R41_REVIEW",
    "p24": "P24_EBB42_Frame_Mount_R41_REVIEW",
    "p02": "P02_Motor_Servo_Plate_MG90D_Snug_Pocket_R41_REVIEW",
    "hardware": "P24_P22_Screws_And_Inserts_R41_REVIEW",
    "assembly": "41_Carriage_Build_Fixes_Complete_REVIEW",
    "review": "41_Carriage_Build_Fixes_REVIEW",
}
MAGNETS = ("15x5x3", "12x6x3", "D6x4", "D6x3")
for _m in MAGNETS:
    NAMES[f"p03_{_m}"] = f"P03_Front_Case_Magnets_{_m}_R41_REVIEW"


def shape(s):
    return P37.shape(s)


def unify(s):
    """Merge coplanar faces; some cone and lean-back face pairs defeat B-spline concatenation, so back off."""
    s = s.wrapped if isinstance(s, cq.Shape) else s
    for flags in ((True, True, True), (True, True, False), (False, True, False)):
        try:
            u = ShapeUpgrade_UnifySameDomain(s, *flags)
            u.Build()
            out = shape(u.Shape())
        except Exception:
            continue
        if out.isValid():
            return out
    return shape(s)


def fuse(*items):
    return shape(a.fuse_all([i.wrapped if isinstance(i, cq.Shape) else i for i in items]))


def cut(base, cutters):
    base = base.wrapped if isinstance(base, cq.Shape) else base
    return shape(a.cut_all(base, [c.wrapped if isinstance(c, cq.Shape) else c for c in cutters]))


def common(base, tools):
    base = base.wrapped if isinstance(base, cq.Shape) else base
    return shape(a.intersect_all(base, [t.wrapped if isinstance(t, cq.Shape) else t for t in tools]))


# --------------------------------------------------------------------------------------------
# CPAP joints: P20 -> P21 at Z-21.58..-17.78 and P21 -> P22 at Z-51.4..-49.0
# --------------------------------------------------------------------------------------------
# Released (corridor offsets from the conduit's outer skin): female socket wall 0.84 mm (two perimeters),
# 0.18 mm radial slip, male sleeve wall 0.82 mm, bore at 1.84. Revision 41 thickens both walls inward to
# 1.25 mm (three perimeters) and keeps the slip, so the outside of every part and the fit stay the same.
# The bore through each sleeve narrows to the 2.68 offset (about 205 mm2, against the 211 mm2 hose bore);
# a 45 degree taper leads into it from the part's own cavity. Above P20's split that cavity leans back
# toward the hose cuff, so the taper fills out to the cavity wall rather than standing as a separate lip.
# P22's socket floor met the roof of its forward sweep in a feather edge along the front (0.03 mm, released);
# revision 41 cuts that edge back to the socket wall. P21 seats on P22's top rim, not on that edge. The cut stays
# inside the duct's own plan outline (p22_air_xy), so it stops exactly on the cable boss and the side walls.
OLD_SOCKET, OLD_SLEEVE_OUT, OLD_BORE = (0.84, 2.7), (1.02, 2.5), (1.84, 2.0)   # (offset, corner radius)
SOCKET_WALL, SLIP, SLEEVE_WALL = 1.25, 0.18, 1.25
SOCKET = (SOCKET_WALL, 3.5 - SOCKET_WALL)
SLEEVE_OUT = (SOCKET_WALL + SLIP, 3.5 - SOCKET_WALL - SLIP)
BORE = (SOCKET_WALL + SLIP + SLEEVE_WALL, 3.5 - SOCKET_WALL - SLIP - SLEEVE_WALL)
TAPER = BORE[0] - OLD_BORE[0]
CONE_RISE = 2.0                       # height of the 45 degree cone that bounds each taper fill
P22_FRONT_EDGE = (-35.15, -51.95)      # Y and Z limits of the cut-back
# Cable boss at the front centre of each joint (probe cable at X0, Y-34.5, r1.95): the socket's boss grows
# back and sideways, the sleeve's matching recess follows with the same 0.06 mm slip, and the sleeve part's own
# boss grows to keep 1.2 mm beside and behind the recess. Released: 0.85 mm around the cable in the socket's
# boss and 0.79 mm in the sleeve's.
OLD_NOTCH_Y, OLD_RECESS_Y, OLD_BOSS_Y = -37.30, -37.36, -38.15
NOTCH_Y, RECESS_Y, BOSS_Y = -37.66, -37.72, -38.97
OLD_NOTCH_HALF, NOTCH_HALF, RECESS_HALF, BOSS_HALF = 2.80, 3.20, 3.26, 4.46
P20_SPLIT, P20_SLEEVE_BOT = -17.78, -21.58
# Behind the released boss's wall the new boss rises to P20_BOSS_TOP, over the released boss's top (Z-12.62), so
# none of it stands above the new one; in front of that wall it stops at the usual height, under the cavity's r4
# blend, which crosses the new boss's corner at Z-12.62. The wall hides the change of height between the two.
P20_BOSS_TOP, P20_BOSS_BACK_Y = -12.55, -36.9
P21_TOP, P21_BOT, P21_SLEEVE_BOT = -17.78, -49.00, -51.40
SADDLE_Z = -18.40                     # released P21 saddle under P24, 0.62 mm below the rest of P21's top


def corridor(offset_r, z0, z1):
    offset, r = offset_r
    return shape(a.prism_xy_r(a.corridor_aero_vertices(offset), r, z0, z1))


def corridor_wire(offset_r, z):
    offset, r = offset_r
    wire = a.rounded_polygon_wire_2d(a.corridor_aero_vertices(offset), r)
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(0, 0, z))
    return cq.Wire(TopoDS.Wire_s(BRepBuilderAPI_Transform(wire, t, True).Shape()))


def cavity_fill(body, z_end):
    """Fill the part's own cavity above the narrowed sleeve bore, outside a 45 degree cone rising from it."""
    cone = cq.Solid.makeLoft([corridor_wire(BORE, z_end),
                              corridor_wire((BORE[0] - CONE_RISE, BORE[1] + CONE_RISE), z_end + CONE_RISE)], True)
    return cut(corridor((1.0, 2.5), z_end, z_end + CONE_RISE), [body, cone])


def ring(outer, inner, z0, z1):
    return cut(corridor(outer, z0, z1), [corridor(inner, z0 - 0.1, z1 + 0.1)])


def notch(y_back, half_x, z0, z1):
    r = half_x - 0.40
    return shape(a.prism_xy_r([(-half_x, -25.0), (-half_x, y_back), (half_x, y_back), (half_x, -25.0)], r, z0, z1))


def cable_boss(y_back, z0, z1, half_x=BOSS_HALF):
    return shape(a.prism_xy_r([(-half_x, -25.0), (-half_x, y_back), (half_x, y_back), (half_x, -25.0)], 3.0, z0, z1))


def socket_fill(z0, z1):
    """Thicker female socket wall plus the deeper cable-boss notch, inside the released recess only."""
    released = cut(corridor(OLD_SOCKET, z0, z1), [notch(OLD_NOTCH_Y, OLD_NOTCH_HALF, z0 - 0.1, z1 + 0.1)])
    wall = ring(OLD_SOCKET, SOCKET, z0, z1)
    boss = common(notch(NOTCH_Y, NOTCH_HALF, z0, z1), [corridor(OLD_SOCKET, z0, z1)])
    return common(fuse(wall, boss), [released])


def sleeve_fix(body, z_sleeve_bot, z_end, back_top=None):
    """Male sleeve: shave the outside to SLEEVE_OUT, fill the bore to BORE, deepen the boss recess and grow
    the part's own cable boss, then re-cut the probe-cable channel. back_top (P20) raises the boss's back part."""
    shave = ring(OLD_SLEEVE_OUT, SLEEVE_OUT, z_sleeve_bot - 0.6, z_end)
    fill = ring(OLD_BORE, BORE, z_sleeve_bot, z_end)
    boss_top = z_end + TAPER + 4.0
    boss = common(cable_boss(BOSS_Y, z_sleeve_bot, boss_top), [corridor(OLD_BORE, z_sleeve_bot, boss_top)])
    if back_top is not None:
        back = common(cable_boss(BOSS_Y, z_sleeve_bot, back_top), [corridor(OLD_BORE, z_sleeve_bot, back_top),
                                                                     shape(a.box(-10.0, 10.0, -45.0, P20_BOSS_BACK_Y,
                                                                                 z_sleeve_bot - 1.0, back_top + 1.0))])
        boss = fuse(boss, back)
    recess = shape(a.prism_xy_r([(-RECESS_HALF, -25.0), (-RECESS_HALF, RECESS_Y), (RECESS_HALF, RECESS_Y),
                                 (RECESS_HALF, -25.0)], RECESS_HALF - 0.41, z_sleeve_bot - 0.6, z_end))
    body = fuse(body, fill, cavity_fill(body, z_end), boss)
    return cut(body, [shave, recess])


def p20():
    body = load(P40.NAMES["p20"])
    body = sleeve_fix(body, P20_SLEEVE_BOT, P20_SPLIT, P20_BOSS_TOP)
    body = cut(body, [shape(a.cyl_z(0.0, -34.5, P20_SLEEVE_BOT - 1.0, -15.8, 1.95)),
                      shape(a.cyl_y(0.0, -15.8, -34.5, -25.0, 1.95)),
                      shape(a.box(-1.95, 1.95, -34.5, -25.0, P20_SPLIT - 0.2, -13.85))])
    return single(unify(body), "revision-41 P20")


def saddle_raise(body):
    """P21's top as one plane: the saddle under P24 (Z-18.40) is extruded up to the trunk rim and the P20-lug
    bosses (P21_TOP), so the part prints top-down on a single flat face. The face's two insert holes go straight
    up through the new layer; the inserts stay where they were, 0.62 mm under the new face."""
    faces = [f for f in body.Faces() if f.geomType() == "PLANE" and f.normalAt().z > 0.99
             and abs(f.BoundingBox().zmin - SADDLE_Z) < 1e-6 and abs(f.BoundingBox().zmax - SADDLE_Z) < 1e-6]
    if len(faces) != 1:
        raise ValueError(f"P21 saddle: {len(faces)} faces at Z{SADDLE_Z}")
    layer = shape(BRepPrimAPI_MakePrism(faces[0].wrapped, gp_Vec(0, 0, P21_TOP - SADDLE_Z)).Shape())
    return fuse(body, layer)


def p21():
    body = load(P40.NAMES["p21"])
    body = fuse(body, socket_fill(-21.58, P21_TOP))
    body = sleeve_fix(body, P21_SLEEVE_BOT, P21_BOT)
    # the conduit's own boss between the joints (the sleeve below P21_BOT keeps its recess)
    body = fuse(body, common(cable_boss(BOSS_Y, P21_BOT, -21.58), [corridor(OLD_BORE, P21_BOT, -21.58)]))
    body = cut(body, [shape(a.cyl_z(0.0, -34.5, P21_SLEEVE_BOT - 1.0, P21_TOP + 1.0, 1.95)),
                      shape(a.box(-1.95, 1.95, -34.5, -30.0, P21_SLEEVE_BOT - 1.0, P21_TOP + 1.0))])
    body = saddle_raise(body)
    return single(unify(body), "revision-41 P21")


# --------------------------------------------------------------------------------------------
# P22 outlet. Released: one louver jet each side of the nozzle, its throat 1.8 mm tall (Z-76.65..-74.85) and
# about 11 mm long, 42 mm2 in all against 154-175 mm2 in the side channels feeding it. The vane over each
# throat tapered to a knife edge (0.04 mm), and the floor lip under it (|X| 8.5-10.2) ended in a feather edge
# where the duct's floor curves up at the rear.
# The jets stay horizontal, aimed across the nozzle at the plastic it has just laid down, not down at the bed.
# They can only grow upward: P22's underside is 1 mm above the nozzle tip and the floor over it is 1.2 mm thick.
# Revision 41 cuts the vane off at ROOF, leaving the wall between the duct and the hotend slot a flat bottom
# 1.4 mm wide, and trims the floor lip back to that wall's face (|X| 10.2), so each jet leaves through a taller
# opening. The Red Lizard's heater block (bottom Z-73.28) stays above the jets. On the Bambu the upper part of
# each jet meets the side of the silicone sock (bottom Z-75.48), as the released jets' top 0.6 mm did.
# P22's outside shape is unchanged.
# --------------------------------------------------------------------------------------------
ROOF = -73.6                                     # flat bottom of the duct-to-slot wall (released vane tip -74.85),
                                                 # 0.32 mm under the Red Lizard block
WALL_X = (10.2, 11.6)                            # |X| of that wall's faces: the hotend slot inside, the duct outside
THROAT_Y = (16.0, 28.2)                          # Y range of the vane cut (the heel and the front wall bound it)
LIP = (8.4, 15.0, 30.0, -78.5, -74.3)            # floor-lip trim: inner |X|, Y range and Z range (out to WALL_X[0])
# The duct's own YZ profile and plan outline, as build_p22_lower_plenum makes them (horn_yz_in, xy_inner_full,
# cable_boss_nose and center_island_body), so the cuts below stop exactly on the released surfaces.
HORN_IN = [(-43.56, -68.90), (-43.56, -48.50), (-35.04, -48.50), (-35.04, -51.40), (-21.413, -58.60), (0.00, -58.60),
           (9.20, -58.60), (16.00, -62.40), (22.80, -70.10), (28.20, -73.40), (28.20, -76.65), (19.60, -76.65),
           (12.20, -68.90)]
HORN_IN_R = [14.8, 0, 0, 0, 61.0, 0, 14.5, 14.5, 10.5, 0.8, 0.5, 6.5, 6.5]
XY_INNER = [(-12.16, -43.56), (-18.76, -37.36), (-18.76, -26.50), (-21.02, -19.50), (-21.02, 14.80),
            (-19.00, 22.00), (-13.80, 27.20), (-8.50, 28.20), (8.50, 28.20), (13.80, 27.20), (19.00, 22.00),
            (21.02, 14.80), (21.02, -19.50), (18.76, -26.50), (18.76, -37.36), (12.16, -43.56)]
XY_INNER_R = [2.0, 2.0, 14.0, 14.0, 10.6, 8.6, 3.0, 0.0, 0.0, 3.0, 8.6, 10.6, 14.0, 14.0, 2.0, 2.0]
XY_BOSS_NOSE = [(-3.65, -20.00), (-3.65, -38.15), (3.65, -38.15), (3.65, -20.00)]   # corner radius 3.0
XY_ISLAND = [(-3.65, -36.50), (-3.65, -31.00), (-12.85, -16.50), (-12.85, 13.50), (-11.60, 17.50), (-11.60, 30.00),
             (11.60, 30.00), (11.60, 17.50), (12.85, 13.50), (12.85, -16.50), (3.65, -31.00), (3.65, -36.50)]
XY_ISLAND_R = [0.0, 14.0, 14.0, 4.0, 4.0, 0.0, 0.0, 4.0, 4.0, 14.0, 14.0, 0.0]
# The heel: the channel floor rises from the jet's floor (Z-76.65, Y19.6) to Z-68.9 at Y12.2 (r6.5 at each end)
# and crosses ROOF here, so the jet ends where the floor meets the wall's flat bottom.
HEEL_Y = 19.60 + (ROOF + 76.65) * (12.20 - 19.60) / (76.65 - 68.90)


def horn_in(x0, x1):
    """The duct's air in side view: above its floor and below its roof."""
    return a.prism_yz_r(HORN_IN, HORN_IN_R, x0, x1)


def p22_air_xy(z0, z1):
    """The duct's air in plan: inside its outer wall, outside the cable boss and the hotend's centre island."""
    return cut(a.prism_xy_r(XY_INNER, XY_INNER_R, z0, z1),
               [a.prism_xy_r(XY_BOSS_NOSE, 3.0, z0 - 1.0, z1 + 1.0), a.prism_xy_r(XY_ISLAND, XY_ISLAND_R, z0 - 1.0, z1 + 1.0)])


def vane_cut(side):
    """The vane below ROOF, inside the channel's outline and above its floor, so neither the front wall nor the floor
    behind the louver is touched and the wall's bottom is flat back to the heel. It reaches |X| 12.9 because the wall
    thickens behind the jet (its outer face runs out to |X| 12.85 by Y13.5); outboard of the wall it only cuts air."""
    lo, hi = sorted((side * (WALL_X[0] - 0.05), side * 12.9))
    z0 = -75.0
    inside = a.prism_xy_r(XY_INNER, XY_INNER_R, z0 - 1.0, ROOF + 1.0)
    return common(a.box(lo, hi, THROAT_Y[0], THROAT_Y[1], z0, ROOF), [horn_in(lo - 1.0, hi + 1.0), inside])


def lip_cut(side):
    """The floor lip and the ledge over it, inboard of the duct-to-slot wall: the slot is |X| <= 10.2 to the bottom."""
    x0, y0, y1, z0, z1 = LIP
    lo, hi = sorted((side * x0, side * WALL_X[0]))
    return shape(a.box(lo, hi, y0, y1, z0, z1))


# The released floor-to-front-wall fillet (r0.5, horn_yz_in's corner at Y28.2) runs straight across in X, but the
# front wall slants back outboard of |X| 8.5, so a strip of fillet 0.03 mm high stood in front of it at the jet's
# front corner (|X| 10.2-11.15). This trims it, so the jet's floor meets the front wall.
JET_FLOOR_CORNER = (10.1, 11.3, 27.6, 28.3, -76.65, -76.3)


def jet_floor_corner(side):
    x0, x1, y0, y1, z0, z1 = JET_FLOOR_CORNER
    return common(a.box(*sorted((side * x0, side * x1)), y0, y1, z0, z1),
                  [a.prism_xy_r(XY_INNER, XY_INNER_R, z0 - 1.0, z1 + 1.0)])


# Bell-mouth jets (from the CFD, cfd_cpap_r41.py). The air comes down the duct face of the duct-to-slot wall and
# turns under it into the jet. Off a square corner it springs clear and leaves through about 0.56 of the opening,
# so the blower has to push it out faster than the opening needs. Rounding that corner, radius the wall's 1.4 mm
# thickness, lets the air follow it round. The wall's lowest point stays at ROOF on the slot side, a 90 degree
# edge, so the jets keep their height under the Red Lizard. P22 prints on its back face, so the round lies flat
# in every layer. The round runs where the duct face is straight; behind Y18 the wall thickens to |X| 11.85 at
# the heel, and the cut squares that off below the round's top (a ledge up to 0.25 mm) rather than leave a fin. It
# starts at the heel, where the floor meets the wall's bottom, and stops before the front roof, which slopes down
# over the jet's last 1.7 mm and leads the air in itself.
JET_LIP_R = 1.4
JET_LIP_Y = (HEEL_Y, 26.2)
JET_LIP_X_OUT = 11.9                             # past the thickened wall at the rear (|X| 11.85 at the heel)


def jet_lip_cut(side):
    x = side * WALL_X[1]
    lo, hi = sorted((x - side * JET_LIP_R, side * JET_LIP_X_OUT))
    corner = shape(a.box(lo, hi, JET_LIP_Y[0], JET_LIP_Y[1], ROOF - 0.01, ROOF + JET_LIP_R))
    corner = corner.cut(shape(a.cyl_y(x - side * JET_LIP_R, ROOF + JET_LIP_R, JET_LIP_Y[0] - 0.1, JET_LIP_Y[1] + 0.1,
                                      JET_LIP_R)))
    return common(corner, [horn_in(lo - 1.0, hi + 1.0)])


def outlet_cutters(bell_mouth=True):
    return [c for side in (-1, 1)
            for c in (vane_cut(side), lip_cut(side), jet_floor_corner(side)) + ((jet_lip_cut(side),) if bell_mouth else ())]


# --------------------------------------------------------------------------------------------
# P22 to P01: face mounts. Released: each upper cheek wrapped around P01's front boss (r4.0, Y11.4-15.9). The
# wrap was 0.05 mm thick on the inner side and 0.42 mm on the outer, and open on top, where the boss stands
# 0.22 mm above the cheek; the screw head's counterbore came within 0.05 mm of the outer face.
# Revision 41 stops each cheek at the boss's front face: P22 bears on the boss face to face and the screw
# locates it. The counterbore is filled, so the cheek is solid around a plain Ø3.3 hole, and an M3x8 ISO 7380
# button head sits on the cheek's front face, 3.6 mm clear of the mounted tool.
# --------------------------------------------------------------------------------------------
CHEEK_FACE = P01_BOSS_Y[1] + 0.05               # P22's cheek ends here, against the boss's front face
CHEEK_X = (13.9, 22.5)                           # |X| span cleared behind that face (the cheek is X13.95-22.42)
HORN_OUT = [(-45.40, -70.80), (-45.40, -49.00), (-33.20, -49.00), (-33.20, -49.50), (-20.736, -57.36),
            (0.00, -57.36), (9.80, -57.36), (16.80, -61.20), (23.50, -68.80), (29.60, -72.20), (29.60, -77.85),
            (19.00, -77.85), (11.55, -70.80)]   # build_p22_lower_plenum's horn_yz_out: P22's outer YZ profile
HORN_OUT_R = [16.0, 0, 0, 0, 50.0, 0, 16.0, 16.0, 12.0, 1.2, 0.8, 7.5, 7.5]
CHEEK_YZ = [(11.48, -66.00), (20.50, -66.00), (19.80, -48.00), (11.48, -48.00)]   # the cheeks' YZ profile
CHEEK_YZ_R = [0, 1.0, 1.0, 0]
HOLE_R, COUNTERBORE = 1.65, (18.10, 3.02)        # screw hole; the released counterbore (r3.0 from Y18.2) is filled


def cheek_front_y(z):
    """Y of the cheek's front face, which leans back 0.7 mm over its 18 mm height."""
    (_, z0), (y0, _), (y1, z1) = CHEEK_YZ[0], CHEEK_YZ[1], CHEEK_YZ[2]
    return y0 + (y1 - y0) * (z - z0) / (z1 - z0)


def cheek_cuts():
    """Everything of each cheek behind the boss's front face, down to P22's outer skin (its roof is untouched)."""
    horn = a.prism_yz_r(HORN_OUT, HORN_OUT_R, -23.0, 23.0)
    out = []
    for side in (-1, 1):
        lo, hi = sorted((side * CHEEK_X[0], side * CHEEK_X[1]))
        out.append(cut(a.box(lo, hi, P01_BOSS_Y[0] - 0.4, CHEEK_FACE, -63.0, -49.5), [horn]))
        out.append(shape(a.cyl_y(side * P01_BOSS_X[1], P01_BOSS_Z, CHEEK_FACE - 0.5, 21.5, HOLE_R)))
    return out


def counterbore_fills():
    envelope = a.prism_yz_r(CHEEK_YZ, CHEEK_YZ_R, -23.0, 23.0)
    y0, r = COUNTERBORE
    return [common(a.cyl_y(side * P01_BOSS_X[1], P01_BOSS_Z, y0, 21.0, r), [envelope]) for side in (-1, 1)]


# The released cheek's pocket round P01's boss dipped 0.1 mm below P22's outer skin just behind the boss
# (X+-17.1..18.9, Y11.00-11.25); cutting the cheek back to the skin left that as a crescent pit 0.1 mm deep.
# These fill it back up to the skin, 1.15 mm clear of the duct's bore and 0.1 mm short of the boss.
PIT_FILL = (17.0, 19.0, 11.0, 11.3, -58.45, -58.0)


def pit_fills():
    horn = a.prism_yz_r(HORN_OUT, HORN_OUT_R, -23.0, 23.0)
    x0, x1, y0, y1, z0, z1 = PIT_FILL
    return [common(a.box(*sorted((side * x0, side * x1)), y0, y1, z0, z1), [horn]) for side in (-1, 1)]


def p22_front_edge():
    """The feather edge where P22's socket floor meets the roof of its forward sweep, cut back to the socket wall,
    within the duct's plan outline: it stops on the cable boss's side and on the duct's side walls."""
    y0, z0 = P22_FRONT_EDGE
    z1 = P21_SLEEVE_BOT + 0.01
    return [common(corridor(SOCKET, z0, z1), [shape(a.box(-25.0, 25.0, y0, -30.0, z0, z1)), p22_air_xy(z0 - 1.0, z1 + 1.0)])]


def p22(bell_mouth=True):
    """bell_mouth=False gives revision 41's first, square-edged jets (the CFD's comparison case)."""
    body, _ = P37.p22()
    body = fuse(body, socket_fill(P21_SLEEVE_BOT, P21_BOT), *counterbore_fills())
    body = cut(body, outlet_cutters(bell_mouth) + p22_front_edge() + cheek_cuts() + [
        shape(a.cyl_z(0.0, -34.5, -58.6, -48.0, 1.95)),
        shape(a.box(-1.95, 1.95, -34.5, -30.0, -58.6, -48.0)),
    ])
    body = fuse(body, *pit_fills())
    return single(unify(body), "revision-41 P22")


# --------------------------------------------------------------------------------------------
# P24: a plain frame. Released: about 20 blocks, a three-slot wire comb, two dead rear holes and generous box
# windows for the EBB42's connectors, which left 0.03-0.85 mm walls around the inserts and thin arcs where
# the motor-bore cutter sliced through its legs and feet.
# Revision 41 keeps every interface: the EBB42 on its four corner standoffs (Y-25.40), the two vertical M3s
# into P21 at (+-6, -15.8), and bearing on P02's rear face (Y-6.70). Its underside sits on P21's saddle, which
# revision 41 raises 0.62 mm to P21's top plane (Z-17.78), so the foot under the deck is 0.62 mm shorter; the
# deck and everything above it stay put. The frame is a bottom block on P21, a
# solid wall at +X, a column at -X, a block over each top corner and a tower under each bottom corner, all
# reaching P02's face, which is also the print face. Clearances follow the EBB42's actual parts, its
# connectors' plugs and wires, the motor body and lead connector, the probe cable and the hall-sensor leads.
# The comb, the dead holes and the hook are gone: P21's two screws carry the frame, and the hook only
# rested on P02's top edge.
# Each M3 x 4 heat-set (OD 4.2, now a Ø4.0 hole) moves 2.8 mm forward to Y-22.6..-18.6. It is pressed in from
# the bay side behind a Ø3.4 clearance step, so the screw pulls it against the step; the two upper ones go in
# through Ø4.4 channels in the corner blocks. The corner blocks reach Z27.2, 2.06 mm under the MG90D (released
# P24: 1.76 mm), and down to just above the header and connector plugs, so every channel has 0.95 mm or more around
# it. The two core button heads on P02's rear face sit in U-slots that open straight through the nearest
# block face. The -X column keeps the released P24's -X face (X-21.8) for its end-stop clearance. The walls
# beside the MicroFit, the heater terminal and the probe header reach 1.0-1.2 mm (released 0.25-0.65 mm).
# The upper screws (through P20's wings) stay M3x18 and now pass through the whole insert; the lower ones grow
# to M3x14.
# --------------------------------------------------------------------------------------------
EBB_CORNERS = {"TR": (-16.748, 22.0), "TL": (14.252, 22.0), "BL": (14.252, -9.0), "BR": (-16.748, -9.0)}
Y_SEAT, Y_FRONT = -25.40, -6.70
HALL_GROOVE = (-2.00, 2.00, -16.10, -14.0)   # X and Z of the hall sensor leads' groove under the motor, through P02
                                             # and P24 to the EBB42's side of the frame; the motor is its roof
BOSS_R = 3.5
INSERT = (-22.60, -18.60, 2.00)        # heat-set pocket: Y range and radius
CLEAR_R, PRESS_R = 1.70, 2.20          # screw clearance behind the insert; pressing channel in front of it
Z_BASE, Z_BLOCK_TOP = P21_TOP, -14.40  # underside on P21's saddle (raised to P21's top plane); top of the bottom
                                       # deck, under the motor
Z_DECK = -16.95                        # below this P24 keeps to P21's saddle outline: at the X limits the 9 mm 2WD
                                       # XY joints reach in to |X|10.7 behind Y-13.75, their M5 heads up to Z-17.63
SADDLE = [(-9.20, -34.50), (-9.20, -12.10), (-21.00, -9.70), (-21.00, 0.30), (21.00, 0.30), (21.00, -9.70),
          (9.20, -12.10), (9.20, -34.50)]   # P21's saddle outline (build_p21_mid's up_bridge_verts, r2.2)
MOTOR = (-1.248, 4.251, 18.25)         # round AHG stator: centre X, Z and radius
P21_SCREWS = ((-6.0, -15.8), (6.0, -15.8))
SIDE_X = (19.0, 22.1)
COLUMN = (-21.8, -20.0, -13.0)         # -X column: X range and rear face (the right connectors' plugs behind)
TOP_Z = 27.2                           # top of the +X wall and both corner blocks
TL_BLOCK = (10.75, 17.30)              # -X face and bottom of the top-left block (the header plugs trim it)
TR_BLOCK = (-12.20, 17.00)             # +X face and bottom of the top-right block (the MicroFit zone trims it)
SCREW_HEADS = ((17.25, 23.72, 1), (-16.748, 19.75, -1))   # core button heads: X, Z, U-slot opens up (+1)/down
HEAD_R = 3.2
PLUG_ZONES = (
    # left headers, one zone per pin column (servo PB6, hall sensor PB8, probe): plugs and wires toward +Y
    (10.45, 13.35, -36.0, -12.5, 6.55, 14.55),
    (13.25, 16.15, -36.0, -12.5, 6.55, 17.05),
    (16.05, 18.95, -36.0, -12.5, 6.55, 19.55),
    # right-edge connectors
    (-20.70, -13.90, -36.0, -13.0, 9.60, 16.40),
    (-21.40, -15.50, -36.0, -13.0, -5.80, 7.00),
    # MicroFit 3.0 (power and CAN): plug and cable from above
    (-13.60, -3.20, -36.0, -16.4, 8.00, 52.0),
    # heater and thermistor terminal: wires leave downward
    (-14.00, -5.90, -36.0, -22.7, -19.5, -5.90),
)


def ebb_clearances():
    """The EBB42's parts on the motor side of the board, each grown 0.25 mm, and its plug zones."""
    out = []
    for s in P37.ebb42().Solids():
        b = s.BoundingBox()
        if b.ymax < Y_SEAT - 0.3:
            continue
        out.append(shape(a.box(b.xmin - 0.25, b.xmax + 0.25, b.ymin - 0.25, b.ymax + 0.25, b.zmin - 0.25, b.zmax + 0.25)))
    return out + [shape(a.box(*z)) for z in PLUG_ZONES]


def block(x0, x1, y0, z0, z1, r=1.0):
    """A frame member from y0 to P02's face, rounded on its rear edges only: rounding the front edges would pinch
    the channels and U-slots that open on that face, which is also the print face."""
    return a.prism_xy_r([(x0, y0), (x1, y0), (x1, Y_FRONT), (x0, Y_FRONT)], [r, r, 0.0, 0.0], z0, z1)


def p24():
    foot = common(a.prism_xy_r(SADDLE, 2.2, Z_BASE, Z_DECK + 0.01), [a.box(-30.0, 30.0, Y_SEAT, Y_FRONT, Z_BASE - 1.0, Z_DECK + 1.0)])
    members = [
        foot,
        block(COLUMN[0], SIDE_X[1], Y_SEAT, Z_DECK, Z_BLOCK_TOP),
        block(SIDE_X[0], SIDE_X[1], Y_SEAT, Z_DECK, TOP_Z),
        block(TL_BLOCK[0], SIDE_X[1], Y_SEAT, TL_BLOCK[1], TOP_Z),
        block(COLUMN[0], COLUMN[1], COLUMN[2], Z_DECK, TR_BLOCK[1] + 1.0, 0.8),
        block(COLUMN[0], TR_BLOCK[0], Y_SEAT, TR_BLOCK[1], TOP_Z),
    ]
    for x, z in EBB_CORNERS.values():
        members.append(a.cyl_y(x, z, Y_SEAT, INSERT[1], BOSS_R))
        if z < 0:
            members.append(a.box(x - BOSS_R, x + BOSS_R, Y_SEAT, INSERT[1], Z_BLOCK_TOP - 0.1, z))
    body = fuse(*members)
    cutters = ebb_clearances() + [
        # motor body and its lead connector (its leads are routed above the bottom block, Z-13.8..-4.8)
        a.cyl_y(MOTOR[0], MOTOR[1], -17.2, 1.0, MOTOR[2] + 0.5),
        a.box(-19.85, -10.44, -17.45, -10.95, -14.35, -4.94),
        # probe cable (revision-37 route) turning up into the bay; hall-sensor leads under the motor, in a groove
        # right through to the EBB42's side of the frame (it stopped at the motor's end cap, 8.2 mm short)
        a.box(-1.95, 1.95, -26.0, -19.40, -19.0, -14.0),
        a.box(HALL_GROOVE[0], HALL_GROOVE[1], Y_SEAT - 0.2, Y_FRONT + 0.1, HALL_GROOVE[2], HALL_GROOVE[3]),
    ]
    # core button heads on P02's rear face (the plate-to-P01 screw and the upper motor-ear screw), in U-slots;
    # the lower one also opens out through the block's +X face, so its wall can't meet the motor arc at a point
    for x, z, up in SCREW_HEADS:
        slot = (a.box(x - HEAD_R, x + HEAD_R, -10.0, -6.0, z, TOP_Z + 1.0) if up > 0 else
                a.box(x - HEAD_R, TR_BLOCK[0] + 1.0, -10.0, -6.0, TR_BLOCK[1] - 1.0, z))
        cutters += [a.cyl_y(x, z, -10.0, -6.0, HEAD_R), slot]
    for x, y in P21_SCREWS:
        cutters += [a.cyl_z(x, y, Z_BASE - 0.2, Z_BLOCK_TOP + 0.2, CLEAR_R),
                    a.cyl_z(x, y, -15.40, Z_BLOCK_TOP + 0.2, 2.90)]
    for x, z in EBB_CORNERS.values():
        cutters += [a.cyl_y(x, z, Y_SEAT - 0.2, INSERT[0] + 0.05, CLEAR_R),
                    a.cyl_y(x, z, INSERT[0], INSERT[1] + 0.05, INSERT[2])]
        if z > 0:
            cutters.append(a.cyl_y(x, z, INSERT[1], Y_FRONT + 0.2, PRESS_R))
    return single(unify(cut(body, cutters)), "revision-41 P24")


# --------------------------------------------------------------------------------------------
# P02: a snug servo pocket. Released: the MG90D's gear tower sits in P02's 7 mm plate and the top 4.5 mm of its
# body in a recess 12.30 x 23.05 mm. TowerPro gives the body as 12.2 x 22.8 mm, so it could shift 0.1 mm across
# and 0.25 mm along, and the two M2 ear screws took the torque. Revision 41 keeps the same recess, only
# smaller: SERVO_POCKET, centred on the servo, is line to line across and 0.05 mm long at each end. If your
# servo measures differently, change SERVO_POCKET.
# The A1104 hall sensor's leads end 0.4 mm in front of P02, against the solid strip under the motor bore (Y-0.9
# to -6.7), so they had no way through to P24 and the EBB42. P02 gets P24's groove (HALL_GROOVE) through that
# strip, leaving 1.68 mm under it. Nothing else on P02 changes.
# --------------------------------------------------------------------------------------------
SERVO_DATASHEET = (12.2, 22.8)                 # MG90D body: width (X) and length (Z)
SERVO_POCKET = (12.20, 22.90)
SERVO_CENTRE = (10.5, 45.34)                   # centre of the v26 servo envelope (X4.40-16.60, Z33.86-56.82)
SERVO_ENVELOPE = (4.40, 16.60, 33.86, 56.82)   # X and Z of the envelope's body (the MG90S/MG90D STEP)
POCKET = (4.35, 16.65, 33.80, 56.85)           # released pocket, from the plate's rear face (Y-11.2) to Y-6.70
PLATE_REAR, POCKET_FLOOR = -11.20, -6.70


def pocket_box(size, y0=PLATE_REAR - 0.1):
    (cx, cz), (w, length) = SERVO_CENTRE, size
    return a.box(cx - w / 2, cx + w / 2, y0, POCKET_FLOOR, cz - length / 2, cz + length / 2)


def p02():
    body = load("P02_Motor_servo_plate_12p5mm")
    body = fuse(body, a.box(POCKET[0], POCKET[1], PLATE_REAR, POCKET_FLOOR, POCKET[2], POCKET[3]))
    hall = a.box(HALL_GROOVE[0], HALL_GROOVE[1], Y_FRONT - 0.1, -0.4, HALL_GROOVE[2], HALL_GROOVE[3])
    return single(unify(cut(body, [pocket_box(SERVO_POCKET), hall])), "revision-41 P02")


# --------------------------------------------------------------------------------------------
# P01: no tab. Since the v26 original, P01 (the print set's revision-31 back case) has had a block 5.3 x 2.9 x 1.9 mm
# under the boss of its +X front frame screw (X15.35-20.65, Y26.1-29.0, Z-19.25..-17.35), modelled line to line in
# a matching slot in P03, and nothing like it on the -X side. Revision 41 cuts it off at the boss's own bottom
# (Z-17.40); P03's slot stays as it is, an empty pocket inside the case. Nothing else on P01 changes.
# --------------------------------------------------------------------------------------------
P01_TAB = (15.25, 20.75, 26.0, 29.1, -19.35, -17.40)


def p01():
    return single(unify(cut(load(R31_NAMES["p01"]), [shape(a.box(*P01_TAB))])), "revision-41 P01")


# --------------------------------------------------------------------------------------------
# P03 magnet variants. Released: one universal pocket per group (two Ø6.12 disc bores, a 6.2 x 12.2 bar box
# and an epoxy undercut), loose for every magnet, its inner wall only 0.2 mm from P03's 6.4 mm centre slot.
# Revision 41 makes one P03 per magnet, the magnets where the tools' receivers expect them (X+-6.5): each
# pocket is 0.10 mm over the magnet's width or diameter and 0.15 mm over its length, with a Ø1.0 relief at
# each bar's two outer corners. A 6 mm magnet's inner edge is only 0.3 mm from the centre slot, too thin to
# print, so wherever that wall would be under 0.6 mm the pocket opens into the slot instead (the whole inner
# side of a 12 x 6 bar, the middle 2.8 mm of a disc); the 15 x 5 bars keep a 0.75 mm wall. No mouth chamfer:
# it would cut into the centre slot and into the notch above the upper pockets. Each magnet's face stands
# 0.2 mm proud of P03's front face (Y31.50), as the released receiver magnets did.
# --------------------------------------------------------------------------------------------
P03_FACE_Y, MAGNET_PROUD = 31.50, 0.20
BAR_CENTRES = ((-6.5, 26.75), (6.5, 26.75), (-6.5, 1.75), (6.5, 1.75))
DISC_CENTRES = tuple((x, z) for x in (-6.5, 6.5) for z in (30.5, 23.0, 5.5, -2.0))
MAGNET_SPECS = {"15x5x3": ("bar", 5.0, 15.0, 3.0), "12x6x3": ("bar", 6.0, 12.0, 3.0),
                "D6x4": ("disc", 6.0, 6.0, 4.0), "D6x3": ("disc", 6.0, 6.0, 3.0)}
FIT_W, FIT_L, RELIEF_R = 0.10, 0.15, 0.5
CENTRE_SLOT, MIN_WALL = 3.2, 0.6       # |X| of P03's centre slot walls; thinnest wall left beside it


def p03_base():
    meta = json.loads((acc.WORK / "v26_meta.json").read_text())
    for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep")):
        if m["name"] == "PRINT_000_outer_shell_of_extruder_1":
            return shape(s)
    raise KeyError("v26 P03 body")


def magnet(kind):
    """The magnets themselves, seated in their pockets (for fit checks and the review model)."""
    form, w, l, t = MAGNET_SPECS[kind]
    y0 = P03_FACE_Y + MAGNET_PROUD - t
    if form == "bar":
        return [shape(a.box(x - w / 2, x + w / 2, y0, y0 + t, z - l / 2, z + l / 2)) for x, z in BAR_CENTRES]
    return [shape(a.cyl_y(x, z, y0, y0 + t, w / 2)) for x, z in DISC_CENTRES]


def window(x, z, x_inner, half_z, floor, mouth):
    """Open a pocket into P03's centre slot, from inside the slot out to x_inner (|X|), over z +- half_z."""
    s = 1 if x > 0 else -1
    lo, hi = sorted((s * (CENTRE_SLOT - 0.3), s * x_inner))
    return shape(a.box(lo, hi, floor, mouth, z - half_z, z + half_z))


def magnet_pockets(kind):
    form, w, l, t = MAGNET_SPECS[kind]
    floor, mouth = P03_FACE_Y + MAGNET_PROUD - t, P03_FACE_Y + 0.5
    out = []
    if form == "bar":
        hw, hl = (w + FIT_W) / 2, (l + FIT_L) / 2
        for x, z in BAR_CENTRES:
            out.append(shape(a.box(x - hw, x + hw, floor, mouth, z - hl, z + hl)))
            xo = x + (hw if x > 0 else -hw)
            out += [shape(a.cyl_y(xo, z + sz * (hl - RELIEF_R), floor, mouth, RELIEF_R)) for sz in (-1, 1)]
            if abs(x) - hw - CENTRE_SLOT < MIN_WALL:
                out.append(window(x, z, abs(x) - hw + 0.01, hl, floor, mouth))
    else:
        r = (w + FIT_W) / 2
        reach = CENTRE_SLOT + MIN_WALL
        for x, z in DISC_CENTRES:
            out.append(shape(a.cyl_y(x, z, floor, mouth, r)))
            if abs(x) - r < reach:
                out.append(window(x, z, reach, (r * r - (abs(x) - reach) ** 2) ** 0.5, floor, mouth))
    return out


def p03(kind):
    return single(unify(cut(p03_base(), magnet_pockets(kind))), f"revision-41 P03 {kind}")


# --------------------------------------------------------------------------------------------
# Hardware: P24's inserts move forward and its screws grow, and P22's two screws into P01 seat on the cheeks'
# front faces; everything else is revision 40's. Each P24 insert is modelled at its Ø4.0 hole: the OD 4.2 knurl
# melts into the plastic around it.
# --------------------------------------------------------------------------------------------
BUTTON = (2.85, 1.65)                  # ISO 7380 M3 head: radius and height


def p24_hardware():
    hw = []
    for i, key in enumerate(("TR", "TL", "BL", "BR")):
        x, z = EBB_CORNERS[key]
        y_head, length = (-35.80, 18.0) if z > 0 else (-32.25, 14.0)
        hw.append((f"R41_EBB42_M3x{length:.0f}_{key}", fuse(a.cyl_y(x, z, y_head, y_head + length, P37.SHANK_R),
                                                            a.cyl_y(x, z, y_head - 1.6, y_head, 2.75))))
        hw.append((f"R41_EBB42_M3x4_HEATSET_{key}", cut(a.cyl_y(x, z, INSERT[0], INSERT[1], INSERT[2]),
                                                         [a.cyl_y(x, z, INSERT[0] - 0.2, INSERT[1] + 0.2, 1.5)])))
    return hw


def p22_mount_hardware():
    """M3x8 ISO 7380 button heads through P22's cheeks into P01's boss inserts. The cheek's front face leans back
    2.2 degrees, so each head is modelled touching it at its lowest point."""
    hw = []
    for i, x in enumerate(P01_BOSS_X):
        seat = cheek_front_y(P01_BOSS_Z - BUTTON[0])
        hw.append((f"R41_P22_P01_M3x8_BUTTON_{i}", fuse(a.cyl_y(x, P01_BOSS_Z, seat - 8.0, seat, P37.SHANK_R),
                                                         a.cyl_y(x, P01_BOSS_Z, seat, seat + BUTTON[1], BUTTON[0]))))
    return hw


def other_hardware():
    """Revision-40 accessory hardware, with P24's four inserts and screws replaced by p24_hardware() and P22's two
    socket-head screws into P01 by p22_mount_hardware() (P01's inserts stay)."""
    old = ("ACC_EBB42_M3_", "ACC_EBB42_HEATSET_", "ACC_CASE_BOSS_M3x10_")
    return [(n, s) for n, s in P40.other_hardware() if not n.startswith(old)] + p24_hardware() + p22_mount_hardware()
