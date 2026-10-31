import sys, json, math, time
from pathlib import Path
sys.path.append(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\CAD\SparkShift_Accessories_v26")
import build_and_verify_accessories_v26 as bva
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Ax3, gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.TopoDS import TopoDS

WORK = Path(__file__).resolve().parent

def place_wire_3d(verts_2d, radius, origin_xyz, theta_rad):
    """
    Place a 2D wire (u, v) on a plane tilted by theta_rad in the YZ plane:
    - theta = 0: normal = (0, 0, -1), u -> +X, v -> -Y (horizontal plane Z = z_c)
    - theta = pi/2: normal = (0, 1, 0), u -> +X, v -> -Z (vertical plane Y = y_c)
    For any theta:
      X = u
      Y = y_c - v * cos(theta)
      Z = z_c - v * sin(theta)
    """
    w_xy = bva.rounded_polygon_wire_xy(verts_2d, radius, 0.0)
    ax_src = gp_Ax3(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0))
    ny = math.sin(theta_rad)
    nz = -math.cos(theta_rad)
    ax_dst = gp_Ax3(gp_Pnt(*origin_xyz), gp_Dir(0.0, ny, nz), gp_Dir(1.0, 0.0, 0.0))
    trsf = gp_Trsf()
    trsf.SetTransformation(ax_dst, ax_src)
    return TopoDS.Wire_s(BRepBuilderAPI_Transform(w_xy, trsf, True).Shape())


def build_mandrel_side_duct(sign, is_inner=False):
    """
    Build one continuous C2 NURBS mandrel-bent tube from Z = -58.00 (rear gantry trunk)
    around a concentric circular bend (theta = 0 -> 80 deg) and along a gentle swan-neck
    glide all the way to the front nozzle tip (Y = +23.8 mm)!
    """
    w = 1.20 if is_inner else 0.0

    # Stations: (y_in, z_in, theta_deg, xi_top, xo_top, xo_bot, xi_bot, h_in, h_out, rad)
    # Note: at v = 0 (top/inner wall of bend), (Y, Z) = (y_in, z_in).
    # At v = h (bottom/outer wall of bend), (Y, Z) = (y_in - h*cos(theta), z_in - h*sin(theta)).
    raw_stations = [
        # Rear mandrel bend: center of inner arc at (Y = -29.70, Z = -58.00) with R_in = 3.50 mm:
        # At theta = 0: y_in = -33.20, z_in = -58.00, h = 12.20 -> rear wall at Y = -45.40, Z = -58.00!
        (-33.20, -57.80 if is_inner else -58.00,  0.0,  4.80, 20.60, 14.50,  4.80, 12.20, 11.20, 2.6),
        (-33.03, -59.08,                         18.0,  4.90, 20.75, 16.00,  4.90, 12.00, 11.20, 2.6),
        (-32.53, -60.06,                         36.0,  5.00, 21.00, 18.00,  5.00, 11.70, 11.20, 2.6),
        (-31.76, -60.83,                         54.0,  5.05, 21.40, 20.00,  5.05, 11.30, 11.00, 2.6),
        (-30.78, -61.33,                         72.0,  5.10, 21.85, 21.50,  5.10, 10.60, 10.50, 2.6),
        (-28.50, -61.50,                         84.0,  5.15, 22.25, 22.15,  5.15,  9.80,  9.80, 2.6),
        # Smooth forward & downward swan-neck glide past GANTRY_Body40 and Beacon keepout:
        (-21.00, -61.20,                         86.0,  5.25, 22.45, 22.45,  5.25,  9.80,  9.80, 2.6),
        (-15.00, -61.00,                         86.0,  6.00, 22.45, 22.45,  6.00,  9.90,  9.90, 2.6),
        ( -9.50, -60.80,                         85.0,  8.20, 22.45, 22.45,  8.20, 10.00, 10.00, 2.5),
        ( -4.00, -60.80,                         84.0,  9.70, 22.45, 22.45,  9.70, 10.00, 10.00, 2.5),
        (  2.50, -61.10,                         82.0,  9.85, 22.45, 22.45,  9.85,  9.80,  9.80, 2.5),
        (  8.50, -62.00,                         78.0, 10.00, 22.45, 22.45, 10.00,  9.50,  9.30, 2.4),
        # Smooth inward & downward calliper curve to the Volcano nozzle tip (no 90-deg drop!):
        ( 13.50, -63.60,                         75.0, 10.10, 22.35, 22.35, 10.10,  9.20,  8.80, 2.2),
        ( 17.50, -66.20,                         74.0,  9.95, 21.70, 21.70,  9.85,  8.60,  7.60, 1.9),
        ( 20.50, -69.20,                         75.0,  9.75, 20.50, 20.50,  8.20,  6.80,  5.60, 1.5),
        ( 22.80, -71.50,                         78.0,  9.65, 19.00, 19.00,  7.00,  4.40,  4.10, 1.2),
        ( 24.30, -72.60,                         82.0,  9.65, 17.60, 17.60,  6.80,  3.30,  3.10, 1.0),
    ]

    loft = BRepOffsetAPI_ThruSections(True, False, 1e-3)
    loft.SetMaxDegree(3)
    for idx, (yin, zin, deg, xit, xot, xob, xib, h_out_side, h_in_side, r) in enumerate(raw_stations):
        th = math.radians(deg)
        # Apply wall offset:
        xit_w = xit + w
        xib_w = xib + w
        xot_w = xot - w
        xob_w = xob - w
        v_top = w
        v_bot_out = h_out_side - w
        v_bot_in  = h_in_side  - w
        # Extend ends slightly on inner air cavity so boolean cut opens both ports cleanly:
        if is_inner and idx == 0:
            zin = -57.50
        if is_inner and idx == len(raw_stations) - 1:
            yin = 23.30
        if sign > 0:
            verts_2d = [
                (xit_w, v_top),
                (xot_w, v_top),
                (xob_w, v_bot_out),
                (xib_w, v_bot_in),
            ]
        else:
            verts_2d = [
                (-xot_w, v_top),
                (-xit_w, v_top),
                (-xib_w, v_bot_in),
                (-xob_w, v_bot_out),
            ]
        wire = place_wire_3d(verts_2d, max(0.5, r - 0.7 * w), (0.0, yin, zin), th)
        loft.AddWire(wire)
    loft.Build()
    return loft.Shape()


