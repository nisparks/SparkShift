import sys
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
s = cq.Shape.importBrep(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\variants\p22_r43_final.brep")
m = TopTools_IndexedDataMapOfShapeListOfShape()
TopExp.MapShapesAndAncestors_s(s.wrapped, TopAbs_EDGE, TopAbs_FACE, m)
for e in s.Edges():
    if e.Length() < 0.06:
        c = e.Center()
        faces = [cq.Face(f) for f in m.FindFromKey(e.wrapped)]
        print(round(e.Length(), 4), e.geomType(), [round(v, 3) for v in (c.x, c.y, c.z)],
              [(f.geomType(), round(f.Area(), 3), [round(v, 2) for v in f.normalAt(f.Center()).toTuple()]) for f in faces])
