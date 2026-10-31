import json
import math
import time
from pathlib import Path
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
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

t0 = time.time()
WORK = Path(__file__).resolve().parent

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
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise RuntimeError(f"Failed to read {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = []
    while exp.More():
        s = exp.Current()
        bbox = Bnd_Box()
        BRepBndLib.Add_s(s, bbox)
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(s, props)
        solids.append((s, bbox.Get(), props.Mass()))
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
print(f"Loaded {len(v26_solids)} v26 solids and {len(gantry_solids)} gantry solids in {time.time()-t0:.2f}s")

sensor_dir = Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files\compact_direct_cam\accessory_sources")
beacon_norm = load_step_solids(sensor_dir / "Beacon_RevH_Assm_Normal.STEP")
beacon_lp = load_step_solids(sensor_dir / "Beacon_RevH_Assm_LowProfile.STEP")

def test_beacon(solids_list, phys_indices, top_ko_idx, bot_ko_idx, rot_z_deg, x_coil, y_coil, z_seat):
    trsf_r = gp_Trsf()
    trsf_r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(rot_z_deg))
    trsf_t = gp_Trsf()
    trsf_t.SetTranslation(gp_Vec(x_coil, y_coil, z_seat))
    trsf = trsf_t.Multiplied(trsf_r)

    transformed = []
    for s, _, _ in solids_list:
        ts = BRepBuilderAPI_Transform(s, trsf, True).Shape()
        transformed.append((ts, bbox_tuple(ts)))

    phys = [transformed[i] for i in phys_indices]
    top_ko, top_bb = transformed[top_ko_idx]
    bot_ko, bot_bb = transformed[bot_ko_idx]

    phys_v26_hits = []
    phys_gantry_hits = []
    metal_hits = []

    for m, s in v26_solids:
        mb = (*m["min_mm"], *m["max_mm"])
        for p_s, p_bb in phys:
            if boxes_overlap(p_bb, mb):
                v = common_vol(p_s, s)
                if v > 1e-3:
                    phys_v26_hits.append((m["name"], round(v, 2)))
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
                    phys_gantry_hits.append((m["name"], round(v, 2)))
        if boxes_overlap(top_bb, mb):
            v = common_vol(top_ko, s)
            if v > 1e-3:
                metal_hits.append((m["name"], round(v, 2)))

    x_min = min(p_bb[0] for _, p_bb in phys)
    x_max = max(p_bb[3] for _, p_bb in phys)
    y_min = min(p_bb[1] for _, p_bb in phys)
    y_max = max(p_bb[4] for _, p_bb in phys)
    return {
        "rot_z": rot_z_deg, "x_coil": x_coil, "y_coil": y_coil, "z_seat": round(z_seat, 3),
        "nozzle_dist": round(math.hypot(x_coil, 22.7 - y_coil), 2),
        "x_span": [round(x_min, 2), round(x_max, 2)],
        "y_span": [round(y_min, 2), round(y_max, 2)],
        "heater_gap_y": round(14.2 - y_max, 2),
        "phys_v26_hits": phys_v26_hits,
        "phys_gantry_hits": phys_gantry_hits,
        "metal_hits": metal_hits
    }

print("\n--- Sweep Beacon Normal rot_z=0 (connector rear -Y, coil front +Y) ---")
for y_c in [-7.5, -7.0, -6.5, -6.0, -5.85, -5.3, -2.0, 0.0, 2.0, 2.3, 2.5]:
    r = test_beacon(beacon_norm, (2, 3, 4), 1, 0, 0, 0.0, y_c, -74.5194)
    print(f"  Y={y_c:5.2f} (d={r['nozzle_dist']:5.2f}, Yspan={r['y_span']}, hGap={r['heater_gap_y']:5.2f}): v26={r['phys_v26_hits']} gantry={r['phys_gantry_hits']} metal={r['metal_hits']}")

print("\n--- Sweep Beacon Normal rot_z=180 (connector front +Y, coil rear -Y) ---")
for y_c in [-8.0, -7.0, -6.5, -6.0, -5.85]:
    r = test_beacon(beacon_norm, (2, 3, 4), 1, 0, 180, 0.0, y_c, -74.5194)
    print(f"  Y={y_c:5.2f} (d={r['nozzle_dist']:5.2f}, Yspan={r['y_span']}, hGap={r['heater_gap_y']:5.2f}): v26={r['phys_v26_hits']} gantry={r['phys_gantry_hits']} metal={r['metal_hits']}")

print("\n--- Sweep Beacon LowProfile rot_z=90 / 270 (connector sideways ±X) ---")
for rot in [90, 270]:
    for x_c in [-3.5, 0.0, 3.5]:
        for y_c in [-7.5, -6.5, -6.0, -5.85, -5.3]:
            r = test_beacon(beacon_lp, (0, 1, 2), 4, 3, rot, x_c, y_c, -74.5194)
            if not r["phys_v26_hits"] and not r["phys_gantry_hits"] and not r["metal_hits"]:
                print(f"  PASS LP rot={rot} X={x_c} Y={y_c} (d={r['nozzle_dist']}, Xspan={r['x_span']}, Yspan={r['y_span']}, hGap={r['heater_gap_y']})")

print("\n--- Sweep Beacon Normal rot_z=90 / 270 (connector sideways ±X) ---")
for rot in [90, 270]:
    for x_c in [-3.5, 0.0, 3.5]:
        for y_c in [-7.5, -6.5, -6.0, -5.85, -5.3]:
            r = test_beacon(beacon_norm, (2, 3, 4), 1, 0, rot, x_c, y_c, -74.5194)
            if not r["phys_v26_hits"] and not r["phys_gantry_hits"] and not r["metal_hits"]:
                print(f"  PASS Norm rot={rot} X={x_c} Y={y_c} (d={r['nozzle_dist']}, Xspan={r['x_span']}, Yspan={r['y_span']}, hGap={r['heater_gap_y']})")

