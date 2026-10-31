import json, sys
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
from fast_geometry import load
from audit_low_z_bed_clearance import load_parked_variants
from audit_ten_tool_rack import world
from audit_tool_owned_2510 import compound, bounds
from build_modular_toolhead import box, primitives
from build_fan_mounts_r33 import carriage
W = primitives.WORK
frames = json.loads((W / "rack_audit_frames.json").read_text())
frames["world_y_offset_mm"] += 6.5
frames["x_gantry_y_shift_to_dock_mm"] += 6.5
def bb(s):
    b = s.BoundingBox(); return [round(v, 2) for v in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)]
v = load_parked_variants()
crossbar = cq.importers.importStep(str(W / "rack_audit_crossbar_world.step")).val()
print("crossbar", bb(crossbar), "faces", len(crossbar.Faces()))
sec = crossbar.intersect(box(-40, -39.5, -40, 0, 180, 215))
print("crossbar section bbox", bb(sec))
for f in sec.Faces():
    b = f.BoundingBox()
    if abs(b.xmin + 40) < 1e-3 and abs(b.xmax + 40) < 1e-3:
        print("  end-face loops:", len(f.Wires()))
        for wire in f.Wires():
            pts = sorted({(round(e.startPoint().y, 2), round(e.startPoint().z, 2)) for e in wire.Edges()})
            print("   ", pts[:40])
band = box(-200, 600, -40, -20, 0, 400)
for label in ("Bambu", "RedLizard"):
    d = world(v[label]["dock"], 7.0, frames)
    t = world(v[label]["tool"], 7.0, frames)
    print(label, "dock", bb(d), "tool", bb(t))
    print(label, "dock in Y-40..-20", bb(d.intersect(band)), "tool in band", "none" if t.intersect(band).isNull() or not t.intersect(band).Solids() else bb(t.intersect(band)))
rig = compound([s for _, s in carriage()])
act = world(rig, 7.0, frames)
print("active carriage at bay0 dock", bb(act))
near = act.intersect(box(-70, -5, -45, 60, 100, 260))
print("carriage part with X<-5:", "none" if near.isNull() or not near.Solids() else bb(near))
beam = cq.importers.importStep(str(W / "rack_audit_X_Gantry_world.step")).val().translate((0, frames["x_gantry_y_shift_to_dock_mm"], 0))
print("x beam at dock", bb(beam))
nb = beam.intersect(box(-70, -5, -45, 60, 100, 260))
print("beam part X<-5", "none" if nb.isNull() or not nb.Solids() else bb(nb))
fly = cq.Shape.importBrep(str(W / "rack_audit_Flying_Gantry_world.brep"))
for z in (172.5, 173.0, 173.4, 173.6, 174.5):
    s = fly.intersect(box(-58.5, -36.5, -39, 20, z, z + 0.1))
    print("gantry material in deck footprint at Z", z, "=", 0 if s.isNull() else round(s.Volume(), 3))
for z in (172.5, 173.4):
    s = fly.intersect(box(-58.5, -36.5, -39, 20, z, z + 0.1))
    if not s.isNull() and s.Solids():
        print("  bbox", bb(s))
print("gantry zmax overall", bb(fly)[5])
top = fly.intersect(box(-100, 450, -100, 500, 215, 230))
for s in top.Solids():
    print("  high gantry solid", bb(s))
