import json
import math
import time
from pathlib import Path
import cadquery as cq
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Compound, TopoDS_Shape, TopoDS
from OCP.BRep import BRep_Builder
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeCone, BRepPrimAPI_MakePrism
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Ax2, gp_Vec, gp_Trsf, gp_Pln
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_Transform, BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
)
from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet

t0 = time.time()
WORK = Path(__file__).resolve().parent

def load_brep_list(brep_path):
    comp = TopoDS_Compound()
    builder = BRep_Builder()
    BRepTools.Read_s(comp, str(brep_path), builder)
    exp = TopExp_Explorer(comp, TopAbs_SOLID)
    solids = []
    while exp.More():
        s = exp.Current()
        bbox = Bnd_Box()
        BRepBndLib.Add_s(s, bbox)
        solids.append((s, bbox.Get()))
        exp.Next()
    return solids

v26_meta = json.loads((WORK / "v26_meta.json").read_text())
v26_raw = load_brep_list(WORK / "v26_cache.brep")
gantry_meta = json.loads((WORK / "gantry_meta.json").read_text())
gantry_raw = load_brep_list(WORK / "gantry_cache.brep")

v26_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(v26_meta, v26_raw)}
gantry_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(gantry_meta, gantry_raw)}

from OCP.BRepMesh import BRepMesh_IncrementalMesh

def bbox_of(shape):
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    return bbox.Get()

def exact_bbox_of(shape):
    BRepMesh_IncrementalMesh(shape, 0.05, False, 0.1, True)
    bbox = Bnd_Box()
    bbox.SetGap(0.0)
    BRepBndLib.Add_s(shape, bbox, True)
    return bbox.Get()




def vol_of(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return max(0.0, props.Mass())

def solid_count(shape):
    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    c = 0
    while exp.More():
        c += 1
        exp.Next()
    return c

def shell_count(shape):
    exp = TopExp_Explorer(shape, TopAbs_SHELL)
    c = 0
    while exp.More():
        c += 1
        exp.Next()
    return c

def box(x0, x1, y0, y1, z0, z1):
    return BRepPrimAPI_MakeBox(gp_Pnt(min(x0,x1), min(y0,y1), min(z0,z1)), gp_Pnt(max(x0,x1), max(y0,y1), max(z0,z1))).Shape()

def cyl_z(x, y, z0, z1, r):
    zmin, zmax = min(z0, z1), max(z0, z1)
    ax = gp_Ax2(gp_Pnt(x, y, zmin), gp_Dir(0, 0, 1))
    return BRepPrimAPI_MakeCylinder(ax, r, zmax - zmin).Shape()

def cyl_y(x, z, y0, y1, r):
    ymin, ymax = min(y0, y1), max(y0, y1)
    ax = gp_Ax2(gp_Pnt(x, ymin, z), gp_Dir(0, 1, 0))
    return BRepPrimAPI_MakeCylinder(ax, r, ymax - ymin).Shape()

def cyl_x(y, z, x0, x1, r):
    xmin, xmax = min(x0, x1), max(x0, x1)
    ax = gp_Ax2(gp_Pnt(xmin, y, z), gp_Dir(1, 0, 0))
    return BRepPrimAPI_MakeCylinder(ax, r, xmax - xmin).Shape()

def fuse_all(shapes):
    res = shapes[0]
    for s in shapes[1:]:
        f = BRepAlgoAPI_Fuse(res, s)
        f.Build()
        res = f.Shape()
    return res

def cut_all(base, cutters):
    res = base
    for c in cutters:
        op = BRepAlgoAPI_Cut(res, c)
        op.Build()
        res = op.Shape()
    return res

def common_vol(s1, s2):
    b1, b2 = bbox_of(s1), bbox_of(s2)
    if b1[3] < b2[0] or b2[3] < b1[0] or b1[4] < b2[1] or b2[4] < b1[1] or b1[5] < b2[2] or b2[5] < b1[2]:
        return 0.0
    op = BRepAlgoAPI_Common(s1, s2)
    if not op.IsDone():
        return 0.0
    return vol_of(op.Shape())

def rounded_polygon_wire_xy(vertices, radius, z):
    n = len(vertices)
    arcs = []
    for i, v in enumerate(vertices):
        prev_v = vertices[i - 1]
        next_v = vertices[(i + 1) % n]
        l1 = math.dist(v, prev_v)
        l2 = math.dist(v, next_v)
        u1 = ((prev_v[0] - v[0]) / l1, (prev_v[1] - v[1]) / l1)
        u2 = ((next_v[0] - v[0]) / l2, (next_v[1] - v[1]) / l2)
        dot = max(-1.0, min(1.0, u1[0]*u2[0] + u1[1]*u2[1]))
        theta = math.acos(dot)
        if radius <= 1e-6 or abs(theta - math.pi) < 1e-6:
            arcs.append({"entry": v, "exit": v, "mid": None})
            continue
        tan_len = radius / math.tan(theta / 2.0)
        bx, by = u1[0] + u2[0], u1[1] + u2[1]
        bl = math.hypot(bx, by)
        cx = v[0] + (radius / math.sin(theta / 2.0)) * (bx / bl)
        cy = v[1] + (radius / math.sin(theta / 2.0)) * (by / bl)
        entry = (v[0] + tan_len * u1[0], v[1] + tan_len * u1[1])
        exit_pt = (v[0] + tan_len * u2[0], v[1] + tan_len * u2[1])
        mid = (cx - radius * (bx / bl), cy - radius * (by / bl))
        arcs.append({"entry": entry, "exit": exit_pt, "mid": mid})

    wb = BRepBuilderAPI_MakeWire()
    for i in range(n):
        row = arcs[i]
        nxt = arcs[(i + 1) % n]
        if row["mid"] is not None:
            p1 = gp_Pnt(row["entry"][0], row["entry"][1], z)
            pm = gp_Pnt(row["mid"][0], row["mid"][1], z)
            p2 = gp_Pnt(row["exit"][0], row["exit"][1], z)
            arc = GC_MakeArcOfCircle(p1, pm, p2).Value()
            wb.Add(BRepBuilderAPI_MakeEdge(arc).Edge())
        p_start = gp_Pnt(row["exit"][0], row["exit"][1], z)
        p_end = gp_Pnt(nxt["entry"][0], nxt["entry"][1], z)
        if p_start.Distance(p_end) > 1e-5:
            seg = GC_MakeSegment(p_start, p_end).Value()
            wb.Add(BRepBuilderAPI_MakeEdge(seg).Edge())
    return wb.Wire()

def prism_xy_rounded(vertices, radius, z0, z1):
    zmin, zmax = min(z0, z1), max(z0, z1)
    wire = rounded_polygon_wire_xy(vertices, radius, zmin)
    face = BRepBuilderAPI_MakeFace(wire, True).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, zmax - zmin)).Shape()

