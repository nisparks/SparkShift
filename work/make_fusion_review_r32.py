"""Named, colored Fusion review assembly for the R32 flush-side bodies (session artifact)."""

import sys

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq

from audit_low_z_bed_clearance import load_parked_variants
from build_bambu_clean_r30 import PITCH, fan_parts
from build_carriage_lowered_mounts_r31 import CORE, CORE_P01, NAMES as R31
from build_modular_toolhead import load
from build_side_clearance_r32 import VARIANTS

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\32_Flush_Side_Fusion_Review.step"


def comp(shapes, dx=0.0):
    return cq.Compound.makeCompound([s.translate((dx, 0, 0)) for shape in shapes for s in shape.Solids()])


fan, screws, _ = fan_parts()
bambu_parts = [load("Tool2510_Reversed_Bambu_Reference_REVIEW"), load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"),
               fan, screws, load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW"), load("P18_Tool_docking_backplate_3010")]
red = load_parked_variants()["RedLizard"]
snap = red["tool"].Solids()
red_parts = [cq.Compound.makeCompound(snap[1:])]
r32 = {label: load(v["name"]) for label, v in VARIANTS.items()}
r30 = {label: load(v["base"]) for label, v in VARIANTS.items()}
core = load(CORE).Solids()
bambu_dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")
parts = [
    ("R32_Bambu_Print_active", r32["Bambu"], (0.95, 0.67, 0.10)),
    ("Active_Toolhead_parts", comp(bambu_parts), (0.55, 0.56, 0.60)),
    ("R31_P01_Lowered_Bosses", load(R31["p01"]), (0.47, 0.49, 0.54)),
    ("R31_P22_Lowered_Mounts", load(R31["p22"]), (0.10, 0.65, 0.65)),
    ("R31_P22_P01_M3_Screws_And_Heatsets", load(R31["hardware"]), (0.85, 0.60, 0.15)),
    ("Carriage_Core_other_reference", cq.Compound.makeCompound([s for i, s in enumerate(core) if i != CORE_P01]),
     (0.30, 0.33, 0.45)),
    ("CPAP_Probe_EBB42_Mounts_reference", comp([load(n) for n in (
        "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge", "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount")]),
     (0.20, 0.55, 0.35)),
    ("R32_Bambu_Print_parked_plusX", r32["Bambu"].translate((PITCH, 0, 0)), (0.95, 0.80, 0.30)),
    ("Parked_Bambu_parts_plusX", comp(bambu_parts, PITCH), (0.40, 0.41, 0.45)),
    ("R32_RedLizard_Print_parked_minusX", r32["RedLizard"].translate((-PITCH, 0, 0)), (0.90, 0.45, 0.15)),
    ("Parked_RedLizard_parts_minusX", comp(red_parts, -PITCH), (0.40, 0.41, 0.45)),
    ("R30_Prints_compare", comp([r30["Bambu"]]).fuse(comp([r30["Bambu"]], PITCH)).fuse(comp([r30["RedLizard"]], -PITCH))
     if False else cq.Compound.makeCompound(
         [*r30["Bambu"].Solids(), *r30["Bambu"].translate((PITCH, 0, 0)).Solids(),
          *r30["RedLizard"].translate((-PITCH, 0, 0)).Solids()]), (0.85, 0.30, 0.10)),
    ("Docks_reference", cq.Compound.makeCompound(
        [*bambu_dock.Solids(), *bambu_dock.translate((PITCH, 0, 0)).Solids(),
         *red["dock"].translate((-PITCH, 0, 0)).Solids()]), (0.22, 0.40, 0.32)),
]
assembly = cq.Assembly(name="32 Flush side review")
for name, shape, color in parts:
    assembly.add(shape, name=name, color=cq.Color(*color))
assembly.export(OUT)
print(OUT, sum(len(s.Solids()) for _, s, _ in parts))
print({name: round(sum(s.Volume() for s in shape.Solids()), 4) for name, shape, _ in parts if name.startswith("R32")})
