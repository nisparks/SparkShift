"""Named, colored Fusion review assembly for the R33 fan mounts (session artifact)."""

import sys

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq

from build_bambu_clean_r30 import PITCH, fan_parts
from build_carriage_lowered_mounts_r31 import NAMES as R31
from build_fan_mounts_r33 import CARRIAGE, NAMES, red_lizard_parts
from build_modular_toolhead import load
from build_side_clearance_r32 import VARIANTS as R32

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\33_Fan_Mounts_Fusion_Review.step"
RL_X = -PITCH


def comp(shapes, dx=0.0):
    return cq.Compound.makeCompound([s.translate((dx, 0, 0)) for shape in shapes for s in shape.Solids()])


fan, _, _ = fan_parts()
rl = red_lizard_parts()
screws3 = [s for s in load(NAMES["bambu_fan"]).Solids() if s.Volume() < 300]
parts = [
    ("R33_Bambu_Print", load(NAMES["bambu"]), (0.95, 0.67, 0.10)),
    ("Bambu_Fan_2510", fan, (0.12, 0.13, 0.16)),
    ("Bambu_Fan_Screws_3x_M2p5x14", cq.Compound.makeCompound(screws3), (0.55, 0.55, 0.58)),
    ("Bambu_Fan_Inserts_3x_M2p5_L4", load(NAMES["bambu_inserts"]), (0.85, 0.60, 0.15)),
    ("Bambu_Hotend_And_Hardware", comp([load("Tool2510_Reversed_Bambu_Reference_REVIEW"),
                                        load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")]), (0.74, 0.74, 0.77)),
    ("Bambu_P18", load("P18_Tool_docking_backplate_3010"), (0.80, 0.15, 0.75)),
    ("R33_RedLizard_Print", load(NAMES["redlizard"]).translate((RL_X, 0, 0)), (0.90, 0.40, 0.12)),
    ("RedLizard_Fan_2510", rl["fan"].translate((RL_X, 0, 0)), (0.12, 0.13, 0.16)),
    ("RedLizard_Fan_Screws_2x_M2p5x14", comp([rl["screws"]], RL_X), (0.55, 0.55, 0.58)),
    ("RedLizard_Fan_Inserts_2x_M2p5_L4", comp([load(NAMES["redlizard_inserts"])], RL_X), (0.85, 0.60, 0.15)),
    ("RedLizard_Hotend_And_Hardware", comp([rl["hotend"]], RL_X), (0.74, 0.74, 0.77)),
    ("RedLizard_P18_And_Magnets", comp([rl["p18"]], RL_X), (0.80, 0.15, 0.75)),
    ("R32_Prints_compare", cq.Compound.makeCompound([*load(R32["Bambu"]["name"]).Solids(),
                                                     *load(R32["RedLizard"]["name"]).translate((RL_X, 0, 0)).Solids()]),
     (0.85, 0.30, 0.10)),
    ("Docks_reference", comp([load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")]).fuse(comp([rl["dock"]], RL_X))
     if False else cq.Compound.makeCompound([*load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW").Solids(),
                                            *rl["dock"].translate((RL_X, 0, 0)).Solids()]), (0.22, 0.40, 0.32)),
    ("Carriage_R31_reference", comp([load(n) for n in CARRIAGE]), (0.36, 0.39, 0.43)),
]
assembly = cq.Assembly(name="33 Fan mounts review")
for name, shape, color in parts:
    assembly.add(shape, name=name, color=cq.Color(*color))
assembly.export(OUT)
print(OUT, sum(len(s.Solids()) for _, s, _ in parts))
print({n: round(sum(x.Volume() for x in s.Solids()), 4) for n, s, _ in parts if n.startswith("R33")})
