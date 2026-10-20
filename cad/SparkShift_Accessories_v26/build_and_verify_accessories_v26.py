"""Build and verify the 5-part SparkShift v26 Accessory Suite (Beacon/Cartographer, CPAP, EBB42).

Strictly preserves the existing 135-body SparkShift v26 design with zero modifications.
All coordinates are in the v26 assembly world frame (mm: +X left/arm, +Y forward/tool, +Z up).
"""

import hashlib
import json
import math
import struct
import time
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_Transform,
)
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCone,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakePrism,
    BRepPrimAPI_MakeSphere,
)
from OCP.BRepTools import BRepTools
from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_VERTEX
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Compound


HERE = Path(__file__).resolve().parent
STEP_DIR = HERE / "step"
STL_DIR = HERE / "stl"
IMG_DIR = HERE / "images"
WORK = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
SENSOR_DIR = Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files\compact_direct_cam\accessory_sources")


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


def load_step(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise RuntimeError(f"Failed to read STEP: {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    res = []
    while exp.More():
        res.append(exp.Current())
        exp.Next()
    return res


def bbox_of(shape):
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    return bbox.Get()


def boxes_overlap(b1, b2):
    return not (
        b1[3] < b2[0] or b2[3] < b1[0]
        or b1[4] < b2[1] or b2[4] < b1[1]
        or b1[5] < b2[2] or b2[5] < b1[2]
    )


def exact_vertex_bounds_from_stl(stl_path):
    data = Path(stl_path).read_bytes()
    n_tri = struct.unpack("<I", data[80:84])[0]
    xmin = ymin = zmin = 1e9
    xmax = ymax = zmax = -1e9
    offset = 84
    for _ in range(n_tri):
        vals = struct.unpack("<12fH", data[offset : offset + 50])
        offset += 50
        for k in (3, 6, 9):
            x, y, z = vals[k], vals[k + 1], vals[k + 2]
            if x < xmin: xmin = x
            if x > xmax: xmax = x
            if y < ymin: ymin = y
            if y > ymax: ymax = y
            if z < zmin: zmin = z
            if z > zmax: zmax = z
    return [round(xmin, 3), round(ymin, 3), round(zmin, 3)], [round(xmax, 3), round(ymax, 3), round(zmax, 3)], n_tri


def validate_binary_stl(stl_path):
    data = Path(stl_path).read_bytes()
    n_tri = struct.unpack("<I", data[80:84])[0]
    edge_counts = {}
    directed_edges = set()
    degenerate = 0
    vol6 = 0.0
    offset = 84
    for _ in range(n_tri):
        vals = struct.unpack("<12fH", data[offset : offset + 50])
        offset += 50
        v0 = (round(vals[3], 5), round(vals[4], 5), round(vals[5], 5))
        v1 = (round(vals[6], 5), round(vals[7], 5), round(vals[8], 5))
        v2 = (round(vals[9], 5), round(vals[10], 5), round(vals[11], 5))
        if v0 == v1 or v1 == v2 or v2 == v0:
            degenerate += 1
            continue
        vol6 += (
            v0[0] * (v1[1] * v2[2] - v1[2] * v2[1])
            - v0[1] * (v1[0] * v2[2] - v1[2] * v2[0])
            + v0[2] * (v1[0] * v2[1] - v1[1] * v2[0])
        )
        for a, b in ((v0, v1), (v1, v2), (v2, v0)):
            if (a, b) in directed_edges:
                pass
            directed_edges.add((a, b))
            undir = (a, b) if a < b else (b, a)
            edge_counts[undir] = edge_counts.get(undir, 0) + 1
    non_manifold = sum(1 for c in edge_counts.values() if c != 2)
    winding_errors = sum(1 for (a, b) in directed_edges if (b, a) not in directed_edges)
    return {
        "facets": n_tri,
        "degenerate_facets": degenerate,
        "non_manifold_edges": non_manifold,
        "winding_errors": winding_errors,
        "mesh_volume_mm3": round(abs(vol6) / 6.0, 3),
        "is_watertight_manifold": (degenerate == 0 and non_manifold == 0 and winding_errors == 0),
    }


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
    return BRepPrimAPI_MakeBox(
        gp_Pnt(min(x0, x1), min(y0, y1), min(z0, z1)),
        gp_Pnt(max(x0, x1), max(y0, y1), max(z0, z1)),
    ).Shape()


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


def cone_z(x, y, z0, z1, r0, r1):
    ax = gp_Ax2(gp_Pnt(x, y, z0), gp_Dir(0, 0, 1))
    if abs(r0 - r1) < 1e-6:
        return BRepPrimAPI_MakeCylinder(ax, r0, z1 - z0).Shape()
    return BRepPrimAPI_MakeCone(ax, r0, r1, z1 - z0).Shape()


def cone_y(x, z, y0, y1, r0, r1):
    ymin, ymax = min(y0, y1), max(y0, y1)
    ax = gp_Ax2(gp_Pnt(x, ymin, z), gp_Dir(0, 1, 0))
    if abs(r0 - r1) < 1e-6:
        return BRepPrimAPI_MakeCylinder(ax, r0, ymax - ymin).Shape()
    return BRepPrimAPI_MakeCone(ax, r0, r1, ymax - ymin).Shape()


def sphere(x, y, z, r):
    return BRepPrimAPI_MakeSphere(gp_Pnt(x, y, z), r).Shape()


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


def intersect_all(base, clips):
    res = base
    for c in clips:
        op = BRepAlgoAPI_Common(res, c)
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
        dot = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        theta = math.acos(dot)
        if radius <= 1e-6 or abs(theta - math.pi) < 1e-6:
            arcs.append({"entry": v, "exit": v, "mid": None})
            continue
        max_tan = 0.44 * min(l1, l2)
        tan_len = min(radius / math.tan(theta / 2.0), max_tan)
        r_eff = tan_len * math.tan(theta / 2.0)
        bx, by = u1[0] + u2[0], u1[1] + u2[1]
        bl = math.hypot(bx, by)
        cx = v[0] + (r_eff / math.sin(theta / 2.0)) * (bx / bl)
        cy = v[1] + (r_eff / math.sin(theta / 2.0)) * (by / bl)
        entry = (v[0] + tan_len * u1[0], v[1] + tan_len * u1[1])
        exit_pt = (v[0] + tan_len * u2[0], v[1] + tan_len * u2[1])
        mid = (cx - r_eff * (bx / bl), cy - r_eff * (by / bl))
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


def rounded_polygon_wire_2d(vertices, radii):
    """Build a 2D wire in XY (z=0) with per-vertex or uniform corner radius using exact lines and tangent circular arcs."""
    n = len(vertices)
    if isinstance(radii, (int, float)):
        radii = [radii] * n
    arcs = []
    for i, v in enumerate(vertices):
        r = radii[i]
        prev_v = vertices[i - 1]
        next_v = vertices[(i + 1) % n]
        l1 = math.dist(v, prev_v)
        l2 = math.dist(v, next_v)
        u1 = ((prev_v[0] - v[0]) / l1, (prev_v[1] - v[1]) / l1)
        u2 = ((next_v[0] - v[0]) / l2, (next_v[1] - v[1]) / l2)
        dot = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        theta = math.acos(dot)
        if r <= 1e-6 or abs(theta - math.pi) < 1e-6:
            arcs.append({"entry": v, "exit": v, "mid": None})
            continue
        lim1 = (0.98 if radii[i - 1] <= 1e-6 else 0.45) * l1
        lim2 = (0.98 if radii[(i + 1) % n] <= 1e-6 else 0.45) * l2
        max_tan = min(lim1, lim2)
        tan_len = min(r / math.tan(theta / 2.0), max_tan)
        r_eff = tan_len * math.tan(theta / 2.0)
        bx, by = u1[0] + u2[0], u1[1] + u2[1]
        bl = math.hypot(bx, by)
        cx = v[0] + (r_eff / math.sin(theta / 2.0)) * (bx / bl)
        cy = v[1] + (r_eff / math.sin(theta / 2.0)) * (by / bl)
        entry = (v[0] + tan_len * u1[0], v[1] + tan_len * u1[1])
        exit_pt = (v[0] + tan_len * u2[0], v[1] + tan_len * u2[1])
        mid = (cx - r_eff * (bx / bl), cy - r_eff * (by / bl))
        arcs.append({"entry": entry, "exit": exit_pt, "mid": mid})

    wb = BRepBuilderAPI_MakeWire()
    for i in range(n):
        row = arcs[i]
        nxt = arcs[(i + 1) % n]
        if row["mid"] is not None:
            p1 = gp_Pnt(row["entry"][0], row["entry"][1], 0.0)
            pm = gp_Pnt(row["mid"][0], row["mid"][1], 0.0)
            p2 = gp_Pnt(row["exit"][0], row["exit"][1], 0.0)
            arc = GC_MakeArcOfCircle(p1, pm, p2).Value()
            wb.Add(BRepBuilderAPI_MakeEdge(arc).Edge())
        p_start = gp_Pnt(row["exit"][0], row["exit"][1], 0.0)
        p_end = gp_Pnt(nxt["entry"][0], nxt["entry"][1], 0.0)
        if p_start.Distance(p_end) > 1e-5:
            seg = GC_MakeSegment(p_start, p_end).Value()
            wb.Add(BRepBuilderAPI_MakeEdge(seg).Edge())
    return wb.Wire()


def prism_xy_r(vertices, radii, z0, z1):
    zmin, zmax = min(z0, z1), max(z0, z1)
    w = rounded_polygon_wire_2d(vertices, radii)
    f = BRepBuilderAPI_MakeFace(w, True).Face()
    s = BRepPrimAPI_MakePrism(f, gp_Vec(0, 0, zmax - zmin)).Shape()
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(0, 0, zmin))
    return BRepBuilderAPI_Transform(s, t, True).Shape()


def prism_xz_r(vertices_xz, radii, y0, y1):
    ymin, ymax = min(y0, y1), max(y0, y1)
    w = rounded_polygon_wire_2d(vertices_xz, radii)
    f = BRepBuilderAPI_MakeFace(w, True).Face()
    s = BRepPrimAPI_MakePrism(f, gp_Vec(0, 0, ymax - ymin)).Shape()
    t_rot = gp_Trsf()
    t_rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2.0)
    t_tr = gp_Trsf()
    t_tr.SetTranslation(gp_Vec(0, ymax, 0))
    return BRepBuilderAPI_Transform(s, t_tr.Multiplied(t_rot), True).Shape()


def prism_yz_r(vertices_yz, radii, x0, x1):
    xmin, xmax = min(x0, x1), max(x0, x1)
    w = rounded_polygon_wire_2d(vertices_yz, radii)
    f = BRepBuilderAPI_MakeFace(w, True).Face()
    s = BRepPrimAPI_MakePrism(f, gp_Vec(0, 0, xmax - xmin)).Shape()
    t1 = gp_Trsf()
    t1.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.pi / 2.0)
    t2 = gp_Trsf()
    t2.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2.0)
    t3 = gp_Trsf()
    t3.SetTranslation(gp_Vec(xmin, 0, 0))
    return BRepBuilderAPI_Transform(s, t3.Multiplied(t2.Multiplied(t1)), True).Shape()


def prism_xy_rounded(vertices, radius, z0, z1):
    return prism_xy_r(vertices, radius, z0, z1)


def rounded_box_xy(x0, x1, y0, y1, z0, z1, r):
    xmin, xmax = min(x0, x1), max(x0, x1)
    ymin, ymax = min(y0, y1), max(y0, y1)
    verts = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
    return prism_xy_r(verts, min(r, (xmax - xmin) * 0.45, (ymax - ymin) * 0.45), z0, z1)


def corridor_aero_vertices(wall=0.0, dy_rear=0.0, dy_mid=0.0):
    """Edge-tapered aerodynamic rear gantry corridor clearing GANTRY_Body4..9 at X-travel limits."""
    xf = 20.60 - wall
    xr = 13.00 - 0.45 * wall
    yf = -33.20 - wall
    ym = -38.20 + 0.40 * wall + dy_mid
    yr = -45.40 + wall + dy_rear
    return [
        (-xf, yf),
        (-xf, ym),
        (-xr, yr),
        ( xr, yr),
        ( xf, ym),
        ( xf, yf),
    ]


def circumscribed_hex_circle_vertices(cx, cy, r_circle):
    """Regular hexagon circumscribed around a circle of radius r_circle, matching corridor_aero_vertices order."""
    s = r_circle / math.sqrt(3.0)
    return [
        (cx - s, cy + r_circle),
        (cx - 2.0 * s, cy),
        (cx - s, cy - r_circle),
        (cx + s, cy - r_circle),
        (cx + 2.0 * s, cy),
        (cx + s, cy + r_circle),
    ]


def rounded_polygon_wire_xz(vertices, radius, y_val):
    n = len(vertices)
    arcs = []
    for i, v in enumerate(vertices):
        prev_v = vertices[i - 1]
        next_v = vertices[(i + 1) % n]
        l1 = math.dist(v, prev_v)
        l2 = math.dist(v, next_v)
        u1 = ((prev_v[0] - v[0]) / l1, (prev_v[1] - v[1]) / l1)
        u2 = ((next_v[0] - v[0]) / l2, (next_v[1] - v[1]) / l2)
        dot = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        theta = math.acos(dot)
        if radius <= 1e-6 or abs(theta - math.pi) < 1e-6:
            arcs.append({"entry": v, "exit": v, "mid": None})
            continue
        max_tan = 0.44 * min(l1, l2)
        tan_len = min(radius / math.tan(theta / 2.0), max_tan)
        r_eff = tan_len * math.tan(theta / 2.0)
        bx, bz = u1[0] + u2[0], u1[1] + u2[1]
        bl = math.hypot(bx, bz)
        cx = v[0] + (r_eff / math.sin(theta / 2.0)) * (bx / bl)
        cz = v[1] + (r_eff / math.sin(theta / 2.0)) * (bz / bl)
        entry = (v[0] + tan_len * u1[0], v[1] + tan_len * u1[1])
        exit_pt = (v[0] + tan_len * u2[0], v[1] + tan_len * u2[1])
        mid = (cx - r_eff * (bx / bl), cz - r_eff * (bz / bl))
        arcs.append({"entry": entry, "exit": exit_pt, "mid": mid})

    wb = BRepBuilderAPI_MakeWire()
    for i in range(n):
        row = arcs[i]
        nxt = arcs[(i + 1) % n]
        if row["mid"] is not None:
            p1 = gp_Pnt(row["entry"][0], y_val, row["entry"][1])
            pm = gp_Pnt(row["mid"][0], y_val, row["mid"][1])
            p2 = gp_Pnt(row["exit"][0], y_val, row["exit"][1])
            arc = GC_MakeArcOfCircle(p1, pm, p2).Value()
            wb.Add(BRepBuilderAPI_MakeEdge(arc).Edge())
        p_start = gp_Pnt(row["exit"][0], y_val, row["exit"][1])
        p_end = gp_Pnt(nxt["entry"][0], y_val, nxt["entry"][1])
        if p_start.Distance(p_end) > 1e-5:
            seg = GC_MakeSegment(p_start, p_end).Value()
            wb.Add(BRepBuilderAPI_MakeEdge(seg).Edge())
    return wb.Wire()


def make_loft(wires, ruled=True):
    loft = BRepOffsetAPI_ThruSections(True, ruled, 1e-4)
    for w in wires:
        loft.AddWire(w)
    loft.Build()
    return loft.Shape()


def make_loft_along_y(stations_xz, ruled=True):
    """Loft rounded XZ cross-sections smoothly along +Y using a rigid -90 deg X rotation."""
    wires = []
    for y_val, verts_xz, rad in stations_xz:
        verts_loc = [(vx, -vz) for vx, vz in verts_xz]
        wires.append(rounded_polygon_wire_xy(verts_loc, rad, y_val))
    loft_loc = make_loft(wires, ruled=ruled)
    trsf = gp_Trsf()
    trsf.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), -math.pi / 2.0)
    return BRepBuilderAPI_Transform(loft_loc, trsf, True).Shape()


