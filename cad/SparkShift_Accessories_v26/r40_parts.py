"""Revision 40: the P20-to-P21 screws, fixed in place; everything else stays as designed.

Released: the two M3x8 socket heads on P20's lug tops (Z-14.2..-12.6) reach 0.9 mm into the EBB42's bottom
edge (Z-13.5) and its bottom headers, and P21's insert pockets for them (X+-4.5) are 0.28 mm from the
probe-cable raceway (X+-1.95) and 0.57 mm from the socket P20's sleeve slides into. Revision 40 moves both
screws to X+-5.5, 1 mm forward, and seats ISO 7380 button heads 1.6 mm down in P20's lugs. Only the lugs of
P20 and P21 change.

The builders take a column shift (dy) and reproduce the released P20, P21 and the revision-37 P22 at
zero. Revision 40 does not shift the column; dy is only used for the beam-clearance note (DY_STUDY).
"""
import math

import cadquery as cq
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

import build_and_verify_accessories_v26 as acc
import build_p24_cable_entry_r35 as r35
import r37_parts as P37
from build_bambu_clean_r29 import single
from build_carriage_lowered_mounts_r31 import MOUNT_DZ
from build_modular_toolhead import box, load

DY_STUDY = -1.5               # note only: moving the column behind the beam this far rearward
FAIRING_Z_STUDY = -27.0       # note only: P21 fairing underside that clears the beam top with that shift
UPPER_CLAMP = (-18.100, 41.720)    # P24's upper rear hole: core right case-clamp axis (insert Y-6.50..-2.50)
LOWER_CLAMP = (-18.500, -14.450)   # P24's lower rear hole: core right case-clamp axis (insert Y-3.70..+0.30)
NAMES = {
    "p20": "P20_CPAP_Hose_Inlet_Button_Head_Lugs_R40_REVIEW",
    "p21": "P21_CPAP_Gantry_Bridge_Moved_Inserts_R40_REVIEW",
    "hardware": "P20_P21_Screws_And_Inserts_R40_REVIEW",
    "assembly": "40_Carriage_P20_P21_Screws_Complete_REVIEW",
    "review": "40_P20_P21_Screws_REVIEW",
}
a = acc


def shape(s):
    return P37.shape(s)


def unify(s):
    u = ShapeUpgrade_UnifySameDomain(s, True, True, True)
    u.Build()
    return u.Shape()


def corridor(wall, dy):
    return [(x, y + dy) for x, y in a.corridor_aero_vertices(wall)]


# --------------------------------------------------------------------------------------------
# P20: build_p20_inlet; a column shift keeps the wing seats and wing-screw heads on the EBB42
# --------------------------------------------------------------------------------------------

WING_SEAT_Y = -32.26
WING_HEAD_Y = -35.80
WING_X = ((-20.1, -5.9), (5.9, 17.6))
# P20-to-P21 screws. Released: M3x8 socket heads on the lug tops (Z-14.2..-12.6) reached 0.9 mm into the
# EBB42's bottom edge (Z-13.5) and headers; P21's insert pockets at X+-4.5 were 0.28 mm from the cable
# raceway (X+-1.95) and 0.57 mm from the P20 sleeve socket. Revision 40: X+-5.5, 1 mm forward,
# ISO 7380 button heads seated 1.6 mm down in P20's lugs.
LUG_X = 5.50
LUG_Y = -31.20 + 1.0
P20_LUG_R = 3.80
LUG_TOP = -14.20
LUG_HEAD_SEAT = -15.80
LUG_CBORE_R = 3.05
BUTTON_HEAD_R, BUTTON_HEAD_H = 2.85, 1.65
P21_INSERT_R, P21_INSERT_Z = 2.27, (-20.80, -17.80)     # released M3 x 3 mm insert in P21's top flange


