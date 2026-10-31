import sys
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import os
os.chdir(sys.path[0])
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
import r41_parts as R41
import r43_parts as R

def hits(s, x, y):
    isect = IntCurvesFace_ShapeIntersector()
    isect.Load(s.wrapped, 1e-6)
    isect.Perform(gp_Lin(gp_Pnt(x, y, -79.0), gp_Dir(0, 0, 1)), 0.0, 6.5)
    return sorted(round(isect.Pnt(k).Z(), 3) for k in range(1, isect.NbPnt() + 1))

old, new = R41.p22(), R.p22()
for x in (10.5, 11.0, 12.0, 12.9):
    print(f"X {x}")
    for y in (18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0, 22.2, 22.5, 23.0, 26.0, 27.5, 27.8):
        print(f"  Y {y:5.2f}  r41 {hits(old, x, y)}  r43 {hits(new, x, y)}")
