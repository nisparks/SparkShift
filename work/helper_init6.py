import json, math
from pathlib import Path
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

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
ebb_raw = load_brep_list(WORK / "ebb42_cache.brep")

def boxes_overlap(b1, b2):
    return not (
        b1[3] < b2[0] or b2[3] < b1[0] or
        b1[4] < b2[1] or b2[4] < b1[1] or
        b1[5] < b2[2] or b2[5] < b1[2]
    )

def common_vol(s1, s2):
    common = BRepAlgoAPI_Common(s1, s2)
    if not common.IsDone():
        return 0.0
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(common.Shape(), props)
    return max(0.0, props.Mass())

# Center EBB42 at (20, 20, 0) first, then rotate +90 deg around X (so board lies in XZ plane, Z_local -> -Y),
# then rotate by angle_y around Y axis, then translate to (x_c, y_pcb, z_c).
t_center = gp_Trsf()
t_center.SetTranslation(gp_Vec(-20.0, -20.0, 0.0))
t_rx90 = gp_Trsf()
t_rx90.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2.0)
base_trsf = t_rx90.Multiplied(t_center)

for rot_y_deg in [0, 90, 180, 270]:
    t_ry = gp_Trsf()
    t_ry.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.radians(rot_y_deg))
    t_pos = gp_Trsf()
    t_pos.SetTranslation(gp_Vec(-1.0, -21.0, 6.0))
    trsf = t_pos.Multiplied(t_ry.Multiplied(base_trsf))

    ebb_t = []
    for s, _ in ebb_raw:
        ts = BRepBuilderAPI_Transform(s, trsf, True).Shape()
        bbox = Bnd_Box()
        BRepBndLib.Add_s(ts, bbox)
        ebb_t.append((ts, bbox.Get()))

    v26_hits = []
    for m, (s, mb) in zip(v26_meta, v26_raw):
        for es, eb in ebb_t:
            if boxes_overlap(eb, mb):
                v = common_vol(es, s)
                if v > 1e-3:
                    v26_hits.append((m["name"], round(v, 2)))
    gantry_hits = []
    for m, (s, mb) in zip(gantry_meta, gantry_raw):
        for es, eb in ebb_t:
            if boxes_overlap(eb, mb):
                v = common_vol(es, s)
                if v > 1e-3:
                    gantry_hits.append((m["name"], round(v, 2)))

    xmin = min(b[0] for _, b in ebb_t)
    ymin = min(b[1] for _, b in ebb_t)
    zmin = min(b[2] for _, b in ebb_t)
    xmax = max(b[3] for _, b in ebb_t)
    ymax = max(b[4] for _, b in ebb_t)
    zmax = max(b[5] for _, b in ebb_t)
    # Find where mounting holes (originally (4.5,4.5,0), (4.5,35.5,0), (35.5,4.5,0), (35.5,35.5,0)) land:
    holes_world = []
    for hx, hy in [(4.5, 4.5), (4.5, 35.5), (35.5, 4.5), (35.5, 35.5)]:
        p = gp_Pnt(hx, hy, 0.0).Transformed(trsf)
        holes_world.append((round(p.X(), 2), round(p.Y(), 2), round(p.Z(), 2)))
    # Find where MicroFit P1 center (27.1, 31.5, 5.0) and USB-C center (12.4, 37.4, 1.2) land:
    p_can = gp_Pnt(27.1, 31.5, 5.0).Transformed(trsf)
    p_usb = gp_Pnt(12.4, 37.4, 1.2).Transformed(trsf)
    print(f"rot_y={rot_y_deg:3d}: bounds=[{xmin:.2f}..{xmax:.2f}, {ymin:.2f}..{ymax:.2f}, {zmin:.2f}..{zmax:.2f}] v26={v26_hits} gantry={gantry_hits}")
    print(f"   holes={holes_world} CAN=({p_can.X():.1f},{p_can.Y():.1f},{p_can.Z():.1f}) USB=({p_usb.X():.1f},{p_usb.Y():.1f},{p_usb.Z():.1f})")