def corridor_vertices(clearance=0.0, wall=0.0, width=44.994):
    # In v26: rear XY joint plane is Y = -43.20, X-beam rear plane is Y = -32.70
    # 45-deg corner chamfers from Body8/Body9 have |X| - Y <= 62.70
    half = width / 2.0 - wall
    rear = -43.20 + clearance + wall
    front = -32.70 - clearance - wall
    diag = 62.70 - math.sqrt(2.0) * (clearance + wall)
    shoulder = diag + rear
    side_rear = half - diag
    return [
        (-half, front),
        (-half, side_rear),
        (-shoulder, rear),
        (shoulder, rear),
        (half, side_rear),
        (half, front)
    ]

# Verify rear corridor prism against gantry keepouts:
outer_verts = corridor_vertices(clearance=0.5, wall=0.0)
inner_verts = corridor_vertices(clearance=0.5, wall=1.2)
mid_outer_conduit = prism_xy_rounded(outer_verts, 1.8, -58.280, -17.780)
mid_inner_air = prism_xy_rounded(inner_verts, 0.6, -58.280, -17.780)

air_area = vol_of(mid_inner_air) / (-17.780 - (-58.280))
print(f"Rear corridor inner air area: {air_area:.2f} mm2 (height 40.50 mm)")
g_hits = []
for gname, (gs, _, _) in gantry_by_name.items():
    v = common_vol(mid_outer_conduit, gs)
    if v > 1e-3:
        g_hits.append((gname, round(v, 3)))
def circle_like_6vert(cx, cy, rx, ry):
    # 6-vertex octagon-like convex polygon matching corridor_vertices topology (6 vertices)
    # Vertices ordered: (-rx, front), (-rx, side_rear), (-shoulder, rear), (shoulder, rear), (rx, side_rear), (rx, front)
    dx = rx * 0.55
    dy = ry * 0.45
    return [
        (cx - rx, cy + ry),
        (cx - rx, cy - ry + dy),
        (cx - rx + dx, cy - ry),
        (cx + rx - dx, cy - ry),
        (cx + rx, cy - ry + dy),
        (cx + rx, cy + ry),
    ]

def make_loft(wires, ruled=False):
    loft = BRepOffsetAPI_ThruSections(True, ruled, 1e-4)
    for w in wires:
        loft.AddWire(w)
    loft.Build()
    return loft.Shape()

