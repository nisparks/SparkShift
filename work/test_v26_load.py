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

t0 = time.time()
v26_step = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-animated-succotash\.local-cad\sparkshift_release_v26\cad\SparkShift_AHG_min_v26.step")
reader = STEPControl_Reader()
if reader.ReadFile(str(v26_step)) != IFSelect_RetDone:
    raise RuntimeError("Failed to read v26 step")
reader.TransferRoots()
shape = reader.OneShape()
exp = TopExp_Explorer(shape, TopAbs_SOLID)
count = 0
while exp.More():
    count += 1
    exp.Next()
print(f"v26 STEP solids: {count} in {time.time()-t0:.2f}s")
