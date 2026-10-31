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
    w_xy = bva.rounded_polygon_wire_xy(verts_2d, radius, 0.0)
    ax_src = gp_Ax3(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0))
    ny = math.sin(theta_rad)
    nz = -math.cos(theta_rad)
    ax_dst = gp_Ax3(gp_Pnt(*origin_xyz), gp_Dir(0.0, ny, nz), gp_Dir(1.0, 0.0, 0.0))
    trsf = gp_Trsf()
    trsf.SetTransformation(ax_dst, ax_src)
    return TopoDS.Wire_s(BRepBuilderAPI_Transform(w_xy, trsf, True).Shape())


def build_mandrel_side_duct(sign, is_inner=False):
    w = 1.20 if is_inner else 0.0
    raw_stations = [
        # Rear mandrel bend: smooth circular inner & outer arcs from Z = -58.00 (theta=0) to theta=85 deg:
        (-33.20, -57.70 if is_inner else -58.00,  0.0,  5.00, 20.60, 14.50,  5.00, 12.20, 11.20, 2.8),
        (-33.03, -59.08,                         18.0,  5.05, 20.75, 16.00,  5.05, 12.00, 11.20, 2.8),
        (-32.53, -60.06,                         36.0,  5.10, 21.00, 18.00,  5.10, 11.70, 11.20, 2.8),
        (-31.76, -60.83,                         54.0,  5.15, 21.40, 20.00,  5.15, 11.30, 11.00, 2.8),
        (-30.78, -61.33,                         72.0,  5.20, 21.85, 21.50,  5.20, 10.60, 10.50, 2.8),
        (-28.50, -61.50,                         84.0,  5.25, 22.25, 22.15,  5.25,  9.80,  9.80, 2.8),
        # Smooth forward & downward swan-neck glide past GANTRY_Body40 and Beacon keepout:
        (-21.00, -61.20,                         86.0,  5.40, 22.45, 22.45,  5.40,  9.80,  9.80, 2.8),
        (-15.00, -61.00,                         86.0,  6.80, 22.45, 22.45,  6.80,  9.80,  9.80, 2.8),
        (-10.50, -60.85,                         85.0,  9.15, 22.45, 22.45,  9.15,  9.90,  9.90, 2.7),
        ( -4.50, -60.80,                         84.0,  9.90, 22.45, 22.45,  9.90,  9.90,  9.90, 2.7),
        (  2.50, -61.10,                         82.0, 10.30, 22.45, 22.45, 10.30,  9.70,  9.70, 2.6),
        ( 10.20, -62.40,                         78.0, 10.85, 22.45, 22.45, 10.85,  9.30,  9.10, 2.5),
        # Smooth inward & downward calliper curve to the Volcano nozzle tip (no 90-deg drop!):
        ( 14.50, -64.10,                         75.0, 10.65, 22.30, 22.30, 10.55,  8.90,  8.50, 2.3),
        ( 18.00, -66.60,                         74.0, 10.10, 21.60, 21.60,  9.85,  8.30,  7.30, 2.0),
        ( 20.80, -69.50,                         75.0,  9.75, 20.40, 20.40,  8.20,  6.50,  5.40, 1.6),
        ( 22.80, -71.50,                         78.0,  9.65, 19.00, 19.00,  7.00,  4.40,  4.10, 1.3),
        ( 24.30, -72.60,                         82.0,  9.65, 17.60, 17.60,  6.80,  3.30,  3.10, 1.0),
    ]

    loft = BRepOffsetAPI_ThruSections(True, False, 1e-3)
    loft.SetMaxDegree(3)
    for idx, (yin, zin, deg, xit, xot, xob, xib, h_out_side, h_in_side, r) in enumerate(raw_stations):
        th = math.radians(deg)
        xit_w = xit + w
        xib_w = xib + w
        xot_w = xot - w
        xob_w = xob - w
        v_top = w
        v_bot_out = h_out_side - w
        v_bot_in  = h_in_side  - w
        if sign > 0:
            verts_2d = [(xit_w, v_top), (xot_w, v_top), (xob_w, v_bot_out), (xib_w, v_bot_in)]
        else:
            verts_2d = [(-xot_w, v_top), (-xit_w, v_top), (-xib_w, v_bot_in), (-xob_w, v_bot_out)]
        wire = place_wire_3d(verts_2d, max(0.5, r - 0.7 * w), (0.0, yin, zin), th)
        loft.AddWire(wire)
    loft.Build()
    return loft.Shape()


