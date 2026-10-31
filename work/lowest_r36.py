import sys
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import build_chute_chamfer_rack_r36 as r36
from audit_tool_owned_2510 import bounds
s = r36.scene()
rows = []
for name, shape in s["carriage_parts"]:
    for i, solid in enumerate(shape.Solids()):
        b = bounds(solid)
        if b[4] < -76.0:
            rows.append((round(b[4], 3), name, i, [round(v, 2) for v in b]))
for r in sorted(rows)[:20]:
    print(r)
c = bounds(s["cartographer"]); print("cartographer", [round(v, 2) for v in c])
