"""R43 study, round 3 (session scratch): valid variants that add jet area low and at/in front of the nozzle.
front     : the floor 0.4 mm lower only where revision 41's is flat (Y22.38 on), a 45 degree ramp behind, the heel as before
lowbell   : revision 43's pocket (the floor 0.4 mm lower from Y19, following the heel) and the r 2.4 bell-mouth
frontbell : front and the r 2.4 bell-mouth
"""
import sys
from pathlib import Path
HERE = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(HERE))
import os
os.chdir(HERE)
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
import r41_parts as R41
import r43_parts as R
from build_bambu_clean_r29 import single

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\variants")
a = R.a
FRONT_Y0 = 22.38                       # revision 41's floor is flat from here forward (its r6.5 heel round ends here)


def front_pocket(side):
    lo, hi = sorted((side * R.LOW_X[0], side * R.LOW_X[1]))
    top = R.FLOOR + 0.03
    pts = [(FRONT_Y0 - 0.4, top), (FRONT_Y0, R.LOW_FLOOR), (29.0, R.LOW_FLOOR), (29.0, top)]
    band = R.shape(a.prism_yz_r(pts, [0] * 4, lo, hi))
    return R.cut(R.common(band, [R.inside(R.UNDER - 1.0, R.ROOF + 1.0)]), [R.front_chamfer(side)])


def variant(kind):
    body = R41.p22()
    if "bell" in kind:
        body = R.fuse(body, *[R.bell_fill(s) for s in (-1, 1)])
    cutters = [R.bell_cut(s) for s in (-1, 1)] if "bell" in kind else []
    cutters += [(front_pocket if kind.startswith("front") else R.pocket)(s) for s in (-1, 1)]
    return single(R.unify(R.cut(body, cutters)), kind)


def floor_min(s):
    isect = IntCurvesFace_ShapeIntersector()
    isect.Load(s.wrapped, 1e-6)
    worst = 9.0
    for x in (10.3, 11.0, 12.0, 12.8, -11.0):
        for k in range(0, 177):
            y = 19.05 + 0.05 * k
            isect.Perform(gp_Lin(gp_Pnt(x, y, -79.0), gp_Dir(0, 0, 1)), 0.0, 6.0)
            z = sorted(isect.Pnt(i).Z() for i in range(1, isect.NbPnt() + 1))
            if len(z) >= 2:
                worst = min(worst, z[1] - z[0])
    return round(worst, 3)


if __name__ == "__main__":
    for kind in sys.argv[1:] or ("front", "lowbell", "frontbell"):
        s = variant(kind)
        s.exportBrep(str(OUT / f"p22_{kind}.brep"))
        print(kind, "valid", s.isValid(), "solids", len(s.Solids()), "volume", round(s.Volume(), 2), "faces", len(s.Faces()),
              "floor min", floor_min(s), flush=True)
