"""Where the metal sits in the Cartographer's top keepout, and the Beacon keepout's shape for comparison."""
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))
sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")

import json  # noqa: E402

import cadquery as cq  # noqa: E402

import build_and_verify_accessories_v26 as acc  # noqa: E402
import build_carriage_fixes_r41 as V  # noqa: E402
import r37_parts as P37  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31  # noqa: E402
from build_modular_toolhead import load, primitives  # noqa: E402

raw = primitives.load_step(primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")


def placed(i, dz):
    s = raw[i] if isinstance(raw[i], cq.Shape) else cq.Shape.cast(raw[i])
    return s.rotate((0, 0, 0), (0, 0, 1), 180).translate((0, -13.00701, -75 + dz))


r = lambda b: [round(v, 2) for v in b]
meta = json.loads((acc.WORK / "v26_meta.json").read_text())
v26 = [(m, P37.shape(s)) for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))]
by_key = {V.key(s): m["name"] for m, s in v26}
core = {by_key.get(V.key(s), f"Core_{i:03d}"): s for i, s in enumerate(load(R31["core"]).Solids())}
names = [n for n in core if n.startswith(("MONOC_M3_NUT", "MONOC_M3x16_DRAW"))]
b = P37.beacon()
beacon_top = P37.beacon_top_keepout(b)
print("Beacon board top Z", round(bounds(b[0])[5], 2), "Beacon top keepout", r(bounds(beacon_top)), "vol", round(beacon_top.Volume(), 1))
for dz, tag in ((P37.DZ, "2.61"), (P37.DZ + 0.2, "2.81")):
    top = placed(101, dz)
    tb = bounds(top)
    print(f"Cartographer at {tag} mm: top keepout {r(tb)}, vol {top.Volume():.1f}; coil centre (0, {(tb[2] + tb[3]) / 2:.2f})")
    for n in sorted(names):
        s = core[n]
        hit = s.intersect(top)
        print(f"   {n}: part {r(bounds(s))}; inside {hit.Volume():.2f} mm3"
              + (f" at {r(bounds(hit))}, {bounds(hit)[4] - tb[4]:.2f}-{bounds(hit)[5] - tb[4]:.2f} mm above the board" if hit.Volume() > 0 else ""))
    print("   in the Beacon's top keepout:", {n: round(core[n].intersect(beacon_top).Volume(), 3) for n in sorted(names)})
