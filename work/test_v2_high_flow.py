import sys, json, math, time
from pathlib import Path
sys.path.append(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\CAD\SparkShift_Accessories_v26")
import build_and_verify_accessories_v26 as bva
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Ax2, gp_Vec, gp_Trsf
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone, BRepPrimAPI_MakePrism, BRepPrimAPI_MakeSphere
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCP.GC import GC_MakeSegment, GC_MakeArcOfCircle
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

WORK = Path(__file__).resolve().parent
SENSOR_DIR = Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files\compact_direct_cam\accessory_sources")

box = bva.box
cyl_z = bva.cyl_z
cyl_y = bva.cyl_y
fuse_all = bva.fuse_all
cut_all = bva.cut_all
intersect_all = bva.intersect_all
common_vol = bva.common_vol
rounded_polygon_wire_xy = bva.rounded_polygon_wire_xy
prism_xy_rounded = bva.prism_xy_rounded
rounded_box_xy = bva.rounded_box_xy
corridor_aero_vertices = bva.corridor_aero_vertices
circumscribed_hex_circle_vertices = bva.circumscribed_hex_circle_vertices
make_loft = bva.make_loft
make_loft_along_y = bva.make_loft_along_y


def build_p20_inlet_v2():
    z_split = -17.780
    v_bot_out = corridor_aero_vertices(0.0)
    v_top_out = circumscribed_hex_circle_vertices(0.0, -45.50, 12.48)
    v_bot_in  = corridor_aero_vertices(1.2)
    v_top_in  = circumscribed_hex_circle_vertices(0.0, -45.50, 11.00)

    wires_out = [rounded_polygon_wire_xy(v_bot_out, 3.5, z_split)]
    wires_in  = [rounded_polygon_wire_xy(v_bot_in,  2.5, z_split - 0.5)]
    n_steps = 10
    for i in range(n_steps + 1):
        t = i / n_steps
        s = 0.5 * (1.0 - math.cos(math.pi * t))
        z_o = -15.50 + t * (12.50 - (-15.50))
        z_i = -15.50 + t * (13.00 - (-15.50))
        vo = [(a[0] + s * (b[0] - a[0]), a[1] + s * (b[1] - a[1])) for a, b in zip(v_bot_out, v_top_out)]
        vi = [(a[0] + s * (b[0] - a[0]), a[1] + s * (b[1] - a[1])) for a, b in zip(v_bot_in,  v_top_in)]
        ro = 3.5 + s * (11.5 - 3.5)
        ri = 2.5 + s * (10.2 - 2.5)
        wires_out.append(rounded_polygon_wire_xy(vo, ro, z_o))
        wires_in.append(rounded_polygon_wire_xy(vi, ri, z_i))

    outer_loft = make_loft(wires_out, ruled=True)
    inner_loft = make_loft(wires_in, ruled=True)

    spigot_base = cyl_z(0.0, -45.50, 11.50, 28.00, 12.50)
    spigot_bead = BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0.0, -45.50, 26.50), gp_Dir(0, 0, 1)), 12.50, 13.00, 1.50).Shape()
    spigot_tip  = BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0.0, -45.50, 28.00), gp_Dir(0, 0, 1)), 13.00, 12.30, 2.00).Shape()
    spigot_bore = cyl_z(0.0, -45.50, 11.00, 31.00, 11.00)

    lug_l = cyl_z(-5.0, -30.5, z_split, -14.20, 3.8)
    lug_r = cyl_z( 5.0, -30.5, z_split, -14.20, 3.8)
    lug_web = rounded_box_xy(-8.8, 8.8, -35.5, -30.5, z_split, -14.20, 1.2)

    body = fuse_all([outer_loft, spigot_base, spigot_bead, spigot_tip, lug_l, lug_r, lug_web])
    body = cut_all(body, [
        box(-50, 50, -100, 50, -50, z_split),
        inner_loft,
        spigot_bore,
        cyl_z(-5.0, -30.5, z_split - 1.0, -10.0, 1.65),
        cyl_z( 5.0, -30.5, z_split - 1.0, -10.0, 1.65),
        cyl_z(-5.0, -30.5, -14.20, 35.0, 3.10),
        cyl_z( 5.0, -30.5, -14.20, 35.0, 3.10),
    ])
    body = intersect_all(body, [box(-22.497, 22.497, -100.0, 50.0, z_split, 30.00)])
    air = fuse_all([
        cut_all(inner_loft, [box(-50, 50, -100, 50, -50, z_split), box(-50, 50, -100, 50, 12.0, 50)]),
        cyl_z(0.0, -45.50, 11.50, 30.00, 11.00),
    ])
    return body, air


