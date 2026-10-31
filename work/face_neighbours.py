"""Neighbours of each small/thin face, to see what made it (session diagnostic)."""
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE  # noqa: E402
from OCP.TopExp import TopExp  # noqa: E402
from OCP.TopoDS import TopoDS  # noqa: E402
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape  # noqa: E402

import r41_parts as R  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402
from build_modular_toolhead import load  # noqa: E402


def r(v, n=3):
    return [round(x, n) for x in v]


def describe(f):
    c = f.Center()
    try:
        n = f.normalAt(c)
        nn = r((n.x, n.y, n.z), 2)
    except Exception:
        nn = None
    return f"{f.geomType():9s} A {f.Area():9.4f} n {nn} b {r(bounds(f))}"


def neighbours(s, pick):
    m = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(s.wrapped, TopAbs_EDGE, TopAbs_FACE, m)
    faces = s.Faces()
    for f in faces:
        if not pick(f):
            continue
        print("\n*", describe(f))
        seen = []
        for e in f.Edges():
            idx = m.FindIndex(e.wrapped)
            for g in m.FindFromIndex(idx):
                g = TopoDS.Face_s(g)
                if g.IsSame(f.wrapped) or any(g.IsSame(h) for h in seen):
                    continue
                seen.append(g)
                print("    edge L", round(e.Length(), 4), "->", describe(cq.Face(g)))


def small(f):
    a = f.Area()
    per = sum(e.Length() for e in f.Edges())
    return a < 0.5 or 2 * a / per < 0.15


part = sys.argv[1]
s = load(R.NAMES[part])
region = [float(v) for v in sys.argv[2:8]] if len(sys.argv) >= 8 else None


def pick(f):
    if not small(f):
        return False
    if region is None:
        return True
    c = f.Center()
    return region[0] <= c.x <= region[1] and region[2] <= c.y <= region[3] and region[4] <= c.z <= region[5]


neighbours(s, pick)
