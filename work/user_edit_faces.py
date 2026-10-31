"""Faces of revision 43's P22 that the user's Fusion edit removed or changed, and the faces it has instead (matched on
surface type, area and centroid)."""
from pathlib import Path

import cadquery as cq

ROOT = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
HERE = Path(__file__).parent
user = cq.importers.importStep(str(HERE / "fusion_user_edit" / "user_p22_local.step")).val()
r43 = cq.importers.importStep(str(ROOT / "step" / "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW.step")).val()


def rows(s):
    out = []
    for f in s.Faces():
        c = f.Center()
        bb = f.BoundingBox()
        out.append((f.geomType(), round(f.Area(), 3), (round(c.x, 2), round(c.y, 2), round(c.z, 2)),
                    tuple(round(v, 2) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax))))
    return out


a, b = rows(r43), rows(user)


def same(p, q):
    return p[0] == q[0] and abs(p[1] - q[1]) < 0.02 + 0.002 * p[1] and all(abs(u - v) < 0.05 for u, v in zip(p[2], q[2]))


only_a = [p for p in a if not any(same(p, q) for q in b)]
only_b = [q for q in b if not any(same(p, q) for p in a)]
print(f"R43 faces {len(a)}, user {len(b)}; only in R43: {len(only_a)}, only in user: {len(only_b)}")
for tag, rr in (("R43 only", only_a), ("user only", only_b)):
    for r in sorted(rr, key=lambda r: r[2]):
        print(f"  {tag:9s} {r[0]:10s} area {r[1]:9.3f}  centre {r[2]}  bbox {r[3]}")