def p20_base(dy=0.0, lug_x=4.50, lug_y=-31.20, lug_r=3.60, head_seat=None, head_r=LUG_CBORE_R):
    """build_and_verify_accessories_v26.build_p20_inlet with the column moved by dy.

    The wing seats (Y-32.26), the wing-screw head seats (Y-35.80) and the cable channel's forward exit
    (Y-25) stay put. lug_x/lug_y/lug_r place the P20-to-P21 lugs; head_seat recesses their screw heads.
    p20_base(0.0) is the released part. Returns (body, air)."""
    z_split = -17.780
    z_sleeve_bot = z_split - 3.800
    y_cuff = -48.50 + dy
    r_bore, r_shank, r_barb1, r_barb2, r_tip = 8.20, 10.10, 10.80, 10.85, 9.65
    male_sleeve = a.prism_xy_r(corridor(1.02, dy), 2.5, z_sleeve_bot, z_split + 0.50)
    xy_outer = a.fuse_all([
        a.cyl_z(0.0, y_cuff, z_split, 16.50, r_shank),
        a.prism_xy_r([(-20.60, -33.20 + dy), (-20.60, -38.20 + dy), (-13.00, -45.40 + dy), (-r_shank, y_cuff),
                      (r_shank, y_cuff), (13.00, -45.40 + dy), (20.60, -38.20 + dy), (20.60, -33.20 + dy)],
                     [3.5, 3.5, 8.0, 0.0, 0.0, 8.0, 3.5, 3.5], z_split, 16.50),
    ])
    xz_outer = a.prism_xz_r([(-20.60, z_split), (20.60, z_split), (20.60, -13.50), (r_shank, 11.50),
                             (r_shank, 25.00), (-r_shank, 25.00), (-r_shank, 11.50), (-20.60, -13.50)],
                            [0, 0, 6.0, 6.0, 0, 0, 6.0, 6.0], -65.0 + dy, -30.0 + dy)
    yz_outer = a.prism_yz_r([(-45.40 + dy, z_split), (-33.20 + dy, z_split), (-33.20 + dy, -16.80),
                             (-36.00 + dy, -13.00), (y_cuff + r_shank, 11.50), (y_cuff + r_shank, 25.00),
                             (y_cuff - r_shank - 1.50, 25.00), (y_cuff - r_shank - 1.50, 14.50),
                             (-45.40 + dy, -16.50)],
                            [0, 0, 1.5, 4.0, 6.0, 0, 0, 0.0, 2.5], -25.0, 25.0)
    cone_outer_env = a.fuse_all([
        a.box(-25.0, 25.0, -65.0 + dy, y_cuff, z_split, 20.00),
        a.box(-25.0, 25.0, y_cuff, -30.0 + dy, z_split, 6.50),
        a.cone_z(0.0, y_cuff, 6.50, 14.50, r_shank + 8.00, r_shank),
        a.cyl_z(0.0, y_cuff, 14.50, 16.50, r_shank),
    ])
    outer_loft = a.fuse_all([male_sleeve, a.intersect_all(xy_outer, [xz_outer, yz_outer, cone_outer_env])])
    c_in = corridor(1.84, dy)
    xy_inner = a.fuse_all([
        a.prism_xy_r(c_in, 2.0, z_sleeve_bot - 0.50, z_split + 0.01),
        a.cyl_z(0.0, y_cuff, z_split, 16.50, r_bore),
        a.prism_xy_r([c_in[0], c_in[1], c_in[2], (-r_bore, y_cuff), (r_bore, y_cuff), c_in[3], c_in[4], c_in[5]],
                     [2.0, 2.0, 6.0, 0.0, 0.0, 6.0, 2.0, 2.0], z_split, 16.50),
    ])
    xz_inner = a.prism_xz_r([(-18.76, z_sleeve_bot - 0.50), (18.76, z_sleeve_bot - 0.50), (18.76, -13.50),
                             (r_bore, 11.50), (r_bore, 25.00), (-r_bore, 25.00), (-r_bore, 11.50), (-18.76, -13.50)],
                            [0, 0, 5.0, 5.0, 0, 0, 5.0, 5.0], -65.0 + dy, -30.0 + dy)
    yz_inner = a.prism_yz_r([(-43.56 + dy, z_sleeve_bot - 0.50), (-35.04 + dy, z_sleeve_bot - 0.50),
                             (-35.04 + dy, -16.80), (-37.84 + dy, -13.00), (y_cuff + r_bore, 11.50),
                             (y_cuff + r_bore, 25.00), (y_cuff - r_bore - 1.50, 25.00),
                             (y_cuff - r_bore - 1.50, 14.50), (-43.56 + dy, z_split)],
                            [0, 0, 1.2, 3.5, 5.0, 0, 0, 0.0, 2.0], -25.0, 25.0)
    cone_inner_env = a.fuse_all([
        a.box(-25.0, 25.0, -65.0 + dy, y_cuff, z_sleeve_bot - 1.0, 20.00),
        a.box(-25.0, 25.0, y_cuff, -30.0 + dy, z_sleeve_bot - 1.0, 6.50),
        a.cone_z(0.0, y_cuff, 6.50, 14.50, r_bore + 8.00, r_bore),
        a.cyl_z(0.0, y_cuff, 14.50, 31.00, r_bore),
    ])
    inner_loft = a.fuse_all([a.intersect_all(xy_inner, [xz_inner, yz_inner, cone_inner_env]),
                             a.cyl_z(0.0, y_cuff, 14.50, 31.00, r_bore)])
    spigot_parts = [
        a.cyl_z(0.0, y_cuff, 14.50, 16.50, r_shank),
        a.cone_z(0.0, y_cuff, 16.50, 17.35, r_shank, r_barb2),
        a.cone_z(0.0, y_cuff, 17.35, 21.00, r_barb2, r_shank),
        a.cone_z(0.0, y_cuff, 21.00, 21.85, r_shank, r_barb2),
        a.cone_z(0.0, y_cuff, 21.85, 25.50, r_barb2, r_shank),
        a.cone_z(0.0, y_cuff, 25.50, 26.30, r_shank, r_barb1),
        a.cone_z(0.0, y_cuff, 26.30, 28.00, r_barb1, r_barb1),
        a.cone_z(0.0, y_cuff, 28.00, 30.00, r_barb1, r_tip),
    ]
    lugs = [a.cyl_z(x, lug_y, z_split, LUG_TOP, lug_r) for x in (-lug_x, lug_x)]
    lug_web = a.rounded_box_xy(-(lug_x + lug_r), lug_x + lug_r, -35.50 + dy, lug_y + 0.40, z_split, LUG_TOP, 1.2)
    seat = WING_SEAT_Y
    yz_wing = a.prism_yz_r([(-45.50 + dy, 2.00), (-41.00 + dy, 2.00), (-41.00 + dy, 10.00), (seat, 20.25),
                            (seat, 25.00), (-39.50 + dy, 25.00), (-39.50 + dy, 19.55), (-45.50 + dy, 11.50)],
                           [0, 0, 4.0, 1.5, 0, 0, 4.0, 4.0], -22.0, 22.0)
    wing_tr = a.intersect_all(yz_wing, [
        a.prism_xz_r([(-12.50, 2.00), (-6.00, 2.00), (-6.00, 10.00), (-13.40, 19.55), (-13.40, 25.00),
                      (-20.00, 25.00), (-20.00, 19.55), (-12.50, 10.00)],
                     [0, 0, 4.0, 2.0, 0, 0, 3.0, 4.0], -48.0 + dy, -32.0),
        a.rounded_box_xy(-20.00, -6.00, -46.50 + dy, seat, 2.00, 25.00, 1.5),
    ])
    wing_tl = a.intersect_all(yz_wing, [
        a.prism_xz_r([(6.00, 2.00), (12.50, 2.00), (12.50, 10.00), (17.50, 19.55), (17.50, 25.00),
                      (11.20, 25.00), (11.20, 19.55), (6.00, 10.00)],
                     [0, 0, 4.0, 3.0, 0, 0, 2.0, 4.0], -48.0 + dy, -32.0),
        a.rounded_box_xy(6.00, 17.50, -46.50 + dy, seat, 2.00, 25.00, 1.5),
    ])
    cable_rib_up = a.intersect_all(
        a.prism_xy_r([(-3.65, -31.50 + dy), (-3.65, -38.15 + dy), (3.65, -38.15 + dy), (3.65, -31.50 + dy)], 3.00,
                     z_sleeve_bot - 0.50, 4.50),
        [a.prism_yz_r([(-38.15 + dy, z_sleeve_bot - 0.50), (-31.50 + dy, z_sleeve_bot - 0.50), (-31.50 + dy, 4.50),
                       (-33.20 + dy, 4.50), (-38.15 + dy, -13.80)], [0, 0, 0, 4.0, 6.0], -4.0, 4.0)])
    body = a.fuse_all([outer_loft, *spigot_parts, *lugs, lug_web, wing_tr, wing_tl])
    inner_cavity = a.cut_all(inner_loft, [cable_rib_up])
    cuts = [
        a.box(-50, 50, -100, 50, -50, z_sleeve_bot),
        a.prism_xy_r([(-2.86, -25.00), (-2.86, -37.36 + dy), (2.86, -37.36 + dy), (2.86, -25.00)], 2.45,
                     z_sleeve_bot - 0.5, z_split),
        inner_cavity,
        *[a.cyl_z(x, lug_y, z_split - 1.0, -10.0, 1.65) for x in (-lug_x, lug_x)],
        *[a.cyl_z(x, lug_y, LUG_TOP, 35.0, 2.85) for x in (-lug_x, lug_x)],
        a.cyl_z(0.0, -34.50 + dy, z_sleeve_bot - 1.0, -15.80, 1.95),
        a.cyl_y(0.0, -15.80, -34.50 + dy, -25.00, 1.95),
        a.box(-1.95, 1.95, -34.50 + dy, -25.00, z_split - 0.2, -13.85),
        a.cyl_y(-16.748, 22.000, -42.00 + dy, -32.00, 1.65),
        a.cyl_y(14.252, 22.000, -42.00 + dy, -32.00, 1.65),
        a.cyl_y(-16.748, 22.000, -42.00 + dy, WING_HEAD_Y, 2.85),
        a.cyl_y(14.252, 22.000, -42.00 + dy, WING_HEAD_Y, 2.85),
    ]
    if head_seat is not None:
        cuts += [a.cyl_z(x, lug_y, head_seat, LUG_TOP + 0.01, head_r) for x in (-lug_x, lug_x)]
    body = a.cut_all(body, cuts)
    body = a.intersect_all(body, [a.box(-22.497, 22.497, -100.0, 50.0, z_sleeve_bot, 30.00)])
    air = a.fuse_all([
        a.cut_all(inner_cavity, [a.box(-50, 50, -100, 50, -50, z_split), a.box(-50, 50, -100, 50, 14.5, 50)]),
        a.cyl_z(0.0, y_cuff, 14.50, 30.00, r_bore),
    ])
    return unify(body), air


