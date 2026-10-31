"""What did the user change on revision 43's P22 in Fusion? Boolean differences between the user's body (exported from
the review document, X + 90) and r43_parts.p22()'s STEP, split into connected pieces."""
import json
import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
HERE = Path(__file__).parent
USER = HERE / "fusion_user_edit" / "user_r43_redlizard_p22.step"
R43 = ROOT / "step" / "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW.step"


def load(p, dx=0.0):
    s = cq.importers.importStep(str(p)).val()
    return s.translate(cq.Vector(dx, 0, 0)) if dx else s


def pieces(s, tag):
    rows = []
    for so in s.Solids():
        v = so.Volume()
        if v < 1e-3:
            continue
        bb = so.BoundingBox()
        rows.append({"what": tag, "volume_mm3": round(v, 3),
                     "bbox": [round(x, 3) for x in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)]})
    return sorted(rows, key=lambda r: -r["volume_mm3"])


user = load(USER, -90.0)
r43 = load(R43)
print("user", round(user.Volume(), 2), "faces", len(user.Faces()), "| r43", round(r43.Volume(), 2), "faces", len(r43.Faces()))
added = user.cut(r43)
removed = r43.cut(user)
rows = pieces(added, "added") + pieces(removed, "removed")
for r in rows:
    print(json.dumps(r))
cq.exporters.export(cq.Workplane().add(added), str(HERE / "fusion_user_edit" / "added.step"))
cq.exporters.export(cq.Workplane().add(removed), str(HERE / "fusion_user_edit" / "removed.step"))
cq.exporters.export(cq.Workplane().add(user), str(HERE / "fusion_user_edit" / "user_p22_local.step"))
cq.exporters.export(cq.Workplane().add(user), str(HERE / "fusion_user_edit" / "user_p22_local.stl"), tolerance=0.02,
                    angularTolerance=0.1)
json.dump(rows, open(HERE / "fusion_user_edit" / "diff.json", "w"), indent=1)
