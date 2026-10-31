import json, math
from pathlib import Path
from OCP.STEPControl import STEPControl_Reader
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

WORK = Path(__file__).resolve().parent
sensor_dir = Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files\compact_direct_cam\accessory_sources")

def load_brep_solids(brep_path, meta_path):
    comp = TopoDS_Compound()
    builder = BRep_Builder()
    BRepTools.Read_s(comp, str(brep_path), builder)
    meta = json.loads(Path(meta_path).read_text())
    exp = TopExp_Explorer(comp, TopAbs_SOLID)
    solids = []
    idx = 0
    while exp.More():
        solids.append((meta[idx], exp.Current()))
        idx += 1
        exp.Next()
    return solids

def load_step_solids(path):
    reader = STEPControl_Reader()
    reader.ReadFile(str(path))
    reader.TransferRoots()
    shape = reader.OneShape()
    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = []
    while exp.More():
        s = exp.Current()
        bbox = Bnd_Box()
        BRepBndLib.Add_s(s, bbox)
        solids.append((s, bbox.Get()))
        exp.Next()
    return solids

def bbox_tuple(shape):
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    return bbox.Get()

def boxes_overlap(b1, b2, tol=0.0):
    return not (
        b1[3] + tol < b2[0] or b2[3] + tol < b1[0] or
        b1[4] + tol < b2[1] or b2[4] + tol < b1[1] or
        b1[5] + tol < b2[2] or b2[5] + tol < b1[2]
    )

def common_vol(s1, s2):
    common = BRepAlgoAPI_Common(s1, s2)
    if not common.IsDone():
        return 0.0
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(common.Shape(), props)
    return max(0.0, props.Mass())

v26_solids = load_brep_solids(WORK / "v26_cache.brep", WORK / "v26_meta.json")
gantry_solids = load_brep_solids(WORK / "gantry_cache.brep", WORK / "gantry_meta.json")
carto_lp = load_step_solids(sensor_dir / "Cartographer_V3_LowProfile.step")
carto_ra = load_step_solids(sensor_dir / "Cartographer_V3_RightAngle.step")

def test_carto(solids_list, phys_indices, top_ko_idx, rot_z_deg, y_holes, z_seat):
    trsf_r = gp_Trsf()
    trsf_r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(rot_z_deg))
    # In STEP, holes are at (0, -12.70701) and coil is at (0, -15.88304).
    # After rot_z=0, holes are at y = -12.70701; after rot_z=180, holes are at y = +12.70701.
    y_trans = y_holes + 12.70701 if rot_z_deg == 0 else y_holes - 12.70701
    y_coil = y_holes - 3.17603 if rot_z_deg == 0 else y_holes + 3.17603
    trsf_t = gp_Trsf()
    trsf_t.SetTranslation(gp_Vec(0.0, y_trans, z_seat))
    trsf = trsf_t.Multiplied(trsf_r)

    phys = []
    for i in phys_indices:
        ts = BRepBuilderAPI_Transform(solids_list[i][0], trsf, True).Shape()
        phys.append((ts, bbox_tuple(ts)))
    top_ko = BRepBuilderAPI_Transform(solids_list[top_ko_idx][0], trsf, True).Shape()
    top_bb = bbox_tuple(top_ko)

    v26_hits, gantry_hits, metal_hits = [], [], []
    for m, s in v26_solids:
        mb = (*m["min_mm"], *m["max_mm"])
        for p_s, p_bb in phys:
            if boxes_overlap(p_bb, mb):
                v = common_vol(p_s, s)
                if v > 1e-3:
                    v26_hits.append((m["name"], round(v, 2)))
        if m["is_metal"] and boxes_overlap(top_bb, mb):
            v = common_vol(top_ko, s)
            if v > 1e-3:
                metal_hits.append((m["name"], round(v, 2)))
    for m, s in gantry_solids:
        mb = (*m["min_mm"], *m["max_mm"])
        for p_s, p_bb in phys:
            if boxes_overlap(p_bb, mb):
                v = common_vol(p_s, s)
                if v > 1e-3:
                    gantry_hits.append((m["name"], round(v, 2)))
        if boxes_overlap(top_bb, mb):
            v = common_vol(top_ko, s)
            if v > 1e-3:
                metal_hits.append((m["name"], round(v, 2)))
    y_min = min(p_bb[1] for _, p_bb in phys)
    y_max = max(p_bb[4] for _, p_bb in phys)
    return {
        "y_holes": y_holes, "y_coil": round(y_coil, 2),
        "y_span": [round(y_min, 2), round(y_max, 2)],
        "ko_y": [round(top_bb[1], 2), round(top_bb[4], 2)],
        "hGap": round(14.2 - y_max, 2),
        "v26": v26_hits, "gantry": gantry_hits, "metal": metal_hits
    }

print("=== Cartographer LowProfile ===")
for rot in [0, 180]:
    for yh in [-9.5, -8.8, -4.0, -3.5, -3.2, -3.0]:
        r = test_carto(carto_lp, (0, 1, 2, 3, 4, 16, 97), 100, rot, yh, -74.5194)
        print(f"  rot={rot:3d} Y_holes={yh:5.2f} Y_coil={r['y_coil']:5.2f} Yspan={r['y_span']} koY={r['ko_y']} hGap={r['hGap']:5.2f} v26={r['v26']} gantry={r['gantry']} metal={r['metal']}")

print("=== Cartographer RightAngle ===")
for rot in [0, 180]:
    for yh in [-9.5, -8.8, -4.0, -3.5, -3.2, -3.0]:
        r = test_carto(carto_ra, (0, 1, 2, 3, 4, 16, 97), 101, rot, yh, -74.5194)
        print(f"  rot={rot:3d} Y_holes={yh:5.2f} Y_coil={r['y_coil']:5.2f} Yspan={r['y_span']} koY={r['ko_y']} hGap={r['hGap']:5.2f} v26={r['v26']} gantry={r['gantry']} metal={r['metal']}")


