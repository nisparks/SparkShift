import sys, time, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
import r37_parts as P
from audit_tool_owned_2510 import bounds, overlaps, compound
from build_modular_toolhead import load
from build_carriage_lowered_mounts_r31 import NAMES as R31
from build_p24_cable_entry_r35 import NAMES as R35
t = time.perf_counter()
p22, air = P.p22()
p23 = P.p23()
print("P23 valid", p23.isValid(), "vol", round(p23.Volume(), 2), "bbox", [round(v, 3) for v in bounds(p23)], round(time.perf_counter() - t, 1), flush=True)
b = P.beacon()
carto = P.cartographer()
cab = P.cable()
hw = P.probe_hardware()
other = P.other_hardware()
fixed = {"Core_R31": load(R31["core"]), "P20": load("P20_CPAP_Hose_Inlet"), "P21": load("P21_CPAP_Gantry_Bridge"),
         "P24_R35": load(R35["p24"]), "EBB42": P.ebb42(), **dict(other)}
new = {"P22_R37": p22, "P23_R37": p23, "Cable_R37": cab, "Beacon_block": b[2], "Beacon_board": b[3], "Beacon_connector": b[4], **dict(hw)}
seen = set()
rows = []
for na, a in new.items():
    for nb, bb in list(new.items()) + list(fixed.items()):
        if na == nb or (nb, na) in seen:
            continue
        seen.add((na, nb))
        for k, v in overlaps(a, {nb: bb}).items():
            rows.append((na, nb, round(v, 4)))
print("R37 carriage-internal overlaps (> 0.001 mm3):", len(rows))
for r in rows:
    print("  ", r)
crows = []
for nb, bb in list(new.items()) + list(fixed.items()):
    if nb.startswith("Beacon") or nb == "Cable_R37":
        continue
    for k, v in overlaps(carto, {nb: bb}).items():
        crows.append((nb, round(v, 4)))
print("Cartographer overlaps:", crows)
ko_top = P.beacon_top_keepout(b)
ko_bot = b[0]
metal = {**dict(hw), **dict(other), "EBB42": fixed["EBB42"]}
for name, ko in (("top", ko_top), ("bottom", ko_bot)):
    hits = overlaps(ko, metal)
    core_hits = overlaps(ko, {"Core_R31": fixed["Core_R31"]})
    print(f"keepout {name}: metal hits {hits}, core solids hit {core_hits}")
print("lowest new features:", sorted((round(bounds(s)[4], 3), n) for n, s in list(new.items()))[:6])
print("t", round(time.perf_counter() - t, 1))
