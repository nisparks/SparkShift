import os, sys
CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, CAD); os.chdir(CAD)
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d
import r43_centre_feed as CF
from audit_tool_owned_2510 import bounds
S = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
base = cq.Shape.importBrep(os.path.join(S, "cfd", "p22_r43.brep"))
print("base shells", len(base.Shells()))
for sh in base.Shells():
    print("  base shell", [round(v, 2) for v in bounds(sh)], "faces", len(sh.Faces()))
p = CF.p22(base)
outer = cq.Shape.cast(BRepClass3d.OuterShell_s(p.Solids()[0].wrapped))
for sh in p.Shells():
    tag = "OUTER" if sh.isSame(outer) else "inner"
    print(tag, [round(v, 2) for v in bounds(sh)], "faces", len(sh.Faces()), "vol", round(abs(cq.Solid.makeSolid(sh).Volume()), 3))
print("legs roof point (8.3, 14.6, -70.4) solid:", p.isInside(cq.Vector(8.3, 14.6, -70.4)), "leg air (8.3,14.6,-71.2) free:", not p.isInside(cq.Vector(8.3, 14.6, -71.2)))
p.exportBrep(os.path.join(S, "cfd", "p22_r43_centre.brep"))
print("vol", round(p.Volume(), 3), "valid", p.isValid())
