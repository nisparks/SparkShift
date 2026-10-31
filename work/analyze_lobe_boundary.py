"""Clean-C28 lobe boundary around the spine: for each (Y, Z), where duct air starts on +X, and where the dry bay is."""
import json
import os
import sys
from pathlib import Path

CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import numpy as np
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN, TopAbs_ON

out = S / "swept_feed" / "flow_tweak"
air = cq.Shape.importBrep(str(out / "ref_air.brep"))
p22 = cq.Shape.importBrep(str(out / "ref_clean22.brep"))
p21 = cq.Shape.importBrep(str(out / "ref_old21.brep"))
classifiers = {k: BRepClass3d_SolidClassifier(s.wrapped) for k, s in (("air", air), ("p22", p22), ("p21", p21))}


def state(x, y, z):
    for key, c in classifiers.items():
        c.Perform(gp_Pnt(x, y, z), 1e-6)
        if c.State() in (TopAbs_IN, TopAbs_ON):
            return key
    return "dry"


xs = np.round(np.arange(0, 7.001, .05), 3)
rows = {}
for z in (-51.8, -53.0, -54.5, -56.0, -57.5, -58.8, -60.0, -61.5, -63.0, -64.5, -65.5, -66.5):
    for y in np.round(np.arange(-40.0, -23.9, .5), 2):
        labels = [state(x, y, z) for x in xs]
        runs, start = [], 0
        for i in range(1, len(xs) + 1):
            if i == len(xs) or labels[i] != labels[start]:
                runs.append([labels[start], float(xs[start]), float(xs[i - 1])])
                start = i
        rows[f"{z},{y}"] = runs
(out / "lobe_boundary.json").write_text(json.dumps(rows))
for z in (-53.0, -56.0, -58.8, -61.5, -64.5, -66.5):
    print(f"Z {z}")
    for y in np.round(np.arange(-40.0, -23.9, 1.0), 2):
        runs = rows[f"{z},{y}"]
        print(f"  Y {y:6.1f}: " + "  ".join(f"{k}[{a:.2f}-{b:.2f}]" for k, a, b in runs))