def p20():
    body, air = p20_base(0.0, LUG_X, LUG_Y, P20_LUG_R, LUG_HEAD_SEAT)
    return single(shape(body), "revision-40 P20"), shape(air)


# --------------------------------------------------------------------------------------------
# P21: build_p21_mid; a column shift keeps the saddle and its P24 bolts in place
# --------------------------------------------------------------------------------------------

def p21_base(dy=0.0, fairing_z=-27.60, lug_x=4.50, lug_y=-31.20):
    """build_and_verify_accessories_v26.build_p21_mid, column moved by dy; lug_x/lug_y place the P20 screw
    lugs and their inserts. (0, -27.60, 4.5, -31.2) is the released part."""
    z_top, z_bot, z_sleeve_bot = -17.780, -49.000, -51.400
    conduit_outer = a.fuse_all([
        a.prism_xy_r(corridor(0.0, dy), 3.5, z_bot, z_top),
        a.prism_xy_r(corridor(1.02, dy), 2.5, z_sleeve_bot, z_bot + 0.50),
    ])
    conduit_inner_loft = a.prism_xy_r(corridor(1.84, dy), 2.0, z_sleeve_bot - 0.50, z_top + 1.00)
    top_socket_recess = a.cut_all(
        a.prism_xy_r(corridor(0.84, dy), 2.7, -21.58, z_top + 0.50),
        [a.prism_xy_r([(-2.80, -25.00), (-2.80, -37.30 + dy), (2.80, -37.30 + dy), (2.80, -25.00)], 2.40,
                      -22.50, z_top + 1.0)],
    )
    cable_boss_excl = a.prism_xy_r([(-3.65, -25.00), (-3.65, -38.15 + dy), (3.65, -38.15 + dy), (3.65, -25.00)],
                                   3.00, z_sleeve_bot - 2.0, z_top + 1.0)
    conduit_inner = a.fuse_all([a.cut_all(conduit_inner_loft, [cable_boss_excl]), top_socket_recess])
    up_lug_l = a.cyl_z(-lug_x, lug_y, -26.50, z_top, 3.6)
    up_lug_r = a.cyl_z(lug_x, lug_y, -26.50, z_top, 3.6)
    up_lug_web = a.box(-lug_x, lug_x, -35.50 + dy, lug_y, -26.50, z_top)
    up_fairing = a.intersect_all(
        a.rounded_box_xy(-9.20, 9.20, -35.50 + dy, -12.10, -27.60, -18.40, 2.2),
        [a.prism_yz_r([
            (-35.50 + dy, fairing_z), (-33.20 + dy, fairing_z), (-25.00, -24.80),
            (-12.10, -22.50), (-12.10, -18.40), (-35.50 + dy, -18.40),
        ], [0, 2.0, 4.0, 1.5, 0, 0], -10.0, 10.0)]
    )
    up_bridge_verts = [
        (-9.20, -34.50 + dy), (-9.20, -12.10), (-21.00, -9.70), (-21.00, 0.30),
        (21.00, 0.30), (21.00, -9.70), (9.20, -12.10), (9.20, -34.50 + dy),
    ]
    up_saddle = a.prism_xy_r(up_bridge_verts, 2.2, -24.10, -18.40)
    body = a.fuse_all([conduit_outer, up_lug_l, up_lug_r, up_lug_web, up_fairing, up_saddle])
    cutters = [
        conduit_inner,
        a.box(-50, 50, -100, 50, -70.0, z_sleeve_bot),
        a.prism_xy_r([(-2.86, -25.00), (-2.86, -37.36 + dy), (2.86, -37.36 + dy), (2.86, -25.00)], 2.45,
                     z_sleeve_bot - 0.5, z_bot),
        a.cyl_z(-lug_x, lug_y, -21.30, z_top + 0.5, P21_INSERT_R),
        a.cyl_z(lug_x, lug_y, -21.30, z_top + 0.5, P21_INSERT_R),
        a.cyl_z(-lug_x, lug_y, -27.00, -21.20, 1.65),
        a.cyl_z(lug_x, lug_y, -27.00, -21.20, 1.65),
        a.cyl_z(-6.00, -15.80, -22.40, -18.00, 2.27),
        a.cyl_z(6.00, -15.80, -22.40, -18.00, 2.27),
        a.cyl_z(-6.00, -15.80, -25.00, -22.00, 1.65),
        a.cyl_z(6.00, -15.80, -25.00, -22.00, 1.65),
        a.cyl_z(0.0, -34.50 + dy, z_sleeve_bot - 1.0, z_top + 1.0, 1.95),
        a.box(-1.95, 1.95, -34.50 + dy, -30.00, z_sleeve_bot - 1.0, z_top + 1.0),
    ]
    body = a.cut_all(body, cutters)
    body = a.intersect_all(body, [a.box(-22.497, 22.497, -50.0, 25.0, z_sleeve_bot, z_top)])
    air = a.cut_all(
        conduit_inner_loft,
        [
            a.prism_xy_r([(-3.65, -25.00), (-3.65, -38.15 + dy), (3.65, -38.15 + dy), (3.65, -25.00)], 3.10,
                         z_sleeve_bot - 1.0, z_top + 1.0),
            a.box(-50, 50, -100, 50, -70.0, z_bot),
            a.box(-50, 50, -100, 50, z_top, 0.0),
        ],
    )
    return unify(body), air, conduit_inner