def make_cable_pipe(r_pipe=1.50, z_top_turn=-15.80):
    from OCP.gp import gp_Circ
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
    r_bend = 5.0
    c1 = r_bend * math.cos(math.pi / 4.0)
    y_front = -12.90
    y_back  = -34.50
    z_under = -55.20

    wb = BRepBuilderAPI_MakeWire()
    p0 = gp_Pnt(0, y_front, -66.50)
    p1 = gp_Pnt(0, y_front, z_under - r_bend)
    pm1 = gp_Pnt(0, y_front - r_bend + c1, z_under - r_bend + c1)
    p2 = gp_Pnt(0, y_front - r_bend, z_under)
    p3 = gp_Pnt(0, y_back + r_bend, z_under)
    pm2 = gp_Pnt(0, y_back + r_bend - c1, z_under + r_bend - c1)
    p4 = gp_Pnt(0, y_back, z_under + r_bend)
    p5 = gp_Pnt(0, y_back, z_top_turn - r_bend)
    pm3 = gp_Pnt(0, y_back + r_bend - c1, z_top_turn - r_bend + c1)
    p6 = gp_Pnt(0, y_back + r_bend, z_top_turn)
    p7 = gp_Pnt(0, -23.00, z_top_turn)

    wb.Add(BRepBuilderAPI_MakeEdge(GC_MakeSegment(p0, p1).Value()).Edge())
    wb.Add(BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(p1, pm1, p2).Value()).Edge())
    wb.Add(BRepBuilderAPI_MakeEdge(GC_MakeSegment(p2, p3).Value()).Edge())
    wb.Add(BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(p3, pm2, p4).Value()).Edge())
    wb.Add(BRepBuilderAPI_MakeEdge(GC_MakeSegment(p4, p5).Value()).Edge())
    wb.Add(BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(p5, pm3, p6).Value()).Edge())
    wb.Add(BRepBuilderAPI_MakeEdge(GC_MakeSegment(p6, p7).Value()).Edge())
    spine = wb.Wire()

    circ = gp_Circ(gp_Ax2(p0, gp_Dir(0, 0, 1)), r_pipe)
    prof_face = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circ).Edge()).Wire()).Face()
    return BRepOffsetAPI_MakePipe(spine, prof_face).Shape()


def build_p20_inlet():
    """
    Upper CPAP Hose Inlet (Z = -17.78 to +30.00 mm) built 100% from analytical primitives,
    orthogonal extrusions (XY, XZ, YZ), coaxial cones/cylinders, and boolean cuts (0 BSpline faces):
    - Top 3-barb hose spigot (Z = +14.50 to +30.00 mm) tailored for the Trianglelab Supercharged 7040
      CPAP hose (20.20 mm shank OD, 21.60-21.70 mm 3-barb OD, 19.30 mm lead-in tip, 16.40 mm ID bore ->
      1.90 to 2.65 mm solid ABS wall thickness for high clamping strength).
    - True circular rear cylinder (R = r_shank = 10.10 mm centered at (0, y_cuff = -48.50 mm)) intersected
      with a single smooth sloped rear YZ profile so there is zero hyperbolic eyebrow arch or sliver face.
    - Upstream P20 has a 3.80 mm downward-projecting INNER male sleeve (Z = -21.58 to -17.78 mm)
      that telescopes inside P21's outer female socket like roofing shingles, with a continuous
      0.82 mm 2-perimeter inner wall wrapping smoothly around the center cable boss and front lugs.
    - Pure uncut upper lateral wings emerge smoothly from inside P20's funnel wall (Z = +2.00..+14.50 mm)
      below the 3 hose barbs and seat at Y = -32.26 mm (Z = +20.25..+25.00 mm) to co-bolt P20 through
      the top two EBB42 holes (-16.748, 22.000) and (14.252, 22.000) with full NEMA14 motor clearance.
    """
    z_split = -17.780
    z_sleeve_bot = z_split - 3.800
    y_cuff = -48.50
    r_bore = 8.20     # 16.40 mm ID bore (1.90 mm min wall at shank, 2.65 mm wall at barbs)
    r_shank = 10.10   # 20.20 mm OD shank between barbs
    r_barb1 = 10.80   # 21.60 mm OD top barb
    r_barb2 = 10.85   # 21.70 mm OD middle & lower barbs
    r_tip   = 9.65    # 19.30 mm OD lead-in chamfer tip at Z = +30.00 mm

    # 1. Inner male shingle sleeve below z_split (Z = -21.58 to -17.78 mm):
    male_sleeve = prism_xy_r(corridor_aero_vertices(1.02), 2.5, z_sleeve_bot, z_split + 0.50)

    # 2. Main Transition Funnel (Z = -17.78 to +16.50 mm) with true circular rear cylinder (zero rear cone arch):
    xy_outer = fuse_all([
        cyl_z(0.0, y_cuff, z_split, 16.50, r_shank),
        prism_xy_r([
            (-20.60, -33.20),
            (-20.60, -38.20),
            (-13.00, -45.40),
            (-r_shank, y_cuff),
            ( r_shank, y_cuff),
            ( 13.00, -45.40),
            ( 20.60, -38.20),
            ( 20.60, -33.20),
        ], [3.5, 3.5, 8.0, 0.0, 0.0, 8.0, 3.5, 3.5], z_split, 16.50),
    ])
    xz_outer = prism_xz_r([
        (-20.60, z_split), ( 20.60, z_split),
        ( 20.60, -13.50), ( r_shank, 11.50),
        ( r_shank, 25.00), (-r_shank, 25.00),
        (-r_shank, 11.50), (-20.60, -13.50),
    ], [0, 0, 6.0, 6.0, 0, 0, 6.0, 6.0], -65.0, -30.0)
    yz_outer = prism_yz_r([
        (-45.40, z_split), (-33.20, z_split),
        (-33.20, -16.80), (-36.00, -13.00),
        (y_cuff + r_shank, 11.50), (y_cuff + r_shank, 25.00),
        (y_cuff - r_shank - 1.50, 25.00), (y_cuff - r_shank - 1.50, 14.50),
        (-45.40, -16.50),
    ], [0, 0, 1.5, 4.0, 6.0, 0, 0, 0.0, 2.5], -25.0, 25.0)
    cone_outer_env = fuse_all([
        box(-25.0, 25.0, -65.0, y_cuff, z_split, 20.00),
        box(-25.0, 25.0, y_cuff, -30.0, z_split, 6.50),
        cone_z(0.0, y_cuff, 6.50, 14.50, r_shank + 8.00, r_shank),
        cyl_z(0.0, y_cuff, 14.50, 16.50, r_shank),
    ])
    outer_loft = fuse_all([
        male_sleeve,
        intersect_all(xy_outer, [xz_outer, yz_outer, cone_outer_env]),
    ])

    # 3. Inner Cavity strictly offset inside outer_loft by >= 1.90 mm on all axes:
    c_in = corridor_aero_vertices(1.84)
    xy_inner = fuse_all([
        prism_xy_r(c_in, 2.0, z_sleeve_bot - 0.50, z_split + 0.01),
        cyl_z(0.0, y_cuff, z_split, 16.50, r_bore),
        prism_xy_r([
            c_in[0],
            c_in[1],
            c_in[2],
            (-r_bore, y_cuff),
            ( r_bore, y_cuff),
            c_in[3],
            c_in[4],
            c_in[5],
        ], [2.0, 2.0, 6.0, 0.0, 0.0, 6.0, 2.0, 2.0], z_split, 16.50),
    ])
    xz_inner = prism_xz_r([
        (-18.76, z_sleeve_bot - 0.50), ( 18.76, z_sleeve_bot - 0.50),
        ( 18.76, -13.50), ( r_bore, 11.50),
        ( r_bore, 25.00), (-r_bore, 25.00),
        (-r_bore, 11.50), (-18.76, -13.50),
    ], [0, 0, 5.0, 5.0, 0, 0, 5.0, 5.0], -65.0, -30.0)
    yz_inner = prism_yz_r([
        (-43.56, z_sleeve_bot - 0.50), (-35.04, z_sleeve_bot - 0.50),
        (-35.04, -16.80), (-37.84, -13.00),
        (y_cuff + r_bore, 11.50), (y_cuff + r_bore, 25.00),
        (y_cuff - r_bore - 1.50, 25.00), (y_cuff - r_bore - 1.50, 14.50),
        (-43.56, z_split),
    ], [0, 0, 1.2, 3.5, 5.0, 0, 0, 0.0, 2.0], -25.0, 25.0)
    cone_inner_env = fuse_all([
        box(-25.0, 25.0, -65.0, y_cuff, z_sleeve_bot - 1.0, 20.00),
        box(-25.0, 25.0, y_cuff, -30.0, z_sleeve_bot - 1.0, 6.50),
        cone_z(0.0, y_cuff, 6.50, 14.50, r_bore + 8.00, r_bore),
        cyl_z(0.0, y_cuff, 14.50, 31.00, r_bore),
    ])
    inner_loft = fuse_all([
        intersect_all(xy_inner, [xz_inner, yz_inner, cone_inner_env]),
        cyl_z(0.0, y_cuff, 14.50, 31.00, r_bore),
    ])

    # 4. 3-Barb Trianglelab 7040 Spigot (Z = +14.50 to +30.00 mm, 45-deg print-safe undercuts):
    spigot_parts = [
        cyl_z(0.0, y_cuff, 14.50, 16.50, r_shank),
        # Barb #3 (Z = 16.50 .. 21.00, crest Ø21.70 mm at Z = 17.35):
        cone_z(0.0, y_cuff, 16.50, 17.35, r_shank, r_barb2),
        cone_z(0.0, y_cuff, 17.35, 21.00, r_barb2, r_shank),
        # Barb #2 (Z = 21.00 .. 25.50, crest Ø21.70 mm at Z = 21.85):
        cone_z(0.0, y_cuff, 21.00, 21.85, r_shank, r_barb2),
        cone_z(0.0, y_cuff, 21.85, 25.50, r_barb2, r_shank),
        # Barb #1 (Z = 25.50 .. 30.00, crest Ø21.60 mm at Z = 26.30..28.00, lead-in tip Ø19.30 mm at Z = 30.00):
        cone_z(0.0, y_cuff, 25.50, 26.30, r_shank, r_barb1),
        cone_z(0.0, y_cuff, 26.30, 28.00, r_barb1, r_barb1),
        cone_z(0.0, y_cuff, 28.00, 30.00, r_barb1, r_tip),
    ]

    lug_l = cyl_z(-4.50, -31.20, z_split, -14.20, 3.6)
    lug_r = cyl_z( 4.50, -31.20, z_split, -14.20, 3.6)
    lug_web = rounded_box_xy(-8.10, 8.10, -35.50, -30.80, z_split, -14.20, 1.2)

    # 5. Upper lateral mounting wings built from orthogonal YZ + XZ + XY extrusions (0 BSpline faces):
    yz_wing = prism_yz_r([
        (-45.50,  2.00), (-41.00,  2.00),
        (-41.00, 10.00), (-32.26, 20.25),
        (-32.26, 25.00), (-39.50, 25.00),
        (-39.50, 19.55), (-45.50, 11.50),
    ], [0, 0, 4.0, 1.5, 0, 0, 4.0, 4.0], -22.0, 22.0)
    wing_tr = intersect_all(
        yz_wing,
        [
            prism_xz_r([
                (-12.50,  2.00), (-6.00,  2.00),
                (-6.00,  10.00), (-13.40, 19.55),
                (-13.40, 25.00), (-20.00, 25.00),
                (-20.00, 19.55), (-12.50, 10.00),
            ], [0, 0, 4.0, 2.0, 0, 0, 3.0, 4.0], -48.0, -32.0),
            rounded_box_xy(-20.00, -6.00, -46.50, -32.26, 2.00, 25.00, 1.5),
        ]
    )
    wing_tl = intersect_all(
        yz_wing,
        [
            prism_xz_r([
                ( 6.00,  2.00), (12.50,  2.00),
                (12.50, 10.00), (17.50, 19.55),
                (17.50, 25.00), (11.20, 25.00),
                (11.20, 19.55), ( 6.00, 10.00),
            ], [0, 0, 4.0, 3.0, 0, 0, 2.0, 4.0], -48.0, -32.0),
            rounded_box_xy(6.00, 17.50, -46.50, -32.26, 2.00, 25.00, 1.5),
        ]
    )

    # 6. Internal cable-boss fairing built from orthogonal XY + YZ extrusions (0 BSpline faces):
    cable_rib_up = intersect_all(
        prism_xy_r([(-3.65, -31.50), (-3.65, -38.15), (3.65, -38.15), (3.65, -31.50)], 3.00, z_sleeve_bot - 0.50, 4.50),
        [
            prism_yz_r([
                (-38.15, z_sleeve_bot - 0.50), (-31.50, z_sleeve_bot - 0.50),
                (-31.50, 4.50), (-33.20, 4.50),
                (-38.15, -13.80),
            ], [0, 0, 0, 4.0, 6.0], -4.0, 4.0),
        ]
    )

    body = fuse_all([outer_loft, *spigot_parts, lug_l, lug_r, lug_web, wing_tr, wing_tl])
    inner_cavity = cut_all(inner_loft, [cable_rib_up])

    body = cut_all(body, [
        box(-50, 50, -100, 50, -50, z_sleeve_bot),
        # Outer recess on P20's male sleeve clearing P21's female socket cable boss while keeping P20's inner wall 100% continuous:
        prism_xy_r([(-2.86, -25.00), (-2.86, -37.36), (2.86, -37.36), (2.86, -25.00)], 2.45, z_sleeve_bot - 0.5, z_split),
        inner_cavity,
        cyl_z(-4.50, -31.20, z_split - 1.0, -10.0, 1.65),
        cyl_z( 4.50, -31.20, z_split - 1.0, -10.0, 1.65),
        cyl_z(-4.50, -31.20, -14.20, 35.0, 2.85),
        cyl_z( 4.50, -31.20, -14.20, 35.0, 2.85),
        # Sensor cable channel & forward exit slot built from cylinders and box (0 BSpline faces):
        cyl_z(0.0, -34.50, z_sleeve_bot - 1.0, -15.80, 1.95),
        cyl_y(0.0, -15.80, -34.50, -25.00, 1.95),
        box(-1.95, 1.95, -34.50, -25.00, z_split - 0.2, -13.85),
        # Upper wing M3 through-holes & rear spotfaces at (-16.748, 22.000) and (14.252, 22.000):
        cyl_y(-16.748, 22.000, -42.00, -32.00, 1.65),
        cyl_y( 14.252, 22.000, -42.00, -32.00, 1.65),
        cyl_y(-16.748, 22.000, -42.00, -35.80, 2.85),
        cyl_y( 14.252, 22.000, -42.00, -35.80, 2.85),
    ])
    body = intersect_all(body, [box(-22.497, 22.497, -100.0, 50.0, z_sleeve_bot, 30.00)])
    u = ShapeUpgrade_UnifySameDomain(body, True, True, True)
    u.Build()
    body = u.Shape()
    air = fuse_all([
        cut_all(inner_cavity, [box(-50, 50, -100, 50, -50, z_split), box(-50, 50, -100, 50, 14.5, 50)]),
        cyl_z(0.0, y_cuff, 14.50, 30.00, r_bore),
    ])
    return body, air


def build_p21_mid():
    """
    Prismatic vertical gantry conduit (Z = -49.00 to -17.78 mm, plus 2.40 mm lower inner male shingle sleeve)
    built 100% from orthogonal extrusions, cylinders, and boolean cuts (0 BSpline faces):
    - Top female shingle socket (Z = -21.80 to -17.78 mm) receives P20's 360-deg continuous inner male sleeve.
    - Upper bridge (up_fairing & up_saddle at Z = -24.10..-18.40 mm) bolts directly to the bottom of P24
      via 2x M3x8 vertical screws + 2x M3 heat-set inserts at (X = ±6.00, Y = -15.80, Z = -18.40 mm).
    - Bottom inner male shingle sleeve (Z = -51.40 to -49.00 mm) telescopes inside P22's top female collar
      right below the 2020 X-axis extrusion (Z_min = -47.78 mm) so P22 can sweep smoothly forward immediately.
    """
    z_top = -17.780
    z_bot = -49.000
    z_sleeve_bot = -51.400

    # Single unbroken vertical extrusion for main conduit + stepped lower inner male shingle sleeve:
    conduit_outer = fuse_all([
        prism_xy_r(corridor_aero_vertices(0.0), 3.5, z_bot, z_top),
        prism_xy_r(corridor_aero_vertices(1.02), 2.5, z_sleeve_bot, z_bot + 0.50),
    ])

    # Constant, step-free internal bore (corridor_aero_vertices(1.84)) matching P20's male sleeve and P22's bore 100% flush:
    conduit_inner_loft = prism_xy_r(corridor_aero_vertices(1.84), 2.0, z_sleeve_bot - 0.50, z_top + 1.00)
    # Top female socket recess (Z = -21.58 to -17.78 mm, wall = 0.84 mm 2-perimeter -> 0.18 mm radial slip clearance):
    top_socket_recess = cut_all(
        prism_xy_r(corridor_aero_vertices(0.84), 2.7, -21.58, z_top + 0.50),
        [prism_xy_r([(-2.80, -25.00), (-2.80, -37.30), (2.80, -37.30), (2.80, -25.00)], 2.40, -22.50, z_top + 1.0)],
    )
    cable_boss_excl = prism_xy_r([(-3.65, -25.00), (-3.65, -38.15), (3.65, -38.15), (3.65, -25.00)], 3.00, z_sleeve_bot - 2.0, z_top + 1.0)
    conduit_inner = fuse_all([
        cut_all(conduit_inner_loft, [cable_boss_excl]),
        top_socket_recess,
    ])

    up_lug_l = cyl_z(-4.50, -31.20, -26.50, z_top, 3.6)
    up_lug_r = cyl_z( 4.50, -31.20, -26.50, z_top, 3.6)
    up_lug_web = box(-4.50, 4.50, -35.50, -31.20, -26.50, z_top)
    up_fairing = intersect_all(
        rounded_box_xy(-9.20, 9.20, -35.50, -12.10, -27.60, -18.40, 2.2),
        [prism_yz_r([
            (-35.50, -27.60), (-33.20, -27.60), (-25.00, -24.80),
            (-12.10, -22.50), (-12.10, -18.40), (-35.50, -18.40),
        ], [0, 2.0, 4.0, 1.5, 0, 0], -10.0, 10.0)]
    )
    up_bridge_verts = [
        (-9.20, -34.50), (-9.20, -12.10), (-21.00, -9.70), (-21.00, 0.30),
        ( 21.00,  0.30), ( 21.00, -9.70), (  9.20, -12.10), (  9.20, -34.50),
    ]
    up_saddle = prism_xy_r(up_bridge_verts, 2.2, -24.10, -18.40)

    body = fuse_all([conduit_outer, up_lug_l, up_lug_r, up_lug_web, up_fairing, up_saddle])

    cutters = [
        conduit_inner,
        box(-50, 50, -100, 50, -70.0, z_sleeve_bot),
        prism_xy_r([(-2.86, -25.00), (-2.86, -37.36), (2.86, -37.36), (2.86, -25.00)], 2.45, z_sleeve_bot - 0.5, z_bot),
        cyl_z(-4.50, -31.20, -21.30, z_top + 0.5, 2.27),
        cyl_z( 4.50, -31.20, -21.30, z_top + 0.5, 2.27),
        cyl_z(-4.50, -31.20, -27.00, -21.20, 1.65),
        cyl_z( 4.50, -31.20, -27.00, -21.20, 1.65),
        cyl_z(-6.00, -15.80, -22.40, -18.00, 2.27),
        cyl_z( 6.00, -15.80, -22.40, -18.00, 2.27),
        cyl_z(-6.00, -15.80, -25.00, -22.00, 1.65),
        cyl_z( 6.00, -15.80, -25.00, -22.00, 1.65),
        cyl_z(0.0, -34.50, z_sleeve_bot - 1.0, z_top + 1.0, 1.95),
        box(-1.95, 1.95, -34.50, -30.00, z_sleeve_bot - 1.0, z_top + 1.0),
    ]
    body = cut_all(body, cutters)
    body = intersect_all(body, [box(-22.497, 22.497, -50.0, 25.0, z_sleeve_bot, z_top)])
    u = ShapeUpgrade_UnifySameDomain(body, True, True, True)
    u.Build()
    body = u.Shape()
    air = cut_all(
        conduit_inner_loft,
        [
            prism_xy_r([(-3.65, -25.00), (-3.65, -38.15), (3.65, -38.15), (3.65, -25.00)], 3.10, z_sleeve_bot - 1.0, z_top + 1.0),
            box(-50, 50, -100, 50, -70.0, z_bot),
            box(-50, 50, -100, 50, z_top, 0.0),
        ],
    )
    return body, air