def build_p20_inlet():
    z_split = -17.780
    # Use ruled=True across closely-spaced smooth stations to eliminate cubic spline overshoot outside [-22.5, 22.5]
    stations_out = [
        (z_split, corridor_vertices(0.5, 0.0), 1.8),
        (-15.500, corridor_vertices(0.5, 0.0), 1.8),
        (-11.500, circle_like_6vert(0.0, -39.5, 15.8, 6.0), 2.4),
        (-6.000,  circle_like_6vert(0.0, -42.0, 14.5, 8.2), 3.6),
        ( 2.000,  circle_like_6vert(0.0, -44.2, 13.2, 10.8), 4.5),
        (12.000,  circle_like_6vert(0.0, -45.5, 12.5, 12.5), 5.0),
    ]
    stations_in = [
        (z_split - 0.5, corridor_vertices(0.5, 1.2), 0.6),
        (-15.500, corridor_vertices(0.5, 1.2), 0.6),
        (-11.500, circle_like_6vert(0.0, -39.5, 14.4, 4.6), 1.4),
        (-6.000,  circle_like_6vert(0.0, -42.0, 13.1, 6.8), 2.4),
        ( 2.000,  circle_like_6vert(0.0, -44.2, 11.8, 9.4), 3.5),
        (12.500,  circle_like_6vert(0.0, -45.5, 11.0, 11.0), 4.4),
    ]
    outer_loft = make_loft([rounded_polygon_wire_xy(v, r, z) for z, v, r in stations_out], ruled=True)
    inner_loft = make_loft([rounded_polygon_wire_xy(v, r, z) for z, v, r in stations_in], ruled=True)

    spigot_base = cyl_z(0.0, -45.5, 10.0, 28.0, 12.5)
    spigot_bead = BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0.0, -45.5, 26.5), gp_Dir(0, 0, 1)), 12.5, 13.0, 1.5).Shape()
    spigot_tip = BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0.0, -45.5, 28.0), gp_Dir(0, 0, 1)), 13.0, 12.3, 2.0).Shape()
    spigot_bore = cyl_z(0.0, -45.5, 9.5, 31.0, 11.0)

    # Dry mounting lugs at (X = ±5.0, Y = -30.5, Z = -17.78..-14.20) — sits below EBB42 (Z >= -13.50)!
    lug_l = cyl_z(-5.0, -30.5, z_split, -14.20, 3.8)
    lug_r = cyl_z( 5.0, -30.5, z_split, -14.20, 3.8)
    lug_web = box(-8.8, 8.8, -35.0, -30.5, z_split, -14.20)

    body = fuse_all([outer_loft, spigot_base, spigot_bead, spigot_tip, lug_l, lug_r, lug_web])
    body = cut_all(body, [
        box(-50, 50, -100, 50, -50, z_split),
        inner_loft,
        spigot_bore,
        cyl_z(-5.0, -30.5, z_split - 1.0, -10.0, 1.65),
        cyl_z( 5.0, -30.5, z_split - 1.0, -10.0, 1.65),
        cyl_z(-5.0, -30.5, -15.6, 35.0, 2.9),
        cyl_z( 5.0, -30.5, -15.6, 35.0, 2.9),
    ])

    air = fuse_all([
        cut_all(inner_loft, [box(-50, 50, -100, 50, -50, z_split), box(-50, 50, -100, 50, 12.0, 50)]),
        cyl_z(0.0, -45.5, 11.5, 30.0, 11.0)
    ])
    return body, air

