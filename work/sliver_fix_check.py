"""Rebuild P20/P22 with the sliver fixes and compare with the committed parts (session check)."""
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))
sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")

import print_audit_brep as A  # noqa: E402
import r41_parts as R  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402
from build_modular_toolhead import load  # noqa: E402


def r(v):
    return [round(x, 3) for x in v]


for key, build in [(k, getattr(R, k)) for k in (sys.argv[1:] or ["p20", "p22"])]:
    old, new = load(R.NAMES[key]), build()
    added, removed = new.cut(old), old.cut(new)
    print(f"== {key}: valid {new.isValid()} solids {len(new.Solids())} faces {len(old.Faces())} -> {len(new.Faces())} "
          f"volume {old.Volume():.4f} -> {new.Volume():.4f} ({new.Volume() - old.Volume():+.4f})")
    for tag, d in (("added", added), ("removed", removed)):
        for s in sorted(d.Solids(), key=lambda s: -s.Volume()):
            if s.Volume() > 1e-6:
                print(f"   {tag} {s.Volume():.5f} mm3 at {r(bounds(s))}")
    faces = A.face_rows(new)
    short, creases, _ = A.edge_rows(new)
    old_faces = A.face_rows(load(R.P37.NAMES['p22']) if key == 'p22' else load(R.P40.NAMES['p20']))
    A.tag(faces, old_faces)
    print(f"   small/thin faces {len(faces)}; short edges {len(short)}")
    for f in sorted(faces, key=lambda f: f["centre"]):
        print(f"     {'old' if f['inherited'] else 'NEW'} {f['type']:9s} A {f['area_mm2']:.4f} w {f['width_mm']:.3f} b {f['bounds']}")
    for e in sorted(short, key=lambda e: e["mid"]):
        print(f"     short edge {e['length_mm']:.4f} at {e['mid']}")
    new.exportBrep(str(Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files") / f"_{key}_fixed.brep"))