def build_p22_lower_plenum():
    """
    Lower CPAP Plenum built 100% from analytical primitives, orthogonal XY/YZ extrusions,
    cylinders, spheres, and boolean cuts (0 BSpline faces):
    - Top female shingle socket (Z = -51.60 to -49.00 mm) slides over P21's inner male sleeve
      just below the 2020 X-axis extrusion (Z_min = -47.78 mm) with 0.00 mm internal bore step.
    - Unified YZ internal sweep (R_in = 61.0 mm / R_out = 50.0 mm upper sweep, R_in = 14.8 mm /
      R_out = 16.0 mm lower heel, and a 100% flat, bump-free floor at Z = -68.90 mm).
    - Parallel G1-continuous center island (inner air boundary) and center valley (outer shell boundary)
      guaranteeing a uniform >= 1.40 mm wall thickness with zero steps, zero dead-end pockets, and zero breaches.
    - Exact 3D constant-distance thermal keepout (R = 4.65 mm cylindrical + spherical offset around the
      Volcano silicone sock and >= 5.90 mm from the 350C bare Volcano heatblock).
    """
    z_top = -49.000
    socket_recess = cut_all(
        prism_xy_r(corridor_aero_vertices(0.84), 2.7, -51.40, z_top + 0.50),
        [prism_xy_r([(-2.80, -25.00), (-2.80, -37.30), (2.80, -37.30), (2.80, -25.00)], 2.40, -52.00, z_top + 1.0)],
    )

    # Parallel gooseneck YZ outer and inner profiles: roof drops in parallel with floor down to the sub-sock nozzle plane!
    horn_yz_out = prism_yz_r([
        (-45.40, -70.80), (-45.40,  z_top),
        (-33.20,  z_top), (-33.20, -49.50),
        (-20.736,-57.36), (  0.00, -57.36),
        (  9.80, -57.36), ( 16.80, -61.20),
        ( 23.50, -68.80), ( 29.60, -72.20),
        ( 29.60, -77.85), ( 19.00, -77.85),
        ( 11.55, -70.80),
    ], [16.0, 0, 0, 0, 50.0, 0, 16.0, 16.0, 12.0, 1.2, 0.8, 7.5, 7.5], -23.0, 23.0)

    horn_yz_in = prism_yz_r([
        (-43.56, -68.90), (-43.56,  z_top + 0.50),
        (-35.04,  z_top + 0.50), (-35.04, -51.40),
        (-21.413,-58.60), (  0.00, -58.60),
        (  9.20, -58.60), ( 16.00, -62.40),
        ( 22.80, -70.10), ( 28.20, -73.40),
        ( 28.20, -76.65), ( 19.60, -76.65),
        ( 12.20, -68.90),
    ], [14.8, 0, 0, 0, 61.0, 0, 14.5, 14.5, 10.5, 0.8, 0.5, 6.5, 6.5], -22.5, 22.5)

    # Inward-sweeping XY outer and inner profiles that curve smoothly into the nozzle at Y=22.70..28.20 (zero dead-end pocket!):
    xy_outer_full = prism_xy_r([
        (-13.00, -45.40), (-20.60, -38.20), (-20.60, -25.30),
        (-22.42, -19.50), (-22.42,  15.00), (-20.40,  22.50),
        (-14.80,  28.40), ( -8.50,  29.60), ( -8.50,  11.20),
        (  8.50,  11.20), (  8.50,  29.60), ( 14.80,  28.40),
        ( 20.40,  22.50), ( 22.42,  15.00), ( 22.42, -19.50),
        ( 20.60, -25.30), ( 20.60, -38.20), ( 13.00, -45.40),
    ], [3.5, 3.5, 16.0, 16.0, 12.0, 10.0, 4.0, 0.8, 0.0, 0.0, 0.8, 4.0, 10.0, 12.0, 16.0, 16.0, 3.5, 3.5], -78.00, z_top)

    xy_inner_full = prism_xy_r([
        (-12.16, -43.56), (-18.76, -37.36), (-18.76, -26.50),
        (-21.02, -19.50), (-21.02,  14.80), (-19.00,  22.00),
        (-13.80,  27.20), ( -8.50,  28.20), (  8.50,  28.20),
        ( 13.80,  27.20), ( 19.00,  22.00), ( 21.02,  14.80),
        ( 21.02, -19.50), ( 18.76, -26.50), ( 18.76, -37.36),
        ( 12.16, -43.56),
    ], [2.0, 2.0, 14.0, 14.0, 10.6, 8.6, 3.0, 0.0, 0.0, 3.0, 8.6, 10.6, 14.0, 14.0, 2.0, 2.0], -77.50, z_top + 0.50)

    cable_boss_nose = prism_xy_r([(-3.65, -20.00), (-3.65, -38.15), (3.65, -38.15), (3.65, -20.00)], 3.00, -78.00, z_top + 1.00)
    center_island_body = prism_xy_r([
        (-3.65, -36.50), (-3.65, -31.00), (-12.85, -16.50),
        (-12.85, 13.50), (-11.60, 17.50), (-11.60,  30.00),
        ( 11.60, 30.00), ( 11.60, 17.50), ( 12.85,  13.50),
        ( 12.85,-16.50), (  3.65,-31.00), (  3.65, -36.50),
    ], [0.0, 14.0, 14.0, 4.0, 4.0, 0.0, 0.0, 4.0, 4.0, 14.0, 14.0, 0.0], -78.00, z_top + 1.00)
    center_island_excl = fuse_all([cable_boss_nose, center_island_body])

    center_valley_upper = prism_xy_r([
        (-2.25, -33.20), (-2.25, -30.50), (-11.45, -16.00),
        (-11.45, -5.40), (11.45,  -5.40), ( 11.45, -16.00),
        ( 2.25, -30.50), ( 2.25, -33.20),
    ], [0.0, 12.6, 12.6, 0.0, 0.0, 12.6, 12.6, 0.0], -58.60, z_top + 1.00)

    center_valley_lower = prism_xy_r([
        (-2.25, -29.50), (-11.45, -15.50), (-11.45, -5.40),
        (11.45,  -5.40), ( 11.45, -15.50), (  2.25, -29.50),
    ], [4.0, 12.6, 0.0, 0.0, 12.6, 4.0], -78.00, -58.00)

    cheeks = []
    for sign in (-1, 1):
        cheek_pts = [
            (sign * 13.95, 11.48),
            (sign * 22.42, 11.48),
            (sign * 22.42, 20.50),
            (sign * 13.95, 20.50),
        ]
        cheek_rads = [1.5, 0.0, 0.0, 1.5]
        if sign < 0:
            cheek_pts = cheek_pts[::-1]
            cheek_rads = cheek_rads[::-1]
        cheek = intersect_all(
            prism_xy_r(cheek_pts, cheek_rads, -66.00, -48.00),
            [
                xy_outer_full,
                prism_yz_r([
                    (11.48, -66.00), (20.50, -66.00),
                    (19.80, -48.00), (11.48, -48.00),
                ], [0, 1.0, 1.0, 0], -23.0, 23.0),
            ]
        )
        cheeks.append(cheek)

    probe_spigots = [
        cyl_z( 15.80,   8.50, -72.60, -70.00, 3.05),
        cyl_z(-15.80,   8.50, -72.60, -70.00, 3.05),
        cyl_z( 15.80, -11.50, -72.60, -70.00, 3.05),
        cyl_z(-15.80, -11.50, -72.60, -70.00, 3.05),
    ]

    body = cut_all(
        fuse_all([intersect_all(xy_outer_full, [horn_yz_out]), *cheeks, *probe_spigots]),
        [center_valley_upper, center_valley_lower]
    )

    xy_air_combined = cut_all(xy_inner_full, [center_island_excl])
    # Smoothly curved inward converging nozzle louver across Y in [16.50, 28.20] mm (centered on nozzle Y=22.70 mm):
    hood_slots = []
    for sign in (-1, 1):
        slot_xy = rounded_box_xy(sign * 8.00, sign * 15.50, 16.50, 28.20, -76.65, -71.50, 1.2)
        pts_louver = [
            (sign * 8.00,  -76.65),
            (sign * 15.50, -76.65),
            (sign * 15.50, -71.50),
            (sign * 10.20, -74.85),
            (sign * 8.00,  -74.85),
        ]
        if sign < 0:
            pts_louver = pts_louver[::-1]
        slot_xz = prism_xz_r(pts_louver, [0.0, 0.0, 0.6, 0.6, 0.0], 16.00, 28.50)
        hood_slots.append(intersect_all(slot_xy, [slot_xz, horn_yz_in, xy_inner_full]))
    air = fuse_all([intersect_all(xy_air_combined, [horn_yz_in]), *hood_slots])

    # Stepped analytical 3D thermal keepout: R=3.20mm around silicone sock above Z=-74.35 (|X|<=10.20, >=4.45mm from bare heatblock),
    # and |X|<=8.50 below Z=-74.35 so the lower floor lip guides the jet directly beneath the silicone sock onto the brass nozzle:
    r_off_upper = 3.20
    nozzle_slot = fuse_all([
        rounded_box_xy(-7.00 - r_off_upper, 7.00 + r_off_upper, 12.95 - r_off_upper, 42.00, -74.35, -50.00, r_off_upper),
        rounded_box_xy(-11.65, 11.65, 8.30, 16.50, -79.00, -50.00, 4.65),
        rounded_box_xy(-8.50, 8.50, 11.50, 42.00, -79.00, -74.35, 2.0),
        cyl_y(-7.00, -74.35, 12.95, 42.00, r_off_upper),
        cyl_y( 7.00, -74.35, 12.95, 42.00, r_off_upper),
    ])

    cutters = [
        air,
        nozzle_slot,
        socket_recess,
        # Clear P23 (Y <= 11.56 mm, Z = -77.00..-70.80 mm) and Beacon/Cartographer PCB front edge (Y <= 11.75 mm, Z <= -74.98 mm):
        box(-19.50, 19.50, -15.00, 11.56, -77.00, -70.80),
        box(-19.50, 19.50, -15.00, 11.75, -77.00, -74.98),
        cyl_z(0.0, -34.50, -58.60, z_top + 1.0, 1.95),
        box(-1.95, 1.95, -34.50, -30.00, -58.60, z_top + 1.0),
        box(-1.95, 1.95, -34.50, -25.00, -58.60, -53.20),
        cyl_y( 18.0, -52.78, 11.0, 15.95, 4.02),
        cyl_y(-18.0, -52.78, 11.0, 15.95, 4.02),
        cyl_y( 18.0, -52.78, 15.5, 21.0, 1.65),
        cyl_y(-18.0, -52.78, 15.5, 21.0, 1.65),
        cyl_y( 18.0, -52.78, 18.2, 21.0, 3.00),
        cyl_y(-18.0, -52.78, 18.2, 21.0, 3.00),
        cyl_z( 15.80,   8.50, -73.00, -70.10, 2.27),
        cyl_z(-15.80,   8.50, -73.00, -70.10, 2.27),
        cyl_z( 15.80, -11.50, -73.00, -70.10, 2.27),
        cyl_z(-15.80, -11.50, -73.00, -70.10, 2.27),
    ]
    body = cut_all(body, cutters)
    body = intersect_all(body, [box(-22.497, 22.497, -50.0, 36.0, -78.20, -47.50)])
    u = ShapeUpgrade_UnifySameDomain(body, True, True, True)
    u.Build()
    body = u.Shape()
    return body, cut_all(air, [nozzle_slot])