def build_p21_mid_v2():
    """
    Vertical gantry conduit (Z = -58.00 to -17.78 mm) with upper MGN12H saddle,
    lower rear mounting lugs at Z = -58.00 mm, and an integrated rear-left cable
    guide boss/channel behind the X-beam so P22 gets 100% of the Z <= -58.00 mm envelope!
    """
    z_top = -17.780
    z_bot = -58.000
    conduit_outer = prism_xy_rounded(corridor_aero_vertices(0.0), 3.5, z_bot, z_top)
    conduit_inner = prism_xy_rounded(corridor_aero_vertices(1.2), 2.5, z_bot - 1.0, z_top + 1.0)

    # Upper bridge & MGN12H top saddle:
    up_lug_l = cyl_z(-5.0, -30.5, -24.20, z_top, 3.8)
    up_lug_r = cyl_z( 5.0, -30.5, -24.20, z_top, 3.8)
    up_bridge_verts = [
        (-9.20, -34.50), (-9.20, -12.10), (-21.00, -9.70), (-21.00, 0.30),
        ( 21.00,  0.30), ( 21.00, -9.70), (  9.20, -12.10), (  9.20, -34.50),
    ]
    up_saddle = prism_xy_rounded(up_bridge_verts, 1.8, -24.20, -18.40)

    # Lower mounting lugs at (X = ±7.20, Y = -30.50, Z = -58.00..-51.00) inside |X| < 10.00 (clearing GANTRY_Body1/2):
    lo_lug_l = cyl_z(-6.20, -30.50, z_bot, -51.00, 3.60)
    lo_lug_r = cyl_z( 6.20, -30.50, z_bot, -51.00, 3.60)
    lo_web   = rounded_box_xy(-9.80, 9.80, -35.00, -29.00, z_bot, -51.00, 1.2)

    body = fuse_all([conduit_outer, up_lug_l, up_lug_r, up_saddle, lo_lug_l, lo_lug_r, lo_web])

    cutters = [
        conduit_inner,
        # Upper M3x3x4.6 heat-set pockets & M3 clearances at (±5.0, -30.5, z_top):
        cyl_z(-5.0, -30.5, -21.30, z_top + 0.5, 2.27),
        cyl_z( 5.0, -30.5, -21.30, z_top + 0.5, 2.27),
        cyl_z(-5.0, -30.5, -25.00, -21.20, 1.65),
        cyl_z( 5.0, -30.5, -25.00, -21.20, 1.65),
        # Lower M3x4x4.6 heat-set pockets at (±6.20, -30.50, z_bot):
        cyl_z(-6.20, -30.50, z_bot - 0.5, z_bot + 4.20, 2.27),
        cyl_z( 6.20, -30.50, z_bot - 0.5, z_bot + 4.20, 2.27),
        cyl_z(-6.20, -30.50, z_bot + 4.00, -50.50, 1.65),
        cyl_z( 6.20, -30.50, z_bot + 4.00, -50.50, 1.65),
        # Integrated sensor cable routing groove along front-center (X = 0.0, Y = -32.80, r = 2.00) from Z = -58 to -17.78:
        cyl_z( 0.00, -32.80, z_bot - 1.0, z_top + 1.0, 2.10),
    ]
    body = cut_all(body, cutters)
    body = intersect_all(body, [box(-22.497, 22.497, -50.0, 25.0, z_bot, z_top)])
    return body, prism_xy_rounded(corridor_aero_vertices(1.2), 2.5, z_bot, z_top)


