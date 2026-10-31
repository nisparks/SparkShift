import sys, json, math, time
from pathlib import Path
sys.path.append(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\CAD\SparkShift_Accessories_v26")
import build_and_verify_accessories_v26 as bva
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Ax2, gp_Vec, gp_Trsf

WORK = Path(__file__).resolve().parent

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
make_loft = bva.make_loft
make_loft_along_y = bva.make_loft_along_y


def build_smooth_p21():
    """
    Smoothly faired vertical gantry conduit (Z = -58.00 to -17.78 mm):
    - Upper MGN12H saddle is lofted smoothly out of the vertical conduit (Z = -31.0 to -18.4 mm)
      so there is NO 90-degree step under the saddle!
    - Lower bolting flange is lofted smoothly out of the conduit (Z = -58.0 to -50.5 mm)!
    """
    z_top = -17.780
    z_bot = -58.000
    conduit_outer = prism_xy_rounded(corridor_aero_vertices(0.0), 3.5, z_bot, z_top)
    conduit_inner = cut_all(
        prism_xy_rounded(corridor_aero_vertices(1.2), 2.5, z_bot - 1.0, z_top + 1.0),
        [cyl_z(0.0, -34.50, z_bot - 2.0, z_top + 2.0, 3.20)],
    )

    # Smoothly tapered upper bridge fairing (no 90-deg overhang!):
    # Note: GANTRY_Body12 (2020 X-beam) is at Y=[-32.70, -12.70], Z=[-47.78, -27.78].
    # Above Z = -27.50, we can smoothly sweep forward from Y=-33.20 to Y=+0.30!
    up_lug_l = cyl_z(-5.0, -30.5, -26.50, z_top, 3.8)
    up_lug_r = cyl_z( 5.0, -30.5, -26.50, z_top, 3.8)
    up_fairing = make_loft([
        rounded_polygon_wire_xy([(-9.20, -35.50), (-9.20, -33.20), (9.20, -33.20), (9.20, -35.50)], 1.5, -27.60),
        rounded_polygon_wire_xy([(-9.20, -35.50), (-9.20, -29.00), (9.20, -29.00), (9.20, -35.50)], 1.5, -25.80),
        rounded_polygon_wire_xy([(-9.50, -35.50), (-9.50, -12.10), (9.50, -12.10), (9.50, -35.50)], 1.8, -24.10),
        rounded_polygon_wire_xy([(-9.50, -35.50), (-9.50, -12.10), (9.50, -12.10), (9.50, -35.50)], 1.8, -18.40),
    ], ruled=True)
    up_bridge_verts = [
        (-9.20, -34.50), (-9.20, -12.10), (-21.00, -9.70), (-21.00, 0.30),
        ( 21.00,  0.30), ( 21.00, -9.70), (  9.20, -12.10), (  9.20, -34.50),
    ]
    up_saddle = prism_xy_rounded(up_bridge_verts, 2.2, -24.10, -18.40)

    # Smoothly tapered lower mounting flange (Z = -56.00 to -49.00, strictly below X-beam Z=-47.78 and inside |X|<=9.80):
    lo_fairing = make_loft([
        rounded_polygon_wire_xy([(-9.80, -35.50), (-9.80, -27.20), (9.80, -27.20), (9.80, -35.50)], 2.2, -56.00),
        rounded_polygon_wire_xy([(-9.80, -35.50), (-9.80, -28.00), (9.80, -28.00), (9.80, -35.50)], 2.2, -52.50),
        rounded_polygon_wire_xy([(-9.20, -35.50), (-9.20, -33.20), (9.20, -33.20), (9.20, -35.50)], 1.5, -48.50),
    ], ruled=True)

    body = fuse_all([conduit_outer, up_lug_l, up_lug_r, up_fairing, up_saddle, lo_fairing])

    cutters = [
        conduit_inner,
        cyl_z(-5.0, -30.5, -21.30, z_top + 0.5, 2.27),
        cyl_z( 5.0, -30.5, -21.30, z_top + 0.5, 2.27),
        cyl_z(-5.0, -30.5, -27.00, -21.20, 1.65),
        cyl_z( 5.0, -30.5, -27.00, -21.20, 1.65),
        cyl_z(-6.80, -30.20, -56.50, -48.00, 1.65),
        cyl_z( 6.80, -30.20, -56.50, -48.00, 1.65),
        cyl_z(-6.80, -30.20, -52.50, -48.00, 3.00),
        cyl_z( 6.80, -30.20, -52.50, -48.00, 3.00),
        cyl_z(0.0, -34.50, z_bot - 1.0, z_top + 1.0, 2.00),
        box(-2.00, 2.00, -34.50, -27.00, -58.50, -52.50),
    ]
    body = cut_all(body, cutters)
    body = intersect_all(body, [box(-22.497, 22.497, -50.0, 25.0, z_bot, z_top)])
    air = cut_all(
        prism_xy_rounded(corridor_aero_vertices(1.2), 2.5, z_bot, z_top),
        [cyl_z(0.0, -34.50, z_bot - 1.0, z_top + 1.0, 3.20)],
    )
    return body, air


def build_smooth_p22():
    """
    Continuous Swan-Neck / Wishbone Swept Lower CPAP Plenum:
    - Eliminates BOTH 90-degree bends!
    - 1) Rear turn: Both the rear wall AND the front roof sweep forward along a smooth curve
         from Z = -58.00 down to Z = -70.80 mm (no 90-deg front step at Z = -58.00!).
    - 2) Side-to-nozzle glide: One single continuous 14-station cosine-smoothed sweep along Y
         from Y = -35.0 mm to Y = +24.3 mm where the duct glides smoothly downward (from Z = -58.5..-70.8
         to Z = -70.5..-75.8) and curves smoothly inward around the nozzle without ANY vertical 90-deg drop!
    - 3) Sculpted mounting cheeks: Smoothly lofted fairings blending organically into the side ducts!
    """
    z_top = -58.000

    # Rear elbow: both rear AND front walls curve forward smoothly as Z drops from -58.00 to -70.80:
    def rear_sweep_verts(wall=0.0, dy_rear=0.0, y_front=-33.20):
        xf = 20.60 - wall
        xr = 13.00 - 0.45 * wall
        yf = y_front - wall
        ym = -38.20 + 0.40 * wall + 0.35 * dy_rear
        yr = -45.40 + wall + dy_rear
        return [
            (-xf, yf),
            (-xf, ym),
            (-xr, yr),
            ( xr, yr),
            ( xf, ym),
            ( xf, yf),
        ]

    # Notice y_front sweeps smoothly from -33.20 (matching P21 at Z=-58.00!) forward to -24.50 as Z drops!
    elbow_out_wires = [
        rounded_polygon_wire_xy(rear_sweep_verts(0.0, 9.5, -24.50), 3.0, -70.80),
        rounded_polygon_wire_xy(rear_sweep_verts(0.0, 6.8, -25.00), 3.2, -68.80),
        rounded_polygon_wire_xy(rear_sweep_verts(0.0, 4.2, -26.00), 3.3, -66.40),
        rounded_polygon_wire_xy(rear_sweep_verts(0.0, 2.0, -27.80), 3.4, -63.60),
        rounded_polygon_wire_xy(rear_sweep_verts(0.0, 0.6, -30.50), 3.5, -60.80),
        rounded_polygon_wire_xy(rear_sweep_verts(0.0, 0.0, -33.20), 3.5,  z_top),
    ]
    collar_outer = make_loft(elbow_out_wires, ruled=True)

    elbow_in_wires = [
        rounded_polygon_wire_xy(rear_sweep_verts(1.2, 9.2, -23.50), 2.0, -69.60),
        rounded_polygon_wire_xy(rear_sweep_verts(1.2, 6.5, -24.00), 2.2, -67.80),
        rounded_polygon_wire_xy(rear_sweep_verts(1.2, 4.0, -25.00), 2.3, -65.50),
        rounded_polygon_wire_xy(rear_sweep_verts(1.2, 1.8, -27.00), 2.4, -63.00),
        rounded_polygon_wire_xy(rear_sweep_verts(1.2, 0.5, -30.00), 2.5, -60.50),
        rounded_polygon_wire_xy(rear_sweep_verts(1.2, 0.0, -33.20), 2.5,  z_top + 0.50),
    ]
    collar_inner = cut_all(
        make_loft(elbow_in_wires, ruled=True),
        [cyl_z(0.0, -34.50, -61.00, z_top + 1.00, 3.20)],
    )

    ducts_outer = []
    ducts_inner = []
    for sign in (-1, 1):
        # Single continuous 15-station swan-neck sweep from Y = -35.5 to Y = +24.3 mm!
        # Notice z_top_o and z_top_i slope smoothly and continuously downward right from Y = -33.20 (Z = -58.00)
        # all the way to the nozzle tip (Y = +24.30, Z = -72.00) with ZERO flat horizontal roof and ZERO 90-deg drop!
        swan_out = [
            #   y,     xi_b,  xo_b,  xo_t,  xi_t,   z_bot,  z_top_o, z_top_i, rad
            (-35.50,   5.00, 20.55, 20.55,  5.00,  -70.80,  -58.20,  -58.20,  2.4),
            (-31.00,   5.00, 21.10, 21.10,  5.00,  -70.80,  -58.60,  -58.60,  2.5),
            (-26.00,   5.05, 21.75, 21.75,  5.05,  -70.80,  -59.30,  -59.30,  2.6),
            (-20.50,   5.20, 22.25, 22.25,  5.20,  -70.80,  -60.00,  -60.00,  2.6),
            (-15.00,   5.80, 22.45, 22.45,  5.80,  -70.80,  -60.50,  -60.50,  2.6),
            ( -9.50,   8.20, 22.45, 22.45,  8.20,  -70.80,  -60.80,  -60.80,  2.6),
            ( -4.00,   9.70, 22.45, 22.45,  9.70,  -70.80,  -61.00,  -61.00,  2.6),
            (  2.00,   9.80, 22.45, 22.45,  9.80,  -70.80,  -61.40,  -61.40,  2.5),
            (  7.50,   9.95, 22.45, 22.45,  9.95,  -70.80,  -62.20,  -62.50,  2.4),
            ( 12.00,  10.10, 22.35, 22.35, 10.10,  -71.50,  -63.50,  -64.20,  2.3),
            ( 15.50,   9.95, 21.95, 21.95, 10.00,  -72.80,  -65.20,  -66.80,  2.1),
            ( 18.50,   9.65, 21.20, 21.20,  9.85,  -74.20,  -67.20,  -70.00,  1.8),
            ( 21.00,   8.10, 20.00, 20.00,  9.70,  -75.30,  -69.20,  -73.45,  1.5),
            ( 22.80,   7.00, 18.80, 18.80,  9.65,  -75.80,  -70.80,  -73.55,  1.2),
            ( 24.30,   6.80, 17.50, 17.50,  9.65,  -75.80,  -72.00,  -73.65,  1.0),
        ]
        swan_in = [
            (-36.00,   6.20, 19.35, 19.35,  6.20,  -69.60,  -59.40,  -59.40,  1.5),
            (-31.00,   6.20, 19.90, 19.90,  6.20,  -69.60,  -59.80,  -59.80,  1.6),
            (-26.00,   6.25, 20.55, 20.55,  6.25,  -69.60,  -60.50,  -60.50,  1.6),
            (-20.50,   6.40, 21.05, 21.05,  6.40,  -69.60,  -61.20,  -61.20,  1.6),
            (-15.00,   7.00, 21.25, 21.25,  7.00,  -69.60,  -61.70,  -61.70,  1.6),
            ( -9.50,   9.40, 21.25, 21.25,  9.40,  -69.60,  -62.00,  -62.00,  1.6),
            ( -4.00,  10.90, 21.25, 21.25, 10.90,  -69.60,  -62.20,  -62.20,  1.6),
            (  2.00,  11.00, 21.25, 21.25, 11.00,  -69.60,  -62.60,  -62.60,  1.5),
            (  7.50,  11.15, 21.25, 21.25, 11.15,  -69.60,  -63.40,  -63.70,  1.4),
            ( 12.00,  11.30, 21.15, 21.15, 11.30,  -70.30,  -64.70,  -65.40,  1.3),
            ( 15.50,  11.15, 20.75, 20.75, 11.20,  -71.60,  -66.40,  -68.00,  1.2),
            ( 18.50,  10.60, 20.00, 20.00, 10.90,  -73.00,  -68.40,  -71.20,  1.0),
            ( 21.00,   7.30, 18.80, 18.80, 10.65,  -74.30,  -70.40,  -73.80,  0.8),
            ( 22.80,   6.00, 17.60, 17.60, 10.55,  -74.70,  -71.90,  -74.00,  0.7),
            ( 23.50,   5.80, 16.50, 16.50, 10.55,  -74.70,  -72.80,  -74.10,  0.6),
        ]

        st_o = []
        for y, xib, xob, xot, xit, zb, zto, zti, r in swan_out:
            if sign > 0:
                pts = [(xib, zb), (xob, zb), (xot, zto), (xit, zti)]
            else:
                pts = [(-xob, zb), (-xib, zb), (-xit, zti), (-xot, zto)]
            st_o.append((y, pts, r))

        st_i = []
        for y, xib, xob, xot, xit, zb, zto, zti, r in swan_in:
            if sign > 0:
                pts = [(xib, zb), (xob, zb), (xot, zto), (xit, zti)]
            else:
                pts = [(-xob, zb), (-xib, zb), (-xit, zti), (-xot, zto)]
            st_i.append((y, pts, r))

        ducts_outer.append(make_loft_along_y(st_o, ruled=True))
        ducts_inner.append(make_loft_along_y(st_i, ruled=True))
        ducts_inner.append(box(sign * 5.8, sign * 14.2, 18.2, 23.5, -74.75, -73.45))

        # Smoothly sculpted upper front mounting fairing (keeping Y >= 11.48 above Z=-58.00 to clear P01):
        x_in_k, x_out_k = (13.95, 22.45) if sign > 0 else (-22.45, -13.95)
        x_in_b, x_out_b = (12.00, 22.40) if sign > 0 else (-22.40, -12.00)
        cheek_loft = make_loft([
            rounded_polygon_wire_xy([(x_in_b,  9.50), (x_out_b,  9.50), (x_out_b, 20.50), (x_in_b, 20.50)], 2.2, -65.50),
            rounded_polygon_wire_xy([(x_in_k, 11.48), (x_out_k, 11.48), (x_out_k, 19.80), (x_in_k, 19.80)], 1.8, -58.50),
            rounded_polygon_wire_xy([(x_in_k, 11.48), (x_out_k, 11.48), (x_out_k, 19.60), (x_in_k, 19.60)], 1.6, -54.00),
            rounded_polygon_wire_xy([(x_in_k, 11.48), (x_out_k, 11.48), (x_out_k, 19.60), (x_in_k, 19.60)], 1.6, -48.60),
        ], ruled=True)
        ducts_outer.append(cheek_loft)

    # Smoothly tapered rear mounting flange to P21 at (±6.80, -30.20, Z = -61.50..-56.00):
    rear_fairing = make_loft([
        rounded_polygon_wire_xy([(-9.80, -35.50), (-9.80, -26.50), (9.80, -26.50), (9.80, -35.50)], 2.2, -61.50),
        rounded_polygon_wire_xy([(-9.80, -33.20), (-9.80, -27.20), (9.80, -27.20), (9.80, -33.20)], 2.2, -56.00),
    ], ruled=True)

    # Smooth MGN12H lower center index pad & front tie:
    cart_cradle = make_loft([
        rounded_polygon_wire_xy([(-11.50, -11.00), (11.50, -11.00), (11.50, 1.50), (-11.50, 1.50)], 2.0, -61.50),
        rounded_polygon_wire_xy([( -9.80,  -9.70), ( 9.80,  -9.70), ( 9.80, 0.30), ( -9.80, 0.30)], 1.5, -57.50),
        rounded_polygon_wire_xy([( -9.80,  -9.70), ( 9.80,  -9.70), ( 9.80, 0.30), ( -9.80, 0.30)], 1.5, -51.35),
    ], ruled=True)
    front_tie = rounded_box_xy(-12.00, 12.00, -1.50, 2.50, -70.80, -67.50, 1.0)

    body = fuse_all([collar_outer, *ducts_outer, rear_fairing, cart_cradle, front_tie])
    air = fuse_all([collar_inner, *ducts_inner])

    air_excl = fuse_all([
        box(-6.00, 6.00, -46.00, -15.80, -75.00, -60.30),
        box(-6.00, 6.00, -26.80, -15.80, -75.00, -57.00),
        cyl_z(-6.80, -30.20, -60.80, -55.50, 3.20),
        cyl_z( 6.80, -30.20, -60.80, -55.50, 3.20),
        cyl_z( 15.80,   8.50, -72.00, -66.50, 3.60),
        cyl_z(-15.80,   8.50, -72.00, -66.50, 3.60),
        cyl_z( 15.80, -11.50, -72.00, -66.50, 3.60),
        cyl_z(-15.80, -11.50, -72.00, -66.50, 3.60),
    ])
    air = cut_all(air, [air_excl])

    cutters = [
        air,
        box(-4.80, 4.80, -46.00, -16.80, -76.00, -61.50),
        box(-4.80, 4.80, -25.60, -16.80, -76.00, -57.00),
        box(-15.00, 15.00, -45.00, -33.20, -58.00, -50.00),
        cyl_z(-6.80, -30.20, -60.00, -55.80, 2.27),
        cyl_z( 6.80, -30.20, -60.00, -55.80, 2.27),
        box(-2.00, 2.00, -36.50, -26.50, -58.20, -53.00),
        cyl_y( 18.0, -52.78, 11.0, 15.95, 4.15),
        cyl_y(-18.0, -52.78, 11.0, 15.95, 4.15),
        cyl_y( 18.0, -52.78, 15.5, 20.0, 1.65),
        cyl_y(-18.0, -52.78, 15.5, 20.0, 1.65),
        cyl_y( 18.0, -52.78, 18.2, 20.5, 3.00),
        cyl_y(-18.0, -52.78, 18.2, 20.5, 3.00),
        # Flat seating pocket at Z=-70.80 for P23 + M3x4x4.6 heat-sets:
        box(-19.30, 19.30, -14.30, 13.30, -76.00, -70.80),
        cyl_z( 15.80,   8.50, -71.50, -66.80, 2.27),
        cyl_z(-15.80,   8.50, -71.50, -66.80, 2.27),
        cyl_z( 15.80, -11.50, -71.50, -66.80, 2.27),
        cyl_z(-15.80, -11.50, -71.50, -66.80, 2.27),
        box(-10.60, 10.60, 12.00, 50.00, -73.45, -50.00),
        cyl_z(0.0, 3.20, -76.00, -54.00, 9.55),
    ]
    body = cut_all(body, cutters)
    body = intersect_all(body, [box(-22.497, 22.497, -50.0, 30.0, -75.80, -48.60)])
    return body, air


if __name__ == "__main__":
    t0 = time.time()
    v26_meta = json.loads((WORK / "v26_meta.json").read_text())
    v26_raw = bva.load_brep_list(WORK / "v26_cache.brep")
    gantry_meta = json.loads((WORK / "gantry_meta.json").read_text())
    gantry_raw = bva.load_brep_list(WORK / "gantry_cache.brep")
    v26_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(v26_meta, v26_raw)}
    gantry_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(gantry_meta, gantry_raw)}

    p21_b, p21_a = build_smooth_p21()
    p22_b, p22_a = build_smooth_p22()
    p23_b = bva.build_p23_probe_mount()
    for name, s in [("P21", p21_b), ("P22", p22_b)]:
        vh = [n for n, (vs, _, _) in v26_by_name.items() if common_vol(s, vs) > 1e-3]
        gh = [n for n, (gs, _, _) in gantry_by_name.items() if common_vol(s, gs) > 1e-3]
        print(f"{name}: solids={bva.solid_count(s)} shells={bva.shell_count(s)} vol={bva.vol_of(s):.1f} v26={vh} gan={gh}")
    print("P21-P22 overlap:", common_vol(p21_b, p22_b))
    print("P22-P23 overlap:", common_vol(p22_b, p23_b))
    print(f"Elapsed: {time.time()-t0:.2f}s")
