"""Benchmark: whole-solid BRepExtrema (old) vs face-filtered exact distance (fast_geometry)."""

import sys
import time

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import numpy as np
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

import fast_geometry as fg
from audit_tool_owned_2510 import bounds
from build_bambu_clean_r30 import PITCH

t0 = time.perf_counter()
core = fg.load("Core_With_Restrained_AHG_Lead_References_REVIEW").Solids()
print(f"cached core load (first call builds the cache): {time.perf_counter() - t0:.2f} s", flush=True)
t0 = time.perf_counter()
core = fg.load("Core_With_Restrained_AHG_Lead_References_REVIEW").Solids()
print(f"cached core load (BREP): {time.perf_counter() - t0:.2f} s", flush=True)
carriage = [(f"core_{i}", s) for i, s in enumerate(core) if i != 54]
carriage += [("P01", fg.load("P01_Back_case_COTS_MR74_Lowered_Bosses_R31_REVIEW")),
             ("P22", fg.load("P22_CPAP_Lower_Plenum_Lowered_Mounts_R31_REVIEW"))]
for n in ("P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge", "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount"):
    carriage += [(n, s) for s in fg.load(n).Solids()]
tool = [("body", fg.load("Bambu_Compact_Flush_Side_R32_REVIEW"))]
for n in ("Tool2510_Reversed_Bambu_Reference_REVIEW", "Tool2510_Existing_Tool_M2_5_Hardware_REVIEW",
          "Bambu_Fan_2510_And_Screws_R30_REVIEW", "Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW",
          "P18_Tool_docking_backplate_3010", "21_Bambu_Closed_Panel_Dock_Complete_REVIEW"):
    tool += [(n, s) for s in fg.load(n).Solids()]

t0 = time.perf_counter()
ga = fg.index_group(carriage)
gb = fg.index_group(tool)
print(f"face indexes for {len(ga)} + {len(gb)} solids: {time.perf_counter() - t0:.2f} s", flush=True)

offset = (PITCH, 0, 0)
pairs = []
for a in ga:
    for b in gb:
        lo = fg._box_distance(a.box_lo, a.box_hi, b.box_lo + offset, b.box_hi + offset)
        if lo <= 5.0:
            pairs.append((a, b))
print(f"candidate solid pairs: {len(pairs)}", flush=True)

t0 = time.perf_counter()
new = []
for a, b in pairs:
    hit = fg.pair_distance(a, b, (0, 0, 0), offset)
    new.append(hit[0])
t_new_all = time.perf_counter() - t0
print(f"NEW exact distance for every pair (no pruning): {t_new_all:.2f} s", flush=True)

t0 = time.perf_counter()
old = []
for a, b in pairs:
    ext = BRepExtrema_DistShapeShape()
    ext.SetMultiThread(True)
    ext.LoadS1(a.shape)
    ext.LoadS2(fg._moved(b.shape, offset))
    ext.Perform()
    old.append(ext.Value())
print(f"OLD whole-solid BRepExtrema, multithreaded: {time.perf_counter() - t0:.2f} s", flush=True)
diff = np.abs(np.array(new) - np.array(old))
print(f"max per-pair difference old vs new: {diff.max():.2e} mm over {len(pairs)} pairs", flush=True)

t0 = time.perf_counter()
best = fg.min_distance(ga, gb, (0, 0, 0), offset)
print(f"NEW min_distance over the whole group (pruned): {time.perf_counter() - t0:.2f} s -> "
      f"{best[0]:.6f} mm {best[1]} vs {best[2]}; old minimum {min(old):.6f}", flush=True)
