import sys, math, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
import os
os.chdir(sys.path[0])
from pathlib import Path
import cadquery as cq
import trimesh
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
import r41_parts as R41
import r43_parts as R
import print_audit_brep as AU

V = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\variants")

def floor_min(s):
    isect = IntCurvesFace_ShapeIntersector()
    isect.Load(s.wrapped, 1e-6)
    worst = (9.0, None)
    for x in (10.3, 11.0, 12.0, 12.8, -10.3, -12.0):
        for k in range(0, 177):
            y = 19.05 + 0.05 * k
            isect.Perform(gp_Lin(gp_Pnt(x, y, -79.0), gp_Dir(0, 0, 1)), 0.0, 6.0)
            z = sorted(isect.Pnt(i).Z() for i in range(1, isect.NbPnt() + 1))
            if len(z) >= 2 and z[1] - z[0] < worst[0]:
                worst = (round(z[1] - z[0], 3), (x, round(y, 2)))
    return worst

def support(s):
    s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90)
    bb = s.BoundingBox()
    s = s.translate(cq.Vector(0, 0, -bb.zmin))
    p = V / "tmp_print.stl"
    cq.exporters.export(s, str(p), tolerance=0.03, angularTolerance=0.1)
    m = trimesh.load_mesh(str(p)); p.unlink()
    n, area, z = m.face_normals, m.area_faces, m.triangles_center[:, 2]
    bed = (n[:, 2] < -0.999) & (z < 0.01)
    down = (n[:, 2] < -math.sin(math.radians(60))) & ~bed
    return round(float(area[down].sum()), 2)

old = R41.p22()
new = R.p22()
print("final: valid", new.isValid(), "solids", len(new.Solids()), "volume", round(new.Volume(), 2), "faces", len(new.Faces()),
      "floor min", floor_min(new), flush=True)
print("support mm2: final", support(new), "R41", support(old), flush=True)
new.exportBrep(str(V / "p22_r43_lowbell_taper.brep"))
slot = cq.Shape.cast(R.a.box(-11.65, 11.65, 8.0, 16.69, -80.0, -60.0))
print("inside the widened slot region (|X|<11.65, Y<16.69): R43", round(new.intersect(slot).Volume(), 4), "R41", round(old.intersect(slot).Volume(), 4), flush=True)

for name, fn in ((("lowbell", R.low_bell_study), ("front", R.front_study), ("frontbell", lambda: R.front_study(bell=True)),
                 ("r43_final", R.pocket_study), ("low", R.low_study), ("bell", R.bell_study), ("combo", lambda: R.bell_study(low=True))))[:1]:
    ref = cq.Shape.importBrep(str(V / f"p22_{name}.brep"))
    s = fn()
    d = s.cut(ref).Volume() + ref.cut(s).Volume()
    print(f"study {name}: volume {s.Volume():.2f} vs simulated {ref.Volume():.2f}, symmetric difference {d:.4f} mm3", flush=True)

lb = cq.Shape.importBrep(str(V / "p22_lowbell.brep"))
add, rem = new.cut(lb), lb.cut(new)
print("final vs simulated lowbell: added", round(add.Volume(), 4), "mm3, bounds", [round(v, 2) for v in (add.BoundingBox().xmin, add.BoundingBox().xmax, add.BoundingBox().ymin, add.BoundingBox().ymax, add.BoundingBox().zmin, add.BoundingBox().zmax)] if add.Volume() > 0 else None,
      "removed", round(rem.Volume(), 4), flush=True)

nf, of = AU.face_rows(new), AU.face_rows(old)
ns, nc, _ = AU.edge_rows(new)
os_, oc, _ = AU.edge_rows(old)
for k, rows, olds in (("small_or_thin_faces", nf, of), ("short_edges", ns, os_), ("shallow_creases", nc, oc)):
    rows = AU.tag(rows, olds)
    fresh = [x for x in rows if not x["inherited"]]
    print(k, len(rows), "new:", json.dumps(fresh), flush=True)