def build_p22_mandrel():
    z_top = -58.000
    s_out_r = build_mandrel_side_duct( 1, False)
    s_in_r  = build_mandrel_side_duct( 1, True)
    s_out_l = build_mandrel_side_duct(-1, False)
    s_in_l  = build_mandrel_side_duct(-1, True)

    # Central bridge block (X = [-8.50, 8.50]) joining s_out_l and s_out_r cleanly at Z = -61.50..-58.00:
    top_collar_out = bva.rounded_box_xy(-8.50, 8.50, -45.40, -33.20, -61.50, z_top, 1.8)
    top_collar_in  = bva.cut_all(
        bva.rounded_box_xy(-7.50, 7.50, -44.20, -34.40, -60.30, z_top + 0.50, 1.2),
        [bva.cyl_z(0.0, -34.50, -61.00, z_top + 1.00, 3.20)],
    )

    cheeks = []
    jet_cuts = []
    for sign in (-1, 1):
        x_in_k, x_out_k = (13.95, 22.45) if sign > 0 else (-22.45, -13.95)
        x_in_b, x_out_b = (12.20, 22.40) if sign > 0 else (-22.40, -12.20)
        loft = BRepOffsetAPI_ThruSections(True, False, 1e-3)
        loft.SetMaxDegree(3)
        for z_c, x0, x1, y0, y1, rad in [
            (-65.50, x_in_b, x_out_b, 11.48, 20.20, 2.2),
            (-59.50, x_in_k, x_out_k, 11.48, 19.80, 1.8),
            (-54.00, x_in_k, x_out_k, 11.48, 19.60, 1.6),
            (-48.60, x_in_k, x_out_k, 11.48, 19.60, 1.6),
        ]:
            loft.AddWire(bva.rounded_polygon_wire_xy([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], rad, z_c))
        loft.Build()
        cheeks.append(loft.Shape())
        jet_cuts.append(bva.box(sign * 5.8, sign * 14.2, 18.0, 23.5, -74.80, -72.80))

    rear_fairing = bva.rounded_box_xy(-12.00, 12.00, -33.20, -27.20, -61.20, -56.00, 2.2)
    cart_cradle = bva.make_loft([
        bva.rounded_polygon_wire_xy([(-13.50, -10.50), (13.50, -10.50), (13.50, 1.00), (-13.50, 1.00)], 2.2, -64.50),
        bva.rounded_polygon_wire_xy([(-12.50,  -9.70), (12.50,  -9.70), (12.50, 0.30), (-12.50, 0.30)], 1.8, -58.20),
        bva.rounded_polygon_wire_xy([( -9.80,  -9.70), ( 9.80,  -9.70), ( 9.80, 0.30), ( -9.80, 0.30)], 1.8, -57.50),
        bva.rounded_polygon_wire_xy([( -9.80,  -9.70), ( 9.80,  -9.70), ( 9.80, 0.30), ( -9.80, 0.30)], 1.8, -51.35),
    ], ruled=True)

    # P23 mounting bosses placed on the inner spine (100% outside s_in_r/s_in_l and 100% outside Beacon r=9.37mm keepout!):
    p23_bosses = [
        bva.rounded_box_xy( 6.80, 13.50,   7.20, 12.50, -70.80, -62.50, 1.5),
        bva.rounded_box_xy(-13.50, -6.80,  7.20, 12.50, -70.80, -62.50, 1.5),
        bva.rounded_box_xy( 5.20, 12.50, -13.00, -7.80, -70.80, -61.00, 1.5),
        bva.rounded_box_xy(-12.50, -5.20,-13.00, -7.80, -70.80, -61.00, 1.5),
    ]

    # Hollow out the two mandrel ducts FIRST (fast 2.5s boolean on clean NURBS):
    hollow_r = bva.cut_all(s_out_r, [s_in_r, jet_cuts[1]])
    hollow_l = bva.cut_all(s_out_l, [s_in_l, jet_cuts[0]])
    hollow_top = bva.cut_all(top_collar_out, [top_collar_in, s_in_r, s_in_l])

    body = bva.fuse_all([hollow_r, hollow_l, hollow_top, *cheeks, rear_fairing, cart_cradle, *p23_bosses])

    cutters = [
        top_collar_in,
        s_in_r,
        s_in_l,
        bva.box(-4.80, 4.80, -46.00, -16.80, -76.00, -61.50),
        bva.box(-4.80, 4.80, -25.60, -16.80, -76.00, -57.00),
        bva.box(-15.00, 15.00, -45.00, -33.20, -58.00, -50.00),
        bva.cyl_z(-6.80, -30.20, -60.00, -55.80, 2.27),
        bva.cyl_z( 6.80, -30.20, -60.00, -55.80, 2.27),
        bva.box(-2.00, 2.00, -36.50, -26.50, -56.80, -53.00),
        bva.cyl_y( 18.0, -52.78, 11.0, 15.95, 4.15),
        bva.cyl_y(-18.0, -52.78, 11.0, 15.95, 4.15),
        bva.cyl_y( 18.0, -52.78, 15.5, 20.0, 1.65),
        bva.cyl_y(-18.0, -52.78, 15.5, 20.0, 1.65),
        bva.cyl_y( 18.0, -52.78, 18.2, 20.5, 3.00),
        bva.cyl_y(-18.0, -52.78, 18.2, 20.5, 3.00),
        bva.box(-19.30, 19.30, -14.30, 13.30, -76.00, -70.80),
        bva.cyl_z( 9.60,  10.20, -71.00, -66.80, 2.27),
        bva.cyl_z(-9.60,  10.20, -71.00, -66.80, 2.27),
        bva.cyl_z( 7.80, -10.50, -71.00, -66.80, 2.27),
        bva.cyl_z(-7.80, -10.50, -71.00, -66.80, 2.27),
        bva.box(-10.60, 10.60, 12.00, 50.00, -73.45, -50.00),
        bva.cyl_z(0.0, 3.20, -76.00, -54.00, 9.55),
    ]
    body = bva.cut_all(body, cutters)
    body = bva.intersect_all(body, [bva.box(-22.497, 22.497, -50.0, 30.0, -75.80, -48.60)])
    return body


if __name__ == "__main__":
    t0 = time.time()
    v26_meta = json.loads((WORK / "v26_meta.json").read_text())
    v26_raw = bva.load_brep_list(WORK / "v26_cache.brep")
    gantry_meta = json.loads((WORK / "gantry_meta.json").read_text())
    gantry_raw = bva.load_brep_list(WORK / "gantry_cache.brep")
    v26_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(v26_meta, v26_raw)}
    gantry_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(gantry_meta, gantry_raw)}

    p22_b = build_p22_mandrel()
    vh = [(n, round(bva.common_vol(p22_b, vs), 3)) for n, (vs, _, _) in v26_by_name.items() if bva.common_vol(p22_b, vs) > 1e-3]
    gh = [(n, round(bva.common_vol(p22_b, gs), 3)) for n, (gs, _, _) in gantry_by_name.items() if bva.common_vol(p22_b, gs) > 1e-3]
    print(f"Mandrel P22: solids={bva.solid_count(p22_b)} shells={bva.shell_count(p22_b)} vol={bva.vol_of(p22_b):.1f} v26={vh} gan={gh} time={time.time()-t0:.2f}s")
