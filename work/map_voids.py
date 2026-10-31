"""Map empty space around the Bambu shelf/front junction against all neighbouring parts."""

import json
import sys

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq

from audit_tool_owned_2510 import bounds, boxes_overlap
from build_modular_toolhead import box, load, volume

body = load(sys.argv[1])
roi = box(*[float(v) for v in sys.argv[2].split(",")])
names = [
    "P18_Tool_docking_backplate_3010", "Core_With_Restrained_AHG_Lead_References_REVIEW",
    "Tool2510_Reversed_Bambu_Reference_REVIEW", "Tool2510_Existing_Tool_M2_5_Hardware_REVIEW",
    "Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
    "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
]
void = roi.cut(body)
rb = bounds(roi)
touching = {}
for name in names:
    for i, s in enumerate(load(name).Solids()):
        if boxes_overlap(bounds(s), rb):
            overlap = volume(s.intersect(roi))
            if overlap > 0.001:
                touching[f"{name}[{i}]"] = {"roi_overlap_mm3": round(overlap, 3), "bounds": [round(v, 3) for v in bounds(s)]}
                void = void.cut(s)
void = void.cut(box(11.45, 21.45, 13, 38, -47.8, -22.8))
print("Occupying references:")
print(json.dumps(touching, indent=1))
print("Void components:")
for s in sorted(void.Solids(), key=lambda s: -volume(s)):
    v = volume(s)
    if v < 0.05:
        continue
    b = [round(x, 3) for x in bounds(s)]
    faces = [n for n, (i, sign) in zip(("-X", "+X", "-Y", "+Y", "-Z", "+Z"), [(0, 0), (1, 1), (2, 0), (3, 1), (4, 0), (5, 1)])
             if abs(b[i] - rb[i]) < 0.002]
    print(f"  vol {v:9.3f}  bounds {b}  open_to_roi_faces {faces}")
