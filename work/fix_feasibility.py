"""Feasibility numbers for the remaining clearance fixes (investigation only)."""

import sys

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

from audit_low_z_bed_clearance import load_parked_variants
from audit_tool_owned_2510 import bounds
from build_modular_toolhead import box, load, volume


def closest(a, b):
    ext = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    ext.Perform()
    p, q = ext.PointOnShape1(1), ext.PointOnShape2(1)
    return round(ext.Value(), 3), [round(v, 2) for v in (p.X(), p.Y(), p.Z())], [round(v, 2) for v in (q.X(), q.Y(), q.Z())]


def r(v):
    return [round(x, 3) for x in v]


red = load_parked_variants()["RedLizard"]
bambu_dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")
red_dock = red["dock"]
fan = load("Bambu_Fan_2510_And_Screws_R30_REVIEW")
red_fan = cq.Compound.makeCompound(red["tool"].Solids()[14:19])
print("Fan and screws to own dock (parked):")
for label, f, dock in (("Bambu", fan, bambu_dock), ("RedLizard", red_fan, red_dock)):
    best = min((closest(s, d) + (i,) for s in f.Solids() for i, d in enumerate(dock.Solids())
                if max(bounds(d)[2] - bounds(s)[3], bounds(s)[2] - bounds(d)[3], 0) < 8), key=lambda t: t[0])
    print(" ", label, best)
    front = [closest(s, d) + (i,) for s in f.Solids() for i, d in enumerate(dock.Solids())
             if bounds(d)[2] >= bounds(s)[3] - 0.5 and bounds(d)[0] < bounds(s)[1] and bounds(d)[1] > bounds(s)[0]
             and bounds(d)[4] < bounds(s)[5] and bounds(d)[5] > bounds(s)[4]]
    print("   dock parts directly in front of the fan (Y):", sorted(front)[:3])

print("Bambu hotend solids (heatsink identification):")
for i, s in enumerate(load("Tool2510_Reversed_Bambu_Reference_REVIEW").Solids()):
    print(f"  {i} vol {s.Volume():9.1f} bbox {r(bounds(s))}")

TRIM = (-14.2, -12.4, 11.0, 38.6, -27.0, -22.5)
bodies = {"Bambu": load("Bambu_Compact_Fan_Closed_Bores_R30_REVIEW"),
          "RedLizard": load("RedLizard_Side2510_Strip_Trim_R30_REVIEW")}
for label, name in (("Bambu", "Bambu_Compact_Fan_Closed_Bores_R30_REVIEW"),
                    ("RedLizard", "RedLizard_Side2510_Strip_Trim_R30_REVIEW")):
    lip = load(name).intersect(box(*TRIM))
    print(label, "-X lip", round(volume(lip), 3), "mm3, bounds", r(bounds(lip)) if lip.Solids() else None)
    dock = bambu_dock if label == "Bambu" else red_dock
    if lip.Solids():
        print("   lip to own dock", min(closest(lip, d) for d in dock.Solids()))
    membrane = load(name).intersect(box(11.0, 15.6, 12.5, 32.6, -22.75, -22.45))
    print(label, "fan-recess skin", round(volume(membrane), 4), "mm3, bounds",
          r(bounds(membrane)) if membrane.Solids() else None)
    body = load(name)
    print("   +X extremes by Z band:")
    for z0, z1 in ((-48, -26), (-26, -22.5), (-22.5, -17.3), (-17.3, 0), (0, 49)):
        part = load(name).intersect(box(0, 30, 0, 50, z0, z1))
        if part.Solids():
            b = bounds(part)
            print(f"     Z{z0}..{z1}: x_max {b[1]:.3f}")
# Red Lizard groove under the -X shelf: report cylindrical faces in the region.
rl = load("RedLizard_Side2510_Strip_Trim_R30_REVIEW")
print("Red Lizard faces in X-14..-9.5, Z-27..-22:")
for f in rl.Faces():
    b = f.BoundingBox()
    if b.xmin > -14.3 and b.xmax < -9.4 and b.zmin > -27.5 and b.zmax < -22.0:
        g = f.geomType()
        extra = ""
        if g == "CYLINDER":
            c = f._geomAdaptor().Cylinder()
            loc, d = c.Location(), c.Axis().Direction()
            extra = f" axis ({loc.X():.2f},{loc.Y():.2f},{loc.Z():.2f}) dir ({d.X():.0f},{d.Y():.0f},{d.Z():.0f}) r {c.Radius():.3f}"
        print(f"  {g:8s} area {f.Area():7.3f} bb {r((b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax))}{extra}")
hot = cq.Compound.makeCompound(red["tool"].Solids()[1:14])
groove_zone = box(-14.2, -9.5, 11.5, 32.0, -27.0, -22.4)
print("RL hotend/hardware inside the groove zone:", round(volume(hot.intersect(groove_zone)), 3),
      "bounds", r(bounds(hot.intersect(groove_zone))) if hot.intersect(groove_zone).Solids() else None)
