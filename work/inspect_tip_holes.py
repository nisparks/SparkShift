import sys, math
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder
from build_modular_toolhead import load, primitives
from audit_tool_owned_2510 import bounds
bam = load("Tool2510_Reversed_Bambu_Reference_REVIEW").Solids()
rl = load("P17M_RedLizard_Hotend_Reference")
print("RL hotend zmin", repr(bounds(rl)[4]), "solids", len(rl.Solids()))
for i, s in enumerate(bam):
    b = bounds(s)
    print(f"bambu solid {i}: vol {s.Volume():9.2f} faces {len(s.Faces()):4d} bbox", [round(v, 3) for v in b])
tip_i = min(range(len(bam)), key=lambda i: bounds(bam[i])[4])
tip = bam[tip_i]
print("tip solid", tip_i)
for f in tip.Faces():
    a = BRepAdaptor_Surface(f.wrapped)
    bb = f.BoundingBox()
    if bb.zmin > -77.0:
        continue
    if a.GetType() == GeomAbs_Cone:
        c = a.Cone(); ap = c.Apex(); ax = c.Axis().Direction()
        print(f" cone face: apex ({ap.X():.4f},{ap.Y():.4f},{ap.Z():.4f}) axis ({ax.X():.3f},{ax.Y():.3f},{ax.Z():.3f}) semi {math.degrees(c.SemiAngle()):.3f} ref r {c.RefRadius():.4f} z {bb.zmin:.4f}..{bb.zmax:.4f}")
    elif a.GetType() == GeomAbs_Cylinder:
        cy = a.Cylinder(); loc = cy.Location()
        print(f" cyl face: r {cy.Radius():.4f} at ({loc.X():.4f},{loc.Y():.4f}) z {bb.zmin:.4f}..{bb.zmax:.4f}")
    else:
        print(" other face type", a.GetType(), f"z {bb.zmin:.4f}..{bb.zmax:.4f}", [round(v, 3) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax)])
# Beacon PCB mounting hole radius
pcb = cq.Shape.cast(primitives.load_step(primitives.SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")[3]).translate((0, 3.2, -75))
for f in pcb.Faces():
    a = BRepAdaptor_Surface(f.wrapped)
    if a.GetType() == GeomAbs_Cylinder:
        cy = a.Cylinder(); loc = cy.Location()
        if cy.Radius() < 3:
            print(f"beacon pcb hole r {cy.Radius():.4f} at ({loc.X():.3f},{loc.Y():.3f})")
carto = [cq.Shape.cast(s).rotate((0, 0, 0), (0, 0, 1), 180).translate((0, -13.00701, -75)) for s in primitives.load_step(primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")[:100]]
big = max(carto, key=lambda s: s.Volume())
print("carto largest solid bbox", [round(v, 3) for v in bounds(big)], "vol", round(big.Volume(), 1))
for f in big.Faces():
    a = BRepAdaptor_Surface(f.wrapped)
    if a.GetType() == GeomAbs_Cylinder:
        cy = a.Cylinder(); loc = cy.Location()
        if 1.0 < cy.Radius() < 2.5:
            print(f"carto pcb hole r {cy.Radius():.4f} at ({loc.X():.3f},{loc.Y():.3f})")
near = [s for s in carto if s is not big and bounds(s)[5] > -75.05 and bounds(s)[4] < -74.5]
print("carto top-side parts above the board:", len(near))
for s in sorted(near, key=lambda s: -bounds(s)[5])[:12]:
    print("  ", [round(v, 2) for v in bounds(s)])
