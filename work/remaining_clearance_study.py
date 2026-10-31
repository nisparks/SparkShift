"""Closest-point study for the remaining carriage and parked-tool clearances after R31 (investigation only)."""

import json
import sys

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

from OCP.BRepExtrema import BRepExtrema_DistShapeShape

from audit_tool_owned_2510 import bounds
from build_bambu_clean_r30 import PITCH
from build_carriage_lowered_mounts_r31 import NAMES, carriage_parts, hardware, tools
from build_modular_toolhead import box, load


def closest(a, b):
    ext = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    ext.Perform()
    p, q = ext.PointOnShape1(1), ext.PointOnShape2(1)
    return ext.Value(), (round(p.X(), 3), round(p.Y(), 3), round(p.Z(), 3)), (round(q.X(), 3), round(q.Y(), 3), round(q.Z(), 3))


def gap(sb, tb):
    return max(tb[0] - sb[1], sb[0] - tb[1], tb[2] - sb[3], sb[2] - tb[3], tb[4] - sb[5], sb[4] - tb[5], 0)


def study(group_a, group_b, dx, cutoff=2.6, keep=8):
    """group_a stays put; group_b is shifted dx. Points are reported in group_a's frame."""
    found = []
    for na, sa in group_a:
        for a in sa.Solids():
            ab = bounds(a)
            for nb, sb in group_b:
                for b in sb.Solids():
                    bm = b.translate((dx, 0, 0))
                    if gap(ab, bounds(bm)) > cutoff:
                        continue
                    d, p, q = closest(a, bm)
                    if d < cutoff:
                        found.append({"mm": round(d, 4), "a": na, "b": nb, "point_a": p, "point_b": q,
                                      "point_b_in_own_frame": (round(q[0] - dx, 3), q[1], q[2])})
    found.sort(key=lambda r: r["mm"])
    out, seen = [], set()
    for r in found:
        if (r["a"], r["b"]) in seen:
            continue
        seen.add((r["a"], r["b"]))
        out.append(r)
    return out[:keep]


unchanged, changed = carriage_parts(load(NAMES["p01"]), load(NAMES["p22"]), hardware(-1.5))
carriage = unchanged + changed
variants = tools()
report = {}
for label, tool in variants.items():
    parts = tool["parts"]
    fan_only = [(n, s) for n, s in parts if n in tool["fan"]]
    print("carriage vs", label, flush=True)
    report[f"carriage | own {label} fan"] = study(carriage, fan_only, 0.0)
    report[f"carriage | {label} parked at +37.3"] = study(carriage, parts, PITCH)
    report[f"carriage | {label} parked at -37.3"] = study(carriage, parts, -PITCH)
for la, ta in variants.items():
    for lb, tb in variants.items():
        print("parked", la, "next to", lb, flush=True)
        report[f"parked {la} | {lb} at +37.3 (fan side of {la})"] = study(ta["parts"], tb["parts"], PITCH, keep=4)
# Extremes of each printed body on its -X (non-fan) side, by Z band.
for label, tool in variants.items():
    body = dict(tool["parts"])[[n for n in tool["moving"]][0]]
    rows = []
    for z0, z1 in ((-66, -48), (-48, -26), (-26, -22.5), (-22.5, -17.3), (-17.3, 0), (0, 49)):
        part = body.copy().intersect(box(-20, 0, 0, 50, z0, z1))
        if part.Solids():
            b = bounds(part)
            rows.append({"z_band": [z0, z1], "x_min": round(b[0], 3), "y_range": [round(b[2], 3), round(b[3], 3)]})
    report[f"{label} body -X extremes"] = rows
print(json.dumps(report, indent=1))
