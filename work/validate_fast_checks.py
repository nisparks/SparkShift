"""Validate the fast helpers against the stored R30/R31/R32 reports and time them."""

import json
import math
import sys
import time

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq

import fast_geometry as fg
from audit_tool_owned_2510 import overlaps
from build_modular_toolhead import ROOT, STEP, box, load, volume
from build_refined_docking_review import translated_hits

failures = []


def check(label, ok):
    print(f"  {'OK ' if ok else 'BAD'} {label}", flush=True)
    if not ok:
        failures.append(label)


def same(a, b, tol=1e-9):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol)


print("== Nested / touching / separated Boolean screen")
big, inner = box(0, 10, 0, 10, 0, 10), box(2, 4, 2, 4, 2, 4)
check("nested solid still reported (8 mm3)", abs(overlaps(inner, {"big": big}).get("big", 0) - 8.0) < 1e-6)
check("nested found when the big one moves", abs(translated_hits(big, {"inner": inner}, (0.5, 0, 0)).get("inner", 0) - 8.0) < 1e-6)
check("touching faces give no hit", overlaps(box(10, 12, 0, 2, 0, 2), {"big": big}) == {})
check("separated give no hit", overlaps(box(10.5, 12, 0, 2, 0, 2), {"big": big}) == {})
check("crossing still reported (4 mm3)", abs(overlaps(box(9, 11, 0, 2, 0, 2), {"big": big}).get("big", 0) - 4.0) < 1e-6)

print("== BREP cache returns the same shapes as STEP import")
for name in ("Core_With_Restrained_AHG_Lead_References_REVIEW", "21_Bambu_Closed_Panel_Dock_Complete_REVIEW",
             "Bambu_Compact_Flush_Side_R32_REVIEW", "P22_CPAP_Lower_Plenum_Lowered_Mounts_R31_REVIEW"):
    a = cq.importers.importStep(str(STEP / f"{name}.step")).val()
    b = load(name)
    check(f"{name}: type, solids, faces, volume",
          type(a) is type(b) and len(a.Solids()) == len(b.Solids()) and len(a.Faces()) == len(b.Faces())
          and abs(volume(a) - volume(b)) < 1e-9)

print("== R32 clearance table (stored run: about 45 min)")
import build_side_clearance_r32 as r32
stored = json.loads((ROOT / r32.REPORT).read_text())["clearances_mm"]
t = time.perf_counter()
before = r32.clearances({label: load(v["base"]) for label, v in r32.VARIANTS.items()})
after = r32.clearances({label: load(v["name"]) for label, v in r32.VARIANTS.items()})
print(f"  time {time.perf_counter() - t:.1f} s", flush=True)
for key in after:
    for state, now in (("r30_bodies", before[key]), ("r32_bodies", after[key])):
        old = stored[key][state]
        check(f"{key} [{state}] {old['mm']:.4f} {old['a']}/{old['b']}",
              same(now["mm"], old["mm"]) and now["a"] == old["a"] and now["b"] == old["b"])

print("== R31 clearances and motion (stored run: about 45 min with exports)")
import build_carriage_lowered_mounts_r31 as r31
stored = json.loads((ROOT / r31.REPORT).read_text())
p01, p22, hw = load(r31.NAMES["p01"]), load(r31.NAMES["p22"]), r31.hardware(r31.MOUNT_DZ)
t = time.perf_counter()
clear = r31.clearances(p01, p22, hw)
print(f"  clearances time {time.perf_counter() - t:.1f} s", flush=True)
for key, value in clear.items():
    old = stored["clearances"][key]
    if key.startswith("vertical"):
        check(key, all(same(value[s], old[s]) for s in ("released", "r31")))
        continue
    for state in ("released", "r31"):
        check(f"{key} [{state}] {old[state]['mm']:.4f}",
              same(value[state]["mm"], old[state]["mm"]) and value[state]["carriage_part"] == old[state]["carriage_part"]
              and value[state]["tool_part"] == old[state]["tool_part"])
t = time.perf_counter()
motion = r31.motion(p01, p22, hw)
print(f"  motion sweeps time {time.perf_counter() - t:.1f} s", flush=True)
check("R31 motion sweeps: no hits, as stored", motion["hits"] == [] == stored["motion"]["hits"])

print("== R30 dock, retreat, service and neighbour sweeps")
import build_bambu_clean_r30 as r30
stored = json.loads((ROOT / r30.REPORT).read_text())["motion"]
t = time.perf_counter()
results, failed = r30.motion_checks(load(r30.NAME), load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW"))
print(f"  time {time.perf_counter() - t:.1f} s", flush=True)
for key in ("dock_hits", "carriage_retreat_hits", "hotend_service_hits"):
    check(f"R30 {key} unchanged ({len(stored[key])})", results[key] == stored[key])
check("R30 neighbour sweeps unchanged", [c["hits"] for c in results["neighbour_checks"]]
      == [c["hits"] for c in stored["neighbour_checks"]])
for key, value in results["minimum_distances"].items():
    old = stored["minimum_distances"][key]
    ok = same(value["mm"], old["mm"]) if isinstance(value, dict) else same(value, old)
    check(f"R30 {key}", ok)

print("\nFAILURES:" if failures else "\nALL CHECKS MATCH", failures if failures else "")