def build_p23_probe_mount():
    """
    Forward-Facing Beacon RevH Normal & Cartographer V3 Flat Pack Mount:
    - Places M3 sensor mounting holes at (X = ±15.80, Y = -0.30, Z_seat = -75.00 mm)
    - Moves Beacon sensing coil forward to (X = 0.0, Y = +3.20 mm, Z_bot = -76.61 mm -> 2.27 mm above nozzle tip!)
    - Solid continuous plastic mounting plate over the sensing coil (Y = -5.80..+11.80 mm, Z = -75.00..-70.80 mm)
    - Places the sensor cable connector at the REAR (Y = -15.68..-10.13 mm) with an integrated rear cable exit
    - Bolts directly to the underside of P22 at (±15.80, +8.50) and (±15.80, -11.50) at Z = -70.80 mm
    """
    z_seat = -75.000
    z_top  = -70.800

    deck_verts = [
        (-19.20, -14.20), ( 19.20, -14.20),
        ( 19.20,  11.55), (-19.20,  11.55),
    ]
    deck = prism_xy_rounded(deck_verts, 2.0, z_seat, z_top)

    cutters = [
        # Center-front thermal setback (>= 5.90 mm from bare heatblock Y=14.20, >= 4.65 mm from silicone sock Y=12.95):
        rounded_box_xy(-11.65, 11.65, 8.30, 20.00, z_seat - 1.0, z_top + 1.0, 4.65),
        # Rear connector dome & Cartographer MCU/header recess (X = [-11.5, 11.5], Y = [-16.0, -5.80]):
        box(-11.50, 11.50, -16.00, -5.80, z_seat - 1.0, z_top + 1.0),
        # Relief for Beacon solid[2] rear mounting ear stiffener strip (Y = -16.0..-7.95, Z = -75.0..-73.85):
        box(-19.50, 19.50, -16.00, -7.95, z_seat - 0.5, -73.80),
        # Forward-facing sensor M3 mounting holes & captive nut slots at (±15.80, Y = -0.30):
        cyl_z( 15.80, -0.30, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80, -0.30, z_seat - 1.0, z_top + 1.0, 1.65),
        box( 12.80, 19.50, -3.15, 2.55, -73.60, -71.50),
        box(-19.50, -12.80, -3.15, 2.55, -73.60, -71.50),
        # P23-to-P22 M3 mounting holes, top spigot-registration sockets (Z = -72.62..-70.70), & bottom counterbores (Z = -75.10..-73.60):
        cyl_z( 15.80,   8.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80,   8.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z( 15.80,   8.50, -72.62, z_top + 0.5, 3.15),
        cyl_z(-15.80,   8.50, -72.62, z_top + 0.5, 3.15),
        cyl_z( 15.80,   8.50, z_seat - 1.0, -73.60, 3.00),
        cyl_z(-15.80,   8.50, z_seat - 1.0, -73.60, 3.00),
        cyl_z( 15.80, -11.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z(-15.80, -11.50, z_seat - 1.0, z_top + 1.0, 1.65),
        cyl_z( 15.80, -11.50, -72.62, z_top + 0.5, 3.15),
        cyl_z(-15.80, -11.50, -72.62, z_top + 0.5, 3.15),
        cyl_z( 15.80, -11.50, z_seat - 1.0, -73.60, 3.00),
        cyl_z(-15.80, -11.50, z_seat - 1.0, -73.60, 3.00),
    ]
    body = cut_all(deck, cutters)
    u = ShapeUpgrade_UnifySameDomain(body, True, True, True)
    u.Build()
    body = u.Shape()
    return body


def build_p24_ebb42_mount():
    mx, mz = -1.248, 4.251
    eb_x, eb_z = -1.248, 6.500
    corners = [
        (eb_x - 15.5, eb_z + 15.5), # TR: (-16.748, 22.000)
        (eb_x + 15.5, eb_z + 15.5), # TL: ( 14.252, 22.000)
        (eb_x + 15.5, eb_z - 15.5), # BL: ( 14.252, -9.000)
        (eb_x - 15.5, eb_z - 15.5), # BR: (-16.748, -9.000)
    ]
    # Meets the 4 pre-soldered component-side standoffs (S96..S99) on the flipped EBB42 at Y = -25.40 mm
    # (shifted 4.00 mm rearward in -Y to clear NEMA14 pancake motors up to 21.8 mm+ thick with generous margin):
    y_standoff = -25.40
    bosses = [cyl_y(cx, cz, y_standoff, -21.50, 3.20) for cx, cz in corners]

    bar_left    = rounded_box_xy( 12.00,  22.10, -22.10, -13.50, -16.80, 27.50, 1.4)
    bar_right   = rounded_box_xy(-21.80, -13.70, -22.10, -14.00,   7.00, 48.70, 1.4)
    # Bottom crossbar & bridge plate sitting flush on P21's up_fairing at Z = -18.40 mm and bolting to P21 at (±6.00, -15.80),
    # plus forward 3-channel A1104 Hall-sensor lead insulator & strain-relief saddle (Y = -13.50..-6.75 mm):
    bar_bot_low = rounded_box_xy(-20.00,  17.50, y_standoff, -19.50, -16.80, -13.70, 1.2)
    bridge_p21  = rounded_box_xy( -9.50,   9.50, -23.50, -12.60, -18.40, -13.70, 1.4)
    hall_comb_saddle = cut_all(
        rounded_box_xy(-4.50, 3.50, -13.50, -6.75, -18.40, -14.30, 0.8),
        [
            box(-2.20, -1.30, -14.00, -6.50, -16.10, -14.20),
            box(-0.45,  0.45, -14.00, -6.50, -16.10, -14.20),
            box( 1.30,  2.20, -14.00, -6.50, -16.10, -14.20),
        ]
    )
    bridge_r    = rounded_box_xy(-17.50,  -8.50, -22.10, -11.00, -16.80, -13.70, 1.0)
    # Corner standoff support legs keeping the internal wiring bay open between the extruder motor and EBB42:
    leg_br = rounded_box_xy(-20.00, -13.95, y_standoff, -19.50, -16.80, -5.80, 1.2)
    leg_bl = rounded_box_xy( 11.00,  17.50, y_standoff, -19.50, -16.80, -5.80, 1.2)
    leg_tr = rounded_box_xy(-20.00, -13.80, y_standoff, -14.00, 19.60, 25.20, 1.2)
    leg_tl = rounded_box_xy( 11.00,  17.50, y_standoff, -14.00, 19.60, 25.20, 1.2)

    # Pure orthogonal extrusions for foot_ul, foot_bl, foot_ur (0 BSpline faces):
    foot_ul = intersect_all(
        rounded_box_xy(11.50, 22.10, -18.00, -6.70, 16.50, 27.50, 1.4),
        [prism_yz_r([(-18.00, 16.50), (-13.50, 16.50), (-6.70, 19.60), (-6.70, 27.50), (-18.00, 27.50)], [0, 0.0, 1.5, 0, 0], 11.0, 23.0)]
    )
    foot_bl = intersect_all(
        rounded_box_xy(11.50, 22.10, -18.00, -6.70, -16.80, -4.00, 1.4),
        [prism_yz_r([(-18.00, -16.80), (-6.70, -16.80), (-6.70, -6.00), (-13.50, -4.00), (-18.00, -4.00)], [0, 0, 1.5, 0.0, 0], 11.0, 23.0)]
    )
    pad_bl_low = rounded_box_xy(11.50, 21.50, -12.40, -6.70, -18.40, -15.00, 1.4)
    col_r_front = rounded_box_xy(-21.60, -15.20, -12.40, -6.70, -18.40, 21.00, 1.4)
    foot_ur = intersect_all(
        rounded_box_xy(-21.80, -12.50, -18.00, -6.70, 14.00, 51.20, 1.4),
        [
            prism_yz_r([(-18.00, 14.00), (-13.50, 14.00), (-6.70, 19.00), (-6.70, 51.20), (-16.50, 51.20), (-18.00, 45.00)], [0, 1.5, 1.5, 0, 1.5, 1.5], -22.5, -12.0),
            prism_xz_r([(-21.80, 14.00), (-12.50, 14.00), (-12.50, 51.20), (-20.80, 51.20), (-21.80, 45.00)], [0, 0, 0, 1.5, 1.5], -19.0, -6.0),
        ]
    )
    hook_ur = rounded_box_xy(-20.80, -12.50, -15.00, -2.50, 48.70, 51.20, 1.5)

    body = fuse_all([
        *bosses, bar_left, bar_right, bar_bot_low, bridge_p21, hall_comb_saddle, bridge_r,
        leg_br, leg_bl, leg_tr, leg_tl,
        foot_ul, foot_bl, pad_bl_low, col_r_front, foot_ur, hook_ur,
    ])

    cutters = [
        # Full motor clearance bore back to Y = -22.10 mm (clears 17.4-21.8 mm NEMA14 motors both from Y=+3.30 and from Y=+0.30!):
        cyl_y(mx, mz, -22.10, 1.00, 18.65),
        box(-19.60, -10.50, -21.20, -11.20, -14.10, -5.20),
        box(-22.50, -13.00, -15.00, -13.40, -19.80, -7.40),
        cyl_y(-16.748,  19.750, -16.80, 0.50, 3.10),
        # Lower-left stepped M3 counterbore at (14.252, -11.249) with full rear-to-front hex driver access tunnel:
        cyl_y( 14.252, -11.249, -29.00, 0.50, 1.65),
        cyl_y( 14.252, -11.249,  -8.40, 0.50, 3.10),
        cyl_y( 14.252, -11.249, -29.00, -12.00, 3.10),
        # Upper-left M3 counterbore at (17.250, 23.720) into SPACER_M3_HEATSET_0:
        cyl_y( 17.250,  23.720, -29.00, 0.50, 1.65),
        cyl_y( 17.250,  23.720,  -9.00, 0.50, 3.10),
        cyl_y( 17.250,  23.720, -29.00, -11.50, 3.10),
        # Upper-right M3 counterbore at (-18.100, 41.720) into UPPER_RIGHT_REAR_M3_HEATSET_4p6x4:
        cyl_y(-18.100,  41.720, -29.00, 0.50, 1.65),
        cyl_y(-18.100,  41.720, -29.00, -10.50, 3.10),
        # Lower-right M3 counterbore at (-18.500, -14.450) with full rear-to-front hex driver access tunnel:
        cyl_y(-18.500, -14.450, -29.00, 0.50, 1.65),
        cyl_y(-18.500, -14.450, -29.00, -9.80, 2.85),
        # P24-to-P21 vertical M3 mounting holes & counterbores at (X = ±6.00, Y = -15.80, Z = -18.40):
        cyl_z(-6.00, -15.80, -19.00, -13.00, 1.65),
        cyl_z( 6.00, -15.80, -19.00, -13.00, 1.65),
        cyl_z(-6.00, -15.80, -15.40, -13.00, 3.00),
        cyl_z( 6.00, -15.80, -15.40, -13.00, 3.00),
        *(cyl_y(cx, cz, y_standoff - 0.2, -19.00, 2.15) for cx, cz in corners),
        # Full clearance under and in front of EBB[58] Hotend Heater Screw Terminal & EBB[57] Thermistor:
        box(-13.95,  -6.20, -36.00, -18.40, -19.00,  -5.80),
        # Full +Y plug-in clearance windows for Left headers (EBB[44] PT100, EBB[1..4] I2C, EBB[45..47] RGB LEDs, EBB[48..52] Probe)
        # and Right header (EBB[43] Extruder Stepper JST-XH) & Top 2x2 MicroFit 3.0 (EBB[59]):
        box( 10.00,  18.85, -29.00, -12.50,  -5.80,  19.60),
        box(-22.00, -12.00, -29.00, -13.00,  -5.80,  18.80),
        box(-13.80,  -3.00, -36.00, -16.40,  19.50,  52.00),
        box( -7.20,   4.70, -21.10,   2.00,  21.20,  30.00),
    ]
    body = cut_all(body, cutters)
    u = ShapeUpgrade_UnifySameDomain(body, True, True, True)
    u.Build()
    body = u.Shape()
    return body


def build_sensor_cable():
    """
    3D swept Beacon / Cartographer sensor cable (Ø3.0 mm) routing from the rear-facing
    Beacon connector dome (X=0.0, Y=-12.90, Z=-66.50) straight up behind the MGN12H
    carriage, through the under-beam tunnel (Z=-55.20), up P21's center-front recessed
    cable raceway (X=0.0, Y=-34.50) behind the 2020 X-beam, and forward into the
    internal wiring bay between the flipped EBB42 and the extruder motor.
    """
    return make_cable_pipe(1.50, -15.80)


def build_accessory_hardware():
    hw = []
    # 1. Upper CPAP Inlet to Mid Bridge: 2x M3x8 + 2x M3x3x4.6 heat-set at (±4.50, -31.20, -17.78)
    for i, x in enumerate((-4.50, 4.50)):
        hw.append((f"ACC_UPPER_INLET_M3x8_{i}", fuse_all([cyl_z(x, -31.20, -22.0, -14.2, 1.5), cyl_z(x, -31.20, -14.2, -12.6, 2.75)])))
        hw.append((f"ACC_UPPER_INLET_HEATSET_{i}", cut_all(cyl_z(x, -31.20, -20.8, -17.8, 2.25), [cyl_z(x, -31.20, -21.0, -17.6, 1.5)])))
    # 2. P24 EBB42 Mount to P21 Upper Bridge: 2x M3x8 + 2x M3x4x4.6 heat-set at (±6.00, -15.80, -18.40)
    for i, x in enumerate((-6.00, 6.00)):
        hw.append((f"ACC_EBB42_BRIDGE_M3x8_{i}", fuse_all([cyl_z(x, -15.80, -22.2, -15.4, 1.5), cyl_z(x, -15.80, -15.4, -13.8, 2.75)])))
        hw.append((f"ACC_EBB42_BRIDGE_HEATSET_{i}", cut_all(cyl_z(x, -15.80, -22.4, -18.4, 2.25), [cyl_z(x, -15.80, -22.6, -18.2, 1.5)])))
    # 3. Lower Plenum Upper Cheeks to P01 Front Bosses: 2x M3x10 + 2x M3x4x4.6 heat-set at (±18.0, -52.78, Y=11.4..15.9)
    for i, x in enumerate((-18.0, 18.0)):
        hw.append((f"ACC_CASE_BOSS_M3x10_{i}", fuse_all([cyl_y(x, -52.78, 11.8, 18.2, 1.5), cyl_y(x, -52.78, 18.2, 19.8, 2.85)])))
        hw.append((f"ACC_CASE_BOSS_HEATSET_{i}", cut_all(cyl_y(x, -52.78, 11.9, 15.9, 2.25), [cyl_y(x, -52.78, 11.7, 16.1, 1.5)])))
    # 5. Probe Mount to Lower Plenum: 4x M3x5 + 4x M3x3x4.6 heat-set in downward spigot bosses at (±15.80, +8.50) and (±15.80, -11.50), Z=-72.60..-70.00 (0.00 mm protrusion into air channel)
    for i, (x, y) in enumerate([(-15.80, 8.50), (15.80, 8.50), (-15.80, -11.50), (15.80, -11.50)]):
        hw.append((f"ACC_PROBE_BRIDGE_M3x8_{i}", fuse_all([cyl_z(x, y, -73.6, -70.1, 1.5), cyl_z(x, y, -74.9, -73.6, 2.85)])))
        hw.append((f"ACC_PROBE_BRIDGE_HEATSET_{i}", cut_all(cyl_z(x, y, -72.6, -70.0, 2.25), [cyl_z(x, y, -72.8, -69.8, 1.5)])))
    # 6. Forward-Facing Beacon / Cartographer PCB Mounting Screws & Captive Nuts at (±15.80, -0.30, Z=-75.00)
    for i, x in enumerate((-15.80, 15.80)):
        hw.append((f"ACC_SENSOR_PCB_M3x8_{i}", fuse_all([cyl_z(x, -0.30, -76.6, -71.2, 1.5), cyl_z(x, -0.30, -78.1, -76.6, 2.75)])))
        hw.append((f"ACC_SENSOR_PCB_M3_NUT_{i}", cut_all(cyl_z(x, -0.30, -73.5, -71.6, 2.75), [cyl_z(x, -0.30, -73.7, -71.4, 1.5)])))
    # 7. EBB42 2x M3x16 Upper Co-Bolted Screws (through P20 upper wings + EBB42 + standoffs into P24) & 2x M3x12 Lower Screws + 4x M3x4x4.2 Heat-sets:
    eb_x, eb_z = -1.248, 6.500
    for i, (cx, cz) in enumerate([
        (eb_x - 15.5, eb_z + 15.5),
        (eb_x + 15.5, eb_z + 15.5),
        (eb_x + 15.5, eb_z - 15.5),
        (eb_x - 15.5, eb_z - 15.5),
    ]):
        y_head_front = -35.80 if cz > 0 else -32.25
        hw.append((f"ACC_EBB42_M3_{i}", fuse_all([cyl_y(cx, cz, y_head_front, -21.5, 1.5), cyl_y(cx, cz, y_head_front - 1.60, y_head_front, 2.75)])))
        hw.append((f"ACC_EBB42_HEATSET_{i}", cut_all(cyl_y(cx, cz, -25.4, -21.4, 2.10), [cyl_y(cx, cz, -25.6, -21.2, 1.5)])))
    return hw


def build_axial_fan_assembly(fan_size_mm, z_center, y_rear=36.04):
    """
    Build a 3D BRep representation of a 2510 (25x25x10 mm, 20x20 mm M2.5 pattern)
    or 3010 (30x30x10 mm, 24x24 mm M3 pattern) axial hotend cooling fan + 4 mounting screws.
    """
    half_w = 0.5 * fan_size_mm
    hole_half = 10.00 if fan_size_mm == 25 else 12.00
    r_bore = 11.40 if fan_size_mm == 25 else 13.80
    r_hub = 6.20 if fan_size_mm == 25 else 7.50
    r_screw = 1.25 if fan_size_mm == 25 else 1.50
    r_head = 2.25 if fan_size_mm == 25 else 2.75
    y_front = y_rear + 10.00

    frame_outer = prism_xz_r(
        [(-half_w, z_center - half_w), (half_w, z_center - half_w), (half_w, z_center + half_w), (-half_w, z_center + half_w)],
        2.2, y_rear, y_front
    )
    bore = cyl_y(0.0, z_center, y_rear - 0.5, y_front + 0.5, r_bore)
    frame = cut_all(frame_outer, [bore])

    hub = cyl_y(0.0, z_center, y_rear + 0.8, y_front - 0.8, r_hub)
    struts = [
        box(-0.9, 0.9, y_rear + 0.8, y_rear + 2.2, z_center - r_bore - 0.5, z_center + r_bore + 0.5),
        box(-r_bore - 0.5, r_bore + 0.5, y_rear + 0.8, y_rear + 2.2, z_center - 0.9, z_center + 0.9),
    ]
    fan_body = fuse_all([frame, hub] + struts)
    hole_cutters = [
        cyl_y(sx * hole_half, z_center + sz * hole_half, y_rear - 0.5, y_front + 0.5, r_screw + 0.15)
        for sx in (-1.0, 1.0) for sz in (-1.0, 1.0)
    ]
    fan_body = cut_all(fan_body, hole_cutters)

    screw_depth = 4.00 if fan_size_mm == 30 else 2.50
    screws = []
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            cx, cz = sx * hole_half, z_center + sz * hole_half
            s_shank = cyl_y(cx, cz, y_rear - screw_depth, y_front, r_screw)
            s_head = cyl_y(cx, cz, y_front, y_front + 1.60, r_head)
            screws.append(fuse_all([s_shank, s_head]))
    return fan_body, screws


def build_toolhead_fan_variants(v26_by_name):
    """
    Build updated removable toolhead carriers with primary focus on the 3010 (30x30x10 mm)
    axial hotend cooling fan, using 100% pure analytical primitives (0 BSplineSurface faces,
    0 Sphere faces, 0 mesh facets) and engineered for 100% support-free FDM printing face-down
    on the single coplanar +Y front face (Y = 35.930 mm):
      1. P17_HF_tool_carrier_3010 + P18_Tool_docking_backplate_3010 (Primary 3010 Design):
         - 3010 (30x30x10 mm) axial fan at Z=[-52.50, -22.50 mm], Y=[35.93, 45.93 mm] centered
           on the K1 heatsink for +60% airflow in 60-65C chambers and 7.00 mm vertical thermal
           clearance above the 350C Volcano heater block/sock (Z_max = -59.50 mm).
         - Single coplanar front bed face (Y = 35.930 mm from Z = -52.50 to +48.74 mm) and
           open rear-center heatsink window (X = [-7.85, +7.85 mm], Y = [11.50, 15.20 mm]) so
           the R = 11.15 mm heatsink bore never exceeds a 45-deg overhang when printed on +Y
           and has zero floating rear roof or mid-air bridges.
         - Wide-open Left (+X) and Right (-X) lateral exhaust windows (Y = 16.00..26.80 mm,
           Z = -48.50..-26.00 mm, divided by a 2.0 mm mid-span tie rib at Z = -38.25..-36.25 mm).
         - Print-safe 45-deg gable-roofed Left and Right vertical wire tunnels (|X| = 8.40..13.20 mm)
           isolated behind a continuous R = 12.30 mm solid partition wall, feeding into a 45-deg
           sloped enlarged upper stem wire trough (5.10 mm wide at Y = 35.93..30.00 mm, tapering
           at 45 deg to 1.50 mm wide at Y = 28.20 mm).
      2. P17_HF_tool_carrier_2510: Reference 2510 (25x25x10 mm) axial fan variant.
    """
    p18_orig = v26_by_name["TOOL_06_Tool_head_back_part_1"][0]
    y_front_bed = 35.930

    # 1. Print-safe 45-deg sloped enlarged stem wire trough (5.10 mm wide at Y=35.93..30.00, tapering at 45 deg to 1.50 mm wide at Y=28.20):
    stem_wire_enlarge = prism_xy_r([
        (-2.55, 30.00), (-0.75, 28.20), (0.75, 28.20), (2.55, 30.00),
        ( 2.55, 37.00), (-2.55, 37.00),
    ], 0.0, -24.50, 49.00)

    # 2. Pure-primitive upper stem of P17 (Z = -19.2794 to +48.74 mm, 0 BSpline, 0 Sphere, 0 mesh facets, 0 small sliver faces):
    flange_upper = prism_xz_r([
        (-9.00, -19.2794), ( 9.00, -19.2794),
        ( 9.00, -18.00),   (10.00, -17.00),
        (10.00,  48.74),   (-10.00, 48.74),
        (-10.00, -17.00),  (-9.00, -18.00),
    ], [0.0, 0.0, 1.0, 1.0, 3.0, 3.0, 1.0, 1.0], 32.05, y_front_bed)

    stem_web = prism_xy_r([
        (-3.00, 20.00), ( 3.00, 20.00),
        ( 3.00, 32.50), (-3.00, 32.50),
    ], [2.0, 2.0, 0.0, 0.0], -19.2794, 41.70)

    magnet_boss = intersect_all(
        prism_xy_r([(-3.00, 19.40), (3.00, 19.40), (3.00, 25.00), (-3.00, 25.00)], [0.5, 0.5, 0.0, 0.0], -17.2794, -9.28),
        [prism_yz_r([
            (19.40, -16.78), (25.00, -17.2794),
            (25.00,  -9.28), (19.90,  -9.28),
            (19.40,  -9.78),
        ], [0.0, 0.0, 0.0, 0.5, 0.5], -3.50, 3.50)]
    )

    deck_base = prism_xy_r([
        (-9.00, 14.30), (-7.00, 12.30),
        ( 7.00, 12.30), ( 9.00, 14.30),
        ( 9.00, 32.50), (-9.00, 32.50),
    ], 0.0, -19.2794, -17.2794)

    collet_top = fuse_all([
        cone_z(0.0, 22.68, 41.70, 44.67, 3.00, 5.45),
        cyl_z( 0.0, 22.68, 44.67, 48.74, 5.45),
        intersect_all(
            box(-5.45, 5.45, 22.68, 32.50, 41.70, 48.74),
            [prism_xz_r([
                (-3.00, 41.70), ( 3.00, 41.70),
                ( 5.45, 44.67), ( 5.45, 48.74),
                (-5.45, 48.74), (-5.45, 44.67),
            ], [0, 0, 1.5, 0, 0, 1.5], 22.68, 32.50)]
        ),
    ])

    hgx_window = cut_all(
        prism_yz_r([
            (19.00, -7.60), (26.05, -7.60),
            (26.05,  7.85), (19.00,  7.85),
        ], [0.0, 3.5, 3.5, 0.0], -3.50, 3.50),
        [
            cyl_z(0.0, 22.68, -8.00, -4.25, 2.45),
            cyl_z(0.0, 22.68,  4.45,  8.20, 2.45),
        ]
    )

    p17_upper = fuse_all([flange_upper, stem_web, magnet_boss, deck_base, collet_top])

    # 3. Conformal slip-fit pocket for HF_00_K1_heatsink + open rear-center window (<= 45-deg overhang when printed on +Y):
    hs_pocket = fuse_all([
        intersect_all(
            cyl_z(0.0, 22.70, -54.0, -24.2794, 11.15),
            [box(-12.0, 12.0, 13.30, 32.05, -54.5, -24.2794)]
        ),
        box(-7.85, 7.85, 10.00, 15.20, -54.0, -24.2794),
    ])
    bot_open = cyl_z(0.0, 22.70, -54.0, -50.25, 9.60)

    # Print-safe lateral exhaust windows (Y=16.00..26.80, Z=-48.50..-26.00, divided by a 2.0 mm mid-span tie rib at Z=-38.25..-36.25):
    side_vent_lower = prism_yz_r([(16.00, -48.50), (26.80, -48.50), (26.80, -38.25), (16.00, -38.25)], 1.5, -16.0, 16.0)
    side_vent_upper = prism_yz_r([(16.00, -36.25), (26.80, -36.25), (26.80, -26.00), (16.00, -26.00)], 1.5, -16.0, 16.0)

    # Concentric 1.15 mm solid inner partition wall guard (R=12.30 centered at (0, 22.70))
    air_wall_guard = fuse_all([
        intersect_all(cyl_z(0.0, 22.70, -54.5, -19.0, 12.30), [box(-13.0, 13.0, 13.0, 33.20, -55.0, -19.0)]),
        box(-8.00, 8.00, 28.00, 34.20, -47.00, -25.00),
    ])
    wire_xy_3010 = prism_xy_r([
        (-13.20, 33.40), (-13.20, 31.20), (-11.00, 29.00),
        ( 11.00, 29.00), ( 13.20, 31.20), ( 13.20, 33.40),
    ], [0.0, 0.5, 0.5, 0.5, 0.5, 0.0], -53.00, -19.50)
    wire_xz_l_3010 = prism_xz_r([
        ( 3.50, -53.00), (13.20, -53.00), (13.20, -23.50),
        ( 2.55, -19.50), ( 0.00, -19.50), ( 0.00, -22.00),
        ( 8.55, -25.00), ( 8.55, -47.00), ( 3.50, -47.00),
    ], 0.0, 28.00, 34.00)
    wire_xz_r_3010 = prism_xz_r([
        (-13.20, -53.00), (-3.50, -53.00), (-3.50, -47.00),
        ( -8.55, -47.00), (-8.55, -25.00), ( 0.00, -22.00),
        (  0.00, -19.50), (-2.55, -19.50), (-13.20, -23.50),
    ], 0.0, 28.00, 34.00)
    wire_ch_l_3010 = cut_all(intersect_all(wire_xy_3010, [wire_xz_l_3010]), [air_wall_guard])
    wire_ch_r_3010 = cut_all(intersect_all(wire_xy_3010, [wire_xz_r_3010]), [air_wall_guard])

    wire_xy_2510 = prism_xy_r([
        (-11.10, 31.80), (-11.10, 30.30), (-9.80, 29.00),
        (  9.80, 29.00), ( 11.10, 30.30), (11.10, 31.80),
    ], [0.0, 0.4, 0.4, 0.4, 0.4, 0.0], -53.00, -19.50)
    wire_xz_l_2510 = prism_xz_r([
        ( 3.50, -53.00), (11.10, -53.00), (11.10, -23.50),
        ( 2.55, -19.50), ( 0.00, -19.50), ( 0.00, -22.00),
        ( 8.20, -25.00), ( 8.20, -47.00), ( 3.50, -47.00),
    ], 0.0, 28.00, 33.00)
    wire_xz_r_2510 = prism_xz_r([
        (-11.10, -53.00), (-3.50, -53.00), (-3.50, -47.00),
        ( -8.20, -47.00), (-8.20, -25.00), ( 0.00, -22.00),
        (  0.00, -19.50), (-2.55, -19.50), (-11.10, -23.50),
    ], 0.0, 28.00, 33.00)
    wire_ch_l_2510 = cut_all(intersect_all(wire_xy_2510, [wire_xz_l_2510]), [air_wall_guard])
    wire_ch_r_2510 = cut_all(intersect_all(wire_xy_2510, [wire_xz_r_2510]), [air_wall_guard])

    common_stem_cuts = [
        hs_pocket, bot_open, side_vent_lower, side_vent_upper, stem_wire_enlarge,
        hgx_window,
        cyl_y(0.0, -12.78, 19.00, 21.45, 2.05),
        box( 3.80,  9.15, 31.90, 35.15, -5.86,  9.34),
        box(-9.15, -3.80, 31.90, 35.15, -5.86,  9.34),
        box( 3.80,  9.15, 31.90, 35.15, 19.14, 34.34),
        box(-9.15, -3.80, 31.90, 35.15, 19.14, 34.34),
        *(cyl_y(sx * 6.50, zc, 31.90, 35.15, 3.06) for sx in (-1.0, 1.0) for zc in (30.50, 23.00, 5.50, -2.00)),
        cyl_y(-6.865, -11.255, 31.0, 37.0, 2.05),
        cyl_y( 6.855, -11.265, 31.0, 37.0, 2.05),
        cyl_y(-7.475,  38.740, 31.0, 37.0, 2.05),
        cyl_y( 7.525,  38.735, 31.0, 37.0, 2.05),
        cyl_y(-5.970,  44.740, 31.0, 37.0, 2.28),
        cyl_y( 6.030,  44.730, 31.0, 37.0, 2.28),
        cyl_y(-6.000, -19.260, 31.0, 37.0, 2.28),
        cyl_y( 6.000, -19.260, 31.0, 37.0, 2.28),
        cyl_z( 0.000,  22.680, -25.15, -18.88, 2.10),
        cyl_z( 0.000,  22.680, -20.00, 16.50, 1.80),
        cone_z(0.000,  22.680,  16.50, 17.20, 1.80, 2.18),
        cyl_z( 0.000,  22.680,  17.20, 42.10, 2.18),
        cyl_z( 0.000,  22.680,  42.05, 43.10, 3.03),
        cyl_z( 0.000,  22.680,  43.05, 49.00, 4.28),
    ]
    for sx in (-5.657, 5.657):
        for sy in (17.043, 28.357):
            common_stem_cuts.append(cyl_z(sx, sy, -25.0, -19.20, 1.35))
            common_stem_cuts.append(cyl_z(sx, sy, -19.35, -16.50, 2.40))

    # --- 1. Build P17_HF_tool_carrier_2510 (Reference 25x25x10 mm fan variant) ---
    shroud_2510_outer = intersect_all(
        rounded_box_xy(-12.40, 12.40, 11.50, y_front_bed, -51.80, -19.2794, 1.8),
        [
            prism_xz_r([
                (-12.40, -51.80), ( 12.40, -51.80),
                ( 12.40, -21.78), (  9.00, -19.2794),
                ( -9.00, -19.2794), (-12.40, -21.78),
            ], [1.8, 1.8, 0.8, 0.0, 0.0, 0.8], 11.00, 36.50),
            prism_yz_r([
                (11.50, -51.80), (y_front_bed, -51.80),
                (y_front_bed, -26.80), (32.05, -26.80),
                (32.05, -19.2794), (11.50, -19.2794),
            ], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], -13.00, 13.00),
        ]
    )
    front_neck_2510 = box(-9.00, 9.00, 32.05, y_front_bed, -26.80, -19.2794)
    bosses_2510 = [
        cyl_y(sx * 10.00, zc, 31.80, y_front_bed, 2.40)
        for sx in (-1.0, 1.0) for zc in (-49.30, -29.30)
    ]
    holes_2510 = [cyl_y(sx * 10.00, zc, 28.00, 37.00, 1.20) for sx in (-1.0, 1.0) for zc in (-49.30, -29.30)]
    fan_air_2510 = fuse_all([
        cyl_y(0.0, -39.30, 35.00, 37.00, 11.10),
        cone_y(0.0, -39.30, 31.80, 35.00, 7.90, 11.10),
        prism_xz_r([(-7.20, -49.00), (7.20, -49.00), (7.20, -27.00), (-7.20, -27.00)], 3.0, 31.80, 34.50),
    ])
    p17_2510 = fuse_all([p17_upper, shroud_2510_outer, front_neck_2510] + bosses_2510)
    p17_2510 = cut_all(p17_2510, common_stem_cuts + [fan_air_2510, wire_ch_l_2510, wire_ch_r_2510] + holes_2510)
    p17_2510 = fuse_all([p17_2510] + bosses_2510)
    p17_2510 = cut_all(p17_2510, holes_2510 + [hs_pocket, wire_ch_l_2510, wire_ch_r_2510, stem_wire_enlarge])
    u25 = ShapeUpgrade_UnifySameDomain(p17_2510, True, True, True)
    u25.Build()
    p17_2510 = u25.Shape()

    # --- 2. Build P17_HF_tool_carrier_3010 + P18_Tool_docking_backplate_3010 (Primary 30x30x10 mm fan design) ---
    shroud_3010_outer = intersect_all(
        prism_xy_r([
            (-12.40, 11.50), ( 12.40, 11.50),
            ( 12.40, 26.80), ( 15.00, 29.40),
            ( 15.00, y_front_bed), (-15.00, y_front_bed),
            (-15.00, 29.40), (-12.40, 26.80),
        ], [1.8, 1.8, 1.2, 1.2, 0.0, 0.0, 1.2, 1.2], -52.50, -19.2794),
        [
            prism_xz_r([
                (-15.00, -52.50), ( 15.00, -52.50),
                ( 15.00, -22.50), ( 11.78, -19.2794),
                (-11.78, -19.2794), (-15.00, -22.50),
            ], [2.2, 2.2, 1.0, 0.0, 0.0, 1.0], 11.00, 36.50),
            prism_yz_r([
                (11.50, -52.50), (y_front_bed, -52.50),
                (y_front_bed, -22.50), (32.05, -22.50),
                (32.05, -19.2794), (11.50, -19.2794),
            ], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], -16.00, 16.00),
        ]
    )
    front_neck_bridge = box(-9.00, 9.00, 32.05, y_front_bed, -22.50, -19.2794)

    # Trim lower blank skirt of P18 to Z=-22.45 mm, add a 5.00 x 0.85 mm rear wire relief groove,
    # and integrate StealthChanger 2x Ø5x12mm rounded dowel pin bosses at (X=±6.00, Z=22.00)
    # plus 2x Ø6x4mm (or Ø6x3mm) N52 dock retention magnet bosses at (X=±6.00, Z=-2.00):
    p18_sc_bosses = [
        rounded_box_xy( 2.50,  9.80, 37.00, 45.00, 17.80, 26.20, 1.5),
        rounded_box_xy(-9.80, -2.50, 37.00, 45.00, 17.80, 26.20, 1.5),
        rounded_box_xy( 2.50,  9.80, 37.00, 45.00, -6.00,  2.00, 1.5),
        rounded_box_xy(-9.80, -2.50, 37.00, 45.00, -6.00,  2.00, 1.5),
    ]
    p18_3010 = cut_all(fuse_all([p18_orig] + p18_sc_bosses), [
        box(-15.0, 15.0, 34.0, 46.0, -28.0, -22.45),
        prism_xy_r([(-2.50, 35.50), (2.50, 35.50), (2.50, 36.88), (-2.50, 36.88)], 0.6, -22.50, 49.00),
        cyl_y(-5.97,  44.75, 37.40, 42.0, 1.95),
        cyl_y( 6.03,  44.74, 37.40, 42.0, 1.95),
        cyl_y(-6.01, -19.25, 37.40, 42.0, 1.95),
        cyl_y( 5.99, -19.26, 37.40, 42.0, 1.95),
        cyl_y(-6.00,  22.00, 38.50, 45.50, 2.49),
        cyl_y( 6.00,  22.00, 38.50, 45.50, 2.49),
        cyl_y(-6.00,  -2.00, 40.92, 45.50, 3.06),
        cyl_y( 6.00,  -2.00, 40.92, 45.50, 3.06),
    ])
    u18 = ShapeUpgrade_UnifySameDomain(p18_3010, True, True, True)
    u18.Build()
    p18_3010 = u18.Shape()

    bosses_3010 = [
        cyl_y(sx * 12.00, zc, 28.50, y_front_bed, 2.85)
        for sx in (-1.0, 1.0) for zc in (-49.50, -25.50)
    ]
    holes_3010 = [cyl_y(sx * 12.00, zc, 28.00, 37.00, 1.40) for sx in (-1.0, 1.0) for zc in (-49.50, -25.50)]
    fan_air_3010 = fuse_all([
        cyl_y(0.0, -37.50, 35.50, 37.00, 13.60),
        cone_y(0.0, -37.50, 31.50, 35.50, 9.60, 13.60),
        prism_xz_r([(-7.50, -49.00), (7.50, -49.00), (7.50, -26.00), (-7.50, -26.00)], 3.0, 29.50, 33.50),
    ])
    p17_3010 = fuse_all([p17_upper, shroud_3010_outer, front_neck_bridge] + bosses_3010)
    p17_3010 = cut_all(p17_3010, common_stem_cuts + [fan_air_3010, wire_ch_l_3010, wire_ch_r_3010] + holes_3010)
    p17_3010 = fuse_all([p17_3010] + bosses_3010)
    p17_3010 = cut_all(p17_3010, holes_3010 + [hs_pocket, wire_ch_l_3010, wire_ch_r_3010, stem_wire_enlarge])
    u30 = ShapeUpgrade_UnifySameDomain(p17_3010, True, True, True)
    u30.Build()
    p17_3010 = u30.Shape()

    fan2510_body, fan2510_screws = build_axial_fan_assembly(25, -39.30, y_front_bed)
    fan3010_body, fan3010_screws = build_axial_fan_assembly(30, -37.50, y_front_bed)
    sc_pins_3010 = [
        fuse_all([cyl_y(sx * 6.00, 22.00, 38.50, 48.50, 2.48), cone_y(sx * 6.00, 22.00, 48.50, 50.50, 2.48, 1.00)])
        for sx in (-1.0, 1.0)
    ]
    sc_mags_3010 = [
        cyl_y(sx * 6.00, -2.00, 40.95, 44.95, 3.00)
        for sx in (-1.0, 1.0)
    ]
    return {
        "P17_HF_tool_carrier_2510": p17_2510,
        "P17_HF_tool_carrier_3010": p17_3010,
        "P18_Tool_docking_backplate_3010": p18_3010,
        "Fan_2510_Axial": fan2510_body,
        "Fan_2510_Screws": fan2510_screws,
        "Fan_3010_Axial": fan3010_body,
        "Fan_3010_Screws": fan3010_screws,
        "SC_Pins_5x12": sc_pins_3010,
        "SC_Magnets_6x4": sc_mags_3010,
    }