def build_p22_lower_plenum_v2():
    """
    Maximum-Volume, Zero-Bottleneck Lower CPAP Plenum:
    - Uses the FULL vertical height Z = -70.80 to -58.00 mm (12.80 mm outer, 10.40 mm inner height - 2.45x taller!)
    - Undivided full-width rear sweeping elbow (Y = -45.40 to -25.60 mm, 333.8 mm2)
    - Smoothly bifurcates around GANTRY_Body40 (X = [-4, 4], Y = [-25.2, -17.2]) with 306+ mm2 combined area
    - Full-height side plenums (214 mm2 combined area, 2.73x larger than before)
    - Full-depth sweeping front horn turn (Y = 11.50 to 24.50 mm, 223 mm2 combined area, 4.66x larger than before!)
    - Integrated upper front cheeks (Z = -58.00..-48.60 mm) bolting directly to P01 front bosses (±18.0, -52.78)
    - Integrated MGN12H lower center cradle (Z = -58.00..-51.35 mm) and rear P21 bolting lugs (±6.20, -30.50)
    """
    z_top = -58.000
    z_bot = -70.800

    # 1. Rear undivided sweeping elbow (Z = -70.80 to -58.00, Y = -45.40 to -25.60):
    # At Z = -58.00, matches P21's corridor_aero_vertices(0.0) on the rear and extends forward to Y = -25.60
    def rear_plen_verts(wall=0.0, dy_rear=0.0, y_front=-25.60):
        xf = 20.60 - wall
        xr = 13.00 - 0.45 * wall
        yf = y_front - wall
        ym = -38.20 + 0.40 * wall + 0.30 * dy_rear
        yr = -45.40 + wall + dy_rear
        return [
            (-xf, yf),
            (-xf, ym),
            (-xr, yr),
            ( xr, yr),
            ( xf, ym),
            ( xf, yf),
        ]

    elbow_out_wires = [
        rounded_polygon_wire_xy(rear_plen_verts(0.0, 7.5, -25.60), 2.8, -70.80),
        rounded_polygon_wire_xy(rear_plen_verts(0.0, 4.8, -25.60), 3.0, -68.50),
        rounded_polygon_wire_xy(rear_plen_verts(0.0, 2.4, -25.60), 3.2, -65.50),
        rounded_polygon_wire_xy(rear_plen_verts(0.0, 0.7, -25.60), 3.4, -62.00),
        rounded_polygon_wire_xy(rear_plen_verts(0.0, 0.0, -25.60), 3.5, -59.50),
        rounded_polygon_wire_xy(rear_plen_verts(0.0, 0.0, -25.60), 3.5,  z_top),
    ]
    collar_outer = make_loft(elbow_out_wires, ruled=True)

    # For the inner air cavity of the rear elbow:
    # At Z = z_top (-58.00), the opening must match P21's inner conduit (corridor_aero_vertices(1.2), Y_front = -34.40),
    # while below Z = -59.20 (under the 1.2 mm roof), it sweeps forward to Y_front = -25.00 to feed the side plenums!
    elbow_in_wires = [
        rounded_polygon_wire_xy(rear_plen_verts(1.2, 7.2, -24.50), 1.8, -69.60),
        rounded_polygon_wire_xy(rear_plen_verts(1.2, 4.6, -24.50), 2.0, -67.50),
        rounded_polygon_wire_xy(rear_plen_verts(1.2, 2.2, -24.50), 2.2, -64.80),
        rounded_polygon_wire_xy(rear_plen_verts(1.2, 0.6, -24.50), 2.4, -61.80),
        rounded_polygon_wire_xy(rear_plen_verts(1.2, 0.0, -24.50), 2.5, -59.20),
    ]
    collar_inner_low = make_loft(elbow_in_wires, ruled=True)
    # Plus vertical entry port from Z = -59.50 to z_top + 0.5 matching P21's exact inner profile:
    collar_inner_port = prism_xy_rounded(corridor_aero_vertices(1.2), 2.5, -59.50, z_top + 0.50)

    ducts_outer = []
    ducts_inner = []
    for sign in (-1, 1):
        # Continuous 8-station S-bend sweep along +Y from rear elbow (Y=-34.0) to front horn (Y=+24.2):
        # Notice Z spans the FULL height Z = -70.80 to -58.00 (outer) and Z = -69.60 to -59.20 (inner)!
        y_stations_out = [
            (-34.00,  5.00, 20.55, -70.80, -58.00, 1.8),
            (-25.50,  5.00, 21.80, -70.80, -58.00, 1.8),
            (-17.00,  5.20, 22.45, -70.80, -58.00, 1.8),
            (-11.50,  7.40, 22.45, -70.80, -58.00, 1.8),
            ( -6.50,  9.65, 22.45, -70.80, -58.00, 1.8),
            ( 12.00,  9.85, 22.45, -70.80, -58.00, 1.8),
            ( 18.50, 10.65, 22.45, -70.80, -58.50, 1.8),
            ( 23.80, 10.85, 22.35, -70.80, -61.50, 1.6),
        ]
        y_stations_in = [
            (-34.50,  6.20, 19.35, -69.60, -59.20, 1.0),
            (-25.50,  6.20, 20.60, -69.60, -59.20, 1.0),
            (-17.00,  6.40, 21.25, -69.60, -59.20, 1.0),
            (-11.50,  8.60, 21.25, -69.60, -59.20, 1.0),
            ( -6.50, 10.85, 21.25, -69.60, -59.20, 1.0),
            ( 12.00, 11.05, 21.25, -69.60, -59.20, 1.0),
            ( 18.50, 11.85, 21.25, -69.60, -59.70, 1.0),
            ( 22.80, 12.05, 21.15, -69.60, -62.50, 0.9),
        ]
        st_o = [
            (y, [(xi, zb), (xo, zb), (xo, zt), (xi, zt)] if sign > 0 else [(-xo, zb), (-xi, zb), (-xi, zt), (-xo, zt)], r)
            for y, xi, xo, zb, zt, r in y_stations_out
        ]
        st_i = [
            (y, [(xi, zb), (xo, zb), (xo, zt), (xi, zt)] if sign > 0 else [(-xo, zb), (-xi, zb), (-xi, zt), (-xo, zt)], r)
            for y, xi, xo, zb, zt, r in y_stations_in
        ]
        ducts_outer.append(make_loft_along_y(st_o, ruled=True))
        ducts_inner.append(make_loft_along_y(st_i, ruled=True))

        # Full-depth (Y = 11.50..24.50 mm) downward & inward converging nozzle horn:
        w_drop = [
            rounded_polygon_wire_xy([(sign * 10.65, 11.50), (sign * 22.45, 11.50), (sign * 22.45, 23.80), (sign * 10.65, 23.80)], 1.6, -61.50),
            rounded_polygon_wire_xy([(sign * 10.65, 12.20), (sign * 22.40, 12.20), (sign * 22.40, 24.20), (sign * 10.65, 24.20)], 1.5, -65.00),
            rounded_polygon_wire_xy([(sign * 10.40, 13.50), (sign * 22.10, 13.40), (sign * 22.10, 24.50), (sign * 10.40, 24.30)], 1.4, -69.20),
            rounded_polygon_wire_xy([(sign *  9.10, 15.60), (sign * 20.90, 15.20), (sign * 20.90, 24.50), (sign *  9.10, 24.00)], 1.2, -73.00),
            rounded_polygon_wire_xy([(sign *  7.30, 17.20), (sign * 19.50, 16.40), (sign * 19.50, 24.50), (sign *  7.30, 23.60)], 1.0, -75.80),
        ]
        ducts_outer.append(make_loft(w_drop, ruled=True))

        wi_drop = [
            rounded_polygon_wire_xy([(sign * 11.85, 12.50), (sign * 21.25, 12.50), (sign * 21.25, 22.80), (sign * 11.85, 22.80)], 1.0, -61.00),
            rounded_polygon_wire_xy([(sign * 11.85, 13.20), (sign * 21.20, 13.20), (sign * 21.20, 23.20), (sign * 11.85, 23.20)], 0.9, -65.00),
            rounded_polygon_wire_xy([(sign * 11.60, 14.50), (sign * 20.90, 14.40), (sign * 20.90, 23.50), (sign * 11.60, 23.30)], 0.8, -69.20),
            rounded_polygon_wire_xy([(sign * 10.10, 16.50), (sign * 19.70, 16.10), (sign * 19.70, 23.50), (sign * 10.10, 23.00)], 0.7, -72.80),
            rounded_polygon_wire_xy([(sign *  6.80, 18.20), (sign * 18.20, 17.40), (sign * 18.20, 23.50), (sign *  6.80, 22.60)], 0.5, -74.60),
        ]
        ducts_inner.append(make_loft(wi_drop, ruled=True))

        # Nozzle exit opening aimed inward at the Volcano nozzle tip (X=0, Y=22.7, Z=-78.88):
        jet_cut = box(sign * 5.8, sign * 14.2, 17.8, 23.6, -74.70, -73.40)
        ducts_inner.append(jet_cut)

        # Integrated upper front mounting cheeks bolting to P01 front bosses at (±18.0, Z=-52.78, Y=11.48..19.60):
        x_in_k, x_out_k = (13.95, 22.45) if sign > 0 else (-22.45, -13.95)
        ducts_outer.append(rounded_box_xy(x_in_k, x_out_k, 11.48, 19.60, -59.50, -48.60, 0.8))

    # MGN12H lower center index pad (strictly |X| <= 9.80 so it clears GANTRY_Body1/2 at |X| >= 10.00):
    cart_cradle = rounded_box_xy(-9.80, 9.80, -9.70, 0.30, -59.50, -51.35, 1.0)
    # Front lower tie bar under P01 (Z = -70.80..-67.00, Y = 0.00..3.50):
    front_tie = rounded_box_xy(-12.00, 12.00, -1.50, 2.50, -70.80, -67.50, 0.8)

    body = fuse_all([collar_outer, *ducts_outer, cart_cradle, front_tie])
    air = fuse_all([collar_inner_low, collar_inner_port, *ducts_inner])
    # Keep solid wall around GANTRY_Body40 (X=[-4.0, 4.0], Y=[-25.2, -17.2]) and rear P21 bolt bosses (±6.20, -30.50):
    air_excl = fuse_all([
        box(-6.20, 6.20, -26.80, -15.80, -75.00, -57.00),
        cyl_z(-6.20, -30.50, -64.50, -57.00, 3.60),
        cyl_z( 6.20, -30.50, -64.50, -57.00, 3.60),
        # Also keep 1.5mm wall around P23 mounting bosses at (±15.80, 8.50) and (±15.80, -11.50) from Z=-70.80 to -66.50:
        cyl_z( 15.80,   8.50, -71.00, -66.50, 3.60),
        cyl_z(-15.80,   8.50, -71.00, -66.50, 3.60),
        cyl_z( 15.80, -11.50, -71.00, -66.50, 3.60),
        cyl_z(-15.80, -11.50, -71.00, -66.50, 3.60),
    ])
    air = cut_all(air, [air_excl])

    cutters = [
        air,
        # Clearance slot for GANTRY_Body40 (X=[-4.0, 4.0], Y=[-25.2, -17.2], Z=[-357.78, -57.78]):
        box(-5.00, 5.00, -25.60, -16.80, -76.00, -57.00),
        # Rear P21 bolting screws at (±6.20, -30.50): M3 through-holes + bottom counterbores:
        cyl_z(-6.20, -30.50, -65.00, -57.50, 1.65),
        cyl_z( 6.20, -30.50, -65.00, -57.50, 1.65),
        cyl_z(-6.20, -30.50, -72.00, -62.00, 3.00),
        cyl_z( 6.20, -30.50, -72.00, -62.00, 3.00),
        # P01 front boss sockets and M3x10 screw holes at (±18.0, Z=-52.78, Y=11.48..19.60):
        cyl_y( 18.0, -52.78, 11.0, 15.95, 4.15),
        cyl_y(-18.0, -52.78, 11.0, 15.95, 4.15),
        cyl_y( 18.0, -52.78, 15.5, 20.0, 1.65),
        cyl_y(-18.0, -52.78, 15.5, 20.0, 1.65),
        cyl_y( 18.0, -52.78, 18.2, 20.5, 3.00),
        cyl_y(-18.0, -52.78, 18.2, 20.5, 3.00),
        # P23 probe mount M3x4x4.6 heat-set pockets at (±15.80, +8.50) and (±15.80, -11.50), Z = -70.80..-66.80:
        cyl_z( 15.80,   8.50, -71.00, -66.80, 2.27),
        cyl_z(-15.80,   8.50, -71.00, -66.80, 2.27),
        cyl_z( 15.80, -11.50, -71.00, -66.80, 2.27),
        cyl_z(-15.80, -11.50, -71.00, -66.80, 2.27),
        # Volcano hotend + Beacon upper keepout clearance in the center (|X| <= 10.60, Y >= -6.50):
        box(-10.60, 10.60, 12.00, 50.00, -76.00, -50.00),
        cyl_z(0.0, 3.20, -76.00, -54.00, 9.55),
    ]
    body = cut_all(body, cutters)
    body = intersect_all(body, [box(-22.497, 22.497, -50.0, 30.0, -75.80, -48.60)])
    return body, air


