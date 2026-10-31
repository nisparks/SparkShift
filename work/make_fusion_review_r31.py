"""Named, colored Fusion review assembly for the R31 lowered P22-to-P01 mounts (session artifact)."""

import sys

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq

from build_bambu_clean_r30 import PITCH, fan_parts
from build_carriage_lowered_mounts_r31 import CORE, CORE_P01, NAMES, P01_BASE, P22_BASE, hardware
from build_modular_toolhead import load

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\31_Carriage_Lowered_Mounts_Fusion_Review.step"
fan, screws, _ = fan_parts()
tool = [
    ("R30_Bambu_Print", load("Bambu_Compact_Fan_Closed_Bores_R30_REVIEW"), (0.95, 0.67, 0.10)),
    ("Bambu_Hotend", load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.74, 0.74, 0.77)),
    ("Hotend_M2p5_Hardware", load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"), (0.20, 0.70, 0.30)),
    ("Fan_2510", fan, (0.12, 0.13, 0.16)),
    ("Fan_Screws_M2p5x14", screws, (0.55, 0.55, 0.58)),
    ("Fan_Inserts_M2p5_L4", load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW"), (0.80, 0.55, 0.20)),
    ("P18_Docking_Backplate", load("P18_Tool_docking_backplate_3010"), (0.80, 0.15, 0.75)),
]
core = load(CORE).Solids()
parts = [
    ("R31_P01_Lowered_Bosses", load(NAMES["p01"]), (0.47, 0.49, 0.54)),
    ("R31_P22_Lowered_Mounts", load(NAMES["p22"]), (0.10, 0.65, 0.65)),
    ("R31_P22_P01_M3_Screws_And_Heatsets", load(NAMES["hardware"]), (0.85, 0.60, 0.15)),
    ("R30_P01_released_compare", load(P01_BASE), (0.85, 0.35, 0.10)),
    ("R30_P22_released_compare", load(P22_BASE), (0.85, 0.35, 0.10)),
    ("R30_P22_P01_hardware_compare", cq.Compound.makeCompound([s for _, s in hardware(0.0)]), (0.85, 0.35, 0.10)),
    ("Carriage_Core_other_reference", cq.Compound.makeCompound([s for i, s in enumerate(core) if i != CORE_P01]),
     (0.30, 0.33, 0.45)),
    ("CPAP_Probe_EBB42_Mounts_reference", cq.Compound.makeCompound([
        s for n in ("P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge", "P23_Beacon_Cartographer_Mount",
                    "P24_EBB42_Controller_Mount") for s in load(n).Solids()]), (0.20, 0.55, 0.35)),
    *tool,
    ("Parked_Neighbour_Bambu_minusX", cq.Compound.makeCompound(
        [s.translate((-PITCH, 0, 0)) for _, shape, _ in tool for s in shape.Solids()]), (0.95, 0.80, 0.45)),
    ("Dock_reference", load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW"), (0.22, 0.40, 0.32)),
]
assembly = cq.Assembly(name="31 Carriage lowered mounts review")
for name, shape, color in parts:
    assembly.add(shape, name=name, color=cq.Color(*color))
assembly.export(OUT)
print(OUT, sum(len(s.Solids()) for _, s, _ in parts))