def build_p21_mid():
    z_top = -17.780
    z_bot = -58.280
    conduit_outer = prism_xy_rounded(corridor_vertices(0.5, 0.0), 1.8, z_bot, z_top)
    conduit_inner = prism_xy_rounded(corridor_vertices(0.5, 1.2), 0.6, z_bot - 1.0, z_top + 1.0)

    # Upper dry lugs at (X = ±5.0, Y = -30.5, Z = -24.20..-17.78) + central bridge above X-beam (Z = -27.779)
    up_lug_l = cyl_z(-5.0, -30.5, -24.20, z_top, 3.8)
    up_lug_r = cyl_z( 5.0, -30.5, -24.20, z_top, 3.8)
    # Central bridge arm through X in [-9.2, 9.2] (clearing Body1/Body2 at |X|>=10.0 and Body12 at Z<=-27.779)
    up_bridge = box(-9.2, 9.2, -34.5, 0.30, -24.20, -18.40)

    # Upper carriage saddle in front of Body1/Body2 (Y in [-9.70, 0.30], resting on MONO_CART_MGN12H Z=-24.279 and P01 Y=0.30)
    up_saddle = box(-21.0, 21.0, -9.70, 0.30, -24.20, -18.40)

    # Lower structural arms below Body1/Body2 (Z_min = -57.7794 -> use Z_max = -58.280 in Y = -33.15..-12.1)
    lo_arm_l = box( 13.20, 22.49, -33.15, -12.10, -62.50, z_bot)
    lo_arm_r = box(-22.49, -13.20, -33.15, -12.10, -62.50, z_bot)
    # Place rear cross-tie in front of P22's rear collar (Y = -33.20), at Y = -33.15..-28.50,
    # and connect it up to conduit_outer's front wall (Y = -33.20) in the central gantry window X in [-9.20, 9.20], Z in [-62.50, -53.00]:
    lo_rear_tie = box(-22.49, 22.49, -33.15, -28.50, -62.50, z_bot)
    lo_conduit_gusset_up = box(-9.20, 9.20, -34.20, -28.50, z_bot, -53.00)
    lo_conduit_gusset_dn = box(-9.20, 9.20, -33.15, -28.50, -62.50, -53.00)





    # Lower carriage blocks in front of Y = -12.10 (under MONO_CART_MGN12H Z = -51.279, against P01 Y = 0.30)
    lo_cart_l = box( 11.50, 22.49, -12.10, 0.30, -62.50, -51.35)
    lo_cart_r = box(-22.49, -11.50, -12.10, 0.30, -62.50, -51.35)
    # Central cross-tie directly under MONO_CART_MGN12H at Z = -54.20..-51.35 (above Beacon 20mm keepout Z = -54.52!)
    lo_cart_tie = box(-12.00, 12.00, -9.70, 0.30, -54.20, -51.35)

    # Forward side arms extending to P01's lower front accessory bosses at (X = ±18.00, Z = -52.780, Y = 15.90)
    # Under P01 bottom (Z = -57.279):
    fwd_under_l = box( 12.50, 22.49, 0.30, 19.50, -62.50, -57.35)
    fwd_under_r = box(-22.49, -12.50, 0.30, 19.50, -62.50, -57.35)
    # Bosses/cheeks at Y = 9.50..19.50 wrapping P01's R4.0 bosses at (±18.0, -52.78, Y=11.4..15.9):
    fwd_cheek_l = box( 13.95, 22.49, 9.50, 19.50, -62.50, -48.80)
    fwd_cheek_r = box(-22.49, -13.95, 9.50, 19.50, -62.50, -48.80)

    body = fuse_all([
        conduit_outer, up_lug_l, up_lug_r, up_bridge, up_saddle,
        lo_arm_l, lo_arm_r, lo_rear_tie, lo_conduit_gusset_up, lo_conduit_gusset_dn,
        lo_cart_l, lo_cart_r, lo_cart_tie,
        fwd_under_l, fwd_under_r, fwd_cheek_l, fwd_cheek_r
    ])



    # Subtract air passage, P01 boss sockets, fastener bores, and dry side wire channels:
    cutters = [
        conduit_inner,
        # Upper lug M3x3x4.6 heat-set pockets (Z = -21.30..-17.78, R = 2.27) and M3 clearance (R = 1.65)
        cyl_z(-5.0, -30.5, -21.30, z_top + 0.5, 2.27),
        cyl_z( 5.0, -30.5, -21.30, z_top + 0.5, 2.27),
        cyl_z(-5.0, -30.5, -25.00, -21.20, 1.65),
        cyl_z( 5.0, -30.5, -25.00, -21.20, 1.65),

        # P01 lower front boss sockets (R = 4.15 mm for Y = 9.0..15.95 at X = ±18.0, Z = -52.78) + P01 spine clearance (Y <= 11.45, Z >= -57.35)
        box(-23.0, 23.0, 0.25, 11.48, -57.35, -48.0),
        cyl_y( 18.0, -52.78, 11.0, 15.95, 4.15),
        cyl_y(-18.0, -52.78, 11.0, 15.95, 4.15),
        # M3 through-holes (R = 1.65) and counterbores (R = 3.0) at (X = ±18.0, Z = -52.78, Y = 15.90..19.50)
        cyl_y( 18.0, -52.78, 15.5, 20.0, 1.65),
        cyl_y(-18.0, -52.78, 15.5, 20.0, 1.65),
        cyl_y( 18.0, -52.78, 18.2, 20.5, 3.00),
        cyl_y(-18.0, -52.78, 18.2, 20.5, 3.00),
        # Horizontal heat-set pockets for P22 (Lower Plenum) at (X = ±12.0, Z = -60.40, Y = -12.10..-8.00, R = 2.27)
        cyl_y( 12.0, -60.40, -12.20, -8.00, 2.27),
        cyl_y(-12.0, -60.40, -12.20, -8.00, 2.27),

        # Vertical heat-set pockets for P23 (Probe Bridge) at (X = ±15.80, Y = -4.50, Z = -62.60..-58.00) and (X = ±18.00, Y = 13.50, Z = -62.60..-58.00)
        cyl_z( 15.80, -4.50, -62.60, -58.00, 2.27),
        cyl_z(-15.80, -4.50, -62.60, -58.00, 2.27),
        cyl_z( 18.00, 13.50, -62.60, -58.00, 2.27),
        cyl_z(-18.00, 13.50, -62.60, -58.00, 2.27),
        # Dry side wire guide channels along X = ±21.2, Z = -60.4
        box( 20.20, 23.00, -35.60, 10.00, -61.60, -59.20),
        box(-23.00, -20.20, -35.60, 10.00, -61.60, -59.20),
    ]
    body = cut_all(body, cutters)
    return body, prism_xy_rounded(corridor_vertices(0.5, 1.2), 0.6, z_bot, z_top)

p20_body, p20_air = build_p20_inlet()
p21_body, p21_air = build_p21_mid()
for name, b in [("P20_Inlet", p20_body), ("P21_Mid", p21_body)]:
    vh = [(n, round(common_vol(b, s), 3)) for n, (s, _, _) in v26_by_name.items() if common_vol(b, s) > 1e-3]
    gh = [(n, round(common_vol(b, s), 3)) for n, (s, _, _) in gantry_by_name.items() if common_vol(b, s) > 1e-3]
    print(f"{name}: solids={solid_count(b)}, shells={shell_count(b)}, vol={vol_of(b):.1f} mm3, bbox={[round(v,2) for v in exact_bbox_of(b)]}")
    print(f"  {name} v26 hits: {vh}, gantry hits: {gh}")
