"""Where does the clearance/motion time go? Times the building blocks used by the R29-R32 scripts."""

import sys
import time

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

from audit_tool_owned_2510 import bounds, compound, overlaps
from build_bambu_clean_r30 import PITCH
from build_modular_toolhead import STEP, load
from build_refined_docking_review import translated_hits

TMP = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\profile_tmp.brep"


def timed(label, fn, *args):
    t = time.perf_counter()
    out = fn(*args)
    print(f"{label:<62} {time.perf_counter() - t:8.2f} s", flush=True)
    return out


print("== Loading")
for name in ("Core_With_Restrained_AHG_Lead_References_REVIEW", "21_Bambu_Closed_Panel_Dock_Complete_REVIEW",
             "P22_CPAP_Lower_Plenum_Lowered_Mounts_R31_REVIEW", "31_Carriage_Lowered_Mounts_Complete_REVIEW"):
    mb = (STEP / f"{name}.step").stat().st_size / 2**20
    shape = timed(f"STEP {name[:40]} ({mb:.0f} MB)", load, name)
    timed("  write BREP", shape.exportBrep, TMP)
    timed("  read BREP", cq.Shape.importBrep, TMP)
from audit_low_z_bed_clearance import load_parked_variants
timed("load_parked_variants() (snapshots + 2 docks)", load_parked_variants)

core = load("Core_With_Restrained_AHG_Lead_References_REVIEW").Solids()
p01 = load("P01_Back_case_COTS_MR74_Lowered_Bosses_R31_REVIEW")
p22 = load("P22_CPAP_Lower_Plenum_Lowered_Mounts_R31_REVIEW")
carriage = [s for i, s in enumerate(core) if i != 54] + [p01, p22] + [
    s for n in ("P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge", "P23_Beacon_Cartographer_Mount",
                "P24_EBB42_Controller_Mount") for s in load(n).Solids()]
body = load("Bambu_Compact_Flush_Side_R32_REVIEW")
dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")
tool = [body] + [s for n in ("Tool2510_Reversed_Bambu_Reference_REVIEW", "Tool2510_Existing_Tool_M2_5_Hardware_REVIEW",
                             "Bambu_Fan_2510_And_Screws_R30_REVIEW", "Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW",
                             "P18_Tool_docking_backplate_3010") for s in load(n).Solids()] + dock.Solids()
parked = [s.translate((PITCH, 0, 0)) for s in tool]
print(f"\n== One clearance sample: {len(carriage)} carriage solids x {len(parked)} parked tool+dock solids")
faces = sorted(((len(s.Faces()), i) for i, s in enumerate(carriage)), reverse=True)[:3]
print("   most complex carriage solids (faces):", faces, "| R32 body faces:", len(body.Faces()))


def gap(a, b):
    return max(b[0] - a[1], a[0] - b[1], b[2] - a[3], a[2] - b[3], b[4] - a[5], a[4] - b[5], 0)


cb = [bounds(s) for s in carriage]
pb = [bounds(s) for s in parked]
pairs = [(i, j) for i in range(len(carriage)) for j in range(len(parked)) if gap(cb[i], pb[j]) <= 5.0]
print(f"   bbox-prefiltered pairs within 5 mm: {len(pairs)} of {len(carriage) * len(parked)}")


def all_pairs(multithread):
    worst = []
    for i, j in pairs:
        t = time.perf_counter()
        ext = BRepExtrema_DistShapeShape()
        ext.SetMultiThread(multithread)
        ext.LoadS1(carriage[i].wrapped)
        ext.LoadS2(parked[j].wrapped)
        ext.Perform()
        worst.append((time.perf_counter() - t, ext.Value(), len(carriage[i].Faces()), len(parked[j].Faces())))
    return sorted(worst, reverse=True)


slow = timed("   BRepExtrema on every candidate pair (1 thread)", all_pairs, False)
print("   slowest pairs (s, mm, faces A, faces B):", [tuple(round(v, 3) for v in r) for r in slow[:4]])
timed("   BRepExtrema on every candidate pair (SetMultiThread)", all_pairs, True)

print("\n== One motion sample (Boolean-based translated_hits)")
moving = compound([p01, p22])
target = compound(parked)
timed("   translated_hits(P01+P22 vs parked tool+dock, dy=0)", translated_hits, moving, {"N": target}, (0, 0, 0))
timed("   overlaps(R32 body vs whole carriage)", overlaps, body, {"C": compound(carriage)})