def build_full_mandrel_p22():
    z_top = -58.000
    s_out_r = build_mandrel_side_duct( 1, False)
    s_in_r  = build_mandrel_side_duct( 1, True)
    s_out_l = build_mandrel_side_duct(-1, False)
    s_in_l  = build_mandrel_side_duct(-1, True)

    # Central bridge block (X = [-8.50, 8.50]) joining s_out_l and s_out_r cleanly at Z = -61.50..-58.00 without coincident outer walls:
    top_collar_out = bva.rounded_box_xy(-8.50, 8.50, -45.40, -33.20, -61.50, z_top, 1.5)
    top_collar_in  = bva.cut_all(
        bva.rounded_box_xy(-7.50, 7.50, -44.20, -34.40, -60.30, z_top + 0.50, 1.2),
        [bva.cyl_z(0.0, -34.50, -61.00, z_top + 1.00, 3.20)],
    )

    # Smooth C2 NURBS upper front mounting cheeks (strictly Y >= 11.48 above Z = -58.00 to clear P01):
    cheeks = []
    for sign in (-1, 1):
        x_in_k, x_out_k = (13.95, 22.45) if sign > 0 else (-22.45, -13.95)
        x_in_b, x_out_b = (12.20, 22.40) if sign > 0 else (-22.40, -12.20)
        cheek = bva.make_loft([
            bva.rounded_polygon_wire_xy([(x_in_b, 11.48), (x_out_b, 11.48), (x_out_b, 20.20), (x_in_b, 20.20)], 2.2, -65.50),
            bva.rounded_polygon_wire_xy([(x_in_k, 11.48), (x_out_k, 11.48), (x_out_k, 19.80), (x_in_k, 19.80)], 1.8, -59.50),
            bva.rounded_polygon_wire_xy([(x_in_k, 11.48), (x_out_k, 11.48), (x_out_k, 19.60), (x_in_k, 19.60)], 1.6, -54.00),
            bva.rounded_polygon_wire_xy([(x_in_k, 11.48), (x_out_k, 11.48), (x_out_k, 19.60), (x_in_k, 19.60)], 1.6, -48.60),
        ], ruled=False)
        cheeks.append(cheek)
        # Nozzle inward jet opening at the front tip:
        jet_cut = bva.box(sign * 5.8, sign * 14.2, 17.8, 23.5, -74.80, -72.80)
        if sign > 0:
            s_in_r = bva.fuse_all([s_in_r, jet_cut])
        else:
            s_in_l = bva.fuse_all([s_in_l, jet_cut])

    # Smooth rear bolting flange to P21 at (±6.80, -30.20, Z = -61.50..-56.00):
    rear_fairing = bva.make_loft([
        bva.rounded_polygon_wire_xy([(-9.80, -34.50), (-9.80, -26.80), (9.80, -26.80), (9.80, -34.50)], 2.4, -61.50),
        bva.rounded_polygon_wire_xy([(-9.80, -33.20), (-9.80, -27.20), (9.80, -27.20), (9.80, -33.20)], 2.4, -56.00),
    ], ruled=False)

    # Smooth MGN12H lower center cradle & P23 mounting bosses:
    cart_cradle = bva.make_loft([
        bva.rounded_polygon_wire_xy([(-11.20, -10.50), (11.20, -10.50), (11.20, 1.00), (-11.20, 1.00)], 2.2, -62.50),
        bva.rounded_polygon_wire_xy([( -9.80,  -9.70), ( 9.80,  -9.70), ( 9.80, 0.30), ( -9.80, 0.30)], 1.8, -58.00),
        bva.rounded_polygon_wire_xy([( -9.80,  -9.70), ( 9.80,  -9.70), ( 9.80, 0.30), ( -9.80, 0.30)], 1.8, -51.35),
    ], ruled=False)
    front_tie = bva.rounded_box_xy(-12.00, 12.00, -1.50, 2.50, -70.80, -67.50, 1.2)
    p23_bosses = [
        bva.cyl_z( 15.80,   8.50, -70.80, -63.00, 3.60),
        bva.cyl_z(-15.80,   8.50, -70.80, -63.00, 3.60),
        bva.cyl_z( 15.80, -11.50, -70.80, -63.00, 3.60),
        bva.cyl_z(-15.80, -11.50, -70.80, -63.00, 3.60),
    ]

    body = bva.fuse_all([top_collar_out, s_out_r, s_out_l, *cheeks, rear_fairing, cart_cradle, front_tie, *p23_bosses])
    print("  fused body in", round(time.time(), 2))
    air  = bva.fuse_all([top_collar_in, s_in_r, s_in_l])
    print("  fused air in", round(time.time(), 2))

    air_excl = bva.fuse_all([
        bva.box(-6.00, 6.00, -46.00, -15.80, -75.00, -60.30),
        bva.box(-6.00, 6.00, -26.80, -15.80, -75.00, -57.00),
        bva.cyl_z(-6.80, -30.20, -61.50, -55.50, 3.20),
        bva.cyl_z( 6.80, -30.20, -61.50, -55.50, 3.20),
        bva.cyl_z( 15.80,   8.50, -71.00, -66.50, 3.60),
        bva.cyl_z(-15.80,   8.50, -71.00, -66.50, 3.60),
        bva.cyl_z( 15.80, -11.50, -71.00, -66.50, 3.60),
        bva.cyl_z(-15.80, -11.50, -71.00, -66.50, 3.60),
    ])
    air = bva.cut_all(air, [air_excl])

    cutters = [
        air,
        bva.box(-4.80, 4.80, -46.00, -16.80, -76.00, -61.50),
        bva.box(-4.80, 4.80, -25.60, -16.80, -76.00, -57.00),
        bva.box(-15.00, 15.00, -45.00, -33.20, -58.00, -50.00),
        bva.cyl_z(-6.80, -30.20, -60.00, -55.80, 2.27),
        bva.cyl_z( 6.80, -30.20, -60.00, -55.80, 2.27),
        bva.box(-2.00, 2.00, -36.50, -26.50, -58.20, -53.00),
        bva.cyl_y( 18.0, -52.78, 11.0, 15.95, 4.15),
        bva.cyl_y(-18.0, -52.78, 11.0, 15.95, 4.15),
        bva.cyl_y( 18.0, -52.78, 15.5, 20.0, 1.65),
        bva.cyl_y(-18.0, -52.78, 15.5, 20.0, 1.65),
        bva.cyl_y( 18.0, -52.78, 18.2, 20.5, 3.00),
        bva.cyl_y(-18.0, -52.78, 18.2, 20.5, 3.00),
        # Flat seating pocket at Z <= -70.80 for P23_Beacon_Cartographer_Mount:
        bva.box(-19.30, 19.30, -14.30, 13.30, -76.00, -70.80),
        bva.cyl_z( 15.80,   8.50, -71.00, -66.80, 2.27),
        bva.cyl_z(-15.80,   8.50, -71.00, -66.80, 2.27),
        bva.cyl_z( 15.80, -11.50, -71.00, -66.80, 2.27),
        bva.cyl_z(-15.80, -11.50, -71.00, -66.80, 2.27),
        bva.box(-10.60, 10.60, 12.00, 50.00, -73.45, -50.00),
        bva.cyl_z(0.0, 3.20, -76.00, -54.00, 9.55),
    ]
    body = bva.cut_all(body, cutters)
    body = bva.intersect_all(body, [bva.box(-22.497, 22.497, -50.0, 30.0, -75.80, -48.60)])
    return body, air


