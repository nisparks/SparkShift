import json, math, time
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

t0 = time.time()
WORK = Path(__file__).resolve().parent

ebb_path = Path(r"C:\Users\nspar\Downloads\BIGTREETECH EBB42 CAN V1.1.step")
reader = STEPControl_Reader()
reader.ReadFile(str(ebb_path))
reader.TransferRoots()
shape = reader.OneShape()
exp = TopExp_Explorer(shape, TopAbs_SOLID)

board_solids = []
standoff_count = 0
while exp.More():
    s = exp.Current()
    bbox = Bnd_Box()
    BRepBndLib.Add_s(s, bbox)
    bb = bbox.Get()
    # The 4 M3x20+6 standoffs in the STEP have zmin around -20.05
    if bb[2] < -10.0:
        standoff_count += 1
    else:
        board_solids.append((s, bb))
    exp.Next()

print(f"Loaded EBB42: {len(board_solids)} board/component solids, excluded {standoff_count} standoffs ({time.time()-t0:.2f}s)")
xmin = min(b[0] for _, b in board_solids)
ymin = min(b[1] for _, b in board_solids)
zmin = min(b[2] for _, b in board_solids)
xmax = max(b[3] for _, b in board_solids)
ymax = max(b[4] for _, b in board_solids)
zmax = max(b[5] for _, b in board_solids)
print(f"EBB42 board+components local bounds: X=[{xmin:.2f}, {xmax:.2f}], Y=[{ymin:.2f}, {ymax:.2f}], Z=[{zmin:.2f}, {zmax:.2f}]")

# Save major EBB42 solids (volume > 5 mm3 or bounding box > 2mm) to ebb42_cache.brep for fast checking & rendering
builder = BRep_Builder()
comp = TopoDS_Compound()
builder.MakeCompound(comp)
kept = 0
for s, bb in board_solids:
    if (bb[3]-bb[0]) > 1.5 or (bb[4]-bb[1]) > 1.5 or (bb[5]-bb[2]) > 1.0:
        builder.Add(comp, s)
        kept += 1
BRepTools.Write_s(comp, str(WORK / "ebb42_cache.brep"))
print(f"Cached {kept} EBB42 solids to ebb42_cache.brep ({time.time()-t0:.2f}s)")
