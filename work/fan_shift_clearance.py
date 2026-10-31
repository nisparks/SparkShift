"""Clearance study: does pulling the Bambu fan inward buy dock/neighbour space? (investigation only)"""

import json
import sys

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq

from audit_tool_owned_2510 import bounds, compound
from build_modular_toolhead import box, load

PITCH = 37.3


def min_dist(a, b, cutoff=6.0):
    best = None
    for s in a.Solids():
        sb = bounds(s)
        for t in b.Solids():
            tb = bounds(t)
            gap = max(tb[0] - sb[1], sb[0] - tb[1], tb[2] - sb[3], sb[2] - tb[3], tb[4] - sb[5], sb[4] - tb[5], 0)
            if gap > cutoff or (best is not None and gap >= best):
                continue
            d = s.distance(t)
            if best is None or d < best:
                best = d
    return best


body = load("Bambu_Clean_Rebuild_R29_REVIEW")
hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
hw = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")
fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")
p18 = load("P18_Tool_docking_backplate_3010")
dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")
carriage = compound([load(n) for n in (
    "Core_With_Restrained_AHG_Lead_References_REVIEW", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
    "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount")])
from audit_low_z_bed_clearance import load_parked_variants
red = load_parked_variants()["RedLizard"]
red_tool = red["tool"]

report = {}
for shift in (0.0, -1.0, -1.65):
    f = compound([fan.translate((shift, 0, 0)), screws.translate((shift, 0, 0))])
    tool = compound([body, hotend, hw, p18, f])
    r = {"fan_screw_xmax": bounds(f)[1]}
    # Parked neighbours on the fan side (+X): another Bambu and a Red Lizard.
    r["parked_bambu_plusX"] = min_dist(tool, tool.translate((PITCH, 0, 0)))
    r["parked_redlizard_plusX"] = min_dist(tool, red_tool.translate((PITCH, 0, 0)))
    r["parked_redlizard_minusX"] = min_dist(tool, red_tool.translate((-PITCH, 0, 0)))
    r["own_dock"] = min_dist(tool, dock)
    report[shift] = r
    print(shift, r, flush=True)
# Active carriage passing parked neighbours (independent of the fan position).
for label, neighbour in (("bambu", compound([body, hotend, hw, p18, fan, screws])), ("redlizard", red_tool)):
    worst = None
    for dy in (0, -5, -10, -20, -30, -45, -60):
        for dx in (PITCH, -PITCH):
            d = min_dist(carriage.translate((0, dy, 0)), neighbour.translate((dx, 0, 0)))
            if d is not None and (worst is None or d < worst[0]):
                worst = (d, dx, dy)
    report[f"carriage_vs_parked_{label}"] = worst
    print("carriage vs parked", label, worst, flush=True)
print(json.dumps({str(k): v for k, v in report.items()}, indent=1))
