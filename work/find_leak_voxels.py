"""Voxel leak finder: flood the empty space around the joint from a duct seed and report how it reaches dry seeds."""
import json
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
import numpy as np
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN, TopAbs_ON

S = Path(__file__).resolve().parent
folder = S / "swept_feed" / (sys.argv[1] if len(sys.argv) > 1 else "userP21_flow_neutral_v5")
scene41 = dict(json.loads((S / "r41_scene" / "manifest.json").read_text())["carriage"])
solids = [cq.Shape.importBrep(str(folder / "p21.brep")), cq.Shape.importBrep(str(folder / "p22.brep")),
          cq.Shape.importBrep(str(S / "r41_scene" / scene41["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))]
cls = [BRepClass3d_SolidClassifier(s.wrapped) for s in solids]
h = .12
xs = np.arange(0.0, 6.0 + 1e-9, h)
ys = np.arange(-40.0, -21.0 + 1e-9, h)
zs = np.arange(-67.0, -48.6 + 1e-9, h)
empty = np.zeros((len(xs), len(ys), len(zs)), bool)
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        for k, z in enumerate(zs):
            p = gp_Pnt(float(x), float(y), float(z))
            solid = False
            for c in cls:
                c.Perform(p, 1e-7)
                if c.State() in (TopAbs_IN, TopAbs_ON):
                    solid = True
                    break
            empty[i, j, k] = not solid
print("grid", empty.shape, "empty fraction", round(empty.mean(), 3), flush=True)


def index(p):
    return (int(round((p[0] - xs[0]) / h)), int(round((p[1] - ys[0]) / h)), int(round((p[2] - zs[0]) / h)))


duct = index((6.0, -37.0, -55.0))
dry = {"bay": index((0.0, -23.0, -62.0)), "cable channel": index((0.0, -32.0, -55.2))}
assert empty[duct], "duct seed not empty"
parent = {duct: None}
queue = deque([duct])
while queue:
    c = queue.popleft()
    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
        if 0 <= n[0] < len(xs) and 0 <= n[1] < len(ys) and 0 <= n[2] < len(zs) and n not in parent and empty[n]:
            parent[n] = c
            queue.append(n)
for name, seed in dry.items():
    print(name, "seed empty", bool(empty[seed]), "reached from duct:", seed in parent)
    if seed in parent:
        path, c = [], seed
        while c is not None:
            path.append(c)
            c = parent[c]
        path.reverse()
        coords = [(round(xs[a], 2), round(ys[b], 2), round(zs[k], 2)) for a, b, k in path]
        # report where the path leaves the lobe region (x > 3.7) for the last time and the narrowest stretch
        print("  path length", len(coords))
        step = max(1, len(coords) // 40)
        print("  ", coords[::step] + [coords[-1]])
