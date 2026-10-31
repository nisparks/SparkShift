import sys, math
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import os
os.chdir(sys.path[0])
from pathlib import Path
import cadquery as cq
import numpy as np
import trimesh
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
import r41_parts as R41
import r43_parts as R

FILES = Path(__file__).resolve().parent

def hits(s, x, y):
    isect = IntCurvesFace_ShapeIntersector()
    isect.Load(s.wrapped, 1e-6)
    isect.Perform(gp_Lin(gp_Pnt(x, y, -79.0), gp_Dir(0, 0, 1)), 0.0, 6.5)
    return sorted(round(isect.Pnt(k).Z(), 3) for k in range(1, isect.NbPnt() + 1))

old, new = R41.p22(), R.p22()
print("R43 valid", new.isValid(), "solids", len(new.Solids()), "volume", round(new.Volume(), 2), "R41", round(old.Volume(), 2),
      "removed", round(old.Volume() - new.Volume(), 2), "faces", len(new.Faces()), "R41 faces", len(old.Faces()))
for x in (10.3, 11.0, 12.0, 12.8, -11.0):
    print(f"X {x}")
    for y in (18.9, 19.1, 20.0, 21.0, 22.0, 22.5, 25.0, 27.0, 27.3, 27.5, 27.7):
        h = hits(new, x, y)
        print(f"  Y {y:5.2f}  r41 {hits(old, x, y)}  r43 {h}  floor {round(h[1] - h[0], 3) if len(h) > 1 else None}")

# minimum floor thickness under the pocket by a dense vertical grid
mins = []
for x in np.arange(10.25, 12.85, 0.1):
    for y in np.arange(19.02, 27.9, 0.05):
        h = hits(new, x, y)
        if len(h) >= 2 and h[0] < -77.0:
            mins.append((round(h[1] - h[0], 3), round(x, 2), round(y, 2)))
mins.sort()
print("thinnest vertical floor under the pocket (mm, x, y):", mins[:4])

# tiny faces / short edges introduced
def small(s):
    fa = sorted((f.Area(), i) for i, f in enumerate(s.Faces()))
    ed = sorted(e.Length() for e in s.Edges())
    return [round(v, 4) for v, _ in fa[:6]], [round(v, 4) for v in ed[:6]]
print("R43 smallest faces/edges", small(new))
print("R41 smallest faces/edges", small(old))

# studies against what was simulated
for name, fn in (("low", R.low_study), ("bell", lambda: R.bell_study()), ("combo", lambda: R.bell_study(low=True))):
    ref = cq.Shape.importBrep(str(FILES / "r43" / "variants" / f"p22_{name}.brep"))
    s = fn()
    d = s.cut(ref).Volume() + ref.cut(s).Volume()
    print(f"study {name}: volume {s.Volume():.2f} vs simulated {ref.Volume():.2f}, symmetric difference {d:.4f} mm3")

# print support (P22 on its back face), as build_cpap_outlet_r43.check_print
def support(s):
    s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90)
    bb = s.BoundingBox()
    s = s.translate(cq.Vector(0, 0, -bb.zmin))
    p = FILES / "tmp_print.stl"
    cq.exporters.export(s, str(p), tolerance=0.03, angularTolerance=0.1)
    m = trimesh.load_mesh(str(p)); p.unlink()
    n, area, z = m.face_normals, m.area_faces, m.triangles_center[:, 2]
    bed = (n[:, 2] < -0.999) & (z < 0.01)
    down = (n[:, 2] < -math.sin(math.radians(60))) & ~bed
    return round(float(area[down].sum()), 2)
print("support mm2: R43", support(new), "R41", support(old))
new.exportBrep(str(FILES / "r43" / "variants" / "p22_r43_final.brep"))
