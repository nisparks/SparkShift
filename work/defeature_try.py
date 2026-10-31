"""Try OCC defeaturing on the micro-faces of P20 and P22 (session experiment)."""
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Defeaturing  # noqa: E402

import r41_parts as R  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402
from build_modular_toolhead import load  # noqa: E402


def width(f):
    per = sum(e.Length() for e in f.Edges())
    return 2 * f.Area() / per if per else 0.0


def micro(s, area=0.25, w=0.06):
    return [f for f in s.Faces() if f.Area() < area and width(f) < w or f.Area() < 0.02]


def defeature(s, faces):
    d = BRepAlgoAPI_Defeaturing()
    d.SetShape(s.wrapped)
    for f in faces:
        d.AddFaceToRemove(f.wrapped)
    d.SetRunParallel(False)
    d.SetToFillHistory(False)
    d.Build()
    if not d.IsDone():
        return None, "not done"
    out = cq.Shape.cast(d.Shape())
    return out, "ok"


def report(tag, s, old):
    small = [(round(f.Area(), 4), round(width(f), 3), f.geomType(), [round(v, 2) for v in bounds(f)]) for f in s.Faces()
             if f.Area() < 0.5 or width(f) < 0.15]
    print(f"  {tag}: valid {s.isValid()} solids {len(s.Solids())} faces {len(s.Faces())} dV {s.Volume() - old.Volume():+.4f} "
          f"changed {old.cut(s).Volume() + s.cut(old).Volume():.4f} mm3; small/thin faces {len(small)}")
    for row in small:
        print("     ", row)


for part in sys.argv[1:]:
    s = load(R.NAMES[part])
    faces = micro(s)
    print(f"== {part}: {len(faces)} micro faces:", [(round(f.Area(), 4), round(width(f), 3), [round(v, 2) for v in bounds(f)][:4]) for f in faces])
    out, msg = defeature(s, faces)
    if out is None:
        print("  all at once:", msg)
        for f in faces:
            o1, m1 = defeature(s, [f])
            print("   one face", round(f.Area(), 4), [round(v, 2) for v in bounds(f)], "->", m1,
                  None if o1 is None else (o1.isValid(), round(o1.Volume() - s.Volume(), 4)))
    else:
        report("all at once", out, s)