if __name__ == "__main__":
    t0 = time.time()
    v26_meta = json.loads((WORK / "v26_meta.json").read_text())
    v26_raw = bva.load_brep_list(WORK / "v26_cache.brep")
    gantry_meta = json.loads((WORK / "gantry_meta.json").read_text())
    gantry_raw = bva.load_brep_list(WORK / "gantry_cache.brep")
    v26_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(v26_meta, v26_raw)}
    gantry_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(gantry_meta, gantry_raw)}

    p22_b, p22_a = build_full_mandrel_p22()
    p23_b = bva.build_p23_probe_mount()
    vh = [(n, round(bva.common_vol(p22_b, vs), 3)) for n, (vs, _, _) in v26_by_name.items() if bva.common_vol(p22_b, vs) > 1e-3]
    gh = [(n, round(bva.common_vol(p22_b, gs), 3)) for n, (gs, _, _) in gantry_by_name.items() if bva.common_vol(p22_b, gs) > 1e-3]
    print(f"Mandrel P22: solids={bva.solid_count(p22_b)} shells={bva.shell_count(p22_b)} vol={bva.vol_of(p22_b):.1f} v26={vh} gan={gh} p23_ov={bva.common_vol(p22_b, p23_b):.4f} time={time.time()-t0:.2f}s")

