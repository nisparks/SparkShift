"""The lower CPAP duct (P21 + P22, revision 41) for Fusion: complete, and two cutaways (session helper)."""
import json
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402

import print_colors as PC  # noqa: E402
import r41_parts as R  # noqa: E402
from build_modular_toolhead import box, load  # noqa: E402

FILES = Path(__file__).resolve().parent
OUT = FILES / "r41_lower_duct.step"
SIDE_CUT_X, TOP_CUT_Z = 16.0, -63.0          # along the right side channel (as CFD image 85); through the channels
OFFSET_SIDE, OFFSET_TOP = (70.0, 0.0, 0.0), (-70.0, 0.0, 0.0)


def main():
    p21, p22 = load(R.NAMES["p21"]), load(R.NAMES["p22"])
    c21, c22 = PC.part("P21"), PC.part("P22")
    items = [("P21 gantry bridge (R41)", p21, c21), ("P22 lower plenum (R41)", p22, c22)]
    keep_side = box(-40, SIDE_CUT_X, -60, 40, -90, 0)
    for name, s, c in (("P21", p21, c21), ("P22", p22, c22)):
        items.append((f"Cutaway at X{SIDE_CUT_X:g}, {name}", s.intersect(keep_side).translate(cq.Vector(*OFFSET_SIDE)), c))
    keep_low = box(-40, 40, -60, 40, -90, TOP_CUT_Z)
    items.append((f"Cutaway at Z{TOP_CUT_Z:g}, P22", p22.intersect(keep_low).translate(cq.Vector(*OFFSET_TOP)), c22))
    assy = cq.Assembly(name="R41_lower_CPAP_duct")
    for name, s, c in items:
        if s.Volume() < 1e-3:
            raise ValueError(f"{name}: empty")
        assy.add(s, name=name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", ""),
                 color=cq.Color(*c, 1.0))
    assy.save(str(OUT), "STEP")
    print(json.dumps({"file": str(OUT), "items": [(n, round(s.Volume(), 1)) for n, s, _ in items]}, indent=1))


if __name__ == "__main__":
    main()