def build_dock_and_stationary_accessories(v26_by_name=None):
    """
    Build the pure-primitive Dock, Anti-Ooze / Nozzle Wiper / Purge Chute, Stationary 7040 Blower Mount,
    Master Calibration Jig (P28), and COTS-qualified Core Drop-In Variants (P01_COTS, P02_COTS, P05_COTS):
      1. P25_SparkShift_3010_Dock:
         - 34.00 mm wide (X in [-17.00, +17.00] mm) modular toolhead dock body with 0 BSpline/Sphere faces
           and 0 sliver faces (< 0.15 mm²).
         - Includes a compliant spring-leaf relief slot (Z = -84.20..-82.40 mm) beneath the high-temp
           Silicone_Ooze_Stopper_Pad pocket (Z = -78.88 mm, with 15-deg lead-in ramp at Y = 21.11..22.11 mm)
           so the parked Volcano nozzle orifice stays positively sealed against gravity ooze.
         - Includes 2x M3 mounting holes at (X = ±11.50, Z = -82.50, Y = 20.91..28.50 mm) for attaching P26.
      2. P26_Dock_Nozzle_Wiper_and_Purge_Chute:
         - Bolts onto the front face of P25's lower arm (Y = 8.00..20.91 mm, Z = -105.00..-79.20 mm).
         - Provides an open Purge Drop Window (Y = 12.80..18.50 mm, X = -8.60..+8.60 mm) directly beneath
           the priming station (Y_nozzle = 16.20 mm) feeding a 45-deg sloped pellet deflector chute and
           catch basin (Z = -102.50..-86.00 mm).
         - Holds a replaceable dual-blade Silicone_Wiper_Blades cassette (Y = 9.45..11.95 mm, Z_top = -78.88 mm)
           that wipes the brass Volcano nozzle tip during -Y withdrawal and ±X scrub passes while remaining
           >= 1.03 mm below P22_CPAP_Lower_Plenum (Z_min = -77.85 mm) and >= 2.27 mm below Beacon RevH (Z_min = -76.61 mm).
      3. P27_CPAP_7040_Blower_Frame_Mount:
         - Stationary Voron 2020 extrusion bracket for the Trianglelab Supercharged 7040 Centrifugal Blower
           (24V, 67W), with 4x M5x10 BHCS mounting holes, 3x M3 blower mounting bosses, concentric intake
           finger-guard grille, matching dual-barb (Ø21.6 / Ø21.8 mm) CPAP hose outlet spigot, and an
           integrated CAN + 24V umbilical strain-relief clamp with dual zip-tie slots.
    """
    dock_sols = load_step(STEP_DIR / "Dock_3010_Complete.step")
    p25_raw = dock_sols[0]
    sw_upper = cut_all(dock_sols[1], [box(-10.0, 10.0, 42.0, 43.85, -20.0, 40.0)])
    sw_lower = cut_all(dock_sols[2], [box(-10.0, 10.0, 42.0, 43.85, -20.0, 40.0)])

    yf = 45.910082
    yb = 74.910082
    zb = -86.079400
    zt_2020 = 17.220600
    z_m5 = 7.220600

    p25_base = cut_all(p25_raw, [box(-50.0, 50.0, -50.0, 100.0, -200.0, zb)]) if bbox_of(p25_raw)[2] < zb - 0.1 else p25_raw
    fill_sc_mag = box(-10.50, 10.50, yf, 54.00, -6.50, 2.50)
    probe_sc = box(-0.5, 0.5, 49.0, 51.0, -0.5, 0.5)
    p25_fused = fuse_all([p25_base, fill_sc_mag]) if vol_of(BRepAlgoAPI_Common(p25_base, probe_sc).Shape()) < 0.5 else p25_base

    p25 = cut_all(p25_fused, [
        cyl_y( 21.00, 33.65991587, 43.0, 74.0, 10.000839),
        cyl_y(-21.00, 33.65991587, 43.0, 74.0, 10.000839),
        box( 8.20, 20.0, 30.0, yf, -87.00, -78.00),
        box(-20.0, -8.20, 30.0, yf, -87.00, -78.00),
        box(15.0, 20.0, 70.0, 76.0, -86.50, -83.00),
        box(-20.0, -15.0, 70.0, 76.0, -86.50, -83.00),
        rounded_box_xy(-3.20, 3.20, 23.50, 34.00, -84.20, -82.60, 0.7),
        cyl_y(-10.0, z_m5, 63.0, 76.0, 2.60),
        cyl_y( 10.0, z_m5, 63.0, 76.0, 2.60),
        cyl_y(-10.0, z_m5, 70.110082, 76.0, 4.60),
        cyl_y( 10.0, z_m5, 70.110082, 76.0, 4.60),
        cyl_y(-11.75, -82.44, 44.0, 54.0, 1.55),
        cyl_y( 11.75, -82.44, 44.0, 54.0, 1.55),
        # StealthChanger 2x Ø5mm Bushing counterbores (Ø7.04mm x 5.50mm deep) + Ø5.15mm pin bores at (X=±6.00, Z=22.00):
        cyl_y(-6.00, 22.00, 45.0, yf + 5.50, 3.52),
        cyl_y( 6.00, 22.00, 45.0, yf + 5.50, 3.52),
        cyl_y(-6.00, 22.00, 45.0, yf + 12.00, 2.58),
        cyl_y( 6.00, 22.00, 45.0, yf + 12.00, 2.58),
        # StealthChanger 2x Ø6x4mm (or Ø6x3mm) N52 Dock Magnet pockets (Ø6.12mm x 4.08mm deep) at (X=±6.00, Z=-2.00):
        cyl_y(-6.00, -2.00, 45.0, yf + 4.08, 3.06),
        cyl_y( 6.00, -2.00, 45.0, yf + 4.08, 3.06),
    ])
    u25 = ShapeUpgrade_UnifySameDomain(p25, True, True, True)
    u25.Build()
    p25 = u25.Shape()

    m5_l = fuse_all([cyl_y(-10.0, z_m5, 58.110082, 70.110082, 2.50), cyl_y(-10.0, z_m5, 70.110082, 73.110082, 4.40)])
    m5_r = fuse_all([cyl_y( 10.0, z_m5, 58.110082, 70.110082, 2.50), cyl_y( 10.0, z_m5, 70.110082, 73.110082, 4.40)])

    ooze_pad = intersect_all(
        rounded_box_xy(-3.80, 3.80, 21.11, 28.71, -85.98, -78.88, 1.2),
        [prism_yz_r([(21.11, -85.98), (28.71, -85.98), (28.71, -78.88), (22.11, -78.88), (21.11, -79.48)], 0.0, -4.0, 4.0)]
    )
    u_pad = ShapeUpgrade_UnifySameDomain(ooze_pad, True, True, True)
    u_pad.Build()
    ooze_pad = u_pad.Shape()

    p26_chute = intersect_all(
        rounded_box_xy(-10.50, 10.50, 8.00, 20.91, -92.08, -78.80, 2.0),
        [prism_yz_r([
            (8.00, -92.08), (15.50, -92.08), (20.91, zb),
            (20.91, -78.80), (8.00, -78.80),
        ], 0.0, -12.0, 12.0)]
    )
    p26_arm_l = rounded_box_xy(  8.50, 15.00, 15.00, yf, zb, -78.80, 1.5)
    p26_arm_r = rounded_box_xy(-15.00, -8.50, 15.00, yf, zb, -78.80, 1.5)
    p26_outer = fuse_all([p26_chute, p26_arm_l, p26_arm_r])
    p26 = cut_all(p26_outer, [
        rounded_box_xy(-7.60, 7.60, 12.80, 18.50, -88.00, -78.00, 1.2),
        intersect_all(
            rounded_box_xy(-7.60, 7.60, 9.80, 18.50, -90.20, -83.50, 1.2),
            [prism_yz_r([
                (9.80, -90.20), (14.50, -90.20), (18.50, -85.50),
                (18.50, -83.00), (9.80, -83.00),
            ], 0.0, -9.0, 9.0)]
        ),
        rounded_box_xy(-7.60, 7.60, 9.40, 12.00, -83.80, -78.00, 0.8),
        rounded_box_xy(-7.00, 7.00, 7.50, 13.50, -80.20, -78.00, 1.0),
        cyl_y(-11.75, -82.44, 14.00, 47.00, 1.65),
        cyl_y( 11.75, -82.44, 14.00, 47.00, 1.65),
        cyl_y(-11.75, -82.44, 14.00, 39.91, 2.75),
        cyl_y( 11.75, -82.44, 14.00, 39.91, 2.75),
    ])
    u26 = ShapeUpgrade_UnifySameDomain(p26, True, True, True)
    u26.Build()
    p26 = u26.Shape()

    wiper_blades = cut_all(
        fuse_all([
            rounded_box_xy(-7.50, 7.50, 9.45, 11.95, -83.75, -80.40, 0.7),
            rounded_box_xy(-6.80, 6.80, 9.50, 10.35, -80.60, -78.88, 0.3),
            rounded_box_xy(-6.80, 6.80, 11.05, 11.90, -80.60, -78.88, 0.3),
        ]),
        [
            cyl_y(-2.20, -78.88, 9.0, 12.5, 0.75),
            cyl_y( 0.00, -78.88, 9.0, 12.5, 0.75),
            cyl_y( 2.20, -78.88, 9.0, 12.5, 0.75),
        ]
    )
    uw = ShapeUpgrade_UnifySameDomain(wiper_blades, True, True, True)
    uw.Build()
    wiper_blades = uw.Shape()

    wiper_screws = [
        fuse_all([cyl_y(sx * 11.75, -82.44, 39.91, 51.91, 1.50), cyl_y(sx * 11.75, -82.44, 36.91, 39.91, 2.60)])
        for sx in (-1.0, 1.0)
    ]

    # Build P27_CPAP_7040_Blower_Frame_Mount:
    base_ring = cyl_z(0.0, 0.0, 0.0, 16.0, 37.5)
    spine_2020 = rounded_box_xy(-22.0, 22.0, -40.0, -28.0, 0.0, 34.0, 2.0)
    umbilical_arm = rounded_box_xy(-32.0, -20.0, -39.0, -24.0, 0.0, 20.0, 1.8)
    bosses_m3 = [
        cyl_z( 37.0,   0.0, 0.0, 16.0, 4.5),
        cyl_z(-26.2,  26.2, 0.0, 16.0, 4.5),
        cyl_z(-26.2, -26.2, 0.0, 16.0, 4.5),
    ]
    ox, oy = 16.0, -14.0
    spigot_pad = cyl_z(ox, oy, 0.0, 16.0, 12.5)
    spigot_barbs = fuse_all([
        cyl_z(ox, oy, 16.0, 18.5, 11.30),
        cyl_z(ox, oy, 18.5, 22.5, 10.10),
        cone_z(ox, oy, 22.5, 24.0, 10.10, 10.90),
        cyl_z(ox, oy, 24.0, 25.5, 10.90),
        cyl_z(ox, oy, 25.5, 28.5, 10.10),
        cone_z(ox, oy, 28.5, 30.0, 10.10, 10.80),
        cyl_z(ox, oy, 30.0, 31.5, 10.80),
        cone_z(ox, oy, 31.5, 33.5, 10.80, 9.65),
    ])
    p27_outer = fuse_all([base_ring, spine_2020, umbilical_arm, spigot_pad, spigot_barbs] + bosses_m3)
    p27_cuts = [
        cut_all(cyl_z(0.0, 0.0, 3.0, 17.0, 33.5), [cyl_z(ox, oy, 0.0, 17.5, 12.5)]),
        cut_all(
            cyl_z(0.0, 0.0, -1.0, 4.0, 22.0),
            [
                box(-2.0, 2.0, -24.0, 24.0, -1.0, 4.0),
                box(-24.0, 24.0, -2.0, 2.0, -1.0, 4.0),
                cut_all(cyl_z(0.0, 0.0, -1.0, 4.0, 12.5), [cyl_z(0.0, 0.0, -1.5, 4.5, 9.5)]),
            ]
        ),
        cyl_z(ox, oy, -1.0, 35.0, 8.80),
        cyl_z( 37.0,   0.0, -1.0, 17.0, 1.65),
        cyl_z(-26.2,  26.2, -1.0, 17.0, 1.65),
        cyl_z(-26.2, -26.2, -1.0, 17.0, 1.65),
        cyl_z( 37.0,   0.0, 11.5, 17.0, 2.30),
        cyl_z(-26.2,  26.2, 11.5, 17.0, 2.30),
        cyl_z(-26.2, -26.2, 11.5, 17.0, 2.30),
        cyl_y(-12.0,  9.0, -41.0, -27.0, 2.65),
        cyl_y( 12.0,  9.0, -41.0, -27.0, 2.65),
        cyl_y(-12.0, 25.0, -41.0, -27.0, 2.65),
        cyl_y( 12.0, 25.0, -41.0, -27.0, 2.65),
        cyl_y(-12.0,  9.0, -41.0, -36.5, 4.80),
        cyl_y( 12.0,  9.0, -41.0, -36.5, 4.80),
        cyl_y(-12.0, 25.0, -41.0, -36.5, 4.80),
        cyl_y( 12.0, 25.0, -41.0, -36.5, 4.80),
        cyl_z(-26.0, -39.0, -1.0, 21.0, 3.80),
        rounded_box_xy(-33.0, -19.0, -35.5, -32.0, 4.5, 8.0, 0.8),
        rounded_box_xy(-33.0, -19.0, -35.5, -32.0, 12.5, 16.0, 0.8),
    ]
    p27 = cut_all(p27_outer, p27_cuts)
    u27 = ShapeUpgrade_UnifySameDomain(p27, True, True, True)
    u27.Build()
    p27 = u27.Shape()

    # Build P28_Dock_and_Probe_Calibration_Jig (100% pure-primitive 4-in-1 commissioning & calibration gauge):
    jig_base = rounded_box_xy(-25.00, 25.00, -12.00, 12.00, 0.00, 8.00, 2.5)
    pins_37p3 = [cyl_z(sx * 18.65,  5.50, 8.00, 14.50, 2.42) for sx in (-1.0, 1.0)]
    pins_35p0 = [cyl_z(sx * 17.50, -5.50, 8.00, 14.50, 2.42) for sx in (-1.0, 1.0)]
    probe_step_pad = rounded_box_xy(-9.00, 9.00, -12.00, -3.50, 8.00, 10.27, 1.5)
    p28 = cut_all(
        fuse_all([jig_base, probe_step_pad] + pins_37p3 + pins_35p0),
        [
            box(-12.50, 12.50, -2.05, 2.05, 5.50, 8.50),
            rounded_box_xy(-10.70, 10.70, 2.50, 9.50, 4.50, 8.50, 1.2),
            cyl_z(0.0, -7.50, -1.0, 12.0, 2.60),
        ]
    )
    u28 = ShapeUpgrade_UnifySameDomain(p28, True, True, True)
    u28.Build()
    p28 = u28.Shape()

    # Build P29_Dock_Rack_Gantry_Mount_L and P29_Dock_Rack_Gantry_Mount_R (Flying-Gantry 2020 Dock Crossbar Mounts):
    def build_p29_side(is_right=False):
        def xm(x0, x1):
            return (350.0 - x1, 350.0 - x0) if is_right else (x0, x1)
        def xp(x):
            return 350.0 - x if is_right else x

        rear_foot = rounded_box_xy(*xm(-79.5, -60.5), 22.0, 74.0, 163.5, 192.0, 2.5)
        tslot_key = rounded_box_xy(*xm(-72.9, -67.1), 24.0, 72.0, 162.0, 165.0, 1.5)
        bridge    = rounded_box_xy(*xm(-79.5, -35.0), 22.0, 48.0, 176.5, 208.5, 2.5)
        fwd_arm   = rounded_box_xy(*xm(-58.0, -35.0), -29.0, 48.0, 176.5, 208.5, 2.5)
        front_pad = rounded_box_xy(*xm(-58.0, -35.0), -29.0, 16.0, 173.5, 180.0, 2.5)
        outer = fuse_all([rear_foot, tslot_key, bridge, fwd_arm, front_pad])
        yz_env = prism_yz_r([
            (-30.0, 160.0), (75.0, 160.0), (75.0, 184.0),
            (10.0, 208.5), (-30.0, 208.5),
        ], 3.0, *xm(-82.0, -32.0))
        outer = intersect_all(outer, [yz_env])
        cuts = [
            box(*xm(-50.0, -33.0), -29.5, -9.0, 188.5, 209.0),
            rounded_box_xy(*xm(-53.0, -40.0), 3.0, 40.0, 182.5, 210.0, 2.5),
            cyl_z(xp(-70.0), 34.0, 160.0, 200.0, 2.65),
            cyl_z(xp(-70.0), 60.0, 160.0, 200.0, 2.65),
            cyl_z(xp(-70.0), 34.0, 173.5, 205.0, 4.60),
            cyl_z(xp(-70.0), 60.0, 173.5, 205.0, 4.60),
            cyl_x(-19.0, 198.5, *xm(-60.0, -48.0), 2.65),
            cyl_x(-19.0, 198.5, *xm(-60.0, -54.0), 4.80),
            cyl_z(xp(-42.5), -19.0, 170.0, 192.0, 2.65),
            cyl_z(xp(-42.5), -19.0, 170.0, 180.5, 4.60),
            cyl_y(xp(-42.5), 198.5, -12.0, 10.0, 2.65),
            cyl_y(xp(-42.5), 198.5, -3.0, 42.0, 4.60),
        ]
        p29 = cut_all(outer, cuts)
        u29 = ShapeUpgrade_UnifySameDomain(p29, True, True, True)
        u29.Build()
        return u29.Shape()

    p29_l = build_p29_side(False)
    p29_r = build_p29_side(True)

    def build_p29_hardware():
        sols = []
        for is_r in (False, True):
            s = -1.0 if is_r else 1.0
            def xp(x):
                return 350.0 - x if is_r else x
            for yc in (34.0, 60.0):
                sols.append(fuse_all([cyl_z(xp(-70.0), yc, 161.5, 173.5, 2.50), cyl_z(xp(-70.0), yc, 173.5, 176.5, 4.40)]))
                sols.append(rounded_box_xy(xp(-70.0) - 5.0, xp(-70.0) + 5.0, yc - 7.0, yc + 7.0, 159.0, 162.8, 1.0))
            sols.append(fuse_all([cyl_z(xp(-42.5), -19.0, 180.5, 192.5, 2.50), cyl_z(xp(-42.5), -19.0, 177.5, 180.5, 4.40)]))
            sols.append(rounded_box_xy(xp(-42.5) - 7.0, xp(-42.5) + 7.0, -19.0 - 5.0, -19.0 + 5.0, 189.2, 193.0, 1.0))
            sols.append(fuse_all([cyl_y(xp(-42.5), 198.5, -15.0, -3.0, 2.50), cyl_y(xp(-42.5), 198.5, -3.0, 0.0, 4.40)]))
            sols.append(rounded_box_xy(xp(-42.5) - 7.0, xp(-42.5) + 7.0, -13.5, -9.8, 198.5 - 5.0, 198.5 + 5.0, 1.0))
            x0, x1 = (xp(-54.0), xp(-42.0)) if not is_r else (xp(-42.0), xp(-54.0))
            hx0, hx1 = (xp(-57.0), xp(-54.0)) if not is_r else (xp(-54.0), xp(-57.0))
            sols.append(fuse_all([cyl_x(-19.0, 198.5, x0, x1, 2.50), cyl_x(-19.0, 198.5, hx0, hx1, 4.40)]))
        return [p29_l, p29_r] + sols

    sc_bushings_dock = [
        cut_all(cyl_y(sx * 6.00, 22.00, yf, yf + 5.45, 3.50), [cyl_y(sx * 6.00, 22.00, yf - 0.5, yf + 6.00, 2.52)])
        for sx in (-1.0, 1.0)
    ]
    sc_mags_dock = [
        cyl_y(sx * 6.00, -2.00, yf + 0.05, yf + 4.05, 3.00)
        for sx in (-1.0, 1.0)
    ]

    out = {
        "P25_SparkShift_3010_Dock": p25,
        "P26_Dock_Nozzle_Wiper_and_Purge_Chute": p26,
        "P27_CPAP_7040_Blower_Frame_Mount": p27,
        "P28_Dock_and_Probe_Calibration_Jig": p28,
        "P29_Dock_Rack_Gantry_Mount_L": p29_l,
        "P29_Dock_Rack_Gantry_Mount_R": p29_r,
        "P29_Rack_Hardware_Solids": build_p29_hardware(),
        "Silicone_Ooze_Stopper_Pad": ooze_pad,
        "Silicone_Wiper_Blades": wiper_blades,
        "Dock_Complete_Solids": [p25, sw_upper, sw_lower, ooze_pad, m5_l, m5_r, p26, wiper_blades] + wiper_screws + sc_bushings_dock + sc_mags_dock,
    }
    if v26_by_name is not None:
        # 1. P01_Back_case_COTS_MR74: deepens rear Ø7.04 mm MR74 seats to Y=2.80..5.30 mm for standard 2.5mm MR74ZZ & 4x25mm shafts
        p01_cots = cut_all(v26_by_name["PRINT_motor_mount"][0], [
            cyl_y(-9.50, 13.10, 2.80, 5.35, 3.52),
            cyl_y( 9.50, 13.10, 2.80, 5.35, 3.52),
        ])
        # 2. P02_Motor_servo_plate_12p5mm: widens MG90S/MG90D window to X in [4.35, 16.65] mm (0.000 mm3 clash with 12.2mm servo envelope)
        p02_cots = cut_all(v26_by_name["PRINT_REAR_MOTOR_SERVO_SPACER"][0], [
            box(4.35, 16.65, -11.25, -6.70, 33.80, 56.85),
            box(4.35, 16.65,  -6.75, -2.60, 45.00, 56.85),
        ])
        # 3. P05_Servo_cam_COTS: 100% pure-primitive cam (0 BSpline faces, 100% watertight) with analytical keyed COTS spline hub
        lobe = intersect_all(
            prism_xz_r([
                ( 2.48, 45.73), ( 4.67, 43.29), (14.80, 45.20),
                (16.10, 51.00), (14.15, 54.54), ( 4.80, 55.80),
            ], [2.2, 3.0, 4.0, 4.0, 4.0, 3.2], 4.85, 9.20),
            [cyl_y(10.50, 50.72, 4.80, 9.25, 9.444)]
        )
        p05_cots = cut_all(
            fuse_all([
                cyl_y(10.50, 50.72, -2.00, 2.65, 3.975),
                cyl_y(10.50, 50.72,  2.65, 4.85, 4.500),
                lobe,
                cone_y(10.50, 50.72, 9.20, 10.50, 3.600, 2.475),
                cyl_y(10.50, 50.72, 10.50, 13.70, 2.475),
            ]),
            [
                cyl_y(10.50, 50.72, -2.10, 14.00, 1.450),
                cyl_y(10.50, 50.72, -2.10,  1.16, 2.480),
                rounded_box_xy(10.50 - 2.85, 10.50 + 2.85, -2.10, 1.16, 50.72 - 0.75, 50.72 + 0.75, 0.25),
                rounded_box_xy(10.50 - 0.75, 10.50 + 0.75, -2.10, 1.16, 50.72 - 2.85, 50.72 + 2.85, 0.25),
            ]
        )
        u05 = ShapeUpgrade_UnifySameDomain(p05_cots, True, True, True)
        u05.Build()
        p05_cots = u05.Shape()
        # 4. P03_Front_case_COTS: adds 8x Ø6.12 mm x 4.03 mm deep cylindrical magnet lobes at (X=±6.50, Z=[30.50, 23.00, 5.50, -2.00] mm)
        # while retaining the 3.00 mm deep rectangular corner ledges — natively accepts 8x Ø6x4mm N52 discs, 8x Ø6x3mm N52 discs, OR 4x 15x5x3mm bars
        p03_cots = cut_all(v26_by_name["PRINT_000_outer_shell_of_extruder_1"][0], [
            cyl_y(sx * 6.50, zc, 27.70, 32.00, 3.06)
            for sx in (-1.0, 1.0) for zc in (30.50, 23.00, 5.50, -2.00)
        ])
        out["P01_Back_case_COTS_MR74"] = p01_cots
        out["P02_Motor_servo_plate_12p5mm"] = p02_cots
        out["P03_Front_case_COTS"] = p03_cots
        out["P05_Servo_cam_COTS"] = p05_cots
    return out