def build_p22_lower_plenum():
    z_port = -58.280
    # 1. Rear intake collar below P21 port (Z = -69.20..-58.28, Y = -42.70..-33.20)
    collar_outer = prism_xy_rounded(corridor_vertices(0.5, 0.0), 1.8, -69.20, z_port)
    collar_inner = prism_xy_rounded(corridor_vertices(0.5, 1.2), 0.6, -68.00, z_port + 0.5)

    # 2. Left (+X) and Right (-X) horizontal plenum ducts from Y = -35.50 to Y = +14.00 in Z = -69.20..-62.55
    ducts_outer = []
    ducts_inner = []
    for sign in (-1, 1):
        # Rear section (Y = -36.0..-11.5)
        x_in_0, x_out_0 = (5.70, 22.49) if sign > 0 else (-22.49, -5.70)
        ducts_outer.append(box(x_in_0, x_out_0, -36.00, -11.50, -69.20, -62.55))
        xi0, xi1 = (6.90, 21.29) if sign > 0 else (-21.29, -6.90)
        ducts_inner.append(box(xi0, xi1, -36.50, -11.00, -68.00, -63.75))

        # Mid section alongside probe bay (Y = -12.5..+14.5, |X| in [10.80, 22.49])
        x_in_1, x_out_1 = (10.80, 22.49) if sign > 0 else (-22.49, -10.80)
        ducts_outer.append(box(x_in_1, x_out_1, -12.50, 14.50, -69.20, -62.55))
        xi2, xi3 = (12.00, 21.29) if sign > 0 else (-21.29, -12.00)
        ducts_inner.append(box(xi2, xi3, -12.50, 14.00, -68.00, -63.75))

        # Transition drop beside Volcano heater block (Y = 12.6..24.5, |X| in [11.00, 22.49], dropping to Z = -75.80)
        w_drop_0 = rounded_polygon_wire_xy([
            (sign*11.00, 12.60), (sign*22.49, 12.60), (sign*22.49, 17.50), (sign*11.00, 17.50)
        ], 1.2, -62.55)
        w_drop_1 = rounded_polygon_wire_xy([
            (sign*11.00, 14.20), (sign*22.00, 14.20), (sign*22.00, 23.50), (sign*11.00, 23.50)
        ], 1.2, -71.50)
        w_drop_2 = rounded_polygon_wire_xy([
            (sign*7.50, 17.50), (sign*19.50, 16.50), (sign*19.50, 24.50), (sign*7.50, 23.50)
        ], 1.0, -75.80)
        ducts_outer.append(make_loft([w_drop_0, w_drop_1, w_drop_2], ruled=True))

        wi_drop_0 = rounded_polygon_wire_xy([
            (sign*12.20, 13.20), (sign*21.29, 13.20), (sign*21.29, 16.70), (sign*12.20, 16.70)
        ], 0.6, -63.75)
        wi_drop_1 = rounded_polygon_wire_xy([
            (sign*12.20, 15.20), (sign*20.80, 15.20), (sign*20.80, 22.50), (sign*12.20, 22.50)
        ], 0.6, -71.50)
        wi_drop_2 = rounded_polygon_wire_xy([
            (sign*7.00, 18.50), (sign*18.00, 17.50), (sign*18.00, 23.50), (sign*7.00, 22.50)
        ], 0.5, -74.60)
        ducts_inner.append(make_loft([wi_drop_0, wi_drop_1, wi_drop_2], ruled=True))

        # Jet exit opening cut through the inner wall at |X| = 7.0..12.0, Z = -74.8..-73.6 aimed at nozzle (0, 22.70, -78.88)
        jet_cut = box(sign*6.0, sign*14.0, 18.2, 23.2, -74.70, -73.60)
        ducts_inner.append(jet_cut)

        # Front mounting flange tab at (X = sign*9.5..13.15, Y = -14.80..-12.15, Z = -69.20..-58.30) to bolt into P21 at Z = -60.40
        flange = box(9.50 if sign > 0 else -13.15, 13.15 if sign > 0 else -9.50, -14.80, -12.15, -69.20, -58.30)
        ducts_outer.append(flange)

    # Cross-tie bridge between left and right ducts in front of GANTRY_Body40 (Y = -16.00..-12.15, X in [-11.00, +11.00], Z = -69.20..-65.50)
    # This joins the left and right lower plenum branches into ONE single rigid printable part while clearing GANTRY_Body40 (Y <= -17.20)!
    front_arch_tie = box(-11.00, 11.00, -16.00, -12.15, -69.20, -65.50)
    # Also join across the top of the rear intake port above the splitter slot (Z = -61.70..-58.28, Y = -42.70..-33.20):
    slot_roof_wall = box(-6.00, 6.00, -42.70, -33.20, -61.90, -60.50)

    body = fuse_all([collar_outer, *ducts_outer, front_arch_tie, slot_roof_wall])
    air = fuse_all([collar_inner, *ducts_inner])
    # Exclude the central splitter wall (X in [-5.70, 5.70], Z <= -60.50) from air so the rear slot is 100% sealed with >=1.2mm walls:
    air = cut_all(air, [box(-5.70, 5.70, -45.00, -11.00, -76.00, -60.50)])

    cutters = [
        air,
        # Rear service slot for GANTRY_Body40 (X in [-4.50, 4.50], Y in [-44.0, -16.20], Z in [-76.0, -61.70])
        box(-4.50, 4.50, -44.00, -16.20, -76.00, -61.70),
        box(-4.50, 4.50, -33.15, -16.20, -76.00, -57.00),
        # M3 mounting holes into P21 at (X = ±12.00, Z = -60.40, Y = -15.50..-12.00)
        cyl_y( 12.00, -60.40, -15.50, -12.00, 1.65),
        cyl_y(-12.00, -60.40, -15.50, -12.00, 1.65),
        # Vertical clearance holes at (X = ±15.80, Y = -4.50)
        cyl_z( 15.80, -4.50, -70.00, -62.00, 2.27),
        cyl_z(-15.80, -4.50, -70.00, -62.00, 2.27),
        # Heater block & tool withdrawal safety clearance (X in [-10.95, +10.95], Y >= 13.40, Z >= -73.50)
        box(-10.95, 10.95, 13.40, 50.00, -73.50, -50.00),
    ]
    body = cut_all(body, cutters)
    return body, air

