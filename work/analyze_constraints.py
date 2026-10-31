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
from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder

t0 = time.time()
WORK = Path(__file__).resolve().parent

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

v26_step = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-animated-succotash\.local-cad\sparkshift_release_v26\cad\SparkShift_AHG_min_v26.step")
v26_solids = load_step_solids(v26_step)
print(f"Loaded v26 STEP: {len(v26_solids)} solids in {time.time()-t0:.2f}s")

# Save v26 compound to .brep for instant loading (<0.2s)
builder = BRep_Builder()
comp = TopoDS_Compound()
builder.MakeCompound(comp)
v26_meta = []
for idx, (s, bb, vol) in enumerate(v26_solids):
    builder.Add(comp, s)
    v26_meta.append({
        "idx": idx,
        "min_mm": [round(bb[0], 3), round(bb[1], 3), round(bb[2], 3)],
        "max_mm": [round(bb[3], 3), round(bb[4], 3), round(bb[5], 3)],
        "vol_mm3": round(vol, 3)
    })
BRepTools.Write_s(comp, str(WORK / "v26_cache.brep"))
(WORK / "v26_meta.json").write_text(json.dumps(v26_meta, indent=2))
print(f"Cached v26_cache.brep ({time.time()-t0:.2f}s)")