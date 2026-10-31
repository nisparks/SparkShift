import sys, time
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
from build_modular_toolhead import load, box, volume
from build_fan_mounts_r33 import carriage
from build_carriage_lowered_mounts_r31 import labelled, nearest
from audit_tool_owned_2510 import bounds
t0 = time.time()
rig = labelled(carriage())
dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW").Solids()
chute = dock[6]
print("chute bounds", [round(v, 3) for v in bounds(chute)])
names = ["P25","UpJaw","LowJaw","Pad","M5L","M5R","P26","Wiper","M3L","M3R","BushL","BushR","MagL","MagR"]
parked = labelled([(n, s) for n, s in zip(names, dock)])
for dx in ():
    for dy in ():
        f = nearest(rig, parked, (0, dy, 0), (dx, 0, 0), cutoff=4.0)
        print(f"dx {dx:+.1f} dy {dy:4d}: {f[0]:.3f} {f[1]} | {f[2]}" if f else f"dx {dx} dy {dy}: none")
def chamfer(c):
    cut = None
    for s in (-1, 1):
        x0 = 15.0 * s
        pts = [(x0 + 0.01 * s, -78.80 + 0.01), (x0 - c * s, -78.80 + 0.01), (x0 + 0.01 * s, -78.80 - c - 0.01)]
        prism = cq.Workplane("XZ").polyline(pts).close().extrude(-40).val().translate((0, 10, 0))
        cut = prism if cut is None else cut.fuse(prism)
    return chute.cut(cut).clean()
for c in (1.0, 1.5, 2.0):
    ch = chamfer(c)
    parts = [(n, s) for n, s in zip(names, dock)]
    parts[6] = ("P26", ch)
    pk = labelled(parts)
    res = []
    for dx in (37.3, -37.3):
        for dy in (0, -1, -3, -10, -30):
            f = nearest(rig, pk, (0, dy, 0), (dx, 0, 0), cutoff=4.0)
            if f: res.append((f[0], dx, dy, f[1], f[2]))
    w = min(res)
    print(f"chamfer {c}: removed {volume(chute)-volume(ch):.2f} mm3, worst {w[0]:.3f} at dx {w[1]} dy {w[2]} {w[3]} | {w[4]}")
print("time", round(time.time() - t0, 1))