def p21():
    body, air, _ = p21_base(0.0, -27.60, LUG_X, LUG_Y)
    return single(shape(body), "revision-40 P21"), shape(air)


# --------------------------------------------------------------------------------------------
# P22: build_p22_lower_plenum (revision-31 mounts, revision-37 probe spigots); a column shift moves
# the collar, riser, elbow and centre island and inserts straight plenum ahead of them (note only)
# --------------------------------------------------------------------------------------------

def p22_base(dy=0.0):
    """build_p22_lower_plenum(MOUNT_DZ, R37 mounts) with the rear collar and riser moved by dy (0: revision 37)."""
    mount_dz, probe_mounts, spigot_z, insert_z = MOUNT_DZ, P37.P22_MOUNTS, P37.SPIGOT_Z, P37.INSERT_HOLE_Z
    z_top = -49.000
    socket_recess = a.cut_all(
        a.prism_xy_r(corridor(0.84, dy), 2.7, -51.40, z_top + 0.50),
        [a.prism_xy_r([(-2.80, -25.00), (-2.80, -37.30 + dy), (2.80, -37.30 + dy), (2.80, -25.00)], 2.40,
                      -52.00, z_top + 1.0)],
    )
    horn_yz_out = a.prism_yz_r([
        (-45.40 + dy, -70.80), (-45.40 + dy, z_top),
        (-33.20 + dy, z_top), (-33.20 + dy, -49.50),
        (-20.736 + dy, -57.36), (0.00, -57.36),
        (9.80, -57.36), (16.80, -61.20),
        (23.50, -68.80), (29.60, -72.20),
        (29.60, -77.85), (19.00, -77.85),
        (11.55, -70.80),
    ], [16.0, 0, 0, 0, 50.0, 0, 16.0, 16.0, 12.0, 1.2, 0.8, 7.5, 7.5], -23.0, 23.0)
    horn_yz_in = a.prism_yz_r([
        (-43.56 + dy, -68.90), (-43.56 + dy, z_top + 0.50),
        (-35.04 + dy, z_top + 0.50), (-35.04 + dy, -51.40),
        (-21.413 + dy, -58.60), (0.00, -58.60),
        (9.20, -58.60), (16.00, -62.40),
        (22.80, -70.10), (28.20, -73.40),
        (28.20, -76.65), (19.60, -76.65),
        (12.20, -68.90),
    ], [14.8, 0, 0, 0, 61.0, 0, 14.5, 14.5, 10.5, 0.8, 0.5, 6.5, 6.5], -22.5, 22.5)
    xy_outer_full = a.prism_xy_r([
        (-13.00, -45.40 + dy), (-20.60, -38.20 + dy), (-20.60, -25.30 + dy),
        (-22.42, -19.50 + dy), (-22.42, 15.00), (-20.40, 22.50),
        (-14.80, 28.40), (-8.50, 29.60), (-8.50, 11.20),
        (8.50, 11.20), (8.50, 29.60), (14.80, 28.40),
        (20.40, 22.50), (22.42, 15.00), (22.42, -19.50 + dy),
        (20.60, -25.30 + dy), (20.60, -38.20 + dy), (13.00, -45.40 + dy),
    ], [3.5, 3.5, 16.0, 16.0, 12.0, 10.0, 4.0, 0.8, 0.0, 0.0, 0.8, 4.0, 10.0, 12.0, 16.0, 16.0, 3.5, 3.5],
        -78.00, z_top)
    xy_inner_full = a.prism_xy_r([
        (-12.16, -43.56 + dy), (-18.76, -37.36 + dy), (-18.76, -26.50 + dy),
        (-21.02, -19.50 + dy), (-21.02, 14.80), (-19.00, 22.00),
        (-13.80, 27.20), (-8.50, 28.20), (8.50, 28.20),
        (13.80, 27.20), (19.00, 22.00), (21.02, 14.80),
        (21.02, -19.50 + dy), (18.76, -26.50 + dy), (18.76, -37.36 + dy),
        (12.16, -43.56 + dy),
    ], [2.0, 2.0, 14.0, 14.0, 10.6, 8.6, 3.0, 0.0, 0.0, 3.0, 8.6, 10.6, 14.0, 14.0, 2.0, 2.0], -77.50, z_top + 0.50)
    cable_boss_nose = a.prism_xy_r([(-3.65, -20.00 + dy), (-3.65, -38.15 + dy), (3.65, -38.15 + dy), (3.65, -20.00 + dy)],
                                   3.00, -78.00, z_top + 1.00)
    center_island_body = a.prism_xy_r([
        (-3.65, -36.50 + dy), (-3.65, -31.00 + dy), (-12.85, -16.50 + dy),
        (-12.85, 13.50), (-11.60, 17.50), (-11.60, 30.00),
        (11.60, 30.00), (11.60, 17.50), (12.85, 13.50),
        (12.85, -16.50 + dy), (3.65, -31.00 + dy), (3.65, -36.50 + dy),
    ], [0.0, 14.0, 14.0, 4.0, 4.0, 0.0, 0.0, 4.0, 4.0, 14.0, 14.0, 0.0], -78.00, z_top + 1.00)
    center_island_excl = a.fuse_all([cable_boss_nose, center_island_body])
    center_valley_upper = a.prism_xy_r([
        (-2.25, -33.20 + dy), (-2.25, -30.50 + dy), (-11.45, -16.00 + dy),
        (-11.45, -5.40), (11.45, -5.40), (11.45, -16.00 + dy),
        (2.25, -30.50 + dy), (2.25, -33.20 + dy),
    ], [0.0, 12.6, 12.6, 0.0, 0.0, 12.6, 12.6, 0.0], -58.60, z_top + 1.00)
    center_valley_lower = a.prism_xy_r([
        (-2.25, -29.50 + dy), (-11.45, -15.50 + dy), (-11.45, -5.40),
        (11.45, -5.40), (11.45, -15.50 + dy), (2.25, -29.50 + dy),
    ], [4.0, 12.6, 0.0, 0.0, 12.6, 4.0], -78.00, -58.00)
    cheeks = []
    for sign in (-1, 1):
        cheek_pts = [(sign * 13.95, 11.48), (sign * 22.42, 11.48), (sign * 22.42, 20.50), (sign * 13.95, 20.50)]
        cheek_rads = [1.5, 0.0, 0.0, 1.5]
        if sign < 0:
            cheek_pts, cheek_rads = cheek_pts[::-1], cheek_rads[::-1]
        cheek = a.intersect_all(
            a.prism_xy_r(cheek_pts, cheek_rads, -66.00, -48.00),
            [xy_outer_full,
             a.prism_yz_r([(11.48, -66.00), (20.50, -66.00), (19.80, -48.00), (11.48, -48.00)], [0, 1.0, 1.0, 0],
                          -23.0, 23.0)])
        if mount_dz:
            cheek = a.intersect_all(cheek, [a.box(-23.0, 23.0, 11.0, 21.0, -66.5, z_top + mount_dz)])
        cheeks.append(cheek)
    probe_spigots = [a.cyl_z(x, y, *spigot_z, 3.05) for x, y in probe_mounts]
    body = a.cut_all(a.fuse_all([a.intersect_all(xy_outer_full, [horn_yz_out]), *cheeks, *probe_spigots]),
                     [center_valley_upper, center_valley_lower])
    xy_air_combined = a.cut_all(xy_inner_full, [center_island_excl])
    hood_slots = []
    for sign in (-1, 1):
        slot_xy = a.rounded_box_xy(sign * 8.00, sign * 15.50, 16.50, 28.20, -76.65, -71.50, 1.2)
        pts_louver = [(sign * 8.00, -76.65), (sign * 15.50, -76.65), (sign * 15.50, -71.50), (sign * 10.20, -74.85),
                      (sign * 8.00, -74.85)]
        if sign < 0:
            pts_louver = pts_louver[::-1]
        slot_xz = a.prism_xz_r(pts_louver, [0.0, 0.0, 0.6, 0.6, 0.0], 16.00, 28.50)
        hood_slots.append(a.intersect_all(slot_xy, [slot_xz, horn_yz_in, xy_inner_full]))
    air = a.fuse_all([a.intersect_all(xy_air_combined, [horn_yz_in]), *hood_slots])
    r_off_upper = 3.20
    nozzle_slot = a.fuse_all([
        a.rounded_box_xy(-7.00 - r_off_upper, 7.00 + r_off_upper, 12.95 - r_off_upper, 42.00, -74.35, -50.00,
                         r_off_upper),
        a.rounded_box_xy(-11.65, 11.65, 8.30, 16.50, -79.00, -50.00, 4.65),
        a.rounded_box_xy(-8.50, 8.50, 11.50, 42.00, -79.00, -74.35, 2.0),
        a.cyl_y(-7.00, -74.35, 12.95, 42.00, r_off_upper),
        a.cyl_y(7.00, -74.35, 12.95, 42.00, r_off_upper),
    ])
    cutters = [
        air, nozzle_slot, socket_recess,
        a.box(-19.50, 19.50, -15.00, 11.56, -77.00, -70.80),
        a.box(-19.50, 19.50, -15.00, 11.75, -77.00, -74.98),
        a.cyl_z(0.0, -34.50 + dy, -58.60, z_top + 1.0, 1.95),
        a.box(-1.95, 1.95, -34.50 + dy, -30.00 + dy, -58.60, z_top + 1.0),
        a.box(-1.95, 1.95, -34.50 + dy, -25.00 + dy, -58.60, -53.20),
        a.cyl_y(18.0, -52.78 + mount_dz, 11.0, 15.95, 4.02),
        a.cyl_y(-18.0, -52.78 + mount_dz, 11.0, 15.95, 4.02),
        a.cyl_y(18.0, -52.78 + mount_dz, 15.5, 21.0, 1.65),
        a.cyl_y(-18.0, -52.78 + mount_dz, 15.5, 21.0, 1.65),
        a.cyl_y(18.0, -52.78 + mount_dz, 18.2, 21.0, 3.00),
        a.cyl_y(-18.0, -52.78 + mount_dz, 18.2, 21.0, 3.00),
        *[a.cyl_z(x, y, *insert_z, 2.27) for x, y in probe_mounts],
    ]
    body = a.cut_all(body, cutters)
    body = a.intersect_all(body, [a.box(-22.497, 22.497, -50.0, 36.0, -78.20, -47.50)])
    return unify(body), a.cut_all(air, [nozzle_slot]), socket_recess


