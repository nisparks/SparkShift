"""Named, colored Fusion review assembly for the R29 Bambu toolhead (session artifact)."""

import sys

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq

from build_modular_toolhead import load

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\29_Bambu_Clean_Fusion_Review.step"

parts = [
    ("R29_Bambu_Print", load("Bambu_Clean_Rebuild_R29_REVIEW"), (0.95, 0.67, 0.10)),
    ("R22_Baseline_Print_compare", load("Bambu_One_Piece_Shelf_Clearance_R22_REVIEW"), (0.85, 0.35, 0.10)),
    ("Bambu_Hotend", load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.74, 0.74, 0.77)),
    ("Hotend_M2p5_Hardware", load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"), (0.20, 0.70, 0.30)),
    ("Fan_2510", load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW"), (0.12, 0.13, 0.16)),
    ("Fan_Screws_M2p5x14", load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW"), (0.55, 0.55, 0.58)),
    ("Fan_Inserts_M2p5_L4", load("Bambu_Fan_Side_M2p5_L4_Inserts_R29_REVIEW"), (0.80, 0.55, 0.20)),
    ("P18_Docking_Backplate", load("P18_Tool_docking_backplate_3010"), (0.80, 0.15, 0.75)),
    ("Carriage_Core_reference", load("Core_With_Restrained_AHG_Lead_References_REVIEW"), (0.36, 0.39, 0.43)),
    ("CPAP_Probe_EBB42_Mounts_reference", cq.Compound.makeCompound([
        s for n in ("P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
                    "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount")
        for s in load(n).Solids()]), (0.10, 0.60, 0.62)),
    ("Dock_reference", load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW"), (0.22, 0.40, 0.32)),
]
assembly = cq.Assembly(name="29 Bambu clean rebuild review")
for name, shape, color in parts:
    assembly.add(shape, name=name, color=cq.Color(*color))
assembly.export(OUT)
print(OUT, sum(len(s.Solids()) for _, s, _ in parts))