def build_p23_probe_mount_v2():
    """
    Forward-Facing Beacon RevH Normal & Cartographer V3 Flat Pack Mount:
    - Places M3 sensor mounting holes at (X = ±15.80, Y = -0.30, Z_seat = -75.00 mm)
    - Moves Beacon sensing coil forward to (X = 0.0, Y = +3.20 mm, Z_bot = -76.61 mm -> 2.27 mm above nozzle tip!)
    - Cuts nozzle-to-sensor offset from 29.40 mm down to 19.50 mm!
    - Places the sensor cable connector at the REAR (Y = -15.68..-10.13 mm) with an integrated rear cable guide
    - Bolts directly to the underside of P22 at (±15.80, +8.50) and (±15.80, -11.50) at Z = -70.80 mm
    """
    z_seat = -75.000
    z_top  = -70.800

    deck_verts = [
        (-19.20, -14.20), ( 19.20, -14.20),
        ( 19.20,  13.20), (-19.20,  13.20),
    ]
    deck = prism_xy_rounded(deck_verts, 2.0, z_seat, z_top)

    # Integrated front radiant thermal baffle between Volcano block (Y=14.00) and Beacon coil (Y=11.70):
    baffle = rounded_box_xy(-10.50, 10.50, 12.10, 13.20, z_seat, -64.00, 0.5)

    body = fuse_all([deck, baffle])

    cutters = [
        # Open coil & keepout window centered at (0.0, +3.20):
        cyl_z(0.0, 3.20, -76.00, -54.00, 9.60),
        # Rear connector dome & cable routing recess (X = [-11.5, 11.5], Y = [-15.0, -5.0]):
        box(-11.50, 11.50, -15.00, -5.00, z_seat - 1.0, z_top + 1.0),
        # Forward-facing sensor M3 mounting holes & captive nut slots at (±15.80, Y = -0.30):
        cyl_z( 15.80, -0.30, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80, -0.30, z_seat - 1.0, z_top + 1.0, 1.65),
        box( 12.80, 19.50, -3.15, 2.55, -73.60, -71.50),
        box(-19.50, -12.80, -3.15, 2.55, -73.60, -71.50),
        # P23-to-P22 M3x8 mounting holes & bottom counterbores at (±15.80, +8.50) and (±15.80, -11.50):
        cyl_z( 15.80,   8.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80,   8.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z( 15.80,   8.50, z_seat - 1.0, -72.60, 3.00),
        cyl_z(-15.80,   8.50, z_seat - 1.0, -72.60, 3.00),
        cyl_z( 15.80, -11.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80, -11.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z( 15.80, -11.50, z_seat - 1.0, -72.60, 3.00),
        cyl_z(-15.80, -11.50, z_seat - 1.0, -72.60, 3.00),
    ]
    body = cut_all(body, cutters)
    return body


if __name__ == "__main__":
    t0 = time.time()
    v26_meta = json.loads((WORK / "v26_meta.json").read_text())
    v26_raw = bva.load_brep_list(WORK / "v26_cache.brep")
    gantry_meta = json.loads((WORK / "gantry_meta.json").read_text())
    gantry_raw = bva.load_brep_list(WORK / "gantry_cache.brep")
    v26_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(v26_meta, v26_raw)}
    gantry_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(gantry_meta, gantry_raw)}

    p20_b, p20_a = build_p20_inlet_v2()
    p21_b, p21_a = build_p21_mid_v2()
    p22_b, p22_a = build_p22_lower_plenum_v2()
    p23_b = build_p23_probe_mount_v2()
    p24_b = bva.build_p24_ebb42_mount()

    # Forward-facing Beacon RevH Normal at (0, +3.20, -75.00), rot_z = 0:
    beacon_sols = bva.load_step(SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")
    trsf_b = gp_Trsf()
    trsf_b.SetTranslation(gp_Vec(0.0, 3.20, -75.00))
    beacon_world = [BRepBuilderAPI_Transform(s, trsf_b, True).Shape() for s in beacon_sols]
    beacon_bot_ko = beacon_world[0]
    beacon_top_ko = beacon_world[1]
    beacon_phys   = beacon_world[2:5]

    for pname, ps in [("P20", p20_b), ("P21", p21_b), ("P22", p22_b), ("P23", p23_b), ("P24", p24_b)]:
        v_hits = [(n, round(common_vol(ps, s), 3)) for n, (s, _, _) in v26_by_name.items() if common_vol(ps, s) > 1e-3]
        g_hits = [(n, round(common_vol(ps, s), 3)) for n, (s, _, _) in gantry_by_name.items() if common_vol(ps, s) > 1e-3]
        b_hits = [round(common_vol(ps, bs), 3) for bs in (*beacon_phys, beacon_bot_ko) if common_vol(ps, bs) > 1e-3]
        print(f"{pname}: solids={bva.solid_count(ps)} shells={bva.shell_count(ps)} vol={bva.vol_of(ps):.1f} v26_hits={v_hits} gan_hits={g_hits} beacon_hits={b_hits}")

    parts = [("P20", p20_b), ("P21", p21_b), ("P22", p22_b), ("P23", p23_b), ("P24", p24_b)]
    for i in range(len(parts)):
        for j in range(i+1, len(parts)):
            ov = common_vol(parts[i][1], parts[j][1])
            if ov > 1e-3:
                print(f"OVERLAP {parts[i][0]}-{parts[j][0]}: {ov:.3f}")
    print(f"Done in {time.time()-t0:.2f}s")