# --------------------------------------------------------------------------------------------
# Probe cable and hardware
# --------------------------------------------------------------------------------------------

def cable_route(y_back):
    """build_p24_cable_entry_r35.cable_route with its riser line at y_back."""
    r, c = 5.0, 5.0 * math.cos(math.pi / 4)
    y_front, z_under = -12.90, -55.20
    s = math.sin(math.pi / 4)
    z_run, y_up, r_up, z_end = r35.Z_RUN, r35.Y_UP, r35.R_UP, r35.Z_TOP
    return r35.pipe([
        (0, y_front, -66.50), (0, y_front, z_under - r),
        ((0, y_front - r + c, z_under - r + c), (0, y_front - r, z_under)),
        (0, y_back + r, z_under),
        ((0, y_back + r - c, z_under + r - c), (0, y_back, z_under + r)),
        (0, y_back, z_run - r),
        ((0, y_back + r - c, z_run - r + c), (0, y_back + r, z_run)),
        (0, y_up, z_run),
        ((0, y_up + r_up * s, z_run + r_up - r_up * s), (0, y_up + r_up, z_run + r_up)),
        (0, y_up + r_up, z_end),
    ])


def cable(dy=0.0):
    """Revision-37 cable (raised probe) with its riser on the moved raceway."""
    route = cable_route(r35.Y_BACK + dy)
    return single(route.intersect(box(-30, 30, -60, 10, -66.5 + P37.DZ, 40)).clean(), "revision-40 cable")