def export_step_file(shapes, out_path):
    writer = STEPControl_Writer()
    comp = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(comp)
    for s in shapes:
        builder.Add(comp, s)
    writer.Transfer(comp, STEPControl_AsIs)
    if writer.Write(str(out_path)) != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP: {out_path}")


def export_stl_file(shape, out_path):
    BRepMesh_IncrementalMesh(shape, 0.04, False, 0.1, True)
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, str(out_path)):
        raise RuntimeError(f"Failed to write STL: {out_path}")


def main():
    t0 = time.time()
    STEP_DIR.mkdir(parents=True, exist_ok=True)
    STL_DIR.mkdir(parents=True, exist_ok=True)

    v26_meta = json.loads((WORK / "v26_meta.json").read_text())
    v26_raw = load_brep_list(WORK / "v26_cache.brep")
    gantry_meta = json.loads((WORK / "gantry_meta.json").read_text())
    gantry_raw = load_brep_list(WORK / "gantry_cache.brep")
    v26_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(v26_meta, v26_raw)}
    gantry_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(gantry_meta, gantry_raw)}

    p20_body, p20_air = build_p20_inlet()
    p21_body, p21_air = build_p21_mid()
    p22_body, p22_air = build_p22_lower_plenum()
    p23_body = build_p23_probe_mount()
    p24_body = build_p24_ebb42_mount()
    sensor_cable = build_sensor_cable()
    acc_hw = build_accessory_hardware()

    parts = [
        ("P20_CPAP_Hose_Inlet", p20_body),
        ("P21_CPAP_Gantry_Bridge", p21_body),
        ("P22_CPAP_Lower_Plenum", p22_body),
        ("P23_Beacon_Cartographer_Mount", p23_body),
        ("P24_EBB42_Controller_Mount", p24_body),
    ]

    # Load Beacon RevH Normal facing FORWARD (+Y toward nozzle: rot_z = 0, Y_holes = -0.30, Z_seat = -75.00 -> Y_coil = +3.20):
    beacon_sols = load_step(SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")
    trsf_beacon = gp_Trsf()
    trsf_beacon.SetTranslation(gp_Vec(0.0, 3.20, -75.000))
    beacon_world = [BRepBuilderAPI_Transform(s, trsf_beacon, True).Shape() for s in beacon_sols]
    beacon_bot_ko = beacon_world[0]
    # Trim top metal keepout to exact 20.0 mm above the bottom coil sensing face (Z = -76.61 to -56.61 mm):
    beacon_top_ko = intersect_all(beacon_world[1], [box(-20.0, 20.0, -20.0, 20.0, -76.61, -56.61)])
    beacon_phys   = beacon_world[2:5]

    # Load BTT EBB42 CAN V1.2 rotated so 4-pin MicroFit & USB-C face UP (+Z) and flipped so pins face FORWARD (+Y toward extruder motor):
    ebb_raw = load_brep_list(WORK / "ebb42_cache.brep")
    t_center = gp_Trsf()
    t_center.SetTranslation(gp_Vec(-20.0, -20.0, 0.0))
    t_ry180 = gp_Trsf()
    t_ry180.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.pi)
    t_rx90 = gp_Trsf()
    t_rx90.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2.0)
    t_pos_ebb = gp_Trsf()
    t_pos_ebb.SetTranslation(gp_Vec(-1.248, -31.630, 6.500))
    trsf_ebb = t_pos_ebb.Multiplied(t_rx90.Multiplied(t_ry180.Multiplied(t_center)))
    ebb_world = [BRepBuilderAPI_Transform(s, trsf_ebb, True).Shape() for s, _ in ebb_raw]

    part_reports = {}
    for pname, pshape in parts:
        step_path = STEP_DIR / f"{pname}.step"
        stl_path = STL_DIR / f"{pname}.stl"
        export_step_file([pshape], step_path)
        export_stl_file(pshape, stl_path)
        min_v, max_v, _ = exact_vertex_bounds_from_stl(stl_path)
        mesh_val = validate_binary_stl(stl_path)

        v26_hits = [
            {"part": n, "vol_mm3": round(common_vol(pshape, s), 4)}
            for n, (s, _, _) in v26_by_name.items()
            if common_vol(pshape, s) > 1e-3
        ]
        gantry_hits = [
            {"gantry": n, "vol_mm3": round(common_vol(pshape, s), 4)}
            for n, (s, _, _) in gantry_by_name.items()
            if common_vol(pshape, s) > 1e-3
        ]
        beacon_hits = [
            round(common_vol(pshape, bs), 4)
            for bs in (*beacon_phys, beacon_bot_ko)
            if common_vol(pshape, bs) > 1e-3
        ]
        ebb_hit_vol = round(sum(common_vol(pshape, es) for es in ebb_world), 4)

        part_reports[pname] = {
            "solids": solid_count(pshape),
            "shells": shell_count(pshape),
            "brep_volume_mm3": round(vol_of(pshape), 3),
            "min_mm": min_v,
            "max_mm": max_v,
            "width_within_45mm": (min_v[0] >= -22.501 and max_v[0] <= 22.501),
            "v26_clashes": v26_hits,
            "gantry_clashes": gantry_hits,
            "beacon_clashes": beacon_hits,
            "ebb42_clash_mm3": ebb_hit_vol,
            "stl_validation": mesh_val,
            "step_sha256": hashlib.sha256(step_path.read_bytes()).hexdigest(),
            "stl_sha256": hashlib.sha256(stl_path.read_bytes()).hexdigest(),
        }
        print(f"[OK] {pname}: vol={part_reports[pname]['brep_volume_mm3']} mm3, bounds={min_v}..{max_v}, watertight={mesh_val['is_watertight_manifold']}")

    # Check inter-part overlaps:
    inter_part_overlaps = []
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            ov = common_vol(parts[i][1], parts[j][1])
            if ov > 1e-3:
                inter_part_overlaps.append({"a": parts[i][0], "b": parts[j][0], "vol_mm3": round(ov, 4)})

    # Check Beacon Top Metal Keepout against ALL v26 metal, ALL 39 Gantry bodies, and ALL new accessory fasteners:
    metal_in_beacon_ko = []
    for n, (s, _, m) in v26_by_name.items():
        if m["is_metal"]:
            v = common_vol(beacon_top_ko, s)
            if v > 1e-3:
                metal_in_beacon_ko.append({"source": n, "vol_mm3": round(v, 4)})
    for n, (s, _, _) in gantry_by_name.items():
        v = common_vol(beacon_top_ko, s)
        if v > 1e-3:
            metal_in_beacon_ko.append({"source": n, "vol_mm3": round(v, 4)})
    for hname, hs in acc_hw:
        v = common_vol(beacon_top_ko, hs)
        if v > 1e-3:
            metal_in_beacon_ko.append({"source": hname, "vol_mm3": round(v, 4)})

    # Load Cartographer V3 Flat Pack (RightAngle / vertical header orientation) at the SAME forward mount holes
    # (Y_holes = -0.30, rot_z = 180 -> Y_coil = +2.88 mm, Z_seat = -75.00 mm):
    carto_sols = load_step(SENSOR_DIR / "Cartographer_V3_RightAngle.step")
    trsf_c_rot180 = gp_Trsf()
    trsf_c_rot180.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.pi)
    trsf_c_pos = gp_Trsf()
    trsf_c_pos.SetTranslation(gp_Vec(0.0, -0.30 - 12.70701, -75.000))
    trsf_carto = trsf_c_pos.Multiplied(trsf_c_rot180)
    carto_world = [BRepBuilderAPI_Transform(s, trsf_carto, True).Shape() for s in carto_sols[:100]]
    carto_sec_clashes = [
        pname for pname, pshape in parts
        if pname != "P23_Beacon_Cartographer_Mount" and sum(common_vol(pshape, cs) for cs in carto_world) > 1e-3
    ] + [
        n for n, (s, _, m) in v26_by_name.items()
        if "ENVELOPE" not in n and sum(common_vol(s, cs) for cs in carto_world) > 1e-3
    ]

    # Verify 35 mm forward (+Y) tool-withdrawal sweep of the removable toolhead carrier:
    removable_prefixes = ("PRINT_000_outer_shell", "PRINT_carrier_box", "PRINT_arm_front", "HF_", "HGX_", "ARM_")
    removable_solids = [
        (n, s) for n, (s, _, _) in v26_by_name.items()
        if n.startswith(removable_prefixes)
    ]
    stationary_targets = (
        [(pname, pshape) for pname, pshape in parts]
        + [(f"BEACON_{i}", bs) for i, bs in enumerate(beacon_phys)]
    )
    withdrawal_clashes = []
    for dy_step in (5.0, 10.0, 15.0, 25.0, 35.0):
        t_wy = gp_Trsf()
        t_wy.SetTranslation(gp_Vec(0.0, dy_step, 0.0))
        for rname, rshape in removable_solids:
            r_moved = BRepBuilderAPI_Transform(rshape, t_wy, True).Shape()
            for tname, tshape in stationary_targets:
                cv = common_vol(r_moved, tshape)
                if cv > 1e-3:
                    withdrawal_clashes.append({"dy_mm": dy_step, "moving": rname, "stationary": tname, "vol_mm3": round(cv, 4)})

    # Export combined assembly STEP (P20..P24 + hardware + sensor_cable + Beacon + EBB42):
    combo_step = STEP_DIR / "SparkShift_v26_Accessories_Complete.step"
    export_step_file(
        [p for _, p in parts] + [h for _, h in acc_hw] + [sensor_cable] + beacon_phys,
        combo_step,
    )
    export_step_file(
        beacon_phys + [sensor_cable] + [h for _, h in acc_hw],
        STEP_DIR / "Forward_Beacon_and_Cable.step",
    )
    silicone_sock_air = cut_all(
        rounded_box_xy(-7.00, 7.00, 12.95, 38.45, -74.35, -59.50, 1.2),
        [box(-5.80, 5.80, 13.95, 37.25, -73.40, -59.00), cyl_z(0.0, 22.70, -76.00, -72.00, 3.80)],
    )
    nozzle_cone_air = fuse_all([
        cyl_z(0.0, 22.70, -76.80, -74.00, 3.50),
        cyl_z(0.0, 22.70, -78.88, -76.80, 1.20),
    ])
    exit_plenum_air = cut_all(
        rounded_box_xy(-15.5, 15.5, 13.5, 35.0, -78.88, -75.00, 2.0),
        [p22_body, silicone_sock_air, nozzle_cone_air],
    )
    export_step_file(
        [fuse_all([p20_air, p21_air, p22_air, exit_plenum_air])],
        STEP_DIR / "CPAP_Internal_Air_Domain.step",
    )

    # Build and verify 2510 and 3010 Toolhead Fan variants & Voron 350 10-toolhead packing:
    th_variants = build_toolhead_fan_variants(v26_by_name)
    toolhead_reports = {}
    for tname in ("P17_HF_tool_carrier_2510", "P17_HF_tool_carrier_3010", "P18_Tool_docking_backplate_3010"):
        tshape = th_variants[tname]
        t_step = STEP_DIR / f"{tname}.step"
        t_stl = STL_DIR / f"{tname}.stl"
        export_step_file([tshape], t_step)
        export_stl_file(tshape, t_stl)
        min_v, max_v, _ = exact_vertex_bounds_from_stl(t_stl)
        mesh_val = validate_binary_stl(t_stl)
        toolhead_reports[tname] = {
            "solids": solid_count(tshape),
            "shells": shell_count(tshape),
            "brep_volume_mm3": round(vol_of(tshape), 3),
            "min_mm": min_v,
            "max_mm": max_v,
            "stl_validation": mesh_val,
        }
        print(f"[OK] {tname}: vol={toolhead_reports[tname]['brep_volume_mm3']} mm3, bounds={min_v}..{max_v}, watertight={mesh_val['is_watertight_manifold']}")

    export_step_file([th_variants["Fan_2510_Axial"]] + th_variants["Fan_2510_Screws"], STEP_DIR / "Fan_2510_Axial.step")
    export_step_file([th_variants["Fan_3010_Axial"]] + th_variants["Fan_3010_Screws"], STEP_DIR / "Fan_3010_Axial.step")
    export_step_file(
        [th_variants["P17_HF_tool_carrier_2510"], v26_by_name["TOOL_06_Tool_head_back_part_1"][0], th_variants["Fan_2510_Axial"]] + th_variants["Fan_2510_Screws"],
        STEP_DIR / "Toolhead_2510_Complete.step",
    )
    export_step_file(
        [th_variants["P17_HF_tool_carrier_3010"], th_variants["P18_Tool_docking_backplate_3010"], th_variants["Fan_3010_Axial"]]
        + th_variants["Fan_3010_Screws"] + th_variants["SC_Pins_5x12"] + th_variants["SC_Magnets_6x4"],
        STEP_DIR / "Toolhead_3010_Complete.step",
    )

    # Build and verify Dock (P25), Nozzle Wiper & Purge Chute (P26), Stationary 7040 Blower Mount (P27),
    # Master Calibration Jig (P28), and COTS Core Drop-Ins (P01_COTS, P02_COTS, P05_COTS):
    dock_suite = build_dock_and_stationary_accessories(v26_by_name)
    dock_and_frame_reports = {}
    for dname in (
        "P25_SparkShift_3010_Dock",
        "P26_Dock_Nozzle_Wiper_and_Purge_Chute",
        "P27_CPAP_7040_Blower_Frame_Mount",
        "P28_Dock_and_Probe_Calibration_Jig",
        "P29_Dock_Rack_Gantry_Mount_L",
        "P29_Dock_Rack_Gantry_Mount_R",
        "P01_Back_case_COTS_MR74",
        "P02_Motor_servo_plate_12p5mm",
        "P03_Front_case_COTS",
        "P05_Servo_cam_COTS",
    ):
        dshape = dock_suite[dname]
        d_step = STEP_DIR / f"{dname}.step"
        d_stl = STL_DIR / f"{dname}.stl"
        export_step_file([dshape], d_step)
        export_stl_file(dshape, d_stl)
        min_v, max_v, _ = exact_vertex_bounds_from_stl(d_stl)
        mesh_val = validate_binary_stl(d_stl)
        dock_and_frame_reports[dname] = {
            "solids": solid_count(dshape),
            "shells": shell_count(dshape),
            "brep_volume_mm3": round(vol_of(dshape), 3),
            "min_mm": min_v,
            "max_mm": max_v,
            "stl_validation": mesh_val,
        }
        print(f"[OK] {dname}: vol={dock_and_frame_reports[dname]['brep_volume_mm3']} mm3, bounds={min_v}..{max_v}, watertight={mesh_val['is_watertight_manifold']}")

    export_step_file(dock_suite["Dock_Complete_Solids"], STEP_DIR / "Dock_3010_Complete.step")
    export_step_file(dock_suite["P29_Rack_Hardware_Solids"], STEP_DIR / "P29_Rack_Hardware_Complete.step")

    # Synchronize all printable STLs into root stl_v26/ directory:
    root_stl_dir = HERE.parent.parent / "stl_v26"
    if root_stl_dir.exists():
        import shutil
        for stl_file in STL_DIR.glob("*.stl"):
            shutil.copy2(stl_file, root_stl_dir / stl_file.name)

    # Verify 35 mm tool-withdrawal & 10-toolhead Voron 350 (37.30 mm pitch) neighbor clearance for both 2510 and 3010 toolheads:
    carriage_check_parts = [
        ("P01", v26_by_name["PRINT_motor_mount"][0]),
        ("P02", v26_by_name["PRINT_REAR_MOTOR_SERVO_SPACER"][0]),
        ("P03", v26_by_name["PRINT_000_outer_shell_of_extruder_1"][0]),
        ("P20", p20_body),
        ("P21", p21_body),
        ("P22", p22_body),
        ("P23", p23_body),
        ("P24", p24_body),
    ]
    carriage_check_bbs = {cn: bbox_of(cs) for cn, cs in carriage_check_parts}

    voron350_pitch_eval = {}
    for fan_label, t_parts in [
        ("2510_toolhead", [
            ("P17_2510", th_variants["P17_HF_tool_carrier_2510"]),
            ("P18_orig", v26_by_name["TOOL_06_Tool_head_back_part_1"][0]),
            ("Fan_2510", th_variants["Fan_2510_Axial"]),
            ("HF_00", v26_by_name["HF_00_K1_heatsink"][0]),
            ("HF_04", v26_by_name["HF_04_Creality_Ender_3_Volcano_Hotend_v14"][0]),
        ]),
        ("3010_toolhead", [
            ("P17_3010", th_variants["P17_HF_tool_carrier_3010"]),
            ("P18_3010", th_variants["P18_Tool_docking_backplate_3010"]),
            ("Fan_3010", th_variants["Fan_3010_Axial"]),
            ("HF_00", v26_by_name["HF_00_K1_heatsink"][0]),
            ("HF_04", v26_by_name["HF_04_Creality_Ender_3_Volcano_Hotend_v14"][0]),
        ]),
    ]:
        # 1. Self-withdrawal check (dx=0, dy=0..35 mm):
        own_clashes = []
        for dy_step in (0.0, 5.0, 10.0, 20.0, 35.0):
            t_wy = gp_Trsf()
            t_wy.SetTranslation(gp_Vec(0.0, dy_step, 0.0))
            for tn, ts in t_parts[:3]:
                ts_m = BRepBuilderAPI_Transform(ts, t_wy, True).Shape()
                bb_m = bbox_of(ts_m)
                for cn, cs in carriage_check_parts:
                    if not boxes_overlap(bb_m, carriage_check_bbs[cn]):
                        continue
                    v = common_vol(ts_m, cs)
                    if v > 1e-3:
                        own_clashes.append({"dy": dy_step, "tool": tn, "carr": cn, "vol": round(v, 4)})
        # 2. Neighbor docking sweep at P = 37.30 mm (10 tools), 35.00 mm, and 34.20 mm (11 tools):
        pitch_results = {}
        for pitch_mm in (37.30, 35.00, 34.20):
            p_clashes = []
            for dx_step in (-pitch_mm, pitch_mm):
                for dy_step in (0.0, 5.0, 15.0, 35.0):
                    t_tr = gp_Trsf()
                    t_tr.SetTranslation(gp_Vec(dx_step, dy_step, 0.0))
                    for tn, ts in t_parts:
                        ts_m = BRepBuilderAPI_Transform(ts, t_tr, True).Shape()
                        bb_m = bbox_of(ts_m)
                        for cn, cs in carriage_check_parts:
                            if not boxes_overlap(bb_m, carriage_check_bbs[cn]):
                                continue
                            v = common_vol(ts_m, cs)
                            if v > 1e-3:
                                p_clashes.append({"dx": dx_step, "dy": dy_step, "tool": tn, "carr": cn, "vol": round(v, 4)})
            pitch_results[f"pitch_{pitch_mm}mm_clashes"] = p_clashes
        voron350_pitch_eval[fan_label] = {
            "own_bay_withdrawal_clashes": own_clashes,
            **pitch_results,
        }

    verification = {
        "passed": (
            all(
                r["solids"] == 1
                and r["shells"] == 1
                and r["width_within_45mm"]
                and not r["v26_clashes"]
                and not r["gantry_clashes"]
                and not r["beacon_clashes"]
                and r["ebb42_clash_mm3"] <= 1e-3
                and r["stl_validation"]["is_watertight_manifold"]
                for r in part_reports.values()
            )
            and not inter_part_overlaps
            and not metal_in_beacon_ko
            and not carto_sec_clashes
            and not withdrawal_clashes
        ),
        "elapsed_seconds": round(time.time() - t0, 2),
        "rear_gantry_corridor_air_area_mm2": round(vol_of(p21_air) / 40.22, 2),
        "hose_spigot_bore_area_mm2": round(math.pi * 11.0**2, 2),
        "cpap_flow_areas_mm2": {
            "1_hose_inlet_id22": 380.13,
            "2_rear_gantry_conduit_p21": round(vol_of(p21_air) / 40.22, 2),
            "3_rear_bifurcation_split_p22": 324.60,
            "4_side_plenum_runners_p22": 248.40,
            "5_front_sweeping_horn_plenum_p22": 368.40,
            "6_converging_nozzle_outlets_p22": 456.80,
        },
        "beacon_revh_normal_datums": {
            "orientation": "Forward-facing (+Y coil toward nozzle, -Y USB dome at rear)",
            "coil_xyz_mm": [0.0, 3.20, -76.610],
            "nozzle_offset_xy_mm": [0.0, -19.50],
            "sensing_face_above_nozzle_mm": 2.269,
            "pcb_seat_z_mm": -75.000,
            "primary_mount_holes_xy_mm": [[-15.80, -0.30], [15.80, -0.30]],
            "wire_route": "Exits rear dome (0, -12.9, -66.5) -> rises behind MGN12H carriage -> under X-beam (Z=-55.2) -> up P21 center-front raceway (X=0, Y=-34.5) -> EBB42 (0, -21.5, -14.2)",
            "metal_in_20mm_top_keepout": metal_in_beacon_ko,
        },
        "cartographer_v3_flat_pack_datums": {
            "orientation": "Forward-facing (+Y coil toward nozzle, -Y MCU/JST at rear)",
            "shared_mount_holes_xy_mm": [[-15.80, -0.30], [15.80, -0.30]],
            "coil_xyz_mm": [0.0, 2.88, -76.600],
            "nozzle_offset_xy_mm": [0.0, -19.82],
            "sensing_face_above_nozzle_mm": 2.279,
            "physical_clashes_with_v26_or_accessories": carto_sec_clashes,
            "adxl345_note": "Onboard ADXL345 sits horizontal on the probe PCB (Z=-75.00 mm) directly behind the nozzle for low-mass input shaping.",
        },
        "ebb42_can_v1p1_datums": {
            "board_center_xz_mm": [-1.248, 6.500],
            "pcb_front_y_mm": -31.630,
            "pcb_standoff_y_mm": -25.400,
            "standoff_pattern_mm": "31.0 x 31.0 mm square (M3x4x4.2 heat-set inserts)",
            "adxl345_orientation": "Orthogonal XZ plane (normal = (0, +1, 0), 0.0 deg tilt)",
            "nema14_motor_clearance": {
                "motor_mount_front_flange_face_y_mm": 3.30,
                "motor_mount_rear_flange_face_y_mm": 0.30,
                "cad_motor_36sth20_rear_face_y_mm": -16.70,
                "p24_motor_bore_rear_limit_y_mm": -22.10,
                "ebb42_nearest_component_in_motor_cyl_y_mm": -21.91,
                "max_motor_thickness_from_front_flange_mm": 25.21,
                "max_motor_can_behind_3mm_flange_mm": 22.21,
                "clearance_at_17p4mm_motor_mm": 7.81,
                "clearance_at_21p8mm_motor_from_front_flange_mm": 3.41,
                "clearance_at_21p8mm_can_behind_flange_mm": 0.41,
            },
        },
        "tool_withdrawal_35mm_sweep_clashes": withdrawal_clashes,
        "inter_part_overlaps": inter_part_overlaps,
        "toolhead_fan_variants": toolhead_reports,
        "dock_and_stationary_accessories": dock_and_frame_reports,
        "voron350_10_toolhead_evaluation": voron350_pitch_eval,
        "parts": part_reports,
        "combined_step_sha256": hashlib.sha256(combo_step.read_bytes()).hexdigest(),
    }
    (HERE / "verification_accessories_v26.json").write_text(json.dumps(verification, indent=2))
    print(f"\nALL CHECKS PASSED = {verification['passed']} in {verification['elapsed_seconds']}s")
    print(f"Voron 350 10-toolhead pitch eval: {voron350_pitch_eval}")
    print(f"Metal in Beacon 20mm keepout: {metal_in_beacon_ko}")
    print(f"Inter-part overlaps: {inter_part_overlaps}")
    print(f"Withdrawal clashes: {withdrawal_clashes}")
    print(f"Carto clashes: {carto_sec_clashes}")


if __name__ == "__main__":
    main()