def build_p23_probe_mount():
    z_seat = -74.520
    z_top = -69.250
    deck_verts = [
        (-19.20, -13.50), (19.20, -13.50), (19.20, 13.50), (-19.20, 13.50)
    ]
    deck = prism_xy_rounded(deck_verts, 2.0, z_seat, z_top)

    # Front thermal shield baffle at Y = 12.35..13.50 (0.17 mm in front of Beacon connector Y = 12.184, 0.70 mm behind Heater block Y = 14.20)
    baffle_base = box(-19.20, 19.20, 12.35, 13.50, z_seat, z_top)
    baffle_up   = box(-10.75, 10.75, 12.35, 13.50, z_top, -64.00)

    # Two stout vertical columns at |X| in [6.80, 10.75], Y in [3.50, 11.40], rising from -73.20 (above Beacon Body3 encapsulation Z = -73.42) to P01's bottom face (-57.30)!
    col_l = box( 6.80, 10.75, 3.50, 11.40, -73.20, -57.30)
    col_r = box(-10.75, -6.80, 3.50, 11.40, -73.20, -57.30)
    # Cross-arch joining the two columns above the Beacon USB connector (Z = -64.50..-57.30):
    col_arch = box(-10.75, 10.75, 3.50, 11.40, -64.50, -57.30)
    # Side bridge webs at Y in [3.50, 13.50], Z in [-73.20, z_top] connecting col_l/col_r to the outer side rails |X| in [11.80, 19.20]:
    web_l = box( 6.80, 19.20, 3.50, 13.50, -73.20, z_top)
    web_r = box(-19.20, -6.80, 3.50, 13.50, -73.20, z_top)

    body = fuse_all([deck, baffle_base, baffle_up, col_l, col_r, col_arch, web_l, web_r])

    cutters = [
        # Central coil window (R = 9.60 mm at X=0, Y=-6.70)
        cyl_z(0.0, -6.70, -75.00, -54.00, 9.60),
        # PCB component/connector bay in the rear/mid (X in [-11.80, 11.80], Y in [-11.50, 3.50])
        box(-11.80, 11.80, -11.50, 3.50, z_seat - 1.0, z_top + 1.0),
        # Relieve bottom 1.32 mm (Z = z_seat - 0.5 .. -73.20) for Beacon's full-width 1.10 mm encapsulation block Body3:
        # In rot_z = 180 (Primary), Body3 is at Y in [4.54, 12.30], X in [-19.0, 19.0], Z in [-74.52, -73.42]:
        box(-19.50, 19.50, 4.30, 12.35, z_seat - 0.5, -73.20),
        # Central USB connector bay in the front (X in [-6.50, 6.50], Y in [3.00, 12.35], Z in [z_seat - 1.0, -64.50])
        box(-6.50, 6.50, 3.00, 12.35, z_seat - 1.0, -64.50),
        # Rear connector clearance notch (X in [-6.00, 6.00], Y in [-14.00, -10.00])
        box(-6.00, 6.00, -14.00, -10.00, z_seat - 1.0, z_top + 1.0),
        # Dual-position M3 sensor mounting holes at X = ±15.800:
        # 1) Primary Monolith position: Y = -3.200 (R = 1.65 through-bore + captive M3 nut slot Z = -72.50..-70.10)
        cyl_z( 15.80, -3.20, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80, -3.20, z_seat - 1.0, z_top + 1.0, 1.65),
        box( 12.80, 19.50, -6.05, -0.35, -72.50, -70.10),
        box(-19.50, -12.80, -6.05, -0.35, -72.50, -70.10),
        # 2) Secondary Standard position: Y = -9.500 (R = 1.65 through-bore + captive M3 nut slot Z = -72.50..-70.10)
        cyl_z( 15.80, -9.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80, -9.50, z_seat - 1.0, z_top + 1.0, 1.65),
        box( 12.80, 19.50, -12.35, -6.65, -72.50, -70.10),
        box(-19.50, -12.80, -12.35, -6.65, -72.50, -70.10),
        # Bridge-to-P22 vertical M3 mounting screw counterbores at (X = ±15.80, Y = +8.50)
        cyl_z( 15.80,  8.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80,  8.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z( 15.80,  8.50, z_seat - 1.0, -71.50, 3.00),
        cyl_z(-15.80,  8.50, z_seat - 1.0, -71.50, 3.00),
    ]
    body = cut_all(body, cutters)
    return body

def build_p24_ebb42_mount():
    # Center EBB42 at (X_c = -1.248, Z_c = 6.500), with PCB back face at Y_pcb_back = -21.200 mm!
    # In EBB42 STEP, PCB is Z_local in [-0.624, 0.0], backside pins/SMDs reach Z_local = -3.78.
    # When we place EBB42 with Z_local = 0 at Y = -21.824, the PCB back face (Z_local = -0.624) rests on our 4 standoff bosses at Y = -21.200!
    # And backside pins (Z_local in [-3.78, -0.624]) occupy Y in [-21.200, -18.040]!
    # So our 4 standoff bosses reach Y = -21.200, while our perimeter frame bars sit at Y in [-18.00, -14.50] (outside the motor R=18.65 or recessed in front of the backside pins)!
    mx, mz = -1.248, 4.251
    eb_x, eb_z = -1.248, 6.500
    corners = [
        (eb_x - 15.5, eb_z + 15.5), # TR: (-16.748, 22.000)
        (eb_x + 15.5, eb_z + 15.5), # TL: ( 14.252, 22.000)
        (eb_x + 15.5, eb_z - 15.5), # BL: ( 14.252, -9.000)
        (eb_x - 15.5, eb_z - 15.5), # BR: (-16.748, -9.000)
    ]
    y_standoff = -21.20
    # 4 cylindrical standoff posts (R = 3.20 mm at Y = -21.20..-17.30 so BR clears AHG lead exit at Y = -16.95!)
    bosses = [cyl_y(cx, cz, y_standoff, -17.30, 3.20) for cx, cz in corners]

    bar_left  = box( 12.00,  21.50, -18.00, -14.00, -16.80, 27.50)
    # Keep bar_right above Z = -4.80 (above AHG lead exit Z = -5.44) where Y > -17.30:
    bar_right = box(-21.80, -13.70, -18.00, -14.00,  -4.80, 48.70)
    # Bottom tie bar at Z = -16.80..-13.60 spanning Y = -21.20..-17.30:
    bar_bot_low = box(-20.00, 18.00, y_standoff, -17.30, -16.80, -13.60)
    # Connect BR (-16.75, -9.00) up to bar_right (-4.80) and down to bar_bot_low (-16.80) at Y = -21.20..-17.30:
    leg_br = box(-19.95, -13.55, y_standoff, -17.30, -15.50, -4.00)
    leg_bl = box( 11.05,  17.45, y_standoff, -17.20, -15.50, -9.00)

    # Top arch bars connecting TR (-16.75, 22.00) and TL (14.25, 22.00) into foot_ur and foot_ul:
    leg_tr = box(-19.95, -13.55, y_standoff, -14.00, 18.80, 25.20)
    leg_tl = box( 11.05,  17.45, y_standoff, -14.00, 18.80, 25.20)

    # 3 Structural Mounting Feet forward to P02's rear face (Y = -6.70), staying outside motor R = 18.65 mm and above gantry Z = -17.20!
    foot_ul = box(11.50, 21.50, -18.00, -6.70, 16.50, 27.50)
    foot_bl = box(11.50, 21.50, -18.00, -6.70, -16.80, -6.00)
    foot_ur = box(-21.80, -12.50, -18.00, -6.70, 16.50, 51.20)
    hook_ur = box(-20.50, -12.50, -12.00, -2.50, 48.70, 51.20)

    body = fuse_all([
        *bosses, bar_left, bar_right, bar_bot_low,
        leg_br, leg_bl, leg_tr, leg_tl,
        foot_ul, foot_bl, foot_ur, hook_ur
    ])

    cutters = [
        # LDO Pancake motor stator + flange clearance cylinder (R = 18.65 mm centered at (-1.248, 4.251), Y = -17.05..1.00)
        cyl_y(mx, mz, -17.05, 1.00, 18.65),
        # LDO Motor ears & ear screw heads at (-16.748, 19.750) and (14.252, -11.249) for Y = -16.80..0.50 (R = 3.10 access bore)
        cyl_y(-16.748,  19.750, -16.80, 0.50, 3.10),
        cyl_y( 14.252, -11.249, -16.80, 0.50, 3.10),
        # PLATE_M3x10_BUTTON screw at (17.25, 23.72, head at Y = -8.35..-6.70): R = 3.10 clearance pocket over head + R = 1.65 access hole
        cyl_y( 17.250,  23.720, -22.00, 0.50, 1.65),
        cyl_y( 17.250,  23.720,  -9.00, 0.50, 3.10),
        cyl_y( 17.250,  23.720, -22.00, -11.50, 3.10),
        # UPPER_RIGHT_SHARED_M3x35 at (-18.10, 41.72): R = 1.65 through-bore + R = 3.10 rear counterbore
        cyl_y(-18.100,  41.720, -22.00, 0.50, 1.65),
        cyl_y(-18.100,  41.720, -22.00, -10.50, 3.10),
        # 4x EBB42 M3x4x4.6 heat-set insert pockets (Y = -21.30..-17.00, R = 2.15):
        *(cyl_y(cx, cz, y_standoff - 0.2, -17.00, 2.15) for cx, cz in corners),
        # Preserve P02's 11.5 mm motor-entry notch (X in [-7.20, 4.70], Z in [21.20, 30.00], Y in [-17.10, 2.0]):
        box(-7.20, 4.70, -17.10, 2.00, 21.20, 30.00),
        # Umbilical zip-tie slots on the upper-right strain-relief tower (Z = 31.0 and Z = 36.5):
        box(-22.50, -12.00, -15.50, -13.50, 30.50, 32.50),
        box(-22.50, -12.00, -15.50, -13.50, 36.00, 38.00),
    ]
    body = cut_all(body, cutters)
    return body



p22_body, p22_air = build_p22_lower_plenum()
p23_body = build_p23_probe_mount()
p24_body = build_p24_ebb42_mount()


all_parts = [
    ("P20_Inlet", p20_body),
    ("P21_Mid", p21_body),
    ("P22_Lower", p22_body),
    ("P23_Probe", p23_body),
    ("P24_EBB42", p24_body),
]
for name, b in all_parts:
    vh = [(n, round(common_vol(b, s), 3)) for n, (s, _, _) in v26_by_name.items() if common_vol(b, s) > 1e-3]
    gh = [(n, round(common_vol(b, s), 3)) for n, (s, _, _) in gantry_by_name.items() if common_vol(b, s) > 1e-3]
    print(f"{name}: solids={solid_count(b)}, shells={shell_count(b)}, vol={vol_of(b):.1f} mm3, bbox={[round(v,2) for v in exact_bbox_of(b)]}")
    if solid_count(b) > 1:
        exp = TopExp_Explorer(b, TopAbs_SOLID)
        while exp.More():
            sub = exp.Current()
            print("   sub-solid:", round(vol_of(sub), 2), [round(v, 2) for v in exact_bbox_of(sub)])
            exp.Next()
    print(f"  {name} v26 hits: {vh}, gantry hits: {gh}")


# Also verify against installed Beacon RevH Normal, Cartographer V3 Flat Pack, and BTT EBB42 CAN V1.1!
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone

def load_step(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise RuntimeError(f"Failed {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    res = []
    while exp.More():
        res.append(exp.Current())
        exp.Next()
    return res

sensor_dir = Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files\compact_direct_cam\accessory_sources")
beacon_sols = load_step(sensor_dir / "Beacon_RevH_Assm_Normal.STEP")
# Place Beacon RevH Normal at Primary Monolith position: Y_holes = -3.20, rot_z = 180, Z_seat = -74.520 (so Y_coil = -6.70)
trsf_b_rot = gp_Trsf()
trsf_b_rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.pi)
trsf_b_pos = gp_Trsf()
trsf_b_pos.SetTranslation(gp_Vec(0.0, -6.70, -74.520))
trsf_beacon = trsf_b_pos.Multiplied(trsf_b_rot)

beacon_world = [BRepBuilderAPI_Transform(s, trsf_beacon, True).Shape() for s in beacon_sols]
beacon_bot_ko = beacon_world[0]
beacon_top_ko = beacon_world[1]
beacon_phys   = beacon_world[2:5]

# Check Beacon physical bodies against P20..P24:
b_part_hits = []
for pname, pb in all_parts:
    for idx_b, bs in enumerate(beacon_phys):
        v = common_vol(pb, bs)
        if v > 1e-3:
            b_part_hits.append((pname, f"Beacon_phys_{idx_b}", round(v, 3)))
    v_bot = common_vol(pb, beacon_bot_ko)
    if v_bot > 1e-3:
        b_part_hits.append((pname, "Beacon_bot_ko", round(v_bot, 3)))
print("Beacon vs P20..P24 physical/bottom-ko hits:", b_part_hits)

# Place BTT EBB42 CAN V1.1 on P24 at (X_c = -1.248, Y_pcb = -21.20, Z_c = 4.251, rot_y = 270 deg)
ebb_raw = load_brep_list(WORK / "ebb42_cache.brep")
t_center = gp_Trsf()
t_center.SetTranslation(gp_Vec(-20.0, -20.0, 0.0))
t_rx90 = gp_Trsf()
t_rx90.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2.0)
t_ry270 = gp_Trsf()
t_ry270.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.radians(270))
t_pos_ebb = gp_Trsf()
# Place EBB42 so its PCB back face (Z_local = -0.624) sits at Y = -21.200 mm (so Z_local = 0 is at Y = -21.824 mm), centered at (-1.248, 6.500):
t_pos_ebb.SetTranslation(gp_Vec(-1.248, -21.824, 6.500))
trsf_ebb = t_pos_ebb.Multiplied(t_ry270.Multiplied(t_rx90.Multiplied(t_center)))


ebb_world = [BRepBuilderAPI_Transform(s, trsf_ebb, True).Shape() for s, _ in ebb_raw]
ebb_part_hits = []
for pname, pb in all_parts:
    tot_v = 0.0
    for es in ebb_world:
        tot_v += common_vol(pb, es)
    if tot_v > 1e-3:
        ebb_part_hits.append((pname, round(tot_v, 3)))
print("EBB42 vs P20..P24 hits:", ebb_part_hits)





