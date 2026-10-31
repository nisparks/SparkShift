"""Jet-detail cut-aways for the Fusion review (session scratch): the left jet's duct-to-slot wall with its bell-mouth
round, seen from the side channel, before the review (the committed revision 43, round to Y26.2 with the tapered foot)
and after (round from the heel to the front wall). Everything outboard of X-13.4 is cut away."""
import subprocess
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import os  # noqa: E402

os.chdir(CAD)
import cadquery as cq  # noqa: E402

import r43_parts as R  # noqa: E402

OUT = Path(__file__).parent / "fusion_user_edit"
old_step = OUT / "r43_committed_p22.step"
if not old_step.exists():
    data = subprocess.run(["git", "show", "HEAD:cad/SparkShift_Accessories_v26/step/P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW.step"],
                          capture_output=True, check=True).stdout
    old_step.write_bytes(data)
old = cq.importers.importStep(str(old_step)).val()
new = R.p22()
box = cq.Solid.makeBox(13.4 - 9.0, 18.0, 13.0, cq.Vector(-13.4, 12.0, -79.0))   # X-13.4..-9, Y12..30, Z-79..-66
rows = []
for tag, s, dx in (("Jet_Before_Review", old, 200.0), ("Jet_After_Review", new, 240.0)):
    cut = s.intersect(box).translate(cq.Vector(dx, 0, 0))
    path = OUT / f"{tag}.step"
    cq.exporters.export(cq.Workplane().add(cut), str(path))
    rows.append((tag, round(cut.Volume(), 2), path))
for r in rows:
    print(*r)
