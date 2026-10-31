"""What sits near P22's window, block, back-bottom edge and cheeks in the assembled carriage (session scratch)."""
import sys, os, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
from pathlib import Path
import cadquery as cq
import build_and_verify_accessories_v26 as acc
import r41_parts as R41
from build_carriage_lowered_mounts_r31 import NEW_Z

SC = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43_scene")
m = json.loads((SC / "manifest.json").read_text())
print("P01 boss Z", NEW_Z, "keys of an entry:", m["carriage"][0])
parts = {}
for n, f in m["carriage"]:
    parts[n] = cq.Shape.importBrep(str(SC / f))
parts["cartographer"] = cq.Shape.importBrep(str(SC / m["cartographer"]))
for label, v in m["variants"].items():
    for n, f in v["parts"]:
        parts[f"{label}:{n}"] = cq.Shape.importBrep(str(SC / f))
print(len(parts), "parts loaded")

regions = {
    "window (Y-36.5..-5.4, |X|<11.5, Z-70.8..-57.4)": (-11.5, 11.5, -36.5, -5.3, -70.85, -57.3),
    "block (Y-5.4..8.3, |X|<13)": (-13.0, 13.0, -5.4, 8.3, -70.85, -57.3),
    "V notch zone (Y-5.4..6.1)": (-11.5, 11.5, -5.4, 6.1, -70.85, -57.3),
    "back-bottom edge (Y-45.6..-29, Z-71..-54.5)": (-22.5, 22.5, -45.6, -29.0, -71.0, -54.5),
    "behind the cheeks (Y11..15.9, |X|13.9-22.5, Z-63..-49.5)": (13.9, 22.5, 11.0, 15.9, -63.0, -49.5),
}
p22 = [n for n in parts if n.startswith("P22_")]
print("P22 in scene:", p22)
for label, (x0, x1, y0, y1, z0, z1) in regions.items():
    b = cq.Shape.cast(acc.box(x0, x1, y0, y1, z0, z1))
    bm = b.mirror("YZ") if x0 > 0 else None
    rows = []
    for n, s in parts.items():
        if n.startswith("P22_"):
            continue
        bb = s.BoundingBox()
        if bb.xmax < x0 - 3 and (bm is None) or bb.xmin > x1 + 3 and (bm is None) or bb.ymax < y0 - 3 or bb.ymin > y1 + 3 or bb.zmax < z0 - 3 or bb.zmin > z1 + 3:
            continue
        d = s.distance(b)
        if bm is not None:
            d = min(d, s.distance(bm))
        if d < 3.0:
            inside = s.intersect(b).Volume() + (s.intersect(bm).Volume() if bm is not None else 0.0)
            rows.append((round(d, 3), n, round(inside, 2)))
    rows.sort()
    print(f"\n{label}:")
    for r in rows[:14]:
        print("   gap %6.3f  inside %8.2f mm3  %s" % (r[0], r[2], r[1]))

