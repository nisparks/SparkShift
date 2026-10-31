"""Cartographer keepout (model solids 100/101, never checked before) against every metal part, at both heights."""
import json
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402

import build_and_verify_accessories_v26 as acc  # noqa: E402
import build_carriage_fixes_r41 as V  # noqa: E402
import r37_parts as P37  # noqa: E402
from audit_tool_owned_2510 import bounds, compound, overlaps  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31  # noqa: E402
from build_modular_toolhead import load, primitives  # noqa: E402

raw = primitives.load_step(primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")


def placed(i, dz):
    s = raw[i] if isinstance(raw[i], cq.Shape) else cq.Shape.cast(raw[i])
    return s.rotate((0, 0, 0), (0, 0, 1), 180).translate((0, -13.00701, -75 + dz))


parts = V.build_parts()
metal = {**dict(parts["hardware"]), **dict(parts["other_hardware"]), "EBB42": parts["ebb42"]}
for label, v in parts["tools"].items():
    metal[f"{label}_hotend"] = v["hotend"]
    for name, s in v["parts"]:
        if any(k in name for k in ("screw", "insert", "hardware", "magnet", "pin")):
            metal[f"{label}_{name}"] = s

meta = json.loads((acc.WORK / "v26_meta.json").read_text())
v26 = [(m, P37.shape(s)) for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))]
by_key = {V.key(s): m for m, s in v26}
core_metal, core_printed = {}, {}
for i, s in enumerate(load(R31["core"]).Solids()):
    m = by_key.get(V.key(s))
    name = m["name"] if m else f"Core_{i:03d}"
    (core_metal if (m and m.get("is_metal")) else core_printed)[name] = s
print("metal parts:", len(metal), "core metal:", len(core_metal), "core other:", len(core_printed))
print("meta keys sample:", sorted(meta[0].keys()))

out = {}
for tag, dz in (("shared P23 (2.61 mm)", P37.DZ), ("Cartographer P23 (2.81 mm)", P37.DZ + 0.2)):
    top, bottom = placed(101, dz), placed(100, dz)
    row = {"top_bounds": [round(v, 2) for v in bounds(top)], "bottom_bounds": [round(v, 2) for v in bounds(bottom)]}
    for zone, ko in (("top", top), ("bottom", bottom)):
        row[f"{zone}_metal_mm3"] = overlaps(ko, metal)
        row[f"{zone}_core_metal_mm3"] = overlaps(ko, core_metal)
        row[f"{zone}_core_other_mm3"] = overlaps(ko, core_printed)
        row[f"{zone}_nearest_metal_mm"] = round(min(ko.distance(s) for s in list(metal.values()) + list(core_metal.values())), 3)
    out[tag] = row
print(json.dumps(out, indent=1, default=str))
