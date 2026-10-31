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
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

t0 = time.time()
WORK = Path(__file__).resolve().parent

# Find monolith_toolhead_integration.step
mono_step = None
for root_dir in [
    Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files"),
    Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-animated-succotash")
]:
    for p in root_dir.rglob("monolith_toolhead_integration.step"):
        mono_step = p
        break
    if mono_step:
        break

print("Found monolith_toolhead_integration.step:", mono_step)

# Load reference_measurements.json to identify exact 2WD full Y travel bodies
ref_json = Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files\compact_direct_cam\monolith_mount_reference\reference_measurements.json")
ref_data = json.loads(ref_json.read_text())
integration_rows = ref_data["sources"]["integration"]["bodies"]
print("Total integration rows in JSON:", len(integration_rows))

reader = STEPControl_Reader()
if reader.ReadFile(str(mono_step)) != IFSelect_RetDone:
    raise RuntimeError("Failed to read monolith_toolhead_integration.step")
reader.TransferRoots()
shape = reader.OneShape()
exp = TopExp_Explorer(shape, TopAbs_SOLID)
raw_solids = []
while exp.More():
    raw_solids.append(exp.Current())
    exp.Next()
print("Raw solids in monolith_toolhead_integration.step:", len(raw_solids))

# Transform from monolith_toolhead_integration.step to v26 world frame:
# X_v26 = -x_s
# Y_v26 = -y_s - 1.2
# Z_v26 = z_s - 37.77940478477181
# Which is: rotate 180 deg around Z axis, then translate by (0, -1.2, -37.77940478477181)
trsf_rot = gp_Trsf()
trsf_rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.pi)
trsf_trans = gp_Trsf()
trsf_trans.SetTranslation(gp_Vec(0.0, -1.2, -37.77940478477181))
trsf_v26 = trsf_trans.Multiplied(trsf_rot)

# Also remember from monolith_cartridge_fusion.py:
# if row["body_name"] in ("Body36", "Body37"):
#     body = scene.cut(body, scene.box(-22.7, 22.7, -8.5, 2, 0, 50)) in authoring -> in v26 that cuts the front belt loop inside the carriage
cut_box_36_37 = BRepPrimAPI_MakeBox(gp_Pnt(-22.7, -0.2, -62.0), gp_Pnt(22.7, 10.3, -11.0)).Shape()

builder = BRep_Builder()
g_comp = TopoDS_Compound()
builder.MakeCompound(g_comp)
g_meta = []

for idx, row in enumerate(integration_rows):
    if row["component"] != "2WD full Y travel:1" or row["body_name"] == "Body3":
        continue
    s_raw = raw_solids[idx]
    s_v26 = BRepBuilderAPI_Transform(s_raw, trsf_v26, True).Shape()
    if row["body_name"] in ("Body36", "Body37"):
        s_v26 = BRepAlgoAPI_Cut(s_v26, cut_box_36_37).Shape()
    bbox = Bnd_Box()
    BRepBndLib.Add_s(s_v26, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(s_v26, props)
    builder.Add(g_comp, s_v26)
    g_meta.append({
        "name": "GANTRY_" + row["body_name"],
        "min_mm": [round(xmin, 3), round(ymin, 3), round(zmin, 3)],
        "max_mm": [round(xmax, 3), round(ymax, 3), round(zmax, 3)],
        "vol_mm3": round(props.Mass(), 2)
    })

BRepTools.Write_s(g_comp, str(WORK / "gantry_cache.brep"))
(WORK / "gantry_meta.json").write_text(json.dumps(g_meta, indent=2))
print(f"Cached {len(g_meta)} gantry keepout solids to gantry_cache.brep ({time.time()-t0:.2f}s)")
for m in g_meta[:10]:
    print(" ", m["name"], m["min_mm"], m["max_mm"], m["vol_mm3"])