def insert(x, y, z0, z1, r_out=2.25, r_in=1.5):
    outer = cq.Solid.makeCylinder(r_out, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))
    return outer.cut(cq.Solid.makeCylinder(r_in, z1 - z0 + 0.2, cq.Vector(x, y, z0 - 0.1), cq.Vector(0, 0, 1)))


def inlet_hardware():
    """P20 to P21: 2x M3x8 ISO 7380 button heads seated in P20's lug counterbores (head top 0.6 mm under
    the EBB42) into 2x M3 x 3 mm (OD 4.5) heat-set inserts in P21's top flange."""
    out = []
    for i, x in enumerate((-LUG_X, LUG_X)):
        head = cq.Solid.makeCylinder(BUTTON_HEAD_R, BUTTON_HEAD_H, cq.Vector(x, LUG_Y, LUG_HEAD_SEAT), cq.Vector(0, 0, 1))
        shank = cq.Solid.makeCylinder(P37.SHANK_R, 8.0, cq.Vector(x, LUG_Y, LUG_HEAD_SEAT - 8.0), cq.Vector(0, 0, 1))
        out.append((f"R40_INLET_M3x8_BUTTON_{i}", head.fuse(shank).clean()))
        out.append((f"R40_INLET_M3x3_HEATSET_{i}", insert(x, LUG_Y, *P21_INSERT_Z)))
    return out


def other_hardware():
    """Revision-37 accessory hardware with the P20-to-P21 screws and inserts replaced by inlet_hardware()."""
    return [(n, s) for n, s in P37.other_hardware() if not n.startswith("ACC_UPPER_INLET")] + inlet_hardware()