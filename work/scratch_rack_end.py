import json, sys
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
from PIL import Image, ImageDraw
from fast_geometry import load
from audit_low_z_bed_clearance import load_parked_variants
from audit_ten_tool_rack import world
from audit_tool_owned_2510 import compound
from build_modular_toolhead import box, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet

W = primitives.WORK
frames = json.loads((W / "rack_audit_frames.json").read_text())
frames["world_y_offset_mm"] += 6.5
frames["x_gantry_y_shift_to_dock_mm"] += 6.5
fly = cq.Shape.importBrep(str(W / "rack_audit_Flying_Gantry_world.brep"))
beam = cq.importers.importStep(str(W / "rack_audit_X_Gantry_world.step")).val().translate((0, frames["x_gantry_y_shift_to_dock_mm"], 0))
crossbar = cq.importers.importStep(str(W / "rack_audit_crossbar_world.step")).val()
v = load_parked_variants()["Bambu"]
dock0 = world(v["dock"], 7.0, frames)
tool0 = world(v["tool"], 7.0, frames)
p29 = load("P29_Dock_Rack_Gantry_Mount_L"); p30 = load("P30_Dock_Side_Spacer_L")
zrail = box(-74.5, -65.5, -20.0, -13.5, 60.0, 300.0)
side = sys.argv[1] if len(sys.argv) > 1 else "L"
clip = box(-95, 30, -50, 85, 100, 235)
items = [(fly, (0.55, 0.6, 0.7)), (beam, (0.35, 0.45, 0.6)), (crossbar, (0.25, 0.25, 0.28)), (p29, (0.95, 0.55, 0.12)),
         (p30, (0.2, 0.7, 0.3)), (dock0, (0.75, 0.2, 0.7)), (tool0, (0.85, 0.85, 0.4)), (zrail, (0.9, 0.1, 0.1))]
actors = []
for shape, color in items:
    part = shape.intersect(clip)
    if part.isNull() or not part.Solids():
        continue
    actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
panels = []
for eye, target, title in (((-260, -260, 330), (-45, 10, 170), "Left rack end from front-left-above"),
                           ((-380, 15, 175), (-45, 15, 170), "Left rack end from -X (side)"),
                           ((-45, -360, 175), (-45, 15, 170), "Left rack end from front (-Y)"),
                           ((-45, 20, 480), (-45, 20, 170), "Left rack end from above")):
    path = W / "scratch_panel.png"
    render_view(actors, eye, target, (0, 1, 0) if title.endswith("above") else (0, 0, 1), path, width=900, height=760)
    im = Image.open(path).convert("RGB"); ImageDraw.Draw(im).text((12, 12), title, fill=(10, 10, 10)); panels.append(im)
out = W / "scratch_rack_end_L.png"
sheet(panels, 2, (900, 760), out)
print(out)

