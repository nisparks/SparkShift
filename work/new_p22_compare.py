"""Build revision 43's P22 with the review's changes and compare it with the user's Fusion body and with the committed
R43 (session scratch)."""
import json
import sys
import time
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import os  # noqa: E402

os.chdir(CAD)
import cadquery as cq  # noqa: E402

import r43_parts as R  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "fusion_user_edit"
t0 = time.time()
new = R.p22()
print(f"built in {time.time() - t0:.0f} s: valid {new.isValid()}, solids {len(new.Solids())}, volume {new.Volume():.2f}, "
      f"faces {len(new.Faces())}")
cq.exporters.export(cq.Workplane().add(new), str(OUT / "new_p22.step"))
cq.exporters.export(cq.Workplane().add(new), str(OUT / "new_p22.stl"), tolerance=0.01, angularTolerance=0.08)
user = cq.importers.importStep(str(OUT / "user_p22_local.step")).val()
old = cq.importers.importStep(str(CAD / "step" / "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW.step")).val()


def pieces(s, tag):
    rows = []
    for so in s.Solids():
        v = so.Volume()
        if v < 2e-3:
            continue
        bb = so.BoundingBox()
        rows.append({"what": tag, "mm3": round(v, 3), "bbox": [round(x, 2) for x in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)]})
    return sorted(rows, key=lambda r: -r["mm3"])


for label, ref in (("vs user", user), ("vs committed R43", old)):
    print(f"--- new {label}: ref volume {ref.Volume():.2f}")
    for r in pieces(new.cut(ref), "new has more") + pieces(ref.cut(new), "new has less"):
        print("  ", json.dumps(r))
